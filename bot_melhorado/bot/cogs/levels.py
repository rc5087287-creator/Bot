"""Sistema de XP e níveis com ranking, cargos por nível e cooldown anti-spam."""
import logging
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import config
from bot.utils import helpers

log = logging.getLogger("bot.levels")
MEDALHAS = {1: "🥇", 2: "🥈", 3: "🥉"}


class Levels(commands.Cog, name="Níveis"):
    emoji = "⭐"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns: dict[tuple[int, int], float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(config.PREFIX):  # comandos não dão XP
            return
        chave = (message.guild.id, message.author.id)
        agora = time.monotonic()
        if agora - self._cooldowns.get(chave, 0) < config.XP_COOLDOWN:
            return
        self._cooldowns[chave] = agora

        ganho = random.randint(config.XP_MIN, config.XP_MAX)
        antigo, novo = await self.bot.db.add_xp(message.guild.id, message.author.id, ganho)
        nivel_antigo, nivel_novo = helpers.level_from_xp(antigo), helpers.level_from_xp(novo)
        if nivel_novo > nivel_antigo:
            await self._subiu_de_nivel(message, nivel_novo)

    async def _subiu_de_nivel(self, message: discord.Message, nivel: int):
        db, guild = self.bot.db, message.guild
        if await db.get_setting(guild.id, "level_announce") != "off":
            canal_id = await db.get_int_setting(guild.id, "level_channel")
            canal = guild.get_channel(canal_id) if canal_id else message.channel
            try:
                await (canal or message.channel).send(
                    f"🎉 {message.author.mention} subiu para o **nível {nivel}**!"
                )
            except discord.HTTPException:
                pass
        await self._aplicar_cargos(message.author, nivel)

    async def _aplicar_cargos(self, membro: discord.Member, nivel: int):
        registros = await self.bot.db.get_level_roles(membro.guild.id)
        para_dar = []
        for reg in registros:
            if reg["level"] <= nivel:
                cargo = membro.guild.get_role(reg["role_id"])
                if cargo and cargo not in membro.roles:
                    para_dar.append(cargo)
        if para_dar:
            try:
                await membro.add_roles(*para_dar, reason=f"Recompensa de nível {nivel}")
            except discord.HTTPException:
                log.warning("Sem permissão para dar cargos de nível em %s", membro.guild.id)

    # ---------- Comandos ----------
    @commands.hybrid_command(name="xp", aliases=["nivel", "level"], description="Mostra seu XP e nível.")
    @app_commands.describe(membro="Quem você quer ver (padrão: você)")
    @commands.guild_only()
    async def xp(self, ctx: commands.Context, membro: Optional[discord.Member] = None):
        membro = membro or ctx.author
        row = await self.bot.db.get_user(ctx.guild.id, membro.id)
        if not row:
            return await ctx.send(embed=helpers.aviso(f"{membro.mention} ainda não possui XP."))
        xp_total = row["xp"]
        nivel = helpers.level_from_xp(xp_total)
        base, proximo = helpers.xp_for_level(nivel), helpers.xp_for_level(nivel + 1)
        pos = await self.bot.db.position(ctx.guild.id, membro.id)
        e = helpers.embed(f"📊 XP de {membro.display_name}")
        e.set_thumbnail(url=membro.display_avatar.url)
        e.add_field(name="Nível", value=f"**{nivel}**")
        e.add_field(name="Posição", value=f"**#{pos}**")
        e.add_field(name="XP total", value=f"**{xp_total}**")
        e.add_field(
            name=f"Progresso para o nível {nivel + 1}",
            value=f"{helpers.progress_bar(xp_total - base, proximo - base)} {xp_total - base}/{proximo - base}",
            inline=False,
        )
        await ctx.send(embed=e)

    @commands.hybrid_command(name="rank", aliases=["top", "ranking", "leaderboard"], description="Ranking de XP do servidor.")
    @app_commands.describe(pagina="Página do ranking")
    @commands.guild_only()
    async def rank(self, ctx: commands.Context, pagina: commands.Range[int, 1, 1000] = 1):
        por_pagina = 10
        total = await self.bot.db.count_users(ctx.guild.id)
        if total == 0:
            return await ctx.send(embed=helpers.aviso("Ninguém tem XP ainda. Comece a conversar!"))
        paginas = max(1, -(-total // por_pagina))
        if pagina > paginas:
            return await ctx.send(embed=helpers.erro(f"Só existem {paginas} página(s)."), ephemeral=True)
        linhas = []
        for i, row in enumerate(await self.bot.db.top(ctx.guild.id, por_pagina, (pagina - 1) * por_pagina), start=(pagina - 1) * por_pagina + 1):
            membro = ctx.guild.get_member(row["user_id"])
            nome = membro.display_name if membro else f"Usuário {row['user_id']}"
            linhas.append(f"{MEDALHAS.get(i, f'**{i}.**')} {nome} — Nível {helpers.level_from_xp(row['xp'])} • {row['xp']} XP")
        e = helpers.embed("🏆 Ranking de XP", "\n".join(linhas))
        e.set_footer(text=f"Página {pagina}/{paginas}")
        await ctx.send(embed=e)

    @commands.hybrid_command(name="setxp", description="[Admin] Define o XP de um membro.")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def setxp(self, ctx: commands.Context, membro: discord.Member, xp: commands.Range[int, 0, 1_000_000_000]):
        await self.bot.db.set_xp(ctx.guild.id, membro.id, xp)
        await self._aplicar_cargos(membro, helpers.level_from_xp(xp))
        await ctx.send(embed=helpers.sucesso(f"XP de {membro.mention} definido para **{xp}** (nível {helpers.level_from_xp(xp)})."))

    @commands.hybrid_command(name="resetxp", description="[Admin] Zera o XP de um membro.")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def resetxp(self, ctx: commands.Context, membro: discord.Member):
        await self.bot.db.reset_user(ctx.guild.id, membro.id)
        await ctx.send(embed=helpers.sucesso(f"XP de {membro.mention} foi zerado."))

    # ---------- Cargos por nível ----------
    @commands.hybrid_group(name="cargonivel", description="[Admin] Cargos dados automaticamente ao atingir um nível.")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def cargonivel(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=helpers.aviso(f"Use `{ctx.clean_prefix}cargonivel adicionar|remover|listar`."), ephemeral=True)

    @cargonivel.command(name="adicionar", description="Define o cargo de um nível.")
    async def cargonivel_add(self, ctx: commands.Context, nivel: commands.Range[int, 1, 1000], cargo: discord.Role):
        if cargo >= ctx.guild.me.top_role or cargo.managed:
            return await ctx.send(embed=helpers.erro("Não consigo dar esse cargo (ele está acima do meu ou é gerenciado)."), ephemeral=True)
        await self.bot.db.set_level_role(ctx.guild.id, nivel, cargo.id)
        await ctx.send(embed=helpers.sucesso(f"Quem chegar ao nível **{nivel}** receberá {cargo.mention}."))

    @cargonivel.command(name="remover", description="Remove o cargo de um nível.")
    async def cargonivel_rem(self, ctx: commands.Context, nivel: int):
        ok = await self.bot.db.remove_level_role(ctx.guild.id, nivel)
        await ctx.send(embed=helpers.sucesso("Removido.") if ok else helpers.erro("Não há cargo nesse nível."))

    @cargonivel.command(name="listar", description="Lista os cargos por nível.")
    async def cargonivel_list(self, ctx: commands.Context):
        regs = await self.bot.db.get_level_roles(ctx.guild.id)
        if not regs:
            return await ctx.send(embed=helpers.aviso("Nenhum cargo por nível configurado."))
        await ctx.send(embed=helpers.embed("🎖️ Cargos por nível", "\n".join(f"Nível **{r['level']}** → <@&{r['role_id']}>" for r in regs)))


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
