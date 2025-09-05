# Craft & Code Club - Discord Bot

A Discord bot for the Craft & Code Club community with automated features and interactive commands.

## Features

- **Welcome Messages**: Greets new members with custom messages
- **Rules Command**: Display server rules and guidelines
- **LeetCode Daily Problem**: Automatically posts LeetCode problem of the day at 3 AM

## Steps to create a Discord Bot

* [Create an application in Discord](./docs/CreateDiscordBot.md)
* [Setup Python environment](./docs/PythonEnvironment.md)
* [Configure Environment Variables](#configure-environment-variables)
* [Setup LeetCode Daily Task](./docs/features/LeetCodeDailyTask.md)



## Configure Environment Variables
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```txt
DISCORD_API_TOKEN=<your_discord_api_key>
LEETCODE_CHANNEL_ID=<your_leetcode_channel_id>
```

### Environment Variables

- `DISCORD_API_TOKEN`: Your Discord bot token (required)
- `LEETCODE_CHANNEL_ID`: Discord channel ID where LeetCode problems will be posted (optional)



## Install the required packages

```bash
pip install -r requirements.txt
```

The required packages include:
- `python-dotenv`: Environment variable management
- `discord.py`: Discord API wrapper
- `aiohttp`: HTTP client for API requests



## References
- [discord.py](https://discordpy.readthedocs.io/en/stable/)
- [Discord Bot Documentation](https://discord.com/developers/docs/intro)
