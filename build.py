#!/usr/bin/env python3
"""RecArch static site generator. Usage: python3 build.py   (env SITE_URL=https://example.com for canonical/sitemap URLs)"""
import glob, html, json, os, re, shutil, sys, datetime
import yaml
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "dist")
SITE_URL = os.environ.get("SITE_URL", "https://recarch.example").rstrip("/")  # TODO: set real domain at launch
E = html.escape

PARADIGMS = ["two-tower","dlrm","sequential-transformer","generative-retrieval","semantic-id","llm-based","foundation-model",
 "graph-neural-network","random-walk","attention-ctr","learning-to-rank","gbdt","item-cf","embedding-based-retrieval","multi-task","online-training","rl-alignment"]
STAGES = ["retrieval","pre-rank","rank","re-rank","single-stage","other"]
TYPES = ["recommendation","search","ads","training_infrastructure","reference_architecture","research"]
EVID = {"production_described":"Production described","open_source_reference":"Open-source reference","research_only":"Research only"}
STATUSES = ("active", "superseded", "retired")   # card lifecycle, see schema/schema.md "Status"
CODE_STATUS = {"official_full":"Full official code","official_partial":"Partial official code","third_party_only":"Third-party code only","none":"No code found"}
CODE_CHIPS = {"official":"Has official code","official_full":"Official: full","official_partial":"Official: partial","third_party_only":"Third-party only","none":"No code found"}
SRC_TYPES = ["paper","engineering_blog","documentation","source_code","press"]
REQ = ["id","name","company","surface","year","system_type","evidence_level","summary","paradigms","stages","id_tokenization",
       "features_signals","training","serving_infra","scale","results_reported","caveats","unknown_fields","sources","code",
       "tldr","era","era_reason","first_public","venue","venue_year","published_version_checked","primary_source","added_on","last_verified"]
# era = dominant modelling paradigm (see schema/schema.md). Year is only a sanity bound: (min_year, max_year) of first public disclosure.
ERA_BOUNDS = {"classic":(1990,2017),"deep":(2016,2100),"generative":(2023,2100)}

TAXONOMY = {}
def load_taxonomy():
    """data/taxonomy.yaml: paradigm families and stage groups for the home filters. Every tag/stage must map to exactly one group."""
    t = yaml.safe_load(open(os.path.join(ROOT, "data/taxonomy.yaml"))); errs = []
    seen = {}
    for f in t["paradigm_families"]:
        for tag in f["tags"]:
            if tag not in PARADIGMS: errs.append(f"taxonomy: family {f['id']} lists unknown tag {tag}")
            if tag in seen: errs.append(f"taxonomy: tag {tag} in two families ({seen[tag]}, {f['id']})")
            seen[tag] = f["id"]
    for tag in PARADIGMS:
        if tag not in seen: errs.append(f"taxonomy: paradigm tag {tag} is not mapped to any family")
    sg = {}
    for g in t["stage_groups"]:
        for st in g["stages"]:
            if st not in STAGES: errs.append(f"taxonomy: stage group {g['id']} lists unknown stage {st}")
            if st in sg: errs.append(f"taxonomy: stage {st} in two groups")
            sg[st] = g["id"]
    for st in STAGES:
        if st not in sg: errs.append(f"taxonomy: stage {st} is not in any stage group")
    if errs: sys.exit("TAXONOMY ERRORS:\n" + "\n".join(errs))
    t["tag_family"] = seen; t["stage_group"] = sg
    return t

def valid_date(s):
    try: datetime.date.fromisoformat(s); return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s))
    except ValueError: return False

def load_site():
    s = yaml.safe_load(open(os.path.join(ROOT, "data/site.yaml")))
    for e in s.get("events") or []:
        assert valid_date(e["date"]) and e["title"], f"bad site event {e}"
    return s

