#!/usr/bin/env python3
"""
enrich.py — Fase 3: classifica, geocodifica e traduz os itens ingeridos.

Ordem: classify (regras, grátis) → geo (estático, grátis) → translate
(API Claude, só strings fora do cache). Idempotente — roda após cada
ingestão; sem pendências, não faz nenhuma chamada de API.

Uso:
  python scraper/enrich.py              # tudo
  python scraper/enrich.py --no-api     # só classify+geo (sem tradução via API)

Critério de saída da Fase 3 (impresso ao final):
  feed 100% com títulos em PT; eventos com país e linhagem ≥ 90%.
"""
from __future__ import annotations

import argparse
import sys

import anthropic

import db as dbmod
from enricher import classify, geo, translate


def coverage(conn) -> dict:
    titles_total, titles_pt = conn.execute(
        "SELECT COUNT(*), SUM(title_pt IS NOT NULL) FROM items WHERE title IS NOT NULL"
    ).fetchone()
    ev_total, ev_ok = conn.execute(
        "SELECT COUNT(*), SUM(country IS NOT NULL AND lineage IS NOT NULL) FROM events"
    ).fetchone()
    return {
        "titles_total": titles_total or 0,
        "titles_pt": titles_pt or 0,
        "events_total": ev_total or 0,
        "events_ok": ev_ok or 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-api", action="store_true",
                    help="pular tradução via API (classify+geo apenas)")
    args = ap.parse_args()

    conn = dbmod.connect()

    c = classify.classify_pending(conn)
    print(f"[classify] {c['reclassified']}/{c['checked']} itens reclassificados")

    g = geo.geocode_pending(conn)
    print(f"[geo] {g['events']} eventos · país +{g['country_filled']} · "
          f"região +{g['region_filled']} · linhagem +{g['lineage_filled']}")

    try:
        t = translate.translate_pending(conn, use_api=not args.no_api)
        print(f"[translate] {t['items']} itens pendentes · {t['copied']} copiados (pt) · "
              f"{t['cache_hits']} do cache · {t['api']} strings via API"
              + (f" · {t['skipped_api']} aguardando API" if t.get("skipped_api") else ""))
    except (anthropic.AuthenticationError, TypeError):
        # TypeError: o SDK não resolveu nenhuma credencial do ambiente
        print("[translate] ERRO: sem credenciais da API Anthropic. "
              "Configure ANTHROPIC_API_KEY (local: export; CI: secret do repo). "
              "classify/geo e cópias pt->pt já foram aplicados.",
              file=sys.stderr)
        conn.close()
        return 1

    cov = coverage(conn)
    pct_t = 100 * cov["titles_pt"] / cov["titles_total"] if cov["titles_total"] else 0
    pct_e = 100 * cov["events_ok"] / cov["events_total"] if cov["events_total"] else 0
    print(f"[cobertura] títulos PT: {cov['titles_pt']}/{cov['titles_total']} ({pct_t:.0f}%) · "
          f"eventos com país+linhagem: {cov['events_ok']}/{cov['events_total']} ({pct_e:.0f}%)")
    ok = pct_t == 100 and pct_e >= 90
    print(f"[critério fase 3] {'ATENDIDO' if ok else 'pendente'}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
