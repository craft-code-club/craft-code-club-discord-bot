"""Forward warnings and errors to the Discord logs channel.

The container bot installed a `logging.Handler` that pushed WARNING+ records
onto the running bot's event loop. A function has no such loop, and a handler
that made a blocking HTTP call per record would be worse than useless on a
3-second deadline.

So records are COLLECTED during an invocation and FLUSHED once at the end, in
one message. Timer and queue functions call `install_collector()` on the way in
and `await flush(rest)` on the way out; the HTTP trigger does neither, because
nothing on that path may make a network call.

Application Insights remains the complete log sink. This channel is the "look
at me" signal for the failures nobody would otherwise notice.
"""

import logging
from typing import Optional

from discord_api.rest import DiscordRest
from utils import config

logger = logging.getLogger(__name__)

MAX_REPORT_LENGTH = 1800
MAX_RECORDS = 20

# Noise from the Azure SDK and the HTTP stack belongs in App Insights, not in a
# Discord channel.
_MUTED_PREFIXES = ('azure', 'aiohttp', 'asyncio', 'urllib3')


class _CollectingHandler(logging.Handler):
    """Buffers WARNING+ records so one invocation produces at most one message."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records: list[str] = []
        self.setFormatter(logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(_MUTED_PREFIXES) or record.name == __name__:
            return
        if len(self.records) >= MAX_RECORDS:
            return
        try:
            self.records.append(self.format(record))
        except Exception:  # noqa: BLE001 - logging must never raise
            self.handleError(record)


_handler: Optional[_CollectingHandler] = None


def install_collector() -> None:
    """Attach the collector to the root logger once per worker process."""
    global _handler
    if _handler is None:
        _handler = _CollectingHandler()
        logging.getLogger().addHandler(_handler)
    _handler.records.clear()


async def flush(rest: DiscordRest) -> None:
    """Post everything collected since `install_collector()`. Never raises."""
    if _handler is None or not _handler.records:
        return

    records, _handler.records = _handler.records, []
    await report(rest, '\n'.join(records))


async def report(rest: DiscordRest, message: str) -> None:
    """Best-effort post to LOGS_CHANNEL_ID. Never raises."""
    channel_id = config.logs_channel_id()
    if not channel_id:
        return

    try:
        safe = message.replace('```', '`​``')[:MAX_REPORT_LENGTH]
        await rest.send_message(channel_id, content=f'```\n{safe}\n```')
    except Exception:  # noqa: BLE001 - reporting must never mask the original failure
        logger.exception('[REPORTING] Failed to send a log message to channel %s', channel_id)
