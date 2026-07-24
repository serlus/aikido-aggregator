"""translate.py — Fase 3: tradução de títulos/resumos (JA/FR/ES/EN → PT).

Regras de custo (ARCHITECTURE.md §5):
  - só título + resumo, nunca conteúdo integral;
  - cache permanente por hash do texto em translations_cache — cada string
    é traduzida UMA única vez;
  - itens já em PT copiam direto, sem API.

Backends (escolhido pelo ambiente, .env da raiz é carregado):
  - GOOGLE_API_KEY    → Gemini (REST via httpx, JSON schema na resposta)
  - ANTHROPIC_API_KEY → Claude (SDK anthropic, structured outputs)
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
CLAUDE_MODEL = "claude-opus-4-8"
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


class TranslationError(RuntimeError):
    """Falha de credencial/API na tradução (classify/geo não são afetados)."""


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Carrega KEY=VALUE do .env da raiz sem sobrescrever o ambiente."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


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


def _prompt(batch: list[tuple[int, str]]) -> str:
    payload = json.dumps([{"id": i, "text": t} for i, t in batch], ensure_ascii=False)
    return f"Traduza o campo 'text' de cada item para pt-BR:\n{payload}"


def _parse(text: str) -> dict[int, str]:
    return {t["id"]: t["pt"] for t in json.loads(text)["translations"]}


# ── backend Gemini ───────────────────────────────────────────────────────
_GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "translations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"id": {"type": "INTEGER"}, "pt": {"type": "STRING"}},
                "required": ["id", "pt"],
            },
        }
    },
    "required": ["translations"],
}


def gemini_translate(batch: list[tuple[int, str]], api_key: str) -> dict[int, str]:
    resp = httpx.post(
        GEMINI_URL,
        headers={"x-goog-api-key": api_key},
        json={
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"parts": [{"text": _prompt(batch)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _GEMINI_SCHEMA,
                "maxOutputTokens": MAX_TOKENS,
            },
        },
        timeout=120.0,
    )
    if resp.status_code != 200:
        raise TranslationError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise TranslationError(f"Gemini: resposta inesperada ({e})") from e


# ── backend Claude ───────────────────────────────────────────────────────
_CLAUDE_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "pt": {"type": "string"}},
                "required": ["id", "pt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def claude_translate(batch: list[tuple[int, str]], client=None) -> dict[int, str]:
    import anthropic

    try:
        client = client or anthropic.Anthropic()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": _CLAUDE_SCHEMA}},
            messages=[{"role": "user", "content": _prompt(batch)}],
        )
    except (anthropic.AuthenticationError, TypeError) as e:
        raise TranslationError(f"Claude: credenciais inválidas/ausentes ({e})") from e
    text = next(b.text for b in response.content if b.type == "text")
    return _parse(text)


def default_translate_fn():
    """Backend conforme o ambiente: Gemini > Claude."""
    load_dotenv()
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        return lambda batch: gemini_translate(batch, google_key)
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return claude_translate
    raise TranslationError(
        "sem credenciais: defina GOOGLE_API_KEY ou ANTHROPIC_API_KEY "
        "(no ambiente ou no .env da raiz)"
    )


# ── pipeline ─────────────────────────────────────────────────────────────
def translate_pending(conn: sqlite3.Connection, translate_fn=None, use_api: bool = True) -> dict:
    """Preenche items.title_pt/summary_pt pendentes. Retorna estatísticas.

    translate_fn injetável p/ testes: list[(id, texto)] -> {id: texto_pt}.
    A API só é chamada p/ strings fora do cache; use_api=False aplica
    apenas cópias pt e cache hits (grátis).
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
        if translate_fn is None:
            translate_fn = default_translate_fn()
        # traduz cada string única uma vez, mesmo que vários itens a usem
        unique: dict[str, tuple[str | None, str]] = {}
        for h, lang, text in pending.values():
            unique.setdefault(h, (lang, text))
        hashes = list(unique)
        for i in range(0, len(hashes), BATCH):
            chunk = hashes[i : i + BATCH]
            result = translate_fn([(n, unique[h][1]) for n, h in enumerate(chunk)])
            for n, h in enumerate(chunk):
                if n in result:
                    cache_put(conn, h, unique[h][0], result[n])
            stats["api"] += len(chunk)
            conn.commit()   # progresso preservado entre lotes
        for (item_id, col), (h, _lang, _text) in pending.items():
            pt = cache_get(conn, h)
            if pt is not None:
                conn.execute(f"UPDATE items SET {col}=? WHERE id=?", (pt, item_id))

    conn.commit()
    return stats
