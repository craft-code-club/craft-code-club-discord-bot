import os
import re
from datetime import datetime, timezone
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(AdminCommandBot(bot))


class AdminCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started_at = datetime.now(timezone.utc)

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
            if target in (m.name.lower(), m.display_name.lower(), (m.global_name or '').lower())
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

    @commands.command(name='add-role', help='Adiciona um cargo a um utilizador ou a todos com @all (apenas administradores, via DM)')
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
