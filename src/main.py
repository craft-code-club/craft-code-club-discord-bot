import os
from dotenv import load_dotenv
import discord
import logging
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info('[BOT][STARTUP] Starting bot...')

load_dotenv() # Load .env file
DISCORD_API_TOKEN = os.environ.get('DISCORD_API_TOKEN')


if DISCORD_API_TOKEN is None or DISCORD_API_TOKEN == '':
    logger.info('[BOT][STARTUP] DISCORD_API_TOKEN is not set in .env file or environment variables. Exiting...')
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
        await self.load_extensions("Commands")
        await self.load_extensions("Events")
        await self.load_extensions("Tasks")


    async def load_extensions(self, context):
        logger.info(f'[BOT][STARTUP][LOAD][{context}] Loading extensions...')

        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/{context}"):

            if file == "register_commands.py":
                logger.info(f'[BOT][STARTUP][LOAD][{context}] Ignoring file "{file}"...')
                continue

            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    logger.info(f'[BOT][STARTUP][LOAD][{context}] Loading "{extension}"...')
                    await self.load_extension(f"{context}.{extension}")
                    logger.info(f'[BOT][STARTUP][LOAD][{context}] Loaded "{extension}"!')
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    logger.info(f'[BOT][STARTUP][LOAD][{context}] Failed to load extension {extension}\n{exception}')

        logger.info(f'[BOT][STARTUP][LOAD][{context}] Loaded extensions!')


    async def on_ready(self):
        logger.info(f'[BOT][STARTUP] Logged in as {self.user} ({self.user.id})')


    # Error handling
    async def on_command_error(self, context, error):
        if isinstance(error, commands.CommandNotFound):
            await context.send('Command not found.')

        else:
            logger.error(f'[BOT][GLOBAL]: {type(error)} - {error}')
            raise error



bot = DiscordBot()
bot.run(DISCORD_API_TOKEN)
