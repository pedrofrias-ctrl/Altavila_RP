import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import pandas as pd
import os
import re
import unicodedata
import io
import random

intents = discord.Intents.all()

WHITELIST_QUESTIONS = [
    "Qual seu nome no RP?",
    "Qual sua idade no RP?",
    "Por que quer entrar na cidade?",
    "O que significa VDM?",
    "O que significa RDM?",
    "Cite 3 regras básicas do servidor.",
    "Explique o que é PowerGaming.",
    "Explique o que é MetaGaming."
]

# Nome do canal de logs para o ticket
NOME_CANAL_LOGS = "📑・logs-tickets"
NOME_CANAL_LOGS_WHITELIST = "📑・logs-whitelist"
NOME_CANAL_VERIFICACAO = "✔️・verificação"
NOME_CARGO_VERIFICADO = "Verificado"

bot = commands.Bot(command_prefix="!", intents=intents)

# Função para limpar nomes de arquivos
def limpar_nome_arquivo(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome = re.sub(r'[\\/*?:"<>|]', "_", nome)
    return nome

# ------------------ PARTE 1: TICKET ------------------

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

    # ====== PARTE TICKET: enviar botão no canal de tickets ======
    for guild in bot.guilds:
        canal_ticket = discord.utils.get(guild.text_channels, name="🎫・tickets")
        canal_logs = discord.utils.get(guild.text_channels, name=NOME_CANAL_LOGS)

        if canal_ticket:
            try:
                button = Button(label="Abrir Ticket 🎫", style=discord.ButtonStyle.green)

                async def button_callback(interaction: discord.Interaction):
                    guild = interaction.guild

                    category = discord.utils.get(guild.categories, name="⚙️・tickets")
                    cargo_staff = discord.utils.get(guild.roles, name="Staff")

                    if not category or not cargo_staff:
                        await interaction.response.send_message(
                            "❌ Categoria ou cargo 'Staff' não encontrados.", ephemeral=True
                        )
                        return

                    existing = discord.utils.get(
                        guild.text_channels, name=f"ticket-{interaction.user.name.lower()}"
                    )
                    if existing:
                        await interaction.response.send_message(
                            f"❌ Você já possui um ticket aberto: {existing.mention}", ephemeral=True
                        )
                        return

                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
                        cargo_staff: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
                    }

                    ticket_channel = await guild.create_text_channel(
                        name=f"ticket-{interaction.user.name}",
                        category=category,
                        overwrites=overwrites,
                        topic=f"Ticket aberto por {interaction.user}"
                    )

                    atender_button = Button(label="🎧 Atender", style=discord.ButtonStyle.blurple)
                    encerrar_button = Button(label="❌ Encerrar Ticket", style=discord.ButtonStyle.red)

                    async def atender_callback(atender_interaction: discord.Interaction):
                        if cargo_staff not in atender_interaction.user.roles:
                            await atender_interaction.response.send_message(
                                "❌ Você não tem permissão para atender este ticket.", ephemeral=True
                            )
                            return

                        await atender_interaction.response.send_message(
                            f"🎧 {atender_interaction.user.mention} está atendendo este chamado!",
                            ephemeral=False
                        )

                        try:
                            await interaction.user.send(
                                f"👋 Olá {interaction.user.name}, seu ticket `{ticket_channel.name}` está sendo atendido por {atender_interaction.user.name}!"
                            )
                        except:
                            await atender_interaction.followup.send(
                                "⚠️ Não consegui enviar DM para o usuário.", ephemeral=True
                            )

                    async def encerrar_callback(encerrar_interaction: discord.Interaction):
                        if cargo_staff not in encerrar_interaction.user.roles:
                            await encerrar_interaction.response.send_message(
                                "❌ Você não tem permissão para encerrar este ticket.", ephemeral=True
                            )
                            return

                        confirm_view = View()
                        confirmar = Button(label="✅ Sim", style=discord.ButtonStyle.green)
                        cancelar = Button(label="❌ Não", style=discord.ButtonStyle.red)

                        async def confirmar_callback(button_interaction: discord.Interaction):
                            await button_interaction.response.send_message(
                                "🔒 Encerrando o ticket e gerando o log...", ephemeral=True
                            )

                            try:
                                transcript = f"📄 Transcrição do ticket {ticket_channel.name}\n\n"
                                async for msg in ticket_channel.history(limit=None, oldest_first=True):
                                    content = msg.content if msg.content else "[Mensagem sem texto]"
                                    transcript += f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author}: {content}\n"

                                if canal_logs:
                                    nome_arquivo = limpar_nome_arquivo(ticket_channel.name)
                                    import io
                                    file = discord.File(
                                        fp=io.BytesIO(transcript.encode('utf-8')),
                                        filename=f"{nome_arquivo}.txt"
                                    )
                                    await canal_logs.send(
                                        f"📑 Log do {ticket_channel.name} encerrado por {encerrar_interaction.user.mention}",
                                        file=file
                                    )
                                else:
                                    print("❌ Canal de logs não encontrado.")

                                # Envia mensagem privada ao usuário do ticket
                                try:
                                    await interaction.user.send(
                                        f"🔒 Seu ticket `{ticket_channel.name}` foi encerrado pela equipe. Se precisar de mais ajuda, abra um novo ticket!"
                                    )
                                except:
                                    pass

                                await ticket_channel.delete()

                            except Exception as e:
                                print(f"❌ Erro ao gerar log ou fechar ticket: {e}")

                        async def cancelar_callback(button_interaction: discord.Interaction):
                            await button_interaction.response.send_message(
                                "❌ Cancelado. O ticket não foi encerrado.", ephemeral=True
                            )

                        confirmar.callback = confirmar_callback
                        cancelar.callback = cancelar_callback

                        confirm_view.add_item(confirmar)
                        confirm_view.add_item(cancelar)

                        await encerrar_interaction.response.send_message(
                            "⚠️ Tem certeza que deseja encerrar este ticket?", view=confirm_view, ephemeral=True
                        )

                    atender_button.callback = atender_callback
                    encerrar_button.callback = encerrar_callback

                    view = View()
                    view.add_item(atender_button)
                    view.add_item(encerrar_button)

                    await ticket_channel.send(
                        embed=discord.Embed(
                            title="🎫 Ticket Aberto",
                            description=f"Ticket criado por {interaction.user.mention}\nAguarde um atendente...",
                            color=discord.Color.green()
                        ),
                        view=view
                    )

                    await interaction.response.send_message(
                        f"✅ Seu ticket foi criado: {ticket_channel.mention}", ephemeral=True
                    )

                button.callback = button_callback

                view = View()
                view.add_item(button)

                await canal_ticket.send(
                    embed=discord.Embed(
                        title="🎫 Sistema de Tickets",
                        description="Clique no botão abaixo para abrir um **ticket** e receber atendimento da equipe!",
                        color=discord.Color.green()
                    ),
                    view=view
                )
                print(f"✅ Botão enviado no canal {canal_ticket.name}")
            except Exception as e:
                print(f"❌ Erro ao enviar o botão no canal {canal_ticket.name}: {e}")

    # ====== PARTE WHITELIST: enviar embed + botão no canal whitelist ======
    canal_whitelist = discord.utils.get(bot.get_all_channels(), name="📜・whitelist")
    if canal_whitelist:
        embed = discord.Embed(
            title="📜 Whitelist da Cidade",
            description="Clique no botão abaixo para iniciar sua **Whitelist** e fazer parte da cidade!",
            color=discord.Color.blue()
        )
        #embed.set_image(url="nvidia.png")  # Coloque o link da imagem desejada
        embed.set_footer(text="Altavila RP - Allowlist")

        view = MenuWhitelistView()
        await canal_whitelist.send(embed=embed, view=view)
        print("✅ Mensagem de whitelist enviada no canal 📜・whitelist")

    # ====== PARTE VERIFICAÇÃO: enviar botão no canal de verificação ======
    canal_verificacao = discord.utils.get(bot.get_all_channels(), name=NOME_CANAL_VERIFICACAO)
    if canal_verificacao:
        view = IniciarVerificacaoView()
        await canal_verificacao.send(
            embed=discord.Embed(
                title="✔️ Verificação de Segurança",
                description="Clique no botão abaixo para iniciar sua **verificação** e provar que você não é um robô!",
                color=discord.Color.blue()
            ),
            view=view
        )
        print("✅ Mensagem de verificação enviada no canal ✔️・verificação")


