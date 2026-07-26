import logging
from discord.ext import commands

from ._helpers import parse_event_link_args

logger = logging.getLogger(__name__)


class EventRecordingLinkCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='event-add-recording-link', help='Adiciona ou atualiza o recording link de um evento (apenas administradores, via DM)', extras={'admin': True, 'scope': 'DM', 'usage': '[-f] <eventId> <recordingLink>', 'notes': 'Usa `-f` para forçar a atualização quando o evento já tem um recording link.'})
    @commands.dm_only()
    async def event_add_recording_link(self, ctx, *args):
        result = await parse_event_link_args(ctx, args, self.bot, 'event-add-recording-link', 'recordingLink')
        if result is None:
            return

        force, event_key, recording_link, community_events_dao, event = result

        if event.has_recording_link() and not force:
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
        try:
            community_events_dao.update(event)
        except Exception:
            logger.exception(
                f'[BOT][COMMAND][EVENT-ADD-RECORDING-LINK] Failed to update recording link for event "{event_key}"'
            )
            await ctx.author.send('❌ Não foi possível atualizar o evento no armazenamento. Verifica a configuração do Azure Storage.')
            return

        if old_link and old_link.strip():
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
