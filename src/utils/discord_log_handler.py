import asyncio
import logging
import sys
import threading

import discord
from discord.ext import commands

# Maximum characters Discord allows in a single message.
DISCORD_MESSAGE_LIMIT = 2000
# Reserve room for the surrounding code block markers ("```\n" ... "\n```").
CODE_BLOCK_OVERHEAD = 8
MAX_CONTENT_LENGTH = DISCORD_MESSAGE_LIMIT - CODE_BLOCK_OVERHEAD


class DiscordLogHandler(logging.Handler):
    """Logging handler that forwards WARNING and above records to a Discord channel.

    The handler is designed to never feed its own failures back into the logging
    system, which would otherwise create an infinite loop (a failed ``send`` that
    logs an error would trigger another ``send`` and so on). Every failure path
    writes to ``sys.stderr`` directly instead of using the logging module.
    """

    def __init__(self, bot: commands.Bot, channel_id: int, level: int = logging.WARNING):
        super().__init__(level=level)
        self.bot = bot
        self.channel_id = channel_id
        # Per-thread reentrancy guard to prevent recursive emit calls.
        self._guard = threading.local()
        # Ensures the "channel not found" notice is printed at most once.
        self._channel_warning_shown = False

    def emit(self, record: logging.LogRecord):
        # Layer 1: reentrancy guard - if we are already inside emit on this
        # thread, bail out immediately.
        if getattr(self._guard, 'active', False):
            return

        # Layer 2: never forward records produced by discord.py itself or by
        # this handler's own module, so send-related logging can't loop back.
        if record.name.startswith('discord') or record.name == __name__:
            return

        self._guard.active = True
        try:
            original_levelname = record.levelname
            record.levelname = logging.getLevelName(record.levelno)
            try:
                message = self.format(record)
            finally:
                record.levelname = original_levelname
            message = message.replace("```", "`\u200b``")
            if len(message) > MAX_CONTENT_LENGTH:
                message = message[:MAX_CONTENT_LENGTH]
            loop = self.bot.loop
            if not loop.is_running():
                return

            # Layer 3: fire-and-forget; do not call .result() so emit never
            # blocks and coroutine errors are handled inside _send.
            asyncio.run_coroutine_threadsafe(self._send(message), loop)
        except Exception:
            # Layer 4: emit must never raise or log; handleError writes to
            # sys.stderr, not through the logging system.
            self.handleError(record)
        finally:
            self._guard.active = False

    async def _send(self, message: str):
        # Layer 5: any failure here is written to sys.stderr only, never via
        # logging, which breaks the potential infinite loop.
        try:
            channel = self.bot.get_channel(self.channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(self.channel_id)
                except Exception as fetch_error:  # noqa: BLE001 - must not escape or log
                    if not self._channel_warning_shown:
                        self._channel_warning_shown = True
                        print(
                            f"[DiscordLogHandler] Channel {self.channel_id} could not be fetched ({fetch_error}); logs will not be forwarded. Check LOGS_CHANNEL_ID.",
                            file=sys.stderr,
                        )
                    return
            if not isinstance(channel, discord.abc.Messageable):
                if not self._channel_warning_shown:
                    self._channel_warning_shown = True
                    print(
                        f"[DiscordLogHandler] Channel {self.channel_id} was not found or is "
                        f"not a text channel; logs will not be forwarded. Check LOGS_CHANNEL_ID.",
                        file=sys.stderr,
                    )
                return
            await channel.send(f"```\n{message}\n```", allowed_mentions=discord.AllowedMentions.none())
        except Exception as error:  # noqa: BLE001 - must not escape or log
            print(
                f"[DiscordLogHandler] Failed to send log to channel "
                f"{self.channel_id}: {error}",
                file=sys.stderr,
            )
