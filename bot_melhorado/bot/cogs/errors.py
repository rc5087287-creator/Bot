"""Tratamento global de erros com mensagens amigáveis."""
import logging
import traceback

import discord
from discord.ext import commands

from bot.utils import helpers

log = logging.getLogger("bot.errors")


class Errors(commands.Cog, name="Erros"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if hasattr(ctx.command, "on_error"):
            return
        # Desembrulha erros encapsulados (comandos híbridos / slash)
        while getattr(error, "original", None) is not None:
            error = error.original

        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            msg = f"Faltou o argumento **{error.param.name}**. Use `{ctx.clean_prefix}ajuda {ctx.command}` para ver como usar."
        elif isinstance(error, (commands.BadArgument, commands.BadUnionArgument, commands.TooManyArguments)):
            msg = f"Argumento inválido. Use `{ctx.clean_prefix}ajuda {ctx.command}` para ver como usar."
        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(p.replace("_", " ").title() for p in error.missing_permissions)
            msg = f"Você precisa da(s) permissão(ões): **{perms}**."
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(p.replace("_", " ").title() for p in error.missing_permissions)
            msg = f"Eu preciso da(s) permissão(ões): **{perms}**."
        elif isinstance(error, commands.CommandOnCooldown):
            msg = f"Calma! Tente de novo em **{error.retry_after:.1f}s**."
        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Este comando só funciona dentro de um servidor."
        elif isinstance(error, commands.NotOwner):
            msg = "Apenas o dono do bot pode usar este comando."
        elif isinstance(error, commands.CheckFailure):
            msg = "Você não pode usar este comando aqui."
        elif isinstance(error, discord.Forbidden):
            msg = "Não tenho permissão para fazer isso (verifique meus cargos e permissões)."
        else:
            log.error("Erro no comando %s", ctx.command, exc_info=(type(error), error, error.__traceback__))
            msg = "Algo deu errado ao executar o comando. O erro foi registrado. 😵"
        try:
            await ctx.send(embed=helpers.erro(msg), ephemeral=True)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Errors(bot))
