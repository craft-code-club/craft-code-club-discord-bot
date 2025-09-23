import logging
import aiohttp

logger = logging.getLogger(__name__)

async def fetch_daily_problem():
    # LeetCode GraphQL endpoint for daily challenge
    url = "https://leetcode.com/graphql"

    query = """
    query questionOfToday {
        activeDailyCodingChallengeQuestion {
            date
            userStatus
            link
            question {
                acRate
                difficulty
                freqBar
                frontendQuestionId: questionFrontendId
                isFavor
                paidOnly: isPaidOnly
                status
                title
                titleSlug
                hasVideoSolution
                hasSolution
                topicTags {
                    name
                    id
                    slug
                }
                content
                stats
            }
        }
    }
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json={'query': query},
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }) as response:
                if response.status != 200:
                    raise Exception(f"Query LeetCode failed with status code {response.status}")

                data = await response.json()
                return data.get('data', {}).get('activeDailyCodingChallengeQuestion')
