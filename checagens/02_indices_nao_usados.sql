-- título: Índices que nunca foram usados
-- categoria: índices
-- descrição: Índices sem nenhuma leitura desde o último reset das estatísticas.
-- limite: Qualquer índice acima de 1 MB sem uso.
--
-- Índice sem uso custa duas vezes: ocupa disco e torna todo INSERT, UPDATE
-- e DELETE da tabela mais lento, porque precisa ser mantido em dia.
--
-- Cuidado antes de apagar: índice que atende um relatório mensal aparece
-- aqui em qualquer coleta feita no dia 2. Confira o tempo desde o último
-- reset das estatísticas antes de concluir qualquer coisa.

SELECT
    i.schemaname || '.' || i.indexrelname                      AS objeto,
    pg_size_pretty(pg_relation_size(i.indexrelid))
        || ' na tabela ' || i.relname
        || ' (' || i.idx_scan || ' leituras)'                   AS detalhe,
    CASE
        WHEN pg_relation_size(i.indexrelid) > 50 * 1024 * 1024 THEN 'atencao'
        ELSE 'informativo'
    END                                                         AS gravidade
FROM pg_stat_user_indexes i
JOIN pg_index x ON x.indexrelid = i.indexrelid
WHERE i.idx_scan = 0
  AND NOT x.indisunique      -- índice único existe para garantir a regra, não para ler
  AND NOT x.indisprimary
  AND pg_relation_size(i.indexrelid) > 1024 * 1024
ORDER BY pg_relation_size(i.indexrelid) DESC;
