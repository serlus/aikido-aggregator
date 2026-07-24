# aikido-aggregator

Agregador de notícias, eventos e diretório do aikido — Japão, França, Brasil e
América do Sul — traduzido para o português.

**Site publicado (AikiHub):** https://serlus.github.io/aikido-aggregator/

Docs: [PRD](PRD.md) · [FASES](FASES.md) · [ARCHITECTURE](ARCHITECTURE.md)

## O que já está no ar

- **Coleta automatizada** (Fases 0–2): ~20 fontes monitoradas com cadência
  calibrada por dados reais de frequência; engines `wp_json`, `rss`, `html` e
  `headless` (Playwright) rodando via GitHub Actions (`scrape.yml`).
- **Enriquecimento** (Fase 3): classificação notícia/seminário/evento,
  geocodificação e tradução JA/FR/ES/EN → PT via Gemini, com cache em SQLite.
- **Site estático** (Fase 4): Astro + Tailwind, 5 páginas (home, agenda com
  filtros, notícias, diretório de linhagens, status dos scrapers), publicado
  no GitHub Pages a cada coleta (`site-deploy.yml`).
- **Operação** (Fase 5): alertas de falha viram issues automáticas
  (`scraper-alert`), newsletter mensal em `reports/`, fontes Tier 2.
- **Front v2** (Fase 6): responsividade refinada (menu mobile, status em
  cards, tipografia fluida), fotos auto-hospedadas do Wikimedia Commons
  (domínio público / CC BY / CC BY-SA — créditos no rodapé e em
  `site/src/assets/img/CREDITS.json`) otimizadas em AVIF/WebP no build,
  micro-interações com `prefers-reduced-motion`. Lighthouse mobile ≥ 90
  nas 5 páginas.

Próximas: expansão de fontes (Fase 7) e canal de submissões da comunidade
(Fase 8) — ver [FASES](FASES.md).

## Rodando localmente

Python via [uv](https://docs.astral.sh/uv/) (`uv.lock` é a fonte de verdade);
site em Node 22+.

```bash
make sync                      # deps Python do lockfile
make ingest                    # coleta todas as fontes (ou SOURCE=<id>)
make enrich                    # classifica, geocodifica e traduz pendências
make test                      # testes offline (fixtures, sem rede)

cd site && npm install
make site-dev                  # dev server em http://localhost:4321
make site-build                # build estático em site/dist
```

Outros atalhos: `make probe`, `make report`, `make newsletter`, `make alerts`
(descritos no [Makefile](Makefile)).

## Estrutura

```
scraper/     probe, fetcher, parsers, ingest, enrich, alerts, newsletter
sources.yml  catálogo de fontes (engine, cadência, tier, prioridade)
db/          SQLite (itens, eventos, orgs, cache de tradução)
site/        site Astro (AikiHub) — deploy via GitHub Pages
reports/     relatórios de frequência e newsletters geradas
```

O site publica apenas título + resumo + link para a fonte original;
o conteúdo integral fica sempre no site de origem.
