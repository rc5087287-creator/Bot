"""Utilidades: enquetes, lembretes, sorteios, calculadora, senhas."""
import asyncio
import logging
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.utils import helpers

log = logging.getLogger("bot.utility")
NUMEROS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class Utility(commands.Cog, name="Utilidades"):
    emoji = "🛠️"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()

    async def cog_unload(self):
        self.check_reminders.cancel()

    # ---------- Calculadora ----------
    @commands.hybrid_command(name="calc", aliases=["calcular"], description="Calculadora (+ - * / ** %).")
    @app_commands.describe(expressao="Ex: (2+3)*4 ou 2^10")
    async def calc(self, ctx: commands.Context, *, expressao: str):
        try:
            resultado = helpers.safe_eval(expressao)
        except ZeroDivisionError:
            return await ctx.send(embed=helpers.erro("Divisão por zero."), ephemeral=True)
        except Exception:
            return await ctx.send(embed=helpers.erro("Expressão inválida."), ephemeral=True)
        if isinstance(resultado, float) and resultado.is_integer():
            resultado = int(resultado)
        await ctx.send(embed=helpers.embed("🧮 Calculadora", f"`{expressao}` = **{resultado}**"))

    # ---------- Senha ----------
    @commands.hybrid_command(name="senha", aliases=["password", "gensenha"], description="Gera uma senha aleatória segura.")
    @app_commands.describe(tamanho="Tamanho da senha (8 a 64)")
    async def senha(self, ctx: commands.Context, tamanho: commands.Range[int, 8, 64] = 16):
        senha = helpers.gen_pass(tamanho)
        if ctx.interaction:  # slash: resposta visível só para você
            return await ctx.send(f"🔐 Sua senha: ||`{senha}`||", ephemeral=True)
        try:  # prefixo: envia por DM para não expor no canal
            await ctx.author.send(f"🔐 Sua senha: ||`{senha}`||")
            await ctx.send(embed=helpers.sucesso("Enviei a senha na sua DM."))
        except discord.Forbidden:
            await ctx.send(embed=helpers.erro("Suas DMs estão fechadas. Use `/senha` para receber de forma privada."))

    # ---------- Enquete ----------
    @commands.hybrid_command(name="enquete", aliases=["poll"], description="Cria uma enquete com reações.")
    @app_commands.describe(pergunta="A pergunta", opcoes="Até 10 opções separadas por | (vazio = sim/não)")
    @commands.guild_only()
    async def enquete(self, ctx: commands.Context, pergunta: str, *, opcoes: Optional[str] = None):
        lista = [o.strip() for o in opcoes.split("|") if o.strip()] if opcoes else []
        if len(lista) > 10 or len(lista) == 1:
            return await ctx.send(embed=helpers.erro("Use de 2 a 10 opções separadas por `|`."), ephemeral=True)
        if lista:
            desc = "\n".join(f"{NUMEROS[i]} {op}" for i, op in enumerate(lista))
            reacoes = NUMEROS[: len(lista)]
        else:
            desc, reacoes = "Vote com ✅ ou ❌", ["✅", "❌"]
        e = helpers.embed(f"📊 {pergunta}", desc)
        e.set_footer(text=f"Enquete de {ctx.author.display_name}")
        msg = await ctx.send(embed=e)
        if ctx.interaction:
            msg = await ctx.interaction.original_response()
        for r in reacoes:
            await msg.add_reaction(r)

    # ---------- Sorteio ----------
    @commands.hybrid_command(name="sorteio", aliases=["giveaway"], description="Faz um sorteio por reação 🎉.")
    @app_commands.describe(duracao="Ex: 30s, 10m, 1h", premio="O que será sorteado")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def sorteio(self, ctx: commands.Context, duracao: str, *, premio: str):
        dur = helpers.parse_duration(duracao)
        if not dur or dur.total_seconds() > 7 * 86400:
            return await ctx.send(embed=helpers.erro("Duração inválida (máx. 7d). Ex: `10m`, `1h30m`."), ephemeral=True)
        fim = discord.utils.utcnow() + dur
        e = helpers.embed(f"🎉 SORTEIO: {premio}", f"Reaja com 🎉 para participar!\nTermina {discord.utils.format_dt(fim, 'R')}")
        msg = await ctx.send(embed=e)
        if ctx.interaction:
            msg = await ctx.interaction.original_response()
        await msg.add_reaction("🎉")
        await asyncio.sleep(dur.total_seconds())  # obs.: sorteios em andamento se perdem se o bot reiniciar
        try:
            msg = await msg.channel.fetch_message(msg.id)
        except discord.NotFound:
            return
        reacao = discord.utils.get(msg.reactions, emoji="🎉")
        participantes = [u async for u in reacao.users() if not u.bot] if reacao else []
        if not participantes:
            return await msg.reply("Ninguém participou do sorteio. 😢")
        ganhador = random.choice(participantes)
        await msg.reply(f"🎊 Parabéns {ganhador.mention}! Você ganhou **{premio}**!")

    # ---------- Lembretes ----------
    @commands.hybrid_command(name="lembrar", aliases=["remind", "lembrete"], description="Cria um lembrete.")
    @app_commands.describe(tempo="Ex: 10m, 2h, 1d", texto="Do que devo lembrar você")
    async def lembrar(self, ctx: commands.Context, tempo: str, *, texto: str):
        dur = helpers.parse_duration(tempo)
        if not dur or dur.total_seconds() > 365 * 86400:
            return await ctx.send(embed=helpers.erro("Tempo inválido. Ex: `10m`, `2h`, `1d`."), ephemeral=True)
        quando = int(time.time() + dur.total_seconds())
        rid = await self.bot.db.add_reminder(ctx.author.id, ctx.channel.id, quando, texto[:500])
        await ctx.send(embed=helpers.sucesso(f"Lembrete **#{rid}** criado! Aviso <t:{quando}:R>."))

    @commands.hybrid_command(name="lembretes", description="Lista seus lembretes ativos.")
    async def lembretes(self, ctx: commands.Context):
        itens = await self.bot.db.user_reminders(ctx.author.id)
        if not itens:
            return await ctx.send(embed=helpers.aviso("Você não tem lembretes ativos."), ephemeral=True)
        linhas = [f"**#{r['id']}** • <t:{r['remind_at']}:R> • {r['text']}" for r in itens[:15]]
        await ctx.send(embed=helpers.embed("⏰ Seus lembretes", "\n".join(linhas)), ephemeral=True)

    @commands.hybrid_command(name="cancelarlembrete", description="Cancela um lembrete pelo número.")
    async def cancelarlembrete(self, ctx: commands.Context, numero: int):
        ok = await self.bot.db.delete_reminder(numero, ctx.author.id)
        msg = helpers.sucesso("Lembrete cancelado.") if ok else helpers.erro("Lembrete não encontrado.")
        await ctx.send(embed=msg, ephemeral=True)

    @tasks.loop(seconds=15)
    async def check_reminders(self):
        for r in await self.bot.db.due_reminders(int(time.time())):
            await self.bot.db.delete_reminder(r["id"])
            texto = f"⏰ <@{r['user_id']}>, lembrete: **{r['text']}**"
            canal = self.bot.get_channel(r["channel_id"])
            try:
                if canal:
                    await canal.send(texto)
                else:
                    user = await self.bot.fetch_user(r["user_id"])
                    await user.send(texto)
            except discord.HTTPException:
                log.warning("Não consegui entregar o lembrete %s", r["id"])

    @check_reminders.before_loop
    async def _antes(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