def load_issues(card_ids):
    """Newsletter issues: data/newsletter/<slug>.yaml (see templates/newsletter_issue.example.yaml)."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/newsletter/*.yaml"))):
        i = yaml.safe_load(open(f)); i["slug"] = os.path.basename(f)[:-5]
        errs = [k for k in ("title", "date", "summary", "body") if not i.get(k)]
        if errs or not valid_date(str(i.get("date"))): sys.exit(f"newsletter {i['slug']}: missing/invalid {errs or 'date'} (date must be a quoted YYYY-MM-DD string)")
        i["date"] = str(i["date"])
        bad = [c for c in i.get("cards") or [] if c not in card_ids]
        if bad: sys.exit(f"newsletter {i['slug']}: unknown card ids {bad}")
        out.append(i)
    return sorted(out, key=lambda i: i["date"], reverse=True)

def card_status(c): return c.get("status") or "active"
def is_active(c): return card_status(c) == "active"

def load_cards():
    cards, errs = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/systems/*.yaml"))):
        c = yaml.safe_load(open(f))
        n = os.path.basename(f)
        for k in REQ:
            if k not in c: errs.append(f"{n}: missing {k}")
        if c.get("id") != n[:-5]: errs.append(f"{n}: id must equal filename")
        if c.get("evidence_level") not in EVID: errs.append(f"{n}: bad evidence_level")
        if c.get("system_type") not in TYPES: errs.append(f"{n}: bad system_type")
        for p in c.get("paradigms", []):
            if p not in PARADIGMS: errs.append(f"{n}: unknown paradigm {p}")
        for s in c.get("stages", []):
            if s.get("stage") not in STAGES: errs.append(f"{n}: unknown stage {s.get('stage')}")
        if not c.get("sources"): errs.append(f"{n}: needs >=1 source")
        for s in c.get("sources", []):
            if not str(s.get("url","")).startswith("https://") or not s.get("title"): errs.append(f"{n}: bad source {s}")
            if s.get("type") not in SRC_TYPES: errs.append(f"{n}: bad source type {s.get('type')}")
        cd = c.get("code") or {}
        st = cd.get("status")
        if st not in CODE_STATUS: errs.append(f"{n}: bad code.status {st}")
        repos = cd.get("repos") or []
        for r in repos:
            if not str(r.get("url","")).startswith("https://github.com/") or not r.get("owner") or not r.get("note") or not isinstance(r.get("official"), bool):
                errs.append(f"{n}: bad code repo {r.get('url')}")
        offs = [r for r in repos if r.get("official") is True]
        if st in ("official_full","official_partial") and not offs: errs.append(f"{n}: {st} needs >=1 official repo")
        if st == "third_party_only" and (not repos or offs): errs.append(f"{n}: third_party_only needs repos, all official=false")
        if st == "none" and repos: errs.append(f"{n}: status none must have no repos")
        tl = c.get("tldr")
        if not (isinstance(tl, str) and tl.strip()): errs.append(f"{n}: tldr required (non-empty string)")
        elif len(tl) > 200: errs.append(f"{n}: tldr is {len(tl)} chars, max 200")
        e = c.get("era")
        if e not in ERA_BOUNDS: errs.append(f"{n}: bad era {e}")
        elif isinstance(c.get("year"), int) and not (ERA_BOUNDS[e][0] <= c["year"] <= ERA_BOUNDS[e][1]): errs.append(f"{n}: era {e} implausible for year {c['year']}")
        if not str(c.get("era_reason","")).strip(): errs.append(f"{n}: era_reason required")
        fp = str(c.get("first_public",""))
        if not re.fullmatch(r"(19|20)\d\d-(0[1-9]|1[0-2])", fp): errs.append(f"{n}: first_public must be YYYY-MM")
        elif int(fp[:4]) != c.get("year"): errs.append(f"{n}: year {c.get('year')} != first_public year {fp[:4]} (year = year of first public disclosure)")
        if c.get("venue") is None:
            if c.get("venue_year") is not None or c.get("published_version_checked") is not None: errs.append(f"{n}: venue null requires venue_year and published_version_checked null")
        else:
            if not isinstance(c.get("venue_year"), int): errs.append(f"{n}: venue_year must be int")
            if not isinstance(c.get("published_version_checked"), bool): errs.append(f"{n}: published_version_checked must be bool when venue set")
        if "deployed_year" in c and not isinstance(c["deployed_year"], int): errs.append(f"{n}: deployed_year must be int")
        if c.get("primary_source") not in [s.get("url") for s in c.get("sources", [])]: errs.append(f"{n}: primary_source must equal one sources[].url")
        ao, lv = c.get("added_on"), c.get("last_verified")
        if not (isinstance(ao, str) and isinstance(lv, str) and valid_date(ao) and valid_date(lv)): errs.append(f"{n}: added_on and last_verified must be quoted YYYY-MM-DD strings")
        elif not (ao <= lv <= datetime.date.today().isoformat()): errs.append(f"{n}: need added_on <= last_verified <= today")
        for u in c.get("updates") or []:
            if not (isinstance(u, dict) and isinstance(u.get("date"), str) and valid_date(u["date"]) and str(u.get("note","")).strip()): errs.append(f"{n}: bad updates entry {u}")
            elif not (ao <= u["date"] <= lv): errs.append(f"{n}: update date {u['date']} must lie between added_on and last_verified")
        vs, vl = c.get("version"), c.get("versions")
        if (vs is None) != (vl is None): errs.append(f"{n}: version and versions go together")
        elif vs is not None:
            urls_ = [s_.get("url") for s_ in c.get("sources", [])]
            if not (isinstance(vs, str) and vs.strip()): errs.append(f"{n}: version must be a non-empty string")
            if not (isinstance(vl, list) and len(vl) >= 2): errs.append(f"{n}: versions needs >= 2 entries, oldest first; a single version card omits both fields")
            else:
                for v_ in vl:
                    if not (isinstance(v_, dict) and str(v_.get("name", "")).strip() and re.fullmatch(r"(19|20)\d\d-(0[1-9]|1[0-2])", str(v_.get("first_public", ""))) and v_.get("source") in urls_ and str(v_.get("note", "")).strip()): errs.append(f"{n}: bad versions entry {v_}")
                if all(isinstance(v_, dict) for v_ in vl):
                    if vs not in [v_.get("name") for v_ in vl]: errs.append(f"{n}: version {vs} must name one of the versions entries")
                    if [str(v_.get("first_public")) for v_ in vl] != sorted(str(v_.get("first_public")) for v_ in vl): errs.append(f"{n}: versions must be oldest first")
                    if str(vl[0].get("first_public")) != fp: errs.append(f"{n}: first_public must equal the oldest version's first_public")
                    if vs in [v_.get("name") for v_ in vl] and c.get("primary_source") != next(v_ for v_ in vl if v_.get("name") == vs).get("source"): errs.append(f"{n}: primary_source must be the presented version's source")
        stt = c.get("status", "active")
        if stt not in STATUSES: errs.append(f"{n}: status must be one of {STATUSES}")
        elif stt != "active":
            if not str(c.get("status_reason", "")).strip(): errs.append(f"{n}: status {stt} needs status_reason")
            sd = c.get("status_date")
            if not (isinstance(sd, str) and valid_date(sd) and isinstance(ao, str) and ao <= sd <= datetime.date.today().isoformat()): errs.append(f"{n}: status {stt} needs status_date as quoted YYYY-MM-DD, between added_on and today")
            if stt == "superseded" and (not c.get("superseded_by") or c.get("superseded_by") == c.get("id")): errs.append(f"{n}: superseded needs superseded_by (a card id)")
        elif any(k in c for k in ("status_reason", "status_date", "superseded_by")): errs.append(f"{n}: status_reason, status_date and superseded_by only belong on superseded or retired cards")
        cards.append(c)
    ids_ = {c["id"] for c in cards}
    for c in cards:
        if c.get("superseded_by") and c["superseded_by"] not in ids_: errs.append(f"{c['id']}: superseded_by {c['superseded_by']} is not a card id")
    if errs:
        print("VALIDATION ERRORS:\n" + "\n".join(errs)); sys.exit(1)
    lint_parens(cards)
    return sorted(cards, key=lambda c: (-c["year"], c["name"]))

# ---- style lint: parentheses in displayed text (warnings only, never fails the build) ----
PAREN_FIELDS_SKIP = ("sources.title", "fulltext", "code.repos.owner", "venue", "added_on", "last_verified")
PAREN_MAX_LEN = 40
def _paren_groups(t):
    """Top-level balanced (...) groups of a string, as strings."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(t):
        if ch == "(":
            if depth == 0: start = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0: out.append(t[start:i + 1])
    return out
def _walk_strings(o, path=""):
    if isinstance(o, str): yield path, o
    elif isinstance(o, dict):
        for k, v in o.items(): yield from _walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for v in o: yield from _walk_strings(v, path)
def lint_parens(cards):
    """Warn on: names containing parentheses; displayed strings with >1 parenthetical or a parenthetical >40 chars.
    Skipped: sources[].title (verbatim paper titles), fulltext.* and code.repos.owner (not displayed prose)."""
    w = []
    for c in cards:
        if "(" in str(c.get("name", "")): w.append(f"{c['id']}: name has parentheses: {c['name']!r}")
        for p, t in _walk_strings({k: v for k, v in c.items() if k != "name"}):
            if any(p == k or p.startswith(k + ".") for k in PAREN_FIELDS_SKIP): continue
            g = _paren_groups(t)
            if len(g) > 1: w.append(f"{c['id']}: {p}: {len(g)} parentheticals")
            for x in g:
                if len(x) > PAREN_MAX_LEN: w.append(f"{c['id']}: {p}: parenthetical of {len(x)} chars: {x[:60]}...")
    for x in w: print("STYLE WARNING " + x)
    if w: print(f"STYLE WARNINGS: {len(w)} (parentheses lint, not a failure)")
    return w

ERAS={"classic":"Classic / pre-deep","deep":"Deep-learning era","generative":"Generative / LLM / scaling era"}

def has_official(c): return c["code"]["status"] in ("official_full","official_partial")

def short_company(c): return c["company"].split(" (")[0].split(" /")[0]

def page(title, desc, body, root, path, extra_head="", scripts=""):
    canon = f"{SITE_URL}/{path}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(canon)}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{E(canon)}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/atom+xml" title="RecArch updates" href="{root}feed.xml">
