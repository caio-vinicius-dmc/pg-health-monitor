-- título: Tabelas sem vacuum recente
-- categoria: manutenção
-- descrição: Tabelas com escrita que nunca passaram por vacuum ou analyze.
-- limite: Nenhum vacuum e nenhum analyze registrado, com mais de mil linhas.
--
-- Sem ANALYZE o planejador trabalha com estatísticas desatualizadas ou
-- inexistentes, e escolhe planos ruins com confiança total. E uma das
-- causas mais comuns de "a consulta ficou lenta do nada".

SELECT
    schemaname || '.' || relname                          AS objeto,
    coalesce(
        'último vacuum: ' || to_char(greatest(last_vacuum, last_autovacuum), 'DD/MM/YYYY'),
        'nunca passou por vacuum'
    ) || ' | ' || coalesce(
        'último analyze: ' || to_char(greatest(last_analyze, last_autoanalyze), 'DD/MM/YYYY'),
        'nunca passou por analyze'
    )                                                     AS detalhe,
    CASE
        WHEN greatest(last_analyze, last_autoanalyze) IS NULL THEN 'critico'
        ELSE 'atencao'
    END                                                   AS gravidade
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
  AND (
        greatest(last_vacuum, last_autovacuum) IS NULL
     OR greatest(last_analyze, last_autoanalyze) IS NULL
  )
ORDER BY n_live_tup DESC;
