import logging
import aiohttp
from typing import List
from datetime import datetime
from usescases.community_events.community_event import CommunityEvent

logger = logging.getLogger(__name__)

FUTURE_EVENTS_URL = "https://craftcodeclub.io/api/events/future"


class WebsiteService:
    async def fetch_future_events(self) -> List[CommunityEvent]:
        logger.debug('[SERVICES][WEBSITE][EVENTS] Fetching future events...')

        async with aiohttp.ClientSession() as session:
            async with session.get(FUTURE_EVENTS_URL) as response:
                if response.status != 200:
                    raise Exception(f'Fetch future events failed with status code {response.status}')

                events_data = await response.json(content_type=None)

        events: List[CommunityEvent] = []
        for event_data in events_data:
            event = self.__parse_event(event_data)
            events.append(event)

        logger.debug(f'[SERVICES][WEBSITE][EVENTS] Successfully fetched {len(events)} future events')
        return events

    def __parse_event(self, data: dict) -> CommunityEvent:
        event_date = data['date']
        time_range = data['time']
        time_parts = [p.strip() for p in time_range.split('-')]
        if len(time_parts) != 2:
            raise Exception(f'Invalid time range "{time_range}" for event "{data.get("id")}"')

        start_str = f"{event_date}T{time_parts[0]}:00"
        end_str = f"{event_date}T{time_parts[1]}:00"

        start_datetime = datetime.fromisoformat(start_str)
        end_datetime = datetime.fromisoformat(end_str)

        return CommunityEvent(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=data.get('location'),
            type=data.get('type', 'online'),
            banner=data.get('banner'),
            is_live=bool(data.get('isLive')) if isinstance(data.get('isLive'), bool) else str(data.get('isLive', '')).strip().lower() == 'true',
            open_session=bool(data.get('openSession')) if isinstance(data.get('openSession'), bool) else str(data.get('openSession', '')).strip().lower() == 'true',
            session_link=data.get('sessionLink'),
            registration_link=None if (data.get('registrationLink') or '').strip() in ('', '{{discord-link}}') else (data.get('registrationLink') or '').strip(),
            recording_link=data.get('recordingLink'),
            post_link=data.get('postLink'),
            speakers=data.get('speakers', []),
            tags=data.get('tags', []),
        )


# Global instance
website_service = WebsiteService()
