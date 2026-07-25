import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import discord


def admin_guilds(bot, user_id):
    guilds = []
    for guild in bot.guilds:
        member = guild.get_member(user_id)
        if member and member.guild_permissions.administrator:
            guilds.append(guild)
    return guilds


def is_server_admin(bot, user_id):
    return len(admin_guilds(bot, user_id)) > 0


def find_role(guild, role_name):
    return discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)


def find_members(guild, user):
    if user.lower() == '@all':
        return list(guild.members)

    match = re.fullmatch(r'<@!?(\d+)>', user) or re.fullmatch(r'(\d+)', user)
    if match:
        member = guild.get_member(int(match.group(1)))
        return [member] if member else []

    target = user.lower()
    return [
        m for m in guild.members
        if target == m.name.lower()
        or target == m.display_name.lower()
        or target == (m.global_name or '').lower()
    ]


def format_uptime(started_at):
    delta = datetime.now(timezone.utc) - started_at
    days, seconds = delta.days, delta.seconds
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{days}d {hours}h {minutes}m {seconds}s'


def is_valid_url(url: str) -> bool:
    url = url.strip()
    if not url or ' ' in url:
        return False

    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


async def send_chunked(user, text: str, limit: int = 2000):
    lines = text.split('\n')
    chunk = ''
    for line in lines:
        # Split lines that are themselves longer than the limit into safe slices
        while len(line) > limit:
            slice_, line = line[:limit], line[limit:]
            if chunk:
                await user.send(chunk)
                chunk = ''
            await user.send(slice_)

        candidate = chunk + '\n' + line if chunk else line
        if len(candidate) > limit:
            if chunk:
                await user.send(chunk)
            chunk = line
        else:
            chunk = candidate
    if chunk:
        await user.send(chunk)
