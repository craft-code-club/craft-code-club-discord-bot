"""/events and /event - list upcoming events, or show one event in full."""

import logging
from datetime import datetime

from discord_api import interactions
from discord_api.rest import DiscordRest
from usescases.community_events.community_events_dao import get_community_events_dao
from utils.timezones import get_brazil_timezone

from ._helpers import is_valid_event_id
from .permissions import require_admin

logger = logging.getLogger(__name__)


async def handle_list(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'events'):
        return

    logger.debug('[COMMAND][EVENTS] User "%s" requested the list of upcoming events',
                 interactions.user_name(interaction))

    try:
        dao = get_community_events_dao()
    except Exception:  # noqa: BLE001 - surfaced to the admin as a friendly message
        logger.exception('[COMMAND][EVENTS] Failed to initialize community events DAO')
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não foi possível conectar ao armazenamento de eventos. '
                    'Verifica a configuração do Azure Storage.')
        return

    brazil_tz = get_brazil_timezone()
    now = datetime.now(brazil_tz).replace(tzinfo=None)
    upcoming_events = dao.get_upcoming_events(now)
    upcoming_events.sort(key=lambda event: event.start_datetime)

    if not upcoming_events:
        await rest.edit_original_response(interaction['token'],
                                          content='📭 Não há eventos futuros cadastrados.')
        return

    lines = ['📅 **Próximos eventos:**', '']
    for event in upcoming_events:
        lines.append(f'`{event.id}` — {event.title} — {event.start_datetime.strftime("%Y/%m/%d - %H:%M")}')

    await rest.respond_chunked(interaction['token'], '\n'.join(lines))
    logger.info('[COMMAND][EVENTS] Sent %s upcoming event(s) to admin "%s"',
                len(upcoming_events), interactions.user_name(interaction))


async def handle_details(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'event'):
        return

    options = interactions.options(interaction)
    event_key = (options.get('event_id') or '').strip()

    logger.debug('[COMMAND][EVENT] User "%s" requested event "%s"',
                 interactions.user_name(interaction), event_key)

    if not is_valid_event_id(event_key):
        logger.warning('[COMMAND][EVENT] Invalid event key "%s" provided by "%s"',
                       event_key, interactions.user_name(interaction))
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ Event id inválido: `{event_key}`. Use apenas letras, números, "-" e "_".')
        return

    try:
        dao = get_community_events_dao()
    except Exception:  # noqa: BLE001
        logger.exception('[COMMAND][EVENT] Failed to initialize community events DAO')
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não foi possível conectar ao armazenamento de eventos. '
                    'Verifica a configuração do Azure Storage.')
        return

    event = dao.get(event_key)
    if event is None:
        logger.warning('[COMMAND][EVENT] Event "%s" not found (requested by "%s")',
                       event_key, interactions.user_name(interaction))
        await rest.edit_original_response(interaction['token'],
                                          content=f'❌ Evento não encontrado: `{event_key}`.')
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
        f'**session_link:** {event.session_link}',
        f'**registration_link:** {event.registration_link}',
        f'**recording_link:** {event.recording_link}',
        f'**post_link:** {event.post_link}',
        '**speakers:** (não persistido no storage)',
        '**tags:** (não persistido no storage)',
        f'**a_weekly_notify:** {event.a_weekly_notify}',
        f'**three_days_notify:** {event.three_days_notify}',
        f'**a_day_notify:** {event.a_day_notify}',
        f'**a_hour_notify:** {event.a_hour_notify}',
    ]

    await rest.respond_chunked(interaction['token'], '\n'.join(lines))
    logger.info('[COMMAND][EVENT-DETAILS] Sent details of event "%s" to admin "%s"',
                event_key, interactions.user_name(interaction))
