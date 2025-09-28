import requests
import discord
from usescases.community_events.community_event import CommunityEvent, ReminderTime

class EventMessageFormatter:
    def __init__(self):
        self.notification_titles = {
            ReminderTime.A_WEEK: "Evento em 1 semana!",
            ReminderTime.THREE_DAYS: "Evento em 3 dias!",
            ReminderTime.A_DAY: "Evento amanhã!",
            ReminderTime.A_HOUR: "Evento começando em 1 hora!"
        }

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

        if event.banner:
            banner_url = f"https://raw.githubusercontent.com/craft-code-club/blog-c3/refs/heads/main/public/events/{event.banner}"
            # Validate if banner URL exists before setting image
            try:
                response = requests.head(banner_url, timeout=5)
                if response.status_code == 200:
                    embed.set_image(url = banner_url)
            except requests.RequestException:
                pass

        return embed


# Global instance
event_formatter = EventMessageFormatter()
