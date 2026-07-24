#!/usr/bin/env python3
"""
newsletter.py — Fase 5: resumo mensal automático da agenda (protótipo).

Gera reports/newsletter-YYYY-MM.md com os eventos futuros e as notícias
do último mês, em PT. Roda no cron mensal (newsletter.yml); o markdown
serve de base p/ e-mail/post quando houver canal de distribuição.

Uso:  python scraper/newsletter.py
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import db as dbmod

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "reports"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

COUNTRY = {"BR": "Brasil", "JP": "Japão", "FR": "França", "DE": "Alemanha",
           "IT": "Itália", "BE": "Bélgica", "CZ": "Tchéquia", "AR": "Argentina",
           "CL": "Chile"}


def fmt(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return f"{int(d):02d}/{int(m):02d}/{y}"


def main() -> None:
    conn = dbmod.connect()
    now = datetime.now(timezone.utc)

    events = conn.execute("""
        SELECT e.starts_at, e.ends_at, e.city, e.country, e.instructor,
               COALESCE(i.title_pt, i.title), i.url
        FROM events e JOIN items i ON i.id = e.item_id
        WHERE COALESCE(e.ends_at, e.starts_at) >= date('now')
        ORDER BY e.starts_at
    """).fetchall()

    news = conn.execute("""
        SELECT COALESCE(i.title_pt, i.title), i.url, i.published_at, s.name
        FROM items i JOIN sources s ON s.id = i.source_id
        WHERE i.type = 'news' AND i.published_at >= date('now', '-1 month')
        ORDER BY i.published_at DESC
    """).fetchall()

    lines = [
        f"# AikiHub — resumo de {MESES[now.month - 1]} de {now.year}",
        "",
        f"_Gerado automaticamente em {now:%Y-%m-%d}. Detalhes sempre no link da fonte original._",
        "",
        "## Próximos eventos e seminários",
        "",
    ]
    if events:
        for starts, ends, city, country, instructor, title, url in events:
            dates = fmt(starts) + (f" – {fmt(ends)}" if ends and ends != starts else "")
            place = " · ".join(x for x in (city, COUNTRY.get(country, country)) if x)
            extra = f" — {instructor}" if instructor else ""
            lines.append(f"- **{dates}** · {place} — [{title}]({url}){extra}")
    else:
        lines.append("_Nenhum evento futuro registrado._")

    lines += ["", "## Notícias do último mês", ""]
    if news:
        for title, url, published, source in news:
            lines.append(f"- {fmt(published)} · [{title}]({url}) — {source}")
    else:
        lines.append("_Nenhuma notícia publicada no período._")

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"newsletter-{now:%Y-%m}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {out.relative_to(ROOT)} ({len(events)} eventos, {len(news)} notícias)")
    conn.close()


if __name__ == "__main__":
    main()
