from datetime import timedelta, timezone, tzinfo
from functools import lru_cache
from typing import cast

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


BRAZIL_TIMEZONE_NAME = 'America/Sao_Paulo'
BRAZIL_TIMEZONE_FALLBACK = timezone(timedelta(hours=-3))
CANADA_TIMEZONE_NAME = 'America/Vancouver'
CANADA_TIMEZONE_FALLBACK = timezone(timedelta(hours=-8))
PORTUGAL_TIMEZONE_NAME = 'Europe/Lisbon'
PORTUGAL_TIMEZONE_FALLBACK = timezone.utc


@lru_cache(maxsize=1)
def get_brazil_timezone() -> tzinfo:
    return get_timezone(BRAZIL_TIMEZONE_NAME, BRAZIL_TIMEZONE_FALLBACK)


@lru_cache(maxsize=None)
def get_timezone(zone_name: str, fallback: tzinfo) -> tzinfo:
    try:
        return cast(tzinfo, ZoneInfo(zone_name))
    except ZoneInfoNotFoundError:
        return fallback


def get_canada_timezone() -> tzinfo:
    return get_timezone(CANADA_TIMEZONE_NAME, CANADA_TIMEZONE_FALLBACK)


def get_portugal_timezone() -> tzinfo:
    return get_timezone(PORTUGAL_TIMEZONE_NAME, PORTUGAL_TIMEZONE_FALLBACK)