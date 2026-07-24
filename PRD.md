# PRD — Agregador de Aikido (nome provisório: "AikiHub")

**Versão:** 0.1 · **Data:** 2026-07-23 · **Owner:** Sergio
**Status:** Draft para validação

---

## 1. Visão

Site pessoal que agrega, organiza e divulga informações do mundo do Aikido —
com foco primário em **Japão** e **França** (matrizes das principais linhagens)
e cobertura secundária de **Brasil, Argentina e Chile** — alimentado por
scrapers periódicos que monitoram fontes oficiais.

**Problema:** as informações de aikido estão fragmentadas em dezenas de sites
de federações, dojos e blogs — muitos desatualizados, em 4+ idiomas, sem
nenhum ponto central. Não existe hoje um calendário unificado de seminários
(estágios) que cruze eventos do Japão, França e América do Sul.

**Proposta de valor (diferencial):**
1. **Agenda unificada de seminários/estágios** — locais (SC/Sul do Brasil) e
   remotos (JP/FR/AR/CL), com filtros por linhagem, país e formato
   (presencial/online). Isso não existe em nenhum lugar hoje.
2. **Feed de notícias multi-fonte** com tradução PT dos títulos (JA/FR/ES → PT).
3. **Diretório de linhagens, federações e dojos** — dados frios, curados,
   com o mapeamento de genealogia técnica (Aikikai, Tissier, Kumano/Anno,
   Kawai, Yoshinkan, Iwama, Ki Society).

## 2. Usuários

| Persona | Necessidade |
|---|---|
| **Eu (owner)** | Organizar minha própria pesquisa; acompanhar fontes JP/FR sem visitar 15 sites |
| Praticante de aikido no Brasil | Descobrir seminários próximos e eventos internacionais; entender linhagens |
| Praticante lusófono geral | Notícias do Hombu Dojo / FFAAA traduzidas |

O produto é primariamente **pessoal** (v1); divulgação pública é objetivo de v2.

## 3. Escopo

### 3.1 Em escopo (v1)
- Coleta automatizada e periódica das fontes catalogadas (ver ARCHITECTURE.md §Fontes)
- Detecção de mudança por hash (evitar reprocessamento de fontes estáticas)
- Banco normalizado: notícias, eventos, fontes, dojos, linhagens
- Site estático com 3 seções: **Agenda**, **Notícias**, **Diretório**
- Pipeline de tradução de títulos (JA/FR/ES → PT)
- Painel simples de saúde dos scrapers (última coleta, status, diff detectado)

### 3.2 Fora de escopo (v1)
- Cadastro de usuários / área logada
- Submissão de eventos por terceiros
- Scraping de Instagram/Facebook (API restrita — coleta manual ou fase futura)
- App mobile
- Monetização

### 3.3 Restrições e riscos
| Risco | Mitigação |
|---|---|
| robots.txt bloqueia fontes (ex.: aikidobr.com.br) | Respeitar sempre; fallback: sitemap, coleta manual mensal |
| Sites JS-rendered (minasaikido) | Motor headless (Puppeteer/Playwright) só onde necessário |
| Encoding legado em sites JP (Shift-JIS) | Normalização UTF-8 na ingestão |
| Fonte comprometida (aikikai.com.br → phishing) | **Excluída** da lista; blocklist explícita no config |
| Mudança de layout quebra parser | Guardar HTML bruto; alertas no painel de saúde; parsers isolados por fonte |
| Custo de tradução | Traduzir apenas títulos + resumo curto; cache agressivo |

## 4. Requisitos funcionais

- **RF-01** Scrapers executam em cadência configurável por fonte (diária/semanal/mensal)
- **RF-02** Todo fetch persiste o conteúdo bruto (HTML/JSON) antes de qualquer parsing
- **RF-03** Sistema calcula `content_hash` e só dispara parsing quando há mudança
- **RF-04** Itens normalizados em schema único (source, type, título, título_pt, datas, local, linhagem, url)
- **RF-05** Eventos com data futura aparecem na Agenda; passados são arquivados
- **RF-06** Notícias exibidas em feed reverso-cronológico com filtro por país/linhagem
- **RF-07** Diretório navegável por linhagem → federação → dojo
- **RF-08** Painel de saúde lista cada fonte com: último run, status, último diff
- **RF-09** Fase de calibração: modo "hash-only" que roda diário em todas as fontes por 30–60 dias para medir frequência real de atualização

## 5. Requisitos não-funcionais

- **RNF-01** Custo de infra ~zero na v1 (GitHub Actions + site estático + SQLite)
- **RNF-02** Rate-limit cortês: 1 req/s por domínio, User-Agent identificado, respeito a robots.txt
- **RNF-03** Reprocessável: qualquer parser pode rodar de novo sobre o raw armazenado
- **RNF-04** Idempotente: re-execução não duplica itens (dedupe por url+hash)
- **RNF-05** Observável: logs por fonte, alerta em falha consecutiva (>2 runs)

## 6. Métricas de sucesso

| Métrica | Alvo v1 |
|---|---|
| Fontes ativas monitoradas | ≥ 12 |
| Cobertura de eventos futuros JP/FR na agenda | ≥ 80% dos publicados nas fontes |
| Uptime dos scrapers (runs bem-sucedidos) | ≥ 95% |
| Latência entre publicação na fonte e aparição no site | ≤ cadência da fonte + 24h |
| Esforço manual recorrente | ≤ 1h/semana |

## 7. Decisões em aberto

- [ ] Nome e domínio do site
- [ ] Idioma da UI: só PT ou PT+EN?
- [ ] Banco: SQLite commitado no repo (simples) vs Postgres gerenciado (Neon/Supabase free tier)
- [ ] Gerador do site: Astro (recomendado p/ conteúdo) vs Next.js SSG
- [ ] Incluir fontes AR/CL já na v1 ou deixar para v1.1?
- [ ] Cadências definitivas — **dependem da Fase 0 (calibração)**
