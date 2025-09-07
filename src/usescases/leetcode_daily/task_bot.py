import os
from datetime import time
from .leetcode_server import fetch_daily_problem
from .leetcode_problem_formatter import format_problem_message
from discord.ext import tasks, commands
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(LeetcodeDailyTaskBot(bot))


class LeetcodeDailyTaskBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leetcode_channel_id = int(os.environ.get('LEETCODE_CHANNEL_ID', '0'))

        if not self.leetcode_channel_id:
            logger.warning('[BOT][TASK][LEETCODE] LEETCODE_CHANNEL_ID is not set. Daily task will not run.')
            return

        self.daily_leetcode_task.start()

    def cog_unload(self):
        self.daily_leetcode_task.cancel()

    @tasks.loop(time=time(15, 0)) # UTC
    async def daily_leetcode_task(self):
        logger.debug('[BOT][TASK][LEETCODE DAILY] Fetching LeetCode problem of the day...')

        try:
            channel = self.bot.get_channel(self.leetcode_channel_id)
            problem_data = await fetch_daily_problem()
            embed = format_problem_message(problem_data)

            await channel.send(embed=embed)
            logger.info(f'[BOT][TASK][LEETCODE DAILY] Sent to channel "{channel.name}"')

        except Exception:
            logger.exception('[BOT][TASK][LEETCODE DAILY] Error in daily task:')

    @daily_leetcode_task.before_loop
    async def before_daily_task(self):
        await self.bot.wait_until_ready()
        logger.info('[BOT][TASK][LEETCODE DAILY] Daily LeetCode task is ready!')
