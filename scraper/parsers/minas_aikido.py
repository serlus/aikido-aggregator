"""minas_aikido.py — calendário de eventos da Federação Mineira (headless).

SPA React (engine: headless); o DOM renderizado traz a tabela
"Calendário AAAA" com colunas: Mês | Evento | Local - Dia | Sensei(s) |
Organização. Eventos não têm URL própria — sintetizamos url com fragmento
do título (estável p/ dedupe).
"""
from __future__ import annotations

import re
import unicodedata

from selectolax.parser import HTMLParser

from .base import Item

_YEAR_RE = re.compile(r"Calend[áa]rio\s+(20\d{2})")
_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")
_UF_RE = re.compile(r"[-–,]\s*(MG|BH|SP|RJ|ES)\s*$", re.I)


def _slug(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def _city(local: str) -> str | None:
    """'08/08 Rua Aluisio Davis, 66, Ouro Preto -BH' -> 'Ouro Preto'."""
    s = _DATE_RE.sub("", local, count=1)
    s = _UF_RE.sub("", s.strip(" -–,"))
    parts = [p.strip() for p in re.split(r"[,–-]", s) if p.strip()]
    if not parts:
        return None
    city = parts[-1]
    return city if not re.search(r"\d", city) and len(city) > 2 else (parts[-2] if len(parts) > 1 else None)


def parse(result, source: dict) -> list[Item]:
    tree = HTMLParser(result.body)
    m = _YEAR_RE.search(tree.body.text() if tree.body else "")
    year = int(m.group(1)) if m else None

    items: list[Item] = []
    seen: set[str] = set()
    for row in tree.css("table tr"):
        cells = [re.sub(r"\s+", " ", td.text(strip=True) or "") for td in row.css("td")]
        if len(cells) < 3:
            continue
        # colunas: Mês | Evento | Local - Dia | Sensei(s) | Organização
        _mes, title, local = cells[0], cells[1], cells[2]
        instructor = cells[3] if len(cells) > 3 and cells[3] else None
        dm = _DATE_RE.search(local)
        if not title or not dm or year is None:
            continue
        day, month = int(dm.group(1)), int(dm.group(2))
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        url = f"{source['url'].rstrip('/')}/#{_slug(title)}"
        if url in seen:
            continue
        seen.add(url)
        items.append(
            Item(
                url=url,
                type="seminar",
                title=title,
                lang="pt",
                starts_at=f"{year:04d}-{month:02d}-{day:02d}",
                ends_at=f"{year:04d}-{month:02d}-{day:02d}",
                tz="America/Sao_Paulo",
                city=_city(local),
                country="BR",
                instructor=instructor,
            )
        )
    return items
