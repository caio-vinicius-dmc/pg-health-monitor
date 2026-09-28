# As checagens, uma a uma

De onde vem cada limite, e o que cada checagem **não** pega. A segunda
parte costuma ser a mais importante: monitoramento que ninguém sabe
interpretar vira ruído, e ruído vira alerta desligado.

## memória

### Taxa de acerto de cache

Proporção de blocos servidos pela memória em vez do disco, a partir de
`pg_stat_database`. Abaixo de 95% vira atenção, abaixo de 90% vira crítico.

O número de 95% é a régua tradicional, e vale menos do que parece. Uma base
OLTP saudável fica acima de 99%; uma base analítica que varre tabelas
grandes de propósito fica bem abaixo e está certa assim. Trate como ponto
de partida de investigação, não como meta.

A linha só aparece quando há mais de cem mil blocos lidos no total. Logo
depois de um restart, a taxa é baixa por natureza e não significa nada --
reportar isso seria alarme falso garantido.

**Não pega.** Pressão de memória no nível do sistema operacional. O
PostgreSQL conta como "acerto" o que veio do cache dele; o que veio do
cache do sistema operacional aparece como leitura de disco, mesmo sem ter
tocado no disco.

## índices

### Índices que nunca foram usados

`idx_scan = 0` em `pg_stat_user_indexes`, para índices acima de 1 MB.
Acima de 50 MB vira atenção; abaixo disso fica informativo.

Índice sem uso custa duas vezes: ocupa disco e torna todo `INSERT`,
`UPDATE` e `DELETE` da tabela mais lento, porque precisa ser mantido em
dia. É dos itens com melhor relação entre esforço e ganho numa faxina.

Índices únicos e de chave primária são excluídos da lista: eles existem
para garantir a regra, não para serem lidos.

**Cuidado antes de apagar.** Índice que atende um relatório mensal aparece
aqui em qualquer coleta feita no dia 2. E as estatísticas são cumulativas
desde o último reset -- numa instância reiniciada ontem, *todos* os índices
aparecem como não usados. Confira `pg_stat_database.stats_reset` antes de
concluir qualquer coisa.

**Não pega.** Índice usado raramente mas indispensável: o que sustenta o
fechamento contábil aparece com duas leituras no mês e parece descartável.

### Índices redundantes

Índice cujo conjunto de colunas é prefixo de outro índice da mesma tabela.
Um índice em `(a)` é redundante quando já existe um em `(a, b)`: o segundo
atende tudo que o primeiro atenderia.

A detecção usa `indkey`, o vetor de colunas do índice, e compara por
prefixo com `LIKE`. Não é a comparação mais elegante possível, mas é a que
funciona sem instalar extensão nenhuma.

**Não pega.** Redundância com colunas na ordem diferente, índices parciais
com a mesma expressão de `WHERE`, e índices equivalentes com métodos
diferentes (B-tree e hash na mesma coluna).

## manutenção

### Tabelas com muitas tuplas mortas

Proporção de `n_dead_tup` sobre o total. Acima de 20% com mais de mil
linhas mortas vira atenção; acima de 40%, crítico.

Tupla morta é espaço que o `UPDATE` e o `DELETE` deixaram para trás. Até o
`VACUUM` passar, ela continua sendo lida em toda varredura -- a tabela
ocupa mais disco e fica mais lenta sem ter crescido.

Proporção alta com autovacuum ligado quase sempre significa uma de duas
coisas: o autovacuum não está dando conta do volume de escrita, ou há uma
transação antiga aberta segurando o horizonte de limpeza. A checagem de
transações longas, logo abaixo, costuma responder qual das duas.

**Não pega.** Bloat de verdade, que inclui espaço fragmentado dentro das
páginas. A medição exata exige `pgstattuple`, que varre a tabela inteira --
caro demais para coleta rotineira. O número aqui é indicador, não conta.

### Tabelas sem vacuum recente

Tabelas com mais de mil linhas que nunca passaram por vacuum ou por
analyze. Nunca ter passado por `ANALYZE` é crítico; só faltar o `VACUUM` é
atenção.

Sem `ANALYZE`, o planejador trabalha com estatísticas inexistentes ou
velhas e escolhe planos ruins com confiança total. É das causas mais comuns
de "a consulta ficou lenta do nada".

A diferença de gravidade é proposital: falta de `VACUUM` incomoda o espaço
em disco, falta de `ANALYZE` quebra o plano de execução -- e plano ruim
aparece para o usuário na mesma hora.

**Não pega.** Tabela com vacuum antigo mas existente. O critério é
binário (passou ou não passou) porque "recente" depende demais do padrão de
escrita de cada tabela para ter um limite único que valha para todas.

### Distância do wraparound de transações

`age(datfrozenxid)` contra `autovacuum_freeze_max_age`. Acima de 50% vira
atenção; acima de 80%, crítico.

O contador de transações do PostgreSQL é circular. Se o `VACUUM` não
congelar as tuplas antigas a tempo, o banco entra em modo somente leitura
para não corromper dados.

É raro, e quando acontece costuma ser em instância com autovacuum desligado
ou sufocado. A saída é uma janela de manutenção longa, sempre em hora ruim
-- daí valer a pena vigiar mesmo sendo improvável.

**Não pega.** Wraparound no nível da tabela individual, que chega antes do
nível do banco. A checagem por tabela usaria
`pg_class.relfrozenxid` e seria o próximo passo natural.

## atividade

### Transações abertas há muito tempo

Sessões com `xact_start` há mais de cinco minutos. Acima de trinta minutos
vira crítico.

Transação antiga segura o horizonte de limpeza: enquanto ela existe, o
`VACUUM` não consegue remover nenhuma tupla morta criada depois que ela
começou. Uma sessão esquecida em `idle in transaction` é capaz de fazer o
banco inteiro inchar sem que nada apareça nos logs.

