import re
from datetime import datetime
from discord.ext import commands
import logging

from ._helpers import is_server_admin, send_chunked
from utils.timezones import get_brazil_timezone

logger = logging.getLogger(__name__)


class EventsCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='events', help='Lista os próximos eventos (apenas administradores, via DM)', extras={'admin': True, 'scope': 'DM'})
    @commands.dm_only()
    async def events(self, ctx):
        logger.debug(f'[BOT][COMMAND][EVENTS] User "{ctx.author.name}" requested the list of upcoming events')

        if not is_server_admin(self.bot, ctx.author.id):
            logger.warning(f'[BOT][COMMAND][EVENTS] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        try:
            from usescases.community_events.community_events_dao import community_events_dao
        except Exception:
            logger.exception('[BOT][COMMAND][EVENTS] Failed to initialize community events DAO')
            await ctx.author.send('❌ Não foi possível conectar ao armazenamento de eventos. Verifica a configuração do Azure Storage.')
            return

        brazil_tz = get_brazil_timezone()
        now = datetime.now(brazil_tz)
        upcoming_events = community_events_dao.get_upcoming_events(now)
        upcoming_events.sort(key=lambda event: (event.start_datetime.replace(tzinfo=brazil_tz) if event.start_datetime.tzinfo is None else event.start_datetime.astimezone(brazil_tz)))

        if not upcoming_events:
            await ctx.author.send('📭 Não há eventos futuros cadastrados.')
            return

        lines = ['📅 **Próximos eventos:**', '']
        for event in upcoming_events:
            lines.append(f'`{event.id}` — {event.title} — {event.brazil_datetime()}')

        await send_chunked(ctx.author, '\n'.join(lines))
        logger.info(f'[BOT][COMMAND][EVENTS] Sent {len(upcoming_events)} upcoming event(s) to admin "{ctx.author.name}"')


class EventDetailsCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='event', help='Mostra todos os detalhes de um evento (apenas administradores, via DM)', extras={'admin': True, 'scope': 'DM', 'usage': '<eventId>'})
    @commands.dm_only()
    async def event_details(self, ctx, *args):
        logger.debug(f'[BOT][COMMAND][EVENT] User "{ctx.author.name}" invoked command with args {args}')

        if not is_server_admin(self.bot, ctx.author.id):
            logger.warning(f'[BOT][COMMAND][EVENT] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        if len(args) != 1:
            await ctx.author.send('❌ Uso incorreto. Sintaxe: `/event <eventId>`')
            return

        event_key = args[0]

        if not re.fullmatch(r'[A-Za-z0-9_-]+', event_key):
            logger.warning(f'[BOT][COMMAND][EVENT] Invalid event key "{event_key}" provided by "{ctx.author.name}"')
            await ctx.author.send(f'❌ Event id inválido: `{event_key}`. Use apenas letras, números, "-" e "_".')
            return

        try:
            from usescases.community_events.community_events_dao import community_events_dao
        except Exception:
            logger.exception('[BOT][COMMAND][EVENT] Failed to initialize community events DAO')
            await ctx.author.send('❌ Não foi possível conectar ao armazenamento de eventos. Verifica a configuração do Azure Storage.')
            return

        event = community_events_dao.get(event_key)
        if event is None:
            logger.warning(f'[BOT][COMMAND][EVENT] Event "{event_key}" not found (requested by "{ctx.author.name}")')
            await ctx.author.send(f'❌ Evento não encontrado: `{event_key}`.')
            return

        lines = [
            f'📋 **Detalhes do evento `{event.id}`:**',
            '',
            f'**id:** {event.id}',
            f'**title:** {event.title}',
            f'**github_url:** {event.github_url}',
            f'**description:** {event.description}',
            f'**start_datetime:** {event.start_datetime.isoformat()}',
            f'**end_datetime:** {event.end_datetime.isoformat()}',
            f'**discord_event_id:** {event.discord_event_id}',
            f'**location:** {event.location}',
            f'**type:** {event.type}',
            f'**banner:** {event.banner}',
            f'**is_live:** {event.is_live}',
            f'**open_session:** {event.open_session}',
            f'**youtube_title:** {event.youtube_title}',
            f'**session_link:** {event.session_link}',
            f'**registration_link:** {event.registration_link}',
            f'**recording_link:** {event.recording_link}',
            f'**post_link:** {event.post_link}',
            f'**speakers:** {event.speakers}',
            f'**tags:** {event.tags}',
            f'**a_weekly_notify:** {event.a_weekly_notify}',
            f'**three_days_notify:** {event.three_days_notify}',
            f'**a_day_notify:** {event.a_day_notify}',
            f'**a_hour_notify:** {event.a_hour_notify}',
        ]

        await send_chunked(ctx.author, '\n'.join(lines))
        logger.info(f'[BOT][COMMAND][EVENT-DETAILS] Sent details of event "{event_key}" to admin "{ctx.author.name}"')
