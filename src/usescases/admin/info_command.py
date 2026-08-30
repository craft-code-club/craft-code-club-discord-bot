"""/info - version plus when the scheduled jobs last ran.

The container bot reported process uptime here. A function app has no
long-lived process, so uptime is meaningless; the timestamps of the last
successful timer runs are the useful equivalent and answer the same question
("is the bot alive?").
"""

import logging

from discord_api import interactions
from discord_api.rest import DiscordRest
from utils import state_dao
from utils import config

from .permissions import require_admin

logger = logging.getLogger(__name__)


async def handle(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'info'):
        return

    version = config.bot_version()
    state = state_dao.get_state_dao()
    last_sync = state.get(state_dao.LAST_SYNC_KEY) or 'nunca'
    last_notify = state.get(state_dao.LAST_NOTIFY_KEY) or 'nunca'

    lines = [
        f'Versão do bot: {version}',
        f'Última sincronização de eventos: {last_sync}',
        f'Última verificação de lembretes: {last_notify}',
    ]
    await rest.edit_original_response(interaction['token'], content='\n'.join(lines))
    logger.info('[COMMAND][INFO] Sent bot info (version "%s") to admin "%s"',
                version, interactions.user_name(interaction))
