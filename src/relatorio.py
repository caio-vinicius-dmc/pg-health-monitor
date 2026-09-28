"""Relatório do diagnóstico, em Markdown e HTML."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .checagens import Checagem
from .config import RAIZ, Config


def _seg(valor: float, casas: int = 2) -> str:
    """Tempo com vírgula decimal, como se escreve em português."""
    return f"{valor:.{casas}f}".replace(".", ",") + "s"

PASTA = RAIZ / "relatorios"

ORDEM = {"critico": 0, "atencao": 1, "erro": 2, "informativo": 3, "ok": 4}

ROTULO = {
    "critico": "crítico",
    "atencao": "atenção",
    "informativo": "informativo",
    "erro": "erro ao executar",
    "ok": "ok",
}


def _ordenar(checagens: list[Checagem]) -> list[Checagem]:
    return sorted(checagens, key=lambda c: (ORDEM.get(c.situacao, 9), c.nome))


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def em_markdown(checagens: list[Checagem], resumo: dict, cfg: Config) -> str:
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    partes = [
        "# Diagnóstico do PostgreSQL",
        "",
        f"Executado em {agora}, contra `{cfg.destino_legivel()}`.",
        f"{resumo['total']} checagens em {_seg(resumo['segundos'])}.",
        "",
        "| Situação | Checagens |",
        "|----------|-----------|",
        f"| crítico | {resumo['criticos']} |",
        f"| atenção | {resumo['atencao']} |",
        f"| informativo | {resumo['informativos']} |",
        f"| ok | {resumo['ok']} |",
    ]
    if resumo["erros"]:
        partes.append(f"| erro ao executar | {resumo['erros']} |")
    partes.append("")

    for checagem in _ordenar(checagens):
        partes.extend(
            [
                f"## {checagem.titulo}",
                "",
                f"*{checagem.categoria}* -- {ROTULO.get(checagem.situacao, checagem.situacao)}",
                "",
            ]
        )
        if checagem.descricao:
            partes.extend([checagem.descricao, ""])
        if checagem.limite:
            partes.extend([f"**Critério.** {checagem.limite}", ""])

        if checagem.erro:
            partes.extend([f"Não foi possível executar: `{checagem.erro}`", ""])
            continue

        if not checagem.achados:
            partes.extend(["Nada encontrado.", ""])
            continue

        partes.extend(
            [
                "| Gravidade | Objeto | Detalhe |",
                "|-----------|--------|---------|",
            ]
        )
        for achado in sorted(
            checagem.achados, key=lambda a: ORDEM.get(a.gravidade, 9)
        ):
            detalhe = achado.detalhe.replace("|", r"\|")
            partes.append(f"| {ROTULO.get(achado.gravidade, achado.gravidade)} | `{achado.objeto}` | {detalhe} |")
        partes.append("")

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
# Arquivo único, com o CSS embutido e sem nenhum recurso externo: abre em
# qualquer navegador, inclusive numa máquina sem rede -- que costuma ser
# exatamente o caso de quem está diagnosticando um banco.
ESTILO = """
:root { color-scheme: light dark; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  max-width: 62rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.55;
  background: #fcfcfb; color: #0b0b0b;
}
h1 { font-size: 1.6rem; margin-bottom: .2rem; }
h2 { font-size: 1.12rem; margin: 2rem 0 .3rem; }
p.meta { color: #898781; margin-top: 0; font-size: .92rem; }
p.criterio { color: #52514e; font-size: .92rem; margin: .2rem 0 .6rem; }
table { border-collapse: collapse; width: 100%; margin: .6rem 0 0; font-size: .9rem; }
th, td { border: 1px solid #e1e0d9; padding: .4rem .6rem; text-align: left; vertical-align: top; }
th { background: #f3f3f0; font-weight: 600; }
code { font-size: .88em; }
.selo {
  display: inline-block; padding: .08rem .5rem; border-radius: 10px;
  font-size: .78rem; font-weight: 600; vertical-align: middle;
}
.crítico { background: #f6d5d5; color: #7a1f1f; }
.atenção { background: #fbeccd; color: #6b4a06; }
.informativo { background: #dde7f6; color: #1c4478; }
.ok { background: #d8ecd8; color: #1d5c1d; }
.erro { background: #e6e6e6; color: #4a4a4a; }
.vazio { color: #898781; font-size: .92rem; }
@média (prefers-color-scheme: dark) {
  body { background: #1a1a19; color: #ffffff; }
  th { background: #2a2a28; }
  th, td { border-color: #383835; }
  p.criterio { color: #c3c2b7; }
  .crítico { background: #5a2020; color: #ffd9d9; }
  .atenção { background: #5a4a15; color: #ffeec2; }
  .informativo { background: #1f3a5f; color: #d6e5fb; }
  .ok { background: #1f4a1f; color: #d6f0d6; }
  .erro { background: #333; color: #ddd; }
}
"""


def _escapar(texto: object) -> str:
    return (
        str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def em_html(checagens: list[Checagem], resumo: dict, cfg: Config) -> str:
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    corpo = [
        "<h2>Resumo</h2>",
        "<table><thead><tr><th>Situacao</th><th>Checagens</th></tr></thead><tbody>",
    ]
    for chave, quantidade in (
        ("critico", resumo["criticos"]),
        ("atencao", resumo["atencao"]),
        ("informativo", resumo["informativos"]),
        ("ok", resumo["ok"]),
        ("erro", resumo["erros"]),
    ):
        if chave == "erro" and not quantidade:
            continue
        corpo.append(
            f'<tr><td><span class="selo {chave}">{ROTULO[chave]}</span></td>'
            f"<td>{quantidade}</td></tr>"
        )
    corpo.append("</tbody></table>")

    for checagem in _ordenar(checagens):
        selo = f'<span class="selo {checagem.situacao}">{ROTULO.get(checagem.situacao, checagem.situacao)}</span>'
        corpo.append(f"<h2>{_escapar(checagem.titulo)} {selo}</h2>")
        if checagem.descricao:
            corpo.append(
                f'<p class="critério">{_escapar(checagem.descricao)}</p>'
            )
        if checagem.limite:
            corpo.append(
                f'<p class="critério"><strong>Critério.</strong> {_escapar(checagem.limite)}</p>'
            )

        if checagem.erro:
            corpo.append(
                f'<p class="vazio">Não foi possível executar: <code>{_escapar(checagem.erro)}</code></p>'
            )
            continue

        if not checagem.achados:
            corpo.append('<p class="vazio">Nada encontrado.</p>')
            continue

        corpo.append(
            "<table><thead><tr><th>Gravidade</th><th>Objeto</th><th>Detalhe</th>"
            "</tr></thead><tbody>"
        )
        for achado in sorted(
            checagem.achados, key=lambda a: ORDEM.get(a.gravidade, 9)
        ):
            corpo.append(
                f'<tr><td><span class="selo {achado.gravidade}">{achado.gravidade}</span></td>'
                f"<td><code>{_escapar(achado.objeto)}</code></td>"
                f"<td>{_escapar(achado.detalhe)}</td></tr>"
            )
        corpo.append("</tbody></table>")

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Diagnóstico do PostgreSQL</title>
<style>{ESTILO}</style>
</head>
<body>
<h1>Diagnóstico do PostgreSQL</h1>
<p class="meta">{_escapar(agora)} &middot; {_escapar(cfg.destino_legivel())} &middot;
{resumo['total']} checagens em {_seg(resumo['segundos'])}</p>
{chr(10).join(corpo)}
</body>
</html>
"""


def salvar(conteudo: str, extensao: str) -> Path:
    PASTA.mkdir(exist_ok=True)
    destino = PASTA / f"{datetime.now():%Y-%m-%d_%H%M%S}.{extensao}"
    destino.write_text(conteudo, encoding="utf-8")
    return destino
