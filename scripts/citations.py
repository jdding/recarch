#!/usr/bin/env python3
"""Generate data/citations.json (card id -> citation count) from the Semantic Scholar Graph API, with OpenAlex as fallback.
No Google Scholar scraping. Stdlib only. Safe to re-run weekly:  python3 scripts/citations.py [--only id1,id2] [--dry]

Lookup order per card:
  1. the primary_source DOI (published version preferred), else the card's arXiv id, else title search verified by title+year.
  2. other DOIs/arXiv ids of the SAME work (title similarity >= 0.9 to the primary record) are looked up too. If Semantic Scholar keeps
     them as separate records (venue + arXiv), the counts are summed and `note` says so. Different papers (e.g. a v2 follow-up) are ignored.
  3. If Semantic Scholar has nothing, OpenAlex (by DOI, else arXiv DOI 10.48550/arXiv.<id>) is used.
Cards with no paper (blog/code only) or whose paper is only a *related* work get no entry at all (see NO_PAPER); pages show nothing.
Entries: {count, source, source_url, fetched_on, matched_title, matched_year, ids, papers:[{name, count, source, source_url, matched_title, matched_year, ids}], note?}
  count is the TOTAL for the system. `papers` has one row per version for merged cards (those with `versions:`) and one row for every other card, so the format is uniform.
  Merged cards: every version's paper is looked up (venue + arXiv records of one version are summed), the per-version counts are summed into `count`,
  and a Semantic Scholar paperId is counted once per card even if two versions point at it. Admission is judged on this total (docs/admission.md).
"""
import argparse, datetime as dt, difflib, glob, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "citations.json")
UA = {"User-Agent": "RecArch-citations/1.0 (static database; contact via site)"}
S2 = "https://api.semanticscholar.org/graph/v1/paper/"
FIELDS = "title,year,citationCount,externalIds,authors"

# Cards deliberately without a count (reason is printed, not shown on the site).
NO_PAPER = {
    "netflix-foundation-model-2025": "based on a Netflix blog post; the paper in sources (RecSys 2024 sliding-window training) is related work, not this system",
}

def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code in (429, 500, 502, 503): time.sleep(3 * (i + 1)); continue
            raise
        except Exception:
            time.sleep(2 * (i + 1))
    return None

def norm(t): return re.sub(r"[^a-z0-9 ]", "", (t or "").lower().replace("-", " ")).strip()
def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()

def ids_of(c):
    dois, arx = [], []
    urls = [c["primary_source"]] + [s["url"] for s in c["sources"]]
    for u in urls:
        m = re.search(r"doi\.org/(10\.\S+)$", u, re.I)
        if m and m.group(1).lower() not in dois: dois.append(m.group(1).lower())
        m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", u)
        if m and m.group(1) not in arx: arx.append(m.group(1))
    return dois, arx

S2CACHE = {}   # "DOI:x"/"arXiv:y" -> record or None (not in S2); filled by one POST /paper/batch (unauthenticated GETs get 429 constantly)

