"""classify.py — Fase 3: classificação automática de items.type por regras.

Sem API: keywords multilíngues no título resolvem a maioria dos casos
("quando inferível", FASES.md). Só promove news/page → event/seminar;
nunca rebaixa o que um parser dedicado já tipou.
"""
from __future__ import annotations

import re
import sqlite3

SEMINAR_RE = re.compile(
    r"\b(stage|semin[aá]rio|seminar|workshop|curso|講習)|(estágio de aikido)",
    re.IGNORECASE,
)
EVENT_RE = re.compile(
    r"\b(embukai|taikai|demonstra\w*|demonstration|encontro|conven[çc][ãa]o|"
    r"festival|exame|memorial|celebra\w*|congresso|kagami biraki|"
    r"calend[aá]rio de exame)|(演武大会)",
    re.IGNORECASE,
)


def classify_type(title: str | None) -> str | None:
    """event/seminar quando inferível pelo título; None = manter como está."""
    if not title:
        return None
    if SEMINAR_RE.search(title):
        return "seminar"
    if EVENT_RE.search(title):
        return "event"
    return None


def classify_pending(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT id, title FROM items WHERE type IN ('news', 'page')"
    ).fetchall()
    stats = {"checked": len(rows), "reclassified": 0}
    for item_id, title in rows:
        new_type = classify_type(title)
        if new_type:
            conn.execute("UPDATE items SET type=? WHERE id=?", (new_type, item_id))
            stats["reclassified"] += 1
    conn.commit()
    return stats
