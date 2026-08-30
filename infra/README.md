# Infrastructure (Pulumi · Azure)

Infrastructure-as-code for the Discord bot, written in **Pulumi (JavaScript)**. Pulumi project
`c3-discord-bot`, stack **`discord-bot`**. It provisions, in the `centralus` region:

- **Resource group** `rg-craft-code-club`
- **Log Analytics workspace** + **Application Insights** (function telemetry)
- **Storage account** (Standard_LRS, StorageV2) holding
  - the `CommunityEvents` table (unchanged — the bot's event data),
  - the `BotState` table (new-member watermark, last-run timestamps),
  - the `discord-work` queue (deferred slash-command work),
  - the `deployment-package` blob container (the zip the function app runs from)
- **App Service plan** `plan-c3-discord-bot-discord-bot` — **Flex Consumption (FC1)**
- **Function app** `func-c3-discord-bot-discord-bot` — the bot

> **Naming:** resource names are `${projectName}-${environment}` and `environment` defaults to the
> Pulumi **stack name**. This stack is named `discord-bot`, so the names carry that suffix
> (e.g. `func-c3-discord-bot-discord-bot`). All names are overridable via env vars (see Setup below).

## Design notes

- **No container, no registry.** The bot is Python code deployed as a zip; there is no Dockerfile,
  no Docker Hub image and no Container App. See [`docs/Architecture.md`](../docs/Architecture.md)
  for why a Discord bot can run without a persistent gateway connection.
- **One storage account for everything.** Tables, queue and the deployment package share the
  account that already held `CommunityEvents`.
- **No always-ready instances.** Flex Consumption's free grant (250,000 executions +
  100,000 GB-s per subscription per month) applies only to on-demand usage — Microsoft's wording is
  "In always ready billing, there are no free grants." Turning always-ready on would make every
  execution billable from the first unit, so the app deliberately runs without it.
- **`AZURE_STORAGE_CONNECTION_STRING` is derived** from the storage account key inside `index.js`.
  Do not set it via env var.
- **The version is stamped into the package**, not into an app setting, so a later `pulumi up`
  cannot revert what `/version` reports.
- **API version pinning:** the Flex Consumption shape (`functionAppConfig`) only exists on the
  `2024-04-01` API version of `WebApp`/`AppServicePlan` in `@pulumi/azure-native` v2, so both
  resources are created through `azure.web.v20240401`.

## Setup

Requires Node.js **>= 22**.

```bash
cd infra
npm install

# Authenticate: `az login`, or export ARM_CLIENT_ID / ARM_CLIENT_SECRET / ARM_TENANT_ID /
# ARM_SUBSCRIPTION_ID for a service principal. Pulumi state lives in Pulumi Cloud
# (export PULUMI_ACCESS_TOKEN).

pulumi stack select discord-bot          # `--create` if it doesn't exist yet

# ALL config — secret and non-secret — is provided via ENV VARS, never written to any file.
# Non-secret (required, no hard-coded fallback):
export DISCORD_GUILD_ID=<id>
export COMMUNITY_EVENTS_CHANNEL_ID=<id>
export SAY_HI_CHANNEL=<id>
export LOGS_CHANNEL_ID=<id>
# Non-secret (optional — index.js falls back to sane defaults if unset):
export PROJECT_NAME=c3-discord-bot
export ENVIRONMENT=discord-bot
export LOCATION=centralus
export RESOURCE_GROUP_NAME=rg-craft-code-club
export LOG_LEVEL=INFO

# Secrets (all required: Discord only):
export DISCORD_API_TOKEN=<token>
export DISCORD_APPLICATION_ID=<id>
export DISCORD_PUBLIC_KEY=<key>

pulumi preview                            # review the plan before applying
pulumi up
```

> **Migrating from the Container App:** the first `pulumi up` after this change DELETES the
> Container App and its managed environment and CREATES the function app. Run `pulumi preview`
> first and read the plan. The storage account and the `CommunityEvents` table are untouched.
> After `pulumi up`, take `interactionsEndpointUrl` from the stack outputs and set it as the
> application's **Interactions Endpoint URL** in the Discord Developer Portal — Discord validates
> it with a signed PING before it will save.

Nothing sensitive is written to any file: `index.js` reads every value (secret or not) from
environment variables (secrets wrapped as Pulumi secrets), so no `Pulumi.<stack>.yaml` exists.
- **CI:** [`infra.yml`](../.github/workflows/infra.yml) injects them into the `pulumi up` step from
  **GitHub `vars`** (non-secret config: `PROJECT_NAME`, `LOCATION`, `RESOURCE_GROUP_NAME`,
  `LOG_LEVEL`, `DISCORD_GUILD_ID`, `COMMUNITY_EVENTS_CHANNEL_ID`, `SAY_HI_CHANNEL`,
  `LOGS_CHANNEL_ID`; `ENVIRONMENT` is optional and defaults to the Pulumi stack name) and
  **GitHub secrets** (on the `PROD` environment, all required): `DISCORD_API_TOKEN`,
  `DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`.
- **Local:** `export` them before `pulumi up` (as above).

## Costs

At this workload every compute meter sits inside a monthly free grant, so the recurring spend is
storage transactions plus Application Insights ingestion — cents, not dollars. The previous
always-on Container App could not be free by construction: the Container Apps grant
(180,000 vCPU-seconds + 360,000 GiB-seconds per subscription per month) buys exactly 200 hours of a
0.25 vCPU / 0.5 GiB replica, and a month is ~730.

To take Application Insights out of the picture entirely, delete the `logs` workspace and the
`appi` component from `index.js` along with the `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting.
The bot still reports warnings and errors to `LOGS_CHANNEL_ID`.

## CI/CD

- [`.github/workflows/infra.yml`](../.github/workflows/infra.yml) runs `pulumi up` on stack
  `discord-bot`. **Manual only** (`workflow_dispatch`).
- [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) builds the zip on a release,
  deploys it to the function app and re-registers the slash commands.
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs the tests on every pull request.
