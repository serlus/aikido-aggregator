"""translate.py — Fase 3: tradução de títulos/resumos (JA/FR/ES/EN → PT).

Regras de custo (ARCHITECTURE.md §5):
  - só título + resumo, nunca conteúdo integral;
  - cache permanente por hash do texto em translations_cache — cada string
    é traduzida UMA única vez;
  - itens já em PT copiam direto, sem API.

Chamadas em lote com structured outputs (JSON schema) — uma request
traduz até BATCH strings. Credenciais: ANTHROPIC_API_KEY no ambiente
(ou perfil `ant auth login`).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

import anthropic

MODEL = "claude-opus-4-8"
BATCH = 25
MAX_TOKENS = 16000

SYSTEM = (
    "Você traduz para o português do Brasil títulos e resumos curtos de "
    "notícias e eventos de aikido vindos de sites em japonês, francês, "
    "espanhol e inglês. Regras: mantenha nomes próprios, títulos honoríficos "
    "(Shihan, Sensei, Doshu), graduações (7º Dan) e nomes de técnicas/eventos "
    "consagrados (Embukai, Kagami Biraki) como estão; traduza o restante de "
    "forma natural e concisa; preserve datas e o formato geral da linha; "
    "não acrescente comentários."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "pt": {"type": "string"},
                },
                "required": ["id", "pt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cache_get(conn: sqlite3.Connection, h: str) -> str | None:
    row = conn.execute(
        "SELECT text_pt FROM translations_cache WHERE content_hash=?", (h,)
    ).fetchone()
    return row[0] if row else None


def cache_put(conn: sqlite3.Connection, h: str, src_lang: str | None, text_pt: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO translations_cache VALUES (?,?,?,?)",
        (h, src_lang, text_pt, _utcnow()),
    )


def call_api(client, batch: list[tuple[int, str]]) -> dict[int, str]:
    """Traduz [(id, texto)] em uma request; retorna {id: texto_pt}."""
    payload = json.dumps(
        [{"id": i, "text": t} for i, t in batch], ensure_ascii=False
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{
            "role": "user",
            "content": f"Traduza o campo 'text' de cada item para pt-BR:\n{payload}",
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return {t["id"]: t["pt"] for t in json.loads(text)["translations"]}


def translate_pending(conn: sqlite3.Connection, client=None, use_api: bool = True) -> dict:
    """Preenche items.title_pt/summary_pt pendentes. Retorna estatísticas.

    client injetável p/ testes; por padrão anthropic.Anthropic() (resolve
    credenciais do ambiente). A API só é chamada p/ strings fora do cache;
    use_api=False aplica apenas cópias pt e cache hits (grátis).
    """
    rows = conn.execute(
        "SELECT id, lang, title, summary, title_pt, summary_pt FROM items "
        "WHERE title_pt IS NULL OR (summary IS NOT NULL AND summary_pt IS NULL)"
    ).fetchall()

    stats = {"items": len(rows), "copied": 0, "cache_hits": 0, "api": 0}
    # (item_id, campo) -> (hash, lang, texto) das strings que precisam de PT
    pending: dict[tuple[int, str], tuple[str, str | None, str]] = {}

    for item_id, lang, title, summary, title_pt, summary_pt in rows:
        fields = []
        if title_pt is None and title:
            fields.append(("title_pt", title))
        if summary_pt is None and summary:
            fields.append(("summary_pt", summary))
        for col, text in fields:
            if lang == "pt":
                conn.execute(f"UPDATE items SET {col}=? WHERE id=?", (text, item_id))
                stats["copied"] += 1
                continue
            h = text_hash(text)
            hit = cache_get(conn, h)
            if hit is not None:
                conn.execute(f"UPDATE items SET {col}=? WHERE id=?", (hit, item_id))
                stats["cache_hits"] += 1
            else:
                pending[(item_id, col)] = (h, lang, text)

    conn.commit()   # cópias pt e cache hits valem mesmo se a API falhar abaixo

    if pending and not use_api:
        stats["skipped_api"] = len(pending)
        return stats
    if pending:
        if client is None:
            client = anthropic.Anthropic()
        # traduz cada string única uma vez, mesmo que vários itens a usem
        unique: dict[str, tuple[str | None, str]] = {}
        for h, lang, text in pending.values():
            unique.setdefault(h, (lang, text))
        hashes = list(unique)
        for i in range(0, len(hashes), BATCH):
            chunk = hashes[i : i + BATCH]
            batch = [(n, unique[h][1]) for n, h in enumerate(chunk)]
            result = call_api(client, batch)
            for n, h in enumerate(chunk):
                if n in result:
                    cache_put(conn, h, unique[h][0], result[n])
            stats["api"] += len(chunk)
        for (item_id, col), (h, _lang, _text) in pending.items():
            pt = cache_get(conn, h)
            if pt is not None:
                conn.execute(f"UPDATE items SET {col}=? WHERE id=?", (pt, item_id))

    conn.commit()
    return stats
