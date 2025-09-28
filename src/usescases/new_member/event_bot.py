from discord.ext import commands
import discord
from utils.message_loader import load_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(NewMemberEventBot(bot))


class NewMemberEventBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if member.bot:
            logger.info(f'[BOT][EVENT][NEW MEMBER] Bot "{member.name}" joined the server')
            return

        logger.info(f'[BOT][EVENT][NEW MEMBER] "{member.name}" joined the server')

        try:
            system_channel = member.guild.system_channel
            if system_channel:
                channel_message = load_message('channel_welcome_message.md').replace('##[username]##', member.mention)
                await system_channel.send(channel_message)
        except Exception:
            logger.exception(f'[BOT][EVENT][NEW MEMBER]: It was not possible to send a welcome message to the system channel')


        try:
            await member.send(load_message('dm_welcome_message.md').replace('##[username]##', member.name))
        except discord.errors.Forbidden: # If the user has DMs disabled
            logger.warning(f'[BOT][EVENT][NEW MEMBER]: The user "{member.name}" has DMs disabled')
