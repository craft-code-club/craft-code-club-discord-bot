import os
import logging
from typing import Optional
from discord.ext import tasks, commands
from usescases.community_events.community_events_dao import community_events_dao
from usescases.community_events.community_event import CommunityEvent, ReminderTime
from usescases.community_events.github_service import github_service
from usescases.community_events.community_event_formatter import event_formatter
from datetime import datetime
from zoneinfo import ZoneInfo
import discord


logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(CommunityEventsTaskBot(bot))


class CommunityEventsTaskBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.community_events_channel_id = int(os.environ.get('COMMUNITY_EVENTS_CHANNEL_ID', '0'))

        if not self.community_events_channel_id:
            logger.warning('[BOT][TASK][COMMUNITY EVENTS] COMMUNITY_EVENTS_CHANNEL_ID is not set. Daily task will not run.')
            return

        self.update_community_events_task.start()
        self.notify_upcoming_events.start()


    def cog_unload(self):
        self.update_community_events_task.cancel()
        self.notify_upcoming_events.cancel()


    @tasks.loop(minutes=15) # Every 15 minutes
    async def notify_upcoming_events(self):
        try:
            logger.debug('[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Notifying upcoming events...')

            channel = self.bot.get_channel(self.community_events_channel_id)
            if channel is None:
                raise ValueError(f'Could not find channel with Id "{self.community_events_channel_id}"')

            time_zone = ZoneInfo('America/Sao_Paulo')
            now = datetime.now(time_zone)

            # only send notifications after 8am
            if now.hour < 8:
                logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Not sending notifications before 8am (São Paulo Time) - current hour: {now.strftime("%Y-%m-%d %H:%M:%S")}')
                return

            upcoming_events = community_events_dao.get_upcoming_events(now)

            logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Found {len(upcoming_events)} upcoming events to check for notifications')

            for event in upcoming_events:
                reminder_time = event.reminder_time()
                if not reminder_time:
                    logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" is not in a timewindow for notification')
                    continue

                if reminder_time == ReminderTime.A_HOUR:
                    if event.a_hour_notify:
                        logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" already had the "{reminder_time.name}" notification sent')
                        continue
                    event.a_hour_notify = True

                elif reminder_time == ReminderTime.A_DAY:
                    if event.a_day_notify:
                        logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" already had the "{reminder_time.name}" notification sent')
                        continue
                    event.a_day_notify = True

                elif reminder_time == ReminderTime.THREE_DAYS:
                    if event.three_days_notify:
                        logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" already had the "{reminder_time.name}" notification sent')
                        continue
                    event.three_days_notify = True

                elif reminder_time == ReminderTime.A_WEEK:
                    if event.a_weekly_notify:
                        logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" already had the "{reminder_time.name}" notification sent')
                        continue
                    event.a_weekly_notify = True

                logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] The event: "{event.title}" will now notify {reminder_time.name} in advance')

                embed = event_formatter.format_to_message(event)
                await channel.send(embed=embed)

                community_events_dao.update(event)

                logger.info(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Notifying event: "{event.title}" at {event.start_datetime} - Reminder: {reminder_time.name}')
                break

        except Exception:
            logger.exception('[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Error in notify task')

    @tasks.loop(hours=3) # Every 3 hours
    async def update_community_events_task(self):
        try:
            logger.debug('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Updating community events...')
            events = await github_service.fetch_community_events()

            for name, url in events.items():
                try:
                    event = await github_service.fetch_community_event(url)

                    if not event.is_future_event():
                        continue

                    existing_event = community_events_dao.get(event.id)
                    if existing_event:
                        if existing_event.start_datetime == event.start_datetime:
                            event.discord_event_id = existing_event.discord_event_id
                        else:
                            # Delete the old Discord event if it exists
                            if existing_event.discord_event_id:
                                await self.__delete_discord_event(existing_event.discord_event_id)
                            community_events_dao.delete(existing_event.id, existing_event.start_datetime)

                    if not event.discord_event_id:
                        event.discord_event_id = await self.__create_discord_event(event)

                    community_events_dao.upsert(event)

                    logger.info(f'[BOT][TASK][COMMUNITY EVENTS][UPDATE] upserted event "{name}" from "{url}"')
                except Exception:
                    logger.exception(f'[BOT][TASK][COMMUNITY EVENTS][UPDATE] Failed to process event "{name}" from "{url}"')

            logger.debug('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Updated community events finished successfully.')
        except Exception:
            logger.exception('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Error in update task')


    @notify_upcoming_events.before_loop
    async def before_notify_upcoming_events(self):
        await self.bot.wait_until_ready()
        logger.debug('[BOT][TASK][COMMUNITY EVENTS] Community events task is ready!')


    async def __create_discord_event(self, event: CommunityEvent) -> Optional[str]:
        try:
            logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Creating discord event for "{event.title}"')

            channel = self.bot.get_channel(self.community_events_channel_id)
            if channel is None:
                raise ValueError(f'Could not find channel with Id "{self.community_events_channel_id}"')

            guild = channel.guild

            # Convert from São Paulo time to UTC
            sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
            utc_tz = ZoneInfo('UTC')

            # Ensure the datetime objects have timezone info
            start_time_utc = event.start_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)
            end_time_utc = event.end_datetime.replace(tzinfo=sao_paulo_tz).astimezone(utc_tz)

            discord_event = await guild.create_scheduled_event(
                name = event.title,
                description = event.description,
                start_time = start_time_utc,
                end_time = end_time_utc,
                privacy_level = discord.PrivacyLevel.guild_only,
                entity_type = discord.EntityType.external,
                location = event.discord_event_location())

            logger.info(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Created discord event for "{event.title}" with Id "{discord_event.id}"')

            return str(discord_event.id)
        except Exception:
            logger.exception(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Failed to create discord event for "{event.title}"')
            return None


    async def __delete_discord_event(self, discord_event_id: str) -> None:
        try:
            logger.debug(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Deleting discord event Id "{discord_event_id}"')

            channel = self.bot.get_channel(self.community_events_channel_id)
            if channel is None:
                raise ValueError(f'Could not find channel with Id "{self.community_events_channel_id}"')

            guild = channel.guild
            discord_event = await guild.fetch_scheduled_event(int(discord_event_id))
            if discord_event:
                await discord_event.delete()
                logger.info(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Deleted discord event Id "{discord_event_id}"')
        except Exception:
            logger.exception(f'[BOT][TASK][COMMUNITY EVENTS][DISCORD] Failed to delete discord event Id "{discord_event_id}"')
