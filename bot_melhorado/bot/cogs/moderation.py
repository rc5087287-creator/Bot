"""Moderação: kick, ban, timeout, limpar chat, advertências, bloqueio de canal."""
import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import config
from bot.utils import helpers

SEM_MOTIVO = "Sem motivo informado"
MAX_TIMEOUT = datetime.timedelta(days=28)
WARNS_PARA_TIMEOUT = 3


class Moderation(commands.Cog, name="Moderação"):
    emoji = "🛡️"

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- Auxiliares ----------
    async def _pode_agir(self, ctx: commands.Context, alvo: discord.Member) -> bool:
        """Valida hierarquia de cargos. Responde com erro e retorna False se não puder."""
        msg = None
        if alvo.id == ctx.author.id:
            msg = "Você não pode fazer isso consigo mesmo."
        elif alvo.id == self.bot.user.id:
            msg = "Eu não vou fazer isso comigo mesmo. 😅"
        elif alvo.id == ctx.guild.owner_id:
            msg = "Não posso punir o dono do servidor."
        elif ctx.author.id != ctx.guild.owner_id and alvo.top_role >= ctx.author.top_role:
            msg = "O cargo desse membro é igual ou maior que o seu."
        elif alvo.top_role >= ctx.guild.me.top_role:
            msg = "O cargo desse membro é igual ou maior que o meu."
        if msg:
            await ctx.send(embed=helpers.erro(msg), ephemeral=True)
            return False
        return True

    async def _avisar_dm(self, membro: discord.abc.User, guild: discord.Guild, acao: str, motivo: str):
        try:
            await membro.send(embed=helpers.embed(f"Você recebeu: {acao}", f"**Servidor:** {guild.name}\n**Motivo:** {motivo}", config.COR_AVISO))
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _log(self, ctx: commands.Context, acao: str, alvo, motivo: str, extra: str = ""):
        e = helpers.embed(f"🛡️ {acao}", cor=config.COR_AVISO)
        e.add_field(name="Alvo", value=f"{alvo} (`{alvo.id}`)")
        e.add_field(name="Moderador", value=ctx.author.mention)
        e.add_field(name="Motivo", value=motivo, inline=False)
        if extra:
            e.add_field(name="Detalhes", value=extra, inline=False)
        await self.bot.send_log(ctx.guild, e)

    # ---------- Expulsar / Banir ----------
    @commands.hybrid_command(name="kick", aliases=["expulsar"], description="Expulsa um membro.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = SEM_MOTIVO):
        if not await self._pode_agir(ctx, membro):
            return
        await self._avisar_dm(membro, ctx.guild, "uma expulsão", motivo)
        await membro.kick(reason=f"{ctx.author}: {motivo}")
        await ctx.send(embed=helpers.sucesso(f"**{membro}** foi expulso. Motivo: {motivo}"))
        await self._log(ctx, "Expulsão", membro, motivo)

    @commands.hybrid_command(name="ban", aliases=["banir"], description="Bane um membro.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = SEM_MOTIVO):
        if not await self._pode_agir(ctx, membro):
            return
        await self._avisar_dm(membro, ctx.guild, "um banimento", motivo)
        await membro.ban(reason=f"{ctx.author}: {motivo}", delete_message_days=0)
        await ctx.send(embed=helpers.sucesso(f"**{membro}** foi banido. Motivo: {motivo}"))
        await self._log(ctx, "Banimento", membro, motivo)

    @commands.hybrid_command(name="unban", aliases=["desbanir"], description="Remove o banimento de um usuário (pelo ID).")
    @app_commands.describe(usuario="ID do usuário banido")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx: commands.Context, usuario: discord.User, *, motivo: str = SEM_MOTIVO):
        try:
            await ctx.guild.unban(usuario, reason=f"{ctx.author}: {motivo}")
        except discord.NotFound:
            return await ctx.send(embed=helpers.erro("Esse usuário não está banido."), ephemeral=True)
        await ctx.send(embed=helpers.sucesso(f"**{usuario}** foi desbanido."))
        await self._log(ctx, "Desbanimento", usuario, motivo)

    # ---------- Timeout ----------
    @commands.hybrid_command(name="timeout", aliases=["mute", "silenciar"], description="Silencia um membro por um tempo.")
    @app_commands.describe(duracao="Ex: 10m, 2h, 1d (máx. 28d)")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def timeout(self, ctx: commands.Context, membro: discord.Member, duracao: str, *, motivo: str = SEM_MOTIVO):
        dur = helpers.parse_duration(duracao)
        if not dur or dur > MAX_TIMEOUT:
            return await ctx.send(embed=helpers.erro("Duração inválida. Use algo como `10m`, `2h`, `1d` (máx. 28d)."), ephemeral=True)
        if not await self._pode_agir(ctx, membro):
            return
        await membro.timeout(dur, reason=f"{ctx.author}: {motivo}")
        await self._avisar_dm(membro, ctx.guild, f"um silenciamento de {duracao}", motivo)
        await ctx.send(embed=helpers.sucesso(f"**{membro}** silenciado por **{duracao}**. Motivo: {motivo}"))
        await self._log(ctx, "Timeout", membro, motivo, f"Duração: {duracao}")

    @commands.hybrid_command(name="untimeout", aliases=["unmute", "dessilenciar"], description="Remove o silenciamento de um membro.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.guild_only()
    async def untimeout(self, ctx: commands.Context, membro: discord.Member):
        await membro.timeout(None, reason=f"Removido por {ctx.author}")
        await ctx.send(embed=helpers.sucesso(f"**{membro}** não está mais silenciado."))
        await self._log(ctx, "Fim do timeout", membro, "—")

    # ---------- Limpeza ----------
    @commands.hybrid_command(name="limpar", aliases=["clear", "purge"], description="Apaga mensagens do canal.")
    @app_commands.describe(quantidade="Quantas mensagens apagar (1 a 100)", membro="Apagar só deste membro (opcional)")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.guild_only()
    async def limpar(self, ctx: commands.Context, quantidade: commands.Range[int, 1, 100], membro: Optional[discord.Member] = None):
        await ctx.defer(ephemeral=True)
        check = (lambda m: m.author.id == membro.id) if membro else None
        # No modo prefixo a própria mensagem do comando também é apagada
        limite = quantidade + (1 if ctx.interaction is None and not membro else 0)
        apagadas = await ctx.channel.purge(limit=limite, check=check)
        qtd = len(apagadas) - (1 if ctx.interaction is None and not membro else 0)
        await ctx.send(embed=helpers.sucesso(f"{max(qtd, 0)} mensagem(ns) apagada(s)."), ephemeral=True, delete_after=5)
        await self._log(ctx, "Limpeza de chat", ctx.author, f"{max(qtd, 0)} mensagens em {ctx.channel.mention}")

    @commands.hybrid_command(name="slowmode", aliases=["modolento"], description="Define o modo lento do canal (0 desativa).")
    @app_commands.describe(segundos="0 a 21600")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(self, ctx: commands.Context, segundos: commands.Range[int, 0, 21600]):
        await ctx.channel.edit(slowmode_delay=segundos)
        txt = "desativado" if segundos == 0 else f"definido para **{segundos}s**"
        await ctx.send(embed=helpers.sucesso(f"Modo lento {txt}."))

    @commands.hybrid_command(name="lock", aliases=["trancar"], description="Impede @everyone de falar no canal.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def lock(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"Lock por {ctx.author}")
        await ctx.send(embed=helpers.sucesso("🔒 Canal trancado."))

    @commands.hybrid_command(name="unlock", aliases=["destrancar"], description="Libera o canal para @everyone.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    async def unlock(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"Unlock por {ctx.author}")
        await ctx.send(embed=helpers.sucesso("🔓 Canal liberado."))

    # ---------- Advertências ----------
    @commands.hybrid_command(name="warn", aliases=["avisar", "advertir"], description="Dá uma advertência a um membro.")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def warn(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = SEM_MOTIVO):
        if not await self._pode_agir(ctx, membro):
            return
        await self.bot.db.add_warn(ctx.guild.id, membro.id, ctx.author.id, motivo[:500])
        total = len(await self.bot.db.get_warns(ctx.guild.id, membro.id))
        await self._avisar_dm(membro, ctx.guild, f"uma advertência ({total}/{WARNS_PARA_TIMEOUT})", motivo)
        texto = f"**{membro}** foi advertido ({total}/{WARNS_PARA_TIMEOUT}). Motivo: {motivo}"
        if total >= WARNS_PARA_TIMEOUT and ctx.guild.me.guild_permissions.moderate_members:
            try:
                await membro.timeout(datetime.timedelta(hours=1), reason="Limite de advertências")
                texto += "\n⏳ Limite atingido: silenciado por 1 hora."
            except discord.HTTPException:
                pass
        await ctx.send(embed=helpers.sucesso(texto))
        await self._log(ctx, "Advertência", membro, motivo, f"Total: {total}")

    @commands.hybrid_command(name="warns", aliases=["advertencias"], description="Lista as advertências de um membro.")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def warns(self, ctx: commands.Context, membro: discord.Member):
        lista = await self.bot.db.get_warns(ctx.guild.id, membro.id)
        if not lista:
            return await ctx.send(embed=helpers.aviso(f"{membro.mention} não tem advertências."), ephemeral=True)
        linhas = [f"**#{w['id']}** • <t:{w['created_at']}:d> • por <@{w['mod_id']}>\n└ {w['reason']}" for w in lista[-10:]]
        await ctx.send(embed=helpers.embed(f"⚠️ Advertências de {membro.display_name} ({len(lista)})", "\n".join(linhas)), ephemeral=True)

    @commands.hybrid_command(name="delwarn", description="Remove uma advertência pelo número.")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def delwarn(self, ctx: commands.Context, numero: int):
        ok = await self.bot.db.delete_warn(ctx.guild.id, numero)
        await ctx.send(embed=helpers.sucesso("Advertência removida.") if ok else helpers.erro("Advertência não encontrada."), ephemeral=True)

    @commands.hybrid_command(name="clearwarns", description="Remove todas as advertências de um membro.")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def clearwarns(self, ctx: commands.Context, membro: discord.Member):
        n = await self.bot.db.clear_warns(ctx.guild.id, membro.id)
        await ctx.send(embed=helpers.sucesso(f"{n} advertência(s) de {membro.mention} removida(s)."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
