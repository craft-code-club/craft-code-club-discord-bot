# Infrastructure (Pulumi · Azure)

Infrastructure-as-code for the Discord bot, written in **Pulumi (JavaScript)**. Pulumi project
`c3-discord-bot`, stack **`discord-bot`**. It provisions, in the `centralus` region:

- **Resource group** `rg-craft-code-club`
- **Log Analytics workspace** (Container Apps logs)
- **Storage account** `sttc3discordbotdiscordbot` (Standard_LRS, StorageV2) + `CommunityEvents` table
- **Container Apps managed environment** `cae-c3-discord-bot-discord-bot` (Consumption)
- **Container App** `ca-c3-discord-bot-discord-bot` — the bot (public Docker Hub image, no ingress, 1 replica)

> **Naming:** resource names are `${projectName}-${environment}` and `environment` defaults to the
> Pulumi **stack name**. This stack is named `discord-bot`, so the names carry that suffix
> (e.g. `ca-c3-discord-bot-discord-bot`). All names are config-overridable in `Pulumi.discord-bot.yaml`.

## Design notes

- **No ACR / managed identity / Key Vault.** The image is a public Docker Hub image and secrets are
  plain Container App secrets sourced from Pulumi config — simpler than the sibling `myfeed` setup
  this pattern is based on.
- **`AZURE_STORAGE_CONNECTION_STRING` is derived** from the storage account key inside `index.js`.
  Do not set it in config.
- **The image tag is owned by the deploy pipeline.** `index.js` keeps `template.containers[0].image`
  under `ignoreChanges`; `Pulumi.discord-bot.yaml:image` is only the bootstrap tag for the first `up`.

## Setup

```bash
cd infra
npm install

# Authenticate: `az login`, or export ARM_CLIENT_ID / ARM_CLIENT_SECRET / ARM_TENANT_ID /
# ARM_SUBSCRIPTION_ID for a service principal. Pulumi state lives in Pulumi Cloud
# (export PULUMI_ACCESS_TOKEN).

pulumi stack select discord-bot          # `--create` if it doesn't exist yet

# Required secrets (already set on this stack; re-run only to rotate):
pulumi config set --secret c3-discord-bot:discordApiToken      <token>
pulumi config set --secret c3-discord-bot:discordApplicationId <id>
pulumi config set --secret c3-discord-bot:discordPublicKey     <key>
# Optional (YouTube live scheduling):
pulumi config set --secret c3-discord-bot:youtubeClientId      <id>
pulumi config set --secret c3-discord-bot:youtubeClientSecret  <secret>
pulumi config set --secret c3-discord-bot:youtubeRefreshToken  <token>
pulumi config set --secret c3-discord-bot:youtubeStreamId      <id>

pulumi up
```

The secret values are stored **encrypted** in `Pulumi.discord-bot.yaml` (committed) and decrypted by
Pulumi Cloud via `PULUMI_TOKEN` — safe to commit.

## CI/CD

- [`.github/workflows/infra.yml`](../.github/workflows/infra.yml) runs `pulumi up` on stack
  `discord-bot`. **Manual only** (`workflow_dispatch`) — the automatic push-on-`infra/**` trigger is
  left commented out so infra changes stay deliberate; uncomment it to enable.
- App deployment ([`publish.yml`](../.github/workflows/publish.yml) → *Publish App*) is **enabled**:
  on a GitHub release it builds & pushes the image and deploys a new revision to
  `ca-c3-discord-bot-discord-bot`.
