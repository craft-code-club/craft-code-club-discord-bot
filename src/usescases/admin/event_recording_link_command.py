import re
from discord.ext import commands
import logging

from ._helpers import is_server_admin, is_valid_url

logger = logging.getLogger(__name__)


class EventRecordingLinkCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='event-add-recording-link', help='Adiciona ou atualiza o recording link de um evento (apenas administradores, via DM)', extras={'admin': True, 'scope': 'DM', 'usage': '[-f] <eventKey> <recordingLink>', 'notes': 'Usa `-f` para forçar a atualização quando o evento já tem um recording link.'})
    @commands.dm_only()
    async def event_add_recording_link(self, ctx, *args):
        logger.debug(f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] User "{ctx.author.name}" invoked command with args {args}')

        if not is_server_admin(self.bot, ctx.author.id):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        args_list = list(args)
        force = False
        if args_list and args_list[0] == '-f':
            force = True
            args_list = args_list[1:]

        if len(args_list) != 2:
            await ctx.author.send(
                '❌ Uso incorreto. Sintaxe: `/event-add-recording-link [-f] <eventKey> <recordingLink>`\n'
                'O `-f` força a atualização quando o evento já tem um recording link.'
            )
            return

        event_key, recording_link = args_list
        recording_link = recording_link.strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]+', event_key):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Invalid event key "{event_key}" provided by "{ctx.author.name}"')
            await ctx.author.send(
                f'❌ Event key inválida: `{event_key}`. Use apenas letras, números, "-" e "_".'
            )
            return
        if not is_valid_url(recording_link):
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Invalid URL "{recording_link}" provided by "{ctx.author.name}"')
            await ctx.author.send(f'❌ Link inválido: `{recording_link}`. Forneça um URL válido com esquema http ou https.')
            return

        try:
            from usescases.community_events.community_events_dao import community_events_dao
        except Exception:
            logger.exception('[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Failed to initialize community events DAO')
            await ctx.author.send('❌ Não foi possível conectar ao armazenamento de eventos. Verifica a configuração do Azure Storage.')
            return

        event = community_events_dao.get(event_key)
        if event is None:
            logger.warning(f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Event "{event_key}" not found (requested by "{ctx.author.name}")')
            await ctx.author.send(f'❌ Evento não encontrado: `{event_key}`.')
            return

        if event.recording_link and not force:
            logger.warning(
                f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Event "{event_key}" already has a recording link '
                f'and -f was not provided (requested by "{ctx.author.name}")'
            )
            await ctx.author.send(
                f'❌ O evento `{event_key}` já tem um recording link: `{event.recording_link}`\n'
                'Use `-f` para forçar a atualização.'
            )
            return

        old_link = event.recording_link
        event.recording_link = recording_link
        community_events_dao.update(event)

        if old_link:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Updated recording link for event "{event_key}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Recording link do evento `{event_key}` atualizado com sucesso: `{recording_link}`')
        else:
            logger.info(
                f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Set recording link for event "{event_key}" '
                f'to "{recording_link}" (by "{ctx.author.name}")'
            )
            await ctx.author.send(f'✅ Recording link do evento `{event_key}` definido com sucesso: `{recording_link}`')