<link rel="stylesheet" href="{root}static/style.css">{extra_head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{root}">Rec<span>Arch</span></a>
<nav><a href="{root}">Systems</a><a href="{root}compare/">Compare</a><a href="{root}changelog/">Changelog</a><a href="{root}newsletter/">Newsletter</a><a href="{root}feed.xml" title="Atom feed">RSS</a><a href="{root}sponsor/">Sponsor</a></nav></div></header>
{body}
<footer class="site"><div class="wrap">RecArch &middot; structured notes on how real companies build recommender, search and ranking systems. Every card cites its public sources; unknowns are marked unknown. <a href="{root}about/">Method</a> &middot; <a href="{root}changelog/">Changelog</a> &middot; <a href="{root}feed.xml">RSS</a></div></footer>
{scripts}<script type="text/javascript" async src="https://subscribe-forms.beehiiv.com/attribution.js"></script></body></html>"""

GLABEL = {"era": "Era", "stage": "Stage", "family": "Paradigm", "paradigm": "Paradigm tag", "evidence": "Evidence"}
def chips(group, values, labels=None):
    out = f'<div class="group" data-group="{group}"><b>{GLABEL.get(group, group)}</b>'
    for v in values:
        out += f'<button class="chip" type="button" data-v="{E(v)}" aria-pressed="false">{E((labels or {}).get(v, v))}</button>'
    return out + "</div>"

def code_badge(c):
    s = c["code"]["status"]
    return "" if s == "none" else f' <span class="badge b-code-{E(s)}">{E(CODE_STATUS[s])}</span>'

def card_attrs(c):
    """data-* attributes shared by list cards and timeline items; app.js filters on these."""
    stages = sorted({TAXONOMY["stage_group"][s["stage"]] for s in c["stages"]})
    fams = sorted({TAXONOMY["tag_family"][p] for p in c["paradigms"]})
    search = " ".join([c["name"], c["company"], c["summary"]]).lower()
    return (f'data-id="{E(c["id"])}" data-paradigms="{E("|".join(c["paradigms"]))}" data-families="{E("|".join(fams))}" data-stages="{E("|".join(stages))}" '
            f'data-evidence="{E(c["evidence_level"])}" data-prod="{int(c["evidence_level"] == "production_described")}" data-official="{int(has_official(c))}" '
            f'data-era="{c["era"]}" data-search="{E(search)}"' + (f' data-cites="{CITES[c["id"]]["count"]}"' if c["id"] in CITES else ""))

def card_html(c, root):
    tags = "".join(f'<span class="tag">{E(p)}</span>' for p in c["paradigms"])
    stages = sorted({s["stage"] for s in c["stages"]})
    st = "".join(f'<span class="tag stage">{E(s)}</span>' for s in stages)
    return f"""<div class="card era-{c['era']}" {card_attrs(c)}>
<div class="co">{E(c['company'])} &middot; {c['year']}</div>
<h3><a href="{root}systems/{E(c['id'])}/">{E(c['name'])}</a></h3>
<div><span class="badge b-{E(c['evidence_level'])}">{E(EVID[c['evidence_level']])}</span>{code_badge(c)}</div>
<p>{E(c['tldr'].strip())}</p>
<div class="tags">{tags}</div><div class="tags">{st}</div>
<div class="foot"><span>{len(c['sources'])} source{'s' if len(c['sources'])!=1 else ''}{f' &middot; {CITES[c["id"]]["count"]:,} citations' if c["id"] in CITES else ''}</span><label><input type="checkbox" class="cmp"> Compare</label></div></div>"""

def timeline_html(cards, root):
    """Year rows x three era columns. Items carry the same data-* attributes as the list cards so one filter drives both views."""
    years = sorted({c["year"] for c in cards})
    head = "".join(f'<div class="tl-h era-{k}">{E(v)}</div>' for k, v in ERAS.items())
    rows = ""
    for y in years:
        cols = ""
        for k in ERAS:
            its = sorted([c for c in cards if c["year"] == y and c["era"] == k], key=lambda c: (c["first_public"], c["name"]))
            cols += f'<div class="tl-cell era-{k}" data-label="{E(ERAS[k])}">' + "".join(
                f'<a class="tl-item era-{k}" href="{root}systems/{E(c["id"])}/" {card_attrs(c)}><span class="tl-m">{E(c["first_public"])}</span> <b>{E(c["name"])}</b><span class="tl-co">{E(short_company(c))}</span></a>' for c in its) + "</div>"
        rows += f'<div class="tl-row" data-year="{y}"><div class="tl-y">{y}</div>{cols}</div>'
    return f'<div class="timeline" id="timeline" hidden><div class="tl-head"><div class="tl-y"></div>{head}</div>{rows}<p class="unk tl-note">Ordered by first public disclosure (year = arXiv v1, blog or venue date). Columns are eras by dominant paradigm, so a year can hold systems from different eras.</p></div>'

SITE = {}
SUB_COPY = "One email a week: new industrial recsys systems, read in full so you don't have to."

def subscribe_box(source, heading="Get the weekly RecArch digest", compact=False):
    """Real Beehiiv embed (form id in data/site.yaml). The loader script renders the form in place; attribution.js (in page())
    forwards UTM params. noscript / no-JS fallback is the hosted subscribe page. `source` is not sent (the embed has no hidden fields);
    attribution comes from Beehiiv's own referrer/UTM capture."""
    nl = SITE.get("newsletter") or {}
    form_id = str(nl.get("form_id") or "")
    pub = str(nl.get("public_url") or "https://recarch.beehiiv.com").rstrip("/")
    loader = str(nl.get("embed_url") or "https://subscribe-forms.beehiiv.com/v3/loader.js")
    return f"""<div class="nlband{' compact' if compact else ''}" data-source="{E(source)}"><h2>{E(heading)}</h2><p>{E(SUB_COPY)}</p>
<div class="nl-embed"><script async src="{E(loader)}" data-beehiiv-form="{E(form_id)}"></script>
<noscript><p><a class="btn" href="{E(pub)}/subscribe">Subscribe on Beehiiv</a></p></noscript></div>
<p class="sub-fine">Free. Unsubscribe any time. <a href="{E(pub)}/subscribe">Subscribe on Beehiiv</a> &middot; <a href="{{ROOT}}feed.xml">Prefer RSS?</a></p></div>"""

def events(cards, site, issues, off=()):
    """Every dated change on the site, newest first. kind: added | updated | site | issue."""
    ev = []
    for c in cards:
        ev.append({"date": c["added_on"], "kind": "added", "title": c["name"], "note": f"{c['company']} \u00b7 {c['surface']}", "path": f"systems/{c['id']}/", "key": f"added:{c['id']}", "summary": c["summary"].strip()})
        for n, u in enumerate(c.get("updates") or []):
            ev.append({"date": u["date"], "kind": "updated", "title": c["name"], "note": u["note"], "path": f"systems/{c['id']}/", "key": f"update:{c['id']}:{n}", "summary": u["note"]})
    for c in off:   # retired or superseded cards: their added/updated events are dropped, one status event stays
        word = "Retired" if card_status(c) == "retired" else "Superseded"
        ev.append({"date": c["status_date"], "kind": "retired", "title": c["name"], "note": f"{word}: {c['status_reason'].strip()}", "path": f"systems/{c.get('superseded_by') or c['id']}/", "key": f"status:{c['id']}", "summary": f"{word}: {c['status_reason'].strip()}"})
    for n, e in enumerate(site.get("events") or []):
        ev.append({"date": e["date"], "kind": "site", "title": e["title"], "note": e.get("note", ""), "path": "changelog/", "key": f"site:{n}", "summary": e.get("note", "")})
    for i in issues:
        ev.append({"date": i["date"], "kind": "issue", "title": i["title"], "note": i["summary"], "path": f"newsletter/{i['slug']}/", "key": f"issue:{i['slug']}", "summary": i["summary"]})
    order = {"issue": 0, "site": 1, "retired": 2, "updated": 3, "added": 4}
    return sorted(ev, key=lambda e: (e["date"], -order[e["kind"]], e["title"]), reverse=True)

KIND_LABEL = {"added": "Added", "updated": "Updated", "site": "Site", "issue": "Newsletter", "retired": "Retired"}

def rel_date(d, today):
    n = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(d)).days
    return "today" if n <= 0 else "yesterday" if n == 1 else f"{n} days ago"

def carousel_select(cards, today, size=6, window=7):
    """Home carousel. Activity date = max(added_on, latest updates[].date). Cards active within `window` days of `today`
    come first, newest first; if fewer than `size`, the most recently active other cards backfill. Ties: updated before added, then id."""
    t = datetime.date.fromisoformat(today); items = []
    for c in cards:
        if not is_active(c): continue
        ups = c.get("updates") or []
        last = max(ups, key=lambda u: u["date"]) if ups else None
        if last and last["date"] > c["added_on"]: kind, date, note = "updated", last["date"], last["note"]
        else: kind, date, note = "added", c["added_on"], None
        recent = (t - datetime.date.fromisoformat(date)).days < window
        items.append({"card": c, "kind": kind, "date": date, "note": note, "recent": recent})
    items.sort(key=lambda x: (x["date"], x["kind"] == "updated", x["card"]["id"]), reverse=True)
    return items[:size]

