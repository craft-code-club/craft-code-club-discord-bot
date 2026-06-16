import logging
import aiohttp
from typing import Any, Dict
from datetime import datetime
from usescases.community_events.community_event import CommunityEvent

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.github_owner = "craft-code-club"
        self.github_repo = "blog-c3"
        self.events_path = "_content/events"
        self.base_url = "https://api.github.com"
        self.website_url = "https://craftcodeclub.io/events"

    async def fetch_community_events(self) -> Dict[str, str]:
        logger.debug('[SERVICES][GITHUB][EVENTS] Fetching community events from GitHub repository...')

        events: Dict[str, str] = {}

        # Get all markdown files from the events directory
        files_url = f"{self.base_url}/repos/{self.github_owner}/{self.github_repo}/contents/{self.events_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(files_url) as response:
                if response.status != 200:
                    raise Exception(f'Get Community Events failed with status code {response.status}')

                files_data = await response.json()

                # Process each markdown file
                for file_info in files_data:
                    event_name = file_info['name']
                    if event_name.endswith('.md'):
                        events[event_name] = file_info['download_url']

        logger.debug(f'[SERVICES][GITHUB][EVENTS] Successfully fetched {len(events)} events from GitHub')
        return events

    async def fetch_community_event(self, url: str) -> CommunityEvent:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Get Community Event file '{url}' failed with status code {response.status}")

                content = await response.text()

                # Parse the markdown frontmatter
                event_data = self.__parse_community_event(content)

                # Extract event name file from URL
                event_id = url.split('/')[-1].replace('.md', '')

                event_date = event_data.get('date', '')

                # Brazilian timezone (UTC-3)
                event_time_range = event_data.get('time', '')
                event_time_range_parts = event_time_range.split('-')

                start_event_time = f'{event_time_range_parts[0]}:00'
                end_event_time = f'{event_time_range_parts[1]}:00'

                start_event_time_str = f"{event_date}T{start_event_time}"
                end_event_time_str = f"{event_date}T{end_event_time}"

                start_event_datetime_brazilian = datetime.fromisoformat(start_event_time_str)
                end_event_datetime_brazilian = datetime.fromisoformat(end_event_time_str)

                # Create CommunityEvent object
                event = CommunityEvent(
                    id = event_id,
                    title = event_data.get('title', ''),
                    description = event_data.get('description', ''),
                    start_datetime = start_event_datetime_brazilian,
                    end_datetime = end_event_datetime_brazilian,
                    location = event_data.get('location', ''),
                    type = event_data.get('type', 'online'),
                    banner = event_data.get('banner', None),
                    is_live = str(event_data.get('isLive', '')).strip().lower() == 'true',
                    youtube_title = event_data.get('youtubeTitle') or None,
                    registration_link = event_data.get('registrationLink'),
                    recording_link = event_data.get('recordingLink'),
                    session_link = event_data.get('sessionLink'),
                    post_link = event_data.get('postLink'),
                    github_url = url,
                    speakers = event_data.get('speakers', []),
                    tags = event_data.get('tags', []))

                logger.debug(f'[SERVICES][GITHUB][EVENTS] Parsed event: {event.title} ({event.id})')

                return event

    def __parse_community_event(self, content: str) -> Dict[str, Any]:
        # Extract frontmatter between --- markers
        if not content.startswith('---'):
            raise Exception('Frontmatter does not start with "---"')

        end_marker = content.find('---', 3)
        if end_marker == -1:
            raise Exception('Frontmatter does not end with "---"')

        try:
            frontmatter = content[3:end_marker].strip()

            # Simple YAML parsing for the event fields we need
            event_data: Dict[str, Any] = {}

            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes from string values
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    event_data[key] = value

            speakers = self.__parse_frontmatter_list(frontmatter, 'speakers')
            if speakers:
                event_data['speakers'] = speakers

            tags = self.__parse_frontmatter_list(frontmatter, 'tags')
            if tags:
                event_data['tags'] = tags
            else:
                raw_tags = event_data.get('tags')
                if not isinstance(raw_tags, str):
                    raw_tags = ''

                event_data['tags'] = [
                    tag.strip()
                    for tag in raw_tags.split(',')
                    if tag.strip()]

            return event_data

        except Exception as e:
            raise Exception(f'Error parsing Community Event: {e}')

    def __parse_frontmatter_list(self, frontmatter: str, key: str) -> list[str]:
        values: list[str] = []
        in_section = False

        for raw_line in frontmatter.split('\n'):
            line = raw_line.strip()
            if line == f'{key}:':
                in_section = True
                continue

            if not in_section:
                continue

            if line.startswith('- '):
                value = line[2:].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                if value:
                    values.append(value)
                continue

            if ':' in line and not line.startswith('- '):
                break

        return values


# Global instance
github_service = GitHubService()
