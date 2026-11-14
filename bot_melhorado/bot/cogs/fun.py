"""Comandos de diversão: dados, moeda, memes, imagens, jogos."""
import logging
import random
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import config
from bot.utils import helpers

log = logging.getLogger("bot.fun")

RESPOSTAS_8BALL = [
    "Sim, com certeza!", "Sem dúvida.", "Pode apostar que sim.", "Provavelmente.",
    "As chances são boas.", "Talvez...", "Não sei dizer.", "Pergunte novamente mais tarde.",
    "Melhor não contar com isso.", "Provavelmente não.", "Não.", "De jeito nenhum!",
]
EMOJIS = ["😀", "🙂", "😆", "🤣", "😎", "🔥"]
EXTENSOES_IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
REGEX_DADO = re.compile(r"^(\d{1,2})d(\d{1,4})([+-]\d{1,4})?$")


class PedraPapelTesoura(discord.ui.View):
    OPCOES = {"pedra": "🪨", "papel": "📄", "tesoura": "✂️"}
    VENCE = {"pedra": "tesoura", "papel": "pedra", "tesoura": "papel"}

    def __init__(self, autor: discord.abc.User):
        super().__init__(timeout=30)
        self.autor = autor
        self.mensagem: Optional[discord.Message] = None
        for nome, emoji in self.OPCOES.items():
            botao = discord.ui.Button(label=nome.capitalize(), emoji=emoji, style=discord.ButtonStyle.primary)
            botao.callback = self._fazer_callback(nome)
            self.add_item(botao)

    def _fazer_callback(self, escolha: str):
        async def callback(interaction: discord.Interaction):
            bot_escolha = random.choice(list(self.OPCOES))
            if escolha == bot_escolha:
                resultado, cor = "Empate! 🤝", config.COR_AVISO
            elif self.VENCE[escolha] == bot_escolha:
                resultado, cor = "Você ganhou! 🎉", config.COR_SUCESSO
            else:
                resultado, cor = "Eu ganhei! 😎", config.COR_ERRO
            e = helpers.embed(
                resultado,
                f"Você: {self.OPCOES[escolha]} **{escolha}**\nEu: {self.OPCOES[bot_escolha]} **{bot_escolha}**",
                cor,
            )
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=e, view=self)
            self.stop()
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("Esse jogo é de outra pessoa! Use /ppt para jogar.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.mensagem:
            try:
                await self.mensagem.edit(view=self)
            except discord.HTTPException:
                pass


class Fun(commands.Cog, name="Diversão"):
    emoji = "🎉"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- Dados e sorte ----------
    @commands.hybrid_command(name="d20", description="Rola um dado de 20 lados.")
    async def d20(self, ctx: commands.Context):
        await ctx.send(f"🎲 {random.randint(1, 20)}")

    @commands.hybrid_command(name="d5", description="Rola um dado de 5 lados.")
    async def d5(self, ctx: commands.Context):
        await ctx.send(f"🎲 {random.randint(1, 5)}")

    @commands.hybrid_command(name="dado", aliases=["roll", "rolar"], description="Rola dados no formato NdM+X (ex: 2d6+3).")
    @app_commands.describe(formula="Ex: 1d20, 2d6+3, 4d8-1")
    async def dado(self, ctx: commands.Context, formula: str = "1d6"):
        m = REGEX_DADO.match(formula.lower().replace(" ", ""))
        if not m or int(m.group(1)) < 1 or int(m.group(2)) < 2:
            return await ctx.send(embed=helpers.erro("Formato inválido. Exemplo: `2d6+3`."), ephemeral=True)
        qtd, lados, bonus = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        rolagens = [random.randint(1, lados) for _ in range(qtd)]
        total = sum(rolagens) + bonus
        detalhe = " + ".join(map(str, rolagens)) + (f" {bonus:+d}" if bonus else "")
        await ctx.send(embed=helpers.embed(f"🎲 {formula}", f"{detalhe}\n**Total: {total}**"))

    @commands.hybrid_command(name="flip", aliases=["moeda", "caraoucoroa"], description="Cara ou coroa.")
    async def flip(self, ctx: commands.Context):
        await ctx.send(f"🪙 **{random.choice(['Cara', 'Coroa'])}**!")

    @commands.hybrid_command(name="8ball", aliases=["eightball", "bola8"], description="Faça uma pergunta à bola 8 mágica.")
    @app_commands.describe(pergunta="Sua pergunta de sim ou não")
    async def eightball(self, ctx: commands.Context, *, pergunta: str):
        await ctx.send(f"🎱 **Pergunta:** {pergunta}\n**Resposta:** {random.choice(RESPOSTAS_8BALL)}")

    @commands.hybrid_command(name="escolher", aliases=["choose"], description="Escolhe uma opção entre várias.")
    @app_commands.describe(opcoes="Opções separadas por vírgula ou |")
    async def escolher(self, ctx: commands.Context, *, opcoes: str):
        lista = [o.strip() for o in re.split(r"[,|]", opcoes) if o.strip()]
        if len(lista) < 2:
            return await ctx.send(embed=helpers.erro("Dê pelo menos 2 opções separadas por vírgula."), ephemeral=True)
        await ctx.send(f"🤔 Eu escolho: **{random.choice(lista)}**")

    @commands.hybrid_command(name="ppt", aliases=["jokenpo"], description="Jogue pedra, papel e tesoura contra o bot.")
    async def ppt(self, ctx: commands.Context):
        view = PedraPapelTesoura(ctx.author)
        view.mensagem = await ctx.send(embed=helpers.embed("✊✋✌️ Pedra, papel ou tesoura?", "Escolha abaixo!"), view=view)

    @commands.hybrid_command(name="heh", description="O bot ri para você.")
    @app_commands.describe(quantidade="Quantos 'he' (1 a 200)")
    async def heh(self, ctx: commands.Context, quantidade: commands.Range[int, 1, 200] = 5):
        await ctx.send("he" * quantidade)

    @commands.hybrid_command(name="emoji", description="Envia um emoji aleatório.")
    async def emoji_cmd(self, ctx: commands.Context):
        await ctx.send(random.choice(EMOJIS))

    # ---------- Imagens ----------
    @commands.hybrid_command(name="meme", description="Envia um meme aleatório da pasta bot_images.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def meme(self, ctx: commands.Context):
        arquivos = [f for f in config.IMAGES_DIR.glob("*") if f.suffix.lower() in EXTENSOES_IMG]
        if not arquivos:
            return await ctx.send(embed=helpers.erro("Não há memes na pasta `bot_images`."), ephemeral=True)
        await ctx.send(file=discord.File(random.choice(arquivos)))

    async def _imagem_api(self, ctx: commands.Context, url: str, extrator, titulo: str):
        await ctx.defer()
        try:
            dados = await self.bot.fetch_json(url)
            link = extrator(dados)
        except Exception:
            log.warning("Falha ao buscar imagem em %s", url, exc_info=True)
            return await ctx.send(embed=helpers.erro("Não consegui buscar a imagem agora. Tente de novo em instantes."))
        e = helpers.embed(titulo)
        e.set_image(url=link)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="dog", aliases=["cachorro"], description="Foto aleatória de cachorro.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def dog(self, ctx: commands.Context):
        await self._imagem_api(ctx, "https://dog.ceo/api/breeds/image/random", lambda d: d["message"], "🐶 Au au!")

    @commands.hybrid_command(name="cat", aliases=["gato"], description="Foto aleatória de gato.")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def cat(self, ctx: commands.Context):
        await self._imagem_api(ctx, "https://api.thecatapi.com/v1/images/search", lambda d: d[0]["url"], "🐱 Miau!")

    @commands.hybrid_command(name="wifu", aliases=["waifu"], description="Imagem aleatória de waifu (nekos.best).")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def wifu(self, ctx: commands.Context):
        await self._imagem_api(ctx, "https://nekos.best/api/v2/waifu", lambda d: d["results"][0]["url"], "💖 Waifu")

    @commands.hybrid_command(name="wifu1", description="Imagem aleatória de waifu (waifu.best).")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def wifu1(self, ctx: commands.Context):
        await self._imagem_api(ctx, "https://api.waifu.best/images", lambda d: d["items"][0]["url"], "💖 Waifu")


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
