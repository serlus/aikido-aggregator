"""christian_tissier_agenda.py — agenda de estágios em christiantissier.com.

A homepage lista os stages como links de texto no formato
"datas > local/instrutor > instrutor/local", ex.:
  "27, 28 juin > Ostrava (Tchéquie) > Christian Tissier, Takeshi Kanazawa"
  "26 – 27 Septembre 2026 > Doshu Moriteru UESHIBA > Fareins (01)"
  "25 juillet au 1 août > Stage été > Roquebrune-sur-Argens"

Heurísticas (pinadas nos testes):
  - um <a> pode conter mais de um stage (uma linha por stage);
  - blocos desktop/mobile duplicam os links → dedupe por texto;
  - parte com Shihan/Sensei/Doshu/nome em CAIXA-ALTA → instrutor;
  - parte com "(País)" ou "(NN)" (departamento FR) → local; senão a última
    parte não-instrutor é o local;
  - ano ausente → ano corrente, ou seguinte se a data já passou há >90 dias.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from selectolax.parser import HTMLParser

from .base import Item

MONTHS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    "decembre": 12,
}
_MONTH_RE = "|".join(MONTHS_FR)

COUNTRIES = {
    "tchéquie": "CZ", "tchequie": "CZ", "allemagne": "DE", "italie": "IT",
    "belgique": "BE", "espagne": "ES", "suisse": "CH", "portugal": "PT",
    "pays-bas": "NL", "angleterre": "GB", "royaume-uni": "GB",
    "autriche": "AT", "pologne": "PL", "grèce": "GR", "grece": "GR",
}

_INSTRUCTOR_RE = re.compile(
    r"(Shihan|Sensei|Doshu|Tissier|[A-ZÀ-Þ]{3,}\s+[A-ZÀ-Þ]{3,})"
)
_PAREN_RE = re.compile(r"\(([^)]+)\)?\s*$")


def _parse_dates(text: str, today: date) -> tuple[str | None, str | None]:
    """Extrai (starts_at, ends_at) ISO de expressões como
    '27, 28 juin', '25 juillet au 1 août', '26 – 27 Septembre 2026'."""
    t = text.lower()
    year_m = re.search(r"\b(20\d{2})\b", t)
    year = int(year_m.group(1)) if year_m else None
    t = re.sub(r"\b20\d{2}\b", "", t)   # ano fora, senão vira "dia 20, dia 26"
    days_months = re.findall(rf"\b(\d{{1,2}})(?:er)?\b\s*({_MONTH_RE})?", t)
    days_months = [(int(d), MONTHS_FR.get(m)) for d, m in days_months if 1 <= int(d) <= 31]
    if not days_months:
        return None, None
    # propaga mês p/ trás: "27, 28 juin" -> 27/jun, 28/jun
    months_known = [m for _, m in days_months if m]
    if not months_known:
        return None, None
    last_month = None
    resolved = []
    for d, m in reversed(days_months):
        last_month = m or last_month
        resolved.append((d, last_month))
    resolved.reverse()
    first_d, first_m = resolved[0]
    last_d, last_m = resolved[-1]
    if year is None:
        year = today.year
        if date(year, last_m, min(last_d, 28)) < today - timedelta(days=90):
            year += 1
    end_year = year + 1 if last_m < first_m else year   # vira o ano (dez→jan)
    return f"{year:04d}-{first_m:02d}-{first_d:02d}", f"{end_year:04d}-{last_m:02d}-{last_d:02d}"


def _classify(parts: list[str]) -> tuple[str | None, str | None, str | None]:
    """(instructor, place, country) a partir das partes após as datas."""
    instructor = place = country = None
    for p in parts:
        paren = _PAREN_RE.search(p)
        if paren:
            inside = paren.group(1).strip().lower()
            place = place or p
            if inside.isdigit():
                country = country or "FR"
            else:
                country = country or COUNTRIES.get(inside)
        elif _INSTRUCTOR_RE.search(p):
            instructor = instructor or p
    for p in reversed(parts):        # última parte não-instrutor = local
        if place is None and p is not instructor and not p.lower().startswith("stage"):
            place = p                # "Stage été"/"Stage de Ligue" é título, não local
    if place:
        city = _PAREN_RE.sub("", place).strip(" >-–")
    else:
        city = None
    return instructor, city or None, country or "FR"


def parse_line(line: str, href: str, today: date) -> Item | None:
    parts = [p.strip() for p in line.split(">") if p.strip()]
    if len(parts) < 2:
        return None
    starts, ends = _parse_dates(parts[0], today)
    if starts is None:
        return None
    instructor, city, country = _classify(parts[1:])
    return Item(
        url=href,
        type="seminar",
        title=re.sub(r"\s+", " ", line).strip(),
        lang="fr",
        starts_at=starts,
        ends_at=ends,
        tz="Europe/Paris" if country == "FR" else None,
        city=city,
        country=country,
        instructor=instructor,
    )


def parse(result, source: dict, today: date | None = None) -> list[Item]:
    today = today or date.today()
    tree = HTMLParser(result.body)
    items: list[Item] = []
    seen_lines: set[str] = set()
    href_uses: dict[str, int] = {}
    for a in tree.css("a"):
        href = (a.attributes.get("href") or "").strip()
        if not href.startswith("http"):
            continue
        text = a.text(separator="\n", strip=True) or ""
        for raw_line in text.split("\n"):
            line = re.sub(r"\s+", " ", raw_line).strip()
            key = line.lower()
            if not re.search(rf"\d\s*(er)?[,\s–-]*.*\b({_MONTH_RE})\b", line.lower()):
                continue
            if ">" not in line or key in seen_lines:
                continue
            seen_lines.add(key)
            # href repetido (mesmo PDF anunciando vários stages) →
            # fragmento numerado p/ manter items.url único
            n = href_uses.get(href, 0)
            url = href if n == 0 else f"{href}#{n}"
            item = parse_line(line, url, today)
            if item:
                href_uses[href] = n + 1
                items.append(item)
    return items
