import discord
from usescases.community_events.community_event import CommunityEvent, ReminderTime
from utils.image_service import image_service
from zoneinfo import ZoneInfo
import discord

class EventMessageFormatter:
    def __init__(self):
        self.notification_titles = {
            ReminderTime.A_WEEK: "Evento em 1 semana!",
            ReminderTime.THREE_DAYS: "Evento em 3 dias!",
            ReminderTime.A_DAY: "Evento amanhã!",
            ReminderTime.A_HOUR: "Evento começando em 1 hora!"
        }

    async def format_to_discord_event(self, event: CommunityEvent) -> dict:
        # Convert from São Paulo time to UTC
        sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
        utc_tz = ZoneInfo('UTC')

        # Ensure the datetime objects have timezone info
        start_time_utc = event.start_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)
        end_time_utc = event.end_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)

        # Build event creation parameters
        event_params = {
            'name': event.title,
            'description': event.description,
            'start_time': start_time_utc,
            'end_time': end_time_utc,
            'privacy_level': discord.PrivacyLevel.guild_only,
            'entity_type': discord.EntityType.external,
            'location': event.discord_event_location()
        }

        image_bytes = await image_service.download_image_bytes(event.banner_url())
        if image_bytes:
            event_params['image'] = image_bytes

        return event_params

    def format_to_message(self, event: CommunityEvent) -> discord.Embed:
        event_description = f"***{self.notification_titles.get(event.reminder_time())}***\n\n{event.description}"

        # Create the embed
        embed = discord.Embed(
            title = f"📢 {event.title}",
            description = event_description,
            color = 0x2ecc71 # Green color
        )

        embed.add_field(
            name = "🇧🇷",
            value = f"*{event.brazil_datetime()}*",
            inline = True)

        embed.add_field(
            name = "🇨🇦",
            value = f"*{event.canada_datetime()}*",
            inline = True)

        embed.add_field(
            name = "🇵🇹",
            value = f"*{event.portugal_datetime()}*",
            inline = True)

        # Add registration link if available
        if event.registration_link:
            embed.add_field(
                name = "🔗 Participar",
                value = f"[Clique aqui para se inscrever]({event.registration_link})",
                inline = False)
        else:
            embed.add_field(
                name = "🔗 Participar",
                value = f"[Clique aqui para ver os detalhes do evento]({event.event_details_url()})",
                inline = False)

        embed.set_author(
            name = "Ver detalhes completos",
            url = event.event_details_url(),
            icon_url = "https://craftcodeclub.io/logo.png")

        banner_url = event.banner_url()
        if banner_url:
            embed.set_image(url = banner_url)

        return embed


# Global instance
event_formatter = EventMessageFormatter()
