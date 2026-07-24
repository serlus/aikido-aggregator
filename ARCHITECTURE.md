# ARCHITECTURE.md — Agregador de Aikido

**Princípios:** custo ~zero · raw-first (sempre reprocessável) · um parser
por fonte, isolado e testável · scheduler simples primeiro (GitHub Actions),
K8s só se necessário.

---

## 1. Visão geral

```
                     ┌─────────────────────────────────────────┐
                     │        GitHub Actions (cron)            │
                     │  daily.yml / weekly.yml / monthly.yml   │
                     └───────────────┬─────────────────────────┘
                                     ▼
┌──────────┐   ┌──────────────────────────────────────────────┐
│sources.yml│──▶│                 FETCHER                      │
│ (catálogo)│   │ rate-limit/domínio · retry · UA identificado │
└──────────┘   │ robots.txt check · UTF-8 (incl. Shift-JIS)   │
               └──────────┬───────────────────────────────────┘
                          ▼
               ┌──────────────────┐     hash igual? ──▶ fim (log only)
               │  RAW STORE       │
               │ raw/{src}/{date}/│──── hash novo
               │   {hash}.html    │        │
               └──────────────────┘        ▼
               ┌──────────────────────────────────┐
               │        PARSERS (1 por fonte)     │
               │  parsers/aikikai_jp.py           │
               │  parsers/ffaaa_fr.py  ...        │
               └──────────┬───────────────────────┘
                          ▼
               ┌──────────────────────────────────┐
               │  ENRICHER                        │
               │  tradução JA/FR/ES→PT (cacheada) │
               │  classificação type/lineage      │
               │  normalização de datas/locais    │
               └──────────┬───────────────────────┘
                          ▼
               ┌──────────────────┐    ┌───────────────────────┐
               │  SQLite (repo)   │───▶│  SITE BUILD (Astro)   │
               │  db/aikido.db    │    │  agenda·notícias·     │
               └──────────────────┘    │  diretório·status     │
                                       └──────────┬────────────┘
                                                  ▼
                                       GitHub/Cloudflare Pages
```

Fluxo disparado por cron; cada run termina com commit do DB atualizado e
rebuild do site. Tudo dentro de um monorepo.

## 2. Estrutura do repositório

```
aikido-aggregator/
├── sources.yml              # catálogo de fontes (ver §3)
├── blocklist.yml            # fontes proibidas (aikikai.com.br)
├── scraper/
│   ├── fetcher.py           # HTTP client compartilhado
│   ├── probe.py             # Fase 0: hash-only
│   ├── parsers/
│   │   ├── base.py          # interface: parse(raw) -> list[Item]
│   │   ├── wp_json.py       # genérico p/ WordPress REST
│   │   ├── aikikai_jp.py
│   │   ├── ffaaa_fr.py
│   │   └── ...
│   ├── enricher/
│   │   ├── translate.py     # cache por content-hash
│   │   └── classify.py
│   └── tests/
│       └── fixtures/        # HTML real congelado p/ testes
├── db/
│   ├── schema.sql
│   └── aikido.db            # SQLite commitado (v1)
├── raw/                     # ou bucket externo se crescer
├── site/                    # Astro
│   └── src/pages/{agenda,noticias,diretorio,status}
├── reports/
│   └── frequency-report.md  # gerado pela Fase 0
└── .github/workflows/
    ├── probe-daily.yml
    ├── scrape-{daily,weekly,monthly}.yml
    └── site-deploy.yml
```

## 3. Catálogo de fontes (`sources.yml`)

Formato:

```yaml
- id: aikikai_jp
  name: Aikikai Foundation (Hombu Dojo)
  url: https://www.aikikai.or.jp/eng/
  country: JP
  lang: [ja, en]
  lineage: aikikai
  engine: http          # http | headless | wp_json | rss
  cadence: weekly       # provisório — Fase 0 decide
  encoding: auto        # auto-detect; forçar shift_jis se preciso
  robots: pending       # allowed | disallowed | pending
  priority: 1           # 1 = Tier 1
```

### Fontes iniciais

| id | País | Engine (hipótese) | Cadência provisória | Tier |
|---|---|---|---|---|
| aikikai_jp (Hombu) | JP | http | weekly | 1 ⭐ |
| iwama_shinshin | JP | http/rss | weekly | 1 |
| kumano_juku_fb | JP | manual (API FB restrita) | monthly | 2 |
| yoshinkan_jp | JP | http | monthly | 2 |
| ffaaa_fr | FR | http | weekly | 1 ⭐ |
| cercle_tissier | FR | http | weekly | 1 ⭐ |
| aikido_parana | BR | wp_json | weekly | 1 |
| shoyukan_br | BR | wp_json | biweekly | 1 |
| acai_sc | BR | wp_json? (verificar) | biweekly | 1 |
| daisho_criciuma | BR | http | monthly | 2 |
| febrai | BR | http (PHP legado) | monthly | 2 |
| fepai | BR | http | monthly | 2 |
| minas_aikido | BR | **headless** | monthly | 2 |
| aikidoba | BR | http | monthly | 3 |
| fedenachaa_cl | CL | http | monthly | 3 |
| circulo_aikikai_ar | AR | http | monthly | 3 |
| ame_no_iwaya_rs | BR | http | monthly | 2 |

