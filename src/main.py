import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging
from Utils.logger import setup_logging

load_dotenv() # Load .env file


# Setup logging
setup_logging()
logging.getLogger(__name__)


logging.debug('[BOT][STARTUP] Starting bot...')


DISCORD_API_TOKEN = os.environ.get('DISCORD_API_TOKEN')
if DISCORD_API_TOKEN is None or DISCORD_API_TOKEN == '':
    logging.error('[BOT][STARTUP] DISCORD_API_TOKEN is not set in .env file or environment variables. Exiting...')
    exit(1)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.messages = True
intents.guilds = True


class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('/'),
            intents = intents)


    # Initial setup
    async def setup_hook(self):
        await self.load_extensions("UsesCases", "Commands")
        await self.load_extensions("UsesCases", "Events")
        await self.load_extensions("UsesCases", "Tasks")


    async def load_extensions(self, *folders):
        relative_path = folders[0] if len(folders) == 1 else "/".join(folders)

        logging.debug(f'[BOT][STARTUP][EXTENSIONS] Loading "{relative_path}"...')

        path = f"{os.path.realpath(os.path.dirname(__file__))}/{relative_path}"

        if not os.path.exists(path):
            logging.warning(f'[BOT][STARTUP][EXTENSIONS] Path "{path}" does not exist. Skipping...')
            return

        for file in os.listdir(path):
            if file.endswith(".py"):
                bot_extension = f"{relative_path.replace('/', '.')}.{file[:-3]}"
                try:
                    logging.debug(f'[BOT][STARTUP][EXTENSIONS] Loading "{bot_extension}"...')
                    await self.load_extension(bot_extension)
                    logging.info(f'[BOT][STARTUP][EXTENSIONS] Loaded "{bot_extension}"!')
                except Exception:
                    logging.exception(f'[BOT][STARTUP][EXTENSIONS] Failed to load "{bot_extension}"')

        logging.info(f'[BOT][STARTUP][EXTENSIONS] Loaded "{relative_path}"!')


    async def on_ready(self):
        logging.info(f'[BOT][STARTUP] Logged in as {self.user} ({self.user.id})')


    # Error handling
    async def on_command_error(self, context, error):
        if isinstance(error, commands.CommandNotFound):
            await context.send('Command not found.')

        else:
            logging.error(f'[BOT][GLOBAL] {type(error)}')
            raise error


bot = DiscordBot()
bot.run(DISCORD_API_TOKEN)
