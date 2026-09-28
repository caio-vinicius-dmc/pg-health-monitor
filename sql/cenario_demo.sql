-- Cenário de demonstração: uma base com problemas plantados.
--
-- Cada bloco abaixo existe para uma checagem ter o que encontrar. Numa
-- base real não é preciso rodar nada disso -- o monitor aponta para
-- qualquer PostgreSQL alcançável.
--
-- O container de demonstração sobe com autovacuum desligado, que é o que
-- permite acumular tuplas mortas. Não faça isso em produção.

SELECT setseed(0.63);

DROP TABLE IF EXISTS app.evento CASCADE;
DROP TABLE IF EXISTS app.item_pedido CASCADE;
DROP TABLE IF EXISTS app.pedido CASCADE;
DROP TABLE IF EXISTS app.cliente CASCADE;
DROP SCHEMA IF EXISTS app CASCADE;

CREATE SCHEMA app;

-- ---------------------------------------------------------------------------
-- Tabelas normais
-- ---------------------------------------------------------------------------
CREATE TABLE app.cliente (
    id       integer PRIMARY KEY,
    nome     text    NOT NULL,
    email    text    NOT NULL,
    cidade   text    NOT NULL,
    uf       char(2) NOT NULL,
    segmento text    NOT NULL
);

-- Sequência declarada como integer de propósito: é o caso que a checagem
-- de capacidade existe para pegar antes de virar incidente.
CREATE SEQUENCE app.pedido_id_seq AS integer;

CREATE TABLE app.pedido (
    id          integer PRIMARY KEY DEFAULT nextval('app.pedido_id_seq'),
    cliente_id  integer       NOT NULL REFERENCES app.cliente (id),
    criado_em   timestamptz   NOT NULL,
    status      text          NOT NULL,
    valor_total numeric(12,2) NOT NULL
);

CREATE TABLE app.item_pedido (
    id             bigserial PRIMARY KEY,
    pedido_id      integer       NOT NULL REFERENCES app.pedido (id),
    produto        text          NOT NULL,
    quantidade     smallint      NOT NULL,
    preco_unitario numeric(10,2) NOT NULL
);

-- ---------------------------------------------------------------------------
-- Problema 1: tabela de log sem chave primária
-- ---------------------------------------------------------------------------
CREATE TABLE app.evento (
    ocorrido_em timestamptz NOT NULL,
    tipo        text        NOT NULL,
    origem      text        NOT NULL,
    payload     text
);

-- ---------------------------------------------------------------------------
-- Problema 2: índices redundantes e índices sem uso
-- ---------------------------------------------------------------------------
-- idx_pedido_cliente e prefixo de idx_pedido_cliente_data: o segundo
-- atende tudo que o primeiro atenderia.
CREATE INDEX idx_pedido_cliente      ON app.pedido (cliente_id);
CREATE INDEX idx_pedido_cliente_data ON app.pedido (cliente_id, criado_em);

-- Estes três nunca serão lidos pela carga de demonstração.
CREATE INDEX idx_pedido_status       ON app.pedido (status);
CREATE INDEX idx_pedido_valor        ON app.pedido (valor_total);
CREATE INDEX idx_item_produto        ON app.item_pedido (produto);
CREATE INDEX idx_evento_tipo         ON app.evento (tipo);

-- ---------------------------------------------------------------------------
-- Massa
-- ---------------------------------------------------------------------------
INSERT INTO app.cliente (id, nome, email, cidade, uf, segmento)
SELECT
    g,
    'Cliente ' || g,
    'cliente' || g || '@exemplo.invalido',
    (ARRAY['Sao Paulo','Campinas','Rio de Janeiro','Belo Horizonte','Curitiba',
           'Porto Alegre','Salvador','Recife','Fortaleza','Goiania'])[1 + (g % 10)],
    (ARRAY['SP','SP','RJ','MG','PR','RS','BA','PE','CE','GO'])[1 + (g % 10)],
    CASE WHEN random() < 0.75 THEN 'Varejo' ELSE 'Corporativo' END
FROM generate_series(1, 20000) AS g;

-- A sequência começa alta para a checagem de capacidade ter o que apontar.
-- Numa base real isso seria resultado de anos de inserção.
SELECT setval('app.pedido_id_seq', 1700000000);

INSERT INTO app.pedido (cliente_id, criado_em, status, valor_total)
SELECT
    1 + (random() * 19999)::int,
    TIMESTAMPTZ '2025-01-01' + (random() * 600)::int * INTERVAL '1 day',
    CASE WHEN random() < 0.05 THEN 'cancelado' ELSE 'faturado' END,
    round((random() * 900 + 30)::numeric, 2)
FROM generate_series(1, 120000) AS g;

INSERT INTO app.item_pedido (pedido_id, produto, quantidade, preco_unitario)
SELECT p.id,
       'Produto ' || (1 + (p.id % 400)),
       1 + (p.id % 4),
       round((random() * 400 + 20)::numeric, 2)
FROM app.pedido p;

INSERT INTO app.evento (ocorrido_em, tipo, origem, payload)
SELECT
    TIMESTAMPTZ '2025-06-01' + (random() * 300)::int * INTERVAL '1 day',
    (ARRAY['login','compra','erro','cadastro'])[1 + (random() * 3)::int],
    (ARRAY['web','app','api'])[1 + (random() * 2)::int],
    repeat('x', 60)
FROM generate_series(1, 80000) AS g;

-- ---------------------------------------------------------------------------
-- Problema 3: tuplas mortas
-- ---------------------------------------------------------------------------
-- Com autovacuum desligado, estes UPDATE e DELETE deixam para trás a
-- versão antiga de cada linha. E o que a checagem de manutenção mede.
UPDATE app.pedido SET valor_total = valor_total * 1.02 WHERE id % 2 = 0;
UPDATE app.pedido SET status = 'revisado'              WHERE id % 5 = 0;
DELETE FROM app.evento WHERE ocorrido_em < TIMESTAMPTZ '2025-08-01';

-- ANALYZE sem VACUUM de propósito: atualiza as estatísticas do planejador
-- sem limpar as tuplas mortas, que é o estado que se quer demonstrar.
ANALYZE app.cliente;
ANALYZE app.pedido;
ANALYZE app.item_pedido;
