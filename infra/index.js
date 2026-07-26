"use strict";
// Craft & Code Club — Discord bot infrastructure on Azure, in Pulumi (JS).
//
// Pattern mirrored from the sibling `myfeed` project, but deliberately simpler:
//   - the bot image is a PUBLIC Docker Hub image (docker.io/craftcodeclub/discord-bot),
//     so there is NO ACR, NO managed identity and NO registry credentials;
//   - secrets live as plain Container App secrets (not Key Vault) sourced from env vars,
//     except the Storage connection string, which is DERIVED from the storage account here;
//   - a single Container App (the bot) — no ingress: it dials out to the Discord gateway,
//     it does not receive HTTP;
//   - an Azure Storage account with a `CommunityEvents` table (the bot uses azure-data-tables).
//
// Resource names are `${projectName}-${environment}`, where `environment` defaults to the Pulumi
// stack name. This lives on stack `discord-bot`, so the names carry that suffix — e.g. the app is
// `ca-c3-discord-bot-discord-bot` in `rg-craft-code-club`, which is what
// .github/workflows/publish.yml deploys to. Every name is overridable via env vars (see below).
//
// ALL config — secret and non-secret alike — comes from ENVIRONMENT VARIABLES, never from
// committed files (no `Pulumi.<stack>.yaml`, no `pulumi config set`). In CI they're injected from
// GitHub `vars`/`secrets` on the `pulumi up` step (see .github/workflows/infra.yml); locally,
// `export` them before running `pulumi up`.
//
// First deploy: `npm install` here, authenticate to Azure, `export` the required env vars below,
// then `pulumi up`.

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

// The image tag is owned by the deploy pipeline (publish.yml -> Update-AzContainerApp). This is
// only the bootstrap image used on the very first `pulumi up`; `ignoreChanges` below stops a later
// `pulumi up` from reverting the tag the pipeline set.
const image = requireEnv("IMAGE");

// Non-secret runtime config. logLevel has a safe default; channel/forum IDs must be set
// explicitly (no hard-coded fallback) so a new stack can't silently point at the wrong channels.
const logLevel = process.env.LOG_LEVEL || "DEBUG";
const leetcodeForumId = requireEnv("LEETCODE_FORUM_ID");
const communityEventsChannelId = requireEnv("COMMUNITY_EVENTS_CHANNEL_ID");
const sayHiChannel = requireEnv("SAY_HI_CHANNEL");
const logsChannelId = requireEnv("LOGS_CHANNEL_ID");

// Secrets are wrapped in pulumi.secret so they're encrypted in Pulumi state too.
const discordApiToken = pulumi.secret(requireEnv("DISCORD_API_TOKEN"));
const discordApplicationId = pulumi.secret(requireEnv("DISCORD_APPLICATION_ID"));
const discordPublicKey = pulumi.secret(requireEnv("DISCORD_PUBLIC_KEY"));

// YouTube secrets are also required — live scheduling is a core feature, not optional.
const youtubeSecrets = [
  { secretName: "youtube-client-id",     env: "YOUTUBE_CLIENT_ID",     value: requireEnv("YOUTUBE_CLIENT_ID") },
  { secretName: "youtube-client-secret", env: "YOUTUBE_CLIENT_SECRET", value: requireEnv("YOUTUBE_CLIENT_SECRET") },
  { secretName: "youtube-refresh-token", env: "YOUTUBE_REFRESH_TOKEN", value: requireEnv("YOUTUBE_REFRESH_TOKEN") },
  { secretName: "youtube-stream-id",     env: "YOUTUBE_STREAM_ID",     value: requireEnv("YOUTUBE_STREAM_ID") },
].map((s) => ({ secretName: s.secretName, env: s.env, value: pulumi.secret(s.value) }));

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

const logs = new azure.operationalinsights.Workspace("logs", {
  resourceGroupName: rg.name,
  workspaceName: `log-${namePrefix}`,
  location: rg.location,
  sku: { name: "PerGB2018" },
  retentionInDays: 30,
  tags,
});

const logsKeys = azure.operationalinsights.getSharedKeysOutput({
  resourceGroupName: rg.name,
  workspaceName: logs.name,
});

