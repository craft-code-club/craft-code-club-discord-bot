"""Async Discord REST client - the outbound half of the bot.

Every Discord operation this bot performs is a plain HTTPS call with a bot
token; none of them need a gateway connection. Routes used here:

  messages          POST   /channels/{channel_id}/messages
  direct messages   POST   /users/@me/channels  +  POST /channels/{dm}/messages
  members           GET    /guilds/{guild_id}/members
                    GET    /guilds/{guild_id}/members/{user_id}
                    PUT    /guilds/{guild_id}/members/{user_id}/roles/{role_id}
  roles             GET    /guilds/{guild_id}/roles
  guild             GET    /guilds/{guild_id}
  channel           GET    /channels/{channel_id}
  scheduled events  POST   /guilds/{guild_id}/scheduled-events
                    GET    /guilds/{guild_id}/scheduled-events/{event_id}
                    DELETE /guilds/{guild_id}/scheduled-events/{event_id}
  interactions      PATCH  /webhooks/{app_id}/{token}/messages/@original
                    POST   /webhooks/{app_id}/{token}
"""

import asyncio
import base64
import logging
import os
from datetime import datetime
from typing import Any, AsyncIterator, Optional

import aiohttp

logger = logging.getLogger(__name__)

API_BASE = 'https://discord.com/api/v10'

# Discord caps a message at 2000 characters.
MESSAGE_LIMIT = 2000

# Permission bits we care about (https://discord.com/developers/docs/topics/permissions).
PERMISSION_ADMINISTRATOR = 1 << 3

# Guild scheduled event enums.
PRIVACY_LEVEL_GUILD_ONLY = 2
ENTITY_TYPE_EXTERNAL = 3

_MAX_RETRIES = 3
# 429s get their own budget: a rate-limit wait is the API working as intended,
# not a failure, so it must not consume the retries reserved for 5xx.
_MAX_RATE_LIMIT_WAITS = 5
_MAX_RATE_LIMIT_SLEEP = 120


class DiscordApiError(Exception):
    """A non-retryable error response from the Discord API."""

    def __init__(self, status: int, route: str, payload: Any):
        self.status = status
        self.route = route
        self.payload = payload
        super().__init__(f'{route} failed with HTTP {status}: {payload}')


