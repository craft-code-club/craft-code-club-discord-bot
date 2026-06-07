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
        raw_say_hi_channel_id = os.environ.get('SAY_HI_CHANNEL', '').strip()
        say_hi_channel_id = int(raw_say_hi_channel_id) if raw_say_hi_channel_id.isdigit() else 0
        self.say_hi_channel = f'<#{say_hi_channel_id}>' if say_hi_channel_id else ''

        if raw_say_hi_channel_id and not raw_say_hi_channel_id.isdigit():
            logger.warning('[BOT][EVENT][NEW MEMBER] SAY_HI_CHANNEL must be a Discord channel ID (digits).')
        elif not self.say_hi_channel:
            logger.warning('[BOT][EVENT][NEW MEMBER] SAY_HI_CHANNEL is not set. Welcome messages will not include a channel.')
    def _replace_welcome_placeholders(self, message: str, username: str) -> str:
        lines = [
            l.replace('##[username]##', username).replace('##[say_hi_channel]##', self.say_hi_channel)
            for l in message.splitlines() if self.say_hi_channel or '##[say_hi_channel]##' not in l
        ]
        return '\n'.join(lines)

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
