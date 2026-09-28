"""Carregamento e execução das checagens.

Cada checagem é um arquivo `.sql` em `checagens/`, com os metadados no
próprio cabeçalho. Acrescentar uma verificação é criar um arquivo -- nada
no Python muda.

O contrato é simples: a consulta devolve zero ou mais linhas, com as
colunas `objeto`, `detalhe` e `gravidade`. Zero linhas significa que está
tudo bem. É o inverso do formato "métrica e limite": aqui a própria
consulta decide o que é achado, e o Python só organiza.

A razão de ser assim: metade das checagens úteis de saúde não tem um
número único (quais índices estão sem uso? quais sessões estão
bloqueadas?). Forçá-las num formato de métrica exigiria uma segunda
consulta para ver o detalhe.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from .config import RAIZ, Config

PASTA = RAIZ / "checagens"

ORDEM_GRAVIDADE = {"critico": 0, "atencao": 1, "informativo": 2}


@dataclass
class Achado:
    objeto: str
    detalhe: str
    gravidade: str


@dataclass
class Checagem:
    nome: str
    titulo: str
    categoria: str
    descricao: str
    limite: str
    sql: str
    achados: list[Achado] = field(default_factory=list)
    erro: str | None = None
    segundos: float = 0.0

    @property
    def informativa(self) -> bool:
        """Checagem que nunca alerta: existe para dar contexto."""
        return all(a.gravidade == "informativo" for a in self.achados) and bool(
            self.achados
        )

    @property
    def situacao(self) -> str:
        if self.erro:
            return "erro"
        if not self.achados:
            return "ok"
        return min(
            (a.gravidade for a in self.achados),
            key=lambda g: ORDEM_GRAVIDADE.get(g, 9),
        )

    def contar(self, gravidade: str) -> int:
        return sum(1 for a in self.achados if a.gravidade == gravidade)


def _sem_acento(texto: str) -> str:
    """Remove acentos para efeito de comparação.

    O cabeçalho das checagens e escrito em portugues corrente, com acento
    (`-- título:`, `-- descrição:`). Comparar sem acento evita que a busca
    dependa de alguém ter digitado exatamente do mesmo jeito -- e evita o
    modo de falha mais chato desse formato: a checagem roda, mas aparece no
    relatório sem título nenhum, porque a chave não casou.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    ).lower()


def _metadado(texto: str, chave: str) -> str:
    alvo = _sem_acento(f"-- {chave}:")
    for linha in texto.splitlines():
        if _sem_acento(linha).startswith(alvo):
            return linha.split(":", 1)[1].strip()
        if linha.strip() and not linha.startswith("--"):
            break
    return ""


def carregar() -> list[Checagem]:
    checagens = []

    for arquivo in sorted(PASTA.glob("*.sql")):
        texto = arquivo.read_text(encoding="utf-8")
        checagens.append(
            Checagem(
                nome=arquivo.stem,
                titulo=_metadado(texto, "titulo") or arquivo.stem,
                categoria=_metadado(texto, "categoria") or "geral",
                descricao=_metadado(texto, "descricao"),
                limite=_metadado(texto, "limite"),
                sql=texto,
            )
        )

    if not checagens:
        raise FileNotFoundError(f"Nenhuma checagem encontrada em {PASTA}")

    return checagens


def executar(cfg: Config, selecionadas: list[str] | None = None) -> list[Checagem]:
    todas = carregar()

    if selecionadas:
        nomes = set(selecionadas)
        todas = [
            c for c in todas if c.nome in nomes or any(n in c.nome for n in nomes)
        ]
        if not todas:
            disponiveis = ", ".join(c.nome for c in carregar())
            raise RuntimeError(f"Nenhuma checagem corresponde. Disponíveis: {disponiveis}")

    with psycopg.connect(cfg.dsn, row_factory=dict_row) as conexao:
        # Somente leitura: garante que uma checagem mal escrita não consiga
        # alterar nada no banco observado, nem por acidente.
        conexao.read_only = True

        for checagem in todas:
            inicio = time.perf_counter()
            try:
                with conexao.cursor() as cursor:
                    cursor.execute(checagem.sql)
                    checagem.achados = [
                        Achado(
                            objeto=str(linha["objeto"]),
                            detalhe=str(linha["detalhe"]),
                            gravidade=str(linha["gravidade"]),
                        )
                        for linha in cursor.fetchall()
                    ]
            except psycopg.Error as erro:
                # Uma checagem que falha não pode derrubar o diagnóstico
                # inteiro: versões diferentes do Postgres expõem colunas
                # diferentes no catálogo, e é normal que uma ou outra não
                # rode em todo lugar.
                conexao.rollback()
                checagem.erro = str(erro).strip().splitlines()[0]

            checagem.segundos = time.perf_counter() - inicio

    return todas


def resumir(checagens: list[Checagem]) -> dict:
    return {
        "total": len(checagens),
        "ok": sum(1 for c in checagens if c.situacao == "ok"),
        "criticos": sum(1 for c in checagens if c.situacao == "critico"),
        "atencao": sum(1 for c in checagens if c.situacao == "atencao"),
        "informativos": sum(1 for c in checagens if c.situacao == "informativo"),
        "erros": sum(1 for c in checagens if c.situacao == "erro"),
        "achados": sum(len(c.achados) for c in checagens),
        "segundos": sum(c.segundos for c in checagens),
    }
