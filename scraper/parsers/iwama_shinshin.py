"""iwama_shinshin.py — blog do Iwama Shinshin Aiki Shuren Kai.

WordPress sem feed nem wp-json públicos (404/403), mas os posts aparecem
na homepage como links permalink datados:
  https://iwamashinshinaikido.com/2026/01/18/new-years-greeting-2026/
A data de publicação vem da própria URL.
"""
from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from .base import Item

_POST_RE = re.compile(
    r"^https?://(?:www\.)?iwamashinshinaikido\.com/(\d{4})/(\d{2})/(\d{2})/[^\s\"?#]+"
)


def parse(result, source: dict) -> list[Item]:
    tree = HTMLParser(result.body)
    items: list[Item] = []
    seen: set[str] = set()
    for a in tree.css("a"):
        href = (a.attributes.get("href") or "").strip()
        m = _POST_RE.match(href)
        title = a.text(strip=True)
        if not m or not title or href in seen:
            continue
        seen.add(href)
        y, mo, d = m.groups()
        items.append(
            Item(
                url=href,
                type="news",
                title=title,
                lang="en" if title.isascii() else "ja",   # site bilíngue
                published_at=f"{y}-{mo}-{d}",
            )
        )
    return items
