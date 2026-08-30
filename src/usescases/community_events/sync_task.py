"""Sync events from craftcodeclub.io into Table Storage and Discord.

Ported from the `@tasks.loop(hours=3)` cog. Creating and deleting guild
scheduled events used `guild.create_scheduled_event` / `fetch_scheduled_event`
from the gateway cache; both are now direct REST calls, and the guild is
resolved from configuration instead of from `channel.guild`.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from discord_api.rest import DiscordRest
from usescases.community_events.community_event import CommunityEvent
from usescases.community_events.community_events_dao import get_community_events_dao
from utils.state_dao import LAST_SYNC_KEY, get_state_dao
from usescases.community_events.community_event_formatter import event_formatter
from usescases.community_events.website_service import website_service
from utils import config
from utils.reporting import report

logger = logging.getLogger(__name__)


async def run(rest: DiscordRest) -> None:
    guild_id = await config.resolve_guild_id(rest)
    if not guild_id:
        logger.error('[TASK][COMMUNITY EVENTS][UPDATE] Could not resolve the guild. Skipping.')
        return

    dao = get_community_events_dao()
    events = await website_service.fetch_future_events()

    for event in events:
        try:
            await _sync_event(rest, dao, guild_id, event)
        except Exception as error:  # noqa: BLE001 - one bad event must not stop the rest
            logger.exception('[TASK][COMMUNITY EVENTS][UPDATE] Failed to process event "%s"', event.id)
            await report(rest, f'[COMMUNITY EVENTS][UPDATE] Failed to process event "{event.id}": {error}')

    get_state_dao().set(LAST_SYNC_KEY, datetime.now(timezone.utc).isoformat(timespec='seconds'))
    logger.debug('[TASK][COMMUNITY EVENTS][UPDATE] Updated community events finished successfully.')


async def _sync_event(rest: DiscordRest, dao, guild_id: str, event: CommunityEvent) -> None:
    existing_event = dao.get(event.id)
    if existing_event:
        if not event.has_recording_link() and existing_event.has_recording_link():
            event.recording_link = existing_event.recording_link

        if not event.session_link and existing_event.session_link:
            event.session_link = existing_event.session_link

        if existing_event.start_datetime == event.start_datetime:
            event.discord_event_id = existing_event.discord_event_id
        else:
            # The event moved: drop the old Discord scheduled event and its row,
            # then recreate both below at the new time.
            if existing_event.discord_event_id:
                await _delete_discord_event(rest, guild_id, existing_event.discord_event_id)
            dao.delete(existing_event.id, existing_event.start_datetime)

    if not event.discord_event_id:
        event.discord_event_id = await _create_discord_event(rest, guild_id, event)

    dao.upsert(event)
    logger.info('[TASK][COMMUNITY EVENTS][UPDATE] upserted event "%s"', event.id)


async def _create_discord_event(rest: DiscordRest, guild_id: str, event: CommunityEvent) -> Optional[str]:
    try:
        logger.debug('[TASK][COMMUNITY EVENTS][DISCORD] Creating discord event for "%s"', event.title)

        payload = await event_formatter.format_to_discord_event(event)
        discord_event = await rest.create_scheduled_event(guild_id, **payload.as_kwargs())
        discord_event_id = str(discord_event['id'])

        logger.info('[TASK][COMMUNITY EVENTS][DISCORD] Created discord event for "%s" with Id "%s"',
                    event.title, discord_event_id)

        await _send_event_created_log_message(rest, event, discord_event_id)
        return discord_event_id
    except Exception:  # noqa: BLE001 - the row is still worth persisting without a Discord event
        logger.exception('[TASK][COMMUNITY EVENTS][DISCORD] Failed to create discord event for "%s"', event.title)
        return None


async def _send_event_created_log_message(rest: DiscordRest, event: CommunityEvent,
                                          discord_event_id: str) -> None:
    channel_id = config.logs_channel_id()
    if not channel_id:
        return

    try:
        await rest.send_message(
            channel_id,
            content=f'[COMMUNITY EVENT] Event created: {event.title} (id: {discord_event_id})',
        )
    except Exception:  # noqa: BLE001 - a missing log message must not fail the sync
        logger.exception('[TASK][COMMUNITY EVENTS][DISCORD] Failed to send event-created log message for "%s"',
                         event.title)


async def _delete_discord_event(rest: DiscordRest, guild_id: str, discord_event_id: str) -> None:
    try:
        logger.debug('[TASK][COMMUNITY EVENTS][DISCORD] Deleting discord event Id "%s"', discord_event_id)
        await rest.delete_scheduled_event(guild_id, discord_event_id)
        logger.info('[TASK][COMMUNITY EVENTS][DISCORD] Deleted discord event Id "%s"', discord_event_id)
    except Exception:  # noqa: BLE001 - a stale scheduled event must not stop the sync
        logger.exception('[TASK][COMMUNITY EVENTS][DISCORD] Failed to delete discord event Id "%s"',
                         discord_event_id)
