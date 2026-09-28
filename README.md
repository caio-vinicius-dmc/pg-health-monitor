# pg-health-monitor

Doze exames de saúde para um banco PostgreSQL, escritos em SQL puro.
Aponta para qualquer banco e devolve um relatório do que está fora do
lugar.

## Do que se trata, em linguagem simples

Todo banco de dados acumula problemas silenciosos: índices que ninguém usa
mas que deixam o sistema mais lento, tabelas que nunca passaram por
limpeza, um contador que vai estourar daqui a seis meses, uma sessão
esquecida segurando o banco inteiro.

Nenhum deles dá erro. O sistema só fica gradualmente pior, até alguém
reclamar.

Este projeto é o que você roda no primeiro contato com um banco que não
conhece. Não é um monitor de tempo real nem substitui ferramentas como
Prometheus: é o exame de rotina, o que se faz sentando na frente do
paciente.

## Os doze exames

| Exame | O que procura | Por que importa |
|-------|--------------|-----------------|
| Taxa de acerto de cache | quanto o banco lê do disco em vez da memória | disco é milhares de vezes mais lento |
| Índices nunca usados | índice que existe mas ninguém consulta | ocupa espaço e atrasa toda gravação |
| Índices redundantes | índice coberto por outro maior | paga o custo duas vezes sem ganho |
| Tabelas com linhas mortas | espaço que exclusões deixaram para trás | a tabela cresce e fica lenta sem ter mais dados |
| Tabelas sem limpeza | nunca passaram por vacuum ou analyze | o banco escolhe caminhos ruins com confiança total |
| Transações antigas | sessão aberta há muito tempo | impede a limpeza do banco inteiro |
| Sessões travadas | consulta esperando outra liberar | e quem é o culpado |
| Uso de conexões | proximidade do limite | chegar no limite derruba a aplicação |
| Sequências no limite | contador perto de estourar | quando estoura, o sistema para de gravar |
| Tabelas sem chave primária | linhas que não dá para identificar | inviabiliza correção e replicação |
| Distância do wraparound | um contador interno do PostgreSQL | se estourar, o banco vira somente leitura |
| Maiores tabelas | onde o espaço está | contexto para os outros exames |

## O que você vai ver

Rodando contra a base de demonstração, que tem problemas plantados de
propósito:

```
Situação      Exame                                   Categoria    Achados
crítico       Tabelas com muitas linhas mortas        manutenção         1
crítico       Tabelas sem vacuum recente              manutenção         4
atenção       Índices redundantes                     índices            1
atenção       Sequências próximas do limite           capacidade         1
informativo   Índices que nunca foram usados          índices            4
informativo   Tabelas sem chave primária              modelagem          1
informativo   Maiores tabelas                         capacidade         4
ok            Taxa de acerto de cache                 memória            0
ok            Transações abertas há muito tempo       atividade          0
ok            Sessões esperando bloqueio              atividade          0
ok            Uso de conexões                         atividade          0
ok            Distância do wraparound                 manutenção         0

12 exames em 0,03s: 2 críticos, 2 em atenção, 3 informativos, 5 ok.
```

Para ver o detalhe de um deles:

```bash
python -m src.cli detalhar 04_tuplas_mortas
```

```
Gravidade   Objeto        Detalhe
crítico     app.pedido    84000 mortas de 204000 linhas (41.2%), 32 MB no total
```

## O que você precisa ter instalado

