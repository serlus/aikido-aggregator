/**
 * Leitura de db/aikido.db em build time (SSG). Sem escrita.
 */
import Database from 'better-sqlite3';
import { fileURLToPath } from 'node:url';

const dbPath = fileURLToPath(new URL('../../../db/aikido.db', import.meta.url));
const db = new Database(dbPath, { readonly: true, fileMustExist: true });

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
               'jul', 'ago', 'set', 'out', 'nov', 'dez'];

/** '2026-09-26' -> '26 set 2026' (datas são date-only, fuso da fonte) */
export function fmtDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MESES[m - 1]} ${y}`;
}

/** intervalo compacto: mesmo mês -> '17–18 out 2026' */
export function fmtRange(start, end) {
  if (!start) return null;
  if (!end || end === start) return fmtDate(start);
  const [ys, ms, ds] = start.slice(0, 10).split('-').map(Number);
  const [ye, me, de] = end.slice(0, 10).split('-').map(Number);
  if (ys === ye && ms === me) return `${ds}–${de} ${MESES[ms - 1]} ${ys}`;
  if (ys === ye) return `${ds} ${MESES[ms - 1]} – ${de} ${MESES[me - 1]} ${ys}`;
  return `${fmtDate(start)} – ${fmtDate(end)}`;
}

export const COUNTRY_NAMES = {
  BR: 'Brasil', JP: 'Japão', FR: 'França', DE: 'Alemanha', IT: 'Itália',
  BE: 'Bélgica', CZ: 'Tchéquia', AR: 'Argentina', CL: 'Chile', ES: 'Espanha',
  CH: 'Suíça', PT: 'Portugal', GB: 'Reino Unido',
};

export function futureEvents() {
  return db.prepare(`
    SELECT e.item_id, e.starts_at, e.ends_at, e.city, e.country, e.region,
           e.online, e.instructor, e.lineage,
           COALESCE(i.title_pt, i.title) AS title, i.url,
           s.name AS source_name,
           l.name AS lineage_name
    FROM events e
    JOIN items i   ON i.id = e.item_id
    LEFT JOIN sources s  ON s.id = i.source_id
    LEFT JOIN lineages l ON l.id = e.lineage
    WHERE COALESCE(e.ends_at, e.starts_at) >= date('now')
    ORDER BY e.starts_at
  `).all();
}

export function news(limit = 120) {
  return db.prepare(`
    SELECT i.id, i.type, COALESCE(i.title_pt, i.title) AS title,
           i.summary_pt, i.url, i.lang,
           COALESCE(i.published_at, i.discovered_at) AS published_at,
           s.name AS source_name, s.country AS source_country
    FROM items i
    JOIN sources s ON s.id = i.source_id
    WHERE i.type IN ('news', 'event', 'seminar')
      AND i.title IS NOT NULL
    ORDER BY COALESCE(i.published_at, i.discovered_at) DESC
    LIMIT ?
  `).all(limit);
}

export function directory() {
  const lineages = db.prepare('SELECT * FROM lineages').all();
  const orgs = db.prepare(
    'SELECT * FROM orgs ORDER BY country, kind, name'
  ).all();
  const byId = Object.fromEntries(lineages.map((l) => [l.id, { ...l, children: [], orgs: [] }]));
  const roots = [];
  for (const l of Object.values(byId)) {
    if (l.parent_id && byId[l.parent_id]) byId[l.parent_id].children.push(l);
    else roots.push(l);
  }
  for (const o of orgs) {
    (byId[o.lineage] ?? byId.ueshiba)?.orgs.push(o);
  }
  return { roots, byId, orgs };
}

export function sourceStatus() {
  const sources = db.prepare(
    "SELECT * FROM sources WHERE active=1 ORDER BY priority, id"
  ).all();
  const fetchesBySource = db.prepare(`
    SELECT source_id, fetched_at, http_status, changed, error
    FROM fetches ORDER BY fetched_at DESC
  `).all();
  const grouped = {};
  for (const f of fetchesBySource) (grouped[f.source_id] ??= []).push(f);

  return sources.map((s) => {
    const fs = grouped[s.id] ?? [];
    const last = fs[0] ?? null;
    let failStreak = 0;
    for (const f of fs) {
      if (f.error || (f.http_status && f.http_status >= 400)) failStreak += 1;
      else break;
    }
    const lastChange = fs.find((f) => f.changed === 1)?.fetched_at ?? null;
    const lastOk = fs.find((f) => !f.error && f.http_status && f.http_status < 400)?.fetched_at ?? null;
    return { ...s, last, lastOk, lastChange, failStreak, fetches: fs.length };
  });
}

export function stats() {
  const q = (sql) => db.prepare(sql).get().n;
  return {
    sources: q('SELECT COUNT(*) n FROM sources WHERE active=1'),
    items: q("SELECT COUNT(*) n FROM items WHERE type IN ('news','event','seminar')"),
    events: q("SELECT COUNT(*) n FROM events WHERE COALESCE(ends_at, starts_at) >= date('now')"),
    countries: q('SELECT COUNT(DISTINCT country) n FROM sources WHERE active=1'),
    orgs: q('SELECT COUNT(*) n FROM orgs'),
    lastUpdate: db.prepare('SELECT MAX(fetched_at) t FROM fetches').get().t,
  };
}
