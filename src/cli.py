"""Linha de comando do monitor.

    python -m src.cli listar
    python -m src.cli diagnosticar
    python -m src.cli diagnosticar --checagem índices --checagem tuplas
    python -m src.cli diagnosticar --markdown --html
    python -m src.cli detalhar 02_indices_nao_usados
    python -m src.cli preparar-demo

Códigos de saída:
    0  nenhuma checagem em estado crítico
    1  ao menos uma checagem crítica
    2  erro de uso ou de conexão
"""

from __future__ import annotations

import argparse
import sys
import time

import psycopg
from rich.console import Console
from rich.table import Table

from . import checagens as mod_checagens
from . import config, relatorio

console = Console()


# O valor interno da gravidade fica sem acento -- ele é comparado no código
# e gravado no relatório como chave. O que aparece para quem lê vai em
# portugues corrente.
def _seg(valor: float, casas: int = 2) -> str:
    """Tempo com vírgula decimal, como se escreve em português."""
    return f"{valor:.{casas}f}".replace(".", ",") + "s"


ROTULO_GRAVIDADE = {
    "critico": "crítico",
    "atencao": "atenção",
    "informativo": "informativo",
}

COR = {
    "critico": "red",
    "atencao": "yellow",
    "informativo": "cyan",
    "ok": "green",
    "erro": "magenta",
}


def _esperar_banco(cfg: config.Config, tentativas: int = 30) -> None:
    ultimo_erro: Exception | None = None
    for _ in range(tentativas):
        try:
            with psycopg.connect(cfg.dsn, connect_timeout=3) as conexao:
                conexao.execute("SELECT 1")
            return
        except psycopg.OperationalError as erro:
            # Senha recusada não melhora com nova tentativa -- insistir só
            # faz o comando demorar um minuto para dar a mensagem errada.
            #
            # O caso clássico e o volume do Docker ter sido criado com outra
            # senha: o Postgres só lê POSTGRES_PASSWORD na primeira
            # inicialização do diretório de dados e ignora a mudança no .env
            # depois disso.
            if "password authentication failed" in str(erro):
                raise RuntimeError(
                    f"O banco recusou a senha de {cfg.destino_legivel()}. "
                    "Se você mudou POSTGRES_PASSWORD depois de já ter subido o "
                    "container, o volume antigo ainda guarda a senha original. "
                    "Recrie o ambiente com: docker compose down -v && docker compose up -d"
                ) from erro

            ultimo_erro = erro
            time.sleep(2)
    raise RuntimeError(
        f"Sem conexão com {cfg.destino_legivel()}. "
        f"O banco está no ar? Último erro: {ultimo_erro}"
    )


def comando_listar(args: argparse.Namespace) -> int:
    tabela = Table(title="Checagens disponíveis")
    tabela.add_column("Nome", style="bold")
    tabela.add_column("Categoria")
    tabela.add_column("O que procura")

    for checagem in mod_checagens.carregar():
        tabela.add_row(checagem.nome, checagem.categoria, checagem.descricao)

    console.print(tabela)
    return 0


def comando_diagnosticar(args: argparse.Namespace) -> int:
    cfg = config.carregar()
    _esperar_banco(cfg)

    console.print(f"Diagnosticando [bold]{cfg.destino_legivel()}[/bold]...\n")
    resultados = mod_checagens.executar(cfg, args.checagem)
    resumo = mod_checagens.resumir(resultados)

    tabela = Table(title="Resultado")
    tabela.add_column("Situação")
    tabela.add_column("Checagem")
    tabela.add_column("Categoria")
    tabela.add_column("Achados", justify="right")

    for checagem in sorted(
        resultados, key=lambda c: (relatorio.ORDEM.get(c.situacao, 9), c.nome)
    ):
        if not args.tudo and checagem.situacao == "ok":
            continue
        cor = COR.get(checagem.situacao, "white")
        tabela.add_row(
            f"[{cor}]{ROTULO_GRAVIDADE.get(checagem.situacao, checagem.situacao)}[/{cor}]",
            checagem.titulo,
            checagem.categoria,
            str(len(checagem.achados)) if not checagem.erro else "-",
        )

    console.print(tabela)
    console.print(
        f"{resumo['total']} checagens em {_seg(resumo['segundos'])}: "
        f"[red]{resumo['criticos']} críticas[/red], "
        f"[yellow]{resumo['atencao']} em atenção[/yellow], "
        f"[cyan]{resumo['informativos']} informativas[/cyan], "
        f"[green]{resumo['ok']} ok[/green]."
    )
    if resumo["erros"]:
        console.print(f"[magenta]{resumo['erros']} não puderam ser executadas.[/magenta]")

    if args.markdown:
        destino = relatorio.salvar(
            relatorio.em_markdown(resultados, resumo, cfg), "md"
        )
        console.print(f"Markdown em [bold]{destino.relative_to(config.RAIZ)}[/bold]")
    if args.html:
        destino = relatorio.salvar(relatorio.em_html(resultados, resumo, cfg), "html")
        console.print(f"HTML em [bold]{destino.relative_to(config.RAIZ)}[/bold]")

    if not args.tudo and resumo["criticos"] == 0 and resumo["atencao"] == 0:
        console.print(
            "\nNada a corrigir. Use [bold]--tudo[/bold] para ver também o que passou."
        )

    return 1 if resumo["criticos"] else 0


