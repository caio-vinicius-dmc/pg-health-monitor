-- título: Sessões esperando bloqueio
-- categoria: atividade
-- descrição: Consultas paradas esperando um lock que outra sessão segura.
-- limite: Qualquer espera; acima de um minuto vira crítico.
--
-- pg_blocking_pids devolve direto quem está segurando o bloqueio. Sem essa
-- função, descobrir o culpado exige cruzar pg_locks com pg_stat_activity
-- na mão -- o caminho que a maioria dos tutoriais antigos ainda ensina, e
-- que é facil de errar quando há mais de um nível de espera.

SELECT
    'pid ' || a.pid || ' bloqueado por '
        || array_to_string(pg_blocking_pids(a.pid), ', ')                 AS objeto,
    'esperando ha ' || to_char(now() - a.state_change, 'HH24:MI:SS')
        || ' | ' || left(regexp_replace(coalesce(a.query, ''), '\s+', ' ', 'g'), 80) AS detalhe,
    CASE
        WHEN now() - a.state_change > interval '1 minute' THEN 'critico'
        ELSE 'atencao'
    END                                                                   AS gravidade
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
ORDER BY a.state_change;
