"""Configurações centrais do bot. Valores vêm do arquivo .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOKEN: str | None = os.getenv("DISCORD_TOKEN")
PREFIX: str = os.getenv("PREFIX", "#")
SYNC_ON_START: bool = os.getenv("SYNC_ON_START", "true").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
OWNER_IDS: set[int] = {
    int(x) for x in os.getenv("OWNER_IDS", "").replace(" ", "").split(",") if x.isdigit()
}

DB_PATH = BASE_DIR / "data" / "bot.db"
IMAGES_DIR = BASE_DIR / "bot_images"
LOGS_DIR = BASE_DIR / "logs"
LEGACY_XP_FILE = BASE_DIR / "data" / "xp_antigo.json"

# --- Sistema de XP ---
XP_MIN = 8            # XP mínimo por mensagem
XP_MAX = 15           # XP máximo por mensagem
XP_COOLDOWN = 60      # segundos entre ganhos de XP (evita spam)
XP_BASE = 30          # fórmula: XP total p/ nível N = XP_BASE * (N-1)^2

# --- Cores padrão dos embeds ---
COR_PADRAO = 0x5865F2
COR_SUCESSO = 0x57F287
COR_ERRO = 0xED4245
COR_AVISO = 0xFEE75C
