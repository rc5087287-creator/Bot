"""Comandos gerais: ajuda, ping, informações."""
import platform
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import config
from bot.utils import helpers


class General(commands.Cog, name="Geral"):
    emoji = "🏠"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Responde quando o bot é mencionado sozinho
        if message.author.bot or not self.bot.user:
            return
        if message.content.strip() in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
            await message.reply(
                f"Oi! Meu prefixo é `{config.PREFIX}` e também uso comandos `/`. Digite `{config.PREFIX}ajuda`.",
                mention_author=False,
            )

    @commands.hybrid_command(name="ajuda", aliases=["help", "comandos"], description="Mostra a lista de comandos.")
    @app_commands.describe(comando="Nome do comando para ver detalhes")
    async def ajuda(self, ctx: commands.Context, comando: Optional[str] = None):
        if comando:
            cmd = self.bot.get_command(comando.lower().lstrip(config.PREFIX))
            if not cmd or cmd.hidden:
                return await ctx.send(embed=helpers.erro(f"Comando `{comando}` não encontrado."), ephemeral=True)
            e = helpers.embed(f"Comando: {cmd.qualified_name}", cmd.description or cmd.help or "Sem descrição.")
            uso = f"{ctx.clean_prefix}{cmd.qualified_name} {cmd.signature}".strip()
            e.add_field(name="Uso", value=f"`{uso}`", inline=False)
            if cmd.aliases:
                e.add_field(name="Apelidos", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
            if isinstance(cmd, commands.Group):
                subs = ", ".join(f"`{c.name}`" for c in cmd.commands)
                e.add_field(name="Subcomandos", value=subs, inline=False)
            return await ctx.send(embed=e)

        e = helpers.embed("📖 Central de ajuda", f"Use `{ctx.clean_prefix}` ou `/` antes dos comandos.\n"
                          f"Detalhes: `{ctx.clean_prefix}ajuda <comando>`")
        for cog in self.bot.cogs.values():
            visiveis = [c for c in cog.get_commands() if not c.hidden]
            if not visiveis:
                continue
            nomes = " ".join(f"`{c.name}`" for c in sorted(visiveis, key=lambda c: c.name))
            e.add_field(name=f"{getattr(cog, 'emoji', '📁')} {cog.qualified_name}", value=nomes, inline=False)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="ping", description="Mostra a latência do bot.")
    async def ping(self, ctx: commands.Context):
        await ctx.send(embed=helpers.embed("🏓 Pong!", f"Latência: **{round(self.bot.latency * 1000)}ms**"))

    @commands.hybrid_command(name="hello", aliases=["oi", "ola"], description="O bot se apresenta.")
    async def hello(self, ctx: commands.Context):
        await ctx.send(f"Olá, {ctx.author.mention}! Eu sou o bot **{self.bot.user.name}**! 👋")

    @commands.hybrid_command(name="botinfo", aliases=["sobre"], description="Informações sobre o bot.")
    async def botinfo(self, ctx: commands.Context):
        import discord as d
        e = helpers.embed(f"🤖 {self.bot.user.name}")
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        e.add_field(name="Servidores", value=len(self.bot.guilds))
        e.add_field(name="Usuários", value=sum(g.member_count or 0 for g in self.bot.guilds))
        e.add_field(name="Comandos", value=len({c.qualified_name for c in self.bot.walk_commands() if not c.hidden}))
        e.add_field(name="Tempo online", value=self.bot.uptime)
        e.add_field(name="Latência", value=f"{round(self.bot.latency * 1000)}ms")
        e.add_field(name="Versões", value=f"Python {platform.python_version()} • discord.py {d.__version__}")
        await ctx.send(embed=e)

    @commands.hybrid_command(name="avatar", description="Mostra o avatar de um membro.")
    @app_commands.describe(membro="Quem você quer ver (padrão: você)")
    async def avatar(self, ctx: commands.Context, membro: Optional[discord.User] = None):
        membro = membro or ctx.author
        e = helpers.embed(f"Avatar de {membro.display_name}")
        e.set_image(url=membro.display_avatar.url)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="userinfo", aliases=["whois", "perfil"], description="Informações de um membro.")
    @app_commands.describe(membro="Quem você quer ver (padrão: você)")
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, membro: Optional[discord.Member] = None):
        m = membro or ctx.author
        e = helpers.embed(str(m), cor=m.color.value or config.COR_PADRAO)
        e.set_thumbnail(url=m.display_avatar.url)
        e.add_field(name="ID", value=m.id)
        e.add_field(name="Apelido", value=m.nick or "—")
        e.add_field(name="Bot?", value="Sim" if m.bot else "Não")
        e.add_field(name="Conta criada", value=discord.utils.format_dt(m.created_at, "R"))
        e.add_field(name="Entrou no servidor", value=discord.utils.format_dt(m.joined_at, "R") if m.joined_at else "—")
        e.add_field(name="Maior cargo", value=m.top_role.mention)
        roles = [r.mention for r in reversed(m.roles[1:])]
        e.add_field(name=f"Cargos ({len(roles)})", value=" ".join(roles[:15]) + (" …" if len(roles) > 15 else "") or "—", inline=False)
        await ctx.send(embed=e)

    @commands.hybrid_command(name="serverinfo", aliases=["servidor"], description="Informações do servidor.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        g = ctx.guild
        e = helpers.embed(g.name, g.description)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="Dono", value=g.owner.mention if g.owner else "—")
        e.add_field(name="ID", value=g.id)
        e.add_field(name="Criado", value=discord.utils.format_dt(g.created_at, "R"))
        e.add_field(name="Membros", value=g.member_count)
        e.add_field(name="Canais", value=f"💬 {len(g.text_channels)} • 🔊 {len(g.voice_channels)}")
        e.add_field(name="Cargos", value=len(g.roles))
        e.add_field(name="Boosts", value=f"{g.premium_subscription_count} (nível {g.premium_tier})")
        e.add_field(name="Emojis", value=len(g.emojis))
        await ctx.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
