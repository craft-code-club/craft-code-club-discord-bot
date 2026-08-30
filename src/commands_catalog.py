"""The bot's slash commands, in one place.

Single source of truth for three things that used to drift apart:
  * what `scripts/register_commands.py` PUTs to Discord;
  * what `/help` renders;
  * which handler the router dispatches to.

Option types (Discord: Application Command Object):
  3 STRING, 4 INTEGER, 5 BOOLEAN, 6 USER, 7 CHANNEL, 8 ROLE.
"""

STRING = 3
BOOLEAN = 5
USER = 6
ROLE = 8

ADMINISTRATOR_PERMISSION = '8'

# Usable both inside the server and in a DM with the bot, matching the reach of
# the old prefix commands (which were mostly DM-only).
CONTEXTS = [0, 1]          # GUILD, BOT_DM
INTEGRATION_TYPES = [0]    # GUILD_INSTALL

COMMANDS = [
    {
        'name': 'rules',
        'description': 'Envia as regras para o utilizador',
        'admin': False,
    },
    {
        'name': 'help',
        'description': 'Mostra a lista de comandos disponíveis',
        'admin': False,
    },
    {
        'name': 'version',
        'description': 'Mostra a versão do bot (apenas administradores)',
        'admin': True,
    },
    {
        'name': 'info',
        'description': 'Mostra a versão e a última execução das tarefas (apenas administradores)',
        'admin': True,
    },
    {
        'name': 'events',
        'description': 'Lista os próximos eventos (apenas administradores)',
        'admin': True,
    },
    {
        'name': 'event',
        'description': 'Mostra todos os detalhes de um evento (apenas administradores)',
        'admin': True,
        'options': [
            {'name': 'event_id', 'description': 'Id do evento', 'type': STRING, 'required': True},
        ],
    },
    {
        'name': 'event-add-session-link',
        'description': 'Adiciona ou atualiza o session link de um evento (apenas administradores)',
        'admin': True,
        'options': [
            {'name': 'event_id', 'description': 'Id do evento', 'type': STRING, 'required': True},
            {'name': 'session_link', 'description': 'URL da sessão', 'type': STRING, 'required': True},
            {'name': 'force', 'description': 'Substituir um session link existente',
             'type': BOOLEAN, 'required': False},
        ],
    },
    {
        'name': 'event-add-recording-link',
        'description': 'Adiciona ou atualiza o recording link de um evento (apenas administradores)',
        'admin': True,
        'options': [
            {'name': 'event_id', 'description': 'Id do evento', 'type': STRING, 'required': True},
            {'name': 'recording_link', 'description': 'URL da gravação', 'type': STRING, 'required': True},
            {'name': 'force', 'description': 'Substituir um recording link existente',
             'type': BOOLEAN, 'required': False},
        ],
    },
    {
        'name': 'add-role',
        'description': 'Adiciona um role a um utilizador ou a todos (apenas administradores)',
        'admin': True,
        'notes': 'Ativa `everyone` para aplicar o role a todos os membros do servidor.',
        'options': [
            {'name': 'role', 'description': 'Role a adicionar', 'type': ROLE, 'required': True},
            {'name': 'user', 'description': 'Utilizador que recebe o role', 'type': USER, 'required': False},
            {'name': 'everyone', 'description': 'Aplicar a todos os membros do servidor',
             'type': BOOLEAN, 'required': False},
        ],
    },
    {
        'name': 'server-status',
        'description': 'Mostra estatísticas do servidor (apenas administradores)',
        'admin': True,
    },
]


def to_discord_payload() -> list[dict]:
    """The exact array Discord expects on PUT .../commands."""
    payload = []
    for command in COMMANDS:
        entry: dict = {
            'name': command['name'],
            'description': command['description'],
            'type': 1,  # CHAT_INPUT
            'contexts': CONTEXTS,
            'integration_types': INTEGRATION_TYPES,
        }
        if command.get('options'):
            entry['options'] = [
                {k: v for k, v in option.items()} for option in command['options']
            ]
        if command.get('admin'):
            # Hides the command from non-administrators inside the server.
            # It has no effect in DMs, which is why every admin handler still
            # verifies the caller.
            entry['default_member_permissions'] = ADMINISTRATOR_PERMISSION
        payload.append(entry)
    return payload


def usage(command: dict) -> str:
    """A '/name <required> [optional]' usage string for the help embed."""
    parts = [f'/{command["name"]}']
    for option in command.get('options', []):
        parts.append(f'<{option["name"]}>' if option.get('required') else f'[{option["name"]}]')
    return ' '.join(parts)
