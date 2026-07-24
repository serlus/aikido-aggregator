-- db/schema.sql — Fase 1: fundação de dados (ver ARCHITECTURE.md §4)
-- Aplicado de forma idempotente por scraper/db.py a cada conexão.

CREATE TABLE IF NOT EXISTS sources (
  id       TEXT PRIMARY KEY,
  name     TEXT,
  url      TEXT,
  country  TEXT,
  lineage  TEXT,
  engine   TEXT,
  cadence  TEXT,
  priority INTEGER,
  robots   TEXT,                    -- allowed | disallowed | pending
  active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fetches (        -- toda tentativa de coleta
  id            INTEGER PRIMARY KEY,
  source_id     TEXT REFERENCES sources(id),
  fetched_at    TEXT,                       -- UTC ISO-8601
  endpoint      TEXT,                       -- URL efetivamente buscada (wp-json/feed ≠ homepage)
  http_status   INTEGER,
  latency_ms    INTEGER,
  content_hash  TEXT,                       -- hash do texto visível (estável)
  etag          TEXT,                       -- p/ If-None-Match no próximo fetch
  last_modified TEXT,                       -- p/ If-Modified-Since no próximo fetch
  raw_path      TEXT,                       -- relativo à raiz do repo; NULL se sem mudança
  changed       INTEGER,                    -- NULL baseline · 0 igual · 1 mudou
  error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetches_source ON fetches(source_id, fetched_at);

CREATE TABLE IF NOT EXISTS items (          -- unidade normalizada (notícia/post/página)
  id            INTEGER PRIMARY KEY,
  source_id     TEXT REFERENCES sources(id),
  url           TEXT UNIQUE,                -- link canônico na fonte (chave de dedupe)
  external_id   TEXT,                       -- id na fonte (ex.: post id do WP, guid do RSS)
  type          TEXT,                       -- news | event | seminar | page
  title         TEXT,
  summary       TEXT,                       -- resumo curto original (entrada da tradução)
  title_pt      TEXT,
  summary_pt    TEXT,
  lang          TEXT,
  published_at  TEXT,                       -- UTC ISO-8601
  updated_at    TEXT,                       -- última modificação na fonte (UTC)
  discovered_at TEXT,
  content_hash  TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_id, published_at);

CREATE TABLE IF NOT EXISTS events (         -- extensão de items tipo event/seminar
  item_id    INTEGER PRIMARY KEY REFERENCES items(id),
  starts_at  TEXT,
  ends_at    TEXT,
  tz         TEXT,                          -- ex.: Asia/Tokyo, Europe/Paris (agenda exibe em America/Sao_Paulo)
  city       TEXT,
  country    TEXT,
  online     INTEGER DEFAULT 0,
  instructor TEXT,
  lineage    TEXT,
  org_id     TEXT REFERENCES orgs(id),
  region     TEXT                            -- sul_br | brasil | america_sul | europa | japao | outro (Fase 3, filtro local/remoto)
);
CREATE INDEX IF NOT EXISTS idx_events_starts ON events(starts_at);

CREATE TABLE IF NOT EXISTS orgs (           -- diretório: federações e dojos
  id        TEXT PRIMARY KEY,
  name      TEXT,
  kind      TEXT,                           -- federation | dojo | dojo_hq
  country   TEXT,
  state     TEXT,
  city      TEXT,
  lineage   TEXT REFERENCES lineages(id),
  parent_id TEXT REFERENCES orgs(id),
  url       TEXT,
  contact   TEXT,
  notes     TEXT
);

CREATE TABLE IF NOT EXISTS lineages (
  id        TEXT PRIMARY KEY,
  name      TEXT,
  founder   TEXT,
  parent_id TEXT REFERENCES lineages(id),
  notes     TEXT
);

CREATE TABLE IF NOT EXISTS translations_cache (
  content_hash TEXT PRIMARY KEY,
  src_lang     TEXT,
  text_pt      TEXT,
  created_at   TEXT
);