# ------------------ PARTE 2: WHITELIST ------------------

class MenuWhitelistView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Fazer Whitelist", style=discord.ButtonStyle.primary)
    async def iniciar_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await iniciar_processo_whitelist(interaction)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ocorreu um erro ao iniciar a whitelist: {e}", ephemeral=True
            )


class WhitelistButtons(discord.ui.View):
    def __init__(self, membro: discord.Member, nome_rp: str, canal: discord.TextChannel, respostas=None):
        super().__init__(timeout=None)
        self.membro = membro
        self.nome_rp = nome_rp
        self.canal = canal
        self.respostas = respostas or {}

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_permissao_staff(interaction):
            await interaction.response.send_message("❌ Você não tem permissão para isso.", ephemeral=True)
            return

        cargo_aprovado = discord.utils.get(interaction.guild.roles, name="Semi-Aprovado")
        if cargo_aprovado:
            await self.membro.add_roles(cargo_aprovado)

        try:
            await self.membro.edit(nick=self.nome_rp)
        except:
            pass

        try:
            await self.membro.send("✅ Parabéns! Você foi **aprovado** na whitelist da cidade. Seja bem-vindo!")
        except:
            pass

        canal_aprovados = discord.utils.get(interaction.guild.text_channels, name="✅・aprovados")
        if canal_aprovados:
            await canal_aprovados.send(f"✅ {self.membro.mention} foi **aprovado** na whitelist!")

        await self.canal.send(f"✅ {self.membro.mention} foi **aprovado** na whitelist pela staff {interaction.user.mention}!")
        await self.log_whitelist(interaction, aprovado=True)
        try:
            await self.canal.delete(reason="Whitelist aprovada")
        except discord.errors.NotFound:
            pass  # Canal já foi deletado, ignore o erro

    @discord.ui.button(label="Reprovar", style=discord.ButtonStyle.danger, emoji="❌")
    async def reprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not tem_permissao_staff(interaction):
            await interaction.response.send_message("❌ Você não tem permissão para isso.", ephemeral=True)
            return

        # Modal para motivo da recusa
        class MotivoRecusaModal(discord.ui.Modal, title="Motivo da Recusa"):
            motivo = discord.ui.TextInput(label="Motivo da recusa", style=discord.TextStyle.paragraph, max_length=300)

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    await self.membro.send(f"❌ Infelizmente, você foi **reprovado** na whitelist da cidade.\nMotivo: {modal_self.motivo.value}\nVocê poderá tentar novamente em 50 minutos.")
                except:
                    pass

                canal_reprovados = discord.utils.get(interaction.guild.text_channels, name="❌・reprovados")
                if canal_reprovados:
                    await canal_reprovados.send(f"❌ {self.membro.mention} foi **reprovado** na whitelist!")

                await self.canal.send(f"❌ {self.membro.mention} foi **reprovado** na whitelist pela staff {interaction.user.mention}.\nMotivo: {modal_self.motivo.value}")
                await self.log_whitelist(interaction, aprovado=False, motivo=modal_self.motivo.value)
                await self.canal.delete(reason="Whitelist reprovada")

                # Espera 30 segundos e reenvia o botão de whitelist no canal de whitelist
                await asyncio.sleep(3000)
                canal_whitelist = discord.utils.get(interaction.guild.text_channels, name="📜・whitelist")
                if canal_whitelist:
                    view = MenuWhitelistView()
                    await canal_whitelist.send(
                        f"{self.membro.mention} Você pode tentar a whitelist novamente agora!",
                        view=view
                    )

        await interaction.response.send_modal(MotivoRecusaModal())

    async def log_whitelist(self, interaction, aprovado, motivo=None):
        canal_logs = discord.utils.get(interaction.guild.text_channels, name=NOME_CANAL_LOGS_WHITELIST)
        status = "APROVADO" if aprovado else "REPROVADO"
        log_msg = (
            f"**Log Whitelist**\n"
            f"Usuário: {self.membro.mention} ({self.membro})\n"
            f"Nome no RP: {self.nome_rp}\n"
            f"Aprovador: {interaction.user.mention}\n"
            f"Status: {status}\n"
        )
        if motivo:
            log_msg += f"Motivo da recusa: {motivo}\n"
        if self.respostas:
            log_msg += "**Respostas:**\n"
            for k, v in self.respostas.items():
                log_msg += f"- {k}: {v}\n"
        if canal_logs:
            await canal_logs.send(log_msg)


