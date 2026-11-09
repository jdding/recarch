// BM25 over card text. Latin words plus CJK unigrams and bigrams, no dependencies.
const CJK = /[\u3400-\u9fff]/;
export function tokenize(text) {
  const s = String(text || "").toLowerCase();
  const out = [];
  for (const m of s.matchAll(/[a-z0-9]+(?:[.\-][a-z0-9]+)*|[\u3400-\u9fff]+/g)) {
    const w = m[0];
    if (CJK.test(w[0])) {
      for (let i = 0; i < w.length; i++) { out.push(w[i]); if (i + 1 < w.length) out.push(w[i] + w[i + 1]); }
    } else {
      out.push(w);
      if (/[.\-]/.test(w)) for (const p of w.split(/[.\-]/)) if (p) out.push(p);
    }
  }
  return out;
}

const FIELDS = [["name", 4], ["id", 2], ["company", 3], ["paradigms", 2], ["system_type", 1], ["tldr", 2], ["core_idea", 1], ["deployed_in", 1], ["summary", 1], ["key_result", 1]];
function docText(c) {
  const parts = [];
  for (const [f, w] of FIELDS) {
    const v = Array.isArray(c[f]) ? c[f].join(" ") : c[f];
    if (v) for (let i = 0; i < w; i++) parts.push(String(v).replace(/-/g, " ") + " " + v);
  }
  return parts.join(" ");
}

export function buildIndex(cards) {
  const docs = cards.map((c) => tokenize(docText(c)));
  const df = new Map(); let total = 0;
  for (const d of docs) { total += d.length; for (const t of new Set(d)) df.set(t, (df.get(t) || 0) + 1); }
  const tf = docs.map((d) => { const m = new Map(); for (const t of d) m.set(t, (m.get(t) || 0) + 1); return m; });
  return { cards, docs, tf, df, avg: total / Math.max(1, docs.length), n: docs.length };
}

export function search(index, query, limit = 5, k1 = 1.4, b = 0.75) {
  const q = [...new Set(tokenize(query))];
  const scored = [];
  for (let i = 0; i < index.n; i++) {
    let s = 0; const len = index.docs[i].length;
    for (const t of q) {
      const f = index.tf[i].get(t); if (!f) continue;
      const n = index.df.get(t); const idf = Math.log(1 + (index.n - n + 0.5) / (n + 0.5));
      s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * len / index.avg));
    }
    if (s > 0) scored.push([s, i]);
  }
  scored.sort((a, b2) => b2[0] - a[0] || index.cards[a[1]].id.localeCompare(index.cards[b2[1]].id));
  return scored.slice(0, limit).map(([s, i]) => ({ card: index.cards[i], score: Math.round(s * 1000) / 1000 }));
}