def strip(ev, root, today, cards=None):
    """Home carousel of recently added/updated cards (replaces the old text list). Pure HTML; static/carousel.js adds the behaviour."""
    size = int((SITE or {}).get("carousel_size", 6)); window = int((SITE or {}).get("carousel_window_days", 7))
    week = [e for e in ev if (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(e["date"])).days < window and e["kind"] in ("added", "updated")]
    na = sum(1 for e in week if e["kind"] == "added"); nu = sum(1 for e in week if e["kind"] == "updated")
    pill = f'<span class="pill">This week: {na} added, {nu} updated</span>' if week else '<span class="pill quiet">Nothing new this week</span>'
    sel = carousel_select(cards or [], today, size, window); n = len(sel)
    slides = ""
    for i, it in enumerate(sel):
        c = it["card"]
        note = f'<p class="slide-note"><b>Update:</b> {E(it["note"])}</p>' if it["note"] else ""
        slides += f"""<article class="slide era-{c['era']}" role="group" aria-roledescription="slide" aria-label="{i + 1} of {n}" data-i="{i}" data-id="{E(c['id'])}"><div class="slide-meta"><span class="era-badge era-{c['era']}">{E(ERAS[c['era']])}</span><span class="k k-{it['kind']}">{KIND_LABEL[it['kind']]}</span><time datetime="{it['date']}" data-date="{it['date']}">{rel_date(it['date'], today)}</time></div>
<h3><a href="{root}systems/{E(c['id'])}/">{E(c['name'])}</a></h3><div class="co">{E(c['company'])}</div><p class="slide-tldr">{E(c['tldr'].strip())}</p>{note}<a class="slide-more" href="{root}systems/{E(c['id'])}/">Read the card &rarr;</a></article>"""
    dots = "".join(f'<button type="button" class="dot" data-go="{i}" aria-label="Go to slide {i + 1}" aria-current="{"true" if i == 0 else "false"}"></button>' for i in range(n))
    return f"""<section class="carousel" aria-roledescription="carousel" aria-label="Recently added and updated systems" data-autoplay="5000" data-count="{n}"><div class="car-h"><h2>Recently added &amp; updated</h2>{pill}<span class="strip-links"><a href="{root}changelog/">Full changelog</a> &middot; <a href="{root}feed.xml">RSS</a></span></div>
<div class="car-body"><button type="button" class="car-btn car-prev" aria-label="Previous slide">&#8249;</button><div class="car-view" tabindex="0" aria-live="off"><div class="car-track">{slides}</div></div><button type="button" class="car-btn car-next" aria-label="Next slide">&#8250;</button></div>
<div class="car-foot"><div class="car-dots">{dots}</div><button type="button" class="car-pause" aria-pressed="false">Pause</button></div></section>"""

def changelog_page(ev):
    root = "../"; by = {}
    for e in ev: by.setdefault(e["date"], []).append(e)
    sec = ""
    for d, items in by.items():
        lis = "".join(f'<li><span class="k k-{e["kind"]}">{KIND_LABEL[e["kind"]]}</span> <a href="{root}{E(e["path"])}">{E(e["title"])}</a><div class="unk" style="font-style:normal">{E(e["note"])}</div></li>' for e in items)
        sec += f'<section class="blk"><h2><time datetime="{d}">{d}</time></h2><ul class="clean changelog">{lis}</ul></section>'
    body = f"""<div class="wrap"><article class="sys"><h1>Changelog</h1><p class="lead">Every system card added or updated, by date. Each card page shows its own &ldquo;Added&rdquo; and &ldquo;Last verified&rdquo; dates. Follow along by <a href="{root}feed.xml">RSS / Atom</a> or the <a href="{root}newsletter/">weekly digest</a>.</p>
{sec}{subscribe_box("changelog").replace("{ROOT}", root)}</article></div>"""
    return page("Changelog | RecArch", "What was added or updated on RecArch, by date: new industrial recommender system cards, corrections and re-verifications.", body, root, "changelog/")

def feed_xml(ev):
    def ts(d): return f"{d}T00:00:00+08:00"   # dates are day-precision; Asia/Shanghai
    top = ev[:100]
    upd = ts(top[0]["date"]) if top else ts(datetime.date.today().isoformat())
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
           f'<title>RecArch: new and updated recommender system cards</title><subtitle>Industrial recsys, search and ads architectures, read in full. Card additions, updates and weekly digest issues.</subtitle>',
           f'<id>{SITE_URL}/</id><link rel="self" type="application/atom+xml" href="{SITE_URL}/feed.xml"/><link rel="alternate" type="text/html" href="{SITE_URL}/"/><updated>{upd}</updated>',
           '<author><name>RecArch</name></author>']
    for e in top:
        label = {"added": "New system", "updated": "Updated", "site": "Site", "issue": "Newsletter", "retired": "Retired"}[e["kind"]]
        out.append(f'<entry><title>{E(label)}: {E(e["title"])}</title><id>tag:{SITE_URL.split("//")[-1]},{e["date"]}:{E(e["key"])}</id><link rel="alternate" type="text/html" href="{SITE_URL}/{E(e["path"])}"/><updated>{ts(e["date"])}</updated><category term="{e["kind"]}"/><summary>{E(e["summary"][:600])}</summary></entry>')
    return "\n".join(out) + "\n</feed>\n"

def md_paras(s):
    return "".join(f"<p>{E(p.strip())}</p>" for p in str(s).strip().split("\n\n") if p.strip())

def newsletter_page(issues, cards):
    root = "../"
    if issues:
        lis = "".join(f'<li><time datetime="{E(i["date"])}">{E(i["date"])}</time> <a href="{root}newsletter/{E(i["slug"])}/">{E(i["title"])}</a><div class="unk" style="font-style:normal">{E(i["summary"])}</div></li>' for i in issues)
        arch = f'<section class="blk"><h2>Issues</h2><ul class="clean changelog">{lis}</ul></section>'
    else:
        arch = '<section class="blk"><h2>Issues</h2><p class="unk">No issues yet. Issue #1 is in preparation; every issue will be published here as its own page and announced in the <a href="../feed.xml">feed</a>.</p></section>'
    body = f"""<div class="wrap"><article class="sys"><h1>The RecArch weekly digest</h1><p class="lead">{E(SUB_COPY)} Newly added system cards, notable papers and engineering posts from industrial recsys teams, with the structured fields pulled out for you.</p>
{subscribe_box("newsletter")}<p class="sub-fine">Past issues also live on <a href="{E(str((SITE.get('newsletter') or {}).get('public_url') or 'https://recarch.beehiiv.com'))}">recarch.beehiiv.com</a>.</p>{arch}</article></div>""".replace("{ROOT}", root)
    return page("Newsletter | RecArch", "Weekly digest of new industrial recommender system cards and papers. Archive of past issues; subscribe by email or RSS.", body, root, "newsletter/")

def issue_page(i, by_id):
    root = "../../"
    cs = "".join(f'<li><a href="{root}systems/{E(c)}/">{E(by_id[c]["name"])}</a> <span class="unk">{E(by_id[c]["company"])}, {by_id[c]["year"]}</span></li>' for c in i.get("cards") or [])
    ps = "".join(f'<li><a href="{E(p["url"])}" rel="noopener nofollow" target="_blank">{E(p["title"])}</a>' + (f' <span class="unk">&mdash; {E(p["note"])}</span>' if p.get("note") else "") + "</li>" for p in i.get("papers") or [])
    body = f"""<div class="wrap"><article class="sys"><div class="crumbs"><a href="{root}newsletter/">Newsletter</a> / {E(i['date'])}</div><h1>{E(i['title'])}</h1><p class="lead">{E(i['summary'])}</p>
<section class="blk">{md_paras(i['body'])}</section>
{f'<section class="blk"><h2>Systems covered</h2><ul class="clean">{cs}</ul></section>' if cs else ''}{f'<section class="blk"><h2>Papers and posts</h2><ul class="clean">{ps}</ul></section>' if ps else ''}
{subscribe_box("issue:" + i["slug"], "Get the next issue by email").replace("{ROOT}", root)}</article></div>"""
    return page(f"{i['title']} | RecArch newsletter", i["summary"][:158], body, root, f"newsletter/{i['slug']}/")

