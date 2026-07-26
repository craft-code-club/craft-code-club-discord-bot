import re
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
import discord

logger = logging.getLogger(__name__)


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


async def parse_event_link_args(ctx, args, bot, command_name, link_label):
    """
    Handles the common boilerplate for event link commands: admin check, -f flag
    parsing, argument count/format validation, DAO loading, and event retrieval.

    Returns (force, event_key, link, dao, event) on success, or None if an error
    was already sent to the user and the caller should return early.
    """
    log_prefix = f'[BOT][COMMAND][{command_name.upper()}]'

    logger.debug(f'{log_prefix} User "{ctx.author.name}" invoked command with args {args}')

    if not is_server_admin(bot, ctx.author.id):
        logger.warning(f'{log_prefix} User "{ctx.author.name}" is not a server admin. Ignoring')
        return None

    args_list = list(args)
    force = False
    if args_list and args_list[0] == '-f':
        force = True
        args_list = args_list[1:]

    if len(args_list) != 2:
        await ctx.author.send(
            f'❌ Uso incorreto. Sintaxe: `/{command_name} [-f] <eventId> <{link_label}>`\n'
            f'O `-f` força a atualização quando o evento já tem um {link_label}.'
        )
        return None

    event_key, link = args_list
    link = link.strip()

    if not re.fullmatch(r'[A-Za-z0-9_-]+', event_key):
        logger.warning(f'{log_prefix} Invalid event key "{event_key}" provided by "{ctx.author.name}"')
        await ctx.author.send(
            f'❌ Event key inválida: `{event_key}`. Use apenas letras, números, "-" e "_".'
        )
        return None

    if not is_valid_url(link):
        logger.warning(f'{log_prefix} Invalid URL "{link}" provided by "{ctx.author.name}"')
        await ctx.author.send(f'❌ Link inválido: `{link}`. Forneça um URL válido com esquema http ou https.')
        return None

    try:
        from usescases.community_events.community_events_dao import community_events_dao as dao
    except Exception:
        logger.exception(f'{log_prefix} Failed to initialize community events DAO')
        await ctx.author.send('❌ Não foi possível conectar ao armazenamento de eventos. Verifica a configuração do Azure Storage.')
        return None

    event = dao.get(event_key)
    if event is None:
        logger.warning(f'{log_prefix} Event "{event_key}" not found (requested by "{ctx.author.name}")')
        await ctx.author.send(f'❌ Evento não encontrado: `{event_key}`.')
        return None

    return force, event_key, link, dao, event
