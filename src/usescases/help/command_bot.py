import discord
from discord.ext import commands
import logging

from usescases.admin._helpers import is_server_admin

logger = logging.getLogger(__name__)


async def setup(bot):
    await bot.add_cog(HelpCommandBot(bot))


class HelpCommandBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help', help='Mostra a lista de comandos disponíveis (enviada via DM)', extras={'scope': 'Servidor e DM'})
    async def help(self, ctx):
        logger.debug(f'[BOT][COMMAND][HELP] User "{ctx.author.name}" requested the help')

        is_admin = is_server_admin(self.bot, ctx.author.id)

        commands_list = sorted(
            (cmd for cmd in self.bot.commands if not cmd.hidden),
            key=lambda cmd: cmd.name,
        )

        general = [cmd for cmd in commands_list if not cmd.extras.get('admin', False)]
        admin = [cmd for cmd in commands_list if cmd.extras.get('admin', False)]

        embed = discord.Embed(
            title='Comandos disponíveis',
            description='Aqui estão os comandos que podes utilizar. Invoca-os com o prefixo `/`.',
            color=discord.Color.blurple(),
        )

        self._add_commands_to_embed(embed, 'Comandos', general)
        if is_admin and admin:
            self._add_commands_to_embed(embed, 'Comandos de administração', admin)

        try:
            await ctx.author.send(embed=embed)
            logger.info(f'[BOT][COMMAND][HELP] Sent help to user "{ctx.author.name}" (admin={is_admin})')
        except discord.errors.Forbidden:
            logger.warning(f'[BOT][COMMAND][HELP] User "{ctx.author.name}" has DMs disabled')

        if ctx.guild is not None:
            try:
                await ctx.message.delete()
                logger.debug(f'[BOT][COMMAND][HELP] Message deleted successfully')
            except Exception:
                logger.exception(f'[BOT][COMMAND][HELP] Failed to delete command message')

    def _add_commands_to_embed(self, embed, section_title, cmds):
        if not cmds:
            return

        entries = []
        for cmd in cmds:
            description = cmd.help or 'Sem descrição.'
            scope = cmd.extras.get('scope', 'Servidor e DM')

            usage = f'/{cmd.name}'
            if cmd.extras.get('usage'):
                usage = f"{usage} {cmd.extras['usage']}"
            elif cmd.signature:
                usage = f'{usage} {cmd.signature}'

            entry = f'`{usage}` · {scope}\n{description}'

            notes = cmd.extras.get('notes')
            if notes:
                entry += f'\n_{notes}_'

            entries.append(entry)

        # Discord embed field values are capped at 1024 chars; chunk if needed.
        chunk, first = '', True
        for entry in entries:
            candidate = entry if not chunk else f'{chunk}\n\n{entry}'
            if len(candidate) > 1024:
                embed.add_field(name=section_title if first else '\u200b', value=chunk, inline=False)
                chunk, first = entry, False
            else:
                chunk = candidate

        if chunk:
            embed.add_field(name=section_title if first else '\u200b', value=chunk, inline=False)