def archive_html(off, root):
    """Small archive of retired and superseded cards: kept at their URL, not counted, not in the sitemap."""
    if not off: return ""
    lis = "".join(f'<li><a href="{root}systems/{E(c["id"])}/">{E(c["name"])}</a> <span class="unk">{E(short_company(c))}, {c["year"]}, {card_status(c)} {E(c["status_date"])}</span><div class="stage-d">{E(c["status_reason"].strip())}</div></li>' for c in sorted(off, key=lambda c: (c["status_date"], c["name"]), reverse=True))
    return f'<details class="archive" id="archive"><summary>Archive: {len(off)} retired or superseded cards, not counted above</summary><ul class="clean">{lis}</ul></details>'

def home(cards, ev=(), today="", off=()):
    root = ""
    cards = [c for c in cards if is_active(c)]
    n = len(cards)
    used_p = [p for p in PARADIGMS if any(p in c["paradigms"] for c in cards)]
    fam = TAXONOMY["paradigm_families"]; sg = TAXONOMY["stage_groups"]
    fam_labels = {f["id"]: f["label"] for f in fam}; sg_labels = {g["id"]: g["label"] for g in sg}
    body = f"""<div class="wrap"><section class="hero"><div class="hero-l"><h1>The atlas of recommender system architecture.</h1>
<p>A living map of industrial recommender architecture, tracking every shift as it happens.</p></div>
<div class="hero-r">{subscribe_box("home", "Get the weekly RecArch digest", compact=True).replace("{ROOT}", root)}</div></section>
{strip(ev, root, today, cards)}
<section class="filters" aria-label="Filters"><input id="q" class="search" type="search" placeholder="Search by name, company or summary&hellip;" aria-label="Search systems">
{chips("era", list(ERAS), ERAS)}{chips("stage", [g["id"] for g in sg], sg_labels)}{chips("family", [f["id"] for f in fam], fam_labels)}
<div class="toggles"><label class="tog"><input type="checkbox" id="f-prod"> Production-deployed only</label><label class="tog"><input type="checkbox" id="f-official"> Has official code</label></div>
<details id="more"><summary>More filters</summary>{chips("paradigm", used_p)}{chips("evidence", list(EVID), EVID)}</details></section>
<div class="meta-row"><span id="count" role="status" aria-live="polite">{n} systems</span><button id="reset" class="linkbtn" type="button">Clear all</button>
<label class="sortl" id="sortwrap">Sort <select id="sort" aria-label="Sort systems"><option value="default">Default</option><option value="cites">Most cited</option></select></label>
<div class="seg" role="group" aria-label="View"><button type="button" data-view="list" aria-pressed="true">List</button><button type="button" data-view="timeline" aria-pressed="false">Timeline</button></div></div>
<div class="grid" id="grid">{"".join(card_html(c, root) for c in cards)}</div>
{timeline_html(cards, root)}
<div id="empty" class="panel" hidden>No systems match. Try fewer filters or <button class="linkbtn" type="button" id="reset2">clear all</button>.</div>
{archive_html(off, root)}</div>
<div class="cmpbar" id="cmpbar"><span id="cmpn"></span><a id="cmplink" href="compare/">Compare</a></div>"""
    return page("RecArch - The atlas of recommender system architecture",
        "A living map of industrial recommender system architecture, with sourced cards on how companies build recommenders and every shift from collaborative filtering to generative recommendation.",
        body, root, "", scripts=f'<script src="{root}static/carousel.js"></script><script src="{root}static/app.js"></script>')

def kv(label, val):
    return f'<div class="fact"><small>{E(label)}</small>{val}</div>'


# ---- diagrams: data/diagrams/<id>.yaml -> inline SVG (one house style: inputs -> core -> outputs) ----
DIAGRAMS = {}
CITES = {}   # card id -> {count, source, source_url, fetched_on, ...} from data/citations.json (generated by scripts/citations.py)
BOX_W, GAP_X, PAD_X, TOP, LH = 144, 52, 16, 34, 16
KIND_STYLE = {"input": ("#f4f4f5", "#d4d4d8", "#18181b"), "module": ("#eef2ff", "#a5b4fc", "#312e81"), "output": ("#ecfdf5", "#6ee7b7", "#064e3b")}

def _wrap(t, n):
    import textwrap
    return textwrap.wrap(t, n, break_long_words=False) or [""]

def load_citations(cards):
    p = os.path.join(ROOT, "data", "citations.json")
    if not os.path.exists(p): return {}
    d = json.load(open(p)); ids = {c["id"] for c in cards}
    for k, v in d.items():
        if k not in ids: sys.exit(f"citations.json: unknown card {k}")
        if not (isinstance(v.get("count"), int) and v["count"] >= 0 and v.get("source") in ("Semantic Scholar", "OpenAlex") and v.get("source_url", "").startswith("https://") and valid_date(v.get("fetched_on", ""))):
            sys.exit(f"citations.json: bad entry for {k}: {v}")
        pp = v.get("papers")   # uniform: one row per version for merged cards, one row for every other card; count is their sum
        if not (isinstance(pp, list) and pp and all(isinstance(x, dict) and isinstance(x.get("count"), int) and x["count"] >= 0 and str(x.get("name", "")).strip() for x in pp)): sys.exit(f"citations.json: {k} needs a papers list with name and count per row")
        if sum(x["count"] for x in pp) != v["count"]: sys.exit(f"citations.json: {k} count {v['count']} is not the sum of its papers {[x['count'] for x in pp]}")
        cv = next((c for c in cards if c["id"] == k), None)
        if cv and cv.get("versions") and [x["name"] for x in pp] != [x["name"] for x in cv["versions"]] and sorted(x["name"] for x in pp) != sorted(x["name"] for x in cv["versions"]): sys.exit(f"citations.json: {k} papers must have one row per version")
    return d

def cite_html(i):
    v = CITES.get(i)
    if not v: return ""   # no paper or no lookup: show nothing, never 0
    n = f'{v["count"]:,}'; note = f' <span class="cite-note">{E(v["note"])}</span>' if v.get("note") else ""
    nv = len(v["papers"]) if len(v["papers"]) > 1 else 0
    tot = f' in total across the papers of all {nv} versions,' if nv else ""
    return f'<p class="cites">Cited by <b>{n}</b>{tot} per <a href="{E(v["source_url"])}" rel="noopener nofollow" target="_blank">{E(v["source"])}</a>, as of <time datetime="{v["fetched_on"]}">{v["fetched_on"]}</time>{note}</p>'

def vcount(i, name):
    """Small per-version citation breakdown for the version list on merged cards. Empty when there is no count."""
    v = CITES.get(i); row = next((x for x in (v or {}).get("papers", []) if x["name"] == name), None) if v and len(v.get("papers", [])) > 1 else None
    return f' <span class="cite-note">{row["count"]:,} citations</span>' if row else ""

def load_diagrams(cards):
    out = {}
    d = os.path.join(ROOT, "data", "diagrams")
    ids = {c["id"]: c for c in cards}
    for f in sorted(glob.glob(os.path.join(d, "*.yaml"))):
        i = os.path.basename(f)[:-5]; g = yaml.safe_load(open(f)); errs = []
        if i not in ids: sys.exit(f"diagram {i}: no such card")
        cap = g.get("caption") or {}
        for k in ("fig", "work", "url"):
            if not cap.get(k): errs.append(f"caption.{k} missing")
        if cap.get("url") and cap["url"] not in [s["url"] for s in ids[i]["sources"]]: errs.append("caption.url must be one of the card's sources[].url")
        bx = {b["id"]: b for col in g["columns"] for b in col["boxes"]}
        for b in bx.values():
            if b.get("kind") not in KIND_STYLE: errs.append(f"box {b.get('id')}: kind must be one of {list(KIND_STYLE)}")
        for a, b in g["edges"]:
            if a not in bx or b not in bx: errs.append(f"edge {a}->{b}: unknown box")
        if not g.get("alt"): errs.append("alt text missing")
        if errs: sys.exit(f"DIAGRAM ERRORS {i}: " + "; ".join(errs))
        out[i] = g
    return out

