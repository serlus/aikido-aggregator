#!/usr/bin/env python3
"""Testes offline dos parsers, contra fixtures congeladas (sem rede).

Uso:  make test   (ou  uv run scraper/tests/test_parsers.py)
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from parsers import generic, rss, wp_json  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


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


if __name__ == "__main__":
    test_wp_json(); test_rss_japones(); test_wp_json_erro_api(); test_generic_html()
    print("4 testes OK")
