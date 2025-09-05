# LeetCode Daily Problem Feature

[<< README.md](../../README.md)

This feature automatically fetches and posts the LeetCode Problem of the Day to a specified Discord channel every day at 3:00 AM.

## Features

- **Automatic Daily Posts**: Sends the LeetCode problem of the day at 3:00 AM daily
- **Rich Embed Messages**: Beautiful Discord embeds with problem details
- **Manual Trigger**: Use `/leetcode` command to manually fetch today's problem
- **Comprehensive Information**: Includes difficulty, acceptance rate, topics, and direct link

## Setup

### 1. Environment Variables

Add the following environment variable to your `.env` file:

```env
LEETCODE_CHANNEL_ID=YOUR_CHANNEL_ID_HERE
```

To get your channel ID:
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on the channel where you want to receive LeetCode problems
3. Click "Copy ID"
4. Paste this ID as the value for `LEETCODE_CHANNEL_ID`

### 2. Install Dependencies

The bot requires the `aiohttp` library for making HTTP requests to LeetCode's API:

```bash
pip install -r requirements.txt
```

### 3. Bot Permissions

Ensure your bot has the following permissions in the target channel:
- Send Messages
- Embed Links
- Use External Emojis

## Usage

### Automatic Daily Posts

The bot will automatically post the LeetCode problem of the day at 3:00 AM (server time) to the configured channel.

### Manual Command

Users can manually trigger the LeetCode problem fetch using:
```
/leetcode
```

This command can be used in any channel where the bot has permissions.

## Message Format

The bot sends an embed message containing:

- **Problem Title and Number**: e.g., "1. Two Sum"
- **Difficulty**: Easy 🟢, Medium 🟡, or Hard 🔴
- **Acceptance Rate**: Percentage of accepted submissions
- **Topics**: Related algorithmic topics (up to 5)
- **Direct Link**: Click to solve the problem on LeetCode

## Troubleshooting

### Common Issues

1. **Channel ID not configured**
   - Error: "LEETCODE_CHANNEL_ID not configured"
   - Solution: Add the correct channel ID to your `.env` file

2. **Channel not found**
   - Error: "Channel not found: [ID]"
   - Solution: Verify the channel ID is correct and the bot has access

3. **Failed to fetch problem**
   - Error: "Failed to fetch daily problem"
   - Solution: Check internet connection and LeetCode availability

### Debug Output

The bot logs all LeetCode task activities with the prefix `[BOT][TASK][LEETCODE]`. Check your console output for detailed error information.

## Technical Details

### API Endpoint

The bot uses LeetCode's GraphQL API endpoint:
- URL: `https://leetcode.com/graphql`
- Query: Fetches the active daily coding challenge

### Schedule

The task uses Discord.py's `@tasks.loop()` decorator with `time(3, 0)` to run at 3:00 AM daily. The time is based on the server's timezone.

### Error Handling

The bot includes comprehensive error handling:
- Network request failures
- JSON parsing errors
- Discord API errors
- Missing configuration errors

All errors are logged to the console with descriptive messages.
