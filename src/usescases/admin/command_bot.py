import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import discord
from discord.ext import commands
import logging

from usescases.community_events.community_events_dao import community_events_dao

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

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
        except Exception:
            return False

    @commands.command(name='event-add-session-link', help='Adiciona ou atualiza o session link de um evento (apenas administradores, via DM)')
    @commands.dm_only()
    async def event_add_session_link(self, ctx, *args):
        logger.debug(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] User "{ctx.author.name}" invoked command with args {args}')

        if not self._is_server_admin(ctx.author.id):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        args_list = list(args)
        force = False
        if args_list and args_list[0] == '-f':
            force = True
            args_list = args_list[1:]

        if len(args_list) != 2:
            await ctx.author.send(
                '❌ Uso incorreto. Sintaxe: `/event-add-session-link [-f] <eventKey> <sessionLink>`\n'
                'O `-f` força a atualização quando o evento já tem um session link.'
            )
            return

        event_key, session_link = args_list

        if not re.fullmatch(r'[A-Za-z0-9_-]+', event_key):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Invalid event key "{event_key}" provided by "{ctx.author.name}"')
            await ctx.author.send(
                f'❌ Event key inválida: `{event_key}`. Use apenas letras, números, "-" e "_".'
            )
            return
        if not self._is_valid_url(session_link):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Invalid URL "{session_link}" provided by "{ctx.author.name}"')
            await ctx.author.send(f'❌ Link inválido: `{session_link}`. Forneça um URL válido com esquema http ou https.')
            return

        event = community_events_dao.get(event_key)
        if event is None:
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Event "{event_key}" not found (requested by "{ctx.author.name}")')
            await ctx.author.send(f'❌ Evento não encontrado: `{event_key}`.')
            return

        from utils.timezones import get_brazil_timezone

        brazil_tz = get_brazil_timezone()
        now = datetime.now(brazil_tz)
        event_start = event.start_datetime
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=brazil_tz)
        else:
            event_start = event_start.astimezone(brazil_tz)
        if event_start < now - timedelta(hours=1):
            logger.warning(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Event "{event_key}" started at "{event_start.isoformat()}" '
                f'which is more than 1h ago (requested by "{ctx.author.name}")'
            )
            await ctx.author.send(
                f'❌ O evento `{event_key}` já ocorreu ou começou há mais de 1 hora. ({event_start.isoformat()}). '
                'Não é possível adicionar o session link.'
            )
            return

        if event.session_link and not force:
            logger.warning(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Event "{event_key}" already has a session link '
                f'and -f was not provided (requested by "{ctx.author.name}")'
            )
            await ctx.author.send(
                f'❌ O evento `{event_key}` já tem um session link: `{event.session_link}`\n'
                'Usa `-f` para forçar a atualização.'
            )
            return

        old_link = event.session_link
        event.session_link = session_link
        community_events_dao.update(event)

        if old_link:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Updated session link for event "{event_key}" '
                f'from "{old_link}" to "{session_link}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Session link do evento `{event_key}` atualizado com sucesso: `{session_link}`')
        else:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Set session link for event "{event_key}" '
                f'to "{session_link}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Session link do evento `{event_key}` definido com sucesso: `{session_link}`')
