# LeetCode Daily Problem Feature

[<< README.md](../../README.md)

This feature automatically fetches and posts the LeetCode Problem of the Day to a specified Discord forum every day at 15:00 UTC.

## Features

- **Automatic Daily Posts**: Sends the LeetCode problem of the day at 15:00 UTC daily
- **Rich Embed Messages**: Beautiful Discord embeds with problem details
- **Manual Trigger**: Use `/leetcode-daily` command to manually fetch today's problem
- **Comprehensive Information**: Includes difficulty, acceptance rate, topics, and direct link

## Setup

### 1. Environment Variables

Add the following environment variable to your `.env` file:

```env
LEETCODE_FORUM_ID=YOUR_FORUM_ID_HERE
```

To get your forum ID:
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on the forum where you want to receive LeetCode problems
3. Click "Copy ID"
4. Paste this ID as the value for `LEETCODE_FORUM_ID`


### 3. Bot Permissions

Ensure your bot has the following permissions in the target forum:
- Send Messages
- Embed Links
- Use External Emojis

## Usage

### Automatic Daily Posts

The bot will automatically post the LeetCode problem of the day at 15:00 UTC to the configured channel.

### Manual Command

Users can manually trigger the LeetCode problem fetch using:
```
/leetcode-daily
```

This command can be used in any channel where the bot has permissions.

## Message Format

The bot sends an embed message containing:

- **Problem Title and Number**: e.g., "1. Two Sum"
- **Difficulty**: Easy 🟢, Medium 🟡, or Hard 🔴
- **Acceptance Rate**: Percentage of accepted submissions
- **Topics**: Related algorithmic topics (up to 5)
- **Direct Link**: Click to solve the problem on LeetCode


## Technical Details

### API Endpoint

The bot uses LeetCode's GraphQL API endpoint:
- URL: `https://leetcode.com/graphql`
- Query: Fetches the active daily coding challenge
