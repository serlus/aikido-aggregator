"""rss.py — parser genérico de feeds RSS 2.0 / Atom.

Cobre aikikai_jp (Hombu Dojo — só expõe /feed/, wp-json responde 403) e
serve de fallback para qualquer fonte com RSS descoberto. Usa xml.etree
da stdlib — sem dependência extra.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .base import Item

_ATOM = "{http://www.w3.org/2005/Atom}"
_TAG_RE = re.compile(r"<[^>]+>")


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", el.text)).strip() or None


def _to_utc_iso(value: str | None) -> str | None:
    """RFC-822 (RSS) ou ISO-8601 (Atom) -> UTC ISO-8601."""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)          # RSS: Tue, 21 Jul 2026 ...
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse(result, source: dict) -> list[Item]:
    root = ET.fromstring(result.body)
    langs = source.get("lang") or []
    lang = langs[0] if langs else None
    items: list[Item] = []

    # RSS 2.0
    for it in root.iter("item"):
        title = _text(it.find("title"))
        link = _text(it.find("link"))
        if not title or not link:
            continue
        items.append(
            Item(
                url=link,
                type="news",
                title=title,
                external_id=_text(it.find("guid")),
                lang=lang,
                published_at=_to_utc_iso(_text(it.find("pubDate"))),
                summary=(_text(it.find("description")) or "")[:500] or None,
            )
        )
    if items:
        return items

    # Atom
    for entry in root.iter(f"{_ATOM}entry"):
        title = _text(entry.find(f"{_ATOM}title"))
        link_el = entry.find(f"{_ATOM}link")
        link = link_el.get("href") if link_el is not None else None
        if not title or not link:
            continue
        items.append(
            Item(
                url=link,
                type="news",
                title=title,
                external_id=_text(entry.find(f"{_ATOM}id")),
                lang=lang,
                published_at=_to_utc_iso(
                    _text(entry.find(f"{_ATOM}published"))
                    or _text(entry.find(f"{_ATOM}updated"))
                ),
                summary=(_text(entry.find(f"{_ATOM}summary")) or "")[:500] or None,
            )
        )
    return items
