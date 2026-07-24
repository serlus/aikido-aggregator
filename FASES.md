# FASES — Roadmap de execução

> Cada fase tem critério de saída explícito. Não avançar sem cumpri-lo.
> Esforço estimado assume trabalho em horas vagas (side project).

---

## Fase 0 — Calibração de frequência (30–60 dias corridos, ~1 dia de dev)

**Objetivo:** substituir chute por dado empírico na definição das cadências.

**Entregas:**
- [x] Repo criado (`aikido-aggregator`) com estrutura base
- [x] `sources.yml` — catálogo das fontes com URL, país, motor, status
- [x] Script `probe.py`: para cada fonte, fetch → normaliza → `content_hash` → grava em `probes.sqlite` (source, timestamp, hash, http_status, latency)
- [x] GitHub Action com cron **diário** rodando o probe em todas as fontes
- [x] Verificação de RSS/`wp-json` em cada fonte WordPress (Paraná, Shoyukan, ACAI…) — anotado no `sources.yml` em 2026-07-24: wp_json real em acai_sc, fepai, ffaaa_fr; via `endpoints:` (pages) em aikido_parana e ica_sc; descartado em aikikai_jp (feed vazio), yoshinkan_jp e shoyukan_br (posts padrão/estáticos)
- [x] Verificação de robots.txt de cada fonte — anotar allow/disallow. Verificado 2026-07-24 (tabela `robots_status` em `db/probes.sqlite`, rechecado a cada probe): 19/19 fontes **allowed**, incl. cercletissier.com (URL nova) e christiantissier.com. Disallow conhecidos já estão em `blocklist.yml` (aikidobr.com.br, mapaosc.ipea.gov.br)

**Critério de saída:** ≥ 30 dias de dados; relatório `frequency-report.md` gerado
automaticamente com: mudanças detectadas por fonte, intervalo médio entre
mudanças, cadência recomendada (diária/semanal/mensal).

**Nota:** o probe é hash-only — não há parsing nesta fase. Baratíssimo,
roda em < 2 min. Enquanto os dados acumulam, você desenvolve as Fases 1–2
em paralelo.

---

## Fase 1 — Fundação de dados (~2–3 fins de semana, paralela à Fase 0)

**Objetivo:** schema, armazenamento de raw e pipeline de ingestão.

**Entregas:**
- [x] Schema SQLite (ver ARCHITECTURE.md §Modelo de dados): `sources`, `fetches`, `items`, `events`, `orgs`, `lineages` — `db/schema.sql`
- [x] Armazenamento de raw: `raw/{source}/{YYYY-MM-DD}/{hash}.html` (ou S3/R2 depois)
- [x] Módulo `fetcher` compartilhado: rate-limit por domínio, retry, UA identificado, normalização UTF-8 (incl. Shift-JIS → UTF-8) — `scraper/fetcher.py`
- [x] Blocklist explícita (aikikai.com.br) — `blocklist.yml`, aplicada pelo fetcher
- [x] Seed manual do diretório: linhagens e federações já mapeadas na pesquisa (Aikikai, Tissier/FFAAA, Kumano/Anno, Kawai, Yoshinkan, Iwama, Ki Society + orgs BR/AR/CL/JP/FR) — `db/seed.sql`

**Critério de saída:** `make ingest SOURCE=x` roda fim-a-fim para 1 fonte
estática (sugestão: aikidocriciuma.com.br — simples e estável) gravando raw
+ item normalizado. ✅ verificado em 2026-07-24 com `daisho_criciuma`
(baseline + re-run sem mudança, sem duplicar raw/item).

---

## Fase 2 — Scrapers Tier 1 (~3–4 fins de semana)

**Objetivo:** cobrir as fontes de maior valor com parser dedicado.

**Ordem de ataque (valor × facilidade):**
1. **Fontes WordPress com `wp-json`** (Paraná, Shoyukan, ACAI se confirmado na Fase 0) — sem parsing de HTML, resposta já estruturada com datas
2. **iwamashinshinaikido.com** (blog ativo, HTML previsível)
3. **aikikai.or.jp/eng** (Hombu — notícias e agenda oficial) ⭐ fonte JP principal
4. **FFAAA + Cercle Tissier** (agenda de stages) ⭐ fonte FR principal
5. **FEBRAI** (PHP legado, mas só 3-4 posts/ano — parser simples, cadência mensal)

