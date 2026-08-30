"""Post upcoming-event reminders. Runs on a timer trigger every 15 minutes.

Ported from the `@tasks.loop(minutes=15)` cog. The schedule now lives in the
function's NCRONTAB expression instead of in a loop that only ticks while a
process happens to be alive.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from discord_api.rest import DiscordRest, everyone_mention, no_mentions
from usescases.community_events.community_event import CommunityEvent, ReminderTime
from usescases.community_events.community_events_dao import get_community_events_dao
from utils.state_dao import LAST_NOTIFY_KEY, get_state_dao
from usescases.community_events.community_event_formatter import event_formatter
from utils import config
from utils.reporting import report
from utils.timezones import get_brazil_timezone

logger = logging.getLogger(__name__)

# Which flag on the event records that a given reminder has already been sent.
_NOTIFY_FLAGS = {
    ReminderTime.A_HOUR: 'a_hour_notify',
    ReminderTime.A_DAY: 'a_day_notify',
    ReminderTime.THREE_DAYS: 'three_days_notify',
    ReminderTime.A_WEEK: 'a_weekly_notify',
}


async def run(rest: DiscordRest, now: Optional[datetime] = None) -> None:
    """Check for due reminders.

    `now` is injectable so the 8am gate and the reminder windows can be tested
    without depending on the host clock or timezone; the timer trigger always
    uses the real São Paulo time.
    """
    get_state_dao().set(LAST_NOTIFY_KEY, datetime.now(timezone.utc).isoformat(timespec='seconds'))

    channel_id = config.community_events_channel_id()
    if not channel_id:
        logger.warning('[TASK][COMMUNITY EVENTS][NOTIFY] COMMUNITY_EVENTS_CHANNEL_ID is not set. Skipping.')
        return

    now = now or datetime.now(get_brazil_timezone())

    # only send notifications after 8am
    if now.hour < 8:
        logger.debug('[TASK][COMMUNITY EVENTS][NOTIFY] Not sending notifications before 8am '
                     '(São Paulo Time) - current hour: %s', now.strftime('%Y-%m-%d %H:%M:%S'))
        return

    dao = get_community_events_dao()
    # RowKeys are naive São Paulo timestamps, so compare against a naive "now".
    upcoming_events = dao.get_upcoming_events(now.replace(tzinfo=None))
    logger.debug('[TASK][COMMUNITY EVENTS][NOTIFY] Found %s upcoming events to check for notifications',
                 len(upcoming_events))

    for event in upcoming_events:
        reminder_time = event.reminder_time(now)
        if not reminder_time:
            logger.debug('[TASK][COMMUNITY EVENTS][NOTIFY] The event: "%s" is not in a timewindow for notification',
                         event.title)
            continue

        flag = _NOTIFY_FLAGS[reminder_time]
        if getattr(event, flag):
            logger.debug('[TASK][COMMUNITY EVENTS][NOTIFY] The event: "%s" already had the "%s" notification sent',
                         event.title, reminder_time.name)
            continue

        await _notify(rest, dao, event, reminder_time, flag, channel_id)
        # One notification per run, matching the original loop.
        break


async def _notify(rest: DiscordRest, dao, event: CommunityEvent, reminder_time: ReminderTime,
                  flag: str, channel_id: int) -> None:
    logger.debug('[TASK][COMMUNITY EVENTS][NOTIFY] The event: "%s" will now notify %s in advance',
                 event.title, reminder_time.name)

    # Claim the reminder BEFORE sending. A timer run that crashes between the
    # send and the write would otherwise re-send on the next tick - and the
    # 1-hour reminder carries an @everyone ping, so a duplicate is much worse
    # than a missed one. The write merges only this flag, so it cannot undo a
    # link the 3-hour sync wrote in the meantime.
    setattr(event, flag, True)
    dao.merge(event, {flag: True})

    embed = event_formatter.format_to_message(event, reminder_time)
    if reminder_time == ReminderTime.A_HOUR:
        content = '@everyone'
        allowed_mentions = everyone_mention()
    else:
        content = None
        allowed_mentions = no_mentions()

    try:
        await rest.send_message(channel_id, content=content, embed=embed,
                                allowed_mentions=allowed_mentions)
    except Exception as error:  # noqa: BLE001 - the flag is already persisted
        logger.exception('[TASK][COMMUNITY EVENTS][NOTIFY] Failed to send the "%s" reminder for "%s"',
                         reminder_time.name, event.title)
        await report(rest, f'[COMMUNITY EVENTS][NOTIFY] Reminder "{reminder_time.name}" for '
                           f'"{event.title}" was marked as sent but the message failed: {error}')
        return

    logger.info('[TASK][COMMUNITY EVENTS][NOTIFY] Notifying event: "%s" at %s - Reminder: %s',
                event.title, event.start_datetime, reminder_time.name)
