"use strict";
// Craft & Code Club — Discord bot infrastructure on Azure, in Pulumi (JS).
//
// The bot runs as an AZURE FUNCTIONS app (Flex Consumption), not a container:
//   - an HTTP-triggered function serves Discord's Interactions Endpoint URL;
//   - timer-triggered functions run the event reminders, the craftcodeclub.io
//     sync and the new-member poll;
//   - a queue-triggered function does the slow half of each slash command.
//
// Everything shares ONE storage account — the same one the bot already used for
// the `CommunityEvents` table. It now also holds `BotState`, the `discord-work`
// queue and the `deployment-package` blob container the Functions host runs from.
//
// Why this shape is (almost) free:
//   - Flex Consumption's monthly free grant is 250,000 executions + 100,000 GB-s
//     per subscription. The bot needs roughly 12,000 executions/month at 512 MB
//     for a few seconds each — about 5% of the grant.
//   - There are NO always-ready instances. Always-ready has no free grant, and
//     turning it on would make every execution billable from the first unit.
//   - The only recurring meters left are storage transactions and Application
//     Insights ingestion, both fractions of a cent at this volume.
//
// Resource names are `${projectName}-${environment}`, where `environment` defaults
// to the Pulumi stack name (`discord-bot`). Every name is overridable via env vars.
//
// ALL config — secret and non-secret alike — comes from ENVIRONMENT VARIABLES, never
// from committed files (no `Pulumi.<stack>.yaml`, no `pulumi config set`). In CI they
// are injected from GitHub `vars`/`secrets` on the `pulumi up` step (see
// .github/workflows/infra.yml); locally, `export` them before running `pulumi up`.

