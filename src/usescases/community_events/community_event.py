from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo
from enum import Enum


class ReminderTime(Enum):
    A_WEEK = "1_week"
    THREE_DAYS = "3_days"
    A_DAY = "1_day"
    A_HOUR = "1_hour"


@dataclass
class CommunityEvent:
    id: str
    title: str
    description: str
    start_datetime: datetime
    location: str
    type: str
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    post_link: Optional[str] = None
    github_url: str = None
    speakers: Optional[List[str]] = None



@dataclass
class CommunityEventSummary:
    id: str
    title: str
    description: str
    start_datetime: datetime
    github_url: str
    registration_link: Optional[str] = None

    a_weekly_notify: bool = False
    three_days_notify: bool = False
    a_day_notify: bool = False
    a_hour_notify: bool = False

    def event_details_url(self) -> str:
        return f"https://craftcodeclub.io/events/{self.id}"

    def is_future_event(self) -> bool:
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        event_time = self.start_datetime
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=now.tzinfo)
        return event_time > now

    def brazil_datetime(self) -> str:
        return self.start_datetime.strftime("%Y/%m/%d - %H:%M")

    def canada_datetime(self) -> str:
        # Convert from Brazil timezone (UTC-3) to Canada Pacific timezone (UTC-8/-7)
        brazil_tz = ZoneInfo('America/Sao_Paulo')
        canada_tz = ZoneInfo('America/Vancouver')

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
        brazil_tz = ZoneInfo('America/Sao_Paulo')
        portugal_tz = ZoneInfo('Europe/Lisbon')

        # Localize the datetime to Brazil timezone if it's naive
        if self.start_datetime.tzinfo is None:
            brazil_time = self.start_datetime.replace(tzinfo=brazil_tz)
        else:
            brazil_time = self.start_datetime.astimezone(brazil_tz)

        # Convert to Portugal timezone
        portugal_time = brazil_time.astimezone(portugal_tz)

        return portugal_time.strftime("%Y/%m/%d - %H:%M")

    def reminder_time(self) -> Optional[ReminderTime]:
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        now_date_only = now.date()

        event_date = self.start_datetime
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=now.tzinfo)
        event_date_only = event_date.date()

        delta_days = (event_date_only - now_date_only).days
        delta_hours = (event_date - now).total_seconds() / 3600

        if delta_hours <= 1:
            return ReminderTime.A_HOUR

        if delta_days <= 1:
            return ReminderTime.A_DAY

        if delta_days <= 3: # 3 days
            return ReminderTime.THREE_DAYS

        if delta_days <= 7: # 1 week
            return ReminderTime.A_WEEK

        return None


    @classmethod
    def create(cls, event: CommunityEvent) -> "CommunityEventSummary":
        return cls(
            id = event.id,
            title = event.title,
            description = event.description,
            start_datetime = event.start_datetime,
            github_url = event.github_url or None,
            registration_link = event.registration_link or None,
            a_weekly_notify = False,
            three_days_notify = False,
            a_day_notify = False,
            a_hour_notify = False)
