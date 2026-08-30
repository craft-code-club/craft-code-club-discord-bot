"""HTTP interactions: request verification, response building, option parsing.

Discord delivers slash commands to an application in exactly one of two ways -
the INTERACTION_CREATE gateway event, or an HTTP POST to the app's Interactions
Endpoint URL - and the docs state the two are mutually exclusive. This module
implements the HTTP side, which is what lets the bot run on Azure Functions.

Deliberately dependency-light: only PyNaCl and the standard library. The HTTP
trigger imports this module on the 3-second-deadline hot path, so nothing here
may pull in aiohttp, azure-data-tables or any other heavy package.
"""

import json
import os
import time
from typing import Any, Optional

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

# Interaction types (Discord: Receiving and Responding).
PING = 1
APPLICATION_COMMAND = 2
MESSAGE_COMPONENT = 3
APPLICATION_COMMAND_AUTOCOMPLETE = 4
MODAL_SUBMIT = 5

# Interaction callback types.
PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4
DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5

# Message flags.
EPHEMERAL = 1 << 6
APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8

# Reject signed requests older than this. Discord's signature covers the
# timestamp, so without a freshness check a captured request could be replayed
# forever, and every replay would re-run the command's side effects.
MAX_SIGNATURE_AGE_SECONDS = 300

# Interaction context types, used when registering commands.
CONTEXT_GUILD = 0
CONTEXT_BOT_DM = 1
CONTEXT_PRIVATE_CHANNEL = 2

_verify_key: Optional[VerifyKey] = None


def _get_verify_key() -> VerifyKey:
    """Build the Ed25519 verify key once per worker process."""
    global _verify_key
    if _verify_key is None:
        public_key = os.environ.get('DISCORD_PUBLIC_KEY', '')
        if not public_key:
            raise RuntimeError('DISCORD_PUBLIC_KEY is not set')
        _verify_key = VerifyKey(bytes.fromhex(public_key))
    return _verify_key


def verify_signature(body: bytes, signature: Optional[str], timestamp: Optional[str]) -> bool:
    """Verify the Ed25519 signature Discord sends with every interaction.

    The signed message is the raw timestamp header concatenated with the raw
    request body - never a re-serialised copy of the parsed JSON, because any
    whitespace or key-order change invalidates the signature.

    Discord periodically probes endpoints with deliberately invalid signatures
    and removes the Interactions Endpoint URL of any app that accepts them, so
    a failure here must produce HTTP 401.
    """
    if not signature or not timestamp:
        return False

    try:
        age = abs(time.time() - float(timestamp))
    except ValueError:
        return False
    if age > MAX_SIGNATURE_AGE_SECONDS:
        return False

    try:
        _get_verify_key().verify(timestamp.encode() + body, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError):
        # ValueError covers a malformed hex signature header.
        return False


# ----------------------------------------------------------------------
# response builders
# ----------------------------------------------------------------------
def pong() -> dict:
    """Answer the PING (type 1) handshake Discord sends when saving the URL."""
    return {'type': PONG}


def message(content: str, *, ephemeral: bool = True) -> dict:
    """Immediate reply, for handlers that need no I/O and fit inside 3 seconds."""
    data: dict[str, Any] = {'content': content, 'allowed_mentions': {'parse': []}}
    if ephemeral:
        data['flags'] = EPHEMERAL
    return {'type': CHANNEL_MESSAGE_WITH_SOURCE, 'data': data}


def embed_message(embed: dict, *, ephemeral: bool = True) -> dict:
    data: dict[str, Any] = {'embeds': [embed], 'allowed_mentions': {'parse': []}}
    if ephemeral:
        data['flags'] = EPHEMERAL
    return {'type': CHANNEL_MESSAGE_WITH_SOURCE, 'data': data}


def empty_autocomplete() -> dict:
    """Autocomplete needs its own callback type; a type-4 reply is invalid."""
    return {'type': APPLICATION_COMMAND_AUTOCOMPLETE_RESULT, 'data': {'choices': []}}


def defer(*, ephemeral: bool = True) -> dict:
    """Acknowledge now, answer later.

    Discord shows "thinking..." and keeps the interaction token valid for 15
    minutes, which is what lets slow work move to a queue-triggered function.
    Note the ACK itself still has to leave the endpoint within 3 seconds - a
    deferral buys time *after* the acknowledgement, never before it.
    """
    data: dict[str, Any] = {}
    if ephemeral:
        data['flags'] = EPHEMERAL
    return {'type': DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE, 'data': data}


# ----------------------------------------------------------------------
# payload accessors
# ----------------------------------------------------------------------
def command_name(interaction: dict) -> str:
    return interaction.get('data', {}).get('name', '')


def options(interaction: dict) -> dict[str, Any]:
    """Flatten the command's options into a {name: value} dict."""
    return {opt['name']: opt.get('value') for opt in interaction.get('data', {}).get('options', [])}


def invoking_user(interaction: dict) -> dict:
    """The user who ran the command, whether in a guild or in a DM.

    Guild interactions carry `member.user`; DM interactions carry `user`.
    """
    member = interaction.get('member')
    if member and 'user' in member:
        return member['user']
    return interaction.get('user', {})


def user_id(interaction: dict) -> str:
    return str(invoking_user(interaction).get('id', ''))


def user_name(interaction: dict) -> str:
    user = invoking_user(interaction)
    return user.get('global_name') or user.get('username', 'unknown')


def guild_id(interaction: dict) -> Optional[str]:
    value = interaction.get('guild_id')
    return str(value) if value else None


def member_permissions(interaction: dict) -> Optional[int]:
    """The precomputed permission bitfield Discord sends for guild interactions.

    Absent in DMs - there is no guild context there, so a DM invocation has to
    fall back to a REST permission lookup.
    """
    member = interaction.get('member') or {}
    permissions = member.get('permissions')
    return int(permissions) if permissions is not None else None


def resolved_member(interaction: dict, user_id_value: str) -> Optional[dict]:
    """A member object Discord resolved for a USER-typed command option."""
    members = interaction.get('data', {}).get('resolved', {}).get('members', {})
    return members.get(str(user_id_value))


def to_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(',', ':')).encode('utf-8')
