"""Ponto de entrada do bot. Execute com:  python main.py"""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from bot import config
from bot.client import DiscordBot


def setup_logging() -> None:
    config.LOGS_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%d/%m/%Y %H:%M:%S", style="{")
    raiz = logging.getLogger()
    raiz.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    arquivo = RotatingFileHandler(
        config.LOGS_DIR / "bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo.setFormatter(fmt)
    raiz.addHandler(console)
    raiz.addHandler(arquivo)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


async def main() -> None:
    if not config.TOKEN:
        sys.exit("❌ Token não encontrado. Copie .env.example para .env e preencha DISCORD_TOKEN.")
    async with DiscordBot() as bot:
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("bot").info("Bot encerrado pelo usuário.")
