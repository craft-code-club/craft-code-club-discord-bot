# Infrastructure (Pulumi · Azure)

Infrastructure-as-code for the Discord bot, written in **Pulumi (JavaScript)**. Pulumi project
`c3-discord-bot`, stack **`discord-bot`**. It provisions, in the `centralus` region:

- **Resource group** `rg-craft-code-club`
- **Log Analytics workspace** (Container Apps logs)
- **Storage account** `sttc3discordbotdiscordbo` (Standard_LRS, StorageV2) + `CommunityEvents` table
- **Container Apps managed environment** `cae-c3-discord-bot-discord-bot` (Consumption)
- **Container App** `ca-c3-discord-bot-discord-bot` — the bot (public Docker Hub image, no ingress, 1 replica)

> **Naming:** resource names are `${projectName}-${environment}` and `environment` defaults to the
> Pulumi **stack name**. This stack is named `discord-bot`, so the names carry that suffix
> (e.g. `ca-c3-discord-bot-discord-bot`). All names are overridable via env vars (see Setup below).

## Design notes

- **No ACR / managed identity / Key Vault.** The image is a public Docker Hub image and secrets are
  plain Container App secrets sourced from env vars — simpler than the sibling `myfeed` setup
  this pattern is based on.
- **`AZURE_STORAGE_CONNECTION_STRING` is derived** from the storage account key inside `index.js`.
  Do not set it via env var.
- **The image tag is owned by the deploy pipeline.** `index.js` keeps `template.containers[0].image`
  under `ignoreChanges`; `IMAGE` is only the bootstrap tag for the first `up`.

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
export LEETCODE_FORUM_ID=<id>
export COMMUNITY_EVENTS_CHANNEL_ID=<id>
export SAY_HI_CHANNEL=<id>
export LOGS_CHANNEL_ID=<id>
export IMAGE=docker.io/craftcodeclub/discord-bot:v1.16.0
# Non-secret (optional — index.js falls back to sane defaults if unset):
export PROJECT_NAME=c3-discord-bot
export ENVIRONMENT=discord-bot
export LOCATION=centralus
export RESOURCE_GROUP_NAME=rg-craft-code-club
export LOG_LEVEL=DEBUG

# Secrets (all required: Discord only):
export DISCORD_API_TOKEN=<token>
export DISCORD_APPLICATION_ID=<id>
export DISCORD_PUBLIC_KEY=<key>

pulumi up
```

Nothing sensitive is written to any file: `index.js` reads every value (secret or not) from
environment variables (secrets wrapped as Pulumi secrets), so no `Pulumi.<stack>.yaml` exists.
- **CI:** [`infra.yml`](../.github/workflows/infra.yml) injects them into the `pulumi up` step from
  **GitHub `vars`** (non-secret config: `PROJECT_NAME`, `LOCATION`,
  `RESOURCE_GROUP_NAME`, `IMAGE`, `LOG_LEVEL`, `LEETCODE_FORUM_ID`, `COMMUNITY_EVENTS_CHANNEL_ID`,
  `SAY_HI_CHANNEL`, `LOGS_CHANNEL_ID`; `ENVIRONMENT` is optional and defaults to the Pulumi stack name) and **GitHub secrets** (on the `PROD` environment, all
  required): `DISCORD_API_TOKEN`, `DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`.
- **Local:** `export` them before `pulumi up` (as above).

## CI/CD

- [`.github/workflows/infra.yml`](../.github/workflows/infra.yml) runs `pulumi up` on stack
  `discord-bot`. **Manual only** (`workflow_dispatch`) — the automatic push-on-`infra/**` trigger is
  left commented out so infra changes stay deliberate; uncomment it to enable.
- App deployment ([`publish.yml`](../.github/workflows/publish.yml) → *Publish App*) is **enabled**:
  on a GitHub release it builds & pushes the image and deploys a new revision to
  `ca-c3-discord-bot-discord-bot`.
