from discord.ext import commands


async def setup(bot):
    await bot.add_cog(RulesCommand(bot))


class RulesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name = 'rules', help = 'Envia as regras para o utilizador')
    async def rules(self, ctx):
        print(f'[BOT][COMMAND][RULES] User "{ctx.author.name}" requested the rules')
        await ctx.author.send(rules_message)
        await ctx.message.delete()
        # await ctx.send(rules_message)


rules_message = '''
**Bem-vindo à nossa Comunidade**
Somos uma comunidade onde a conversa, colaboração e criatividade se encontram. Aqui, cada linha de código importa, e cada decisão de design molda o futuro.

**Regras:**
* Respeitar todos os membros;
* Ter cuidado com a linguagem utilizada;
* Evitar expressar visões políticas;
* Evitar expressar crenças religiosas;
* Mensagens preconceituosas ou discriminatórias serão removidas, e o responsável será banido;
* És responsável por tudo o que dizes e escreves;
* Usar os canais corretos para comunicação;
* Nenhuma pergunta é estúpida. Se não quiseres responder, simplesmente abstém-te;
* Fazer o mínimo de pesquisa antes de perguntar algo. Google ou ChatGPT funcionam 24 horas por dia. Depois disso, estamos aqui para o que der e vier.

**Para quem é esta comunidade?**
* És um developer? Temos vários canais para ti.
* Trabalhas com infraestrutura? O mundo precisa de ti. E esta comunidade também.
* És um DevOps? Vamos fazer tudo funcionar.
* És um engenheiro de dados? Aqui, dados são abundantes.
* És um engenheiro de machine learning? Vamos aprender juntos.
* És um designer? Design é tecnologia. Estamos contigo.
* És um estudante? Incomoda estas pessoas porque um dia elas fizeram o mesmo.
'''
