-- título: Distância do wraparound de transações
-- categoria: manutenção
-- descrição: Idade do xid mais antigo em relação ao limite de congelamento.
-- limite: Acima de 50% do autovacuum_freeze_max_age; acima de 80% vira crítico.
--
-- O contador de transações do Postgres e circular. Se o VACUUM não
-- congelar as tuplas antigas a tempo, o banco entra em modo somente
-- leitura para não corromper dados.
--
-- E raro, mas quando acontece costuma ser em instância com autovacuum
-- desligado ou sufocado -- e a saída e uma janela de manutenção longa,
-- sempre em hora ruim.

SELECT
    'banco ' || datname                                        AS objeto,
    'idade do xid: ' || age(datfrozenxid)
        || ' de ' || current_setting('autovacuum_freeze_max_age')
        || ' (' || round(100.0 * age(datfrozenxid)
            / current_setting('autovacuum_freeze_max_age')::bigint, 1) || '%)' AS detalhe,
    CASE
        WHEN age(datfrozenxid)
             > current_setting('autovacuum_freeze_max_age')::bigint * 0.8
            THEN 'critico'
        ELSE 'atencao'
    END                                                        AS gravidade
FROM pg_database
WHERE datname = current_database()
  AND age(datfrozenxid)
      > current_setting('autovacuum_freeze_max_age')::bigint * 0.5;
