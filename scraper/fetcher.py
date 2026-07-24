#!/usr/bin/env python3
"""
fetcher.py — Fase 1: HTTP client compartilhado do agregador.

Aplica as práticas não-negociáveis de ARCHITECTURE.md §6:
  - blocklist.yml checada antes de qualquer request
  - robots.txt checado e cacheado por domínio
  - rate-limit ≥1s + jitter por domínio
  - User-Agent identificado
  - retry com backoff exponencial (3 tentativas)
  - If-None-Match / If-Modified-Since quando o servidor suportar
  - normalização de encoding (UTF-8, Shift-JIS, cp1252) → str
"""
from __future__ import annotations

import hashlib
import random
import re
import time
import unicodedata
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from selectolax.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
BLOCKLIST_PATH = ROOT / "blocklist.yml"

USER_AGENT = (
    "AikidoAggregator/1.0 (+https://github.com/serlus/aikido-aggregator)"
)
TIMEOUT = 30.0
MIN_DELAY_S = 1.0
MAX_RETRIES = 3

_META_CHARSET = re.compile(rb"""charset\s*=\s*["']?([\w-]+)""", re.I)


class BlockedSourceError(Exception):
    """URL bate com blocklist.yml — nunca acessar."""


class RobotsDisallowedError(Exception):
    """robots.txt do domínio proíbe o fetch (ou retornou 5xx)."""


@dataclass
class FetchResult:
    url: str
    status: int
    body: bytes
    text: str                     # body decodificado e normalizado (NFC)
    content_hash: str             # hash do texto visível — estável a nonces
    latency_ms: int
    etag: str | None
    last_modified: str | None
    not_modified: bool = False    # True quando o servidor respondeu 304


def load_blocklist(path: Path = BLOCKLIST_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["blocked"]


def decode_body(body: bytes, declared: str | None) -> str:
    """Decodifica tentando: charset do header → <meta charset> → UTF-8 →
    Shift-JIS (fontes JP) → cp1252. Último recurso: UTF-8 com replace."""
    candidates: list[str] = []
    if declared:
        candidates.append(declared)
    m = _META_CHARSET.search(body[:4096])
    if m:
        candidates.append(m.group(1).decode("ascii", errors="ignore"))
    candidates += ["utf-8", "shift_jis", "cp1252"]
    for enc in candidates:
        try:
            return unicodedata.normalize("NFC", body.decode(enc))
        except (UnicodeDecodeError, LookupError):
            continue
    return unicodedata.normalize("NFC", body.decode("utf-8", errors="replace"))


def visible_text_hash(body: bytes) -> str:
    """Hash do texto visível — ignora <script>/<style> e whitespace, o mesmo
    critério do probe.py da Fase 0, p/ não acusar mudança por nonce/token."""
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
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class Fetcher:
    def __init__(self, blocklist: list[dict] | None = None):
        self.blocklist = blocklist if blocklist is not None else load_blocklist()
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        self._robots: dict[str, bool] = {}          # netloc -> allowed
        self._last_hit: dict[str, float] = {}       # netloc -> monotonic ts

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── guardas ──────────────────────────────────────────────────────────
    def check_blocklist(self, url: str) -> None:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        for entry in self.blocklist:
            b = entry["domain"].lower().removeprefix("www.")
            if host == b or host.endswith("." + b):
                raise BlockedSourceError(
                    f"{host}: {entry.get('reason', 'blocked').strip()[:120]}"
                )

    def _robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if netloc in self._robots:
            return self._robots[netloc]
        robots_url = f"{parsed.scheme}://{netloc}/robots.txt"
        try:
            resp = self._client.get(robots_url)
            if resp.status_code >= 500:
                allowed = False          # 5xx: conservador, não coleta
            elif resp.status_code >= 400:
                allowed = True           # sem robots.txt: permitido
            else:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(resp.text.splitlines())
                allowed = rp.can_fetch(USER_AGENT, url)
        except httpx.HTTPError:
            allowed = True               # inacessível ≠ proibido (RFC 9309)
        self._robots[netloc] = allowed
        return allowed

    def _throttle(self, netloc: str) -> None:
        last = self._last_hit.get(netloc)
        if last is not None:
            wait = MIN_DELAY_S + random.random() - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[netloc] = time.monotonic()

    # ── fetch ────────────────────────────────────────────────────────────
    def fetch(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        self.check_blocklist(url)
        if not self._robots_allowed(url):
            raise RobotsDisallowedError(url)

        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        netloc = urlparse(url).netloc
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            self._throttle(netloc)
            t0 = time.monotonic()
            try:
                resp = self._client.get(url, headers=headers)
            except httpx.HTTPError as e:
                last_err = e
                time.sleep(2 ** attempt)
                continue
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code >= 500 and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 304:
                return FetchResult(
                    url=url, status=304, body=b"", text="", content_hash="",
                    latency_ms=latency, etag=etag, last_modified=last_modified,
                    not_modified=True,
                )
            body = resp.content
            return FetchResult(
                url=url,
                status=resp.status_code,
                body=body,
                text=decode_body(body, resp.charset_encoding),
                content_hash=visible_text_hash(body),
                latency_ms=latency,
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
            )
        raise last_err if last_err else httpx.HTTPError(f"fetch failed: {url}")

    # ── headless (Fase 5: fontes JS-rendered, ex. minas_aikido) ──────────
    def fetch_headless(self, url: str) -> FetchResult:
        """Renderiza a página com Chromium (Playwright) e retorna o DOM.
        Mesmas guardas do fetch normal; timeout 90s (ARCHITECTURE §6)."""
        from playwright.sync_api import sync_playwright

        self.check_blocklist(url)
        if not self._robots_allowed(url):
            raise RobotsDisallowedError(url)
        self._throttle(urlparse(url).netloc)

        t0 = time.monotonic()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                resp = page.goto(url, timeout=90_000, wait_until="networkidle")
                html = page.content()
                status = resp.status if resp else 200
            finally:
                browser.close()
        latency = int((time.monotonic() - t0) * 1000)
        body = html.encode("utf-8")
        return FetchResult(
            url=url,
            status=status,
            body=body,
            text=unicodedata.normalize("NFC", html),
            content_hash=visible_text_hash(body),
            latency_ms=latency,
            etag=None,
            last_modified=None,
        )
