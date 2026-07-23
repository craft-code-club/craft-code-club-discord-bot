from discord.ext import commands
import discord
import asyncio
import os
from utils.message_loader import load_message
import logging

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(NewMemberEventBot(bot))


class NewMemberEventBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        raw_welcome_delay = os.environ.get('WELCOME_DELAY_SECONDS', '').strip()
        self.welcome_delay_seconds = int(raw_welcome_delay) if raw_welcome_delay.isdigit() else 10
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

        # Wait before greeting so that anti-scam/anti-troll moderation bots have time to
        # kick suspicious accounts. Avoids sending a welcome message/DM to a user that has
        # already been removed from the server.
        await asyncio.sleep(self.welcome_delay_seconds)

        try:
            await member.guild.fetch_member(member.id)
        except discord.NotFound:
            logger.info(f'[BOT][EVENT][NEW MEMBER] "{member.name}" left the server during the grace period. No welcome message will be sent.')
            return
        except discord.HTTPException:
            logger.exception(f'[BOT][EVENT][NEW MEMBER] Could not verify if "{member.name}" is still in the server')
            return

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
