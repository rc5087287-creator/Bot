"""Registro de eventos do servidor no canal de logs."""
import discord
from discord.ext import commands

from bot import config
from bot.utils import helpers


class Logs(commands.Cog, name="Logs"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if msg.author.bot or not msg.guild:
            return
        e = helpers.embed("🗑️ Mensagem apagada", cor=config.COR_ERRO)
        e.add_field(name="Autor", value=f"{msg.author.mention} (`{msg.author.id}`)")
        e.add_field(name="Canal", value=msg.channel.mention)
        e.add_field(name="Conteúdo", value=(msg.content or "*(sem texto/anexo)*")[:1000], inline=False)
        await self.bot.send_log(msg.guild, e)

    @commands.Cog.listener()
    async def on_message_edit(self, antes: discord.Message, depois: discord.Message):
        if antes.author.bot or not antes.guild or antes.content == depois.content:
            return
        e = helpers.embed("✏️ Mensagem editada", cor=config.COR_AVISO)
        e.add_field(name="Autor", value=f"{antes.author.mention} (`{antes.author.id}`)")
        e.add_field(name="Canal", value=f"{antes.channel.mention} [ir](<{depois.jump_url}>)")
        e.add_field(name="Antes", value=(antes.content or "—")[:1000], inline=False)
        e.add_field(name="Depois", value=(depois.content or "—")[:1000], inline=False)
        await self.bot.send_log(antes.guild, e)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self.bot.send_log(guild, helpers.embed("🔨 Membro banido", f"{user} (`{user.id}`)", config.COR_ERRO))

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self.bot.send_log(guild, helpers.embed("♻️ Banimento removido", f"{user} (`{user.id}`)", config.COR_SUCESSO))

    @commands.Cog.listener()
    async def on_member_join(self, m: discord.Member):
        await self.bot.send_log(m.guild, helpers.embed("📥 Entrou", f"{m.mention} (`{m.id}`)\nConta criada {discord.utils.format_dt(m.created_at, 'R')}", config.COR_SUCESSO))

    @commands.Cog.listener()
    async def on_member_remove(self, m: discord.Member):
        await self.bot.send_log(m.guild, helpers.embed("📤 Saiu", f"{m} (`{m.id}`)", config.COR_AVISO))


async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))
