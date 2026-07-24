#!/usr/bin/env python3
"""
alerts.py — Fase 5: detecta fontes com falhas consecutivas de coleta.

Regra (ARCHITECTURE.md §6/§7): falha isolada não é alarme; >2 runs
consecutivos com erro (streak >= 3) => alerta. O workflow usa a saída
para abrir/fechar issues no GitHub (label scraper-alert).

Saída (stdout): uma linha por fonte ativa no formato
  ALERT|<source_id>|<streak>|<último erro>
  OK|<source_id>
Exit code: 0 sempre (alertar não é falhar o job).
"""
from __future__ import annotations

import sys

import db as dbmod

THRESHOLD = 3


def streaks(conn) -> list[tuple[str, int, str | None]]:
    """[(source_id, fail_streak, último_erro)] para fontes ativas."""
    sources = [r[0] for r in conn.execute(
        "SELECT id FROM sources WHERE active=1 ORDER BY id"
    )]
    out = []
    for sid in sources:
        rows = conn.execute(
            "SELECT http_status, error FROM fetches WHERE source_id=? "
            "ORDER BY fetched_at DESC LIMIT 10",
            (sid,),
        ).fetchall()
        streak, last_error = 0, None
        for status, error in rows:
            failed = bool(error) or (status is not None and status >= 400)
            if not failed:
                break
            streak += 1
            last_error = last_error or error or f"http_{status}"
        out.append((sid, streak, last_error))
    return out


def main() -> int:
    conn = dbmod.connect()
    alerts = 0
    for sid, streak, last_error in streaks(conn):
        if streak >= THRESHOLD:
            print(f"ALERT|{sid}|{streak}|{last_error or 'desconhecido'}")
            alerts += 1
        else:
            print(f"OK|{sid}")
    conn.close()
    print(f"# {alerts} alerta(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
