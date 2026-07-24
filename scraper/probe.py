#!/usr/bin/env python3
"""
probe.py — Fase 0: calibração de frequência de atualização.

Para cada fonte em sources.yml:
  1. Checa blocklist e robots.txt
  2. Faz UM fetch da homepage (rate-limited, UA identificado)
  3. Extrai o texto visível e calcula content_hash (ignora scripts/nonces
     para reduzir falsos positivos de "mudança")
  4. Grava o resultado em db/probes.sqlite

Não faz parsing de conteúdo — é hash-only, barato, seguro de rodar diário.

Uso:
  python scraper/probe.py                 # roda todas as fontes
  python scraper/probe.py --only febrai   # roda uma fonte
  python scraper/probe.py --discover      # também testa /feed e /wp-json
"""
from __future__ import annotations

import argparse
import hashlib
import random
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from selectolax.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "probes.sqlite"
SOURCES_PATH = ROOT / "sources.yml"
BLOCKLIST_PATH = ROOT / "blocklist.yml"

USER_AGENT = (
    "AikidoAggregator/0.1 (Fase 0 - probe de frequencia; "
    "+https://github.com/serlus/aikido-aggregator)"
)
TIMEOUT = 30.0
MIN_DELAY_S = 1.0  # rate-limit entre requests (mesmo em domínios diferentes)

SCHEMA = """
CREATE TABLE IF NOT EXISTS probes (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  probed_at TEXT NOT NULL,          -- UTC ISO-8601
  http_status INTEGER,
  latency_ms INTEGER,
  raw_hash TEXT,                    -- hash dos bytes brutos
  text_hash TEXT,                   -- hash do texto visível (usar este p/ diff)
  text_len INTEGER,
  changed INTEGER,                  -- 1 se text_hash difere do probe anterior
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_probes_source ON probes(source_id, probed_at);

CREATE TABLE IF NOT EXISTS robots_status (
  source_id TEXT PRIMARY KEY,
  checked_at TEXT,
  allowed INTEGER,                  -- 1 allowed / 0 disallowed
  robots_url TEXT
);

CREATE TABLE IF NOT EXISTS endpoints (   -- resultado do --discover
  source_id TEXT NOT NULL,
  kind TEXT NOT NULL,               -- rss | wp_json
  url TEXT NOT NULL,
  http_status INTEGER,
  works INTEGER,
  checked_at TEXT,
  PRIMARY KEY (source_id, kind)
);
"""


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def is_blocked(url: str, blocklist: list[dict]) -> str | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for entry in blocklist:
        b = entry["domain"].lower().removeprefix("www.")
        if host == b or host.endswith("." + b):
            return entry.get("reason", "blocked")
    return None


