-- título: Tabelas sem chave primária
-- categoria: modelagem
-- descrição: Tabelas de usuário sem PRIMARY KEY declarada.
-- limite: Qualquer tabela com mais de mil linhas estimadas.
--
-- Sem chave primária não há como identificar uma linha específica, o que
-- inviabiliza correção pontual, deduplicação e replicação lógica -- esta
-- última simplesmente se recusa a replicar UPDATE e DELETE em tabela sem
-- identidade.
--
-- Tabela de log e de staging costumam aparecer aqui, e nesses casos a
-- ausência pode ser deliberada. A checagem aponta; a decisão e de quem
-- conhece o modelo.
--
-- A contagem vem de pg_class.reltuples, e não de pg_stat_user_tables.
-- Parece detalhe e não é: as estatísticas de atividade vivem em arquivo
-- próprio e se perdem num encerramento abrupto do servidor, enquanto
-- reltuples fica no catálogo e sobrevive. Usando a fonte volátil, esta
-- checagem parava de acusar qualquer coisa depois de um crash -- que é
-- justamente quando alguém vai olhar para o banco.

SELECT
    n.nspname || '.' || c.relname                              AS objeto,
    CASE
        WHEN c.reltuples < 0 THEN 'sem estimativa (nunca passou por analyze)'
        ELSE round(c.reltuples)::bigint || ' linhas estimadas'
    END || ', ' || pg_size_pretty(pg_total_relation_size(c.oid)) AS detalhe,
    CASE
        WHEN c.reltuples > 100000 THEN 'atencao'
        ELSE 'informativo'
    END                                                        AS gravidade
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND NOT EXISTS (
      SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary
  )
  -- reltuples vale -1 quando a tabela nunca passou por analyze. Nesse caso
  -- o tamanho em disco serve de critério: acima de 1 MB já vale reportar.
  AND (c.reltuples > 1000 OR (c.reltuples < 0 AND pg_total_relation_size(c.oid) > 1024 * 1024))
ORDER BY c.reltuples DESC;
