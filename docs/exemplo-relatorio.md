# Diagnóstico do PostgreSQL

Executado em 26/09/2026 às 00:23, contra `monitor@localhost:15438/aplicacao`.
12 checagens em 0,03s.

| Situação | Checagens |
|----------|-----------|
| crítico | 2 |
| atenção | 2 |
| informativo | 3 |
| ok | 5 |

## Tabelas com muitas tuplas mortas

*manutenção* -- crítico

Proporção de linhas mortas em relação as vivas.

**Critério.** Acima de 20% com mais de mil linhas mortas.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| crítico | `app.pedido` | 84000 mortas de 204000 linhas (41.2%), 32 MB no total |

## Tabelas sem vacuum recente

*manutenção* -- crítico

Tabelas com escrita que nunca passaram por vacuum ou analyze.

**Critério.** Nenhum vacuum e nenhum analyze registrado, com mais de mil linhas.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| crítico | `app.evento` | nunca passou por vacuum \| nunca passou por analyze |
| atenção | `app.pedido` | nunca passou por vacuum \| último analyze: 26/09/2026 |
| atenção | `app.item_pedido` | nunca passou por vacuum \| último analyze: 26/09/2026 |
| atenção | `app.cliente` | nunca passou por vacuum \| último analyze: 26/09/2026 |

## Índices redundantes

*índices* -- atenção

Índices cujo conjunto de colunas e prefixo de outro índice da mesma tabela.

**Critério.** Qualquer ocorrência.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| atenção | `app.pedido: idx_pedido_cliente` | coberto por idx_pedido_cliente_data (libera 2344 kB) |

## Sequências próximas do limite

*capacidade* -- atenção

Sequências que já consumiram boa parte do intervalo do tipo.

**Critério.** Acima de 70% do máximo; acima de 90% vira crítico.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| atenção | `app.pedido_id_seq` | em 1700120000 de 2147483647 (79.17%) |

## Índices que nunca foram usados

*índices* -- informativo

Índices sem nenhuma leitura desde o último reset das estatísticas.

**Critério.** Qualquer índice acima de 1 MB sem uso.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| informativo | `app.idx_pedido_cliente_data` | 6440 kB na tabela pedido (0 leituras) |
| informativo | `app.idx_pedido_valor` | 5400 kB na tabela pedido (0 leituras) |
| informativo | `app.idx_pedido_cliente` | 2344 kB na tabela pedido (0 leituras) |
| informativo | `app.idx_pedido_status` | 1360 kB na tabela pedido (0 leituras) |

## Tabelas sem chave primária

*modelagem* -- informativo

Tabelas de usuário sem PRIMARY KEY declarada.

**Critério.** Qualquer tabela com mais de mil linhas estimadas.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| informativo | `app.evento` | sem estimativa (nunca passou por analyze), 9208 kB |

## Maiores tabelas

*capacidade* -- informativo

As dez maiores tabelas, com a proporção ocupada por índices.

**Critério.** Informativo. Não gera alerta; serve de contexto para as demais checagens.

| Gravidade | Objeto | Detalhe |
|-----------|--------|---------|
| informativo | `app.pedido` | 32 MB no total, 20 MB de índices (63%), 120000 linhas |
| informativo | `app.item_pedido` | 11 MB no total, 3640 kB de índices (31%), 120000 linhas |
| informativo | `app.evento` | 9208 kB no total, 536 kB de índices (6%), 64014 linhas |
| informativo | `app.cliente` | 2472 kB no total, 456 kB de índices (18%), 20000 linhas |

## Taxa de acerto de cache

*memória* -- ok

Proporção de blocos servidos pela memória em vez do disco.

**Critério.** Abaixo de 95% costuma indicar shared_buffers pequeno para o volume de leitura.

Nada encontrado.

## Transações abertas há muito tempo

*atividade* -- ok

Sessões com transação aberta há mais de cinco minutos.

**Critério.** Acima de 5 minutos vira atenção; acima de 30 minutos, crítico.

Nada encontrado.

## Sessões esperando bloqueio

*atividade* -- ok

Consultas paradas esperando um lock que outra sessão segura.

**Critério.** Qualquer espera; acima de um minuto vira crítico.

Nada encontrado.

## Uso de conexões

*atividade* -- ok

Conexões abertas em relação ao max_connections, e ociosas em transação.

**Critério.** Acima de 70% do máximo, ou qualquer sessão ociosa em transação.

Nada encontrado.

## Distância do wraparound de transações

*manutenção* -- ok

Idade do xid mais antigo em relação ao limite de congelamento.

**Critério.** Acima de 50% do autovacuum_freeze_max_age; acima de 80% vira crítico.

Nada encontrado.
