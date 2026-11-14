"""Configuração do bot por servidor (canais, mensagens, cargo automático)."""
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.welcome import PADRAO_BOAS_VINDAS, PADRAO_DESPEDIDA
from bot.utils import helpers

CANAIS = {
    "boasvindas": ("welcome_channel", "Boas-vindas"),
    "despedida": ("goodbye_channel", "Despedida"),
    "logs": ("log_channel", "Logs"),
    "niveis": ("level_channel", "Avisos de nível"),
}


class Settings(commands.Cog, name="Configuração"):
    emoji = "⚙️"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="config", aliases=["configurar"], description="[Admin] Configurações do bot neste servidor.")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def config(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=helpers.aviso(f"Use `{ctx.clean_prefix}config ver|canal|mensagem|autocargo|anunciarnivel`."), ephemeral=True)

    @config.command(name="ver", description="Mostra as configurações atuais.")
    async def ver(self, ctx: commands.Context):
        db, g = self.bot.db, ctx.guild.id
        e = helpers.embed("⚙️ Configurações do servidor")
        for chave, (setting, nome) in CANAIS.items():
            cid = await db.get_int_setting(g, setting)
            e.add_field(name=nome, value=f"<#{cid}>" if cid else "*não definido*")
        rid = await db.get_int_setting(g, "autorole")
        e.add_field(name="Cargo automático", value=f"<@&{rid}>" if rid else "*não definido*")
        e.add_field(name="Anunciar level up", value="desligado" if await db.get_setting(g, "level_announce") == "off" else "ligado")
        e.add_field(name="Msg boas-vindas", value=(await db.get_setting(g, "welcome_message") or PADRAO_BOAS_VINDAS)[:200], inline=False)
        e.add_field(name="Msg despedida", value=(await db.get_setting(g, "goodbye_message") or PADRAO_DESPEDIDA)[:200], inline=False)
        await ctx.send(embed=e)

    @config.command(name="canal", description="Define (ou remove) um canal especial.")
    @app_commands.describe(tipo="Qual função do canal", canal="Canal (deixe vazio para remover)")
    async def canal(self, ctx: commands.Context, tipo: Literal["boasvindas", "despedida", "logs", "niveis"], canal: Optional[discord.TextChannel] = None):
        setting, nome = CANAIS[tipo]
        await self.bot.db.set_setting(ctx.guild.id, setting, canal.id if canal else None)
        txt = f"Canal de **{nome}** definido para {canal.mention}." if canal else f"Canal de **{nome}** removido."
        await ctx.send(embed=helpers.sucesso(txt))

    @config.command(name="mensagem", description="Muda a mensagem de boas-vindas ou despedida.")
    @app_commands.describe(tipo="boasvindas ou despedida", texto="Use {membro} {nome} {servidor} {contagem}")
    async def mensagem(self, ctx: commands.Context, tipo: Literal["boasvindas", "despedida"], *, texto: str):
        chave = "welcome_message" if tipo == "boasvindas" else "goodbye_message"
        await self.bot.db.set_setting(ctx.guild.id, chave, texto[:500])
        await ctx.send(embed=helpers.sucesso("Mensagem atualizada!"))

    @config.command(name="autocargo", description="Cargo dado automaticamente a novos membros.")
    async def autocargo(self, ctx: commands.Context, cargo: Optional[discord.Role] = None):
        if cargo and (cargo >= ctx.guild.me.top_role or cargo.managed):
            return await ctx.send(embed=helpers.erro("Não consigo dar esse cargo (ele está acima do meu ou é gerenciado)."), ephemeral=True)
        await self.bot.db.set_setting(ctx.guild.id, "autorole", cargo.id if cargo else None)
        await ctx.send(embed=helpers.sucesso(f"Cargo automático: {cargo.mention}" if cargo else "Cargo automático removido."))

    @config.command(name="anunciarnivel", description="Liga/desliga o aviso de level up no chat.")
    async def anunciarnivel(self, ctx: commands.Context, ligado: bool):
        await self.bot.db.set_setting(ctx.guild.id, "level_announce", "on" if ligado else "off")
        await ctx.send(embed=helpers.sucesso(f"Avisos de nível {'ligados' if ligado else 'desligados'}."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
