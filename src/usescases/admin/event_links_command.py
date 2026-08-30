"""/event-add-session-link and /event-add-recording-link.

The positional `-f` flag and hand-rolled argument parsing are gone: slash
command options give typed, validated arguments, so `force` is a real boolean.
"""

import logging
from datetime import datetime, timedelta

from discord_api import interactions
from discord_api.rest import DiscordRest
from usescases.community_events.community_events_dao import get_community_events_dao
from utils.timezones import get_brazil_timezone

from ._helpers import is_valid_event_id, is_valid_url
from .permissions import require_admin

logger = logging.getLogger(__name__)


async def _load_event(rest: DiscordRest, interaction: dict, command: str, link_option: str):
    """Shared validation for both link commands.

    Returns (dao, event, event_id, link, force) or None when the command was
    already answered with a validation error.
    """
    log_prefix = f'[COMMAND][{command.upper()}]'
    options = interactions.options(interaction)
    event_id = (options.get('event_id') or '').strip()
    link = (options.get(link_option) or '').strip()
    force = bool(options.get('force', False))
    user_name = interactions.user_name(interaction)

    logger.debug('%s User "%s" invoked the command for event "%s"', log_prefix, user_name, event_id)

    if not is_valid_event_id(event_id):
        logger.warning('%s Invalid event key "%s" provided by "%s"', log_prefix, event_id, user_name)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ Event key inválida: `{event_id}`. Use apenas letras, números, "-" e "_".')
        return None

    if not is_valid_url(link):
        logger.warning('%s Invalid URL "%s" provided by "%s"', log_prefix, link, user_name)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ Link inválido: `{link}`. Forneça um URL válido com esquema http ou https.')
        return None

    try:
        dao = get_community_events_dao()
    except Exception:  # noqa: BLE001
        logger.exception('%s Failed to initialize community events DAO', log_prefix)
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não foi possível conectar ao armazenamento de eventos. '
                    'Verifica a configuração do Azure Storage.')
        return None

    event = dao.get(event_id)
    if event is None:
        logger.warning('%s Event "%s" not found (requested by "%s")', log_prefix, event_id, user_name)
        await rest.edit_original_response(interaction['token'],
                                          content=f'❌ Evento não encontrado: `{event_id}`.')
        return None

    return dao, event, event_id, link, force


async def handle_session_link(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'event-add-session-link'):
        return

    loaded = await _load_event(rest, interaction, 'event-add-session-link', 'session_link')
    if loaded is None:
        return
    dao, event, event_id, session_link, force = loaded
    user_name = interactions.user_name(interaction)

    brazil_tz = get_brazil_timezone()
    now = datetime.now(brazil_tz)
    event_start = event.start_datetime
    if event_start.tzinfo is None:
        event_start = event_start.replace(tzinfo=brazil_tz)
    else:
        event_start = event_start.astimezone(brazil_tz)

    if event_start < now - timedelta(hours=1):
        logger.warning('[COMMAND][EVENT-ADD-SESSION-LINK] Event "%s" started at "%s" which is more '
                       'than 1h ago (requested by "%s")', event_id, event_start.isoformat(), user_name)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ O evento `{event_id}` já ocorreu ou começou há mais de 1 hora. '
                    f'({event_start.isoformat()}). Não é possível adicionar o session link.')
        return

    if event.session_link and not force:
        logger.warning('[COMMAND][EVENT-ADD-SESSION-LINK] Event "%s" already has a session link '
                       'and force was not set (requested by "%s")', event_id, user_name)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ O evento `{event_id}` já tem um session link: `{event.session_link}`\n'
                    'Usa a opção `force` para forçar a atualização.')
        return

    old_link = event.session_link
    event.session_link = session_link
    try:
        dao.merge(event, {'session_link': session_link})
    except Exception:  # noqa: BLE001
        logger.exception('[COMMAND][EVENT-ADD-SESSION-LINK] Failed to update session link for event "%s"', event_id)
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não foi possível atualizar o evento no armazenamento. '
                    'Verifica a configuração do Azure Storage.')
        return

    verb = 'atualizado' if old_link else 'definido'
    logger.info('[COMMAND][EVENT-ADD-SESSION-LINK] %s session link for event "%s" (by "%s")',
                'Updated' if old_link else 'Set', event_id, user_name)
    await rest.edit_original_response(
        interaction['token'],
        content=f'✅ Session link do evento `{event_id}` {verb} com sucesso: `{session_link}`')


async def handle_recording_link(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'event-add-recording-link'):
        return

    loaded = await _load_event(rest, interaction, 'event-add-recording-link', 'recording_link')
    if loaded is None:
        return
    dao, event, event_id, recording_link, force = loaded
    user_name = interactions.user_name(interaction)

    if event.has_recording_link() and not force:
        logger.warning('[COMMAND][EVENT-ADD-RECORDING-LINK] Event "%s" already has a recording link '
                       'and force was not set (requested by "%s")', event_id, user_name)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ O evento `{event_id}` já tem um recording link: `{event.recording_link}`\n'
                    'Usa a opção `force` para forçar a atualização.')
        return

    old_link = event.recording_link
    event.recording_link = recording_link
    try:
        dao.merge(event, {'recording_link': recording_link})
    except Exception:  # noqa: BLE001
        logger.exception('[COMMAND][EVENT-ADD-RECORDING-LINK] Failed to update recording link for event "%s"', event_id)
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não foi possível atualizar o evento no armazenamento. '
                    'Verifica a configuração do Azure Storage.')
        return

    verb = 'atualizado' if (old_link and old_link.strip()) else 'definido'
    logger.info('[COMMAND][EVENT-ADD-RECORDING-LINK] %s recording link for event "%s" (by "%s")',
                'Updated' if old_link else 'Set', event_id, user_name)
    await rest.edit_original_response(
        interaction['token'],
        content=f'✅ Recording link do evento `{event_id}` {verb} com sucesso: `{recording_link}`')
