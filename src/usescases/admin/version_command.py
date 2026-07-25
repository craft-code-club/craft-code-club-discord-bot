import os
from discord.ext import commands
import logging

from ._helpers import is_server_admin

logger = logging.getLogger(__name__)


class VersionCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='version', help='Mostra a versão do bot (apenas administradores, via DM)')
    @commands.dm_only()
    async def version(self, ctx):
        logger.debug(f'[BOT][COMMAND][VERSION] User "{ctx.author.name}" requested the bot version')

        if not is_server_admin(self.bot, ctx.author.id):
            logger.warning(f'[BOT][COMMAND][VERSION] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        version = os.environ.get('BOT_VERSION', 'dev')
        await ctx.author.send(f'Versão do bot: {version}')
        logger.info(f'[BOT][COMMAND][VERSION] Sent bot version "{version}" to admin "{ctx.author.name}"')
