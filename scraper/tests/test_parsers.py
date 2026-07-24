#!/usr/bin/env python3
"""Testes offline dos parsers, contra fixtures congeladas (sem rede).

Uso:  make test   (ou  uv run scraper/tests/test_parsers.py)
"""
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from parsers import generic, rss, wp_json  # noqa: E402
from parsers import (  # noqa: E402
    aikikai_jp,
    aikikai_jp_agenda,
    christian_tissier_agenda,
    febrai,
    iwama_shinshin,
    minas_aikido,
    yoshinkan_jp,
)

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 7, 24)   # data congelada — mesma dos fixtures


def fake_result(path: Path, url: str = "https://exemplo.com.br/") -> SimpleNamespace:
    body = path.read_bytes()
    return SimpleNamespace(url=url, body=body, text=body.decode("utf-8"))


def test_wp_json():
    items = wp_json.parse(fake_result(FIX / "wp_posts.json"), {"id": "teste_wp", "lang": ["pt"]})
    assert len(items) == 2
    a = items[0]
    assert a.title == "Seminário Internacional 2026"        # tags e entidades limpas
    assert a.summary == "Inscrições abertas para o seminário."
    assert a.published_at == "2026-07-20T14:03:11+00:00"    # GMT anotado
    assert a.updated_at == "2026-07-21T09:00:00+00:00"
    assert a.external_id == "101"
    assert a.lang == "pt"
    assert items[1].summary is None                          # excerpt vazio -> None


def test_rss_japones():
    items = rss.parse(fake_result(FIX / "feed_rss.xml"), {"id": "aikikai_jp", "lang": ["ja"]})
    assert len(items) == 1
    a = items[0]
    assert "演武大会" in a.title                              # japonês preservado
    assert a.published_at == "2026-07-20T18:00:00+00:00"    # JST -> UTC (-9h)
    assert a.url.endswith("embukai-2026")
    assert a.external_id == "embukai-2026"


def test_wp_json_erro_api():
    r = SimpleNamespace(url="x", body=b'{"code":"rest_no_route"}', text='{"code":"rest_no_route"}')
    assert wp_json.parse(r, {"id": "x"}) == []


def test_generic_html():
    html = b"<html><head><title>Dojo Teste</title></head><body><h1>oi</h1></body></html>"
    r = SimpleNamespace(url="https://dojo.teste/", body=html, text=html.decode())
    items = generic.parse(r, {"id": "dojo_teste", "lang": ["pt"]})
    assert len(items) == 1
    assert items[0].title == "Dojo Teste"
    assert items[0].type == "page"


def test_aikikai_news():
    items = aikikai_jp.parse(fake_result(FIX / "aikikai_news.json"), {"id": "aikikai_jp"})
    assert len(items) == 3
    a = items[0]
    assert a.title == "Regarding the video of the 63rd All Japan Aikido Embukai"
    assert a.url == "https://aikikai.or.jp/eng/news/detail/?news_id=576"
    assert a.published_at == "2026-07-10"
    assert a.type == "news"


def test_aikikai_agenda():
    items = aikikai_jp_agenda.parse(fake_result(FIX / "aikikai_events.json"), {"id": "x"})
    assert len(items) == 4
    memorial = next(i for i in items if "Memorial" in i.title)
    assert memorial.starts_at == "2026-10-17"        # "2026/10/17-2026/10/18"
    assert memorial.ends_at == "2026-10-18"
    assert memorial.city == "Tanabe City"
    assert memorial.country == "JP" and memorial.tz == "Asia/Tokyo"
    assert memorial.type == "event"
    single = next(i for i in items if i.external_id == "143")
    assert single.starts_at == single.ends_at == "2026-08-07"


def test_tissier_agenda():
    items = christian_tissier_agenda.parse(
        fake_result(FIX / "tissier_agenda.html", "https://christiantissier.com/"),
        {"id": "x"}, today=TODAY,
    )
    by_city = {i.city: i for i in items}
    assert len(items) == 9                            # dedupe desktop/mobile
    ostrava = by_city["Ostrava"]
    assert ostrava.starts_at == "2026-06-27" and ostrava.ends_at == "2026-06-28"
    assert ostrava.country == "CZ"
    assert ostrava.instructor == "Christian Tissier, Takeshi Kanazawa"
    assert by_city["Fareins"].starts_at == "2026-09-26"       # ano explícito
    assert by_city["Fareins"].instructor == "Doshu Moriteru UESHIBA"
    assert by_city["Berlin"].country == "DE"
    ete = by_city["Roquebrune-sur-Argens"]
    assert ete.starts_at == "2026-07-25" and ete.ends_at == "2026-08-01"  # cruza mês
    assert by_city["Paris"].city == "Paris"           # "Stage de Ligue" é título
    assert by_city["Louvain la Neuve"].country == "BE"  # <a> com 2 stages, split
    assert all(i.type == "seminar" for i in items)
    assert len({i.url for i in items}) == 9           # urls únicas p/ dedupe


def test_iwama():
    items = iwama_shinshin.parse(
        fake_result(FIX / "iwama_home.html", "https://iwamashinshinaikido.com/"),
        {"id": "x", "url": "https://iwamashinshinaikido.com/"},
    )
    assert len(items) == 4
    assert items[0].title == "New Year's Greeting (2026)"
    assert items[0].published_at == "2026-01-18"      # data extraída da URL
    assert items[0].lang == "en"


def test_febrai():
    items = febrai.parse(
        fake_result(FIX / "febrai_home.html", "https://aikidofebrai.com.br/"),
        {"id": "x", "url": "https://aikidofebrai.com.br/"},
    )
    assert len(items) == 4
    assert items[0].title == "Encontro de Senseis"
    assert items[0].published_at == "2026-06-20"      # "20/06/2026Título"
    assert items[0].url == "https://aikidofebrai.com.br/noticia/encontro-de-senseis"


def test_yoshinkan():
    items = yoshinkan_jp.parse(
        fake_result(FIX / "yoshinkan_home.html", "https://www.yoshinkan.net/"),
        {"id": "x", "url": "https://www.yoshinkan.net/"},
    )
    assert len(items) == 3
    assert items[0].published_at == "2026-07-18"      # de <time datetime>
    assert items[0].lang == "ja"
    assert "8月休館日" in items[0].title               # prefixo de data removido


def test_minas_calendario():
    items = minas_aikido.parse(
        fake_result(FIX / "minas_calendario.html", "https://www.minasaikido.com.br/"),
        {"id": "minas_aikido", "url": "https://www.minasaikido.com.br/"},
    )
    assert len(items) == 2
    a, b = items
    assert a.starts_at == "2026-08-08"                # ano do heading "Calendário 2026"
    assert a.city == "Ouro Preto" and a.country == "BR"
    assert a.instructor == "Alcino Lagares"
    assert a.type == "seminar" and a.tz == "America/Sao_Paulo"
    assert b.starts_at == "2026-08-15" and b.city == "Ipatinga"
    assert a.url != b.url and "#" in a.url            # url sintética estável


TESTS = [
    test_wp_json, test_rss_japones, test_wp_json_erro_api, test_generic_html,
    test_aikikai_news, test_aikikai_agenda, test_tissier_agenda,
    test_iwama, test_febrai, test_yoshinkan, test_minas_calendario,
]

if __name__ == "__main__":
    for t in TESTS:
        t()
    print(f"{len(TESTS)} testes OK")
