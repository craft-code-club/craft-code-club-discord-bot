import discord
import re
from markdownify import markdownify as md

class LeetCodeProblemFormatter:

    def format_to_forum_post(self, problem_data):
        question = problem_data.get('question', {})
        title = question.get('title', 'Unknown Problem')
        problem_id = question.get('frontendQuestionId', '?')
        thread_title = f"{problem_id}. {title}"

        # Format from html to markdown
        content = question.get('content', '')
        if content:
            content = self.__convert_html_to_markdown(content)

        return {
            "name": thread_title,
            "embed": self.format_to_message(problem_data),
            "content": content,
            "reason": "Daily LeetCode problem"
        }


    def format_to_message(self, problem_data):
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
            title = f"🚀 LeetCode Problem of the Day",
            description = f"**{problem_id}. {title}**",
            url = link,
            color = self.__get_difficulty_color(difficulty))


        embed.add_field(
            name = "Dificuldade",
            value = f"{difficulty_emoji} {difficulty}",
            inline = True)

        embed.add_field(
            name = "Taxa de Aceitação",
            value = f"{acceptance_rate:.1f}%",
            inline = True)

        embed.add_field(
            name = "Tópicos",
            value = topics_str,
            inline = False)

        embed.add_field(
            name = "🔗 Resolve agora",
            value = f"[Clique aqui para resolver o problema]({link})",
            inline = False)

        return embed

    def __get_difficulty_color(self, difficulty):
        colors = {
            'Easy': 0x00ff00,    # Green
            'Medium': 0xffa500,  # Orange
            'Hard': 0xff0000     # Red
        }
        return colors.get(difficulty, 0x808080)  # Gray default

    def __convert_html_to_markdown(self, html_content) -> str:
        if not html_content:
            return ''

        # replace cases like <sup>1</sup> to ^number
        html_content = re.sub(r'<sup>(\d+)</sup>', r'^\1', html_content)

        # Convert HTML to markdown with custom settings
        markdown = md(
            html_content,
            heading_style='ATX',  # Use # for headings
            bullets='-',          # Use - for bullet points
            strip=['script', 'style', 'img']  # Remove script, style, and img tags
        )

        # Clean up extra whitespace and newlines
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)  # Remove excessive newlines
        markdown = markdown.strip()

        return markdown


# Global instance
leet_code_formatter = LeetCodeProblemFormatter()
