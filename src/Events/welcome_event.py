from discord.ext import commands
import discord


async def setup(bot):
    await bot.add_cog(WelcomeEvent(bot))


class WelcomeEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if member.bot:
            print(f'[BOT][EVENT][WELCOME] Bot "{member.name}" joined the server')
            return

        print(f'[BOT][EVENT][WELCOME] "{member.name}" joined the server')


        try:
            system_channel = member.guild.system_channel
            if system_channel:
                # system_channel_name = system_channel.name
                # system_channel_id = system_channel.id
                await system_channel.send(f'Olá {member.mention}! 👋 Bem-vindo a nossa comunidade')
        except Exception as e:
            print(f'[BOT][ERROR][EVENT][WELCOME]: It was not possible to send a welcome message to the system channel: {e}')


        try:
            await member.send(get_welcome_message(member.name))
        except discord.errors.Forbidden: # If the user has DMs disabled
            print(f'[BOT][ERROR][EVENT][WELCOME]: The user "{member.name}" has DMs disabled')



def get_welcome_message(username: str) -> str:
    ### It is important mantain the text formatation with f''' and align in left side to preserve the message formatation in Discord
    return f'''
Olá, **{username}**! 👋

Bem-vindo(a) à comunidade Craft & Code Club! Estamos muito contentes por ter-te aqui. 🚀

Aqui, a paixão e o conhecimento encontram-se num amplo espectro que inclui programação, infraestrutura, cloud computing, DevOps, e muito mais. Participamos ativamente em conversas ricas e envolventes sobre temas como system design, arquitetura de software, além de um foco especial em algoritmos e estruturas de dados. Também promovemos debates animados sobre o problema do dia do LeetCode, incentivando a resolução e partilha de soluções.

**Confere os nossos encontros:**

- **Clube do Livro Tech:** Às segundas, atualmente exploramos "ByteByteGo / System Design Interview".
- **Algorithms & Data Structures - From Zero to Hero:** Às sextas, cobrimos desde os conceitos fundamentais até técnicas avançadas.

Partilhamos o link dos nossos encontros no canal #events, para que possas participar e contribuir ativamente.

Não te esqueças de consultar `/rules` para conhecer as regras da nossa comunidade ou visitar o canal #rules.

**Conecta-te connosco através das nossas redes sociais:**

- **YouTube:** [CraftCodeClub](https://www.youtube.com/@CraftCodeClub)
- **Meetup:** [Eventos](https://www.meetup.com/craft-code-club/events/)
- **GitHub:** [Craft-Code-Club](https://github.com/craft-code-club)
- **Instagram:** [@craftcodeclub](https://www.instagram.com/craftcodeclub/)
- **LinkedIn:** [Grupo](https://www.linkedin.com/groups/9557921/)

Aguardamos com expectativa tua participação ativa. Juntos, avançaremos, aprendendo, compartilhando e crescendo em comunidade.

Bem-vindo e até já! 🌟
'''

# Não te esqueças de consultar `/rules` para conhecer as regras da nossa comunidade ou visitar o canal #rules. Se precisares de assistência, utiliza `/help` para descobrir os comandos disponíveis e maximizar tua experiência no nosso espaço.
