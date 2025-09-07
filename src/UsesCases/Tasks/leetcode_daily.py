import os
import aiohttp
from datetime import datetime, time
from discord.ext import tasks, commands
import discord
import logging

logger = logging.getLogger(__name__)


class LeetCodeDailyTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leetcode_channel_id = int(os.environ.get('LEETCODE_CHANNEL_ID', '0'))
        self.daily_leetcode_task.start()

    def cog_unload(self):
        self.daily_leetcode_task.cancel()

    @tasks.loop(time=time(3, 0))  # Run at 3:00 AM
    async def daily_leetcode_task(self):
        """Send the LeetCode problem of the day at 3 AM"""
        try:
            logger.info('[BOT][TASK][LEETCODE] Fetching LeetCode problem of the day...')

            problem_data = await self.fetch_daily_problem()
            if problem_data:
                message = self.format_problem_message(problem_data)
                await self.send_to_channel(message)
                logger.info('[BOT][TASK][LEETCODE] Successfully sent daily LeetCode problem!')
            else:
                logger.error('[BOT][TASK][LEETCODE] Failed to fetch daily problem')

        except Exception as e:
            logger.exception(f'[BOT][TASK][LEETCODE] Error in daily task: {type(e).__name__}: {e}')

    @daily_leetcode_task.before_loop
    async def before_daily_task(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info('[BOT][TASK][LEETCODE] Daily LeetCode task is ready!')

    async def fetch_daily_problem(self):
        """Fetch the daily coding challenge from LeetCode"""
        try:
            # LeetCode GraphQL endpoint for daily challenge
            url = "https://leetcode.com/graphql"

            query = """
            query questionOfToday {
                activeDailyCodingChallengeQuestion {
                    date
                    userStatus
                    link
                    question {
                        acRate
                        difficulty
                        freqBar
                        frontendQuestionId: questionFrontendId
                        isFavor
                        paidOnly: isPaidOnly
                        status
                        title
                        titleSlug
                        hasVideoSolution
                        hasSolution
                        topicTags {
                            name
                            id
                            slug
                        }
                        content
                        stats
                    }
                }
            }
            """

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={'query': query},
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {}).get('activeDailyCodingChallengeQuestion')
                    else:
                        logger.error(f'[BOT][TASK][LEETCODE] HTTP Error: {response.status}')
                        return None

        except Exception as e:
            logger.exception(f'[BOT][TASK][LEETCODE] Error fetching problem: {type(e).__name__}: {e}')
            return None

    def format_problem_message(self, problem_data):
        """Format the problem data into a Discord message"""
        question = problem_data.get('question', {})

        # Extract basic info
        title = question.get('title', 'Unknown Problem')
        problem_id = question.get('frontendQuestionId', '?')
        difficulty = question.get('difficulty', 'Unknown')
        acceptance_rate = question.get('acRate', 0)
        link = f"https://leetcode.com{problem_data.get('link', '')}"

        # Get topic tags
        topics = question.get('topicTags', [])
        topic_names = [tag.get('name', '') for tag in topics[:5]]  # Limit to 5 topics
        topics_str = ', '.join(topic_names) if topic_names else 'N/A'

        # Determine difficulty emoji and color
        difficulty_emoji = {
            'Easy': '🟢',
            'Medium': '🟡',
            'Hard': '🔴'
        }.get(difficulty, '⚪')

        # Create embed
        embed = discord.Embed(
            title=f"🚀 LeetCode Problem of the Day",
            description=f"**{problem_id}. {title}**",
            url=link,
            color=self.get_difficulty_color(difficulty),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Difficulty",
            value=f"{difficulty_emoji} {difficulty}",
            inline=True
        )

        embed.add_field(
            name="Acceptance Rate",
            value=f"{acceptance_rate:.1f}%",
            inline=True
        )

        embed.add_field(
            name="Topics",
            value=topics_str,
            inline=False
        )

        embed.add_field(
            name="🔗 Solve Now",
            value=f"[Click here to solve the problem]({link})",
            inline=False
        )

        embed.set_footer(text="Happy coding! 💻")

        return embed

    def get_difficulty_color(self, difficulty):
        """Get Discord color based on difficulty"""
        colors = {
            'Easy': 0x00ff00,    # Green
            'Medium': 0xffa500,  # Orange
            'Hard': 0xff0000     # Red
        }
        return colors.get(difficulty, 0x808080)  # Gray default

    async def send_to_channel(self, embed):
        """Send the message to the configured channel"""
        if self.leetcode_channel_id == 0:
            logger.error('[BOT][TASK][LEETCODE] LEETCODE_CHANNEL_ID not configured')
            return

        try:
            channel = self.bot.get_channel(self.leetcode_channel_id)
            if channel:
                await channel.send(embed=embed)
                logger.info(f'[BOT][TASK][LEETCODE] Sent to channel: {channel.name}')
            else:
                logger.error(f'[BOT][TASK][LEETCODE] Channel not found: {self.leetcode_channel_id}')
        except Exception as e:
            logger.exception(f'[BOT][TASK][LEETCODE] Error sending message: {type(e).__name__}: {e}')

    @commands.command(name='leetcode')
    async def manual_leetcode(self, ctx):
        """Manually trigger the LeetCode problem of the day"""
        try:
            logger.info(f'[BOT][COMMAND][LEETCODE] User "{ctx.author.name}" requested the LeetCode problem of the day')

            problem_data = await self.fetch_daily_problem()
            if problem_data:
                embed = self.format_problem_message(problem_data)
                await ctx.send(embed=embed)
                logger.info(f'[BOT][COMMAND][LEETCODE] Sent LeetCode problem to user "{ctx.author.name}" and deleted the command message.')
            else:
                logger.error(f'[BOT][COMMAND][LEETCODE] Failed to fetch problem data')

            await ctx.message.delete()

        except Exception as e:
            logger.exception(f'[BOT][COMMAND][LEETCODE] Error: {type(e).__name__}: {e}')


async def setup(bot):
    await bot.add_cog(LeetCodeDailyTask(bot))
