import os
import re
from datetime import datetime, timezone
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

_STATUS_CACHE_TTL = 30  # seconds


async def setup(bot):
    await bot.add_cog(AdminCommandBot(bot))


class AdminCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started_at = datetime.now(timezone.utc)
        self._status_cache: dict[int, tuple[datetime, str]] = {}

    def _admin_guilds(self, user_id):
        guilds = []
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member and member.guild_permissions.administrator:
                guilds.append(guild)
        return guilds

    def _is_server_admin(self, user_id):
        return len(self._admin_guilds(user_id)) > 0

    @staticmethod
    def _find_role(guild, role_name):
        return discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)

    @staticmethod
    def _find_members(guild, user):
        if user.lower() == '@all':
            return list(guild.members)

        match = re.fullmatch(r'<@!?(\d+)>', user) or re.fullmatch(r'(\d+)', user)
        if match:
            member = guild.get_member(int(match.group(1)))
            return [member] if member else []

        target = user.lower()
        return [
            m for m in guild.members
            if target == m.name.lower()
            or target == m.display_name.lower()
            or target == (m.global_name or '').lower()
        ]

    def _format_uptime(self):
        delta = datetime.now(timezone.utc) - self.started_at
        days, seconds = delta.days, delta.seconds
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f'{days}d {hours}h {minutes}m {seconds}s'

    @commands.command(name='version', help='Mostra a versão do bot (apenas administradores, via DM)')
    @commands.dm_only()
    async def version(self, ctx):
        logger.debug(f'[BOT][COMMAND][VERSION] User "{ctx.author.name}" requested the bot version')

        if not self._is_server_admin(ctx.author.id):
            logger.warning(f'[BOT][COMMAND][VERSION] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        version = os.environ.get('BOT_VERSION', 'dev')
        await ctx.author.send(f'Versão do bot: {version}')
        logger.info(f'[BOT][COMMAND][VERSION] Sent bot version "{version}" to admin "{ctx.author.name}"')

    @commands.command(name='info', help='Mostra a versão e o tempo online do bot (apenas administradores, via DM)')
    @commands.dm_only()
    async def info(self, ctx):
        logger.debug(f'[BOT][COMMAND][INFO] User "{ctx.author.name}" requested the bot info')

        if not self._is_server_admin(ctx.author.id):
            logger.warning(f'[BOT][COMMAND][INFO] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        version = os.environ.get('BOT_VERSION', 'dev')
        uptime = self._format_uptime()
        await ctx.author.send(f'Versão do bot: {version}\nTempo online: {uptime}')
        logger.info(f'[BOT][COMMAND][INFO] Sent bot info (version "{version}", uptime "{uptime}") to admin "{ctx.author.name}"')

    @commands.command(name='add-role', help='Adiciona um role a um utilizador ou a todos com @all (apenas administradores, via DM)')
    @commands.dm_only()
    async def add_role(self, ctx, user: str, *, role_name: str):
        logger.debug(f'[BOT][COMMAND][ADD-ROLE] User "{ctx.author.name}" requested to add role "{role_name}" to "{user}"')

        guilds = self._admin_guilds(ctx.author.id)
        if not guilds:
            logger.warning(f'[BOT][COMMAND][ADD-ROLE] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        summary = []
        for guild in guilds:
            role = self._find_role(guild, role_name)
            if role is None:
                logger.warning(f'[BOT][COMMAND][ADD-ROLE] Role "{role_name}" not found in guild "{guild.name}"')
                summary.append(f'❌ {guild.name}: role "{role_name}" não encontrado')
                continue

            if user.lower() == '@all':
                members = [m async for m in guild.fetch_members(limit=None)]
                max_members = int(os.environ.get('ADD_ROLE_ALL_MAX_MEMBERS', '3000'))
                if len(members) > max_members:
                    logger.warning(
                        f'[BOT][COMMAND][ADD-ROLE] @all request in guild "{guild.name}" aborted: '
                        f'{len(members)} members exceeds cap of {max_members}'
                    )
                    summary.append(
                        f'⚠️ {guild.name}: operação cancelada para @all '
                        f'({len(members)} utilizador(es), limite {max_members})'
                    )
                    continue
                await ctx.author.send(
                    f'⏳ {guild.name}: a adicionar role "{role.name}" a {len(members)} utilizador(es)...'
                )
            else:
                members = self._find_members(guild, user)

            if not members:
                logger.warning(f'[BOT][COMMAND][ADD-ROLE] User "{user}" not found in guild "{guild.name}"')
                summary.append(f'❌ {guild.name}: utilizador "{user}" não encontrado')
                continue

            assigned = 0
            failed = 0
            for member in members:
                try:
                    await member.add_roles(role, reason=f'Requested by admin {ctx.author.name}')
                    assigned += 1
                    logger.info(f'[BOT][COMMAND][ADD-ROLE] Added role "{role.name}" to "{member.name}" in guild "{guild.name}"')
                except discord.Forbidden:
                    failed += 1
                    logger.warning(f'[BOT][COMMAND][ADD-ROLE] Missing permissions to add role "{role.name}" to "{member.name}" in guild "{guild.name}"')
                except Exception:
                    failed += 1
                    logger.exception(f'[BOT][COMMAND][ADD-ROLE] Failed to add role "{role.name}" to "{member.name}" in guild "{guild.name}"')

            line = f'✅ {guild.name}: role "{role.name}" adicionado a {assigned} utilizador(es)'
            if failed:
                line += f' ({failed} falha(s) - verifica as permissões do bot)'
            summary.append(line)
            logger.info(f'[BOT][COMMAND][ADD-ROLE] Added role "{role.name}" to {assigned} member(s) in guild "{guild.name}" ({failed} failures)')

        await ctx.author.send('\n'.join(summary))

    async def _build_guild_status(self, guild) -> tuple[str, datetime]:
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

    @staticmethod
    async def _send_chunked(user, text: str, limit: int = 2000):
        lines = text.split('\n')
        chunk = ''
        for line in lines:
            # Split lines that are themselves longer than the limit into safe slices
            while len(line) > limit:
                slice_, line = line[:limit], line[limit:]
                if chunk:
                    await user.send(chunk)
                    chunk = ''
                await user.send(slice_)

            candidate = chunk + '\n' + line if chunk else line
            if len(candidate) > limit:
                if chunk:
                    await user.send(chunk)
                chunk = line
            else:
                chunk = candidate
        if chunk:
            await user.send(chunk)

    @commands.command(name='server-status', help='Mostra estatísticas do servidor (apenas administradores, via DM)')
    @commands.dm_only()
    async def status(self, ctx):
        logger.debug(f'[BOT][COMMAND][STATUS] User "{ctx.author.name}" requested the server status')

        guilds = self._admin_guilds(ctx.author.id)
        if not guilds:
            logger.warning(f'[BOT][COMMAND][STATUS] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        for guild in guilds:
            text = await self._get_guild_status(guild)
            await self._send_chunked(ctx.author, text)
            logger.info(
                f'[BOT][COMMAND][STATUS] Sent server status for guild "{guild.name}" to admin "{ctx.author.name}"'
            )
