## [1.25.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.25.0...v1.25.1) (2026-08-21)

# [1.25.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.24.2...v1.25.0) (2026-08-12)


### Features

* **task_bot:** add logs channel ID parsing and event log message sending ([09a0b0c](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/09a0b0cb943d5260a8a0a35d7bd0363baf691aca))

## [1.24.2](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.24.1...v1.24.2) (2026-08-04)


### Bug Fixes

* remove YouTube secrets from infra files ([bee048b](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/bee048b485e63800ab41b446a98543f48dd3dcfa))


### Code Refactoring

* **youtube:** remove YouTube live scheduling functionality and related configurations ([9075345](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/9075345447a091e9ecf605bf5ab4b51947a1fbe4))
* **youtube:** remove YouTube live scheduling functionality and related configurations ([f896dab](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/f896dab524b5298f182924326c77677068593766))


### BREAKING CHANGES

* **youtube:** This commit removes the YouTube live scheduling feature, including all related code, configurations, and documentation. The bot will no longer schedule YouTube live events for community events.
* **youtube:** This commit removes the YouTube live scheduling feature, including all related code, configurations, and documentation. The bot will no longer schedule YouTube live events for community events.

## [1.24.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.24.0...v1.24.1) (2026-08-04)

# [1.24.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.23.0...v1.24.0) (2026-07-30)


### Features

* **new-member:** configurable public welcome + admin join notification ([fc966b1](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/fc966b135479cb3f46cac2784ec0f006860e3c47))

# [1.23.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.22.0...v1.23.0) (2026-07-28)


### Features

* **youtube:** classify scheduled lives as Education instead of Entertainment ([8bf3a2a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/8bf3a2a5f6aa6fbeb0aa90dce514f1e17ff2318a))

# [1.22.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.21.0...v1.22.0) (2026-07-27)


### Bug Fixes

* escape Discord mentions in embed title/description to prevent unexpected pings ([4412087](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/44120875fbb039410a611c516ca3dc2073640a16))
* remove escape_mentions from URL fields to prevent corrupting @ in links ([b8076e3](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b8076e3ee7b4c7f5f398f3ccca7d79dabf32c75e))
* sanitize session_link and recording_link URLs in embed fields ([e3b731b](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/e3b731b234a32ec15906ecbc769a1392cd37bbf1))
* strip session_link and recording_link before building markdown URLs ([87af12f](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/87af12f4224bb9266f915ccdc0f54d212cfacc68))


### Features

* **notify:** tag everyone when publishing event reminders ([8c13d04](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/8c13d0462b08f4a83824dfcd34f9a35e63013b08))

# [1.21.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.20.1...v1.21.0) (2026-07-26)


### Features

* **event:** add event recording link command for admins ([5b4ac46](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/5b4ac4614feb09c8e9d74e2bf32f61123ad9275c))

## [1.20.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.20.0...v1.20.1) (2026-07-26)


### Bug Fixes

* hardcode communityEventsChannelId and sayHiChannel defaults in index.js ([3203093](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/3203093d4264d83d828c9c0aed96562a6e529d5f))
* remove hardcoded defaults for channel/forum IDs from index.js ([008421e](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/008421e1d3f63af3a66d06be7185b11f0f77fca3))
* restore communityEventsChannelId and sayHiChannel in Pulumi.discord-bot.yaml ([fbd1ec7](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/fbd1ec747efff73a05ff96318658a769e9f66c09))
* **infra:** update environment variable handling and remove config file ([1102f03](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/1102f039c5b3ccd33b8a2b21d27c471eed9e6ddc))

# [1.20.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.19.0...v1.20.0) (2026-07-26)


### Features

* **server-status:** add online user count to server status command ([c806665](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/c8066654fccc6b7a8535c3e97df9695625ed7723))

# [1.19.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.18.0...v1.19.0) (2026-07-26)


### Bug Fixes

* **infra:** add LOGS_CHANNEL_ID to Pulumi production container env ([cd63754](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/cd63754bd3ee3990e949aa3ac31cfd887728fef5))


### Features

