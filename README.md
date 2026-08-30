# Craft & Code Club - Discord Bot

A Discord bot for the Craft & Code Club community, running as an **Azure Functions** app:
HTTP-triggered slash commands plus timer-triggered background jobs, on top of the Azure Table
Storage the bot already used.

## Features

- **Welcome Messages**: Greets new members with custom messages
- **Rules Command**: Display server rules and guidelines
- **Community Events**: Manage and notify about community events

## How it works

| Trigger | Schedule | What it does |
|---|---|---|
| `interactions` (HTTP) | on demand | Verifies Discord's Ed25519 signature, acknowledges within the 3-second deadline and queues the work |
| `discord_work` (Queue) | on demand | Runs the slash command and edits the deferred reply |
| `notify_upcoming_events` (Timer) | every 15 min | Posts event reminders (1 week / 3 days / 1 day / 1 hour) |
| `sync_community_events` (Timer) | every 3 h | Syncs craftcodeclub.io events into Table Storage and Discord scheduled events |
| `welcome_new_members` (Timer) | every 5 min | Greets members who joined since the last run |

Discord delivers slash commands over HTTP, but member joins and chat messages only over a gateway
websocket — which is why the welcome flow polls and why the commands are real slash commands.
[`docs/Architecture.md`](./docs/Architecture.md) explains the constraints and the trade-offs.

## Commands

| Command | Who | What |
|---|---|---|
| `/rules` | everyone | DMs the server rules |
| `/help` | everyone | Lists the available commands |
| `/version` | admins | Deployed version |
| `/info` | admins | Version and the last run of each scheduled job |
| `/events` | admins | Upcoming events |
| `/event <event_id>` | admins | Full detail for one event |
| `/event-add-session-link <event_id> <session_link> [force]` | admins | Set an event's session link |
| `/event-add-recording-link <event_id> <recording_link> [force]` | admins | Set an event's recording link |
| `/add-role <role> [user] [everyone]` | admins | Grant a role to one member or to everyone |
| `/server-status` | admins | Membership statistics |

The command set lives in [`src/commands_catalog.py`](./src/commands_catalog.py) and is registered
with `scripts/register_commands.py`.

## Setup

* [Create an application in Discord](./docs/CreateDiscordBot.md) — enable the **Server Members**
  privileged intent; `Message Content` and `Presence` are no longer needed
* [Setup Python environment](./docs/PythonEnvironment.md)
* [Configure environment variables](#configure-environment-variables)
* [Provision the infrastructure](./infra/README.md)

## Configure environment variables

The Functions host reads `src/local.settings.json` locally and app settings in Azure.

```bash
./init-env.sh          # creates .venv, installs src/requirements.txt and seeds local.settings.json
```

Then fill in `src/local.settings.json` (see [`.env.example`](./.env.example) for what each value
means). `DISCORD_GUILD_ID` is new: with no gateway connection there is no guild cache, so the
server the bot operates on is configured explicitly.

## Run it locally

```bash
docker compose up -d azurite     # storage emulator (blob + queue + table)
cd src && func start             # requires the Azure Functions Core Tools
```

```bash
python -m unittest discover -s tests -v
```

## Register the slash commands

```bash
DISCORD_APPLICATION_ID=... DISCORD_API_TOKEN=... DISCORD_GUILD_ID=... \
  python scripts/register_commands.py
```

The call is a bulk overwrite, so it is idempotent. CI re-runs it on every release.

## References
- [Discord Bot Documentation](https://discord.com/developers/docs/intro)
- [Receiving and Responding to Interactions](https://discord.com/developers/docs/interactions/receiving-and-responding)
- [Azure Functions Flex Consumption](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan)
