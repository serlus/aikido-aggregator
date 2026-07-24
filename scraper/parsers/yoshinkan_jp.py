"""yoshinkan_jp.py — notícias do Yoshinkan Honbu (yoshinkan.net).

WordPress com wp-json inútil (só o "Hello world" padrão); as notícias
reais estão na homepage como <a href="/news/{slug}"> contendo
<time datetime="YYYY-MM-DD"> + categoria + título em japonês.
"""
from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from .base import Item

_NEWS_RE = re.compile(r"^https?://(?:www\.)?yoshinkan\.net/news/.+")
_DATE_PREFIX = re.compile(r"^\d{4}\.\d{2}\.\d{2}")


def parse(result, source: dict) -> list[Item]:
    tree = HTMLParser(result.body)
    items: list[Item] = []
    seen: set[str] = set()
    for a in tree.css("a"):
        href = (a.attributes.get("href") or "").strip()
        if not _NEWS_RE.match(href) or href in seen:
            continue
        time_el = a.css_first("time")
        published = time_el.attributes.get("datetime") if time_el else None
        title = re.sub(r"\s+", " ", a.text(strip=True) or "")
        title = _DATE_PREFIX.sub("", title).strip()
        if not title:
            continue
        seen.add(href)
        items.append(
            Item(
                url=href,
                type="news",
                title=title,
                lang="ja",
                published_at=published,
            )
        )
    return items