def s2_prefetch(queries):
    queries = sorted(set(queries))
    for i in range(0, len(queries), 400):
        chunk = queries[i:i + 400]
        for attempt in range(6):
            try:
                req = urllib.request.Request(S2 + "batch?fields=" + FIELDS, data=json.dumps({"ids": chunk}).encode(), headers={**UA, "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as r: recs = json.load(r)
                for q, rec in zip(chunk, recs): S2CACHE[q] = rec
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503): time.sleep(10 * (attempt + 1)); continue
                raise
            except Exception: time.sleep(5 * (attempt + 1))

def s2_lookup(kind, v):
    q = {"doi": "DOI:" + v, "arxiv": "arXiv:" + v}[kind]
    if q in S2CACHE: return S2CACHE[q]
    return get(S2 + urllib.parse.quote(q, safe=":") + "?fields=" + FIELDS)

def oa_lookup(kind, v):
    key = ("doi:" + v) if kind == "doi" else ("doi:10.48550/arxiv." + v)
    r = get("https://api.openalex.org/works/" + urllib.parse.quote(key, safe=":") + "?mailto=recarch@example.com")
    return r

def s2_title_search(title, year):
    r = get(S2 + "search?query=" + urllib.parse.quote(title) + "&limit=5&fields=" + FIELDS)
    for p in (r or {}).get("data", []):
        if sim(p["title"], title) >= 0.92 and p.get("year") and abs(p["year"] - year) <= 1: return p
    return None

def paper_entry(recs, today):
    """recs: [(kind, v, S2 record)], first = the main record. Same work listed twice (venue + arXiv) is summed once per S2 paperId."""
    main = recs[0][2]; parts, ignored = [], []
    for k, v, r in recs:
        if r["paperId"] in {p[2]["paperId"] for p in parts}: continue
        if sim(r["title"], main["title"]) < 0.9: ignored.append(f"{k}:{v} ({r['title'][:50]})"); continue
        parts.append((k, v, r))
    e = {"count": sum(r["citationCount"] for _, _, r in parts), "source": "Semantic Scholar",
         "source_url": "https://www.semanticscholar.org/paper/" + main["paperId"], "fetched_on": today,
         "matched_title": main["title"], "matched_year": main.get("year"), "ids": [f"{k}:{v}" for k, v, _ in parts]}
    if len(parts) > 1:
        e["note"] = "Semantic Scholar lists the venue and arXiv versions separately; counts are summed (" + " + ".join(f"{r['citationCount']} {k}:{v}" for k, v, r in parts) + "). Papers citing both are counted twice."
    if ignored: e["ignored_other_papers"] = ignored
    return e

def fallback_entry(c, cands, today, title, year):
    p = s2_title_search(title, year)
    if p: return {"count": p["citationCount"], "source": "Semantic Scholar", "source_url": "https://www.semanticscholar.org/paper/" + p["paperId"],
                  "fetched_on": today, "matched_title": p["title"], "matched_year": p.get("year"), "ids": ["title-match"]}
    for k, v in cands:
        r = oa_lookup(k, v); time.sleep(0.2)
        if r and r.get("cited_by_count") is not None:
            return {"count": r["cited_by_count"], "source": "OpenAlex", "source_url": r["id"], "fetched_on": today,
                    "matched_title": r.get("title"), "matched_year": r.get("publication_year"), "ids": [f"{k}:{v}"]}
    return None

def ids_from_urls(urls):
    dois, arx = [], []
    for u in urls:
        m = re.search(r"doi\.org/(10\.\S+)$", u, re.I)
        if m and m.group(1).lower() not in dois: dois.append(m.group(1).lower())
        m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", u)
        if m and m.group(1) not in arx: arx.append(m.group(1))
    return [("doi", d) for d in dois] + [("arxiv", a) for a in arx]

def fetch(cands):
    out = []
    for k, v in cands:
        r = s2_lookup(k, v); time.sleep(0.4)
        if r and r.get("citationCount") is not None: out.append((k, v, r))
    return out

def lookup_card(c, today):
    """Returns the uniform entry: count = TOTAL over all papers of the system, papers = one row per version (single-version cards: one row).
    Each Semantic Scholar paperId is counted once across the whole card, so a paper reachable from two versions is never double counted."""
    dois, arx = ids_of(c)
    all_cands = [("doi", d) for d in dois] + [("arxiv", a) for a in arx]
    versions = c.get("versions") or [{"name": c.get("name"), "first_public": c.get("first_public"), "source": c["primary_source"]}]
    if c.get("versions"):   # presented version first so a shared record is credited to it
        versions = sorted(versions, key=lambda v: v["name"] != c.get("version"))
    claimed, rows, missing = set(), [], []
    pool = {(k, v): r for k, v, r in fetch(all_cands)}
    if not c.get("versions"):   # single-version card: its one paper = the first record found (primary source first) plus same-work records
        recs = [(k, v, pool[(k, v)]) for k, v in all_cands if (k, v) in pool]
        if recs: rows = [dict(paper_entry(recs, today), name=c["name"])]
        else:
            e = fallback_entry(c, all_cands, today, c.get("title") or c["name"], c["year"])
            if not e: return None
            rows = [dict(e, name=c["name"])]
        versions = []
    owned = {(k, v) for ver in versions for k, v in ids_from_urls([ver["source"]])} if c.get("versions") else set()
    for ver in versions:
        own = ids_from_urls([ver["source"]])
        recs = [(k, v, pool[(k, v)]) for k, v in own if (k, v) in pool and pool[(k, v)]["paperId"] not in claimed]
        if not recs and own and any((k, v) in pool for k, v in own):   # its paper was already counted under another version
            missing.append(ver["name"] + " (shares a paper with another version, counted once)"); continue
        if recs:
            main = recs[0][2]
            for k, v in all_cands:   # other records of the same work (venue + arXiv), matched by title
                r = pool.get((k, v))
                if r and (k, v) not in owned and r["paperId"] not in claimed and r["paperId"] != main["paperId"] and sim(r["title"], main["title"]) >= 0.9: recs.append((k, v, r))
            e = paper_entry(recs, today)
        else:
            e = fallback_entry(c, own or all_cands, today, ver["name"] if c.get("versions") else (c.get("title") or c["name"]), int(str(ver["first_public"])[:4]))
            if not e: return None
        for k, v, r in recs: claimed.add(r["paperId"])
        e["name"] = ver["name"]; rows.append(e)
    if not rows: return None
    if c.get("versions"): rows.sort(key=lambda r: [v["name"] for v in c["versions"]].index(r["name"]))   # oldest first, like `versions`
    # single-version cards keep the full old shape at top level; the one paper row mirrors it
    pres = next((r for r in rows if r["name"] == c.get("version")), rows[0])
    e = {"count": sum(r["count"] for r in rows), "source": pres["source"], "source_url": pres["source_url"], "fetched_on": today,
         "matched_title": pres["matched_title"], "matched_year": pres.get("matched_year"),
         "ids": [i for r in rows for i in r["ids"]],
         "papers": [{k: r[k] for k in ("name", "count", "source", "source_url", "matched_title", "matched_year", "ids") if k in r} for r in rows]}
    if len(rows) == 1 and rows[0].get("note"): e["note"] = rows[0]["note"]
    if any(r.get("ignored_other_papers") for r in rows): e["ignored_other_papers"] = [x for r in rows for x in r.get("ignored_other_papers", [])]
    if missing: e["shared_papers"] = missing
    return e

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only"); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    today = dt.date.today().isoformat()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    res = dict(old); problems = []
    qs = []
    for f in glob.glob(os.path.join(ROOT, "data/systems/*.yaml")):
        c = yaml.safe_load(open(f)); d, ar = ids_of(c); qs += ["DOI:" + x for x in d] + ["arXiv:" + x for x in ar]
    s2_prefetch(qs); print(f"S2 batch: {sum(1 for v in S2CACHE.values() if v)} of {len(qs)} ids found", flush=True)
    for f in sorted(glob.glob(os.path.join(ROOT, "data/systems/*.yaml"))):
        c = yaml.safe_load(open(f)); cid = c["id"]
        if a.only and cid not in a.only.split(","): continue
        if cid in NO_PAPER: res.pop(cid, None); print(f"{cid}: no count ({NO_PAPER[cid]})"); continue
        dois, arx = ids_of(c)
        if not dois and not arx: res.pop(cid, None); print(f"{cid}: no paper (blog/code only)"); continue
        e = lookup_card(c, today)
        if not e:
            if cid in old: print(f"{cid}: lookup failed, keeping previous value"); problems.append(cid); continue
            res.pop(cid, None); print(f"{cid}: NOT FOUND"); problems.append(cid); continue
        y = e.get("matched_year")
        if y and not c.get("versions") and abs(y - c["year"]) > 2: print(f"  WARN {cid}: matched year {y} vs card year {c['year']} -> {e['matched_title']}"); problems.append(cid)
        print(f"{cid}: {e['count']} ({e['source']}) {e['matched_title'][:60]}" + (" [" + " + ".join(f"{p['name']} {p['count']}" for p in e["papers"]) + "]" if len(e["papers"]) > 1 else "") + (" [venue+arXiv summed]" if e.get("note") else ""))
        res[cid] = e
    if not a.dry:
        json.dump(dict(sorted(res.items())), open(OUT, "w"), indent=1, ensure_ascii=False); open(OUT, "a").write("\n")
    print(f"{len(res)} cards with counts; problems: {problems}")

if __name__ == "__main__": main()