Blocklist: `aikikai.com.br` (redirecionamento p/ phishing detectado em 2026-07).
`aikidobr.com.br` e `mapaosc.ipea.gov.br`: robots.txt disallow → não scrapear;
uso manual apenas.

## 4. Modelo de dados (`schema.sql`)

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY, name TEXT, url TEXT, country TEXT,
  lineage TEXT, engine TEXT, cadence TEXT, priority INT,
  robots TEXT, active INT DEFAULT 1
);

CREATE TABLE fetches (            -- toda tentativa de coleta
  id INTEGER PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  fetched_at TEXT, http_status INT, latency_ms INT,
  content_hash TEXT, raw_path TEXT, changed INT
);

CREATE TABLE items (              -- unidade normalizada (notícia/post)
  id INTEGER PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  url TEXT UNIQUE, type TEXT,     -- news | event | seminar | page
  title TEXT, title_pt TEXT, summary_pt TEXT,
  lang TEXT, published_at TEXT, discovered_at TEXT,
  content_hash TEXT
);

CREATE TABLE events (             -- extensão de items tipo event/seminar
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  starts_at TEXT, ends_at TEXT,
  city TEXT, country TEXT, online INT DEFAULT 0,
  instructor TEXT, lineage TEXT, org_id TEXT
);

CREATE TABLE orgs (               -- diretório: federações e dojos
  id TEXT PRIMARY KEY, name TEXT, kind TEXT,  -- federation | dojo | dojo_hq
  country TEXT, state TEXT, city TEXT,
  lineage TEXT, parent_id TEXT, url TEXT, contact TEXT, notes TEXT
);

CREATE TABLE lineages (
  id TEXT PRIMARY KEY, name TEXT, founder TEXT,
  parent_id TEXT, notes TEXT
);

CREATE TABLE translations_cache (
  content_hash TEXT PRIMARY KEY, src_lang TEXT, text_pt TEXT, created_at TEXT
);
```

Dedupe: `items.url` UNIQUE + comparação de `content_hash` (item editado na
fonte → update, não insert).

Seed inicial de `lineages` (da pesquisa):
`aikikai` → filhos: `tissier_ffaaa`, `kawai`, `kumano_anno`;
irmãos: `yoshinkan`, `iwama_saito`, `ki_society`, `shodokan`, `yuishinkai`.

## 5. Decisões técnicas e justificativas

| Decisão | Escolha v1 | Por quê / quando revisitar |
|---|---|---|
| Scheduler | GitHub Actions cron | Grátis, logs, zero infra. Migrar p/ K8s (CronJob) só se: runs > 6h/mês de quota, necessidade de IP fixo, ou volume de headless alto |
| Linguagem scraper | Python (httpx + selectolax) | ETL é o forte do stack; parsers testáveis. Headless em Playwright-Python p/ manter uma língua só (alternativa: Puppeteer/Node que você já domina — decisão livre, isolar em `engine: headless`) |
| Banco | SQLite commitado no repo | Volume minúsculo (centenas de itens/ano). Migrar p/ Postgres (Neon free) se: escrita concorrente, site dinâmico, ou repo > 100MB |
| Raw store | Pasta `raw/` no repo, gzip | Migrar p/ Cloudflare R2 (free 10GB) quando incomodar |
| Site | Astro SSG | Content-first, build rápido, zero JS por padrão. Rebuild via workflow após ingestão |
| Hospedagem | Cloudflare Pages ou GitHub Pages | Custo zero, CDN global |
| Tradução | API (Claude/DeepL) só de título+resumo, cache permanente | Custo estimado < US$1/mês nesse volume |
| Timezone | Armazenar UTC + tz da fonte; exibir em America/Sao_Paulo | Eventos JP/FR têm fuso próprio — crítico p/ agenda |

## 6. Boas práticas de coleta (não-negociáveis)

1. Respeitar `robots.txt` — checado e cacheado por domínio antes de cada run
2. Rate-limit: ≥ 1s entre requests no mesmo domínio; jitter aleatório
3. `User-Agent` identificado: `AikidoAggregator/1.0 (+https://SEUSITE; contato@email)`
4. `If-Modified-Since` / `ETag` quando o servidor suportar (fontes estáticas → 304 grátis)
5. Nunca republicar conteúdo integral: título + resumo curto + **link canônico** para a fonte
6. Retry com backoff exponencial (3 tentativas); falha ≠ alarme, 3 falhas consecutivas = alerta
7. Timeout 30s http / 90s headless

## 7. Observabilidade

- Cada run grava linha em `fetches` (status, latência, changed)
- `reports/frequency-report.md` regenerado semanalmente:
  intervalo médio entre mudanças por fonte → recomendação de cadência
- Página `/status` do site renderiza a partir de `fetches`: última coleta,
  última mudança, streak de falhas
- Notificação (GitHub issue automática ou e-mail) quando `fail_streak >= 3`

## 8. Evolução prevista

```
v1  SQLite + Actions + Astro          (Fases 0–4)
v1.1 Fontes AR/CL/Yoshinkan, newsletter
v2  Postgres + API própria, se houver audiência
     ├─ submissão de eventos por terceiros (moderada)
     └─ i18n (EN)
```
