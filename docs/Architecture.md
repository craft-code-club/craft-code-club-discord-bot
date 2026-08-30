# Architecture — why the bot runs on Azure Functions

The bot used to be a single long-lived Python process holding a Discord **gateway** websocket,
running 24/7 in an Azure Container App. This document records what that cost, what Discord's docs
actually allow, and how the code is laid out now.

## The cost problem

Azure Container Apps' Consumption plan gives every subscription a free grant of **180,000
vCPU-seconds + 360,000 GiB-seconds** per calendar month. The bot's replica was the smallest shape
available (0.25 vCPU / 0.5 GiB), and at that shape the grant buys:

```
180,000 vCPU-s ÷ 0.25 vCPU = 720,000 s = 200 hours
360,000 GiB-s  ÷ 0.5 GiB   = 720,000 s = 200 hours
```

A month is ~730 hours, so an always-on replica is billable for ~73% of it *by construction* — there
is no configuration that makes it free. Most of that time bills at the reduced **idle** rate
(a replica using under 0.01 vCPU with no ingress qualifies), which is a 8× discount on vCPU but
**no discount on memory** — the idle and active memory rates are identical. The grant is also
**per subscription**, so any other Container App in the same subscription competes for it.

Azure Functions' Flex Consumption plan grants **250,000 executions + 100,000 GB-s** per
subscription per month, on-demand only. This bot's schedule needs roughly:

| Trigger | Runs/month | ~GB-s at 512 MB |
|---|---:|---:|
| `notify_upcoming_events` (15 min) | 2,920 | ~2,900 |
| `welcome_new_members` (5 min) | 8,760 | ~8,800 |
| `sync_community_events` (3 h) | 240 | ~1,700 |
| interactions + queue worker | a few hundred | ~500 |

That is well under both limits, and there are **no always-ready instances** — Microsoft is explicit
that "In always ready billing, there are no free grants", so enabling one would make every
execution billable from the first unit.

## What Discord does and does not allow

Two constraints from the Discord developer docs decide the whole design.

**1. Slash commands can arrive over HTTP; chat messages cannot.**
An application receives interactions either through the `INTERACTION_CREATE` gateway event *or*
through an **Interactions Endpoint URL** — the docs state the two are mutually exclusive. The
interaction type enum is closed (PING, APPLICATION_COMMAND, MESSAGE_COMPONENT, AUTOCOMPLETE,
MODAL_SUBMIT). A user typing `/rules` as *text* produces a `MESSAGE_CREATE` gateway event, which is
not an interaction and has no HTTP delivery path at all.

The old commands were `discord.py` **prefix commands** (`command_prefix=when_mentioned_or('/')`) —
the bot was reading chat messages, not receiving interactions. They are now registered
**application (slash) commands**, which is what makes them deliverable over HTTP.

**2. Member joins are gateway-only.**
`GUILD_MEMBER_ADD` is a gateway event. Discord's Webhook Events feature delivers a fixed list of
event types — authorization, entitlement and Social SDK events — and no member-join signal; the
audit log has no join action either. The welcome flow is therefore a **poller**: every 5 minutes the
bot pages `GET /guilds/{id}/members`, compares each `joined_at` against a watermark in Table
Storage, and greets whoever is new. (`after` pages by user snowflake, which encodes *account
creation* time, not join time, so there is no "joined since X" shortcut — the full list is scanned.)

Everything else the bot does — sending messages and DMs, creating and deleting guild scheduled
events, assigning roles, reading members and roles — is a plain REST call that never needed a
gateway.

### What changed for users

| Before | After |
|---|---|
| `/rules` typed as a message in a channel or DM | `/rules` as a real slash command, with autocompletion in the client |
| Welcome message ~10 s after joining | Welcome message within ~5 minutes of joining |
| `/server-status` exact online count | Discord's `approximate_presence_count` — per-member presence has no REST equivalent |
| `/info` process uptime | Last successful run of each scheduled job |
| `/add-role @all` | `/add-role` with an `everyone` option |
| `-f` flag parsed out of message text | A typed `force` boolean option |

Privileged intents: `MESSAGE_CONTENT` and `GUILD_PRESENCES` are no longer needed and can be turned
off in the Developer Portal. **`GUILD_MEMBERS` must stay on** — `GET /guilds/{id}/members` requires
it even with no gateway connection.

## Layout

```
src/
  function_app.py          all five triggers, and nothing else
  router.py                interaction name -> handler
  commands_catalog.py      the command set: registration payload + /help, one source
  host.json                queue tuning, function timeout
  discord_api/
    rest.py                async Discord REST client (aiohttp), 429-aware
    interactions.py        Ed25519 verification, response builders, payload accessors
  usescases/               unchanged layout; cogs became handlers
  utils/                   config, logging, reporting, state, timezones, message loading
scripts/register_commands.py   bulk-overwrite the slash commands
tests/test_smoke.py            triggers index, commands answer, timers behave
```

### The 3-second rule, and why the HTTP trigger is so small

Discord invalidates an interaction if the initial response takes longer than **3 seconds**, and
deferring does not help — the deferred acknowledgement itself must make that deadline. The HTTP
trigger therefore imports only `azure.functions` and PyNaCl, verifies the signature, drops the
payload on a Storage queue and returns `type: 5`. `aiohttp`, `azure-data-tables` and every handler
are imported *inside* the queue and timer functions, which have no such deadline.

Background work after responding is deliberately not used: the host considers an invocation
finished when the handler returns and may recycle the worker immediately, so a fire-and-forget task
can be dropped silently. The queue is the durable equivalent, and it brings retries and a poison
queue for free.

### Statelessness

Three things that a long-lived process got for free now live in Table Storage or are re-derived:

- the **new-member watermark** (`BotState`), advanced after every member so a crashed run cannot
  re-greet people it already messaged;
- **last-run timestamps** for `/info`, replacing process uptime;
- **administrator checks**, which used to read the gateway member cache. A guild interaction carries
  a precomputed `member.permissions` bitfield (used only when the interaction came from the
  configured guild — otherwise an admin of any other server the bot is in could act on this one);
  a DM interaction falls back to `GET /guilds/{id}/members/{user}` plus the guild's role
  permissions.

Concurrency also has to be explicit now. Two timers can run at once, so the reminder job writes
**only the flag it owns** (a merge write) rather than the whole event row, and it claims a reminder
*before* sending it — a duplicate `@everyone` ping is worse than a missed one.

## Local development

```bash
./init-env.sh                    # venv + src/local.settings.json
docker compose up -d azurite     # blob + queue + table emulator
cd src && func start             # Azure Functions Core Tools
python -m unittest discover -s tests -v
```

To exercise the interactions endpoint end to end, expose `http://localhost:7071/api/interactions`
with a tunnel and set it as the application's Interactions Endpoint URL in the Discord Developer
Portal. Discord validates the URL with a signed PING before saving it.