def comando_detalhar(args: argparse.Namespace) -> int:
    cfg = config.carregar()
    _esperar_banco(cfg)

    resultados = mod_checagens.executar(cfg, [args.nome])

    for checagem in resultados:
        console.print(f"\n[bold]{checagem.titulo}[/bold] ({checagem.categoria})")
        if checagem.descricao:
            console.print(checagem.descricao)
        if checagem.limite:
            console.print(f"[dim]Critério: {checagem.limite}[/dim]")

        if checagem.erro:
            console.print(f"[magenta]Não foi possível executar: {checagem.erro}[/magenta]")
            continue

        if not checagem.achados:
            console.print("[green]Nada encontrado.[/green]")
            continue

        tabela = Table()
        tabela.add_column("Gravidade")
        tabela.add_column("Objeto")
        tabela.add_column("Detalhe")
        for achado in sorted(
            checagem.achados, key=lambda a: relatorio.ORDEM.get(a.gravidade, 9)
        ):
            cor = COR.get(achado.gravidade, "white")
            tabela.add_row(
                f"[{cor}]{ROTULO_GRAVIDADE.get(achado.gravidade, achado.gravidade)}[/{cor}]",
                achado.objeto,
                achado.detalhe,
            )
        console.print(tabela)

    return 0


def comando_preparar_demo(args: argparse.Namespace) -> int:
    """Monta a base de demonstração, com os problemas plantados.

    Só faz sentido no container deste repositório. Apontar isto para um
    banco de verdade criaria um schema `app` que ninguém pediu -- por isso
    o comando confirma o destino antes.
    """
    cfg = config.carregar()
    _esperar_banco(cfg)

    console.print(f"Vou criar o schema [bold]app[/bold] em {cfg.destino_legivel()}.")
    if not args.confirmar:
        console.print(
            "[yellow]Nada foi feito.[/yellow] Repita com [bold]--confirmar[/bold] "
            "se este for mesmo o banco de demonstração."
        )
        return 0

    caminho = config.RAIZ / "sql" / "cenario_demo.sql"
    console.print("Criando as tabelas e gerando a massa...")

    inicio = time.perf_counter()
    with psycopg.connect(cfg.dsn) as conexao:
        conexao.execute(caminho.read_text(encoding="utf-8"))
    decorrido = time.perf_counter() - inicio

    console.print(f"Cenário pronto em {_seg(decorrido, 1)}.")
    console.print("Agora rode: [bold]python -m src.cli diagnosticar[/bold]")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pg-health",
        description="Diagnóstico de saude de uma instância PostgreSQL.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("listar", help="mostra as checagens cadastradas")
    p.set_defaults(funcao=comando_listar)

    p = sub.add_parser("diagnosticar", help="roda todas as checagens")
    p.add_argument(
        "--checagem",
        action="append",
        metavar="NOME",
        help="roda apenas as checagens cujo nome contem o texto; pode repetir",
    )
    p.add_argument("--tudo", action="store_true", help="mostra também o que passou")
    p.add_argument("--markdown", action="store_true", help="grava relatório em Markdown")
    p.add_argument("--html", action="store_true", help="grava relatório em HTML")
    p.set_defaults(funcao=comando_diagnosticar)

    p = sub.add_parser("detalhar", help="mostra os achados de uma checagem")
    p.add_argument("nome")
    p.set_defaults(funcao=comando_detalhar)

    p = sub.add_parser(
        "preparar-demo", help="cria a base de demonstração com problemas plantados"
    )
    p.add_argument("--confirmar", action="store_true")
    p.set_defaults(funcao=comando_preparar_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return args.funcao(args)
    except (RuntimeError, FileNotFoundError) as erro:
        console.print(f"[red]{erro}[/red]")
        return 2


if __name__ == "__main__":
    sys.exit(main())
