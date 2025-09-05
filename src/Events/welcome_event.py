from discord.ext import commands
import discord
from Messages.message_loader import load_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(WelcomeEvent(bot))


class WelcomeEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if member.bot:
            logger.info(f'[BOT][EVENT][WELCOME] Bot "{member.name}" joined the server')
            return

        logger.info(f'[BOT][EVENT][WELCOME] "{member.name}" joined the server')


        try:
            system_channel = member.guild.system_channel
            if system_channel:
                # system_channel_name = system_channel.name
                # system_channel_id = system_channel.id
                channel_message = load_message('events-welcome-channel.md').replace('##[username]##', member.mention)
                await system_channel.send(channel_message)
        except Exception as e:
            logger.exception(f'[BOT][EVENT][WELCOME]: It was not possible to send a welcome message to the system channel: {e}')


        try:
            await member.send(load_message('events-welcome-dm.md').replace('##[username]##', member.name))
        except discord.errors.Forbidden: # If the user has DMs disabled
            logger.exception(f'[BOT][EVENT][WELCOME]: The user "{member.name}" has DMs disabled')
