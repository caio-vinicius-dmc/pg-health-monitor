-- título: Transações abertas há muito tempo
-- categoria: atividade
-- descrição: Sessões com transação aberta há mais de cinco minutos.
-- limite: Acima de 5 minutos vira atenção; acima de 30 minutos, crítico.
--
-- Transação antiga segura o horizonte de limpeza: enquanto ela existe, o
-- VACUUM não consegue remover nenhuma tupla morta criada depois que ela
-- começou. Uma sessão esquecida em "idle in transaction" e capaz de fazer
-- o banco inteiro inchar sem que nada apareca nos logs.

SELECT
    'pid ' || pid || ' ('
        || coalesce(usename, '?') || '@'
        || coalesce(nullif(application_name, ''), 'sem nome') || ')'     AS objeto,
    state || ' ha ' || to_char(now() - xact_start, 'HH24:MI:SS')
        || ' | ' || left(regexp_replace(coalesce(query, ''), '\s+', ' ', 'g'), 80) AS detalhe,
    CASE
        WHEN now() - xact_start > interval '30 minutes' THEN 'critico'
        ELSE 'atencao'
    END                                                                  AS gravidade
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND now() - xact_start > interval '5 minutes'
  AND pid <> pg_backend_pid()
  AND backend_type = 'client backend'
ORDER BY xact_start;
