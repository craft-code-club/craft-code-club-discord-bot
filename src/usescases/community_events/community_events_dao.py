import os
from typing import Optional
from azure.data.tables import TableServiceClient
from datetime import datetime, timedelta

from usescases.community_events.community_event import CommunityEvent

# Table
#    PartitionKey: id
#    RowKey: start_datetime
#    weekly_notify: bool
#    three_days_notify: bool
#    one_day_notify: bool
#    one_hour_notify: bool

class CommunityEventsDao:
    def __init__(self):
        TABLE_NAME = "CommunityEvents"

        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        connection = TableServiceClient.from_connection_string(connection_string)
        connection.create_table_if_not_exists(TABLE_NAME)

        self.table = connection.get_table_client(TABLE_NAME)


    def get_upcoming_events(self, now: datetime) -> list[CommunityEvent]:
        now_isoformat = now.isoformat()
        upcoming_events = self.table.query_entities(f"RowKey gt '{now_isoformat}'")

        result: list[CommunityEvent] = []
        for upcoming_event in upcoming_events:
            result.append(self.__to_community_event(upcoming_event))

        return result


    def get(self, event_id: str) -> Optional[CommunityEvent]:
        events = self.table.query_entities(f"PartitionKey eq '{event_id}'")
        for event in events:
            return self.__to_community_event(event)
        return None

    def delete(self, event_id: str, start_date: datetime) -> None:
        start_date_isoformat = start_date.isoformat()
        self.table.delete_entity(
            partition_key = event_id,
            row_key = start_date_isoformat)


    def upsert(self, event: CommunityEvent) -> None:
        # insert into table
        entity = {
            'PartitionKey': event.id,
            'RowKey': event.start_datetime.isoformat(),
            'end_datetime': event.end_datetime.isoformat(),
            'discord_event_id': event.discord_event_id,

            'title': event.title,
            'github_url': event.github_url,
            'description': event.description,

            'location': event.location,
            'type': event.type,
            'banner': event.banner,

            'registration_link': event.registration_link,
            'recording_link': event.recording_link,
            'post_link': event.post_link
        }

        self.table.upsert_entity(entity = entity)


    def update(self, event: CommunityEvent) -> None:
        event_datetime = event.start_datetime.isoformat()
        entity = {
            'PartitionKey': event.id,
            'RowKey': event_datetime,
            'end_datetime': event.end_datetime.isoformat(),
            'discord_event_id': event.discord_event_id,

            'title': event.title,
            'github_url': event.github_url,
            'description': event.description,

            'location': event.location,
            'type': event.type,
            'banner': event.banner,

            'registration_link': event.registration_link,
            'recording_link': event.recording_link,
            'post_link': event.post_link,

            'a_weekly_notify': event.a_weekly_notify,
            'three_days_notify': event.three_days_notify,
            'a_day_notify': event.a_day_notify,
            'a_hour_notify': event.a_hour_notify
        }
        self.table.update_entity(entity = entity)

    def __to_community_event(self, event: dict) -> CommunityEvent:
        start_datetime = datetime.fromisoformat(event["RowKey"])

        # fallback to start_datetime plus 2 hours if end_datetime is not present
        end_datetime = datetime.fromisoformat(event["end_datetime"]) if "end_datetime" in event else start_datetime + timedelta(hours=2)

        return CommunityEvent(
            id = event["PartitionKey"],
            start_datetime = start_datetime,
            end_datetime = end_datetime,

            title = event["title"],
            github_url = event["github_url"],
            description = event["description"],

            discord_event_id = event["discord_event_id"] if "discord_event_id" in event else None,

            location = event["location"] if "location" in event else None,
            type = event["type"] if "type" in event else None,
            banner = event["banner"] if "banner" in event else None,

            registration_link = event["registration_link"] if "registration_link" in event else None,
            recording_link = event["recording_link"] if "recording_link" in event else None,
            post_link = event["post_link"] if "post_link" in event else None,

            a_weekly_notify = event["a_weekly_notify"] if "a_weekly_notify" in event else False,
            three_days_notify = event["three_days_notify"] if "three_days_notify" in event else False,
            a_day_notify = event["a_day_notify"] if "a_day_notify" in event else False,
            a_hour_notify = event["a_hour_notify"] if "a_hour_notify" in event else False
        )

# Global instance
community_events_dao = CommunityEventsDao()
