"""wp_json.py — parser genérico para a REST API do WordPress.

Cobre (conforme discover de 2026-07-24 em db/probes.sqlite): acai_sc,
aikido_parana, fepai, ffaaa_fr, ica_sc, shoyukan_br, yoshinkan_jp — e
qualquer futura fonte WP. A API já entrega dados estruturados; não há
parsing de HTML de página.
"""
from __future__ import annotations

import html as html_mod
import json
import re
from urllib.parse import urljoin

from .base import Item

FIELDS = "id,link,title,excerpt,date_gmt,modified_gmt"

_TAG_RE = re.compile(r"<[^>]+>")


def build_url(base: str, per_page: int = 20) -> str:
    return urljoin(base, f"/wp-json/wp/v2/posts?per_page={per_page}&_fields={FIELDS}")


def _clean(rendered: str | None) -> str:
    """Remove tags e entidades HTML do campo 'rendered' do WP."""
    if not rendered:
        return ""
    text = _TAG_RE.sub(" ", rendered)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _iso_utc(wp_gmt: str | None) -> str | None:
    """WP entrega '2026-07-20T14:03:11' em GMT sem sufixo — anexa +00:00."""
    if not wp_gmt:
        return None
    return wp_gmt if wp_gmt.endswith(("Z", "+00:00")) else wp_gmt + "+00:00"


def parse(result, source: dict) -> list[Item]:
    posts = json.loads(result.text)
    if isinstance(posts, dict):  # resposta de erro da API ({"code": ...})
        return []

    langs = source.get("lang") or []
    items: list[Item] = []
    for p in posts:
        title = _clean((p.get("title") or {}).get("rendered"))
        link = p.get("link")
        if not title or not link:
            continue
        summary = _clean((p.get("excerpt") or {}).get("rendered"))
        items.append(
            Item(
                url=link,
                type="news",
                title=title,
                external_id=str(p["id"]) if p.get("id") is not None else None,
                lang=langs[0] if langs else None,
                published_at=_iso_utc(p.get("date_gmt")),
                updated_at=_iso_utc(p.get("modified_gmt")),
                summary=summary[:500] or None,
            )
        )
    return items
