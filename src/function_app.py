"""Azure Functions entry point - the whole bot, as triggers.

  interactions            HTTP   POST /api/interactions   Discord slash commands
  discord_work            Queue  discord-work             does the slow half of a command
  notify_upcoming_events  Timer  every 15 minutes         event reminders
  sync_community_events   Timer  every 3 hours            craftcodeclub.io -> storage + Discord
  welcome_new_members     Timer  every 5 minutes          greets members who just joined

WHY THE HTTP TRIGGER IS SO SMALL
Discord invalidates an interaction if the initial response takes longer than
3 seconds, and a deferred response does not help: the acknowledgement itself
still has to make that deadline. So this module keeps its import graph to
`azure.functions` plus PyNaCl, verifies the Ed25519 signature, hands the
payload to a Storage queue and acknowledges. Everything heavy - aiohttp,
azure-data-tables, the command handlers - is imported inside the queue and
timer functions, which have no such deadline.

Background work after responding is deliberately NOT used: the Functions host
treats an invocation as finished when the handler returns and may recycle the
worker immediately, so a fire-and-forget task can be dropped silently. The
queue is the durable equivalent.
"""

import json
import logging

import azure.functions as func

from discord_api import interactions
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = func.FunctionApp()

QUEUE_NAME = 'discord-work'
STORAGE_CONNECTION = 'AzureWebJobsStorage'


# ----------------------------------------------------------------------
# HTTP: Discord interactions endpoint
# ----------------------------------------------------------------------
@app.function_name(name='interactions')
@app.route(route='interactions', methods=['POST'], auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name='work', queue_name=QUEUE_NAME, connection=STORAGE_CONNECTION)
def discord_interactions(req: func.HttpRequest, work: func.Out[str]) -> func.HttpResponse:
    # Synchronous on purpose: no event loop to start on the 3-second hot path.
    body = req.get_body()
    signature = req.headers.get('X-Signature-Ed25519')
    timestamp = req.headers.get('X-Signature-Timestamp')

    if not interactions.verify_signature(body, signature, timestamp):
        # Discord probes this endpoint with deliberately invalid signatures and
        # removes the Interactions Endpoint URL of apps that accept them.
        return func.HttpResponse('invalid request signature', status_code=401)

    try:
        interaction = json.loads(body)
    except ValueError:
        return func.HttpResponse('invalid payload', status_code=400)

    interaction_type = interaction.get('type')

    if interaction_type == interactions.PING:
        return _json(interactions.pong())

    if interaction_type == interactions.APPLICATION_COMMAND_AUTOCOMPLETE:
        # No command registers autocomplete yet, but a type-4 reply here would be
        # an invalid callback type rather than a harmless one.
        return _json(interactions.empty_autocomplete())

    if interaction_type != interactions.APPLICATION_COMMAND:
        logger.info('[INTERACTIONS] Ignoring unsupported interaction type %s', interaction_type)
        return _json(interactions.message('❌ Tipo de interação não suportado.'))

    work.set(json.dumps(interaction))
    logger.info('[INTERACTIONS] Queued "%s" from "%s"',
                interactions.command_name(interaction), interactions.user_name(interaction))
    return _json(interactions.defer())


def _json(payload: dict) -> func.HttpResponse:
    return func.HttpResponse(interactions.to_json_bytes(payload),
                             status_code=200, mimetype='application/json')


# ----------------------------------------------------------------------
# Queue: the slow half of a slash command
# ----------------------------------------------------------------------
@app.function_name(name='discord_work')
@app.queue_trigger(arg_name='msg', queue_name=QUEUE_NAME, connection=STORAGE_CONNECTION)
async def discord_work(msg: func.QueueMessage) -> None:
    # Imported here, not at module scope, to keep the HTTP trigger's imports light.
    from discord_api.rest import DiscordRest
    from router import dispatch
    from utils import reporting

    reporting.install_collector()
    interaction = json.loads(msg.get_body().decode('utf-8'))
    logger.info('[WORKER] Handling "%s" (dequeue count %s)',
                interaction.get('data', {}).get('name'), msg.dequeue_count)
    try:
        await dispatch(interaction)
    finally:
        async with DiscordRest() as rest:
            await reporting.flush(rest)


# ----------------------------------------------------------------------
# Timers
# ----------------------------------------------------------------------
@app.function_name(name='notify_upcoming_events')
@app.timer_trigger(arg_name='timer', schedule='0 */15 * * * *', run_on_startup=False)
async def notify_upcoming_events(timer: func.TimerRequest) -> None:
    from discord_api.rest import DiscordRest
    from utils import reporting
    from usescases.community_events import notify_task

    reporting.install_collector()
    logger.debug('[TIMER][NOTIFY] Started (past due: %s)', timer.past_due)
    async with DiscordRest() as rest:
        try:
            await notify_task.run(rest)
        finally:
            await reporting.flush(rest)


@app.function_name(name='sync_community_events')
@app.timer_trigger(arg_name='timer', schedule='0 0 */3 * * *', run_on_startup=False)
async def sync_community_events(timer: func.TimerRequest) -> None:
    from discord_api.rest import DiscordRest
    from utils import reporting
    from usescases.community_events import sync_task

    reporting.install_collector()
    logger.debug('[TIMER][SYNC] Started (past due: %s)', timer.past_due)
    async with DiscordRest() as rest:
        try:
            await sync_task.run(rest)
        finally:
            await reporting.flush(rest)


@app.function_name(name='welcome_new_members')
@app.timer_trigger(arg_name='timer', schedule='0 */5 * * * *', run_on_startup=False)
async def welcome_new_members(timer: func.TimerRequest) -> None:
    from discord_api.rest import DiscordRest
    from utils import reporting
    from usescases.new_member import welcome_task

    reporting.install_collector()
    logger.debug('[TIMER][WELCOME] Started (past due: %s)', timer.past_due)
    async with DiscordRest() as rest:
        try:
            await welcome_task.run(rest)
        finally:
            await reporting.flush(rest)
