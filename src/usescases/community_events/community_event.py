from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from utils.timezones import get_brazil_timezone, get_canada_timezone, get_portugal_timezone


class ReminderTime(Enum):
    A_WEEK = "1_week"
    THREE_DAYS = "3_days"
    A_DAY = "1_day"
    A_HOUR = "1_hour"


@dataclass
class CommunityEvent:
    id: str
    title: str
    github_url: str
    description: str

    start_datetime: datetime
    end_datetime: datetime

    discord_event_id: Optional[str] = None

    location: Optional[str] = None
    type: Optional[str] = None
    banner: Optional[str] = None

    is_live: bool = False
    youtube_title: Optional[str] = None

    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    post_link: Optional[str] = None

    speakers: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    a_weekly_notify: bool = False
    three_days_notify: bool = False
    a_day_notify: bool = False
    a_hour_notify: bool = False

    def event_details_url(self) -> str:
        return f"https://craftcodeclub.io/events/{self.id}"

    def banner_url(self) -> Optional[str]:
        if self.banner:
            return f"https://raw.githubusercontent.com/craft-code-club/blog-c3/refs/heads/main/public/events/{self.banner}"
        return None

    def discord_event_location(self) -> str:
        if self.has_recording_link() and self.is_live_event():
            return self.recording_link
        if self.registration_link:
            return self.registration_link
        return self.event_details_url()

    def get_youtube_title(self) -> Optional[str]:
        if not self.is_live_event():
            return None

        if self.youtube_title:
            return self.youtube_title

        return self.title

    def has_recording_link(self) -> bool:
        return bool(self.recording_link and self.recording_link.strip())

    def is_live_event(self) -> bool:
        return self.is_live

    def is_future_event(self) -> bool:
        now = datetime.now(get_brazil_timezone())
        event_time = self.start_datetime
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=now.tzinfo)
        return event_time > now

    def brazil_datetime(self) -> str:
        return self.start_datetime.strftime("%Y/%m/%d - %H:%M")

    def canada_datetime(self) -> str:
        # Convert from Brazil timezone (UTC-3) to Canada Pacific timezone (UTC-8/-7)
        brazil_tz = get_brazil_timezone()
        canada_tz = get_canada_timezone()

        # Localize the datetime to Brazil timezone if it's naive
        if self.start_datetime.tzinfo is None:
            brazil_time = self.start_datetime.replace(tzinfo=brazil_tz)
        else:
            brazil_time = self.start_datetime.astimezone(brazil_tz)

        # Convert to Canada timezone
        canada_time = brazil_time.astimezone(canada_tz)

        return canada_time.strftime("%Y/%m/%d - %H:%M")

    def portugal_datetime(self) -> str:
        # Convert from Brazil timezone (UTC-3) to Portugal timezone (UTC+0/+1)
        brazil_tz = get_brazil_timezone()
        portugal_tz = get_portugal_timezone()

        # Localize the datetime to Brazil timezone if it's naive
        if self.start_datetime.tzinfo is None:
            brazil_time = self.start_datetime.replace(tzinfo=brazil_tz)
        else:
            brazil_time = self.start_datetime.astimezone(brazil_tz)

        # Convert to Portugal timezone
        portugal_time = brazil_time.astimezone(portugal_tz)

        return portugal_time.strftime("%Y/%m/%d - %H:%M")

    def reminder_time(self) -> Optional[ReminderTime]:
        now = datetime.now(get_brazil_timezone())
        now_date_only = now.date()

        event_date = self.start_datetime
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=now.tzinfo)
        event_date_only = event_date.date()

        delta_days = (event_date_only - now_date_only).days
        delta_hours = (event_date - now).total_seconds() / 3600

        if delta_hours <= 1:
            return ReminderTime.A_HOUR

        if delta_days == 1:
            return ReminderTime.A_DAY

        if delta_days == 3: # 3 days
            return ReminderTime.THREE_DAYS

        if delta_days == 7: # 1 week
            return ReminderTime.A_WEEK

        return None
