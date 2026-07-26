import logging
from datetime import datetime, timedelta
from discord.ext import commands

from ._helpers import parse_event_link_args

logger = logging.getLogger(__name__)


class EventSessionLinkCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='event-add-session-link', help='Adiciona ou atualiza o session link de um evento (apenas administradores, via DM)', extras={'admin': True, 'scope': 'DM', 'usage': '[-f] <eventId> <sessionLink>', 'notes': 'Usa `-f` para forçar a atualização quando o evento já tem um session link.'})
    @commands.dm_only()
    async def event_add_session_link(self, ctx, *args):
        result = await parse_event_link_args(ctx, args, self.bot, 'event-add-session-link', 'sessionLink')
        if result is None:
            return

        force, event_key, session_link, community_events_dao, event = result

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
