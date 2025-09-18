import os
from dotenv import load_dotenv
import logging
from Utils.logger import setup_logging
from services.discord_bot import run_discord_bot


def main():
    load_dotenv()

    # Setup logging
    setup_logging()
    logging.getLogger(__name__)

    logging.info('[APP] Starting...')

    run_discord_bot()

if __name__ == "__main__":
    main()