def diagram_svg(g):
    cols = g["columns"]; lay = {}
    def lines(b):
        t = b["text"]; res = [(l, True) for l in _wrap(t[0], 17)]
        for x in t[1:]: res += [(l, False) for l in _wrap(x, 21)]
        return res
    heights = []
    for col in cols:
        h = 0
        for b in col["boxes"]:
            b["_lines"] = lines(b); b["_h"] = 22 + LH * len(b["_lines"]); h += b["_h"]
        h += 18 * (len(col["boxes"]) - 1); heights.append(h)
    H = max(heights); W = PAD_X * 2 + BOX_W * len(cols) + GAP_X * (len(cols) - 1); full = TOP + H + 16
    parts = []
    for ci, col in enumerate(cols):
        x = PAD_X + ci * (BOX_W + GAP_X); y = TOP + (H - heights[ci]) / 2
        parts.append(f'<text x="{x + BOX_W / 2}" y="18" text-anchor="middle" class="dg-col">{E(col["label"].upper())}</text>')
        for b in col["boxes"]:
            fill, stroke, ink = KIND_STYLE[b["kind"]]
            lay[b["id"]] = (x, y, BOX_W, b["_h"], ci)
            t = f'<rect x="{x}" y="{y:.1f}" width="{BOX_W}" height="{b["_h"]}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
            ty = y + 11 + 12
            for ln, bold in b["_lines"]:
                t += f'<text x="{x + BOX_W / 2}" y="{ty:.1f}" text-anchor="middle" class="{"dg-t" if bold else "dg-s"}" fill="{ink if bold else "#52525b"}">{E(ln.replace("->", "→"))}</text>'; ty += LH
            parts.append(t); y += b["_h"] + 18
    edges = ""
    for a, b in g["edges"]:
        ax, ay, aw, ah, ac = lay[a]; bx_, by, bw, bh, bc = lay[b]
        if ac == bc:
            x1 = ax + aw / 2; y1 = ay + ah; y2 = by if by > ay else by + bh
            edges += f'<path d="M{x1} {y1:.1f} L{x1} {y2 - (6 if by > ay else -6):.1f}" class="dg-e" marker-end="url(#dg-ar)"/>'
        else:
            x1 = ax + aw; y1 = ay + ah / 2; x2 = bx_ - 2; y2 = by + bh / 2; mx = (x1 + x2) / 2
            edges += f'<path d="M{x1} {y1:.1f} C{mx} {y1:.1f} {mx} {y2:.1f} {x2} {y2:.1f}" class="dg-e" marker-end="url(#dg-ar)"/>'
    defs = '<defs><marker id="dg-ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#6366f1"/></marker></defs>'
    style = '<style>.dg-col{font:700 10.5px sans-serif;letter-spacing:.08em;fill:#71717a}.dg-t{font:700 12.5px sans-serif}.dg-s{font:12px sans-serif}.dg-e{fill:none;stroke:#6366f1;stroke-width:1.6}</style>'
    return f'viewBox="0 0 {W} {full:.0f}"', W, f'{defs}{style}{edges}{"".join(parts)}'

def diagram_html(i, g):
    vb, w, inner = diagram_svg(g); cap = g["caption"]
    return (f'<figure class="diagram"><div class="dg-scroll"><svg xmlns="http://www.w3.org/2000/svg" {vb} width="{w}" role="img" aria-label="{E(g["alt"])}" class="dg">{inner}</svg></div>'
            f'<figcaption>Redrawn and simplified from {E(cap["fig"])} of <a href="{E(cap["url"])}" rel="noopener nofollow" target="_blank">{E(cap["work"])}</a>.'
            + (f' {E(cap["note"])}' if cap.get("note") else "") + '</figcaption></figure>')

STAGE_LABEL = {"retrieval": "Retrieval", "pre-rank": "Pre-ranking", "rank": "Ranking", "re-rank": "Re-ranking", "single-stage": "Single-stage", "other": "Other"}
V2_KEYS = ("core_idea", "deployed_in", "scale_short", "key_result", "results_table")

def check_v2(cards):
    """Every card has the key-facts fields. key_result and results_table add no number absent from results_reported.
    core_idea, deployed_in and scale_short add no number absent from the card's own results_reported, summary, scale, surface or tldr."""
    errs = []
    tok = lambda t: set(re.findall(r"\d+(?:[.,]\d+)*", str(t).replace(",", "")))
    for c in cards:
        i = c["id"]
        for k in V2_KEYS:
            if not c.get(k): errs.append(f"{i}: needs {k}")
        rt = c.get("results_table") or {}
        rows = [r for g in ("online", "offline", "other") for r in (rt.get(g) or [])]
        if not rows and not str(rt.get("note") or "").strip(): errs.append(f"{i}: results_table needs rows or a note")
        for r in rows:
            for k in ("setting", "method", "metric", "result", "versus"):
                if not str(r.get(k, "")).strip(): errs.append(f"{i}: results_table row missing {k}: {r}")
        rr = tok(c.get("results_reported") or "")
        texts = [("key_result", c.get("key_result") or ""), ("results_table", " ".join(str(v) for r in rows for v in r.values()) + " " + str(rt.get("note") or ""))]
        for label, text in texts:
            extra = tok(text) - rr
            if extra: errs.append(f"{i}: {label} has numbers not in results_reported: {sorted(extra)}")
        pool = tok(" ".join([str(c.get("results_reported") or ""), str(c.get("summary") or ""), str(c.get("surface") or ""), str(c.get("tldr") or ""), json.dumps(c.get("scale") or [])]))
        for label in ("core_idea", "deployed_in", "scale_short"):
            extra = tok(c.get(label) or "") - pool
            if extra: errs.append(f"{i}: {label} has numbers not in the card's own fields: {sorted(extra)}")
    if errs: raise SystemExit("V2 LAYOUT ERRORS:\n  " + "\n  ".join(errs))

