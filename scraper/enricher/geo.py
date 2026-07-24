"""geo.py — Fase 3: geocodificação leve de eventos (cidade → país/região).

Sem API externa: mapeamentos estáticos cobrem as cidades/venues que as
fontes reais produzem. Preenche events.country (quando a cidade é
conhecida), events.region (filtro local/remoto do site: "perto de mim" =
sul_br) e events.lineage (fallback: linhagem da fonte do item).
"""
from __future__ import annotations

import sqlite3

# cidade/venue (lowercase) -> país, p/ eventos sem country
CITY_COUNTRY = {
    "tokyo budokan": "JP", "nippon budokan": "JP", "hombu dojo": "JP",
    "tanabe city": "JP", "iwama": "JP", "shingu": "JP",
    "paris": "FR", "vincennes": "FR", "lyon": "FR", "marseille": "FR",
    "berlin": "DE", "bologne": "IT", "bologna": "IT",
    "louvain la neuve": "BE", "ostrava": "CZ",
    "são paulo": "BR", "rio de janeiro": "BR", "curitiba": "BR",
    "florianópolis": "BR", "criciúma": "BR", "blumenau": "BR",
    "joinville": "BR", "itajaí": "BR", "balneário camboriú": "BR",
    "porto alegre": "BR", "viamão": "BR",
    "buenos aires": "AR", "córdoba": "AR", "santiago": "CL",
}

# cidades do Sul do Brasil (SC/PR/RS) — filtro "perto de mim"
SUL_BR_CITIES = {
    "florianópolis", "criciúma", "blumenau", "joinville", "itajaí",
    "balneário camboriú", "curitiba", "londrina", "maringá",
    "porto alegre", "viamão", "caxias do sul", "pelotas",
}

COUNTRY_REGION = {
    "BR": "brasil",
    "AR": "america_sul", "CL": "america_sul", "UY": "america_sul", "PY": "america_sul",
    "JP": "japao",
    "FR": "europa", "DE": "europa", "IT": "europa", "BE": "europa",
    "ES": "europa", "CH": "europa", "PT": "europa", "GB": "europa",
    "CZ": "europa", "NL": "europa", "AT": "europa", "PL": "europa", "GR": "europa",
}


def region_for(country: str | None, city: str | None) -> str | None:
    if city and city.strip().lower() in SUL_BR_CITIES:
        return "sul_br"
    if country:
        return COUNTRY_REGION.get(country.upper(), "outro")
    return None


def country_for_city(city: str | None) -> str | None:
    return CITY_COUNTRY.get(city.strip().lower()) if city else None


def geocode_pending(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT e.item_id, e.city, e.country, e.region, e.lineage, s.lineage "
        "FROM events e JOIN items i ON i.id = e.item_id "
        "LEFT JOIN sources s ON s.id = i.source_id"
    ).fetchall()
    stats = {"events": len(rows), "country_filled": 0, "region_filled": 0, "lineage_filled": 0}
    for item_id, city, country, region, lineage, src_lineage in rows:
        updates = {}
        if country is None:
            inferred = country_for_city(city)
            if inferred:
                updates["country"] = country = inferred
                stats["country_filled"] += 1
        new_region = region_for(country, city)
        if region is None and new_region:
            updates["region"] = new_region
            stats["region_filled"] += 1
        if lineage is None and src_lineage:
            updates["lineage"] = src_lineage
            stats["lineage_filled"] += 1
        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(
                f"UPDATE events SET {sets} WHERE item_id=?",
                (*updates.values(), item_id),
            )
    conn.commit()
    return stats
