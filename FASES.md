# FASES — Roadmap de execução

> Cada fase tem critério de saída explícito. Não avançar sem cumpri-lo.
> Esforço estimado assume trabalho em horas vagas (side project).

---

## Fase 0 — Calibração de frequência (30–60 dias corridos, ~1 dia de dev)

**Objetivo:** substituir chute por dado empírico na definição das cadências.

**Entregas:**
- [ ] Repo criado (`aikido-aggregator`) com estrutura base
- [ ] `sources.yml` — catálogo das fontes com URL, país, motor, status
- [ ] Script `probe.py`: para cada fonte, fetch → normaliza → `content_hash` → grava em `probes.sqlite` (source, timestamp, hash, http_status, latency)
- [ ] GitHub Action com cron **diário** rodando o probe em todas as fontes
- [ ] Verificação de RSS/`wp-json` em cada fonte WordPress (Paraná, Shoyukan, ACAI…) — anotar no `sources.yml` quais expõem API
- [ ] Verificação de robots.txt de cada fonte — anotar allow/disallow

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
- [ ] Schema SQLite (ver ARCHITECTURE.md §Modelo de dados): `sources`, `fetches`, `items`, `events`, `orgs`, `lineages`
- [ ] Armazenamento de raw: `raw/{source}/{YYYY-MM-DD}/{hash}.html` (ou S3/R2 depois)
- [ ] Módulo `fetcher` compartilhado: rate-limit por domínio, retry, UA identificado, normalização UTF-8 (incl. Shift-JIS → UTF-8)
- [ ] Blocklist explícita (aikikai.com.br)
- [ ] Seed manual do diretório: linhagens e federações já mapeadas na pesquisa (Aikikai, Tissier/FFAAA, Kumano/Anno, Kawai, Yoshinkan, Iwama, Ki Society + orgs BR/AR/CL/JP/FR)

**Critério de saída:** `make ingest SOURCE=x` roda fim-a-fim para 1 fonte
estática (sugestão: aikidocriciuma.com.br — simples e estável) gravando raw
+ item normalizado.

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
- [ ] 1 parser isolado por fonte (`parsers/{source}.py`), testável offline contra raw salvo
- [ ] Testes de parser usando fixtures de HTML real
- [ ] Extração de eventos: título, data(s), cidade/país, instrutor, link
- [ ] GitHub Actions com crons separados por cadência (definidos pela Fase 0)

**Critério de saída:** ≥ 5 fontes com parser rodando em produção;
eventos futuros JP/FR aparecendo na tabela `events`.

---

## Fase 3 — Tradução e enriquecimento (~1–2 fins de semana)

**Entregas:**
- [ ] Pipeline de tradução de títulos/resumos (JA/FR/ES → PT) via API (Claude ou DeepL), com cache por hash — item traduzido uma única vez
- [ ] Classificação automática: `type` (news/event/seminar) e `lineage` quando inferível
- [ ] Geocodificação leve de eventos (cidade → país/região) para filtro local/remoto

**Critério de saída:** feed com 100% dos títulos em PT; eventos com país
e linhagem preenchidos em ≥ 90% dos casos.

---

## Fase 4 — Site público v1 (~2–3 fins de semana)

**Entregas:**
- [ ] Site estático (Astro sugerido) com build disparado pós-ingestão
- [ ] `/agenda` — eventos futuros, filtros: país, linhagem, presencial/online, "perto de mim" (Sul do Brasil)
- [ ] `/noticias` — feed agregado com origem e link canônico (respeitando direitos: título + resumo curto + link, nunca conteúdo integral)
- [ ] `/diretorio` — linhagens → federações → dojos (dados da Fase 1 + pesquisa)
- [ ] `/status` — painel de saúde dos scrapers (público ou privado)
- [ ] Deploy: GitHub Pages / Cloudflare Pages (custo zero)

**Critério de saída:** site no ar com domínio próprio, atualizando sozinho.

---

## Fase 5 — Operação e expansão (contínua)

- [ ] Alertas de falha (>2 runs consecutivos com erro → notificação)
- [ ] Fontes Tier 2: minasaikido (headless), FEDENACHAA, Círculo Aikikai AR, Yoshinkan
- [ ] Migração do scheduler p/ K8s **somente se** GitHub Actions limitar (não antecipar)
- [ ] Avaliar: newsletter mensal automática com resumo da agenda
- [ ] Avaliar: página em EN para alcance internacional

---

## Resumo visual

```
Fase 0 (calibração, 30-60d)  ━━━━━━━━━━━━━━━━━━━━━━┓ dados de frequência
Fase 1 (fundação)      ━━━━━━━━┓ (paralela à F0)    ┃
Fase 2 (scrapers T1)           ┗━━━━━━━━━━━┓        ┃
Fase 3 (tradução)                          ┗━━━━┓   ┃
Fase 4 (site v1)                                ┗━━━┻━━━━━▶ lançamento
Fase 5 (operação)                                          ━━━━━▶ contínua
```