def card_page(c):
    """Card detail page. Section order is fixed, the architecture block only when a diagram exists; tests/v2_order.test.js checks it."""
    root = "../../"; cd = c["code"]; st = card_status(c)
    unk = '<span class="unk">unknown, the source does not say</span>'
    ps = next(x for x in c["sources"] if x["url"] == c["primary_source"])
    paper_btn = f'<a class="btn" href="{E(ps["url"])}" rel="noopener nofollow" target="_blank">{"Paper" if ps["type"] == "paper" else "Primary source"}' + (f' <small>{E(c["venue"])}</small>' if c.get("venue") else "") + '</a>'
    off = [r for r in cd["repos"] if r["official"]]
    if off: code_btn = f'<a class="btn btn-code" href="{E(off[0]["url"])}" rel="noopener nofollow" target="_blank">Code <small>official</small></a>'
    elif cd["repos"]: code_btn = f'<a class="btn btn-alt" href="{E(cd["repos"][0]["url"])}" rel="noopener nofollow" target="_blank">Code <small>unofficial</small></a>'
    else: code_btn = '<span class="btn btn-off" aria-disabled="true">No public code found</span>'
    stage_names = []
    for s_ in c["stages"]:
        n_ = STAGE_LABEL.get(s_["stage"], s_["stage"])
        if n_ not in stage_names: stage_names.append(n_)
    stage_badges = "".join(f'<span class="badge b-stage">{E(n_)}</span>' for n_ in stage_names)
    venue = c.get("venue") or "preprint"
    byline = f'{E(c["company"])} &middot; {c["year"]} &middot; {E(venue)}'
    cell = lambda label, val: f'<div class="kf"><small>{label}</small><div>{val}</div></div>'
    code_cell = f'<span class="badge b-code-{E(cd["status"])}">{E(CODE_STATUS[cd["status"]])}</span>'
    has_dg = c["id"] in DIAGRAMS
    toc = ([("architecture", "Architecture")] if has_dg else []) + [("how-it-works", "How it works"), ("results", "Results"), ("details", "Technical details"), ("limitations", "Limitations"), ("sources", "Sources"), ("history", "History")]
    toc_h = '<nav class="toc" aria-label="On this page"><b>On this page</b>' + "".join(f'<a href="#{i}"' + (' onclick="document.getElementById(\'details\').open=true"' if i == "details" else "") + f'>{t}</a>' for i, t in toc) + '</nav>'
    keyfacts = (f'<section class="keyfacts" id="key-facts" style="--kfspan:KFSPAN" aria-labelledby="h-key-facts"><h2 id="h-key-facts">Key facts</h2><div class="kfgrid">'
        + cell("Stage", E(" + ".join(stage_names))) + cell("Core idea", E(c["core_idea"])) + cell("Deployed in", E(c["deployed_in"]))
        + cell("Scale", E(c["scale_short"])) + cell("Headline result", E(c["key_result"])) + cell("Code status", code_cell)
        + f'</div>{toc_h}</section>')
    arch = f'<section class="blk" id="architecture"><h2>Architecture</h2>{diagram_html(c["id"], DIAGRAMS[c["id"]])}</section>' if has_dg else ""
    stages = "".join(f'<div class="stagebox"><b>{E(STAGE_LABEL.get(s_["stage"], s_["stage"]))}</b><div>{E(s_.get("model_family") or "unknown")}</div><div class="stage-d">{E((s_.get("details") or "").strip())}</div></div>' for s_ in c["stages"])
    rt = c["results_table"]
    def rows(kind, label):
        r_ = rt.get(kind) or []
        if not r_: return ""
        return f'<tbody><tr class="grp"><th colspan="5">{label}</th></tr>' + "".join(f'<tr><td>{E(r["setting"])}</td><td>{E(r["method"])}</td><td>{E(r["metric"])}</td><td class="num"><b>{E(r["result"])}</b></td><td>{E(r["versus"])}</td></tr>' for r in r_) + '</tbody>'
    table = (f'<div class="tbl-scroll"><table class="cmp restab"><thead><tr><th>Setting</th><th>Method</th><th>Metric</th><th>Result</th><th>Compared with</th></tr></thead>'
             + rows("online", "Online") + rows("offline", "Offline") + rows("other", "Reported, type not stated") + '</table></div>') if any(rt.get(g) for g in ("online", "offline", "other")) else ""
    note = f'<p class="stage-d">{E(rt["note"])}</p>' if rt.get("note") else ""
    idt = c["id_tokenization"]
    idh = f'<p>{E(idt.get("approach") or "") or unk}</p>' + (f'<p class="stage-d">{E(idt["details"])}</p>' if idt.get("details") else "")
    tr = c["training"]
    trh = f'<ul class="clean"><li><b>Mode:</b> {E(tr.get("mode") or "unknown")}</li><li><b>Objectives:</b> {E(", ".join(tr.get("objectives") or []) or "unknown")}</li>' + (f'<li>{E(tr["notes"])}</li>' if tr.get("notes") else "") + "</ul>"
    feats = "<ul class='clean'>" + "".join(f"<li>{E(f)}</li>" for f in c["features_signals"]) + "</ul>" if c["features_signals"] else unk
    sc = "<ul class='clean'>" + "".join(f'<li><b>{E(s_["metric"])}:</b> {E(str(s_["value"]))}</li>' for s_ in c["scale"]) + "</ul>" if c["scale"] else ""
    serving = f'<p>{E(c["serving_infra"]) if c["serving_infra"] else unk}</p>' + sc
    details = (f'<details id="details" class="tech"><summary><h2 id="h-details">Technical details</h2></summary>'
        f'<h3>Features &amp; signals</h3>{feats}<h3>Training</h3>{trh}<h3>Serving &amp; infra</h3>{serving}<h3>ID / tokenization</h3>{idh}</details>')
    lim_items = [E(x) for x in c["caveats"]] + ([E(c["version_note"])] if c.get("version_note") else []) + ([f'<span class="unk">Not stated in the sources: {E(", ".join(c["unknown_fields"]))}.</span>'] if c["unknown_fields"] else [])
    limits = f'<section class="blk" id="limitations"><h2>Limitations</h2><div class="caveat"><ul class="clean">{"".join(f"<li>{x}</li>" for x in lim_items)}</ul></div></section>' if lim_items else ""
    earlier = {v_["source"]: v_["name"] for v_ in (c.get("versions") or []) if v_["name"] != c.get("version")}
    srcs = "<ul class='clean'>" + "".join(f'<li><a href="{E(s_["url"])}" rel="noopener nofollow" target="_blank">{E(s_["title"])}</a> <span class="tag stage">{E(s_["type"])}</span>' + (f' <span class="tag stage">other version: {E(earlier[s_["url"]])}</span>' if s_["url"] in earlier else "") + '</li>' for s_ in c["sources"]) + "</ul>"
    repos = "".join(f'<li><a href="{E(r["url"])}" rel="noopener nofollow" target="_blank">{E(r["url"][len("https://github.com/"):])}</a> <span class="tag stage">{"official" if r["official"] else "unofficial"}</span><div class="stage-d">{E(r["owner"])}. {E(r["note"])}</div></li>' for r in cd["repos"])
    codeblk = f'<h3>Code</h3><ul class="clean">{repos}</ul>' if repos else f'<h3>Code</h3><p class="unk">{E(cd.get("note") or "No code found.")}</p>'
    h_items = [(c["added_on"], "Added", "Card published.")] + [(u["date"], "Updated", u["note"]) for u in c.get("updates") or []] + ([(c["status_date"], "Retired" if st == "retired" else "Superseded", c["status_reason"].strip())] if st != "active" else [])
    vers = ('<h3>Versions</h3><ul class="clean versions">' + "".join(f'<li><time datetime="{E(v_["first_public"])}">{E(v_["first_public"])}</time> <b>{E(v_["name"])}</b>' + (' <span class="k k-added">presented here</span>' if v_["name"] == c["version"] else "") + f' <a href="{E(v_["source"])}" rel="noopener nofollow" target="_blank">source</a>' + vcount(c["id"], v_["name"]) + f'<div class="stage-d">{E(v_["note"])}</div></li>' for v_ in reversed(c["versions"])) + '</ul>') if c.get("versions") else ""
    hist = ('<section class="blk" id="history"><h2>History</h2>' + vers + '<ul class="clean changelog">' + "".join(f'<li><time datetime="{d}">{d}</time> <span class="k k-{k.lower()}">{k}</span> {E(n)}</li>' for d, k, n in sorted(h_items, reverse=True))
            + f'</ul><p class="unk">Last verified {E(c["last_verified"])}. Spotted an error? Check the sources above and tell us once a contact address is set.</p>'
            + f'{f'<p><a class="btn" href="{root}compare/?ids={E(c["id"])}">Compare this system</a></p>' if st == "active" else ''}</section>')
    if not limits: keyfacts = keyfacts.replace('<a href="#limitations">Limitations</a>', "")
    keyfacts = keyfacts.replace("KFSPAN", str(6 + bool(arch) + bool(limits)))
    sup = f' Replaced by <a href="{root}systems/{E(c["superseded_by"])}/">{E(c["superseded_by"])}</a>.' if c.get("superseded_by") else ""
    notice = (f'<aside class="status-note status-{st}" id="status-note" role="note"><b>{"Retired" if st == "retired" else "Superseded"} on {E(c["status_date"])}.</b> {E(c["status_reason"].strip())}{sup} '
              f'This card stays online at its URL for reference. It is not counted on the home page and is no longer updated.</aside>') if st != "active" else ""
    body = f"""<div class="wrap"><article class="sys v2"><div class="crumbs"><a href="{root}">Systems</a> / {E(short_company(c))}</div>{notice}
<header class="v2head" id="top"><h1>{E(c['name'])}</h1><p class="byline">{byline}</p>
<div class="tags" style="margin:0 0 14px"><span class="badge b-era b-era-{E(c['era'])}">{E(ERAS[c['era']])}</span>{stage_badges}<span class="badge b-{E(c['evidence_level'])}">{E(EVID[c['evidence_level']])}</span>{f'<span class="badge b-version">Presents {E(c["version"])}, {"latest of" if c["versions"][-1]["name"] == c["version"] else "one of"} {len(c["versions"])} versions{"" if c["versions"][-1]["name"] == c["version"] else ", latest is " + E(c["versions"][-1]["name"])}</span>' if c.get("versions") else ''}</div>
<div class="tldr"><span class="tldr-l">TL;DR</span><p>{E(c['tldr'].strip())}</p></div>
<div class="actions">{paper_btn}{code_btn}</div>{cite_html(c["id"])}</header>
<div class="v2grid">{keyfacts}
{arch}
<section class="blk" id="how-it-works"><h2>How it works</h2><p class="lead">{E(c['summary'].strip())}</p>{stages}</section>
<section class="blk" id="results"><h2>Results</h2>{table}{note}</section>
<div id="subscribe">{subscribe_box("card:" + c["id"], "Like this card? Get one a week.").replace("{ROOT}", root)}</div>
{details}
{limits}
<section class="blk" id="sources"><h2>Sources</h2>{srcs}{codeblk}</section>
{hist}</div></article></div>"""
    title = f"{c['name']} - {c['company']}, {c['year']} | RecArch"
    desc = f"{c['name']} by {c['company']}: {c['summary'].strip()}"[:158]
    ld = {"@context":"https://schema.org","@type":"TechArticle","headline":c["name"],"about":c["surface"],"datePublished":c["added_on"],"dateModified":c["last_verified"],
          "citation":[s_["url"] for s_ in c["sources"]],"publisher":{"@type":"Organization","name":"RecArch"}}
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>' + ('' if st == "active" else '<meta name="robots" content="noindex">')
    if st != "active": title = f"{'Retired' if st == 'retired' else 'Superseded'}: {title}"
    return page(title, desc, body, root, f"systems/{c['id']}/", extra_head=head)

