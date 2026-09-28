-- título: Índices redundantes
-- categoria: índices
-- descrição: Índices cujo conjunto de colunas e prefixo de outro índice da mesma tabela.
-- limite: Qualquer ocorrência.
--
-- Um índice em (a) e redundante quando já existe um em (a, b): o segundo
-- atende tudo que o primeiro atenderia. Manter os dois paga o custo de
-- escrita duas vezes sem ganho nenhum de leitura.

WITH indices AS (
    SELECT
        x.indrelid::regclass::text AS tabela,
        i.relname                  AS nome,
        x.indexrelid,
        array_to_string(x.indkey, ' ') AS colunas,
        pg_relation_size(x.indexrelid) AS tamanho
    FROM pg_index x
    JOIN pg_class i ON i.oid = x.indexrelid
    JOIN pg_class t ON t.oid = x.indrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND NOT x.indisprimary
)
SELECT
    a.tabela || ': ' || a.nome                           AS objeto,
    'coberto por ' || b.nome
        || ' (libera ' || pg_size_pretty(a.tamanho) || ')' AS detalhe,
    'atencao'                                            AS gravidade
FROM indices a
JOIN indices b
  ON a.tabela = b.tabela
 AND a.indexrelid <> b.indexrelid
 AND b.colunas LIKE a.colunas || ' %'
ORDER BY a.tamanho DESC;
