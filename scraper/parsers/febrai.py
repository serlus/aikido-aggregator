"""febrai.py — notícias da FEBRAI (PHP legado, sem API).

A homepage lista links /noticia/{slug} cujo texto começa com a data:
  "20/06/2026Encontro de Senseis"
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from .base import Item

_DATE_PREFIX = re.compile(r"^(\d{2})/(\d{2})/(\d{4})\s*(.+)$", re.S)


def parse(result, source: dict) -> list[Item]:
    tree = HTMLParser(result.body)
    items: list[Item] = []
    seen: set[str] = set()
    for a in tree.css("a"):
        href = (a.attributes.get("href") or "").strip()
        if "/noticia/" not in href:
            continue
        url = urljoin(source["url"], href)
        text = re.sub(r"\s+", " ", a.text(strip=True) or "")
        m = _DATE_PREFIX.match(text)
        if not m or url in seen:
            continue
        seen.add(url)
        day, month, year, title = m.groups()
        items.append(
            Item(
                url=url,
                type="news",
                title=title.strip(),
                lang="pt",
                published_at=f"{year}-{month}-{day}",
            )
        )
    return items