def tem_permissao_staff(interaction: discord.Interaction):
    cargo_staff = discord.utils.get(interaction.guild.roles, name="Staff")
    return cargo_staff in interaction.user.roles


async def iniciar_processo_whitelist(interaction: discord.Interaction):
    guild = interaction.guild
    user = interaction.user

    # Verifica se já existe um canal de whitelist para o usuário
    canal_existente = discord.utils.get(
        guild.text_channels, name=f"prova-{user.name}".lower()
    )
    if canal_existente:
        await interaction.response.send_message(
            f"❌ Você já possui uma prova de whitelist em andamento: {canal_existente.mention}", ephemeral=True
        )
        return

    # Cria canal privado na categoria 🔧・whitelist
    categoria = discord.utils.get(guild.categories, name="🔧・whitelist")
    if not categoria:
        await interaction.response.send_message("❌ Categoria de whitelist não encontrada.", ephemeral=True)
        return

    canal_nome = f"prova-{user.name}".lower()
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    cargo_staff = discord.utils.get(guild.roles, name="Staff")
    if cargo_staff:
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    canal_privado = await guild.create_text_channel(
        name=canal_nome,
        overwrites=overwrites,
        category=categoria,
        reason="Canal de prova de whitelist"
    )

    # Envia o embed inicial e guarda a mensagem enviada
    embed_inicial = discord.Embed(
        title="📝 Prova de Whitelist",
        description=(
            "Cite as informações do seu personagem a baixo para podermos começar a prova:\n\n"
            "▶️ **Você tem até 10 minutos para responder cada pergunta abaixo, caso contrário esse canal será deletado e você terá que começar novamente.**\n\n"
            "▶️ **Você receberá o RESULTADO em seu privado, logo após um de nossos STAFFS analisar a sua Whitelist.**\n\n"
        ),
        color=discord.Color.dark_green()
    )
    embed_inicial.set_image(url="https://link-da-sua-imagem.com/allowlist.png")
    msg_embed_inicial = await canal_privado.send(embed=embed_inicial)  # <-- Salva a mensagem

    perguntas_fixas = [
        "Qual seu nome no RP?",
        "Qual sua idade no RP?",
        "Por que quer entrar na cidade?"
    ]
    respostas_fixas = []
    def check(m):
        return m.author == user and m.channel == canal_privado

    try:
        for idx, pergunta in enumerate(perguntas_fixas):
            pergunta_msg = await canal_privado.send(f"**Pergunta {idx+1}/{len(perguntas_fixas)}:** {pergunta}")
            msg = await bot.wait_for("message", check=check, timeout=600)
            respostas_fixas.append(msg.content)
            try:
                await pergunta_msg.delete()
                await msg.delete()
            except:
                pass

        # Após responder as perguntas iniciais, deleta o embed inicial
        try:
            await msg_embed_inicial.delete()
        except:
            pass

        # Cabeçalho para a prova
        embed_prova = discord.Embed(
            title="📝 Prova de Whitelist",
            description=(
                "▶️ **Você tem até 10 minutos para responder cada pergunta abaixo, caso contrário esse canal será deletado e você terá que começar novamente.**\n\n"
                "▶️ **Você receberá o RESULTADO em seu privado, logo após um de nossos STAFFS analisar a sua Whitelist.**\n\n"
                "❗ **VOCÊ PRECISA ACERTAR 9 DAS 10 PERGUNTAS**\n"
            ),
            color=discord.Color.dark_green()
        )
        embed_prova.set_image(url="https://link-da-sua-imagem.com/allowlist.png")
        await canal_privado.send(embed=embed_prova)

        # Perguntas da prova (embaralhadas)
        perguntas_prova = [
            "O que significa VDM?",
            "O que significa RDM?",
            "Cite 3 regras básicas do servidor.",
            "Explique o que é PowerGaming.",
            "Explique o que é MetaGaming."
        ]
        perguntas_embaralhadas = random.sample(perguntas_prova, len(perguntas_prova))
        respostas_prova = []

        for idx, pergunta in enumerate(perguntas_embaralhadas):
            pergunta_msg = await canal_privado.send(f"**Prova {idx+1}/{len(perguntas_embaralhadas)}:** {pergunta}\n_Responda em até 10 minutos._")
            msg = await bot.wait_for("message", check=check, timeout=600)
            respostas_prova.append(msg.content)
            try:
                await pergunta_msg.delete()
                await msg.delete()
            except:
                pass

        # Junta todas as respostas
        respostas_finais = respostas_fixas + respostas_prova

        await canal_privado.send("✅ Whitelist enviada para avaliação da staff! Aguarde o resultado.")
        await user.send("✅ Whitelist enviada para avaliação da staff! Aguarde o resultado.")
        await processar_respostas_whitelist(guild, user, respostas_finais, canal_privado)
    except asyncio.TimeoutError:
        await canal_privado.send("⏰ Tempo esgotado! Você demorou mais de 10 minutos para responder uma das perguntas. O canal será deletado.")
        try:
            await user.send("⏰ Tempo esgotado! Você demorou mais de 10 minutos para responder uma das perguntas da whitelist.")
        except:
            pass
        await asyncio.sleep(10)
        await canal_privado.delete(reason="Tempo esgotado na whitelist.")

