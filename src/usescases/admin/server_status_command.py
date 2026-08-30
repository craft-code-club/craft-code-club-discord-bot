"""/server-status - membership statistics for the guild.

Everything here used to be read from the gateway member cache. Members and
roles now come from REST (one page of 1000 members per request), and
administrator counts are computed from the role permission bitfields.

One genuine downgrade: the exact online count is gone. Per-member presence is
only delivered over the gateway with the GUILD_PRESENCES intent and has no
REST equivalent, so this reports Discord's `approximate_presence_count`.
"""

import logging
import os
from datetime import datetime, timezone

from discord_api import interactions
from discord_api.rest import DiscordRest, member_is_administrator

from .permissions import require_admin

logger = logging.getLogger(__name__)


async def handle(rest: DiscordRest, interaction: dict) -> None:
    guild_id = await require_admin(rest, interaction, 'server-status')
    if not guild_id:
        return

    logger.debug('[COMMAND][STATUS] User "%s" requested the server status',
                 interactions.user_name(interaction))

    guild = await rest.get_guild(guild_id, with_counts=True)
    guild_name = guild.get('name', guild_id)
    member_count = guild.get('approximate_member_count')
    presence_count = guild.get('approximate_presence_count')

    max_members = int(os.environ.get('STATUS_MAX_MEMBERS', '5000'))
    if member_count and member_count > max_members:
        logger.warning('[COMMAND][STATUS] Guild "%s" has %s members, exceeding cap of %s. '
                       'Skipping status fetch.', guild_name, member_count, max_members)
        await rest.edit_original_response(
            interaction['token'],
            content='\n'.join([
                f'**{guild_name}**',
                f'- **Erro:** servidor demasiado grande ({member_count} membros, limite {max_members})',
                f'- **Atualizado em:** {_timestamp()}',
            ]))
        return

    roles = await rest.get_guild_roles(guild_id)
    roles_by_id = {str(role['id']): role for role in roles}
    owner_id = str(guild.get('owner_id', ''))

    total_users = 0
    total_admins = 0
    no_role_users = 0
    role_counts: dict[str, int] = {}

    async for member in rest.iter_members(guild_id):
        total_users += 1
        if member_is_administrator(member, roles_by_id, guild_id, owner_id):
            total_admins += 1
        member_roles = [str(role_id) for role_id in member.get('roles', [])]
        if not member_roles:
            no_role_users += 1
        for role_id in member_roles:
            role_counts[role_id] = role_counts.get(role_id, 0) + 1

    role_lines = [
        f'  - {roles_by_id[role_id]["name"]}: {role_counts[role_id]}'
        for role_id in sorted(role_counts,
                              key=lambda rid: roles_by_id.get(rid, {}).get('position', 0),
                              reverse=True)
        if role_id in roles_by_id and role_id != str(guild_id)
    ]

    online = f'{presence_count} (aproximado)' if presence_count is not None else 'indisponível'

    lines = [
        f'**{guild_name}**',
        f'- **Total de utilizadores:** {total_users}',
        f'- **Utilizadores online:** {online}',
        f'- **Total de administradores:** {total_admins}',
        f'- **Utilizadores sem role:** {no_role_users}',
        '- **Utilizadores por role:**',
    ] + role_lines + [f'- **Atualizado em:** {_timestamp()}']

    await rest.respond_chunked(interaction['token'], '\n'.join(lines))
    logger.info('[COMMAND][STATUS] Sent server status for guild "%s" to admin "%s"',
                guild_name, interactions.user_name(interaction))


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
