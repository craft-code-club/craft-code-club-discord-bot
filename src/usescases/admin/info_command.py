import os
from datetime import datetime, timezone
from discord.ext import commands
import logging

from ._helpers import is_server_admin, format_uptime

logger = logging.getLogger(__name__)


class InfoCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started_at = datetime.now(timezone.utc)

    @commands.command(name='info', help='Mostra a versão e o tempo online do bot (apenas administradores, via DM)')
    @commands.dm_only()
    async def info(self, ctx):
        logger.debug(f'[BOT][COMMAND][INFO] User "{ctx.author.name}" requested the bot info')

        if not is_server_admin(self.bot, ctx.author.id):
            logger.warning(f'[BOT][COMMAND][INFO] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        version = os.environ.get('BOT_VERSION', 'dev')
        uptime = format_uptime(self.started_at)
        await ctx.author.send(f'Versão do bot: {version}\nTempo online: {uptime}')
        logger.info(f'[BOT][COMMAND][INFO] Sent bot info (version "{version}", uptime "{uptime}") to admin "{ctx.author.name}"')