* **logging:** add logging to Discord channel for warnings and errors ([a77d6d2](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a77d6d22c96eb702ec4b85b0afb778c78cde8fa2))

# [1.18.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.17.0...v1.18.0) (2026-07-26)


### Bug Fixes

* brazil time for event list ([43375b6](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/43375b666f1f4072af9b9b25e936cb434de9bdfc))
* brazil time for event list ([639cff7](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/639cff7148253cb923f5fab57350b6e89025a251))
* indentation ([863ac80](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/863ac80af53df65e16a2a26b0104c57194fce3d2))


### Features

* **commands:** add events command to list upcoming events for admins ([4e360fd](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/4e360fdfa603a93e2810bc0253b5caed2dc6292e))

# [1.17.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.16.0...v1.17.0) (2026-07-25)


### Features

* **help:** add help command to list available commands with descriptions ([4065057](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/4065057a5393f4152cd7dce31853d6f56e8c420b))
* **init-env:** add initialization script for Python environment setup ([70c028f](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/70c028f13592353085c5120a7a5261af95ef98a3))
* **commands:** split admin commands ([04bc45d](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/04bc45da785f44ead092bbb6af265e200f11b0b8))

# [1.16.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.15.0...v1.16.0) (2026-07-25)


### Bug Fixes

* lazy-load community_events_dao inside event_add_session_link ([37067d1](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/37067d1237634a3c5744bec74b1a1f4987c45f0b))


### Features

* **event:** add command to manage event session links ([48828e3](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/48828e3549c00d53a1be3fa3d537864a00c32391))

# [1.15.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.14.0...v1.15.0) (2026-07-24)


### Bug Fixes

* **github_service:** handle invalid registration link for events ([172f60a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/172f60a3e50e10e183a5157d2362f7b266808463))


### Features

* **community_event:** only show session link if open session is true and reminder time is an hour ([df0750a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/df0750ad60058b963255c0356a6b069f711c5e34))

# [1.14.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.13.0...v1.14.0) (2026-07-24)


### Features

* **new-member:** add delay before sending welcome messages ([02c963a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/02c963abbc45517fc01daed7f73eee14d26b590a))

# [1.13.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.12.0...v1.13.0) (2026-07-24)


### Bug Fixes

* **status:** add STATUS_MAX_MEMBERS safety cap to _build_guild_status ([b779290](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b779290bc3a499c741b95e7406e6a19b686bc67d))
* **status:** improve formatting of server status command output ([0a6c8a1](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/0a6c8a1a6b7ff46b23a0d247c800d23a1aa44114))
* **send_chunked:** skip empty chunk flushes and split overlong lines into safe slices ([3036ff2](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/3036ff2cd49962cef97fadf530a20b2bdf093b9a))
* **status:** stream member fetch and handle member query failures ([e3be33a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/e3be33ab14fe6e068ca0265851e7237956f9858b))


### Features

* **status:** add server status command for admins via DM ([1c44812](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/1c4481234ff60a52d61772e60c3b0c01fd3b4827))


### Performance Improvements

* **status:** single-pass role counting, 30s cache, timestamp, chunked DM output ([fe22152](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/fe2215202c9979b7cb336f401e69cf12fa58d337))

# [1.12.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.11.0...v1.12.0) (2026-07-23)


### Bug Fixes

