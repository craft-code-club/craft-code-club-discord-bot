"""Register the bot's slash commands with Discord.

Run once after changing `src/commands_catalog.py` (and once when first setting
the bot up). The call is a bulk overwrite - the array sent replaces the whole
command set - so it is idempotent and safe to re-run.

    DISCORD_APPLICATION_ID=... DISCORD_API_TOKEN=... \
    DISCORD_GUILD_ID=...  python scripts/register_commands.py

With DISCORD_GUILD_ID set the commands are registered for that guild and are
available immediately; without it they are registered globally, which Discord
rolls out with a version check that can make the first invocation after a
change bounce once.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from commands_catalog import to_discord_payload  # noqa: E402

API_BASE = 'https://discord.com/api/v10'


def main() -> int:
    application_id = os.environ.get('DISCORD_APPLICATION_ID', '').strip()
    token = os.environ.get('DISCORD_API_TOKEN', '').strip()
    guild_id = os.environ.get('DISCORD_GUILD_ID', '').strip()

    if not application_id or not token:
        print('DISCORD_APPLICATION_ID and DISCORD_API_TOKEN are required.', file=sys.stderr)
        return 1

    path = (f'/applications/{application_id}/guilds/{guild_id}/commands' if guild_id
            else f'/applications/{application_id}/commands')

    payload = to_discord_payload()
    request = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode('utf-8'),
        method='PUT',
        headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json'},
    )

    try:
        with urllib.request.urlopen(request) as response:
            registered = json.load(response)
    except urllib.error.HTTPError as error:
        print(f'Registration failed: HTTP {error.code}\n{error.read().decode("utf-8", "replace")}',
              file=sys.stderr)
        return 1

    scope = f'guild {guild_id}' if guild_id else 'globally'
    print(f'Registered {len(registered)} command(s) {scope}:')
    for command in sorted(registered, key=lambda c: c['name']):
        print(f'  /{command["name"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
