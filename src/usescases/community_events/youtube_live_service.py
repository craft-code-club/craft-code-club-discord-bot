import asyncio
import io
import logging
import os
import re
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from usescases.community_events.community_event import CommunityEvent
from utils.message_loader import load_message
from utils.timezones import get_brazil_timezone
from utils.image_service import DownloadedImage, image_service

logger = logging.getLogger(__name__)


class YouTubeLiveService:
    SCOPES = ['https://www.googleapis.com/auth/youtube']
    TOKEN_URI = 'https://oauth2.googleapis.com/token'
    GLOBAL_TAGS = ['CraftCodeClub', 'AI', 'ComputerScience', 'Coding', 'Development']

    def __init__(self) -> None:
        self.__live_streaming_disabled = False

    async def schedule_live_event(self, event: CommunityEvent) -> Optional[str]:
        if self.__live_streaming_disabled:
            logger.warning(
                f'[SERVICES][YOUTUBE] Skipping YouTube live scheduling for "{event.title}". '
                'Live streaming is not enabled for the configured YouTube account. '
                'Enable live streaming in YouTube Studio and restart the bot to retry.')
            return None

        missing_configuration = self.__missing_configuration()
        if missing_configuration:
            logger.warning(
                f'[SERVICES][YOUTUBE] Skipping YouTube live scheduling for "{event.title}". '
                f'Missing environment variables: {", ".join(missing_configuration)}')
            return None

        invalid_configuration = self.__invalid_configuration()
        if invalid_configuration:
            logger.warning(
                f'[SERVICES][YOUTUBE] Skipping YouTube live scheduling for "{event.title}". '
                f'Invalid environment variables (placeholder values detected): {", ".join(invalid_configuration)}')
            return None

        banner_url = event.banner_url()
        banner_image = await image_service.download_image(banner_url) if banner_url else None
        return await asyncio.to_thread(self.__create_live_broadcast, event, banner_image)

    def __create_live_broadcast(self, event: CommunityEvent, banner_image: Optional[DownloadedImage]) -> Optional[str]:
        youtube = None
        try:
            youtube = self.__build_client()
            stream_id = os.environ['YOUTUBE_STREAM_ID'].strip()

            if not self.__validate_stream_for_authenticated_channel(youtube, stream_id):
                return None

            logger.debug(f'[SERVICES][YOUTUBE] Creating scheduled live broadcast for "{event.title}"')

            broadcast = youtube.liveBroadcasts().insert(
                part = 'snippet,contentDetails,status',
                body = {
                    # Basic info about the live event
                    'snippet': {
                        'title': event.get_youtube_title(),  # Event title shown on YouTube
                        'description': self.__build_description(event),  # Video description with event details
                        'scheduledStartTime': self.__youtube_datetime(event.start_datetime),  # When the live is set to begin
                    },
                    # Visibility and audience settings
                    'status': {
                        'privacyStatus': 'public',  # Scheduled live is public as soon as YouTube creates it
                        'selfDeclaredMadeForKids': False,  # Content is not made for kids (affects ads & chat features)
                    },
                    # Stream behavior configuration
                    'contentDetails': {
                        'enableAutoStart': False,  # Keep False so the broadcast does not go live automatically when the encoder starts (allows manual setup/start)
                        'enableAutoStop': True,  # Stream automatically ends when encoder stops
                        'enableDvr': True,  # Viewers can rewind and replay during the stream
                        'recordFromStart': True,  # Full stream is saved as VOD (video on demand)
                        'enableLiveChat': True,  # Live chat is enabled during the stream
                        'enableContentEncryption': False,  # No DRM encryption (standard setting)
                    }
                }).execute()

            broadcast_id = broadcast['id']

            # Bind broadcast to reusable stream
            youtube.liveBroadcasts().bind(
                part = 'id,contentDetails',
                id = broadcast_id,
                streamId = stream_id).execute()

            if banner_image:
                self.__upload_thumbnail(youtube, broadcast_id, banner_image)

            watch_url = f'https://www.youtube.com/watch?v={broadcast_id}'

            logger.info(f'[SERVICES][YOUTUBE] Scheduled YouTube live for "{event.title}": {watch_url}')
            return watch_url
        except RefreshError as error:
            self.__log_refresh_error(event.title, error)
        except HttpError as error:
            if self.__is_live_streaming_not_enabled(error):
                self.__log_authenticated_channel(youtube)
                self.__live_streaming_disabled = True
                logger.error(
                    f'[SERVICES][YOUTUBE] Failed to schedule YouTube live for "{event.title}": {error}. '
                    'The authenticated YouTube account is not enabled for live streaming. '
                    'Enable live streaming at https://www.youtube.com/features and wait until YouTube activates it. '
                    'The bot will skip new YouTube scheduling attempts until it is restarted.',
                    exc_info = True)
                return None

            if self.__is_stream_not_found(error):
                self.__log_available_streams(youtube, os.environ.get('YOUTUBE_STREAM_ID', '').strip())
                logger.error(
                    f'[SERVICES][YOUTUBE] Failed to schedule YouTube live for "{event.title}": {error}. '
                    'The configured YOUTUBE_STREAM_ID was not found for the authenticated channel. '
                    'Use liveStreams.list with mine=true and copy the stream resource id (not stream key, not video id).',
                    exc_info = True)
                return None

            logger.exception(f'[SERVICES][YOUTUBE] YouTube API error while scheduling "{event.title}": {error}')
        except Exception:
            logger.exception(f'[SERVICES][YOUTUBE] Failed to schedule YouTube live for "{event.title}"')

        return None

    def __upload_thumbnail(self, youtube, broadcast_id: str, banner_image: DownloadedImage) -> None:
        try:
            media = MediaIoBaseUpload(
                io.BytesIO(banner_image.data),
                mimetype = banner_image.content_type,
                resumable = False)

            youtube.thumbnails().set(videoId = broadcast_id, media_body = media).execute()

            logger.info(f'[SERVICES][YOUTUBE] Uploaded thumbnail for broadcast Id "{broadcast_id}"')
        except HttpError as error:
            logger.warning(f'[SERVICES][YOUTUBE] Failed to upload thumbnail for broadcast Id "{broadcast_id}": {error}')
        except Exception:
            logger.warning(f'[SERVICES][YOUTUBE] Failed to upload thumbnail for broadcast Id "{broadcast_id}"', exc_info = True)

    def __build_client(self):
        credentials = Credentials(
            token = None,
            refresh_token = os.environ['YOUTUBE_REFRESH_TOKEN'],
            token_uri = self.TOKEN_URI,
            client_id = os.environ['YOUTUBE_CLIENT_ID'],
            client_secret = os.environ['YOUTUBE_CLIENT_SECRET'],
            scopes = self.SCOPES)

        credentials.refresh(Request())

        return build('youtube', 'v3', credentials = credentials, cache_discovery = False)

    def __missing_configuration(self) -> list[str]:
        missing = []
        for env_var in ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN', 'YOUTUBE_STREAM_ID']:
            if not os.environ.get(env_var):
                missing.append(env_var)
        return missing

    def __invalid_configuration(self) -> list[str]:
        placeholders = ['your_', 'your_google_oauth_', 'your_reusable_youtube_stream_id', 'YOUR_GOOGLE_OAUTH_']
        invalid = []

        for env_var in ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REFRESH_TOKEN', 'YOUTUBE_STREAM_ID']:
            value = os.environ.get(env_var, '').strip()
            if value and any(placeholder in value for placeholder in placeholders):
                invalid.append(env_var)

        return invalid

    def __log_refresh_error(self, event_title: str, error: RefreshError) -> None:
        details = str(error)
        if 'unauthorized_client' in details.lower():
            logger.error(
                f'[SERVICES][YOUTUBE] Failed to refresh OAuth token while scheduling "{event_title}": {details}. '
                'The OAuth client is not authorized for this refresh token. '
                'Confirm YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET belong to the same OAuth app used to issue '
                'YOUTUBE_REFRESH_TOKEN, and regenerate the refresh token with OAuth Playground using your own credentials.',
                exc_info = True)
            return

        logger.exception(
            f'[SERVICES][YOUTUBE] Failed to refresh OAuth token while scheduling "{event_title}": {details}')

    def __is_live_streaming_not_enabled(self, error: HttpError) -> bool:
        details = str(error).lower()
        return 'livestreamingnotenabled' in details or 'not enabled for live streaming' in details

    def __is_stream_not_found(self, error: HttpError) -> bool:
        details = str(error).lower()
        return 'livestreamnotfound' in details or 'stream not found' in details

    def __validate_stream_for_authenticated_channel(self, youtube, configured_stream_id: str) -> bool:
        if not configured_stream_id:
            logger.error('[SERVICES][YOUTUBE] YOUTUBE_STREAM_ID is empty after trimming spaces.')
            return False

        try:
            response = youtube.liveStreams().list(part = 'id,snippet,status', mine = True, maxResults = 50).execute()
            items = response.get('items', [])

            if not items:
                logger.error(
                    '[SERVICES][YOUTUBE] The authenticated channel has no reusable live streams configured. '
                    'Create one in YouTube Studio and set YOUTUBE_STREAM_ID to its stream resource id.')
                return False

            if any(item.get('id') == configured_stream_id for item in items):
                return True

            self.__log_available_streams(youtube, configured_stream_id, items)
            logger.error(
                f'[SERVICES][YOUTUBE] YOUTUBE_STREAM_ID "{configured_stream_id}" does not belong to the authenticated channel.')
            return False
        except Exception:
            logger.warning('[SERVICES][YOUTUBE] Failed to validate YOUTUBE_STREAM_ID before creating live broadcast.', exc_info = True)
            return True

    def __log_available_streams(self, youtube, configured_stream_id: str, streams: Optional[list[dict]] = None) -> None:
        try:
            stream_items = streams
            if stream_items is None:
                response = youtube.liveStreams().list(part = 'id,snippet,status', mine = True, maxResults = 50).execute()
                stream_items = response.get('items', [])

            if not stream_items:
                logger.warning(
                    f'[SERVICES][YOUTUBE] No streams found for authenticated channel while checking YOUTUBE_STREAM_ID "{configured_stream_id}".')
                return

            available_streams = []
            for item in stream_items[:10]:
                stream_id = item.get('id', '<unknown>')
                title = item.get('snippet', {}).get('title', '<untitled>')
                status = item.get('status', {}).get('streamStatus', '<unknown-status>')
                available_streams.append(f'{stream_id} (title="{title}", status={status})')

            logger.warning(
                f'[SERVICES][YOUTUBE] Configured YOUTUBE_STREAM_ID "{configured_stream_id}" was not found. '
                f'Available streams for the authenticated channel: {"; ".join(available_streams)}')
        except Exception:
            logger.warning('[SERVICES][YOUTUBE] Failed to list available streams while diagnosing stream configuration.', exc_info = True)

    def __log_authenticated_channel(self, youtube) -> None:
        try:
            response = youtube.channels().list(part = 'id,snippet', mine = True, maxResults = 1).execute()
            items = response.get('items', [])
            if not items:
                logger.warning('[SERVICES][YOUTUBE] Could not resolve authenticated YouTube channel from OAuth token (mine=true returned no channels).')
                return

            channel = items[0]
            channel_id = channel.get('id', '<unknown>')
            channel_title = channel.get('snippet', {}).get('title', '<unknown>')
            logger.warning(
                f'[SERVICES][YOUTUBE] OAuth token is authenticated as channel "{channel_title}" (Id: {channel_id}). '
                'If this is not the channel you enabled for live streaming, regenerate YOUTUBE_REFRESH_TOKEN using the correct account/channel.')
        except Exception:
            logger.warning('[SERVICES][YOUTUBE] Failed to resolve authenticated YouTube channel while diagnosing live streaming configuration.', exc_info = True)

    def __build_description(self, event: CommunityEvent) -> str:
        description_template = load_message('youtube_description_template.md')

        description_parts = [event.description.strip()] if event.description else []
        description_parts.append(f'📅 Evento: {event.event_details_url()}')

        hashtags = self.__build_hashtags(event.tags)

        return (description_template
                .replace('##[DESCRIPTION]##', '\n\n'.join(description_parts))
                .replace('##[HASH_TAGS]##', hashtags))

    def __build_hashtags(self, event_tags: Optional[list[str]]) -> str:
        unique_tags: list[str] = []
        seen_tags: set[str] = set()

        for raw_tag in [*self.GLOBAL_TAGS, *(event_tags or [])]:
            normalized_tag = self.__normalize_tag(raw_tag)
            if not normalized_tag:
                continue

            dedupe_key = normalized_tag.lower()
            if dedupe_key in seen_tags:
                continue

            seen_tags.add(dedupe_key)
            unique_tags.append(f'#{normalized_tag}')

        return ' '.join(unique_tags)

    def __normalize_tag(self, tag: str) -> str:
        sanitized = re.sub(r'[^A-Za-z0-9\-\s]', '', tag.strip().lstrip('#'))
        if not sanitized:
            return ''

        if '-' not in sanitized and ' ' not in sanitized and any(char.isupper() for char in sanitized):
            return sanitized

        words = [word for word in sanitized.replace('-', ' ').split() if word]
        return ''.join(word[:1].upper() + word[1:].lower() for word in words)

    def __youtube_datetime(self, event_datetime: datetime) -> str:
        sao_paulo_tz = get_brazil_timezone()
        if event_datetime.tzinfo is None:
            event_datetime = event_datetime.replace(tzinfo = sao_paulo_tz)
        return event_datetime.isoformat()


youtube_live_service = YouTubeLiveService()
