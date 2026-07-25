import re
from datetime import datetime, timedelta
from discord.ext import commands
import logging

from ._helpers import is_server_admin, is_valid_url

logger = logging.getLogger(__name__)


class EventSessionLinkCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='event-add-session-link', help='Adiciona ou atualiza o session link de um evento (apenas administradores, via DM)')
    @commands.dm_only()
    async def event_add_session_link(self, ctx, *args):
        logger.debug(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] User "{ctx.author.name}" invoked command with args {args}')

        if not is_server_admin(self.bot, ctx.author.id):
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
        if not is_valid_url(session_link):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Invalid URL "{session_link}" provided by "{ctx.author.name}"')
            await ctx.author.send(f'❌ Link inválido: `{session_link}`. Forneça um URL válido com esquema http ou https.')
            return

        try:
            from usescases.community_events.community_events_dao import community_events_dao
        except Exception:
            logger.exception('[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Failed to initialize community events DAO')
            await ctx.author.send('❌ Não foi possível conectar ao armazenamento de eventos. Verifica a configuração do Azure Storage.')
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
                'Use `-f` para forçar a atualização.'
            )
            return

        old_link = event.session_link
        event.session_link = session_link
        community_events_dao.update(event)

        if old_link:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Updated session link for event "{event_key}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Session link do evento `{event_key}` atualizado com sucesso: `{session_link}`')
        else:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-SESSION-LINK] Set session link for event "{event_key}" '
                f'to "{session_link}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Session link do evento `{event_key}` definido com sucesso: `{session_link}`')
