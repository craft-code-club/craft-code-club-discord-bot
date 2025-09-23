import os
import logging
from discord.ext import tasks, commands
from usescases.community_events.community_events_dao import community_events_dao
from usescases.community_events.community_event import CommunityEventSummary, ReminderTime
from usescases.community_events.github_service import github_service
from usescases.community_events.community_event_formatter import event_formatter
from datetime import datetime
from zoneinfo import ZoneInfo


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



    @tasks.loop(hours=1)
    async def notify_upcoming_events(self):
        try:
            channel = self.bot.get_channel(self.community_events_channel_id)
            if channel is None:
                raise ValueError(f'Could not find channel with ID {self.community_events_channel_id}')

            time_zone = ZoneInfo('America/Sao_Paulo')
            now = datetime.now(time_zone)

            # only send notifications after 8am
            if now.hour < 8:
                return

            logger.debug('[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Notifying upcoming events...')

            upcoming_events = community_events_dao.get_upcoming_events(now)

            for event in upcoming_events:
                event_summary = CommunityEventSummary.create(event)

                reminder_time = event_summary.reminder_time()
                if not reminder_time:
                    continue

                if reminder_time == ReminderTime.A_HOUR:
                    if event.a_hour_notify:
                        continue
                    event.a_hour_notify = True

                elif reminder_time == ReminderTime.A_DAY:
                    if event.a_day_notify:
                        continue
                    event.a_day_notify = True

                elif reminder_time == ReminderTime.THREE_DAYS:
                    if event.three_days_notify:
                        continue
                    event.three_days_notify = True

                elif reminder_time == ReminderTime.A_WEEK:
                    if event.a_weekly_notify:
                        continue
                    event.a_weekly_notify = True

                embed = event_formatter.format_event_notification(event_summary)
                await channel.send(embed=embed)

                community_events_dao.update(event)

                logger.info(f'[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Notifying event: {event_summary.title} at {event_summary.start_datetime}')
                break

        except Exception:
            logger.exception('[BOT][TASK][COMMUNITY EVENTS][NOTIFY] Error in notify task:')

    @tasks.loop(hours=3) # Every 3 hours
    async def update_community_events_task(self):
        try:
            logger.debug('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Updating community events...')

            events = await github_service.fetch_community_events()

            for name, url in events.items():
                try:
                    event = await github_service.fetch_community_event(url)
                    event_summary = CommunityEventSummary.create(event)

                    if not event_summary.is_future_event():
                        continue

                    community_events_dao.upsert(event_summary)

                    logger.info(f'[BOT][TASK][COMMUNITY EVENTS][UPDATE] upserted event {name} from {url}')
                except Exception:
                    logger.exception(f'[BOT][TASK][COMMUNITY EVENTS][UPDATE] Failed to process event {name} from {url}')

            logger.info('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Updated community events finished successfully.')
        except Exception:
            logger.exception('[BOT][TASK][COMMUNITY EVENTS][UPDATE] Error in update task:')


    @notify_upcoming_events.before_loop
    async def before_notify_upcoming_events(self):
        await self.bot.wait_until_ready()
        logger.debug('[BOT][TASK][COMMUNITY EVENTS] Community events task is ready!')