def check_robots(client: httpx.Client, url: str) -> tuple[bool, str]:
    """Retorna (allowed, robots_url). Em erro de rede, assume allowed
    (padrão da RFC 9309 para robots inacessível ≠ 5xx)."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = client.get(robots_url)
        if resp.status_code >= 500:
            return False, robots_url  # 5xx: conservador, não coleta
        if resp.status_code >= 400:
            return True, robots_url   # sem robots.txt: permitido
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(USER_AGENT, url), robots_url
    except httpx.HTTPError:
        return True, robots_url


def visible_text_hash(body: bytes, content_type: str) -> tuple[str, str, int]:
    """(raw_hash, text_hash, text_len). text_hash ignora <script>/<style>
    e normaliza whitespace — reduz falso-positivo por nonce/token dinâmico."""
    raw_hash = hashlib.sha256(body).hexdigest()[:16]
    try:
        tree = HTMLParser(body)
        for sel in ("script", "style", "noscript"):
            for node in tree.css(sel):
                node.decompose()
        text = tree.body.text(separator=" ") if tree.body else tree.root.text()
    except Exception:
        text = body.decode("utf-8", errors="ignore")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return raw_hash, text_hash, len(text)


def previous_text_hash(conn: sqlite3.Connection, source_id: str) -> str | None:
    row = conn.execute(
        "SELECT text_hash FROM probes WHERE source_id=? AND text_hash IS NOT NULL "
        "ORDER BY probed_at DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    return row[0] if row else None


def probe_source(client: httpx.Client, conn: sqlite3.Connection, src: dict) -> str:
    sid, url = src["id"], src["url"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    allowed, robots_url = check_robots(client, url)
    conn.execute(
        "INSERT OR REPLACE INTO robots_status VALUES (?,?,?,?)",
        (sid, now, int(allowed), robots_url),
    )
    if not allowed:
        conn.execute(
            "INSERT INTO probes (source_id, probed_at, error) VALUES (?,?,?)",
            (sid, now, "robots_disallowed"),
        )
        return f"[{sid}] SKIP robots.txt disallow"

    t0 = time.monotonic()
    try:
        resp = client.get(url)
        latency = int((time.monotonic() - t0) * 1000)
        raw_hash, text_hash, text_len = visible_text_hash(
            resp.content, resp.headers.get("content-type", "")
        )
        prev = previous_text_hash(conn, sid)
        changed = None if prev is None else int(prev != text_hash)
        conn.execute(
            "INSERT INTO probes (source_id, probed_at, http_status, latency_ms,"
            " raw_hash, text_hash, text_len, changed) VALUES (?,?,?,?,?,?,?,?)",
            (sid, now, resp.status_code, latency, raw_hash, text_hash, text_len, changed),
        )
        flag = {None: "baseline", 0: "same", 1: "CHANGED"}[changed]
        return f"[{sid}] {resp.status_code} {latency}ms text={text_len} -> {flag}"
    except httpx.HTTPError as e:
        latency = int((time.monotonic() - t0) * 1000)
        conn.execute(
            "INSERT INTO probes (source_id, probed_at, latency_ms, error) VALUES (?,?,?,?)",
            (sid, now, latency, type(e).__name__),
        )
        return f"[{sid}] ERROR {type(e).__name__}"


def discover_endpoints(client: httpx.Client, conn: sqlite3.Connection, src: dict) -> list[str]:
    """Testa /feed (RSS) e /wp-json/wp/v2/posts. Grava em endpoints."""
    sid, base = src["id"], src["url"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    candidates = {
        "rss": urljoin(base, "/feed/"),
        "wp_json": urljoin(base, "/wp-json/wp/v2/posts?per_page=1"),
    }
    for kind, ep_url in candidates.items():
        time.sleep(MIN_DELAY_S + random.random())
        try:
            resp = client.get(ep_url)
            ct = resp.headers.get("content-type", "")
            works = int(
                resp.status_code == 200
                and (("xml" in ct) if kind == "rss" else ("json" in ct))
            )
            conn.execute(
                "INSERT OR REPLACE INTO endpoints VALUES (?,?,?,?,?,?)",
                (sid, kind, ep_url, resp.status_code, works, now),
            )
            if works:
                out.append(f"[{sid}] DISCOVER {kind} OK -> {ep_url}")
        except httpx.HTTPError:
            conn.execute(
                "INSERT OR REPLACE INTO endpoints VALUES (?,?,?,?,?,?)",
                (sid, kind, ep_url, None, 0, now),
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="rodar apenas uma fonte (id)")
    ap.add_argument("--discover", action="store_true",
                    help="também testar endpoints /feed e /wp-json")
    args = ap.parse_args()

    sources = load_yaml(SOURCES_PATH)["sources"]
    blocklist = load_yaml(BLOCKLIST_PATH)["blocked"]
    if args.only:
        sources = [s for s in sources if s["id"] == args.only]
        if not sources:
            print(f"fonte '{args.only}' não encontrada", file=sys.stderr)
            return 2

    conn = get_db()
    client = httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    )

    failures = 0
    for src in sources:
        reason = is_blocked(src["url"], blocklist)
        if reason:
            print(f"[{src['id']}] BLOCKED — {reason.strip()[:80]}")
            continue
        line = probe_source(client, conn, src)
        print(line)
        if "ERROR" in line:
            failures += 1
        if args.discover:
            for l in discover_endpoints(client, conn, src):
                print(l)
        conn.commit()
        time.sleep(MIN_DELAY_S + random.random())  # rate-limit + jitter

    conn.commit()
    conn.close()
    # exit 0 mesmo com falhas parciais — o report é quem analisa tendências;
    # falha total (todas as fontes) retorna 1 p/ o CI sinalizar
    return 1 if failures == len(sources) and sources else 0


if __name__ == "__main__":
    sys.exit(main())
