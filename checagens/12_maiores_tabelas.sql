-- título: Maiores tabelas
-- categoria: capacidade
-- descrição: As dez maiores tabelas, com a proporção ocupada por índices.
-- limite: Informativo. Não gera alerta; serve de contexto para as demais checagens.
--
-- A relação entre tamanho de índice e tamanho de tabela e um sinal útil:
-- índices ocupando mais espaço que a própria tabela costuma indicar
-- indexação excessiva, e combina bem com o que a checagem de índices não
-- usados aponta.

SELECT
    schemaname || '.' || relname                               AS objeto,
    pg_size_pretty(pg_total_relation_size(relid)) || ' no total, '
        || pg_size_pretty(pg_indexes_size(relid)) || ' de índices ('
        || round(100.0 * pg_indexes_size(relid)
            / nullif(pg_total_relation_size(relid), 0), 0) || '%), '
        || coalesce(n_live_tup, 0) || ' linhas'                AS detalhe,
    'informativo'                                              AS gravidade
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
