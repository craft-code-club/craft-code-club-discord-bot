"""/help - list the available commands.

Built from the shared command catalogue rather than from discord.py's command
registry, so it stays correct without a bot object. Administration commands
are only listed for administrators, as before.
"""

import logging

from commands_catalog import COMMANDS, usage
from discord_api import interactions
from discord_api.rest import DiscordRest
from usescases.admin.permissions import is_admin

logger = logging.getLogger(__name__)

EMBED_COLOR = 0x5865F2  # Discord blurple
FIELD_VALUE_LIMIT = 1024


async def handle(rest: DiscordRest, interaction: dict) -> None:
    user_name = interactions.user_name(interaction)
    logger.debug('[COMMAND][HELP] User "%s" requested the help', user_name)

    admin = await is_admin(rest, interaction)

    fields: list[dict] = []
    _add_section(fields, 'Comandos', [c for c in COMMANDS if not c.get('admin')])
    if admin:
        _add_section(fields, 'Comandos de administração', [c for c in COMMANDS if c.get('admin')])

    embed = {
        'title': 'Comandos disponíveis',
        'description': 'Aqui estão os comandos que podes utilizar.',
        'color': EMBED_COLOR,
        'fields': fields,
    }

    await rest.edit_original_response(interaction['token'], embed=embed)
    logger.info('[COMMAND][HELP] Sent help to user "%s" (admin=%s)', user_name, admin)


def _add_section(fields: list[dict], title: str, commands: list[dict]) -> None:
    if not commands:
        return

    entries = []
    for command in sorted(commands, key=lambda c: c['name']):
        entry = f'`{usage(command)}`\n{command["description"]}'
        if command.get('notes'):
            entry += f'\n_{command["notes"]}_'
        entries.append(entry)

    # Embed field values are capped at 1024 characters; chunk if needed.
    chunk, first = '', True
    for entry in entries:
        candidate = entry if not chunk else f'{chunk}\n\n{entry}'
        if len(candidate) > FIELD_VALUE_LIMIT:
            fields.append({'name': title if first else '​', 'value': chunk, 'inline': False})
            chunk, first = entry, False
        else:
            chunk = candidate

    if chunk:
        fields.append({'name': title if first else '​', 'value': chunk, 'inline': False})
