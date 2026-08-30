"""Smoke tests for the Functions port.

No network and no Azure: the Discord REST transport and both DAOs are replaced
with in-memory fakes, so this runs anywhere with `python -m unittest`.

    python -m unittest discover -s tests -v
"""

import asyncio
import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
sys.path.insert(0, SRC)

os.environ.setdefault('DISCORD_API_TOKEN', 'test-token')
os.environ.setdefault('DISCORD_APPLICATION_ID', '999')
os.environ.setdefault('DISCORD_GUILD_ID', '777')
os.environ.setdefault('COMMUNITY_EVENTS_CHANNEL_ID', '111')
os.environ.setdefault('LOGS_CHANNEL_ID', '222')
os.environ.setdefault('SAY_HI_CHANNEL', '333')
os.environ.setdefault('AZURE_STORAGE_CONNECTION_STRING', 'UseDevelopmentStorage=true')
os.environ.setdefault('LOG_LEVEL', 'CRITICAL')

from nacl.signing import SigningKey  # noqa: E402

SIGNING_KEY = SigningKey.generate()
os.environ['DISCORD_PUBLIC_KEY'] = SIGNING_KEY.verify_key.encode().hex()

import azure.functions as func  # noqa: E402

import discord_api.rest as rest_module  # noqa: E402
from discord_api import interactions  # noqa: E402
from usescases.community_events.community_event import CommunityEvent  # noqa: E402

CALLS: list[tuple] = []


async def fake_request(self, method, route, *, json_body=None, params=None):
    CALLS.append((method, route, json_body, params))
    if route == '/guilds/777':
        return {'id': '777', 'name': 'C3', 'owner_id': '42',
                'approximate_member_count': 2, 'approximate_presence_count': 1}
    if route == '/guilds/777/roles':
        return [{'id': '777', 'name': '@everyone', 'permissions': '0', 'position': 0},
                {'id': '900', 'name': 'Admin', 'permissions': '8', 'position': 2},
                {'id': '901', 'name': 'Member', 'permissions': '0', 'position': 1}]
    if route == '/guilds/777/members':
        if params and params.get('after') == '0':
            return [{'user': {'id': '1', 'username': 'ana'}, 'roles': ['900'],
                     'joined_at': '2026-01-01T10:00:00.000000+00:00'},
                    {'user': {'id': '2', 'username': 'helper', 'bot': True}, 'roles': [],
                     'joined_at': '2026-01-01T10:05:00.000000+00:00'}]
        return []
    if route.startswith('/guilds/777/members/'):
        return {'user': {'id': '1', 'username': 'ana'}, 'roles': ['900']}
    if route == '/users/@me/channels':
        return {'id': 'dm-1'}
    if route.startswith('/guilds/777/scheduled-events'):
        return {'id': 'evt-1'}
    return {'id': 'msg-1', 'guild_id': '777'}


async def _aenter(self):
    return self


async def _aexit(self, *_):
    return None


rest_module.DiscordRest.request = fake_request
rest_module.DiscordRest.__aenter__ = _aenter
rest_module.DiscordRest.__aexit__ = _aexit


class FakeEventsDao:
    def __init__(self):
        self.events: dict[str, CommunityEvent] = {}

    def get_upcoming_events(self, now):
        return [e for e in self.events.values() if e.start_datetime > now]

    def get(self, event_id):
        return self.events.get(event_id)

    def upsert(self, event):
        self.events[event.id] = event

    def merge(self, event, values):
        stored = self.events.get(event.id)
        if stored is None:
            raise KeyError(event.id)
        for key, value in values.items():
            setattr(stored, key, value)

    def delete(self, event_id, _start):
        self.events.pop(event_id, None)


class FakeStateDao:
    def __init__(self):
        self.values: dict[str, str] = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


FAKE_EVENTS = FakeEventsDao()
FAKE_STATE = FakeStateDao()

import usescases.admin.event_links_command as event_links_command  # noqa: E402
import usescases.admin.events_command as events_command  # noqa: E402
import usescases.admin.info_command as info_command  # noqa: E402
import usescases.community_events.notify_task as notify_task  # noqa: E402
import usescases.community_events.sync_task as sync_task  # noqa: E402
import usescases.new_member.welcome_task as welcome_task  # noqa: E402

