import os
import discord
from discord.ext import commands
import logging

from ._helpers import admin_guilds, find_role, find_members

logger = logging.getLogger(__name__)


class AddRoleCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add-role', help='Adiciona um role a um utilizador ou a todos com @all (apenas administradores, via DM)')
    @commands.dm_only()
    async def add_role(self, ctx, user: str, *, role_name: str):
        logger.debug(f'[BOT][COMMAND][ADD-ROLE] User "{ctx.author.name}" requested to add role "{role_name}" to "{user}"')

        guilds = admin_guilds(self.bot, ctx.author.id)
        if not guilds:
            logger.warning(f'[BOT][COMMAND][ADD-ROLE] User "{ctx.author.name}" is not a server admin. Ignoring')
            return

        summary = []
        for guild in guilds:
            role = find_role(guild, role_name)
            if role is None:
                logger.warning(f'[BOT][COMMAND][ADD-ROLE] Role "{role_name}" not found in guild "{guild.name}"')
                summary.append(f'❌ {guild.name}: role "{role_name}" não encontrado')
                continue

            if user.lower() == '@all':
                members = [m async for m in guild.fetch_members(limit=None)]
                max_members = int(os.environ.get('ADD_ROLE_ALL_MAX_MEMBERS', '3000'))
                if len(members) > max_members:
                    logger.warning(
                        f'[BOT][COMMAND][ADD-ROLE] @all request in guild "{guild.name}" aborted: '
                        f'{len(members)} members exceeds cap of {max_members}'
                    )
                    summary.append(
                        f'⚠️ {guild.name}: operação cancelada para @all '
                        f'({len(members)} utilizador(es), limite {max_members})'
                    )
                    continue
                await ctx.author.send(
                    f'⏳ {guild.name}: a adicionar role "{role.name}" a {len(members)} utilizador(es)...'
                )
            else:
                members = find_members(guild, user)

            if not members:
                logger.warning(f'[BOT][COMMAND][ADD-ROLE] User "{user}" not found in guild "{guild.name}"')
                summary.append(f'❌ {guild.name}: utilizador "{user}" não encontrado')
                continue

            assigned = 0
            failed = 0
            for member in members:
                try:
                    await member.add_roles(role, reason=f'Requested by admin {ctx.author.name}')
                    assigned += 1
                    logger.info(f'[BOT][COMMAND][ADD-ROLE] Added role "{role.name}" to "{member.name}" in guild "{guild.name}"')
                except discord.Forbidden:
                    failed += 1
                    logger.warning(f'[BOT][COMMAND][ADD-ROLE] Missing permissions to add role "{role.name}" to "{member.name}" in guild "{guild.name}"')
                except Exception:
                    failed += 1
                    logger.exception(f'[BOT][COMMAND][ADD-ROLE] Failed to add role "{role.name}" to "{member.name}" in guild "{guild.name}"')

            line = f'✅ {guild.name}: role "{role.name}" adicionado a {assigned} utilizador(es)'
            if failed:
                line += f' ({failed} falha(s) - verifica as permissões do bot)'
            summary.append(line)
            logger.info(f'[BOT][COMMAND][ADD-ROLE] Added role "{role.name}" to {assigned} member(s) in guild "{guild.name}" ({failed} failures)')

        await ctx.author.send('\n'.join(summary))
