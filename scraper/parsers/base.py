"""base.py — contrato dos parsers: parse(result, source) -> list[Item].

Um parser recebe o conteúdo já baixado pelo fetcher (result tem .body,
.text e .url) e nunca faz requests por conta própria — isso mantém os
parsers testáveis offline contra fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Item:
    url: str                          # link canônico na fonte (chave de dedupe)
    type: str = "page"                # news | event | seminar | page
    title: str | None = None
    external_id: str | None = None    # id na fonte (post id do WP, guid do RSS)
    lang: str | None = None
    published_at: str | None = None   # UTC ISO-8601 quando a fonte informar
    updated_at: str | None = None     # última modificação na fonte (UTC)
    summary: str | None = None        # texto curto original (entrada da tradução)
    extra: dict = field(default_factory=dict)
