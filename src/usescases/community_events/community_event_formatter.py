"""Render a CommunityEvent as raw Discord API payloads.

Previously built `discord.Embed` objects and `guild.create_scheduled_event`
keyword arguments. Both are now plain dicts sent straight to the REST API, so
the bot no longer needs discord.py.
"""

from datetime import timezone
from typing import Optional

from discord_api.rest import escape_mentions
from usescases.community_events.community_event import CommunityEvent, ReminderTime
from utils.image_service import image_service
from utils.timezones import get_brazil_timezone

EMBED_COLOR = 0x2ECC71  # Green


class ScheduledEventPayload:
    """Arguments for `DiscordRest.create_scheduled_event`."""

    def __init__(self, name: str, description: str, start_time, end_time, location: str,
                 image: Optional[bytes] = None, image_content_type: Optional[str] = None):
        self.name = name
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.image = image
        self.image_content_type = image_content_type

    def as_kwargs(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'image': self.image,
            'image_content_type': self.image_content_type,
        }


class EventMessageFormatter:
    def __init__(self):
        self.notification_titles = {
            ReminderTime.A_WEEK: "Evento em 1 semana!",
            ReminderTime.THREE_DAYS: "Evento em 3 dias!",
            ReminderTime.A_DAY: "Evento amanhã!",
            ReminderTime.A_HOUR: "Evento começando em 1 hora!"
        }

    async def format_to_discord_event(self, event: CommunityEvent) -> ScheduledEventPayload:
        # Stored datetimes are naive São Paulo local time; Discord wants ISO 8601 UTC.
        sao_paulo_tz = get_brazil_timezone()
        utc_tz = timezone.utc

        start_time_utc = event.start_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)
        end_time_utc = event.end_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)

        image_bytes = None
        image_content_type = None
        banner_url = event.banner_url()
        if banner_url:
            downloaded = await image_service.download_image(banner_url)
            if downloaded:
                image_bytes = downloaded.data
                image_content_type = downloaded.content_type

        return ScheduledEventPayload(
            name=event.title,
            description=event.description,
            start_time=start_time_utc,
            end_time=end_time_utc,
            location=event.discord_event_location(),
            image=image_bytes,
            image_content_type=image_content_type,
        )

    def format_to_message(self, event: CommunityEvent,
                          reminder_time: Optional[ReminderTime] = None) -> dict:
        # The caller usually already computed the window; recomputing it here
        # against a slightly later clock could render a different reminder than
        # the one being sent.
        reminder_time = reminder_time or event.reminder_time()
        reminder_title = self.notification_titles.get(reminder_time) if reminder_time else None
        reminder_title = reminder_title or "Evento"
        safe_title = escape_mentions(event.title)
        safe_description = escape_mentions(event.description)
        event_description = f"***{reminder_title}***\n\n{safe_description}"

        fields = [
            {'name': '🇧🇷', 'value': f'*{event.brazil_datetime()}*', 'inline': True},
            {'name': '🇨🇦', 'value': f'*{event.canada_datetime()}*', 'inline': True},
            {'name': '🇵🇹', 'value': f'*{event.portugal_datetime()}*', 'inline': True},
        ]

        if (event.session_link and event.session_link.strip()) and event.open_session and reminder_time == ReminderTime.A_HOUR:
            safe_session_link = event.session_link.strip().replace(')', '%29')
            fields.append({
                'name': '🧑‍💻 Participar',
                'value': f'[Clique aqui para participar conosco]({safe_session_link})',
                'inline': False,
            })

        if event.recording_link and event.recording_link.strip():
            safe_recording_link = event.recording_link.strip().replace(')', '%29')
            fields.append({
                'name': '📺 Live',
                'value': f'[Clique aqui para assistir a live]({safe_recording_link})',
                'inline': False,
            })

        fields.append({
            'name': '🔗 Detalhes',
            'value': f'[Clique aqui para ver os detalhes do evento]({event.event_details_url()})',
            'inline': False,
        })

        embed: dict = {
            'title': f'📢 {safe_title}',
            'description': event_description,
            'color': EMBED_COLOR,
            'fields': fields,
            'author': {
                'name': 'Ver detalhes completos',
                'url': event.event_details_url(),
                'icon_url': 'https://craftcodeclub.io/logo.png',
            },
        }

        banner_url = event.banner_url()
        if banner_url:
            embed['image'] = {'url': banner_url}

        return embed


# Global instance
event_formatter = EventMessageFormatter()
