"""Comandos exclusivos do dono do bot + status rotativo."""
import itertools
import json
import logging

import discord
from discord.ext import commands, tasks

from bot import config
from bot.utils import helpers

log = logging.getLogger("bot.admin")


class Admin(commands.Cog, name="Admin", command_attrs={"hidden": True}):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._status = itertools.cycle(range(3))
        self.rotate_status.start()

    async def cog_unload(self):
        self.rotate_status.cancel()

    @tasks.loop(minutes=5)
    async def rotate_status(self):
        i = next(self._status)
        if i == 0:
            atividade = discord.Game(f"{config.PREFIX}ajuda | /ajuda")
        elif i == 1:
            atividade = discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.bot.guilds)} servidores")
        else:
            total = sum(g.member_count or 0 for g in self.bot.guilds)
            atividade = discord.Activity(type=discord.ActivityType.watching, name=f"{total} membros")
        await self.bot.change_presence(activity=atividade)

    @rotate_status.before_loop
    async def _antes(self):
        await self.bot.wait_until_ready()

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        """Sincroniza os comandos slash globalmente."""
        n = await self.bot.tree.sync()
        await ctx.send(embed=helpers.sucesso(f"{len(n)} comandos sincronizados. (Pode levar alguns minutos para aparecer.)"))

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, modulo: str):
        """Recarrega um módulo (ex: fun, levels)."""
        try:
            await self.bot.reload_extension(f"bot.cogs.{modulo}")
        except Exception as exc:
            return await ctx.send(embed=helpers.erro(f"Falha: `{exc}`"))
        await ctx.send(embed=helpers.sucesso(f"Módulo `{modulo}` recarregado."))

    @commands.command(name="desligar", aliases=["shutdown"])
    @commands.is_owner()
    async def desligar(self, ctx: commands.Context):
        """Desliga o bot."""
        await ctx.send("👋 Desligando...")
        await self.bot.close()

    @commands.command(name="importarxp")
    @commands.is_owner()
    @commands.guild_only()
    async def importarxp(self, ctx: commands.Context):
        """Importa o XP do antigo xp.json (data/xp_antigo.json) para ESTE servidor."""
        if not config.LEGACY_XP_FILE.exists():
            return await ctx.send(embed=helpers.erro("Arquivo `data/xp_antigo.json` não encontrado."))
        dados = json.loads(config.LEGACY_XP_FILE.read_text(encoding="utf-8"))
        importados = 0
        for uid, info in dados.items():
            xp = int(info.get("xp", 0))
            nivel = int(info.get("nivel", 1))
            if nivel > helpers.level_from_xp(xp):  # preserva o nível antigo
                xp = helpers.xp_for_level(nivel)
            atual = await self.bot.db.get_user(ctx.guild.id, int(uid))
            if not atual or atual["xp"] < xp:
                await self.bot.db.set_xp(ctx.guild.id, int(uid), xp)
                importados += 1
        await ctx.send(embed=helpers.sucesso(f"{importados} usuário(s) importado(s) para este servidor."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
