import discord
from datetime import datetime, timezone

def format_problem_message(problem_data):
    question = problem_data.get('question', {})

    # Extract basic info
    title = question.get('title', 'Unknown Problem')
    problem_id = question.get('frontendQuestionId', '?')
    difficulty = question.get('difficulty', 'Unknown')
    acceptance_rate = question.get('acRate', 0)
    link = f"https://leetcode.com{problem_data.get('link', '')}"

    # Get topic tags
    topics = question.get('topicTags', [])
    topic_names = [tag.get('name', '') for tag in topics[:5]]  # Limit to 5 topics
    topics_str = ', '.join(topic_names) if topic_names else 'N/A'

    # Determine difficulty emoji and color
    difficulty_emoji = {
        'Easy': '🟢',
        'Medium': '🟡',
        'Hard': '🔴'
    }.get(difficulty, '⚪')

    # Create embed
    embed = discord.Embed(
        title=f"🚀 LeetCode Problem of the Day",
        description=f"**{problem_id}. {title}**",
        url=link,
        color=get_difficulty_color(difficulty),
        timestamp=datetime.now(timezone.utc))

    embed.add_field(
        name="Difficulty",
        value=f"{difficulty_emoji} {difficulty}",
        inline=True)

    embed.add_field(
        name="Acceptance Rate",
        value=f"{acceptance_rate:.1f}%",
        inline=True)

    embed.add_field(
        name="Topics",
        value=topics_str,
        inline=False)

    embed.add_field(
        name="🔗 Solve Now",
        value=f"[Click here to solve the problem]({link})",
        inline=False)

    embed.set_footer(text="Happy coding! 💻")

    return embed

def get_difficulty_color(difficulty):
    colors = {
        'Easy': 0x00ff00,    # Green
        'Medium': 0xffa500,  # Orange
        'Hard': 0xff0000     # Red
    }
    return colors.get(difficulty, 0x808080)  # Gray default
