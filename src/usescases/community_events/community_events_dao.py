import os
from azure.data.tables import TableServiceClient
from datetime import datetime

from usescases.community_events.community_event import CommunityEventSummary

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


    def get_upcoming_events(self, now: datetime) -> list[CommunityEventSummary]:
        now_isoformat = now.isoformat()
        upcoming_events = self.table.query_entities(f"RowKey gt '{now_isoformat}'")

        result: list[CommunityEventSummary] = []
        for upcoming_event in upcoming_events:

            event_brazilian_datetime = datetime.fromisoformat(upcoming_event["RowKey"])
            event = CommunityEventSummary(
                id = upcoming_event["PartitionKey"],
                title = upcoming_event["title"],
                description = upcoming_event["description"],
                github_url = upcoming_event["github_url"],
                registration_link = upcoming_event["registration_link"],
                start_datetime = event_brazilian_datetime,

                a_weekly_notify = upcoming_event["a_weekly_notify"] if "a_weekly_notify" in upcoming_event else False,
                three_days_notify = upcoming_event["three_days_notify"] if "three_days_notify" in upcoming_event else False,
                a_day_notify = upcoming_event["a_day_notify"] if "a_day_notify" in upcoming_event else False,
                a_hour_notify = upcoming_event["a_hour_notify"] if "a_hour_notify" in upcoming_event else False
            )

            result.append(event)

        return result


    def upsert(self, event: CommunityEventSummary) -> None:
        event_datetime = event.start_datetime.isoformat()
        events_in_db = self.table.query_entities(f"PartitionKey eq '{event.id}'")
        for event_in_db in events_in_db:
            events_in_db_datetime = event_in_db["RowKey"]

            if events_in_db_datetime != event_datetime:
                self.table.delete_entity(
                    partition_key = event_in_db["PartitionKey"],
                    row_key = event_in_db["RowKey"])

        # insert into table
        event_datetime = event.start_datetime.isoformat()
        entity={
            'PartitionKey': event.id,
            'RowKey': event_datetime,
            'title': event.title,
            'description': event.description,
            'github_url': event.github_url,
            'registration_link': event.registration_link
        }

        self.table.upsert_entity(entity = entity)


    def update(self, event: CommunityEventSummary) -> None:
        event_datetime = event.start_datetime.isoformat()
        entity={
            'PartitionKey': event.id,
            'RowKey': event_datetime,
            'title': event.title,
            'description': event.description,
            'github_url': event.github_url,
            'registration_link': event.registration_link,
            'a_weekly_notify': event.a_weekly_notify,
            'three_days_notify': event.three_days_notify,
            'a_day_notify': event.a_day_notify,
            'a_hour_notify': event.a_hour_notify
        }
        self.table.update_entity(entity = entity)

# Global instance
community_events_dao = CommunityEventsDao()
