-- título: Taxa de acerto de cache
-- categoria: memória
-- descrição: Proporção de blocos servidos pela memória em vez do disco.
-- limite: Abaixo de 95% costuma indicar shared_buffers pequeno para o volume de leitura.
--
-- A taxa e calculada desde o último reset das estatísticas, então logo
-- depois de um restart ela e baixa por natureza e não significa nada.
-- A linha só aparece quando há volume suficiente para o número ter sentido.

SELECT
    'banco ' || d.datname                                AS objeto,
    round(100.0 * d.blks_hit / nullif(d.blks_hit + d.blks_read, 0), 2) || '% de acerto '
        || '(' || pg_size_pretty((d.blks_read * 8192)::bigint) || ' lidos do disco)' AS detalhe,
    CASE
        WHEN 100.0 * d.blks_hit / nullif(d.blks_hit + d.blks_read, 0) < 90 THEN 'critico'
        ELSE 'atencao'
    END                                                  AS gravidade
FROM pg_stat_database d
WHERE d.datname = current_database()
  AND d.blks_hit + d.blks_read > 100000
  AND 100.0 * d.blks_hit / nullif(d.blks_hit + d.blks_read, 0) < 95;