**Entregas:**
- [x] 1 parser isolado por fonte (`parsers/{source}.py`), testável offline contra raw salvo — dedicados: `aikikai_jp` (API JSON própria do site, descoberta no fonte da página), `aikikai_jp_agenda`, `christian_tissier_agenda`, `iwama_shinshin`, `febrai`; genéricos por engine: `wp_json` (ffaaa_fr, acai_sc, fepai, aikido_parana e ica_sc via `endpoints:` pages) e `rss`
- [x] Testes de parser usando fixtures de HTML real — `scraper/tests/` (9 testes, `make test`)
- [x] Extração de eventos: título, data(s), cidade/país, instrutor, link — agenda Hombu (JSON) + stages Tissier (datas em francês, país por parênteses, instrutor por heurística)
- [x] GitHub Actions com crons separados por cadência — `.github/workflows/scrape.yml` (weekly seg / biweekly 1,15 / monthly dia 2; cadências provisórias até a Fase 0 fechar)

**Critério de saída:** ≥ 5 fontes com parser rodando em produção;
eventos futuros JP/FR aparecendo na tabela `events`. ✅ 2026-07-24:
10 fontes ingerindo (5 parsers dedicados + wp_json×5), 13 eventos
futuros JP/FR/CZ/DE/IT/BE em `events` com data, local e instrutor.
"Produção" efetiva quando o branch mergear e os crons rodarem.

---

## Fase 3 — Tradução e enriquecimento (~1–2 fins de semana)

**Entregas:**
- [x] Pipeline de tradução de títulos/resumos (JA/FR/ES → PT) via API, com cache por hash — item traduzido uma única vez (`scraper/enricher/translate.py`; backends Gemini via GOOGLE_API_KEY ou Claude via ANTHROPIC_API_KEY; lotes com JSON schema; itens pt copiam sem API)
- [x] Classificação automática: `type` (news/event/seminar) por regras multilíngues e `lineage` via linhagem da fonte (`classify.py`; 36 itens reclassificados na 1ª rodada)
- [x] Geocodificação leve de eventos (cidade → país/região) para filtro local/remoto — `geo.py` + coluna `events.region` (sul_br/brasil/america_sul/europa/japao)

**Critério de saída:** feed com 100% dos títulos em PT; eventos com país
e linhagem preenchidos em ≥ 90% dos casos. ✅ 2026-07-24: títulos
116/116 (100%) e eventos 13/13 (100%); 81 strings únicas traduzidas via
Gemini na 1ª rodada, cache permanente em `translations_cache`. Chaves
locais em `.env` (gitignored); p/ o cron, configurar o secret
`GOOGLE_API_KEY` no repositório.

---

## Fase 4 — Site público v1 (~2–3 fins de semana)

**Entregas:**
- [x] Site estático (Astro + Tailwind v4, visual do `design-system.html`) com build disparado pós-ingestão — `site/` + `.github/workflows/site-deploy.yml` (workflow_run após o scrape)
- [x] `/agenda` — eventos futuros, filtros: país, linhagem, online, "perto de mim" (Sul do Brasil via `events.region=sul_br`)
- [x] `/noticias` — feed agregado com origem e link canônico (título PT + resumo ≤200 chars + link; nunca conteúdo integral)
- [x] `/diretorio` — árvore de linhagens (ueshiba → aikikai → …) com federações e dojos do seed
- [x] `/status` — painel público de saúde por fonte (última coleta, última mudança, streak de falhas)
- [x] Deploy: GitHub Pages (custo zero) — `make site-dev` / `make site-build` p/ local

**Critério de saída:** site no ar com domínio próprio, atualizando sozinho.
⏳ código na main; falta: (1) habilitar Pages no repo (Settings → Pages →
Source: GitHub Actions), (2) apontar domínio próprio (CNAME + SITE_URL/
BASE_PATH="/" no workflow) quando o nome for decidido.

---

## Fase 5 — Operação e expansão (contínua)