* **add-role:** increase max members limit for [@all](https://github.com/all) role assignment ([063e4f6](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/063e4f6b919143556c3d9d7e982d60f1c21638bf))


### Features

* **admin:** add command to assign roles to users or [@all](https://github.com/all) ([af325ae](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/af325aed744ca045df471d01d7c57a81a1782bca))

# [1.11.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.10.1...v1.11.0) (2026-07-19)


### Bug Fixes

* move docker build context to end ([167c001](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/167c001dd2c50f37076c916650f3eeba07eaf5be))
* **admin:** update access denial messages for admin commands ([826e04f](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/826e04fa2e45f9d4f0f17500581ca344b4436635))
* update command error handling to log instead of send message ([2a8e602](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/2a8e602c76168bd174ae920da159ec06778d5875))


### Features

* **admin:** add admin commands to check bot version and uptime ([4e7dcde](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/4e7dcdee9ce92bb498403899076a7bed7ffdd4db))

## [1.10.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.10.0...v1.10.1) (2026-07-19)


### Bug Fixes

* enable case sensitivity for command recognition ([f8409bd](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/f8409bdc11c77298e089258e266c94aca31e77b4))

# [1.10.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.9.0...v1.10.0) (2026-07-18)


### Features

* provision Azure infra (Storage + Container App) with Pulumi ([e62da2a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/e62da2a13ac1920c6019019f95b32b6de9cd6fdf))

# [1.9.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.8.3...v1.9.0) (2026-07-04)


### Bug Fixes

* extract broadcast ([9a06466](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/9a06466f26909dbff7e743c48a0bc97a0628fc2c))
* preserve YouTube broadcast snippet on update ([a06ace4](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a06ace4379f7f71d75cfa07a3d2515917a7f48f4))
* support youtu.be and youtube.com/live URL formats in __extract_broadcast_id ([236de5a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/236de5a568f884cba29c4a439bac9f8c19f038b6))
* **youtube:** use existing title in updated broadcast snippet ([695951a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/695951a82086105ff07dd045a46ef9b025efba15))


### Features

* **youtube:** update live event datetime when scheduled ([ac3b067](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/ac3b067aaca3e4b5e03516a710313f38c7163527))

## [1.8.3](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.8.2...v1.8.3) (2026-06-30)


### Bug Fixes

* purge build-only packages after pip install, retain libffi8 runtime ([a725dce](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a725dce03ac37fc270d1f2eacb09e18c48edb25f))

## [1.8.2](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.8.1...v1.8.2) (2026-06-30)


### Bug Fixes

* **youtube_live_service:** set enableAutoStart to False for manual stream setup ([0e4d7f4](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/0e4d7f449ea78c237cbd1c3240cb272d517740f9))

## [1.8.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.8.0...v1.8.1) (2026-06-17)


### Bug Fixes

* **youtube_live_service:** set enableAutoStart to False for manual stream setup ([0afaf8f](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/0afaf8f3fc2db3de1d6d3dd3886e5c1b6c9f8085))

# [1.8.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.7.3...v1.8.0) (2026-06-15)


### Bug Fixes

* **youtube_live_service:** remove unused title assignment in schedule_live_event ([e45b125](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/e45b1258be916b1af807360aeb6868450ec06115))


### Features

* Implement YouTube live scheduling ([a6b70aa](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a6b70aa356816b00e9e5b4694d4f1128dcc56c91))

## [1.7.3](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.7.2...v1.7.3) (2026-06-09)


### Bug Fixes

* **publish:** update health check conditions for container app ([a292f3d](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a292f3dfa3188a19676f1e913fa77d2fc90b7e7d))

## [1.7.2](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.7.1...v1.7.2) (2026-06-09)


### Bug Fixes

* deployment ([9fdaa8d](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/9fdaa8d67d572223b88888871df7745989a42ab5))

## [1.7.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.7.0...v1.7.1) (2026-06-09)

# [1.7.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.6.1...v1.7.0) (2026-06-07)


### Bug Fixes

* correct welcome message phrasing for new members ([1829433](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/1829433c18d5a9cee110a78277c06ed96f2a9e90))


### Features

* add say hi channel to welcome messages ([a072abb](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a072abbc94aaed9c6bdc887c622ff6af0c2fc035))

## [1.6.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.6.0...v1.6.1) (2025-09-28)


### Bug Fixes

* folder utils ([a2485c0](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a2485c0771a42f493b782085dfa8cf1575a5e893))

# [1.6.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.5.0...v1.6.0) (2025-09-28)


### Features

* **community_events:** add banner image in discord event ([3f4f0c2](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/3f4f0c2d3a6503083130d1554450b1683ab7ca83))
* **leetcode_daily:** enhance forum post formatting and markdown conversion ([b7ec8ba](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b7ec8bad9732fd1e31b6dbe58c57626e407d4394))

# [1.5.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.4.1...v1.5.0) (2025-09-28)


### Features

* **community_events:** add banner field ([7a5fac3](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/7a5fac3158b575346c071a49a7deddc6959f96a0))
* Leet code problem as forum post ([7c8596c](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/7c8596c0708188252aba876a7448b0a568c613ce))

## [1.4.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.4.0...v1.4.1) (2025-09-24)

# [1.4.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.3.0...v1.4.0) (2025-09-23)


### Features

* **community_events:** add discord event creation ([b11db34](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b11db34da87d9d347ce31865e428c01cb4447d49))

# [1.3.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.2.2...v1.3.0) (2025-09-23)


### Bug Fixes

* import datetime ([6cbfbd6](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/6cbfbd689a790782455e194d1f5cdfa634de05e7))
* Update src/Utils/logger.py ([e58b8a0](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/e58b8a0f39098ae2d5c0ef395faff4febad971b4))
* Update src/Utils/message_loader.py ([39eb4ca](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/39eb4ca5961df89e8293af1eb2bff37dde88d3d0))


### Features

* **community_events:** add community events management ([5f73f1b](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/5f73f1b1d8a3f7fc864e464c35530a2eeca6498d))

## [1.2.2](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.2.1...v1.2.2) (2025-09-23)


### Bug Fixes

* Update src/Utils/logger.py ([a622feb](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a622feb293bb88b04f46876882a9ea3fb41f4b4d))
* Update src/Utils/message_loader.py ([3e1d865](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/3e1d8655f324d53b40b60efe6cb9c56aa8bd4e5a))

## [1.2.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.2.0...v1.2.1) (2025-09-05)


### Bug Fixes

* **leetcodedaily:** improve logging and message ([8a6b17a](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/8a6b17a91bfd004aba4bc764955fcb14724172df))
* **leetcodedaily:** improve logging for LeetCode command response ([536d872](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/536d8723d912b201726b5a78f7342397e92713c5))
* **welcome_event:** change log level for DM disabled warning to warning ([3549adc](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/3549adc01b73603e7b4e8d491424a7fa45fcd280))

# [1.2.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.1.0...v1.2.0) (2025-09-05)


### Features

* add daily LeetCode problem posting feature ([a388dc6](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a388dc64e7fd9965f5a6815c5b48010266b44ba4))

# [1.1.0](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.5...v1.1.0) (2025-09-03)


### Features

* **messages:** implement message loading functionality for rules and welcome messages ([5931713](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/59317132ef5ef856dbc4cbd37f08bbfa9fcd6cb8))

## [1.0.5](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.4...v1.0.5) (2025-09-03)


### Bug Fixes

* remove unnecessary permissions from release job ([c426d57](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/c426d570886efe78a55402bd9b66ba6cbfcb98e6))
* test ([43bdc01](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/43bdc019feae8958314cbb2aa0f9818ae0dc4be0))

## [1.0.4](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.3...v1.0.4) (2025-09-03)


### Bug Fixes

* **publish:** change release event type from published to created ([b4db62d](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b4db62dc49a88cca3db1a257a36add3f2ba4a5dd))

## [1.0.3](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.2...v1.0.3) (2025-09-03)


### Bug Fixes

* change release event type from created to published ([b555f90](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b555f90ffc0443208695811c16e6c475cad3b332))

## [1.0.2](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.1...v1.0.2) (2025-09-03)


### Bug Fixes

* update publish workflow to resolve image tag correctly ([861e63b](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/861e63b6fd06c42c6b7401120ca93303bfee553f))

## [1.0.1](https://github.com/craft-code-club/craft-code-club-discord-bot/compare/v1.0.0...v1.0.1) (2025-09-03)


### Bug Fixes

* remove branches filter from release workflow trigger ([6a01807](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/6a01807fd316e4c74b2037e9b0a4b6a5aa50b5f3))

# 1.0.0 (2025-09-03)


### Bug Fixes

* add permissions for GitHub Releases and PR updates ([b6e8ad3](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/b6e8ad3ca9e87423673313f5bd96bf4c83905a41))


### Features

* kickoff ([a41296f](https://github.com/craft-code-club/craft-code-club-discord-bot/commit/a41296f8460433c29fef55df0f9a98c19e41079d))