O limite de cinco minutos é curto de propósito. Em OLTP, transação que
passa disso quase sempre é bug -- conexão devolvida ao pool sem commit, ou
código que abriu transação antes de uma chamada externa lenta.

**Não pega.** Transação legítima e longa: migração, carga em lote,
`REINDEX`. Elas aparecem aqui e precisam ser reconhecidas por quem lê.

### Sessões esperando bloqueio

`pg_blocking_pids` devolve direto quem está segurando o lock. Qualquer
espera é reportada; acima de um minuto vira crítico.

Sem essa função, descobrir o culpado exige cruzar `pg_locks` com
`pg_stat_activity` na mão -- o caminho que a maioria dos tutoriais antigos
ainda ensina, e que é fácil de errar quando há mais de um nível de espera.

**Não pega.** Contenção que já passou. É uma foto do instante: um lock que
travou o sistema por trinta segundos meia hora atrás não deixa rastro aqui.
Para isso serviria `log_lock_waits` nos logs do servidor.

### Uso de conexões

Conexões abertas contra o `max_connections`, mais a contagem de sessões em
`idle in transaction`. Acima de 70% do máximo vira atenção; acima de 85%,
crítico. Qualquer sessão ociosa em transação já reporta.

Sessão em `idle in transaction` é pior do que conexão ociosa comum: ocupa um
slot e ainda segura o horizonte de limpeza do `VACUUM`. Costuma ser
aplicação que abriu transação e esqueceu de fechar, ou pool mal configurado
que devolve a conexão sem dar commit.

O limite de 70% existe porque as conexões reservadas
(`superuser_reserved_connections`) e um pico de tráfego consomem a folga
rápido. Chegar a 100% significa aplicação sem conseguir conectar, o que
aparece como indisponibilidade total.

## capacidade

### Sequências próximas do limite

Percentual consumido do intervalo do tipo. Acima de 70% vira atenção; acima
de 90%, crítico.

O caso clássico é a coluna `integer` com sequência: o limite é pouco mais de
dois bilhões, e uma tabela com muita inserção chega lá. Quando chega, a
aplicação para de gravar de uma vez -- e migrar para `bigint` numa tabela
grande, sob pressão, não é uma tarde agradável.

Vale olhar esta checagem com folga de meses, não de dias. A correção é uma
migração de tipo, e migração de tipo em tabela grande precisa de
planejamento.

**Não pega.** A velocidade de consumo. Uma sequência em 72% que cresce
devagar tem anos pela frente; outra em 72% crescendo rápido tem semanas. A
checagem mostra a posição, não a trajetória.

### Maiores tabelas

Informativa: nunca gera alerta. As dez maiores tabelas, com a proporção
ocupada por índices.

A relação entre tamanho de índice e tamanho de tabela é um sinal útil:
índices ocupando mais espaço que a própria tabela costuma indicar indexação
excessiva, e combina bem com o que a checagem de índices não usados aponta.

## modelagem

### Tabelas sem chave primária

Tabelas de usuário com mais de mil linhas e sem `PRIMARY KEY`. Acima de cem
mil linhas vira atenção; abaixo fica informativo.

Sem chave primária não há como identificar uma linha específica, o que
inviabiliza correção pontual, deduplicação e replicação lógica -- esta
última simplesmente se recusa a replicar `UPDATE` e `DELETE` em tabela sem
identidade.

Tabela de log e de staging costumam aparecer aqui, e nesses casos a ausência
pode ser deliberada. A checagem aponta; a decisão é de quem conhece o
modelo.

## Um detalhe que custou uma execução inteira

As estatísticas de atividade (`pg_stat_user_tables`, `pg_stat_user_indexes`)
vivem num arquivo próprio e **se perdem num encerramento abrupto** do
servidor. Depois de um crash, `n_dead_tup` volta a zero, `last_analyze`
some e `n_live_tup` zera.

Isso aconteceu no meio do desenvolvimento, quando o Docker caiu: o
diagnóstico passou de duas checagens críticas para nenhuma, sem que nada no
banco tivesse melhorado.

Duas consequências práticas:

- **Um diagnóstico logo após um restart não vale nada.** Tudo aparece
  saudável porque não há histórico acumulado. Confira
  `pg_stat_database.stats_reset` antes de tirar conclusões.
- **Checagem estrutural não deve depender de estatística de atividade.** A
  de tabelas sem chave primária dependia de `n_live_tup` e parava de acusar
  qualquer coisa depois de um crash -- justamente quando alguém vai olhar
  para o banco. Hoje ela usa `pg_class.reltuples`, que fica no catálogo e
  sobrevive.

A distinção vale como regra geral: o que é estrutura (existe chave? existe
índice? qual o tamanho?) vem do catálogo; o que é comportamento (quantas
leituras? quantas tuplas mortas?) vem das estatísticas, e estatística e
volátil.

## Sobre as gravidades

Três níveis, e a diferença entre eles é o que se espera de quem lê:

| Gravidade | Significado |
|-----------|-------------|
| `critico` | alguém precisa olhar hoje |
| `atencao` | entra na fila, não é urgente |
| `informativo` | contexto; não é para agir |

A gravidade é decidida dentro do SQL de cada checagem, não no Python. Quem
escreve a consulta é quem sabe o que significa aquele valor naquele
contexto, e manter as duas coisas no mesmo arquivo evita a regra de
severidade ficar longe da medição que ela interpreta.

Uma checagem herda a pior gravidade entre os seus achados. Uma tabela
crítica entre quatro em atenção faz a checagem inteira aparecer como
crítica -- que é o comportamento certo para uma lista que se lê de cima
para baixo.