- [x] Alertas de falha (>2 runs consecutivos com erro → notificação) — `scraper/alerts.py` + passo no `scrape.yml`: streak ≥ 3 abre issue com label `scraper-alert`; fonte recuperada fecha a issue automaticamente
- [x] Fontes Tier 2 — minasaikido: **engine headless implementado** (Playwright no fetcher; Chromium instalado no CI só na cadência monthly) + parser da tabela "Calendário" → 2 seminários BR na agenda; Yoshinkan: parser dedicado da homepage (`<time datetime>`) → 3 notícias JA; FEDENACHAA (timeout) e Círculo Aikikai AR (DNS morto) inacessíveis em 2026-07-24 — anotados no `sources.yml`, monitorados pelos alertas, URL nova fica p/ Fase 7
- [ ] Migração do scheduler p/ K8s **somente se** GitHub Actions limitar (não antecipar)
- [x] Avaliar: newsletter mensal automática — protótipo entregue: `scraper/newsletter.py` gera `reports/newsletter-YYYY-MM.md` (eventos futuros + notícias do mês) via cron mensal (`newsletter.yml`); canal de distribuição (e-mail) fica p/ quando houver audiência
- [x] Avaliar: página em EN — **adiado por decisão**: custo de manter tradução bidirecional não se justifica antes de haver audiência PT consolidada (revisitar após lançamento com domínio próprio; a infra de tradução da Fase 3 já suportaria o caminho inverso)

---

## Fase 6 — Front v2: refinamento visual (~2 fins de semana)

**Objetivo:** elevar o acabamento do site v1 mantendo o design system como base.

**Entregas:**
- [ ] Responsividade refinada mobile/desktop: navegação mobile (menu compacto), grids e tipografia fluida, filtros da agenda confortáveis no toque, tabela de status utilizável em tela pequena
- [ ] Imagens de fundo e texturas nas seções (hero e aberturas) — otimizadas (AVIF/WebP), sem custo de CDN, sem ferir o Lighthouse
- [ ] Elementos dinâmicos: micro-interações do design system (lift, nudge, reveal) revisadas + avaliar o hero 3D (torus/partículas douradas do `design-system.html`) com fallback estático
- [ ] Limpeza de informações internas do projeto no site público: **nenhuma menção a "fases"/roadmap** nas páginas (ex.: `/status` hoje cita "Fase 5") — esse vocabulário fica restrito ao repositório

**Critério de saída:** Lighthouse mobile ≥ 90 nas 5 páginas; zero menções a
fases/roadmap no HTML publicado; navegação completa confortável em 375px.

---

## Fase 7 — Expansão de fontes (~2–3 fins de semana, contínua depois)

**Objetivo:** ampliar a cobertura além das 19 fontes atuais sem degradar a qualidade.

**Entregas:**
- [ ] Levantamento de candidatas: federações estaduais BR restantes, Europa (Espanha, Portugal, Itália, Alemanha), EUA/Canadá, diretórios e calendários agregadores existentes
- [ ] Esteira de triagem por candidata: robots.txt → probe/discover (wp-json/rss) → cadência → parser (genérico quando possível, dedicado quando valer)
- [ ] Registro no `sources.yml` com tier e prioridade; blocklist quando necessário

**Critério de saída:** ≥ 10 novas fontes ativas ingerindo em produção,
nenhuma com fail streak crônico (≥3) após 2 semanas.

---

## Fase 8 — Comunidade: correções e submissões (~2 fins de semana)

**Objetivo:** abrir canal com os praticantes sem perder a curadoria.

**Entregas:**
- [ ] Contato para informações incorretas: e-mail dedicado + link "reportar erro" em itens da agenda, notícias e cards do diretório (assunto pré-preenchido com o identificador do item)
- [ ] Formulário de submissão de **evento** ou **novo dojo** (serviço estático compatível com Pages, ex.: Formspree/Tally/Google Forms) com campos alinhados ao schema (`events`/`orgs`)
- [ ] Fluxo de moderação documentado: fila → revisão manual → incorporação no `seed.sql`/`events` (submissão nunca publica direto — cf. ARCHITECTURE §8 "submissão moderada")

**Critério de saída:** canais publicados no site; 1 submissão de teste
percorrendo o fluxo fim-a-fim (envio → moderação → publicado no site).

---

## Resumo visual

```
Fase 0 (calibração, 30-60d)  ━━━━━━━━━━━━━━━━━━━━━━┓ dados de frequência
Fase 1 (fundação)      ━━━━━━━━┓ (paralela à F0)    ┃
Fase 2 (scrapers T1)           ┗━━━━━━━━━━━┓        ┃
Fase 3 (tradução)                          ┗━━━━┓   ┃
Fase 4 (site v1)                                ┗━━━┻━━━━━▶ lançamento
Fase 5 (operação)                                          ━━━━━▶ contínua
Fase 6 (front v2)                                          ━━━┓
Fase 7 (expansão de fontes)                                   ┣━━━▶ crescimento
Fase 8 (comunidade)                                        ━━━┛
```