for module in (events_command, event_links_command, notify_task, sync_task):
    module.get_community_events_dao = lambda: FAKE_EVENTS
for module in (notify_task, sync_task, welcome_task):
    module.get_state_dao = lambda: FAKE_STATE
info_command.state_dao.get_state_dao = lambda: FAKE_STATE

import function_app  # noqa: E402
from router import HANDLERS, dispatch  # noqa: E402


def interaction(name, options=None, dm=False):
    payload = {'type': interactions.APPLICATION_COMMAND, 'token': 'tok',
               'data': {'name': name}, 'guild_id': None if dm else '777'}
    if options:
        payload['data']['options'] = [{'name': k, 'value': v} for k, v in options.items()]
    if dm:
        payload['user'] = {'id': '1', 'username': 'ana'}
    else:
        payload['member'] = {'user': {'id': '1', 'username': 'ana'}, 'permissions': '8'}
    return payload


class _QueueOut:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


def post_interaction(body: bytes, *, sign=True, timestamp=None):
    # Signatures carry a freshness window, so the timestamp has to be current.
    timestamp = timestamp or str(int(time.time()))
    signature = (SIGNING_KEY.sign(timestamp.encode() + body).signature.hex()
                 if sign else 'aa' * 64)
    request = func.HttpRequest(
        method='POST', url='/api/interactions', body=body,
        headers={'X-Signature-Ed25519': signature, 'X-Signature-Timestamp': timestamp})
    queue = _QueueOut()
    handler = function_app.discord_interactions.build().get_user_function()
    return handler(request, queue), queue


