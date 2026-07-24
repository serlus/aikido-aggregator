"""aikikai_jp.py — notícias do Hombu Dojo via API JSON própria do site.

O aikikai.or.jp renderiza notícias client-side (Vue) alimentado por
/js/load_information.php — JSON limpo, sem parsing de HTML (endpoint
anotado em sources.yml via `endpoints:`). Descoberto em 2026-07-24
lendo o fonte da homepage /eng/.

Formato: {"total": N, "data": [{"id", "news_date": "2026/07/10",
"kind_str", "link_type": "detail|news_url|upload_file", "news_link",
"news_title"}]}
"""
from __future__ import annotations

import json

from .base import Item

BASE = "https://aikikai.or.jp/"


def _news_url(n: dict) -> str | None:
    if n.get("link_type") == "detail":
        return f"{BASE}eng/news/detail/?news_id={n['id']}"
    return n.get("news_link") or None


def _iso_date(jp_date: str | None) -> str | None:
    return jp_date.replace("/", "-") if jp_date else None


def parse(result, source: dict) -> list[Item]:
    data = json.loads(result.text).get("data") or []
    items: list[Item] = []
    for n in data:
        url = _news_url(n)
        title = (n.get("news_title") or "").strip()
        if not url or not title:
            continue
        items.append(
            Item(
                url=url,
                type="news",
                title=title,
                external_id=str(n.get("id")),
                lang="en",
                published_at=_iso_date(n.get("news_date")),
                summary=n.get("kind_str") or None,   # rótulo: Aikikai/Publication…
            )
        )
    return items
