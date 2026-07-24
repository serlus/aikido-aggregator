# Makefile — atalhos do agregador. Tudo roda via uv (uv.lock é a fonte de verdade).

.PHONY: sync probe report ingest test enrich site-dev site-build site-dev site-build

sync:            ## instala deps do lockfile
	uv sync --locked

probe:           ## Fase 0: probe hash-only de todas as fontes
	uv run scraper/probe.py

report:          ## Fase 0: regenera reports/frequency-report.md
	uv run scraper/report.py

test:            ## testes offline (fixtures, sem rede)
	uv run scraper/tests/test_parsers.py
	uv run scraper/tests/test_enricher.py

enrich:          ## Fase 3: classifica, geocodifica e traduz pendências
	uv run scraper/enrich.py

site-dev:        ## Fase 4: dev server do site (http://localhost:4321)
	cd site && npm run dev

site-build:      ## Fase 4: build estático do site em site/dist
	cd site && npm run build

site-dev:        ## Fase 4: dev server do site (http://localhost:4321)
	cd site && npm run dev

site-build:      ## Fase 4: build estático do site em site/dist
	cd site && npm run build

ingest:          ## Fase 1: make ingest SOURCE=daisho_criciuma (sem SOURCE = todas)
ifdef SOURCE
	uv run scraper/ingest.py --source $(SOURCE)
else
	uv run scraper/ingest.py --all
endif
