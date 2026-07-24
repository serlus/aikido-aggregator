#!/usr/bin/env python3
"""Testes offline do enricher (classify, geo, translate com client fake).

Uso:  make test   (ou  uv run scraper/tests/test_enricher.py)
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db as dbmod  # noqa: E402
from enricher import classify, geo, translate  # noqa: E402


def memdb():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    ROOT = Path(__file__).resolve().parent.parent.parent
    conn.executescript((ROOT / "db" / "schema.sql").read_text())
    return conn


def test_classify():
    assert classify.classify_type("Seminário Internacional 2026") == "seminar"
    assert classify.classify_type("Stage été > Roquebrune") == "seminar"
    assert classify.classify_type("63rd All Japan Aikido Demonstration") == "event"
    assert classify.classify_type("CALENDÁRIO DE EXAME – 2025") == "event"
    assert classify.classify_type("Hombu Dojo Summer Vacation") is None  # news fica news
    assert classify.classify_type(None) is None


def test_geo():
    assert geo.region_for("BR", "Criciúma") == "sul_br"
    assert geo.region_for("BR", "São Paulo") == "brasil"
    assert geo.region_for("JP", "Tanabe City") == "japao"
    assert geo.region_for("CZ", "Ostrava") == "europa"
    assert geo.region_for("US", None) == "outro"
    assert geo.country_for_city("Berlin") == "DE"
    assert geo.country_for_city("cidade inexistente") is None


def test_geo_pending_fills_lineage_and_region():
    conn = memdb()
    conn.execute("INSERT INTO sources (id, lineage) VALUES ('src', 'aikikai')")
    conn.execute("INSERT INTO items (id, source_id, url, type) VALUES (1, 'src', 'u', 'event')")
    conn.execute("INSERT INTO events (item_id, city, country) VALUES (1, 'Tanabe City', 'JP')")
    stats = geo.geocode_pending(conn)
    region, lineage = conn.execute(
        "SELECT region, lineage FROM events WHERE item_id=1"
    ).fetchone()
    assert region == "japao" and lineage == "aikikai"
    assert stats["region_filled"] == 1 and stats["lineage_filled"] == 1


class FakeClient:
    """Client fake: 'traduz' prefixando PT: e conta as chamadas."""
    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        prompt = kwargs["messages"][0]["content"]
        items = json.loads(prompt.split("\n", 1)[1])
        out = {"translations": [{"id": it["id"], "pt": f"PT: {it['text']}"} for it in items]}
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(out, ensure_ascii=False))]
        )


def test_translate_copia_pt_e_usa_cache():
    conn = memdb()
    conn.execute("INSERT INTO sources (id) VALUES ('src')")
    conn.executemany(
        "INSERT INTO items (id, source_id, url, lang, title, summary) VALUES (?,?,?,?,?,?)",
        [
            (1, "src", "u1", "pt", "Título em português", None),
            (2, "src", "u2", "fr", "Stage à Paris", "Résumé court"),
            (3, "src", "u3", "fr", "Stage à Paris", None),  # mesmo título do 2
        ],
    )
    fake = FakeClient()
    stats = translate.translate_pending(conn, client=fake)

    t1, t2, t3 = [conn.execute("SELECT title_pt FROM items WHERE id=?", (i,)).fetchone()[0]
                  for i in (1, 2, 3)]
    assert t1 == "Título em português"          # pt copiado sem API
    assert t2 == t3 == "PT: Stage à Paris"      # string única traduzida 1x
    assert stats["copied"] == 1
    assert stats["api"] == 2                     # título (único) + resumo
    assert fake.calls == 1                       # tudo em um batch

    # segunda rodada: nada pendente, nenhuma chamada nova
    conn.execute("INSERT INTO items (id, source_id, url, lang, title) VALUES (4,'src','u4','fr','Stage à Paris')")
    stats2 = translate.translate_pending(conn, client=fake)
    assert stats2["cache_hits"] == 1 and stats2["api"] == 0
    assert fake.calls == 1


TESTS = [test_classify, test_geo, test_geo_pending_fills_lineage_and_region,
         test_translate_copia_pt_e_usa_cache]

if __name__ == "__main__":
    for t in TESTS:
        t()
    print(f"{len(TESTS)} testes OK")
