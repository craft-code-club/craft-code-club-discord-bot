from discord.ext import commands
import discord
import os
from utils.message_loader import load_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(NewMemberEventBot(bot))


class NewMemberEventBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.say_hi_channel = os.environ.get('SAY_HI_CHANNEL', '')

        if not self.say_hi_channel:
            logger.warning('[BOT][EVENT][NEW MEMBER] SAY_HI_CHANNEL is not set. Welcome messages will not include a channel.')

    def _replace_welcome_placeholders(self, message: str, username: str) -> str:
        return (
            message
            .replace('##[username]##', username)
            .replace('##[say_hi_channel]##', self.say_hi_channel)
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if member.bot:
            logger.info(f'[BOT][EVENT][NEW MEMBER] Bot "{member.name}" joined the server')
            return

        logger.info(f'[BOT][EVENT][NEW MEMBER] "{member.name}" joined the server')

        try:
            system_channel = member.guild.system_channel
            if system_channel:
                channel_message = self._replace_welcome_placeholders(
                    load_message('channel_welcome_message.md'),
                    member.mention
                )
                await system_channel.send(channel_message)
        except Exception:
            logger.exception(f'[BOT][EVENT][NEW MEMBER]: It was not possible to send a welcome message to the system channel')


        try:
            dm_message = self._replace_welcome_placeholders(
                load_message('dm_welcome_message.md'),
                member.name
            )
            await member.send(dm_message)
        except discord.errors.Forbidden: # If the user has DMs disabled
            logger.warning(f'[BOT][EVENT][NEW MEMBER]: The user "{member.name}" has DMs disabled')
