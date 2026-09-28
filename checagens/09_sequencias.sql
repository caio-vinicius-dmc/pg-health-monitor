-- título: Sequências próximas do limite
-- categoria: capacidade
-- descrição: Sequências que já consumiram boa parte do intervalo do tipo.
-- limite: Acima de 70% do máximo; acima de 90% vira crítico.
--
-- O caso clássico e a coluna integer com sequência: o limite e pouco mais
-- de dois bilhões, e uma tabela com muita inserção chega lá. Quando chega,
-- a aplicação para de gravar de uma vez -- e migrar para bigint numa
-- tabela grande, sob pressão, não é uma tarde agradável.
--
-- Vale olhar esta checagem com folga de meses, não de dias.

SELECT
    schemaname || '.' || sequencename                          AS objeto,
    'em ' || coalesce(last_value, 0) || ' de ' || max_value
        || ' (' || round(100.0 * coalesce(last_value, 0) / max_value, 2) || '%)' AS detalhe,
    CASE
        WHEN 100.0 * coalesce(last_value, 0) / max_value > 90 THEN 'critico'
        ELSE 'atencao'
    END                                                        AS gravidade
FROM pg_sequences
WHERE 100.0 * coalesce(last_value, 0) / max_value > 70
ORDER BY coalesce(last_value, 0)::numeric / max_value DESC;