- **Python 3.11 ou mais novo** —
  [python.org](https://www.python.org/downloads/), marcando "Add Python to
  PATH".
- **Um banco PostgreSQL** que você queira examinar. Se quiser só
  experimentar, o projeto traz um pronto — aí você também precisa do
  **Docker Desktop**.

## Como rodar

**1. Ambiente do Python.**

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

No Linux ou macOS: `source .venv/bin/activate`.

**2. Aponte para o banco.** Copie o arquivo de exemplo e preencha com os
dados do banco que você quer examinar:

```bash
cp .env.example .env
```

**3. Rode o exame.**

```bash
python -m src.cli diagnosticar
```

Por padrão só aparece o que precisa de atenção. Numa instância saudável a
saída é curta — e isso é bom.

### Para experimentar sem apontar para um banco de verdade

O repositório traz um banco de demonstração com problemas plantados:

```bash
docker compose up -d
python -m src.cli preparar-demo --confirmar
python -m src.cli diagnosticar --tudo --html
```

O `--confirmar` existe de propósito: o comando cria um schema chamado
`app`, e sem a confirmação ele apenas mostra em qual banco iria mexer e
não faz nada. É uma proteção contra rodar isso sem querer num banco real.

Para desligar depois: `docker compose down -v`.

## Escolhendo o que rodar

```bash
python -m src.cli listar                            # o catálogo completo
python -m src.cli diagnosticar --checagem indices   # só os de índice
python -m src.cli diagnosticar --checagem tuplas --checagem vacuum
python -m src.cli diagnosticar --tudo               # inclui o que passou
python -m src.cli detalhar 02_indices_nao_usados    # o detalhe de um exame
```

## Os relatórios

```bash
python -m src.cli diagnosticar --markdown --html
```

O Markdown serve para colar num chamado ou num pull request. O HTML é um
arquivo único, com o estilo embutido e sem nada vindo da internet — abre
em qualquer navegador, inclusive numa máquina sem rede, que costuma ser
exatamente a situação de quem está diagnosticando um banco.

Os dois trazem, para cada exame, a descrição, o critério usado e a tabela
completa de achados. Um relatório de verdade está em
[docs/exemplo-relatorio.md](docs/exemplo-relatorio.md).

## Apontando para um banco de produção

Tudo que o monitor precisa é permissão de leitura:

```sql
CREATE USER pg_health WITH PASSWORD 'defina_uma_senha_forte';
GRANT CONNECT ON DATABASE sua_base TO pg_health;
GRANT pg_read_all_stats TO pg_health;
GRANT USAGE ON SCHEMA public TO pg_health;
```

A permissão `pg_read_all_stats` é o que libera as estatísticas para um
usuário comum. Sem ela, vários exames devolvem vazio em vez de erro — o
que é pior, porque parece que está tudo bem.

A conexão é aberta em modo somente leitura. Um exame mal escrito não
consegue alterar nada no banco observado, nem por acidente.

## Acrescentando um exame

Cada exame é um arquivo `.sql` na pasta `checagens/`, com as informações
no próprio cabeçalho:

```sql
-- titulo: Tabelas com muitas tuplas mortas
-- categoria: manutencao
-- descricao: Proporcao de linhas mortas em relacao as vivas.
-- limite: Acima de 20% com mais de mil linhas mortas.

SELECT ... AS objeto, ... AS detalhe, ... AS gravidade FROM ...
```

A regra é devolver zero ou mais linhas com três colunas: `objeto`,
`detalhe` e `gravidade` (que pode ser `critico`, `atencao` ou
`informativo`). Zero linhas significa que está tudo bem.

Criar o arquivo basta — nada no Python muda.

Esse formato é o inverso do "métrica e limite", e por um motivo prático:
metade dos exames úteis não tem um número único. "Quais índices estão sem
uso?" e "quais sessões estão travadas?" são listas, não medidas.

O raciocínio por trás de cada exame — de onde veio o limite e o que ele
**não** pega — está em [docs/checagens.md](docs/checagens.md).

## Estrutura das pastas

```
checagens/*.sql      um exame por arquivo, informações no cabeçalho
src/checagens.py     carrega, executa e classifica
src/relatorio.py     escreve o Markdown e o HTML
src/cli.py           a linha de comando
sql/cenario_demo.sql o banco de demonstração com problemas plantados
docs/checagens.md    o critério de cada exame e o que ele não pega
```

## Problemas comuns

**"ports are not available" ou "bind: An attempt was made to access a socket
in a way forbidden by its access permissions".** O Windows reserva faixas de
porta para uso próprio, e elas mudam a cada reinício. Veja quais estão
reservadas com:

```bash
netsh int ipv4 show excludedportrange protocol=tcp
```

Se a porta do projeto estiver numa das faixas, mude `POSTGRES_PORT` no
arquivo `.env` para qualquer valor livre abaixo de 49152 e suba de novo.

**"O banco recusou a senha."** Se você está usando o banco de
demonstração e mudou a senha no `.env` depois de já ter subido o
container, recrie com `docker compose down -v && docker compose up -d`.

**Vários exames aparecem vazios num banco que você sabe que tem
problemas.** Provavelmente falta a permissão `pg_read_all_stats` no
usuário.

**Tudo aparece saudável logo depois de reiniciar o banco.** É esperado: as
estatísticas se perdem no reinício. Veja a próxima seção.

## Limitações

- **O inchaço das tabelas é estimado, não medido.** A medição exata exige
  uma extensão que varre a tabela inteira, cara demais para uso rotineiro.
  O número aqui é um indicador.
- **As estatísticas são cumulativas e se perdem num desligamento
  abrupto.** "Índice nunca usado" numa instância reiniciada ontem não
  significa nada. O caso está contado em
  [docs/checagens.md](docs/checagens.md#um-detalhe-que-custou-uma-execucao-inteira).
- **É uma foto, não um filme.** Cada execução é independente; o projeto
  não guarda histórico. Para acompanhar tendência, o
  [query-regression-radar](../query-regression-radar) faz isso para
  desempenho de consulta.
- **Não há exame de replicação.** Réplica atrasada e slot abandonado são
  duas causas comuns de disco cheio, e ficaram de fora porque exigiriam
  uma instância com réplica configurada para serem testados de verdade.

---

## 👤 Autor

Desenvolvido por **Caio Vinícius Barbosa Barros**.

Se você tiver dúvidas, sugestões ou quiser reportar um problema, sinta-se à vontade para entrar em contato:

*   **✉️ E-mail:** [caio@dynamicmotioncentury.com.br](mailto:caio@dynamicmotioncentury.com.br)
*   **🌐 Site/Portfólio:** [www.dynamicmotioncentury.com.br](https://dynamicmotioncentury.com.br)
*   **💼 LinkedIn:** [linkedin.com/in/caio-vinicius-dmc](https://linkedin.com/in/caio-vinicius-dmc)
*   **🐙 GitHub:** [@caio-vinicius-dmc](https://github.com/caio-vinicius-dmc)

💡 *Se este projeto te ajudou, deixe uma ⭐ no repositório!*
