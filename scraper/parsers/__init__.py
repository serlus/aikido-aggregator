"""Registro de parsers.

Resolução por fonte: parser dedicado (parsers/{source_id}.py, Fase 2)
> parser do engine (wp_json/rss, resposta já estruturada) > genérico
(item único tipo "page" a partir do HTML).

Um parser expõe `parse(result, source) -> list[Item]`.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType

from . import generic, rss, wp_json

_BY_ENGINE = {"wp_json": wp_json, "rss": rss}


def get_parser(source: dict) -> ModuleType:
    try:
        return import_module(f".{source['id']}", package=__name__)
    except ImportError:
        return _BY_ENGINE.get(source.get("engine", ""), generic)
