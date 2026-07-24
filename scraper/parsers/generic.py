"""generic.py — parser fallback: 1 item tipo "page" por fetch.

Extrai só o que dá pra extrair de qualquer HTML (título e data de
publicação via metatags). Suficiente p/ fechar a Fase 1; parsers
dedicados por fonte são entrega da Fase 2.
"""
from __future__ import annotations

from selectolax.parser import HTMLParser

from .base import Item


def _meta(tree: HTMLParser, *selectors: str) -> str | None:
    for sel in selectors:
        node = tree.css_first(sel)
        if node:
            content = (node.attributes.get("content") or "").strip()
            if content:
                return content
    return None


def parse(result, source: dict) -> list[Item]:
    tree = HTMLParser(result.body)
    title = _meta(tree, 'meta[property="og:title"]', 'meta[name="twitter:title"]')
    if not title:
        node = tree.css_first("title") or tree.css_first("h1")
        title = node.text(strip=True) if node else None
    published = _meta(tree, 'meta[property="article:published_time"]')
    summary = _meta(tree, 'meta[property="og:description"]', 'meta[name="description"]')
    langs = source.get("lang") or []
    return [
        Item(
            url=result.url,
            type="page",
            title=title,
            lang=langs[0] if langs else None,
            published_at=published,
            summary=(summary or "")[:500] or None,
        )
    ]
