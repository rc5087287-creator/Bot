"""Mensagens de boas-vindas/despedida e cargo automático."""
import discord
from discord.ext import commands

from bot import config
from bot.utils import helpers

PADRAO_BOAS_VINDAS = "Bem-vindo(a) ao **{servidor}**, {membro}! 🎉 Você é o membro nº {contagem}."
PADRAO_DESPEDIDA = "**{nome}** saiu do servidor. 👋"


class Welcome(commands.Cog, name="Boas-vindas"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, membro: discord.Member):
        db, guild = self.bot.db, membro.guild
        cargo_id = await db.get_int_setting(guild.id, "autorole")
        if cargo_id and (cargo := guild.get_role(cargo_id)) and not membro.bot:
            try:
                await membro.add_roles(cargo, reason="Cargo automático")
            except discord.HTTPException:
                pass
        canal_id = await db.get_int_setting(guild.id, "welcome_channel")
        canal = guild.get_channel(canal_id) if canal_id else None
        if not isinstance(canal, discord.TextChannel):
            return
        modelo = await db.get_setting(guild.id, "welcome_message") or PADRAO_BOAS_VINDAS
        texto = render(modelo, membro=membro.mention, nome=membro.display_name,
                       servidor=guild.name, contagem=guild.member_count)
        e = helpers.embed("👋 Novo membro!", texto, config.COR_SUCESSO)
        e.set_thumbnail(url=membro.display_avatar.url)
        try:
            await canal.send(embed=e)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, membro: discord.Member):
        db, guild = self.bot.db, membro.guild
        canal_id = await db.get_int_setting(guild.id, "goodbye_channel")
        canal = guild.get_channel(canal_id) if canal_id else None
        if not isinstance(canal, discord.TextChannel):
            return
        modelo = await db.get_setting(guild.id, "goodbye_message") or PADRAO_DESPEDIDA
        texto = render(modelo, membro=str(membro), nome=membro.display_name,
                       servidor=guild.name, contagem=guild.member_count)
        try:
            await canal.send(embed=helpers.embed(None, texto, config.COR_AVISO))
        except discord.HTTPException:
            pass


def render(modelo: str, **valores) -> str:
    """Substitui {placeholders} de forma segura (sem str.format)."""
    for chave, valor in valores.items():
        modelo = modelo.replace("{" + chave + "}", str(valor))
    return modelo


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
