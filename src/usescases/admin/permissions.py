"""Administrator checks without the gateway member cache.

`is_server_admin()` used to walk `bot.guilds` and read
`guild.get_member(id).guild_permissions.administrator`, which only exists
inside a live gateway session. Two replacements, cheapest first:

  * a guild interaction carries a precomputed `member.permissions` bitfield,
    so no API call is needed at all;
  * a DM interaction has no guild context, so the member and the guild's roles
    are fetched over REST and the bitfield is computed locally.
"""

import logging
from typing import Optional

from discord_api import interactions
from discord_api.rest import (PERMISSION_ADMINISTRATOR, DiscordRest,
                              member_is_administrator)
from utils import config

logger = logging.getLogger(__name__)


async def is_admin(rest: DiscordRest, interaction: dict) -> bool:
    """True when the invoking user is an administrator OF THE CONFIGURED GUILD.

    The guild matters. `member.permissions` describes the guild the interaction
    came from, so trusting it unconditionally would let an administrator of any
    other server the bot happens to be in run these commands against the
    community's server. It is only used when the interaction came from the
    configured guild; every other case falls through to a REST lookup that is
    explicitly scoped to that guild.
    """
    guild_id = await config.resolve_guild_id(rest)
    if not guild_id:
        return False

    if interactions.guild_id(interaction) == str(guild_id):
        permissions = interactions.member_permissions(interaction)
        if permissions is not None:
            return permissions & PERMISSION_ADMINISTRATOR != 0

    user_id = interactions.user_id(interaction)
    if not user_id:
        return False

    member = await rest.get_member(guild_id, user_id)
    if member is None:
        return False

    guild = await rest.get_guild(guild_id)
    roles = await rest.get_guild_roles(guild_id)
    roles_by_id = {str(role['id']): role for role in roles}

    return member_is_administrator(member, roles_by_id, guild_id, str(guild.get('owner_id', '')))


async def require_admin(rest: DiscordRest, interaction: dict, command: str) -> Optional[str]:
    """Resolve the guild for an admin command, or answer with a refusal.

    Returns the guild id when the caller is an administrator, otherwise None
    after replying to the interaction.
    """
    if not await is_admin(rest, interaction):
        logger.warning('[COMMAND][%s] User "%s" is not a server admin. Ignoring',
                       command.upper(), interactions.user_name(interaction))
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Este comando é apenas para administradores do servidor.')
        return None

    guild_id = await config.resolve_guild_id(rest)
    if not guild_id:
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Configuração inválida: não foi possível determinar o servidor '
                    '(define `DISCORD_GUILD_ID`).')
        return None
    return guild_id
