import os
from datetime import datetime, timezone
import discord
from discord.ext import commands
import logging

from ._helpers import admin_guilds, send_chunked

logger = logging.getLogger(__name__)

_STATUS_CACHE_TTL = 30  # seconds


class ServerStatusCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._status_cache: dict[int, tuple[datetime, str]] = {}

    async def _build_guild_status(self, guild) -> tuple[str, datetime]:
        max_members = int(os.environ.get('STATUS_MAX_MEMBERS', '5000'))
        if guild.member_count and guild.member_count > max_members:
            logger.warning(
                f'[BOT][COMMAND][STATUS] Guild "{guild.name}" has {guild.member_count} members, '
                f'exceeding cap of {max_members}. Skipping status fetch.'
            )
            computed_at = datetime.now(timezone.utc)
            timestamp_str = computed_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            return '\n'.join([
                f'**{guild.name}**',
                f'- **Erro:** servidor demasiado grande ({guild.member_count} membros, limite {max_members})',
                f'- **Atualizado em:** {timestamp_str}',
            ]), computed_at

        total_users = 0
        total_admins = 0
        no_role_users = 0
        role_counts: dict[int, int] = {}
        try:
            async for m in guild.fetch_members(limit=None):
                total_users += 1
                if m.guild_permissions.administrator:
                    total_admins += 1
                if len(m.roles) == 1:
                    no_role_users += 1
                for role in m.roles:
                    if role != guild.default_role:
                        role_counts[role.id] = role_counts.get(role.id, 0) + 1
        except discord.Forbidden:
            logger.warning(f'[BOT][COMMAND][STATUS] Missing permissions to fetch members in guild "{guild.name}"')
            computed_at = datetime.now(timezone.utc)
            timestamp_str = computed_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            return '\n'.join([
                f'**{guild.name}**',
                '- **Erro:** sem permissão para consultar membros',
                f'- **Atualizado em:** {timestamp_str}',
            ]), computed_at
        except discord.HTTPException:
            logger.exception(f'[BOT][COMMAND][STATUS] Failed to fetch members in guild "{guild.name}"')
            computed_at = datetime.now(timezone.utc)
            timestamp_str = computed_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            return '\n'.join([
                f'**{guild.name}**',
                '- **Erro:** erro ao consultar membros',
                f'- **Atualizado em:** {timestamp_str}',
            ]), computed_at
        except Exception:
            logger.exception(f'[BOT][COMMAND][STATUS] Unexpected error while fetching members in guild "{guild.name}"')
            computed_at = datetime.now(timezone.utc)
            timestamp_str = computed_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            return '\n'.join([
                f'**{guild.name}**',
                '- **Erro:** erro inesperado ao consultar membros',
                f'- **Atualizado em:** {timestamp_str}',
            ]), computed_at

        role_lines = [
            f'  - {role.name}: {role_counts[role.id]}'
            for role in sorted(guild.roles, key=lambda r: r.position, reverse=True)
            if role != guild.default_role and role.id in role_counts
        ]

        computed_at = datetime.now(timezone.utc)
        timestamp_str = computed_at.strftime('%Y-%m-%d %H:%M:%S UTC')

        lines = [
            f'**{guild.name}**',
            f'- **Total de utilizadores:** {total_users}',
            f'- **Total de administradores:** {total_admins}',
            f'- **Utilizadores sem role:** {no_role_users}',
            '- **Utilizadores por role:**',
        ] + role_lines + [f'- **Atualizado em:** {timestamp_str}']

        return '\n'.join(lines), computed_at

    async def _get_guild_status(self, guild) -> str:
        cached = self._status_cache.get(guild.id)
        if cached:
            cached_at, text = cached
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < _STATUS_CACHE_TTL:
                return text

        text, computed_at = await self._build_guild_status(guild)
        self._status_cache[guild.id] = (computed_at, text)
        return text

    @commands.command(name='server-status', help='Mostra estatísticas do servidor (apenas administradores, via DM)')
    @commands.dm_only()
    async def status(self, ctx):
        logger.debug(f'[BOT][COMMAND][STATUS] User "{ctx.author.name}" requested the server status')

        guilds = admin_guilds(self.bot, ctx.author.id)
        if not guilds:
            logger.warning(f'[BOT][COMMAND][STATUS] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        for guild in guilds:
            text = await self._get_guild_status(guild)
            await send_chunked(ctx.author, text)
            logger.info(
                f'[BOT][COMMAND][STATUS] Sent server status for guild "{guild.name}" to admin "{ctx.author.name}"'
            )
