from discord.ext import commands
from .leetcode_server import fetch_daily_problem
from .leetcode_problem_formatter import format_problem_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(LeetcodeDailyCommandBot(bot))


class LeetcodeDailyCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='leetcode-daily', help='Obtém o problema diário do LeetCode')
    async def manual_leetcode(self, ctx):
        logger.debug(f'[BOT][COMMAND][LEETCODE DAILY] User "{ctx.author.name}" requested the LeetCode problem of the day')

        problem_data = await fetch_daily_problem()
        embed = format_problem_message(problem_data)
        await ctx.author.send(embed=embed)
        logger.info(f'[BOT][COMMAND][LEETCODE DAILY] Sent LeetCode problem to user "{ctx.author.name}"')

        try:
            await ctx.message.delete()
            logger.debug(f'[BOT][COMMAND][LEETCODE DAILY] Message deleted successfully')
        except Exception:
            logger.exception(f'[BOT][COMMAND][LEETCODE DAILY] Failed to delete command message')
