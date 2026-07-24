#!/usr/bin/env python3
"""
ingest.py — Fase 1: pipeline de ingestão fim-a-fim.

Para cada fonte, roteia pelo engine de sources.yml:
  wp_json/rss → endpoint estruturado (sem parsing de HTML)
  http        → homepage + parser dedicado (Fase 2) ou genérico

Fetch é condicional (ETag/Last-Modified do último run); conteúdo que mudou
grava raw em raw/{source}/{YYYY-MM-DD}/{hash}.{ext} e faz upsert em items.
Toda tentativa vira linha em fetches (observabilidade, ARCHITECTURE.md §7).

Uso:
  python scraper/ingest.py --source daisho_criciuma
  python scraper/ingest.py --all
  AIKIDO_DB=/tmp/dev.db python scraper/ingest.py ...   # banco alternativo
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import yaml

import db as dbmod
from fetcher import (
    BlockedSourceError,
    Fetcher,
    FetchResult,
    RobotsDisallowedError,
)
from parsers import get_parser, wp_json

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
SOURCES_PATH = ROOT / "sources.yml"

RAW_EXT = {"wp_json": "json", "rss": "xml"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def resolve_endpoint(src: dict) -> str:
    """URL efetiva da coleta. O campo opcional `endpoints:` em sources.yml
    sobrepõe a URL construída (ex.: WP que publica em /pages e não /posts)."""
    engine = src.get("engine", "http")
    override = (src.get("endpoints") or {}).get(engine)
    if override:
        return override
    if engine == "wp_json":
        return wp_json.build_url(src["url"])
    if engine == "rss":
        return urljoin(src["url"], "/feed/")
    return src["url"]


def last_fetch(conn: sqlite3.Connection, source_id: str, endpoint: str) -> tuple | None:
    """(content_hash, etag, last_modified) do último fetch 200 deste endpoint."""
    return conn.execute(
        "SELECT content_hash, etag, last_modified FROM fetches "
        "WHERE source_id=? AND endpoint=? AND http_status=200 "
        "AND content_hash IS NOT NULL ORDER BY fetched_at DESC LIMIT 1",
        (source_id, endpoint),
    ).fetchone()


def save_raw(source_id: str, content_hash: str, body: bytes, ext: str) -> str:
    """Grava raw/{source}/{YYYY-MM-DD}/{hash}.{ext}; retorna path relativo."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = RAW_DIR / source_id / day / f"{content_hash}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path.relative_to(ROOT))


def record_fetch(
    conn: sqlite3.Connection,
    source_id: str,
    endpoint: str,
    result: FetchResult | None = None,
    *,
    changed: int | None = None,
    raw_path: str | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO fetches (source_id, fetched_at, endpoint, http_status,"
        " latency_ms, content_hash, etag, last_modified, raw_path, changed, error)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            source_id, utcnow(), endpoint,
            result.status if result else None,
            result.latency_ms if result else None,
            (result.content_hash or None) if result else None,
            result.etag if result else None,
            result.last_modified if result else None,
            raw_path, changed, error,
        ),
    )


def upsert_items(conn: sqlite3.Connection, source_id: str, items) -> tuple[int, int]:
    """Insere itens novos; atualiza (e invalida tradução) quando o conteúdo
    do item mudou na fonte. Dedupe por items.url."""
    new = updated = 0
    for it in items:
        chash = hashlib.sha256(
            f"{it.title}|{it.summary or ''}".encode()
        ).hexdigest()[:16]
        row = conn.execute(
            "SELECT id, content_hash FROM items WHERE url=?", (it.url,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO items (source_id, url, external_id, type, title,"
                " summary, lang, published_at, updated_at, discovered_at, content_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (source_id, it.url, it.external_id, it.type, it.title,
                 it.summary, it.lang, it.published_at, it.updated_at,
                 utcnow(), chash),
            )
            new += 1
        elif row[1] != chash:
            conn.execute(
                "UPDATE items SET title=?, summary=?, updated_at=?, content_hash=?,"
                " title_pt=NULL, summary_pt=NULL WHERE id=?",  # re-traduzir na Fase 3
                (it.title, it.summary, it.updated_at, chash, row[0]),
            )
            updated += 1
    return new, updated


def ingest_source(conn: sqlite3.Connection, fetcher: Fetcher, src: dict) -> str:
    sid = src["id"]
    if src.get("engine") == "headless":
        return f"[{sid}] SKIP engine=headless (Fase 5)"

    endpoint = resolve_endpoint(src)
    prev = last_fetch(conn, sid, endpoint)
    prev_hash, etag, last_modified = prev if prev else (None, None, None)

    try:
        result = fetcher.fetch(endpoint, etag=etag, last_modified=last_modified)
    except BlockedSourceError as e:
        record_fetch(conn, sid, endpoint, error=f"blocked: {e}")
        conn.execute("UPDATE sources SET active=0 WHERE id=?", (sid,))
        return f"[{sid}] BLOCKED — {e}"
    except RobotsDisallowedError:
        record_fetch(conn, sid, endpoint, error="robots_disallowed")
        conn.execute("UPDATE sources SET robots='disallowed' WHERE id=?", (sid,))
        return f"[{sid}] SKIP robots.txt disallow"
    except Exception as e:
        record_fetch(conn, sid, endpoint, error=f"{type(e).__name__}: {e}"[:200])
        return f"[{sid}] ERROR {type(e).__name__}: {e}"

    conn.execute("UPDATE sources SET robots='allowed' WHERE id=?", (sid,))

    if result.not_modified:
        record_fetch(conn, sid, endpoint, result, changed=0)
        return f"[{sid}] 304 not modified"
    if result.status != 200:
        record_fetch(conn, sid, endpoint, result, error=f"http_{result.status}")
        return f"[{sid}] HTTP {result.status}"
    if prev_hash is not None and result.content_hash == prev_hash:
        record_fetch(conn, sid, endpoint, result, changed=0)
        return f"[{sid}] 200 sem mudança (hash {result.content_hash})"

    ext = RAW_EXT.get(src.get("engine", ""), "html")
    raw_path = save_raw(sid, result.content_hash, result.body, ext)
    changed = None if prev_hash is None else 1
    record_fetch(conn, sid, endpoint, result, changed=changed, raw_path=raw_path)

    try:
        items = get_parser(src).parse(result, src)
    except Exception as e:  # raw já está salvo — dá pra reprocessar offline
        return f"[{sid}] PARSE ERROR {type(e).__name__}: {e} (raw em {raw_path})"
    new, upd = upsert_items(conn, sid, items)
    flag = "baseline" if prev_hash is None else "CHANGED"
    return (
        f"[{sid}] 200 {flag} -> {raw_path} · "
        f"{len(items)} item(s): {new} novos, {upd} atualizados"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", help="ingerir apenas uma fonte (id)")
    g.add_argument("--all", action="store_true", help="ingerir todas as fontes ativas")
    args = ap.parse_args()

    sources = load_sources()
    if args.source:
        sources = [s for s in sources if s["id"] == args.source]
        if not sources:
            print(f"fonte '{args.source}' não encontrada em sources.yml", file=sys.stderr)
            return 2

    conn = dbmod.connect()
    dbmod.sync_sources(conn, load_sources())

    failures = 0
    with Fetcher() as fetcher:
        for src in sources:
            line = ingest_source(conn, fetcher, src)
            print(line)
            if "ERROR" in line:
                failures += 1
            conn.commit()

    conn.close()
    return 1 if failures == len(sources) and sources else 0


if __name__ == "__main__":
    sys.exit(main())
