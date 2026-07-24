"""aikikai_jp_agenda.py — agenda oficial do Hombu via API JSON do site.

Endpoint /js/load_events.php com from_now=1 (só eventos futuros), anotado
em sources.yml via `endpoints:`. Descoberto em 2026-07-24.

Formato: {"total": N, "data": [{"id", "calendar_from_to":
"2026/08/07" ou "2026/10/17-2026/10/18", "calendar_title",
"calendar_topics": "<p>...</p>", "calendar_place", "kind_str"}]}
"""
from __future__ import annotations

import json
import re

from .base import Item

BASE = "https://aikikai.or.jp/"
_TAG_RE = re.compile(r"<[^>]+>")


def _dates(from_to: str | None) -> tuple[str | None, str | None]:
    """'2026/10/17-2026/10/18' -> ('2026-10-17', '2026-10-18')."""
    if not from_to:
        return None, None
    found = re.findall(r"\d{4}/\d{2}/\d{2}", from_to)
    if not found:
        return None, None
    start = found[0].replace("/", "-")
    end = found[-1].replace("/", "-")
    return start, end


def _clean(html: str | None) -> str | None:
    if not html:
        return None
    text = re.sub(r"\s+", " ", _TAG_RE.sub(" ", html)).strip()
    return text or None


def parse(result, source: dict) -> list[Item]:
    data = json.loads(result.text).get("data") or []
    items: list[Item] = []
    for n in data:
        title = (n.get("calendar_title") or "").strip()
        if not title:
            continue
        starts, ends = _dates(n.get("calendar_from_to"))
        items.append(
            Item(
                url=f"{BASE}eng/event/detail/?event_id={n['id']}",
                type="event",
                title=title,
                external_id=str(n.get("id")),
                lang="en",
                summary=_clean(n.get("calendar_topics")),
                starts_at=starts,
                ends_at=ends,
                tz="Asia/Tokyo",
                city=n.get("calendar_place") or None,   # local/venue como anunciado
                country="JP",
            )
        )
    return items
