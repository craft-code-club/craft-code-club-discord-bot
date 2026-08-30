"""/rules - send the server rules to the invoking user by DM."""

import logging

from discord_api import interactions
from discord_api.rest import DiscordRest
from utils.message_loader import load_message

logger = logging.getLogger(__name__)


async def handle(rest: DiscordRest, interaction: dict) -> None:
    user_name = interactions.user_name(interaction)
    logger.debug('[COMMAND][RULES] User "%s" requested the rules', user_name)

    rules_message = load_message('rules_message.md')
    user_id = interactions.user_id(interaction)

    sent = await rest.send_dm(user_id, content=rules_message)
    if sent is None:
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Não consegui enviar-te uma mensagem direta. Ativa as DMs do servidor e tenta de novo.')
        return

    # The prefix command deleted the invoking message to keep the channel tidy;
    # a slash command leaves no message behind, and this reply is ephemeral.
    await rest.edit_original_response(interaction['token'], content='📬 Enviei-te as regras por mensagem direta!')
    logger.info('[COMMAND][RULES] Sent rules to user "%s"', user_name)
