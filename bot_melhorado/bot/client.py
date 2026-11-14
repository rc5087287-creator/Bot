"""Classe principal do bot."""
import logging
import time
from typing import Any, Optional

import aiohttp
import discord
from discord.ext import commands

from bot import config
from bot.database import Database
from bot.utils import helpers

log = logging.getLogger("bot")

EXTENSIONS = [
    "bot.cogs.errors",
    "bot.cogs.general",
    "bot.cogs.fun",
    "bot.cogs.utility",
    "bot.cogs.levels",
    "bot.cogs.moderation",
    "bot.cogs.welcome",
    "bot.cogs.logs",
    "bot.cogs.settings",
    "bot.cogs.admin",
]


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # necessário para comandos com prefixo e XP
        intents.members = True          # necessário para boas-vindas e cargos (ative no Developer Portal)
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=config.OWNER_IDS or None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
        )
        self.db = Database(config.DB_PATH)
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = time.time()

    async def setup_hook(self) -> None:
        await self.db.connect()
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "DiscordBot/2.0"}, timeout=aiohttp.ClientTimeout(total=10)
        )
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info("Módulo carregado: %s", ext)
            except Exception:
                log.exception("Falha ao carregar %s", ext)
        if config.SYNC_ON_START:
            try:
                sincronizados = await self.tree.sync()
                log.info("%d comandos slash sincronizados.", len(sincronizados))
            except Exception:
                log.exception("Falha ao sincronizar comandos slash")

    async def on_ready(self) -> None:
        log.info("Conectado como %s (ID %s) em %d servidores.", self.user, self.user.id, len(self.guilds))

    async def close(self) -> None:
        if self.session:
            await self.session.close()
        await self.db.close()
        await super().close()

    # ---------- Utilidades compartilhadas ----------
    async def fetch_json(self, url: str, **kwargs: Any) -> Any:
        async with self.session.get(url, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        """Envia um embed ao canal de logs configurado no servidor (se existir)."""
        canal_id = await self.db.get_int_setting(guild.id, "log_channel")
        canal = guild.get_channel(canal_id) if canal_id else None
        if isinstance(canal, discord.TextChannel):
            try:
                await canal.send(embed=embed)
            except discord.HTTPException:
                pass

    @property
    def uptime(self) -> str:
        return helpers.format_duration(int(time.time() - self.start_time))
