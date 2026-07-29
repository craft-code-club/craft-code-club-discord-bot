from discord.ext import commands
import discord
import asyncio
import os
from utils.message_loader import load_message
import logging

logger = logging.getLogger(__name__)

TRUTHY_VALUES = ('1', 'true', 'yes', 'on')


async def setup(bot):
    await bot.add_cog(NewMemberEventBot(bot))


def _parse_bool(raw: str, default: bool) -> bool:
    value = raw.strip().lower()
    if not value:
        return default
    return value in TRUTHY_VALUES


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

        # Public channel welcome message. Gated by WELCOME_MESSAGE_ENABLED (default on) and posted to
        # WELCOME_CHANNEL_ID. The direct-message welcome is always sent and is not affected by these.
        self.welcome_message_enabled = _parse_bool(os.environ.get('WELCOME_MESSAGE_ENABLED', ''), default=True)
        self.welcome_channel_id = self.__parse_channel_id('WELCOME_CHANNEL_ID')

        if self.welcome_message_enabled and not self.welcome_channel_id:
            logger.warning(
                '[BOT][EVENT][NEW MEMBER] WELCOME_MESSAGE_ENABLED is on but WELCOME_CHANNEL_ID is not set. '
                'The public welcome message will be skipped.')

        # Private admin notification about new joiners. Opt-in (default off) and posted to
        # ADMIN_JOIN_NOTIFICATION_CHANNEL_ID.
        self.admin_notification_enabled = _parse_bool(os.environ.get('ADMIN_JOIN_NOTIFICATION_ENABLED', ''), default=False)
        self.admin_notification_channel_id = self.__parse_channel_id('ADMIN_JOIN_NOTIFICATION_CHANNEL_ID')

        if self.admin_notification_enabled and not self.admin_notification_channel_id:
            logger.warning(
                '[BOT][EVENT][NEW MEMBER] ADMIN_JOIN_NOTIFICATION_ENABLED is on but '
                'ADMIN_JOIN_NOTIFICATION_CHANNEL_ID is not set. Admin join notifications will be skipped.')

    def __parse_channel_id(self, env_var: str) -> int:
        raw = os.environ.get(env_var, '').strip()
        if raw and not raw.isdigit():
            logger.warning(f'[BOT][EVENT][NEW MEMBER] {env_var} must be a Discord channel ID (digits).')
            return 0
        return int(raw) if raw.isdigit() else 0

    def _replace_welcome_placeholders(self, message: str, username: str) -> str:
        lines = [
            l.replace('##[username]##', username).replace('##[say_hi_channel]##', self.say_hi_channel)
            for l in message.splitlines() if self.say_hi_channel or '##[say_hi_channel]##' not in l
        ]
        return '\n'.join(lines)

    def _replace_admin_placeholders(self, message: str, member) -> str:
        member_count = member.guild.member_count or 0
        return (message
                .replace('##[username]##', member.mention)
                .replace('##[member_count]##', str(member_count)))

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

        await self.__send_channel_welcome(member)
        await self.__send_admin_notification(member)
        await self.__send_dm_welcome(member)

    async def __send_channel_welcome(self, member) -> None:
        if not self.welcome_message_enabled:
            logger.debug(f'[BOT][EVENT][NEW MEMBER] Public welcome disabled (WELCOME_MESSAGE_ENABLED). Skipping for "{member.name}".')
            return

        if not self.welcome_channel_id:
            logger.debug(f'[BOT][EVENT][NEW MEMBER] WELCOME_CHANNEL_ID is not set. Skipping public welcome for "{member.name}".')
            return

        try:
            channel = self.bot.get_channel(self.welcome_channel_id)
            if channel is None:
                logger.warning(
                    f'[BOT][EVENT][NEW MEMBER] Welcome channel "{self.welcome_channel_id}" not found. '
                    f'Skipping public welcome for "{member.name}".')
                return

            channel_message = self._replace_welcome_placeholders(
                load_message('channel_welcome_message.md'),
                member.mention
            )
            await channel.send(channel_message)
        except Exception:
            logger.exception('[BOT][EVENT][NEW MEMBER]: It was not possible to send a welcome message to the welcome channel')

    async def __send_admin_notification(self, member) -> None:
        if not self.admin_notification_enabled:
            return

        if not self.admin_notification_channel_id:
            logger.debug(f'[BOT][EVENT][NEW MEMBER] ADMIN_JOIN_NOTIFICATION_CHANNEL_ID is not set. Skipping admin notification for "{member.name}".')
            return

        try:
            channel = self.bot.get_channel(self.admin_notification_channel_id)
            if channel is None:
                logger.warning(
                    f'[BOT][EVENT][NEW MEMBER] Admin notification channel "{self.admin_notification_channel_id}" not found. '
                    f'Skipping admin notification for "{member.name}".')
                return

            admin_message = self._replace_admin_placeholders(
                load_message('admin_new_member_message.md'),
                member
            )
            # Suppress pings: the new member usually cannot see the admin channel, so a real mention
            # would be a confusing "ghost ping". The mention still renders as a clickable name.
            await channel.send(admin_message, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            logger.exception('[BOT][EVENT][NEW MEMBER]: It was not possible to send the admin join notification')

    async def __send_dm_welcome(self, member) -> None:
        try:
            dm_message = self._replace_welcome_placeholders(
                load_message('dm_welcome_message.md'),
                member.name
            )
            await member.send(dm_message)
        except discord.errors.Forbidden:  # If the user has DMs disabled
            logger.warning(f'[BOT][EVENT][NEW MEMBER]: The user "{member.name}" has DMs disabled')
