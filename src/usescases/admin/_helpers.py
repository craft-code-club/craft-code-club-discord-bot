"""Validation helpers shared by the admin command handlers."""

import re
from urllib.parse import urlparse

EVENT_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]+')


def is_valid_event_id(event_id: str) -> bool:
    return bool(EVENT_ID_PATTERN.fullmatch(event_id or ''))


def is_valid_url(url: str) -> bool:
    url = (url or '').strip()
    if not url or ' ' in url:
        return False

    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
