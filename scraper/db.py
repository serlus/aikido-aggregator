#!/usr/bin/env python3
"""
db.py — Fase 1: conexão com db/aikido.db, aplicação de schema e seed.

Schema e seed são idempotentes (IF NOT EXISTS / INSERT OR IGNORE), então
toda conexão os aplica — banco novo nasce pronto, banco existente não muda.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AIKIDO_DB", ROOT / "db" / "aikido.db"))
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def sync_sources(conn: sqlite3.Connection, sources: list[dict]) -> None:
    """Upsert do catálogo sources.yml na tabela sources.

    O YAML é a fonte de verdade dos campos de configuração; `robots` e
    `active` são estado de runtime e não são sobrescritos aqui.
    """
    for s in sources:
        conn.execute(
            """
            INSERT INTO sources (id, name, url, country, lineage, engine,
                                 cadence, priority, robots)
            VALUES (?,?,?,?,?,?,?,?, 'pending')
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name, url=excluded.url, country=excluded.country,
              lineage=excluded.lineage, engine=excluded.engine,
              cadence=excluded.cadence, priority=excluded.priority
            """,
            (
                s["id"], s.get("name"), s["url"], s.get("country"),
                s.get("lineage"), s.get("engine", "http"),
                s.get("cadence"), s.get("priority"),
            ),
        )
    conn.commit()
