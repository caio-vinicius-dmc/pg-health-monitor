"""Configuração lida de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent

load_dotenv(RAIZ / ".env")


@dataclass(frozen=True)
class Config:
    host: str
    porta: int
    banco: str
    usuario: str
    senha: str

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.porta} dbname={self.banco} "
            f"user={self.usuario} password={self.senha} "
            "application_name=pg-health-monitor"
        )

    def destino_legivel(self) -> str:
        """Identificacao do banco sem a senha, para log e relatório."""
        return f"{self.usuario}@{self.host}:{self.porta}/{self.banco}"


def carregar() -> Config:
    return Config(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        porta=int(os.getenv("POSTGRES_PORT", "15438")),
        banco=os.getenv("POSTGRES_DB", "aplicacao"),
        usuario=os.getenv("POSTGRES_USER", "monitor"),
        senha=os.getenv("POSTGRES_PASSWORD", "monitor_local"),
    )