# Atualize a função processar_respostas_whitelist para receber canal_privado:
async def processar_respostas_whitelist(guild, user, answers, canal_privado):
    texto = f"👋 Olá {user.mention}! Aqui estão suas respostas da whitelist:\n\n"
    for idx, pergunta in enumerate(WHITELIST_QUESTIONS):
        texto += f"**{pergunta}**\n{answers[idx]}\n\n"

    await canal_privado.send(texto)
    await canal_privado.send(
        f"👮‍♂️ **Staff:** Utilize os botões abaixo para **aprovar** ou **reprovar** {user.mention}.",
        view=WhitelistButtons(user, answers[0], canal_privado, respostas=dict(zip(WHITELIST_QUESTIONS, answers)))
    )


def salvar_em_planilha(dados):
    arquivo = "whitelist_dados.xlsx"

    if os.path.exists(arquivo):
        df_existente = pd.read_excel(arquivo)
        df_novo = pd.DataFrame([dados])
        df_final = pd.concat([df_existente, df_novo], ignore_index=True)
    else:
        df_final = pd.DataFrame([dados])

    df_final.to_excel(arquivo, index=False)


# ------------------ PARTE 3: COMANDO ENCERRAR TICKET ------------------

@bot.command()
@commands.has_role("Staff")
async def encerrar(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Este comando só pode ser usado dentro de um ticket.")
        return

    await ctx.send("🔒 Encerrando o ticket e gerando o log...")

    try:
        canal_logs = discord.utils.get(ctx.guild.text_channels, name=NOME_CANAL_LOGS)

        if canal_logs is None:
            await ctx.send("⚠️ Canal de logs não encontrado. Verifique o nome.")
            print("❌ Canal de logs não encontrado.")
            return

        transcript = f"📄 Transcrição do ticket {ctx.channel.name}\n\n"
        async for msg in ctx.channel.history(limit=None, oldest_first=True):
            content = msg.content if msg.content else "[Mensagem sem texto]"
            transcript += f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author}: {content}\n"

        nome_arquivo = limpar_nome_arquivo(ctx.channel.name)
        file = discord.File(fp=bytes(transcript, 'utf-8'), filename=f"{nome_arquivo}.txt")

        await canal_logs.send(
            f"📑 Log do {ctx.channel.name} encerrado por {ctx.author.mention}",
            file=file
        )

        await ctx.channel.delete()

    except Exception as e:
        await ctx.send(f"❌ Erro ao tentar encerrar o ticket: {e}")
        print(f"❌ Erro ao encerrar o ticket: {e}")

class IniciarVerificacaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(IniciarVerificacaoButton())

class IniciarVerificacaoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Você não é um robô", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        codigo = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=5))
        interaction.client.verificacao_codigos = getattr(interaction.client, "verificacao_codigos", {})
        interaction.client.verificacao_codigos[interaction.user.id] = codigo
        await interaction.channel.send(
            embed=discord.Embed(
                title="✔️ Verificação de Segurança",
                description=f"{interaction.user.mention} Digite o código abaixo para provar que você não é um robô:\n\n**{codigo}**",
                color=discord.Color.blue()
            ),
            view=CodigoView(codigo, interaction.user)
        )

class CodigoView(discord.ui.View):
    def __init__(self, codigo, usuario):
        super().__init__(timeout=None)
        self.codigo = codigo
        self.usuario = usuario
        self.add_item(EnviarCodigoButton(codigo, usuario))
        self.add_item(CancelarCodigoButton())

class EnviarCodigoButton(discord.ui.Button):
    def __init__(self, codigo, usuario):
        super().__init__(label="Enviar código", style=discord.ButtonStyle.primary)
        self.codigo = codigo
        self.usuario = usuario

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VerificacaoCodigoModal(self.codigo, self.usuario))

class CancelarCodigoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Cancelar", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        # Reenvia o botão inicial
        view = IniciarVerificacaoView()
        await interaction.channel.send(
            "Clique no botão abaixo para iniciar sua verificação:",
            view=view
        )

