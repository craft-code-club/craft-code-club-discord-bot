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
        logging.CRITICAL: Colors.BRIGHT_RED + Colors.BOLD,
    }

    def format(self, record):
        # Get the color for this log level
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)

        # Color only the level name, leave message and timestamp in default color
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"

        return super().format(record)


def resolve_log_level() -> int:
    try:
        return getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper())
    except AttributeError:
        return logging.INFO


def setup_logging():
    """Apply LOG_LEVEL, and add a colored console handler only when we own the root logger.

    Inside Azure Functions the host installs its own handler and forwards root
    logger records to the platform, so replacing the handlers (as
    `logging.basicConfig(handlers=[...])` would) is how user logs go missing.
    Here the level is always applied and a handler is only added when nothing
    else has configured one - i.e. when running the code outside the host.
    """
    log_level = resolve_log_level()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(handler)