// ---------------------------------------------------------------------------
// Storage account (Standard_LRS, StorageV2) + CommunityEvents table
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
  allowSharedKeyAccess: true, // the bot authenticates with the account connection string
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

// Connection string derived from the account key — the bot's AZURE_STORAGE_CONNECTION_STRING.
const storageKeys = azure.storage.listStorageAccountKeysOutput({
  resourceGroupName: rg.name,
  accountName: storage.name,
});
const storageConnectionString = pulumi.secret(pulumi.interpolate`DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storageKeys.keys[0].value};EndpointSuffix=core.windows.net`);

// ---------------------------------------------------------------------------
// Container Apps environment + the bot app
// ---------------------------------------------------------------------------
const containerEnv = new azure.app.ManagedEnvironment("env", {
  resourceGroupName: rg.name,
  environmentName: `cae-${namePrefix}`,
  location: rg.location,
  appLogsConfiguration: {
    destination: "log-analytics",
    logAnalyticsConfiguration: {
      customerId: logs.customerId,
      sharedKey: logsKeys.primarySharedKey,
    },
  },
  // Classic Consumption environment — no `workloadProfiles`. The workload-profiles form of the
  // API requires minimumCount/maximumCount on each profile (a count of *dedicated nodes*), which
  // does not apply to Consumption. Omitting it yields a Consumption-only env (same as myfeed), and
  // the container app sets no `workloadProfileName`, so nothing references a profile.
  zoneRedundant: false,
  tags,
});

// Container App secrets: the three required Discord secrets, the derived storage connection
// string, and the four required YouTube secrets.
const appSecrets = [
  { name: "discord-api-token", value: discordApiToken },
  { name: "discord-application-id", value: discordApplicationId },
  { name: "discord-public-key", value: discordPublicKey },
  { name: "azure-storage-connection-string", value: storageConnectionString },
  ...youtubeSecrets.map((s) => ({ name: s.secretName, value: s.value })),
];

// Env: plain values + secretRefs. Mirrors the exported Container App template.
const appEnv = [
  { name: "LOG_LEVEL", value: logLevel },
  { name: "LEETCODE_FORUM_ID", value: leetcodeForumId },
  { name: "COMMUNITY_EVENTS_CHANNEL_ID", value: communityEventsChannelId },
  { name: "SAY_HI_CHANNEL", value: sayHiChannel },
  { name: "LOGS_CHANNEL_ID", value: logsChannelId },
  { name: "DISCORD_API_TOKEN", secretRef: "discord-api-token" },
  { name: "DISCORD_APPLICATION_ID", secretRef: "discord-application-id" },
  { name: "DISCORD_PUBLIC_KEY", secretRef: "discord-public-key" },
  { name: "AZURE_STORAGE_CONNECTION_STRING", secretRef: "azure-storage-connection-string" },
  ...youtubeSecrets.map((s) => ({ name: s.env, secretRef: s.secretName })),
];

// No ingress: the bot is an outbound gateway client. Exactly 1 replica (fixed) so scheduled jobs
// never run twice concurrently. The http scale rule is kept for parity with the exported template
// but is inert while min == max == 1.
const app = new azure.app.ContainerApp("app", {
  resourceGroupName: rg.name,
  containerAppName: `ca-${namePrefix}`,
  location: rg.location,
  managedEnvironmentId: containerEnv.id,
  configuration: {
    activeRevisionsMode: "Single",
    secrets: appSecrets,
  },
  template: {
    containers: [{
      name: `ca-${namePrefix}`,
      image,
      resources: { cpu: 0.25, memory: "0.5Gi" },
      env: appEnv,
    }],
    scale: {
      minReplicas: 1,
      maxReplicas: 1,
      rules: [{ name: "http-scaler", http: { metadata: { concurrentRequests: "10" } } }],
    },
  },
  tags,
}, {
  // The deploy pipeline (publish.yml) owns the running image tag.
  ignoreChanges: ["template.containers[0].image"],
});

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
exports.resourceGroupName = rg.name;
exports.storageAccountName = storage.name;
exports.containerEnvName = containerEnv.name;
exports.containerAppName = app.name;
// Storage connection string (secret) — recover with `pulumi stack output storageConnectionString --show-secrets`.
exports.storageConnectionString = pulumi.secret(storageConnectionString);
