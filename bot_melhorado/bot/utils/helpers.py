"""Funções utilitárias compartilhadas pelos módulos."""
from __future__ import annotations

import ast
import math
import operator
import re
import secrets
import string
from datetime import timedelta

import discord

from bot import config

# ---------- Embeds ----------

def embed(titulo: str | None = None, descricao: str | None = None, cor: int = config.COR_PADRAO) -> discord.Embed:
    return discord.Embed(title=titulo, description=descricao, color=cor, timestamp=discord.utils.utcnow())


def sucesso(texto: str) -> discord.Embed:
    return embed(None, f"✅ {texto}", config.COR_SUCESSO)


def erro(texto: str) -> discord.Embed:
    return embed(None, f"❌ {texto}", config.COR_ERRO)


def aviso(texto: str) -> discord.Embed:
    return embed(None, f"⚠️ {texto}", config.COR_AVISO)


# ---------- Níveis ----------

def level_from_xp(xp: int) -> int:
    """Nível 1 com 0 XP; nível N exige XP_BASE * (N-1)^2 de XP total."""
    return math.isqrt(max(xp, 0) // config.XP_BASE) + 1


def xp_for_level(level: int) -> int:
    return config.XP_BASE * (max(level, 1) - 1) ** 2


def progress_bar(atual: int, total: int, tamanho: int = 12) -> str:
    total = max(total, 1)
    cheio = min(tamanho, int(tamanho * atual / total))
    return "▰" * cheio + "▱" * (tamanho - cheio)


# ---------- Tempo ----------
_DURACAO = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
_UNIDADES = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duration(texto: str) -> timedelta | None:
    """Converte '1h30m', '10m', '2d' em timedelta. Retorna None se inválido."""
    texto = texto.strip().lower()
    partes = _DURACAO.findall(texto)
    if not partes or _DURACAO.sub("", texto).strip():
        return None
    segundos = sum(int(n) * _UNIDADES[u] for n, u in partes)
    return timedelta(seconds=segundos) if segundos > 0 else None


def format_duration(segundos: int) -> str:
    partes = []
    for nome, valor in (("d", 86400), ("h", 3600), ("min", 60), ("s", 1)):
        q, segundos = divmod(segundos, valor)
        if q:
            partes.append(f"{q}{nome}")
    return " ".join(partes) or "0s"


# ---------- Senhas ----------

def gen_pass(tamanho: int = 16) -> str:
    """Senha aleatória criptograficamente segura (letras, números e símbolos)."""
    alfabeto = string.ascii_letters + string.digits + "+-/*!&$#?=@<>"
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
        if tamanho < 8 or (
            any(c.islower() for c in senha)
            and any(c.isupper() for c in senha)
            and any(c.isdigit() for c in senha)
        ):
            return senha


# ---------- Calculadora segura ----------
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(expressao: str) -> float:
    """Avalia expressões matemáticas simples sem usar eval()."""

    def _eval(no):
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return no.value
        if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
            esq, dir_ = _eval(no.left), _eval(no.right)
            if isinstance(no.op, ast.Pow) and abs(dir_) > 100:
                raise ValueError("Expoente muito grande")
            return _OPS[type(no.op)](esq, dir_)
        if isinstance(no, ast.UnaryOp) and type(no.op) in _OPS:
            return _OPS[type(no.op)](_eval(no.operand))
        raise ValueError("Expressão inválida")

    arvore = ast.parse(expressao.replace("^", "**").replace(",", "."), mode="eval")
    return _eval(arvore.body)
