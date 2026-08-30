"""/version - report the deployed bot version."""

import logging

from discord_api import interactions
from discord_api.rest import DiscordRest
from utils import config

from .permissions import require_admin

logger = logging.getLogger(__name__)


async def handle(rest: DiscordRest, interaction: dict) -> None:
    if not await require_admin(rest, interaction, 'version'):
        return

    version = config.bot_version()
    await rest.edit_original_response(interaction['token'], content=f'Versão do bot: {version}')
    logger.info('[COMMAND][VERSION] Sent bot version "%s" to admin "%s"',
                version, interactions.user_name(interaction))
