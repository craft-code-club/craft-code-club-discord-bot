# YouTube Live Scheduling Feature

[<< README.md](../../README.md)

This feature automatically schedules a public YouTube live when a future community event should have a live stream created by the bot.

## When the Bot Schedules a YouTube Live

The bot schedules a YouTube live only when all of these conditions are true:

- The event frontmatter field `isLive` is `true`
- The event `recordingLink` from GitHub is empty
- The stored `recording_link` in Azure Table Storage is also empty

The bot skips YouTube scheduling when any of these are true:

- The event frontmatter field `isLive` is not `true`
- GitHub already provides a `recordingLink`
- The database already has a `recording_link` for the event

When a live is created successfully, the YouTube watch URL is saved into `recording_link`.

## Setup

### 1. Enable the YouTube Data API

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with your Google account

2. **Create or select a project** — at the top left, click the project dropdown and either pick an existing project or click **New Project**

3. **Enable the API:**
   - In the left sidebar, go to **APIs & Services → Library**

4. Search for **YouTube Data API v3**

5. Click on it, then click the blue **Enable** button

Once that's done, you can move on to Step 2 in your doc — creating OAuth credentials.

### 2. Create OAuth Credentials

The YouTube API must act as the real YouTube account that owns the channel. Service accounts do not work for YouTube channel live management.

1. In [Google Cloud Console](https://console.cloud.google.com), go to **APIs & Services → Credentials** in the left sidebar

2. Click **+ Create Credentials** at the top, then choose **OAuth client ID**

3. If prompted to configure a consent screen first:
   - Click **Configure Consent Screen**
   - Choose **External** (unless you're in a Google Workspace org)
   - Fill in the required app name and email fields
   - Save and go back to Credentials

4. Back on the **Create OAuth client ID** page, set **Application type** to **Web application**

5. Give it a name (e.g., `YouTube Bot Web`)

6. Under **Authorized redirect URIs**, add:
   - `https://developers.google.com/oauthplayground`

7. Click **Create**

8. A popup will show your **Client ID** and **Client Secret** — copy both and save them somewhere safe (you'll need them for your `.env` file and the next step)

If you are already on a **Desktop app** OAuth client page and do not see where to add redirect URIs:

1. Click the **back arrow** to return to the Credentials list
2. Click **+ Create Credentials** → **OAuth client ID**
3. Choose **Web application**
4. Give it a name (for example, `YouTube Bot Web`)
5. In **Authorized redirect URIs**, add `https://developers.google.com/oauthplayground`
6. Click **Create**
7. Copy the new **Client ID** and **Client Secret**

### 3. Generate a Refresh Token

Use the same Google account that owns the YouTube channel.

1. Open the OAuth Playground: https://developers.google.com/oauthplayground/
2. Open the settings gear
3. Enable **Use your own OAuth credentials**
4. Paste your OAuth client ID and client secret, make sure **Access type** is **Offline**, then click **Close**
5. In **Input your own scopes**, paste `https://www.googleapis.com/auth/youtube`
6. Click **Authorize APIs**
7. Sign in with the YouTube channel owner account and accept permissions
8. In Step 2, click **Exchange authorization code for tokens**
9. Copy the `refresh_token`

If you get `Error 400: redirect_uri_mismatch`, your OAuth client is likely a **Desktop app**. Create a **Web application** OAuth client and add `https://developers.google.com/oauthplayground` to **Authorized redirect URIs**, then retry.

After creating the Web application OAuth client:

1. Open OAuth Playground settings again
2. Replace the old credentials with the new **Client ID** and **Client Secret**
3. Retry **Authorize APIs**

If the bot logs `google.auth.exceptions.RefreshError: unauthorized_client`:

1. Confirm `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` are from the same OAuth app
2. Confirm `YOUTUBE_REFRESH_TOKEN` was generated using that exact OAuth app (same client ID/secret pair)
3. Regenerate the refresh token in OAuth Playground with **Use your own OAuth credentials** enabled
4. Ensure the OAuth app is still enabled and not deleted/rotated in Google Cloud Console

If the bot logs `liveStreamingNotEnabled` or `The user is not enabled for live streaming`:

1. Sign in with the same account used in `YOUTUBE_REFRESH_TOKEN`
2. Open https://www.youtube.com/features and enable live streaming
3. Wait for YouTube activation to complete (it may take up to 24 hours for first-time enablement)
4. Restart the bot after activation so scheduling attempts resume
5. Confirm the OAuth token is for the same channel you enabled (Brand Accounts can use a different channel than your personal profile)
6. If needed, regenerate `YOUTUBE_REFRESH_TOKEN` while signed into the correct channel identity

If the bot logs `liveStreamNotFound` or `Stream not found`:

1. Confirm `YOUTUBE_STREAM_ID` is the liveStream resource id from `liveStreams.list` with `mine=true`
2. Do not use the stream key shown in encoder settings (OBS), video/watch id, or broadcast id
3. Confirm the stream belongs to the same channel authenticated by `YOUTUBE_REFRESH_TOKEN`
4. Update `.env` with the correct stream id and restart the bot

### 4. Create One Reusable YouTube Stream

This bot uses one reusable YouTube stream configuration and links each scheduled live page to it.

1. Go to [YouTube Studio](https://studio.youtube.com), click **Create** → **Go Live**
2. Create or select one stream/encoder setup to reuse
3. Get the value for `YOUTUBE_STREAM_ID` using **API Explorer** (recommended):
   - Open: [liveStreams.list](https://developers.google.com/youtube/v3/docs/liveStreams/list)
   - Set `part` to `id,snippet`
   - Set `mine` to `true`
   - Execute and sign in with the channel owner account
   - Copy the stream `id` from the response
4. Save this value as `YOUTUBE_STREAM_ID` in `.env`

This is the simplest setup because the bot only creates the scheduled live page and reuses the same stream configuration each time.

Important:

- `YOUTUBE_STREAM_ID` must be the YouTube **liveStream resource ID**
- Do **not** use the stream key shown for OBS/encoder setup
- Do **not** use the video/watch page ID

### 5. Configure Environment Variables

Add these variables to your `.env` file:

```env
YOUTUBE_CLIENT_ID=YOUR_GOOGLE_OAUTH_CLIENT_ID
YOUTUBE_CLIENT_SECRET=YOUR_GOOGLE_OAUTH_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN=YOUR_GOOGLE_OAUTH_REFRESH_TOKEN
YOUTUBE_STREAM_ID=YOUR_REUSABLE_YOUTUBE_STREAM_ID
```

## Behavior Details

- New YouTube lives are created as `public`
- The event banner image is uploaded as the YouTube thumbnail when available
- The saved `recording_link` may temporarily point to the scheduled YouTube watch page before the event happens
- If the YouTube environment variables are missing, the bot logs the problem and skips YouTube scheduling without breaking Discord event creation

## Notes

- The bot uses the existing event banner from the website repository
- The bot keeps retrying future eligible events on the next sync if YouTube scheduling fails and `recording_link` is still empty