class VerificacaoCodigoModal(discord.ui.Modal, title="Verificação de Código"):
    def __init__(self, codigo_esperado, usuario):
        super().__init__()
        self.codigo_esperado = codigo_esperado
        self.usuario = usuario
        self.codigo = discord.ui.TextInput(
            label="Digite o código exatamente como mostrado",
            placeholder="Exemplo: 7G5K2",
            max_length=10
        )
        self.add_item(self.codigo)

    async def on_submit(self, interaction: discord.Interaction):
        codigo_digitado = self.codigo.value.strip().upper()
        codigo_correto = self.codigo_esperado
        if codigo_digitado == codigo_correto:
            cargo = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_VERIFICADO)
            if cargo:
                if cargo in interaction.user.roles:
                    await interaction.response.send_message("Você já está verificado!", ephemeral=True)
                else:
                    await interaction.user.add_roles(cargo)
                    await interaction.response.send_message("✅ Você foi verificado e agora tem acesso ao servidor!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Cargo de verificado não encontrado. Avise um administrador.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Código incorreto! Aguarde 30 segundos para tentar novamente.", ephemeral=True)
            await asyncio.sleep(30)
            # Reenvia o botão inicial após 30s
            view = IniciarVerificacaoView()
            await interaction.channel.send(
                "Clique no botão abaixo para iniciar sua verificação:",
                view=view
            )

@bot.command()
@commands.has_any_role("Staff")
@commands.has_permissions(administrator=True)
async def limpar(ctx, quantidade: int = 10):
    """
    Limpa uma quantidade de mensagens do canal atual.
    Exemplo: !limpar 20
    """
    if quantidade < 1 or quantidade > 300:
        await ctx.send("❌ Você pode limpar entre 1 e 300 mensagens por vez.")
        return
    await ctx.channel.purge(limit=quantidade + 1)  # +1 para apagar o comando também
    msg = await ctx.send(f"✅ {quantidade} mensagens apagadas!")
    await asyncio.sleep(3)
    await msg.delete()

bot.run('MTM4NDM0NTEwMjAyOTE2MDQ5OQ.Gk1zom.FZT7QW1F4kUunsnztYbLc_JbfTeCykry6KHBrw')
