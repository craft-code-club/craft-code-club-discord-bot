import logging
import aiohttp
from typing import Any, Dict, Optional
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

        events = {}

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
                # Convert date and time to datetime object - Brazilian timezone (UTC-3)
                event_time_range = event_data.get('time', '')
                event_time_start = f'{event_time_range.split('-')[0]}:00'
                event_datetime_str = f"{event_date}T{event_time_start}"

                event_datetime_brazilian = datetime.fromisoformat(event_datetime_str)
                # Convert to UTC

                # Create CommunityEvent object
                event = CommunityEvent(
                    id=event_id,
                    title=event_data.get('title', ''),
                    description=event_data.get('description', ''),
                    start_datetime=event_datetime_brazilian,
                    location=event_data.get('location', ''),
                    type=event_data.get('type', 'online'),
                    registration_link=event_data.get('registrationLink'),
                    recording_link=event_data.get('recordingLink'),
                    post_link=event_data.get('postLink'),
                    github_url=url,
                    speakers=event_data.get('speakers', []))

                logger.debug(f'[SERVICES][GITHUB][EVENTS] Parsed event: {event.title} ({event.id})')

                return event

    def __parse_community_event(self, content: str) -> Optional[Dict[str, Any]]:
        # Extract frontmatter between --- markers
        if not content.startswith('---'):
            raise Exception('Frontmatter does not start with "---"')

        end_marker = content.find('---', 3)
        if end_marker == -1:
            raise Exception('Frontmatter does not end with "---"')

        try:
            frontmatter = content[3:end_marker].strip()

            # Simple YAML parsing for the event fields we need
            event_data = {}

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

            # Handle speakers array (simple parsing)
            if 'speakers' in content:
                speakers = []
                in_speakers = False
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if line == 'speakers:':
                        in_speakers = True
                        continue
                    elif in_speakers:
                        if line.startswith('- '):
                            speaker = line[2:].strip()
                            if speaker.startswith('"') and speaker.endswith('"'):
                                speaker = speaker[1:-1]
                            elif speaker.startswith("'") and speaker.endswith("'"):
                                speaker = speaker[1:-1]
                            speakers.append(speaker)
                        elif not line.startswith(' ') and ':' in line:
                            break

                if speakers:
                    event_data['speakers'] = speakers

            return event_data

        except Exception as e:
            raise Exception(f'Error parsing Community Event: {e}')


# Global instance
github_service = GitHubService()
