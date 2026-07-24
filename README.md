# aikido-aggregator

Agregador pessoal de informações de aikido (Japão, França, Brasil, AR/CL).
Docs: [PRD](PRD.md) · [FASES](FASES.md) · [ARCHITECTURE](ARCHITECTURE.md)

## Fase 0 — calibração de frequência (estado atual)

Probe hash-only roda diário via GitHub Actions e mede a frequência real de
atualização de cada fonte, para calibrar as cadências dos scrapers da Fase 2.

### Setup

```bash
pip install -r requirements.txt
python scraper/probe.py --discover   # primeiro run (baseline + endpoints)
python scraper/report.py             # gera reports/frequency-report.md
```

Antes do primeiro push: editar o `USER_AGENT` em `scraper/probe.py`
com a URL real do seu repositório.

No GitHub, o workflow `.github/workflows/probe-daily.yml` roda sozinho
(cron 09:00 UTC) e commita `db/probes.sqlite` + o relatório. Pode ser
disparado manualmente em Actions → probe-daily → Run workflow.

### Critério de saída da Fase 0
≥ 30 dias de dados e `reports/frequency-report.md` com cadência
recomendada por fonte. Aí atualizamos `sources.yml` e partimos pra Fase 2.
