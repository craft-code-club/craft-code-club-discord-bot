"""Greet new members. Runs on a timer trigger every 5 minutes.

Why a poller and not an event handler: GUILD_MEMBER_ADD is a gateway-only
event. Discord's Webhook Events feature delivers exactly twelve event types
(authorization, entitlement and Social SDK events) and none of them is a
member join, and the audit log has no join action either. Polling the member
list is the only HTTP-only way to notice a new member.

Tradeoffs versus the gateway `on_member_join` listener:
  * a welcome now lands within one poll interval instead of ~10 seconds;
  * the anti-scam grace period is kept: members who joined within
    WELCOME_DELAY_SECONDS are left for the next run, and each one is re-checked
    immediately before being greeted (the same guard the listener had after its
    sleep), so an account banned between the scan and the send is skipped;
  * a member who leaves and rejoins gets welcomed again, because Discord
    rewrites `joined_at` on rejoin.

`GET /guilds/{id}/members` requires the GUILD_MEMBERS privileged intent to
stay enabled for the application, even with no gateway connection.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from discord_api.rest import DiscordRest
from utils.state_dao import get_state_dao
from utils import config
from utils.message_loader import load_message

logger = logging.getLogger(__name__)

WATERMARK_KEY = 'new_member_watermark'

# Upper bound on welcomes per run, so a member-list backfill or a raid cannot
# turn into hundreds of DMs in one invocation. The rest are picked up next run.
MAX_WELCOMES_PER_RUN = 25


async def run(rest: DiscordRest) -> None:
    guild_id = await config.resolve_guild_id(rest)
    if not guild_id:
        logger.error('[TASK][NEW MEMBER] Could not resolve the guild. Skipping.')
        return

    state = get_state_dao()
    now = datetime.now(timezone.utc)
    # Members who joined within the grace window are left for the next run.
    cutoff = now - timedelta(seconds=config.welcome_delay_seconds())

    watermark = _read_watermark(state)
    if watermark is None:
        # First ever run: adopt the current moment so the entire existing
        # membership is not greeted at once.
        _write_watermark(state, cutoff)
        logger.info('[TASK][NEW MEMBER] Initialised the join watermark at %s. No welcomes this run.',
                    cutoff.isoformat())
        return

    arrivals = []
    async for member in rest.iter_members(guild_id):
        joined_at = _parse_joined_at(member.get('joined_at'))
        if joined_at is None or not (watermark < joined_at <= cutoff):
            continue
        if member.get('user', {}).get('bot'):
            logger.info('[TASK][NEW MEMBER] Bot "%s" joined the server', _name(member))
            continue
        arrivals.append((joined_at, member))

    arrivals.sort(key=lambda item: item[0])
    capped = arrivals[:MAX_WELCOMES_PER_RUN]

    welcomed = 0
    for joined_at, member in capped:
        if not await _still_a_member(rest, guild_id, member):
            logger.info('[TASK][NEW MEMBER] "%s" left or was removed during the grace period. '
                        'No welcome message will be sent.', _name(member))
        else:
            logger.info('[TASK][NEW MEMBER] "%s" joined the server', _name(member))
            await _welcome(rest, member)
            welcomed += 1

        # Advance after EVERY member, not once at the end: an invocation that
        # dies halfway (a timeout, a worker recycle) must not re-greet the
        # people it already messaged on the next run.
        _write_watermark(state, joined_at)

    if len(arrivals) > len(capped):
        logger.warning('[TASK][NEW MEMBER] %s new members found, %s processed this run; '
                       'the remainder follow next run.', len(arrivals), len(capped))
    else:
        # Everything up to the cutoff has been handled.
        _write_watermark(state, cutoff)

    logger.debug('[TASK][NEW MEMBER] %s member(s) processed, %s welcomed.', len(capped), welcomed)


async def _still_a_member(rest: DiscordRest, guild_id: str, member: dict) -> bool:
    """Re-check just before greeting, mirroring the listener's post-sleep fetch.

    The member list is a snapshot; an anti-scam bot may have removed the account
    since it was taken.
    """
    user_id = member.get('user', {}).get('id')
    if not user_id:
        return False
    try:
        return await rest.get_member(guild_id, user_id) is not None
    except Exception:  # noqa: BLE001 - a lookup failure must not block the welcome
        logger.exception('[TASK][NEW MEMBER] Could not verify if "%s" is still in the server',
                         _name(member))
        return False


async def _welcome(rest: DiscordRest, member: dict) -> None:
    await _send_channel_welcome(rest, member)
    await _send_admin_notification(rest, member)
    await _send_dm_welcome(rest, member)


async def _send_channel_welcome(rest: DiscordRest, member: dict) -> None:
    if not config.welcome_message_enabled():
        logger.debug('[TASK][NEW MEMBER] Public welcome disabled (WELCOME_MESSAGE_ENABLED). Skipping for "%s".',
                     _name(member))
        return

    channel_id = config.welcome_channel_id()
    if not channel_id:
        logger.debug('[TASK][NEW MEMBER] WELCOME_CHANNEL_ID is not set. Skipping public welcome for "%s".',
                     _name(member))
        return

    try:
        message = _replace_welcome_placeholders(
            load_message('channel_welcome_message.md'), _mention(member))
        # The public welcome is meant to ping the new member - the REST client
        # suppresses every mention by default, so it has to be allowed here.
        await rest.send_message(channel_id, content=message,
                                allowed_mentions={'parse': [], 'users': [str(member['user']['id'])]})
    except Exception:  # noqa: BLE001 - one failed welcome must not stop the run
        logger.exception('[TASK][NEW MEMBER] It was not possible to send a welcome message to the welcome channel')


async def _send_admin_notification(rest: DiscordRest, member: dict) -> None:
    if not config.admin_join_notification_enabled():
        return

    channel_id = config.admin_notification_channel_id()
    if not channel_id:
        logger.debug('[TASK][NEW MEMBER] ADMIN_JOIN_NOTIFICATION_CHANNEL_ID is not set. '
                     'Skipping admin notification for "%s".', _name(member))
        return

    try:
        message = load_message('admin_new_member_message.md').replace('##[username]##', _mention(member))
        # allowed_mentions only controls the ping, not the rendering: the client
        # still turns <@id> into a clickable name. The ping is suppressed because
        # the new member usually cannot see the admin channel, so pinging them
        # would be a confusing "ghost ping".
        await rest.send_message(channel_id, content=message)
    except Exception:  # noqa: BLE001
        logger.exception('[TASK][NEW MEMBER] It was not possible to send the admin join notification')


async def _send_dm_welcome(rest: DiscordRest, member: dict) -> None:
    try:
        message = _replace_welcome_placeholders(
            load_message('dm_welcome_message.md'), _username(member))
        await rest.send_dm(member['user']['id'], content=message)
    except Exception:  # noqa: BLE001
        logger.exception('[TASK][NEW MEMBER] It was not possible to send the welcome DM to "%s"', _name(member))


def _replace_welcome_placeholders(message: str, username: str) -> str:
    say_hi_channel = config.say_hi_channel_mention()
    lines = [
        line.replace('##[username]##', username).replace('##[say_hi_channel]##', say_hi_channel)
        for line in message.splitlines()
        if say_hi_channel or '##[say_hi_channel]##' not in line
    ]
    return '\n'.join(lines)


def _parse_joined_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        logger.warning('[TASK][NEW MEMBER] Could not parse joined_at "%s"', value)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _read_watermark(state) -> Optional[datetime]:
    raw = state.get(WATERMARK_KEY)
    return _parse_joined_at(raw) if raw else None


def _write_watermark(state, value: datetime) -> None:
    state.set(WATERMARK_KEY, value.astimezone(timezone.utc).isoformat())


def _name(member: dict) -> str:
    return member.get('user', {}).get('username', 'unknown')


def _username(member: dict) -> str:
    return member.get('user', {}).get('username', 'unknown')


def _mention(member: dict) -> str:
    return f'<@{member.get("user", {}).get("id", "")}>'
