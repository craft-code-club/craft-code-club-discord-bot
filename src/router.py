"""Dispatch a verified interaction to its handler.

Runs inside the queue-triggered worker, never on the HTTP hot path, so it is
free to import the heavier modules (aiohttp, azure-data-tables).

Every handler receives an already-acknowledged interaction: the HTTP trigger
answered Discord with a deferred response, so the handler's job is to finish
the work and edit that response within the token's 15-minute window.
"""

import logging

from discord_api import interactions
from discord_api.rest import DiscordRest
from usescases.admin import (add_role_command, event_links_command, events_command,
                             info_command, server_status_command, version_command)
from usescases.help import help_command
from usescases.rules import rules_command
from utils.reporting import report

logger = logging.getLogger(__name__)

HANDLERS = {
    'rules': rules_command.handle,
    'help': help_command.handle,
    'version': version_command.handle,
    'info': info_command.handle,
    'events': events_command.handle_list,
    'event': events_command.handle_details,
    'event-add-session-link': event_links_command.handle_session_link,
    'event-add-recording-link': event_links_command.handle_recording_link,
    'add-role': add_role_command.handle,
    'server-status': server_status_command.handle,
}


async def dispatch(interaction: dict) -> None:
    name = interactions.command_name(interaction)
    handler = HANDLERS.get(name)

    async with DiscordRest() as rest:
        if handler is None:
            logger.warning('[ROUTER] Unknown command "%s"', name)
            await rest.edit_original_response(
                interaction['token'],
                content=f'❌ Comando desconhecido: `{name}`. Corre o registo de comandos.')
            return

        try:
            await handler(rest, interaction)
        except Exception as error:  # noqa: BLE001 - the user is waiting on a deferred response
            logger.exception('[ROUTER] Command "%s" failed', name)
            await report(rest, f'[COMMAND][{name.upper()}] failed: {error}')
            try:
                await rest.edit_original_response(
                    interaction['token'],
                    content='❌ Ocorreu um erro a executar o comando. Os administradores foram notificados.')
            except Exception:  # noqa: BLE001 - the token may already be gone
                logger.exception('[ROUTER] Could not report the failure of "%s" to the user', name)
            raise
