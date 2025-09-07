from discord.ext import commands
from Messages.message_loader import load_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(RulesCommand(bot))


class RulesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name = 'rules', help = 'Envia as regras para o utilizador')
    async def rules(self, ctx):
        logger.debug(f'[BOT][COMMAND][RULES] User "{ctx.author.name}" requested the rules')

        rules_message = load_message('command-rules.md')
        await ctx.author.send(rules_message)

        try:
            await ctx.message.delete()
        except Exception:
            logger.exception(f'[BOT][COMMAND][RULES] Failed to delete command message')

        logger.info(f'[BOT][COMMAND][RULES] Sent rules to user "{ctx.author.name}" and deleted the command message.')