const pulumi = require("@pulumi/pulumi");
const azure = require("@pulumi/azure-native");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
// Required env vars throw a clear error instead of silently deploying with a wrong/missing value.
const requireEnv = (name) => {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var ${name} — set it (GitHub var/secret in CI, or 'export' locally) before running 'pulumi up'.`);
  return v;
};

const projectName = process.env.PROJECT_NAME || "c3-discord-bot";
const environment = process.env.ENVIRONMENT || pulumi.getStack();
const location = process.env.LOCATION || "centralus";
const resourceGroupName = process.env.RESOURCE_GROUP_NAME || "rg-craft-code-club";

// Non-secret runtime config. logLevel has a safe default; the channel and guild IDs
// must be set explicitly (no hard-coded fallback) so a new stack can't silently point
// at the wrong server.
const logLevel = process.env.LOG_LEVEL || "INFO";
const communityEventsChannelId = requireEnv("COMMUNITY_EVENTS_CHANNEL_ID");
const sayHiChannel = requireEnv("SAY_HI_CHANNEL");
const logsChannelId = requireEnv("LOGS_CHANNEL_ID");
// New in the Functions port: without a gateway there is no channel/guild cache, so the
// guild the bot operates on is configured rather than discovered.
const discordGuildId = requireEnv("DISCORD_GUILD_ID");

// New-member messaging. Toggles have safe defaults; the channel IDs are optional (empty = the
// bot skips that message), so a missing value can't silently point at the wrong channel.
const welcomeMessageEnabled = process.env.WELCOME_MESSAGE_ENABLED || "false";
const welcomeChannelId = process.env.WELCOME_CHANNEL_ID || "";
const adminJoinNotificationEnabled = process.env.ADMIN_JOIN_NOTIFICATION_ENABLED || "false";
const adminJoinNotificationChannelId = process.env.ADMIN_JOIN_NOTIFICATION_CHANNEL_ID || "";

// Secrets are wrapped in pulumi.secret so they're encrypted in Pulumi state too.
const discordApiToken = pulumi.secret(requireEnv("DISCORD_API_TOKEN"));
const discordApplicationId = pulumi.secret(requireEnv("DISCORD_APPLICATION_ID"));
const discordPublicKey = pulumi.secret(requireEnv("DISCORD_PUBLIC_KEY"));

const tags = { project: projectName, environment, managedBy: "pulumi" };
const namePrefix = `${projectName}-${environment}`;
// Compact, alnum-only prefix for the storage account (3-24 chars, lowercase, no hyphens).
const compactPrefix = `${projectName}${environment}`.toLowerCase().replace(/[^a-z0-9]/g, "");

// ---------------------------------------------------------------------------
// Resource group + observability
// ---------------------------------------------------------------------------
const rg = new azure.resources.ResourceGroup("rg", {
  resourceGroupName,
  location,
  tags,
});

// Application Insights needs a workspace. `dailyQuotaGb` is a safety valve, not a
// budget: at this workload the app ingests single-digit MB/month. Drop the workspace
// and the component (and the APPLICATIONINSIGHTS_CONNECTION_STRING setting below) if
// you want the bill to be exactly zero and are happy debugging from the logs channel.
const logs = new azure.operationalinsights.Workspace("logs", {
  resourceGroupName: rg.name,
  workspaceName: `log-${namePrefix}`,
  location: rg.location,
  sku: { name: "PerGB2018" },
  retentionInDays: 30,
  workspaceCapping: { dailyQuotaGb: 0.1 },
  tags,
});

const appInsights = new azure.insights.Component("appi", {
  resourceGroupName: rg.name,
  resourceName: `appi-${namePrefix}`,
  location: rg.location,
  kind: "web",
  applicationType: "web",
  ingestionMode: "LogAnalytics",
  workspaceResourceId: logs.id,
  tags,
});

// ---------------------------------------------------------------------------
// Storage account (Standard_LRS, StorageV2) — tables, queue and deployment package
// ---------------------------------------------------------------------------
const storage = new azure.storage.StorageAccount("storage", {
  resourceGroupName: rg.name,
  accountName: `stt${compactPrefix}`.slice(0, 24),
  location: rg.location,
  sku: { name: "Standard_LRS" },
  kind: "StorageV2",
  accessTier: "Hot",
  minimumTlsVersion: "TLS1_2",
  supportsHttpsTrafficOnly: true,
  allowBlobPublicAccess: false,
  // The Functions host authenticates to this account with the connection string.
  allowSharedKeyAccess: true,
  tags,
});

// 7-day soft delete on blobs, matching the exported account.
new azure.storage.BlobServiceProperties("blob-svc", {
  resourceGroupName: rg.name,
  accountName: storage.name,
  blobServicesName: "default",
  deleteRetentionPolicy: { enabled: true, days: 7 },
  containerDeleteRetentionPolicy: { enabled: true, days: 7 },
});

// The table the bot reads/writes via azure-data-tables.
new azure.storage.Table("community-events", {
  resourceGroupName: rg.name,
  accountName: storage.name,
  tableName: "CommunityEvents",
});

// Small key/value table: the new-member watermark and the last-run timestamps that
// `/info` reports. A stateless function has nowhere else to keep them.
new azure.storage.Table("bot-state", {
  resourceGroupName: rg.name,
  accountName: storage.name,
  tableName: "BotState",
});

// The interactions endpoint answers Discord within its 3-second deadline and hands the
// work to this queue; a queue-triggered function finishes it and edits the response.
new azure.storage.Queue("discord-work", {
  resourceGroupName: rg.name,
  accountName: storage.name,
  queueName: "discord-work",
});

// Flex Consumption runs the app from a zip in this container, uploaded by the deploy pipeline.
const deploymentContainer = new azure.storage.BlobContainer("deployment-package", {
  resourceGroupName: rg.name,
  accountName: storage.name,
  containerName: "deployment-package",
  publicAccess: azure.storage.PublicAccess.None,
});

// Connection string derived from the account key — used for AzureWebJobsStorage, for the
// deployment container and by the bot's own azure-data-tables client.
const storageKeys = azure.storage.listStorageAccountKeysOutput({
  resourceGroupName: rg.name,
  accountName: storage.name,
});
const storageConnectionString = pulumi.secret(pulumi.interpolate`DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storageKeys.keys[0].value};EndpointSuffix=core.windows.net`);

// ---------------------------------------------------------------------------
// Function app (Flex Consumption)
// ---------------------------------------------------------------------------
// `functionAppConfig` (the Flex Consumption shape) only exists on the pinned
// 2024-04-01 API version of these resources in @pulumi/azure-native v2; the
// version-less `azure.web.WebApp` still maps to an older API that has no such
// property. Both resources are pinned so the plan and the app agree.
const webApi = azure.web.v20240401;

const plan = new webApi.AppServicePlan("plan", {
  resourceGroupName: rg.name,
  name: `plan-${namePrefix}`,
  location: rg.location,
  // Flex Consumption is Linux-only, which is what `reserved` selects.
  sku: { tier: "FlexConsumption", name: "FC1" },
  reserved: true,
  tags,
});

const appSettings = [
  { name: "AzureWebJobsStorage", value: storageConnectionString },
  { name: "DEPLOYMENT_STORAGE_CONNECTION_STRING", value: storageConnectionString },
  { name: "APPLICATIONINSIGHTS_CONNECTION_STRING", value: appInsights.connectionString },

  { name: "LOG_LEVEL", value: logLevel },

  { name: "AZURE_STORAGE_CONNECTION_STRING", value: storageConnectionString },

  { name: "DISCORD_API_TOKEN", value: discordApiToken },
  { name: "DISCORD_APPLICATION_ID", value: discordApplicationId },
  { name: "DISCORD_PUBLIC_KEY", value: discordPublicKey },
  { name: "DISCORD_GUILD_ID", value: discordGuildId },

  { name: "COMMUNITY_EVENTS_CHANNEL_ID", value: communityEventsChannelId },
  { name: "SAY_HI_CHANNEL", value: sayHiChannel },
  { name: "LOGS_CHANNEL_ID", value: logsChannelId },

  { name: "WELCOME_MESSAGE_ENABLED", value: welcomeMessageEnabled },
  { name: "WELCOME_CHANNEL_ID", value: welcomeChannelId },
  { name: "ADMIN_JOIN_NOTIFICATION_ENABLED", value: adminJoinNotificationEnabled },
  { name: "ADMIN_JOIN_NOTIFICATION_CHANNEL_ID", value: adminJoinNotificationChannelId },
];

const functionApp = new webApi.WebApp("func", {
  resourceGroupName: rg.name,
  name: `func-${namePrefix}`,
  location: rg.location,
  kind: "functionapp,linux",
  serverFarmId: plan.id,
  httpsOnly: true,
  functionAppConfig: {
    deployment: {
      storage: {
        type: "blobContainer",
        value: pulumi.interpolate`${storage.primaryEndpoints.blob}${deploymentContainer.name}`,
        // Connection-string auth keeps the deploying service principal from needing
        // permission to create role assignments.
        authentication: {
          type: "StorageAccountConnectionString",
          storageAccountConnectionStringName: "DEPLOYMENT_STORAGE_CONNECTION_STRING",
        },
      },
    },
    runtime: { name: "python", version: "3.12" },
    scaleAndConcurrency: {
      // 512 MB is the smallest Flex instance (0.25 vCPU) and keeps GB-s consumption
      // well inside the free grant. No always-ready instances: see the header.
      instanceMemoryMB: 512,
      maximumInstanceCount: 40,
    },
  },
  siteConfig: {
    appSettings,
    // The interactions endpoint is called by Discord only; CORS is irrelevant, and
    // FTP deployment is disabled because the pipeline deploys the zip package.
    ftpsState: "Disabled",
  },
  tags,
}, {
  // The deploy pipeline owns the code; Pulumi owns the infrastructure around it.
  ignoreChanges: ["siteConfig.linuxFxVersion"],
});

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
exports.resourceGroupName = rg.name;
exports.storageAccountName = storage.name;
exports.functionAppName = functionApp.name;
// Set this as the application's "Interactions Endpoint URL" in the Discord Developer Portal.
exports.interactionsEndpointUrl = pulumi.interpolate`https://${functionApp.defaultHostName}/api/interactions`;
// Storage connection string (secret) — recover with `pulumi stack output storageConnectionString --show-secrets`.
exports.storageConnectionString = pulumi.secret(storageConnectionString);