def redirect_page(c):
    """Old URL of a card merged into another (status superseded): static redirect, canonical points at the merged card."""
    to = c["superseded_by"]; canon = f"{SITE_URL}/systems/{to}/"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved to {E(by_id_name(to))} | RecArch</title>
<link rel="canonical" href="{E(canon)}"><meta http-equiv="refresh" content="0; url=../{E(to)}/"><meta name="robots" content="noindex"></head>
<body><p>{E(c["name"])} was merged into <a href="../{E(to)}/">{E(by_id_name(to))}</a>, which presents the latest version.</p></body></html>"""

NAMES = {}
def by_id_name(i): return NAMES.get(i, i)

def compare_page():
    root = "../"
    body = f"""<div class="wrap"><article class="sys"><h1>Compare systems</h1><p class="lead">Pick 2&ndash;3 systems to compare side by side.</p>
<div id="picker" class="controls"></div><div id="out"></div>{subscribe_box("compare").replace("{ROOT}", root)}</article></div>"""
    return page("Compare recommender systems | RecArch", "Side-by-side comparison of 2-3 industrial recommender, search or ranking systems: stages, paradigms, tokenization, training and scale.",
                body, root, "compare/", scripts=f'<script>window.RECARCH_ROOT="{root}"</script><script src="{root}static/compare.js"></script>')

def sponsor_page():
    root = "../"
    body = """<div class="wrap"><article class="sys"><h1>Advertise / sponsor RecArch</h1><p class="lead">Reach practitioners who design and operate recommender, search and ranking systems.</p>
<div class="panel"><span class="todo">TODO: placeholder</span>
<p>Planned: a sponsor slot in the weekly digest and a labelled sponsor line on the home page. Sponsors never change card content; all cards are sourced and editorially independent.</p>
<ul class="clean"><li>Audience: ML engineers, researchers and leads in recsys, search and ads; audience numbers will be added once real data exists.</li><li>Formats: newsletter sponsor line, home-page sponsor, job post.</li><li>Pricing: <span class="unk">not set</span></li><li>Contact: <span class="unk">TODO: add a contact address</span></li></ul></div></article></div>"""
    return page("Advertise / sponsor | RecArch", "Sponsor RecArch to reach recommender, search and ranking practitioners This is a placeholder page.", body, root, "sponsor/")

def about_page(n):
    root = "../"
    body = f"""<div class="wrap"><article class="sys"><h1>Method</h1><p class="lead">RecArch cards are written from public primary sources only: papers, official engineering blogs, documentation and released code.</p>
<ul class="clean"><li>Every card lists its sources. If a source does not state a fact, the field is marked unknown rather than guessed.</li>
<li>Evidence level separates systems a source says are deployed from open-source references and research-only work.</li>
<li>Scale numbers are only those the sources state, with attribution.</li><li>New systems are added as they are read in full. Candidate sources are queued by a refresh script and reviewed by hand before publication.</li></ul></article></div>"""
    return page("Method | RecArch", "How RecArch cards are sourced and what the evidence levels mean.", body, root, "about/")

def write(path, content):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)

def main():
    global SITE
    allc = load_cards(); SITE = load_site(); check_v2(allc); TAXONOMY.update(load_taxonomy()); DIAGRAMS.update(load_diagrams(allc)); CITES.update(load_citations(allc))
    by_id = {c["id"]: c for c in allc}; issues = load_issues(by_id)
    cards = [c for c in allc if is_active(c)]; off = [c for c in allc if not is_active(c)]   # retired and superseded: page built, but no list, count, carousel, feed card event or sitemap entry
    today = datetime.date.today().isoformat(); ev = events(cards, SITE, issues, off)
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"))
    write("index.html", home(cards, ev, today, off))
    NAMES.update({c["id"]: c["name"] for c in allc})
    for c in allc: write(f"systems/{c['id']}/index.html", redirect_page(c) if card_status(c) == "superseded" else card_page(c))
    write("compare/index.html", compare_page()); write("newsletter/index.html", newsletter_page(issues, cards))
    for i in issues: write(f"newsletter/{i['slug']}/index.html", issue_page(i, by_id))
    write("changelog/index.html", changelog_page(ev)); write("feed.xml", feed_xml(ev))
    write("sponsor/index.html", sponsor_page()); write("about/index.html", about_page(len(cards)))
    write("data/systems.json", json.dumps(cards, ensure_ascii=False))   # active only: compare picker
    base = (urlparse(SITE_URL).path.rstrip("/") + "/")  # 404 is served at any depth, so it needs the site's absolute base path
    write("404.html", page("Not found | RecArch", "Page not found.", f'<div class="wrap"><article class="sys"><h1>Not found</h1><p><a href="{base}">Back to all systems</a></p></article></div>', base, "404.html"))
    urls = [("", ev[0]["date"] if ev else today)] + [(f"systems/{c['id']}/", c["last_verified"]) for c in cards] + [("changelog/", ev[0]["date"]), ("newsletter/", issues[0]["date"] if issues else ev[0]["date"])] + [(f"newsletter/{i['slug']}/", i["date"]) for i in issues] + [("compare/", ev[0]["date"]), ("sponsor/", ev[0]["date"]), ("about/", ev[0]["date"])]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"built {len(allc)} card pages, {len(cards)} active, {len(off)} retired or superseded -> {OUT}")

if __name__ == "__main__": main()
