"""Environment configuration, shared by every trigger.

Same variable names the container bot used, so nothing has to be renamed in
GitHub `vars`/`secrets` or in Pulumi - with one addition, `DISCORD_GUILD_ID`.
The gateway bot could reach the guild through `channel.guild` in its cache;
a stateless function has no cache, so the guild is either configured
explicitly or resolved once from the community-events channel.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

TRUTHY_VALUES = ('1', 'true', 'yes', 'on')


def parse_bool(raw: Optional[str], default: bool = False) -> bool:
    value = (raw or '').strip().lower()
    if not value:
        return default
    return value in TRUTHY_VALUES


def parse_channel_id(env_var: str) -> int:
    """Read a Discord snowflake from the environment, 0 when unset/invalid."""
    raw = os.environ.get(env_var, '').strip()
    if raw and not raw.isdigit():
        logger.warning('[CONFIG] %s must be a Discord ID (digits). Ignoring "%s".', env_var, raw)
        return 0
    return int(raw) if raw.isdigit() else 0


def community_events_channel_id() -> int:
    return parse_channel_id('COMMUNITY_EVENTS_CHANNEL_ID')


def logs_channel_id() -> int:
    return parse_channel_id('LOGS_CHANNEL_ID')


def welcome_channel_id() -> int:
    return parse_channel_id('WELCOME_CHANNEL_ID')


def admin_notification_channel_id() -> int:
    return parse_channel_id('ADMIN_JOIN_NOTIFICATION_CHANNEL_ID')


def say_hi_channel_mention() -> str:
    channel_id = parse_channel_id('SAY_HI_CHANNEL')
    return f'<#{channel_id}>' if channel_id else ''


def welcome_message_enabled() -> bool:
    return parse_bool(os.environ.get('WELCOME_MESSAGE_ENABLED'), default=False)


def admin_join_notification_enabled() -> bool:
    return parse_bool(os.environ.get('ADMIN_JOIN_NOTIFICATION_ENABLED'), default=False)


def welcome_delay_seconds() -> int:
    """Grace period before greeting a new member.

    The container bot slept this long inside `on_member_join` so anti-scam bots
    could kick a suspicious account first. The poller instead ignores members
    who joined more recently than this, which achieves the same thing without
    holding a process open - an account kicked during the grace window simply
    never appears in a later member list.
    """
    raw = os.environ.get('WELCOME_DELAY_SECONDS', '').strip()
    return int(raw) if raw.isdigit() else 10


def bot_version() -> str:
    """The deployed version, reported by /version and /info.

    Read from the VERSION file written into the package at build time, so it
    always matches the code that is actually running - an app setting could be
    reverted by an unrelated `pulumi up`. Falls back to the environment (handy
    locally) and then to "dev".
    """
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as handle:
            version = handle.read().strip()
            if version:
                return version
    except OSError:
        pass
    return os.environ.get('BOT_VERSION', 'dev')


async def resolve_guild_id(rest) -> Optional[str]:
    """The guild the bot operates on.

    Prefers the explicit `DISCORD_GUILD_ID`; otherwise derives it from the
    community-events channel with one REST call.
    """
    configured = os.environ.get('DISCORD_GUILD_ID', '').strip()
    if configured.isdigit():
        return configured

    channel_id = community_events_channel_id()
    if not channel_id:
        logger.error('[CONFIG] Neither DISCORD_GUILD_ID nor COMMUNITY_EVENTS_CHANNEL_ID is set; '
                     'cannot determine the guild.')
        return None

    channel = await rest.get_channel(channel_id)
    guild_id = channel.get('guild_id')
    if not guild_id:
        logger.error('[CONFIG] Channel %s has no guild_id (is it a DM channel?).', channel_id)
        return None
    return str(guild_id)
