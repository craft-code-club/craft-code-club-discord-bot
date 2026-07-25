import os
from pathlib import Path
import discord
from discord.ext import commands
import logging

from utils.discord_log_handler import DiscordLogHandler


class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.messages = True
        intents.guilds = True

        super().__init__(
            command_prefix=commands.when_mentioned_or('/'),
            case_insensitive=True,
            intents=intents)

    # Initial setup
    async def setup_hook(self):
        await self.load_extensions()

    async def load_extensions(self, *folders):
        logging.debug('[BOT][STARTUP][EXTENSIONS] Loading...')

        path = Path(f"{os.path.realpath(os.path.dirname(__file__))}/../usescases")

        if not path.exists():
            logging.warning(f'[BOT][STARTUP][EXTENSIONS] Path "{path}" does not exist')
            return

        for file in path.rglob("*.py"):
            if file.name.endswith(("command_bot.py", "task_bot.py", "event_bot.py")):
                try:
                    bot_extension = ".".join(file.relative_to(path.parent).with_suffix('').parts)
                    logging.debug(f'[BOT][STARTUP][EXTENSIONS] Loading "{bot_extension}"...')
                    await self.load_extension(bot_extension)
                    logging.info(f'[BOT][STARTUP][EXTENSIONS] Loaded "{bot_extension}"!')
                except Exception:
                    logging.exception(f'[BOT][STARTUP][EXTENSIONS] Failed to load "{bot_extension}"')

        logging.info('[BOT][STARTUP][EXTENSIONS] Loaded!')


    async def on_ready(self):
        logging.info(f'[BOT][STARTUP] Logged in as {self.user} ({self.user.id})')
        self.setup_channel_logs()

    def setup_channel_logs(self):
        logs_channel_id = os.environ.get('LOGS_CHANNEL_ID')
        if logs_channel_id is None or logs_channel_id == '':
            logging.debug('[BOT][STARTUP][LOGS] LOGS_CHANNEL_ID is not set, skipping channel logs')
            return

        root_logger = logging.getLogger()

        # Guard against on_ready firing again on reconnect adding duplicates.
        if any(isinstance(handler, DiscordLogHandler) for handler in root_logger.handlers):
            return

        try:
            channel_id = int(logs_channel_id)
        except ValueError:
            logging.error(f'[BOT][STARTUP][LOGS] LOGS_CHANNEL_ID "{logs_channel_id}" is not a valid channel id')
            return

        handler = DiscordLogHandler(self, channel_id)
        handler.setFormatter(logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(handler)
        logging.info(f'[BOT][STARTUP][LOGS] Channel logs enabled on channel {channel_id}')

    # Error handling
    async def on_command_error(self, context, error):
        if isinstance(error, commands.CommandNotFound):
            #await context.send('Command not found.')
            logging.debug
        else:
            logging.error(f'[BOT][GLOBAL] {type(error)}')
            raise error


def run_discord_bot():
    # Get Discord API token
    discord_api_token = os.environ.get('DISCORD_API_TOKEN')
    if discord_api_token is None or discord_api_token == '':
        logging.error('[BOT][STARTUP] DISCORD_API_TOKEN is not set in .env file or environment variables. Exiting...')
        exit(1)

    logging.debug('[BOT][STARTUP] Creating Discord bot instance...')
    bot =  DiscordBot()

    logging.debug('[BOT][STARTUP] Starting Discord bot...')
    bot.run(discord_api_token)