class InteractionsEndpointTests(unittest.TestCase):
    def test_all_triggers_are_indexed(self):
        names = {f.get_function_name() for f in function_app.app.get_functions()}
        self.assertEqual(names, {'interactions', 'discord_work', 'notify_upcoming_events',
                                 'sync_community_events', 'welcome_new_members'})

    def test_ping_is_answered_with_pong(self):
        response, queue = post_interaction(b'{"type":1}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {'type': interactions.PONG})
        self.assertIsNone(queue.value)

    def test_command_is_deferred_and_queued(self):
        body = json.dumps(interaction('version')).encode()
        response, queue = post_interaction(body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body())['type'],
                         interactions.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
        self.assertEqual(json.loads(queue.value)['data']['name'], 'version')

    def test_invalid_signature_is_rejected(self):
        response, queue = post_interaction(b'{"type":1}', sign=False)
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(queue.value)

    def test_malformed_body_is_rejected(self):
        response, _ = post_interaction(b'not json')
        self.assertEqual(response.status_code, 400)

    def test_replayed_request_is_rejected(self):
        stale = str(int(time.time()) - 3600)
        response, queue = post_interaction(b'{"type":1}', timestamp=stale)
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(queue.value)


class CommandTests(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        FAKE_EVENTS.events.clear()
        FAKE_STATE.values.clear()
        start = datetime.now() + timedelta(minutes=50)
        FAKE_EVENTS.upsert(CommunityEvent(id='ev1', title='Test Event', description='desc',
                                          start_datetime=start,
                                          end_datetime=start + timedelta(hours=2)))

    def _reply(self):
        answers = [c for c in CALLS if c[1].startswith('/webhooks/')]
        self.assertTrue(answers, 'the command never answered the deferred interaction')
        return answers[-1][2]

    def test_every_registered_command_has_a_handler(self):
        from commands_catalog import COMMANDS
        self.assertEqual({c['name'] for c in COMMANDS}, set(HANDLERS))

    def test_all_commands_answer(self):
        cases = [
            ('version', None), ('info', None), ('help', None), ('rules', None),
            ('events', None), ('event', {'event_id': 'ev1'}),
            ('event-add-session-link', {'event_id': 'ev1', 'session_link': 'https://a.example/s'}),
            ('event-add-recording-link', {'event_id': 'ev1', 'recording_link': 'https://a.example/r'}),
            ('server-status', None), ('add-role', {'role': '901', 'user': '3'}),
        ]
        for name, options in cases:
            with self.subTest(command=name):
                CALLS.clear()
                asyncio.run(dispatch(interaction(name, options)))
                self._reply()

    def test_dm_invocation_falls_back_to_a_rest_permission_check(self):
        asyncio.run(dispatch(interaction('version', dm=True)))
        self.assertTrue(any(c[1].startswith('/guilds/777/members/') for c in CALLS))

    def test_link_command_rejects_an_invalid_url(self):
        asyncio.run(dispatch(interaction('event-add-session-link',
                                         {'event_id': 'ev1', 'session_link': 'not a url'})))
        self.assertIn('Link inválido', self._reply()['content'])

    def test_link_command_requires_force_to_overwrite(self):
        FAKE_EVENTS.get('ev1').session_link = 'https://existing.example/s'
        asyncio.run(dispatch(interaction('event-add-session-link',
                                         {'event_id': 'ev1', 'session_link': 'https://new.example/s'})))
        self.assertIn('já tem um session link', self._reply()['content'])

    def test_admin_of_another_guild_is_not_trusted(self):
        """member.permissions describes the guild the interaction came from.

        An administrator of some other server the bot is in must not be able to
        run admin commands against the configured guild, so a foreign guild_id
        forces the REST permission lookup instead of trusting the payload.
        """
        foreign = interaction('add-role', {'role': '901', 'user': '3'})
        foreign['guild_id'] = '31337'
        foreign['member'] = {'user': {'id': '66', 'username': 'intruder'}, 'permissions': '8'}

        original_get_member = rest_module.DiscordRest.get_member

        async def not_a_member(self, guild_id, user_id):
            return None

        rest_module.DiscordRest.get_member = not_a_member
        try:
            asyncio.run(dispatch(foreign))
        finally:
            rest_module.DiscordRest.get_member = original_get_member

        self.assertIn('administradores', self._reply()['content'])
        self.assertEqual([c for c in CALLS if c[0] == 'PUT'], [])

    def test_unknown_command_is_reported(self):
        asyncio.run(dispatch(interaction('does-not-exist')))
        self.assertIn('desconhecido', self._reply()['content'])


class TimerTests(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        FAKE_EVENTS.events.clear()
        FAKE_STATE.values.clear()

    def test_notify_sends_once_and_then_stops(self):
        start = datetime.now() + timedelta(minutes=50)
        FAKE_EVENTS.upsert(CommunityEvent(id='ev1', title='Soon', description='d',
                                          start_datetime=start,
                                          end_datetime=start + timedelta(hours=1)))

        async def run_twice():
            async with rest_module.DiscordRest() as rest:
                await notify_task.run(rest)
                first = [c for c in CALLS if c[1] == '/channels/111/messages']
                CALLS.clear()
                await notify_task.run(rest)
                second = [c for c in CALLS if c[1] == '/channels/111/messages']
                return first, second

        first, second = asyncio.run(run_twice())
        self.assertEqual(len(first), 1, 'the reminder should be posted once')
        self.assertEqual(second, [], 'a second run must not repeat the reminder')
        self.assertTrue(FAKE_EVENTS.get('ev1').a_hour_notify)

    def test_first_welcome_run_only_sets_the_watermark(self):
        async def run():
            async with rest_module.DiscordRest() as rest:
                await welcome_task.run(rest)

        asyncio.run(run())
        self.assertTrue(FAKE_STATE.get('new_member_watermark'))
        self.assertEqual([c for c in CALLS if c[1] == '/users/@me/channels'], [])

    def test_second_welcome_run_greets_humans_only(self):
        FAKE_STATE.set('new_member_watermark', '2025-01-01T00:00:00+00:00')

        async def run():
            async with rest_module.DiscordRest() as rest:
                await welcome_task.run(rest)

        asyncio.run(run())
        dms = [c for c in CALLS if c[1] == '/users/@me/channels']
        self.assertEqual(len(dms), 1, 'the bot account must not be welcomed')


if __name__ == '__main__':
    unittest.main()
