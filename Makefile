# Makefile — atalhos do agregador. Tudo roda via uv (uv.lock é a fonte de verdade).

.PHONY: sync probe report ingest test

sync:            ## instala deps do lockfile
	uv sync --locked

probe:           ## Fase 0: probe hash-only de todas as fontes
	uv run scraper/probe.py

report:          ## Fase 0: regenera reports/frequency-report.md
	uv run scraper/report.py

test:            ## testes offline dos parsers (fixtures, sem rede)
	uv run scraper/tests/test_parsers.py

ingest:          ## Fase 1: make ingest SOURCE=daisho_criciuma (sem SOURCE = todas)
ifdef SOURCE
	uv run scraper/ingest.py --source $(SOURCE)
else
	uv run scraper/ingest.py --all
endif