class DiscordRest:
    """Thin async wrapper over the Discord REST API.

    Use as an async context manager so the aiohttp session is always closed;
    an Azure Functions worker is recycled between invocations and a leaked
    session logs "Unclosed client session" noise on teardown.
    """

    def __init__(self, token: Optional[str] = None, application_id: Optional[str] = None):
        self._token = token or os.environ.get('DISCORD_API_TOKEN', '')
        self.application_id = application_id or os.environ.get('DISCORD_APPLICATION_ID', '')
        if not self._token:
            raise RuntimeError('DISCORD_API_TOKEN is not set')
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> 'DiscordRest':
        self._session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bot {self._token}',
                'User-Agent': 'CraftCodeClubBot (https://craftcodeclub.io, functions)',
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, *_exc_info) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # transport
    # ------------------------------------------------------------------
    async def request(self, method: str, route: str, *, json_body: Any = None,
                      params: Optional[dict] = None) -> Any:
        """Perform one API call, honouring 429 Retry-After and retrying 5xx."""
        if self._session is None:
            raise RuntimeError('DiscordRest must be used as an async context manager')

        url = f'{API_BASE}{route}'
        rate_limit_waits = 0
        attempt = 0

        while attempt < _MAX_RETRIES:
            attempt += 1
            async with self._session.request(method, url, json=json_body, params=params) as response:
                if response.status == 429:
                    body = await self._safe_json(response)
                    retry_after = float(body.get('retry_after', 1)) if isinstance(body, dict) else 1.0
                    scope = 'Globally rate' if (isinstance(body, dict) and body.get('global')) else 'Rate'
                    rate_limit_waits += 1
                    if rate_limit_waits > _MAX_RATE_LIMIT_WAITS:
                        raise DiscordApiError(429, route, 'rate limited too many times')
                    logger.warning('[DISCORD][REST] %s limited on %s, waiting %.2fs (%s/%s)',
                                   scope, route, retry_after, rate_limit_waits, _MAX_RATE_LIMIT_WAITS)
                    await asyncio.sleep(min(retry_after, _MAX_RATE_LIMIT_SLEEP) + 0.1)
                    attempt -= 1  # waiting out a rate limit is not a failed attempt
                    continue

                if response.status >= 500 and attempt < _MAX_RETRIES:
                    logger.warning('[DISCORD][REST] %s %s returned %s, retrying', method, route, response.status)
                    await asyncio.sleep(attempt)
                    continue

                if response.status == 204 or response.content_length == 0:
                    if response.status >= 400:
                        raise DiscordApiError(response.status, route, None)
                    return None

                body = await self._safe_json(response)
                if response.status >= 400:
                    raise DiscordApiError(response.status, route, body)
                return body

        raise DiscordApiError(503, route, 'exhausted retries')

    @staticmethod
    async def _safe_json(response: aiohttp.ClientResponse) -> Any:
        try:
            return await response.json(content_type=None)
        except Exception:  # noqa: BLE001 - body may not be JSON on an error path
            return await response.text()

    # ------------------------------------------------------------------
    # messages
    # ------------------------------------------------------------------
    async def send_message(self, channel_id: int | str, content: Optional[str] = None,
                           embed: Optional[dict] = None,
                           allowed_mentions: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {'allowed_mentions': allowed_mentions or no_mentions()}
        if content is not None:
            payload['content'] = content
        if embed is not None:
            payload['embeds'] = [embed]
        return await self.request('POST', f'/channels/{channel_id}/messages', json_body=payload)

    async def send_chunked(self, channel_id: int | str, text: str, limit: int = MESSAGE_LIMIT) -> None:
        """Send `text` as as few messages as possible without exceeding `limit`."""
        for chunk in chunk_text(text, limit):
            await self.send_message(channel_id, chunk)

    async def create_dm_channel(self, user_id: int | str) -> dict:
        return await self.request('POST', '/users/@me/channels', json_body={'recipient_id': str(user_id)})

    async def send_dm(self, user_id: int | str, content: Optional[str] = None,
                      embed: Optional[dict] = None) -> Optional[dict]:
        """DM a user. Returns None when the user has DMs closed (HTTP 403)."""
        try:
            channel = await self.create_dm_channel(user_id)
            return await self.send_message(channel['id'], content=content, embed=embed)
        except DiscordApiError as error:
            if error.status == 403:
                logger.warning('[DISCORD][REST] User "%s" has DMs disabled', user_id)
                return None
            raise

    async def send_dm_chunked(self, user_id: int | str, text: str, limit: int = MESSAGE_LIMIT) -> None:
        try:
            channel = await self.create_dm_channel(user_id)
        except DiscordApiError as error:
            if error.status == 403:
                logger.warning('[DISCORD][REST] User "%s" has DMs disabled', user_id)
                return
            raise
        for chunk in chunk_text(text, limit):
            await self.send_message(channel['id'], chunk)

    # ------------------------------------------------------------------
    # guilds, channels, members and roles
    # ------------------------------------------------------------------
    async def get_channel(self, channel_id: int | str) -> dict:
        return await self.request('GET', f'/channels/{channel_id}')

    async def get_guild(self, guild_id: int | str, with_counts: bool = False) -> dict:
        params = {'with_counts': 'true'} if with_counts else None
        return await self.request('GET', f'/guilds/{guild_id}', params=params)

    async def get_guild_roles(self, guild_id: int | str) -> list[dict]:
        return await self.request('GET', f'/guilds/{guild_id}/roles')

    async def get_member(self, guild_id: int | str, user_id: int | str) -> Optional[dict]:
        try:
            return await self.request('GET', f'/guilds/{guild_id}/members/{user_id}')
        except DiscordApiError as error:
            if error.status == 404:
                return None
            raise

    async def iter_members(self, guild_id: int | str, page_size: int = 1000) -> AsyncIterator[dict]:
        """Paginate the full member list.

        `after` pages by user snowflake (account creation order), which is why
        there is no "members who joined since X" query - callers filter on the
        `joined_at` field themselves.
        Requires the GUILD_MEMBERS privileged intent to be enabled for the app,
        even though no gateway connection is ever opened.
        """
        after = '0'
        while True:
            page = await self.request(
                'GET', f'/guilds/{guild_id}/members',
                params={'limit': str(page_size), 'after': after},
            )
            if not page:
                return
            for member in page:
                yield member
            if len(page) < page_size:
                return
            after = page[-1]['user']['id']

    async def add_role(self, guild_id: int | str, user_id: int | str, role_id: int | str) -> None:
        await self.request('PUT', f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}')

    async def search_members(self, guild_id: int | str, query: str, limit: int = 100) -> list[dict]:
        return await self.request(
            'GET', f'/guilds/{guild_id}/members/search',
            params={'query': query, 'limit': str(limit)},
        )

    # ------------------------------------------------------------------
    # guild scheduled events
    # ------------------------------------------------------------------
    async def create_scheduled_event(self, guild_id: int | str, *, name: str, description: str,
                                     start_time: datetime, end_time: datetime, location: str,
                                     image: Optional[bytes] = None,
                                     image_content_type: Optional[str] = None) -> dict:
        payload: dict[str, Any] = {
            'name': name,
            'description': description,
            'scheduled_start_time': start_time.isoformat(),
            'scheduled_end_time': end_time.isoformat(),
            'privacy_level': PRIVACY_LEVEL_GUILD_ONLY,
            'entity_type': ENTITY_TYPE_EXTERNAL,
            'entity_metadata': {'location': location},
        }
        if image:
            payload['image'] = to_data_uri(image, image_content_type)
        return await self.request('POST', f'/guilds/{guild_id}/scheduled-events', json_body=payload)

    async def get_scheduled_event(self, guild_id: int | str, event_id: int | str) -> Optional[dict]:
        try:
            return await self.request('GET', f'/guilds/{guild_id}/scheduled-events/{event_id}')
        except DiscordApiError as error:
            if error.status == 404:
                return None
            raise

    async def delete_scheduled_event(self, guild_id: int | str, event_id: int | str) -> None:
        try:
            await self.request('DELETE', f'/guilds/{guild_id}/scheduled-events/{event_id}')
        except DiscordApiError as error:
            if error.status != 404:
                raise

    # ------------------------------------------------------------------
    # interaction follow-ups (the deferred half of a slash command)
    # ------------------------------------------------------------------
    async def edit_original_response(self, interaction_token: str, *, content: Optional[str] = None,
                                     embed: Optional[dict] = None) -> dict:
        payload: dict[str, Any] = {'allowed_mentions': no_mentions()}
        if content is not None:
            payload['content'] = content
        if embed is not None:
            payload['embeds'] = [embed]
        return await self.request(
            'PATCH', f'/webhooks/{self.application_id}/{interaction_token}/messages/@original',
            json_body=payload,
        )

    async def create_followup(self, interaction_token: str, *, content: Optional[str] = None,
                              embed: Optional[dict] = None, ephemeral: bool = True) -> dict:
        payload: dict[str, Any] = {'allowed_mentions': no_mentions()}
        if content is not None:
            payload['content'] = content
        if embed is not None:
            payload['embeds'] = [embed]
        if ephemeral:
            payload['flags'] = 1 << 6
        return await self.request(
            'POST', f'/webhooks/{self.application_id}/{interaction_token}', json_body=payload,
        )

    async def respond_chunked(self, interaction_token: str, text: str, limit: int = MESSAGE_LIMIT) -> None:
        """Answer a deferred interaction with text that may exceed one message."""
        chunks = chunk_text(text, limit)
        if not chunks:
            chunks = ['(sem conteúdo)']
        await self.edit_original_response(interaction_token, content=chunks[0])
        for chunk in chunks[1:]:
            await self.create_followup(interaction_token, content=chunk)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def no_mentions() -> dict:
    """allowed_mentions payload that suppresses every ping."""
    return {'parse': []}


def everyone_mention() -> dict:
    """allowed_mentions payload that allows @everyone and nothing else."""
    return {'parse': ['everyone']}


def escape_mentions(text: str) -> str:
    """Neutralise @everyone / @here in user-supplied text (discord.py parity)."""
    return text.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')


def chunk_text(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Split `text` on line boundaries into chunks of at most `limit` chars."""
    chunks: list[str] = []
    chunk = ''
    for line in text.split('\n'):
        while len(line) > limit:
            slice_, line = line[:limit], line[limit:]
            if chunk:
                chunks.append(chunk)
                chunk = ''
            chunks.append(slice_)

        candidate = f'{chunk}\n{line}' if chunk else line
        if len(candidate) > limit:
            if chunk:
                chunks.append(chunk)
            chunk = line
        else:
            chunk = candidate
    if chunk:
        chunks.append(chunk)
    return chunks


def to_data_uri(data: bytes, content_type: Optional[str] = None) -> str:
    """Encode image bytes as the data URI Discord expects for image fields."""
    mime = content_type or 'image/png'
    return f'data:{mime};base64,{base64.b64encode(data).decode("ascii")}'


def member_is_administrator(member: dict, roles_by_id: dict[str, dict],
                            guild_id: str, guild_owner_id: str) -> bool:
    """Compute ADMINISTRATOR for a member from the guild's role permissions.

    Replaces `guild.get_member(id).guild_permissions.administrator`, which read
    the gateway member cache that no longer exists. The guild owner always has
    every permission, and the @everyone role (whose id equals the guild id) is
    implicit - it never appears in `member["roles"]`.
    """
    user_id = str(member.get('user', {}).get('id', ''))
    if user_id and user_id == str(guild_owner_id):
        return True

    permissions = 0
    everyone = roles_by_id.get(str(guild_id))
    if everyone:
        permissions |= int(everyone.get('permissions', 0))
    for role_id in member.get('roles', []):
        role = roles_by_id.get(str(role_id))
        if role:
            permissions |= int(role.get('permissions', 0))

    return permissions & PERMISSION_ADMINISTRATOR != 0
