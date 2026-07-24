#!/usr/bin/env python3
"""
report.py — gera reports/frequency-report.md a partir de db/probes.sqlite.

Analisa o histórico de probes e recomenda cadência por fonte:
  - mudanças ~diárias/semanais  -> weekly (ou daily se muito ativa)
  - mudanças quinzenais/mensais -> monthly
  - nenhuma mudança observada   -> monthly (revisar após 60 dias)

Uso:  python scraper/report.py
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "probes.sqlite"
OUT_PATH = ROOT / "reports" / "frequency-report.md"
SOURCES_PATH = ROOT / "sources.yml"


def recommend(days_observed: float, changes: int) -> str:
    if days_observed < 7:
        return "aguardando dados (≥7 dias)"
    if changes == 0:
        return "monthly (nenhuma mudança ainda — revisar aos 60d)"
    interval = days_observed / changes
    if interval <= 2:
        return "daily"
    if interval <= 9:
        return "weekly"
    if interval <= 20:
        return "biweekly"
    return "monthly"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    with open(SOURCES_PATH, encoding="utf-8") as f:
        sources = {s["id"]: s for s in yaml.safe_load(f)["sources"]}

    rows = conn.execute(
        """
        SELECT source_id,
               COUNT(*)                                   AS probes,
               SUM(COALESCE(changed,0))                   AS changes,
               MIN(probed_at)                             AS first,
               MAX(probed_at)                             AS last,
               SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
               MAX(CASE WHEN changed=1 THEN probed_at END)        AS last_change
        FROM probes GROUP BY source_id ORDER BY source_id
        """
    ).fetchall()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Relatório de frequência de atualização",
        "",
        f"_Gerado em {now} · fonte: db/probes.sqlite_",
        "",
        "| Fonte | País | Probes | Mudanças | Erros | Última mudança | Intervalo médio | Cadência recomendada |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for sid, probes, changes, first, last, errors, last_change in rows:
        src = sources.get(sid, {})
        try:
            d0 = datetime.fromisoformat(first)
            d1 = datetime.fromisoformat(last)
            days = max((d1 - d0).total_seconds() / 86400, 0.01)
        except (TypeError, ValueError):
            days = 0.01
        interval = f"{days/changes:.1f}d" if changes else "—"
        rec = recommend(days, changes or 0)
        lines.append(
            f"| {src.get('name', sid)} | {src.get('country','?')} | {probes} "
            f"| {changes or 0} | {errors} | {last_change or '—'} | {interval} | **{rec}** |"
        )

    # endpoints descobertos
    eps = conn.execute(
        "SELECT source_id, kind, url FROM endpoints WHERE works=1 ORDER BY source_id"
    ).fetchall()
    if eps:
        lines += ["", "## Endpoints estruturados descobertos (usar em vez de scraping!)", ""]
        for sid, kind, url in eps:
            lines.append(f"- `{sid}` — **{kind}**: {url}")

    # robots disallow
    blocked = conn.execute(
        "SELECT source_id, robots_url FROM robots_status WHERE allowed=0"
    ).fetchall()
    if blocked:
        lines += ["", "## Bloqueadas por robots.txt", ""]
        for sid, robots_url in blocked:
            lines.append(f"- `{sid}` ({robots_url}) — coleta manual apenas")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {OUT_PATH}")


if __name__ == "__main__":
    main()
