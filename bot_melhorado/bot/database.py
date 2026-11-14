"""Camada de banco de dados (SQLite assíncrono)."""
from __future__ import annotations

import time
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    xp       INTEGER NOT NULL DEFAULT 0,
    messages INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS warns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    mod_id     INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_warns ON warns (guild_id, user_id);
CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER NOT NULL,
    key      TEXT NOT NULL,
    value    TEXT,
    PRIMARY KEY (guild_id, key)
);
CREATE TABLE IF NOT EXISTS level_roles (
    guild_id INTEGER NOT NULL,
    level    INTEGER NOT NULL,
    role_id  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, level)
);
CREATE TABLE IF NOT EXISTS reminders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    remind_at  INTEGER NOT NULL,
    text       TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # ---------- XP ----------
    async def get_user(self, guild_id: int, user_id: int):
        cur = await self.conn.execute(
            "SELECT xp, messages FROM users WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        )
        return await cur.fetchone()

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int]:
        """Soma XP e retorna (xp_antigo, xp_novo)."""
        row = await self.get_user(guild_id, user_id)
        old = row["xp"] if row else 0
        await self.conn.execute(
            """INSERT INTO users (guild_id, user_id, xp, messages) VALUES (?, ?, ?, 1)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = xp + ?, messages = messages + 1""",
            (guild_id, user_id, amount, amount),
        )
        await self.conn.commit()
        return old, old + amount

    async def set_xp(self, guild_id: int, user_id: int, xp: int) -> None:
        await self.conn.execute(
            """INSERT INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = ?""",
            (guild_id, user_id, xp, xp),
        )
        await self.conn.commit()

    async def reset_user(self, guild_id: int, user_id: int) -> None:
        await self.conn.execute("DELETE FROM users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()

    async def position(self, guild_id: int, user_id: int) -> int:
        cur = await self.conn.execute(
            """SELECT COUNT(*) + 1 AS pos FROM users
               WHERE guild_id=? AND xp > (SELECT COALESCE(MAX(xp), 0) FROM users WHERE guild_id=? AND user_id=?)""",
            (guild_id, guild_id, user_id),
        )
        return (await cur.fetchone())["pos"]

    async def top(self, guild_id: int, limit: int = 10, offset: int = 0):
        cur = await self.conn.execute(
            "SELECT user_id, xp, messages FROM users WHERE guild_id=? ORDER BY xp DESC LIMIT ? OFFSET ?",
            (guild_id, limit, offset),
        )
        return await cur.fetchall()

    async def count_users(self, guild_id: int) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS n FROM users WHERE guild_id=?", (guild_id,))
        return (await cur.fetchone())["n"]

    # ---------- Advertências ----------
    async def add_warn(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason, int(time.time())),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_warns(self, guild_id: int, user_id: int):
        cur = await self.conn.execute(
            "SELECT * FROM warns WHERE guild_id=? AND user_id=? ORDER BY id", (guild_id, user_id)
        )
        return await cur.fetchall()

    async def delete_warn(self, guild_id: int, warn_id: int) -> bool:
        cur = await self.conn.execute("DELETE FROM warns WHERE guild_id=? AND id=?", (guild_id, warn_id))
        await self.conn.commit()
        return cur.rowcount > 0

    async def clear_warns(self, guild_id: int, user_id: int) -> int:
        cur = await self.conn.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()
        return cur.rowcount

    # ---------- Configurações por servidor ----------
    async def get_setting(self, guild_id: int, key: str) -> str | None:
        cur = await self.conn.execute("SELECT value FROM settings WHERE guild_id=? AND key=?", (guild_id, key))
        row = await cur.fetchone()
        return row["value"] if row else None

    async def get_int_setting(self, guild_id: int, key: str) -> int | None:
        value = await self.get_setting(guild_id, key)
        return int(value) if value and value.lstrip("-").isdigit() else None

    async def set_setting(self, guild_id: int, key: str, value: str | int | None) -> None:
        if value is None:
            await self.conn.execute("DELETE FROM settings WHERE guild_id=? AND key=?", (guild_id, key))
        else:
            await self.conn.execute(
                """INSERT INTO settings (guild_id, key, value) VALUES (?, ?, ?)
                   ON CONFLICT(guild_id, key) DO UPDATE SET value = ?""",
                (guild_id, key, str(value), str(value)),
            )
        await self.conn.commit()

    # ---------- Cargos por nível ----------
    async def set_level_role(self, guild_id: int, level: int, role_id: int) -> None:
        await self.conn.execute(
            """INSERT INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)
               ON CONFLICT(guild_id, level) DO UPDATE SET role_id = ?""",
            (guild_id, level, role_id, role_id),
        )
        await self.conn.commit()

    async def remove_level_role(self, guild_id: int, level: int) -> bool:
        cur = await self.conn.execute("DELETE FROM level_roles WHERE guild_id=? AND level=?", (guild_id, level))
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_level_roles(self, guild_id: int):
        cur = await self.conn.execute(
            "SELECT level, role_id FROM level_roles WHERE guild_id=? ORDER BY level", (guild_id,)
        )
        return await cur.fetchall()

    # ---------- Lembretes ----------
    async def add_reminder(self, user_id: int, channel_id: int, remind_at: int, text: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO reminders (user_id, channel_id, remind_at, text) VALUES (?, ?, ?, ?)",
            (user_id, channel_id, remind_at, text),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def due_reminders(self, now: int):
        cur = await self.conn.execute("SELECT * FROM reminders WHERE remind_at <= ?", (now,))
        return await cur.fetchall()

    async def user_reminders(self, user_id: int):
        cur = await self.conn.execute("SELECT * FROM reminders WHERE user_id=? ORDER BY remind_at", (user_id,))
        return await cur.fetchall()

    async def delete_reminder(self, reminder_id: int, user_id: int | None = None) -> bool:
        if user_id is None:
            cur = await self.conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
        else:
            cur = await self.conn.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (reminder_id, user_id))
        await self.conn.commit()
        return cur.rowcount > 0
