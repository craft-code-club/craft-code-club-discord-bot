import os
import logging

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_RED = '\033[91m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels"""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.exception: Colors.RED,
        logging.CRITICAL: Colors.BRIGHT_RED + Colors.BOLD,
    }

    def format(self, record):
        # Get the color for this log level
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)

        # Color only the level name, leave message and timestamp in default color
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"

        return super().format(record)


def setup_logging():
    """Setup colored logging configuration"""
    try:
        # Get log level from environment, default to INFO
        log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper())
    except AttributeError:
        log_level = logging.INFO

    # Setup colored logging
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(level=log_level, handlers=[handler])
