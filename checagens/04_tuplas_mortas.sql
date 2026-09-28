-- título: Tabelas com muitas tuplas mortas
-- categoria: manutenção
-- descrição: Proporção de linhas mortas em relação as vivas.
-- limite: Acima de 20% com mais de mil linhas mortas.
--
-- Tupla morta e espaço que o UPDATE e o DELETE deixaram para trás. Até o
-- VACUUM passar, ela continua sendo lida em toda varredura -- a tabela
-- ocupa mais disco e fica mais lenta sem ter crescido.
--
-- Proporção alta com autovacuum ligado quase sempre significa uma das
-- duas coisas: o autovacuum não está dando conta do volume de escrita, ou
-- há uma transação antiga aberta segurando o horizonte de limpeza.

SELECT
    schemaname || '.' || relname                                   AS objeto,
    n_dead_tup || ' mortas de ' || (n_live_tup + n_dead_tup) || ' linhas ('
        || round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) || '%), '
        || pg_size_pretty(pg_total_relation_size(relid)) || ' no total'   AS detalhe,
    CASE
        WHEN 100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0) > 40 THEN 'critico'
        ELSE 'atencao'
    END                                                            AS gravidade
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
  AND 100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0) > 20
ORDER BY n_dead_tup DESC;
