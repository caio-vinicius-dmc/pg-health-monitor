-- título: Uso de conexões
-- categoria: atividade
-- descrição: Conexões abertas em relação ao max_connections, e ociosas em transação.
-- limite: Acima de 70% do máximo, ou qualquer sessão ociosa em transação.
--
-- Sessão em "idle in transaction" é pior do que conexão ociosa comum: ela
-- ocupa um slot e ainda segura o horizonte de limpeza do VACUUM. Costuma
-- ser aplicação que abriu transação e esqueceu de fechar -- ou um pool mal
-- configurado que devolve a conexão sem dar commit.

WITH uso AS (
    SELECT
        count(*)                                                  AS abertas,
        count(*) FILTER (WHERE state = 'idle in transaction')      AS ociosas_em_transacao,
        current_setting('max_connections')::int                    AS maximo
    FROM pg_stat_activity
    WHERE backend_type = 'client backend'
)
SELECT
    'conexões'                                                     AS objeto,
    abertas || ' de ' || maximo
        || ' (' || round(100.0 * abertas / maximo, 1) || '%), '
        || ociosas_em_transacao || ' ociosas em transação'          AS detalhe,
    CASE
        WHEN 100.0 * abertas / maximo > 85 THEN 'critico'
        ELSE 'atencao'
    END                                                            AS gravidade
FROM uso
WHERE 100.0 * abertas / maximo > 70
   OR ociosas_em_transacao > 0;
