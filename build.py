#!/usr/bin/env python3
"""RecArch static site generator. Usage: python3 build.py   (env SITE_URL=https://example.com for canonical/sitemap URLs)"""
import glob, html, json, os, posixpath, re, shutil, sys, datetime
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
EVID_KEYS = ["production_described","open_source_reference","research_only"]
EVID = {}   # key -> label in the language being rendered, filled by set_lang()
STATUSES = ("active", "superseded", "retired")   # card lifecycle, see schema/schema.md "Status"
CODE_KEYS = ["official_full","official_partial","third_party_only","none"]
CODE_STATUS = {}   # filled by set_lang()
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
        assert e.get("title_zh") and (e.get("note_zh") or not e.get("note")), f"site event needs title_zh and note_zh: {e['title']}"
    return s

def load_issues(card_ids):
    """Newsletter issues: data/newsletter/<slug>.yaml (see templates/newsletter_issue.example.yaml)."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/newsletter/*.yaml"))):
        i = yaml.safe_load(open(f)); i["slug"] = os.path.basename(f)[:-5]
        errs = [k for k in ("title", "date", "summary", "body", "title_zh", "summary_zh", "body_zh") if not i.get(k)]
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


# ====================================================================================================
# i18n. Chinese (zh) is the default language at the site root, English (en) lives under /en/.
#   UI strings:      data/i18n/ui.txt                  "key || English || Chinese", every key needs both
#   Card prose:      data/i18n/zh/systems/<id>.txt     "path|Chinese", "=" keeps the English text as it is
#   Diagrams:        data/i18n/zh/diagrams/<id>.txt    same format
#   Topics:          data/i18n/zh/topics/<slug>.yaml   same structure as data/topics/<slug>.yaml
#   Site events:     title_zh / note_zh next to title / note in data/site.yaml
#   Newsletter:      title_zh / summary_zh / body_zh (and note_zh on papers) in each issue file
#   Company names:   data/i18n/companies.txt          "English || Chinese", whole-string match
# Build fails when a required Chinese string is missing, when Chinese text introduces a number the
# English source does not have, or when it uses parentheses. RECARCH_ALLOW_MISSING_ZH=1 relaxes only the
# missing-string check (falls back to English) for work in progress, never for the published build.
# ====================================================================================================
LANGS = ("zh", "en"); DEFAULT_LANG = "zh"; LANG = "en"
LANG_TAG = {"zh": "zh-CN", "en": "en"}
I18N = os.path.join(ROOT, "data", "i18n")
ALLOW_MISSING = os.environ.get("RECARCH_ALLOW_MISSING_ZH") == "1"
UI = {}
CJK = re.compile(r"[\u3400-\u9fff]")
PARENS = re.compile(r"[()\uff08\uff09]")
PROSE_WORD = re.compile(r"(?<![A-Za-z])[a-z]{3,}(?![A-Za-z])")
_NUMS = lambda t: set(re.findall(r"\d+(?:[.,]\d+)*", str(t).replace(",", "")))
# Magnitude words. Chinese counts in units of wan and yi, so an English "20 million" is written 两千万 or 2000 万 and
# never left as "20 million" in Chinese prose. The check converts by value: every Chinese magnitude phrase must equal a
# quantity of the English source, so the conversion cannot smuggle in a new number. billion=十亿, million=百万,
# half a billion=五亿, hundreds of billions=数千亿.
_MAG = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_EN_WORDNUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}
_EN_NUM_VAL = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*\+?\s*(?:(thousand|million|billion|trillion)s?\b|([KMB])\b)?")
_EN_HALF = re.compile(r"\bhalf an? (thousand|million|billion|trillion)\b", re.I)
_EN_WORD_MAG = re.compile(r"(?<!half )\b(" + "|".join(_EN_WORDNUM) + r")\s+(thousand|million|billion|trillion)\b", re.I)
_EN_HUNDRED = re.compile(r"\b(?:a |one )?hundred[- ](thousand|million|billion|trillion)\b", re.I)
_EN_BARE = re.compile(r"\b(million|billion|trillion)(?=[- ]?(?:scale|node|level|sized?)\b)", re.I)
_EN_MAG_WORD = re.compile(r"\b(thousand|million|billion|trillion)s?\b", re.I)
# approximate counts: English phrase -> the Chinese phrase that renders it
_APPROX = [("tens of thousands", "数万"), ("hundreds of thousands", "数十万"), ("millions", "数百万"), ("tens of millions", "数千万"),
           ("hundreds of millions", "数亿"), ("billions", "数十亿"), ("tens of billions", "数百亿"), ("hundreds of billions", "数千亿"),
           ("trillions", "数万亿"), ("tens of trillions", "数十万亿"), ("hundreds of trillions", "数百万亿"), ("several million", "数百万"), ("several billion", "数十亿"), ("several hundred thousand", "数十万"),
           ("several hundred million", "数亿"), ("several hundred billion", "数千亿")]
# a Chinese approximate count is also fine when the source has a quantity in its range: 数万 for 10K to 99K and so on
_APPROX_RANGE = {"数万": (1e4, 1e5), "数十万": (1e5, 1e6), "数百万": (1e6, 1e7), "数千万": (1e7, 1e8), "数亿": (1e8, 1e9), "数十亿": (1e9, 1e10),
                 "数百亿": (1e10, 1e11), "数千亿": (1e11, 1e12), "数万亿": (1e12, 1e13), "数十万亿": (1e13, 1e14), "数百万亿": (1e14, 1e15)}
_ZH_DIG = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_ZH_UNIT = {"十": 10, "百": 100, "千": 1000}
_ZH_MAG = {"万亿": 1e12, "亿": 1e8, "万": 1e4}
_ZH_MAG_RE = re.compile(r"(?<![数几\d.])(?:(\d+(?:\.\d+)?)|([零〇一二两三四五六七八九十百千]+(?:点[零〇一二三四五六七八九]+)?))\s*(万亿|亿|万)")
_ZH_APPROX_RE = re.compile("|".join(sorted({z for _, z in _APPROX}, key=len, reverse=True)))
def _zh_int(t):
    total = cur = 0
    for ch in t:
        if ch in _ZH_DIG: cur = _ZH_DIG[ch]
        else: total += (cur or 1) * _ZH_UNIT[ch]; cur = 0
    return total + cur
def _zh_numeral(t):
    if "点" in t:
        a, b = t.split("点"); return (_zh_int(a) if a else 0) + float("0." + "".join(str(_ZH_DIG[c]) for c in b))
    return _zh_int(t)
def en_values(en):
    """Every quantity of an English text as a number: plain, with million/billion/trillion, K M B suffixes, half a billion, two billion."""
    en = str(en); vals = set()
    for m in _EN_NUM_VAL.finditer(en):
        v = float(m.group(1).replace(",", ""))
        if m.group(2): v *= _MAG[m.group(2).lower()]
        elif m.group(3): v *= {"K": 1e3, "M": 1e6, "B": 1e9}[m.group(3)]
        vals.add(v)
    for m in _EN_HALF.finditer(en): vals.add(0.5 * _MAG[m.group(1).lower()])
    for m in _EN_WORD_MAG.finditer(en): vals.add(_EN_WORDNUM[m.group(1).lower()] * _MAG[m.group(2).lower()])
    for m in _EN_HUNDRED.finditer(en): vals.add(100 * _MAG[m.group(1).lower()])
    for m in _EN_BARE.finditer(en): vals.add(_MAG[m.group(1).lower()])
    return vals
def zh_magnitudes(zh):
    """Split a Chinese text into the text without its wan/yi quantities, and those quantities as numbers."""
    vals = []
    def take(m):
        n = float(m.group(1)) if m.group(1) else _zh_numeral(m.group(2))
        vals.append(n * _ZH_MAG[m.group(3)]); return " "
    return _ZH_MAG_RE.sub(take, zh), vals
def zh_number_problems(zh, en_text, en_digits=None):
    """(new digit numbers, magnitude problems) of a Chinese text against its English source."""
    rest, mags = zh_magnitudes(zh)
    ok = en_values(en_text); probs = []
    for v in mags:
        if not any(abs(v - o) <= 1e-6 * max(abs(v), abs(o), 1) for o in ok):
            probs.append(f"{v:,.0f} is not a quantity of the English source")
    low = str(en_text).lower()
    for z in sorted(set(_ZH_APPROX_RE.findall(zh))):
        lo, hi = _APPROX_RANGE[z]
        if not any(e in low and zz == z for e, zz in _APPROX) and not any(lo <= o < hi for o in ok): probs.append(f"{z} has no matching English phrase such as {[e for e, zz in _APPROX if zz == z][0]}")
    if _EN_MAG_WORD.search(zh) or _EN_HALF.search(zh): probs.append("English magnitude word left in Chinese prose, write it with 万 or 亿")
    base = _NUMS(en_text) if en_digits is None else en_digits
    return _NUMS(rest) - base, probs
def needs_zh(s):
    """True when an English string contains prose and so must have a Chinese text. Names, numbers and units do not."""
    return isinstance(s, str) and bool(PROSE_WORD.search(s))
def _fields(s): return set(re.findall(r"\{(\w+)\}", s))

def load_ui():
    if UI: return
    errs = []
    for n, line in enumerate(open(os.path.join(I18N, "ui.txt"), encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"): continue
        p = [x.strip() for x in line.split(" || ")]
        if len(p) != 3 or not all(p): errs.append(f"ui.txt:{n}: need 'key || English || Chinese', all non-empty"); continue
        k, en, zh = p
        if k in UI: errs.append(f"ui.txt:{n}: duplicate key {k}")
        if _fields(en) != _fields(zh): errs.append(f"ui.txt:{n}: {k}: placeholders differ {_fields(en)} vs {_fields(zh)}")
        if PARENS.search(zh) and k not in UI_PAREN_OK: errs.append(f"ui.txt:{n}: {k}: no parentheses in Chinese copy")
        if needs_zh(re.sub(r"\{\w+\}|<[^>]+>", " ", en)) and not CJK.search(zh): errs.append(f"ui.txt:{n}: {k}: Chinese text has no Chinese characters")
        if _NUMS(zh) - _NUMS(en): errs.append(f"ui.txt:{n}: {k}: Chinese text adds numbers {sorted(_NUMS(zh) - _NUMS(en))}")
        UI[k] = {"en": en, "zh": zh}
    if errs: sys.exit("UI STRING ERRORS:\n  " + "\n  ".join(errs))
UI_PAREN_OK = set()

def T(key, **kw):
    """UI string in the language being rendered. Raises KeyError for a key missing from data/i18n/ui.txt, which fails the build."""
    if not UI: load_ui()
    s = UI[key][LANG]
    return s.format(**kw) if kw else s

COMPANIES = {}
def load_companies():
    p = os.path.join(I18N, "companies.txt")
    for line in open(p, encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            a, b = [x.strip() for x in line.split(" || ")]; COMPANIES[a] = b

ERA_KEYS = ["classic", "deep", "generative"]
STAGE_KEYS = ["retrieval", "pre-rank", "rank", "re-rank", "single-stage", "other"]
ERAS, STAGE_LABEL, DEP_EVID, KIND_LABEL, GLABEL = {}, {}, {}, {}, {}
DEP_EVID_KEYS = ["online_numbers", "online_qualitative", "deployed_only", "no_online_claim"]
KIND_KEYS = ["added", "updated", "site", "issue", "retired"]
SUB_COPY = ""
def set_lang(lang):
    """Switch the language being rendered and refill the label tables."""
    global LANG, SUB_COPY
    LANG = lang
    for d, keys, pre in ((ERAS, ERA_KEYS, "era."), (EVID, EVID_KEYS, "evid."), (CODE_STATUS, CODE_KEYS, "code."), (STAGE_LABEL, STAGE_KEYS, "stage."),
                         (DEP_EVID, DEP_EVID_KEYS, "depev."), (KIND_LABEL, KIND_KEYS, "kind."), (GLABEL, ["era", "stage", "family", "paradigm", "evidence"], "grp.")):
        d.clear(); d.update({k: T(pre + k) for k in keys})
    SUB_COPY = T("sub.copy")

# ---- Chinese overlays ----
def _tget(o, path):
    for p in path.split("."):
        o = o[int(p)] if isinstance(o, list) else o[p]
    return o
def _tset(o, path, v):
    ps = path.split(".")
    for p in ps[:-1]: o = o[int(p)] if isinstance(o, list) else o[p]
    if isinstance(o, list): o[int(ps[-1])] = v
    else: o[ps[-1]] = v

CARD_SCALARS = ("surface", "era_reason", "tldr", "summary", "core_idea", "deployed_in", "scale_short", "key_result", "results_reported", "version_note", "status_reason", "serving_infra")
DEP_PROSE = ("scenario", "ab_traffic", "ab_duration", "baseline", "training_compute", "serving_latency", "serving_qps", "inference_cost", "hardware")
def card_tpaths(c):
    """(dotted path, English value, required) for every translatable string of a card. Optional paths keep the English text unless overridden:
    metric names and result values are data and stay as they are."""
    out = []
    for k in CARD_SCALARS:
        if isinstance(c.get(k), str): out.append((k, c[k], True))
    for i, s in enumerate(c.get("stages") or []):
        for k in ("model_family", "details"):
            if isinstance(s.get(k), str): out.append((f"stages.{i}.{k}", s[k], True))
    for k in ("approach", "details"):
        if isinstance((c.get("id_tokenization") or {}).get(k), str): out.append((f"id_tokenization.{k}", c["id_tokenization"][k], True))
    for i, f in enumerate(c.get("features_signals") or []): out.append((f"features_signals.{i}", f, True))
    tr = c.get("training") or {}
    if isinstance(tr.get("mode"), str): out.append(("training.mode", tr["mode"], True))
    for i, o in enumerate(tr.get("objectives") or []): out.append((f"training.objectives.{i}", o, True))
    if isinstance(tr.get("notes"), str): out.append(("training.notes", tr["notes"], True))
    for i, s in enumerate(c.get("scale") or []):
        out.append((f"scale.{i}.metric", s["metric"], True))
        if isinstance(s.get("value"), str): out.append((f"scale.{i}.value", s["value"], True))
    rt = c.get("results_table") or {}
    if isinstance(rt.get("note"), str): out.append(("results_table.note", rt["note"], True))
    for g in ("online", "offline", "other"):
        for i, r in enumerate(rt.get(g) or []):
            out.append((f"results_table.{g}.{i}.setting", r["setting"], True))
            for k in ("method", "metric", "result", "versus"):
                if isinstance(r.get(k), str): out.append((f"results_table.{g}.{i}.{k}", r[k], False))
    for i, x in enumerate(c.get("caveats") or []): out.append((f"caveats.{i}", x, True))
    for i, x in enumerate(c.get("unknown_fields") or []): out.append((f"unknown_fields.{i}", x, True))
    for i, v in enumerate(c.get("versions") or []): out.append((f"versions.{i}.note", v["note"], True))
    for i, u in enumerate(c.get("updates") or []): out.append((f"updates.{i}.note", u["note"], True))
    cd = c.get("code") or {}
    if isinstance(cd.get("note"), str): out.append(("code.note", cd["note"], True))
    for i, r in enumerate(cd.get("repos") or []):
        out.append((f"code.repos.{i}.owner", r["owner"], True)); out.append((f"code.repos.{i}.note", r["note"], True))
    d = c.get("deployment") or {}
    for k in DEP_PROSE:
        if isinstance(d.get(k), str) and d[k] != NR: out.append((f"deployment.{k}", d[k], True))
    for i, x in enumerate(d.get("notes") or []): out.append((f"deployment.notes.{i}", x, True))
    if isinstance(d.get("online_lifts"), list):
        for i, x in enumerate(d["online_lifts"]):
            out.append((f"deployment.online_lifts.{i}.metric", x["metric"], False)); out.append((f"deployment.online_lifts.{i}.value", x["value"], False))
    return out

def read_overlay(path, errs, label):
    """'path|text' lines -> dict. Blank lines and # comments are skipped."""
    d = {}
    if not os.path.exists(path): return d
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"): continue
        if "|" not in line: errs.append(f"{label}:{n}: expected 'path|text'"); continue
        k, v = line.split("|", 1); k, v = k.strip(), v.strip()
        if k in d: errs.append(f"{label}:{n}: duplicate path {k}")
        d[k] = v
    return d

def check_zh_text(label, en, zh, errs, warns):
    if zh == "=":
        if _EN_MAG_WORD.search(str(en)): errs.append(f"{label}: = keeps an English magnitude word, write it with 万 or 亿")
        return
    if PARENS.search(zh): errs.append(f"{label}: no parentheses in Chinese copy: {zh[:50]}")
    extra, probs = zh_number_problems(zh, en)
    if extra: errs.append(f"{label}: Chinese text adds numbers not in the English source: {sorted(extra)}")
    for pr in probs: errs.append(f"{label}: {pr}")
    if needs_zh(en) and not CJK.search(zh): errs.append(f"{label}: Chinese text has no Chinese characters (use = to keep English as is)")
    _, zv = zh_magnitudes(zh)
    def covered(m):
        if not (m.group(2) or m.group(3)): return m.group(0)
        v = float(m.group(1).replace(",", "")) * (_MAG[m.group(2).lower()] if m.group(2) else {"K": 1e3, "M": 1e6, "B": 1e9}[m.group(3)])
        return " " if any(abs(v - o) <= 1e-6 * v for o in zv) else m.group(0)
    lost = _NUMS(_EN_NUM_VAL.sub(covered, en)) - _NUMS(zh)
    if lost: warns.append(f"{label}: numbers of the English text missing in Chinese: {sorted(lost)}")

def zh_card(c, errs, warns):
    """Chinese version of one card: a deep copy with the overlay applied. Required prose without a Chinese text is an error."""
    import copy
    label = f"zh/systems/{c['id']}"; ov = read_overlay(os.path.join(I18N, "zh", "systems", c["id"] + ".txt"), errs, label)
    z = copy.deepcopy(c); paths = card_tpaths(c); known = {p for p, _, _ in paths}
    for p in ov:
        if p != "company" and p not in known: errs.append(f"{label}: path {p} is not a translatable field of the card")
    z["company"] = COMPANIES.get(c["company"], c["company"])
    for p, en, req in paths:
        if p in ov:
            check_zh_text(f"{label}:{p}", en, ov[p], errs, warns)
            if ov[p] != "=": _tset(z, p, ov[p])
        elif req and needs_zh(en) and not ALLOW_MISSING: errs.append(f"{label}: missing Chinese for {p}")
        elif not req and _EN_MAG_WORD.search(str(en)) and not ALLOW_MISSING: errs.append(f"{label}: {p} keeps an English magnitude word, add a Chinese text with 万 or 亿")
    return z

def zh_diagram(i, g, errs, warns):
    import copy
    label = f"zh/diagrams/{i}"; ov = read_overlay(os.path.join(I18N, "zh", "diagrams", i + ".txt"), errs, label)
    z = copy.deepcopy(g); paths = [("alt", g["alt"]), ("caption.fig", g["caption"]["fig"])] + ([("caption.note", g["caption"]["note"])] if g["caption"].get("note") else [])
    for ci, col in enumerate(g["columns"]):
        paths.append((f"columns.{ci}.label", col["label"]))
        for bi, b in enumerate(col["boxes"]):
            for ti, t in enumerate(b["text"]): paths.append((f"columns.{ci}.boxes.{bi}.text.{ti}", t))
    known = {p for p, _ in paths}
    for p in ov:
        if p not in known: errs.append(f"{label}: path {p} is not translatable")
    for p, en in paths:
        if p in ov:
            check_zh_text(f"{label}:{p}", en, ov[p], errs, warns)
            if ov[p] != "=": _tset(z, p, ov[p])
        elif needs_zh(en) and not ALLOW_MISSING: errs.append(f"{label}: missing Chinese for {p}")
    return z


# ---- helpers for the two languages ----
def lang_prefix(lang): return "" if lang == DEFAULT_LANG else lang + "/"
def abs_url(lang, path): return f"{SITE_URL}/{lang_prefix(lang)}{path}"
def _norm(p):   # tidy absolute paths of the 404 page, e.g. /en/../ -> /
    if not p.startswith("/"): return p
    q = posixpath.normpath(p)
    return "/" + q.lstrip("/") + ("/" if p.endswith("/") and q.lstrip("/") else "")
def sroot(root): return _norm(root + ("../" if LANG == "en" else ""))      # relative path to the site root, where static/ lives
def twin_href(root, path, lang):
    """Relative href from the page being rendered (root = path back to its language root) to the same page in `lang`."""
    if lang == LANG: return root + path
    return _norm(root + "en/" + path if LANG == "zh" else root + "../" + path)

def lang_switch(root, path):
    other = "en" if LANG == "zh" else "zh"
    cur = {"zh": "中文", "en": "EN"}
    here = f'<span class="on" lang="{LANG_TAG[LANG]}" aria-current="true">{cur[LANG]}</span>'
    there = f'<a lang="{LANG_TAG[other]}" hreflang="{LANG_TAG[other]}" href="{E(twin_href(root, path, other))}" title="{E(T("lang.switch_title"))}">{cur[other]}</a>'
    return f'<span class="langsw" role="group" aria-label="{E(T("lang.label"))}">' + (here + there if LANG == "zh" else there + here) + '</span>'

def page(title, desc, body, root, path, extra_head="", scripts="", noalt=False):
    canon = abs_url(LANG, path)
    alts = "" if noalt else "".join(f'<link rel="alternate" hreflang="{LANG_TAG[l]}" href="{E(abs_url(l, path))}">' for l in LANGS) + f'<link rel="alternate" hreflang="x-default" href="{E(abs_url(DEFAULT_LANG, path))}">'
    sr = sroot(root)
    return f"""<!doctype html><html lang="{LANG_TAG[LANG]}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(canon)}">{alts}
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{E(canon)}"><meta property="og:locale" content="{LANG_TAG[LANG].replace('-', '_')}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/atom+xml" title="{E(T('feed.link_title'))}" href="{root}feed.xml">
<link rel="stylesheet" href="{sr}static/style.css">{extra_head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{root}">Rec<span>Arch</span></a>
<nav><a href="{root}">{E(T('nav.systems'))}</a><a href="{root}topics/">{E(T('nav.topics'))}</a><a href="{root}compare/">{E(T('nav.compare'))}</a><a href="{root}changelog/">{E(T('nav.changelog'))}</a><a href="{root}newsletter/">{E(T('nav.newsletter'))}</a><a href="{root}feed.xml" title="{E(T('nav.rss_title'))}">RSS</a></nav>{lang_switch(root, path)}</div></header>
{body}
<footer class="site"><div class="wrap">{E(T('footer.text'))} <a href="{root}about/">{E(T('nav.method'))}</a> &middot; <a href="{root}changelog/">{E(T('nav.changelog'))}</a> &middot; <a href="{root}feed.xml">RSS</a></div></footer>
<script>document.querySelectorAll(".langsw a").forEach(function(a){{a.href+=location.search+location.hash}})</script>
{scripts}<script type="text/javascript" async src="https://subscribe-forms.beehiiv.com/attribution.js"></script></body></html>"""

def js_l10n():
    """Strings for the client scripts, injected as window.RECARCH_L10N. The scripts fall back to English when it is absent."""
    d = {k[3:]: v[LANG] for k, v in UI.items() if k.startswith("js.")}
    d.update({"era": ERAS, "evid": EVID, "code": CODE_STATUS, "depev": DEP_EVID, "stage": STAGE_LABEL, "lang": LANG})
    return '<script>window.RECARCH_L10N=' + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + '</script>'

def chips(group, values, labels=None):
    out = f'<div class="group" data-group="{group}"><b>{GLABEL.get(group, group)}</b>'
    for v in values:
        out += f'<button class="chip" type="button" data-v="{E(v)}" aria-pressed="false">{E((labels or {}).get(v, v))}</button>'
    return out + "</div>"

def code_badge(c):
    s = c["code"]["status"]
    return "" if s == "none" else f' <span class="badge b-code-{E(s)}">{E(CODE_STATUS[s])}</span>'

def card_attrs(c):
    """data-* attributes shared by list cards and timeline items; app.js filters on these. Search covers both languages."""
    stages = sorted({TAXONOMY["stage_group"][s["stage"]] for s in c["stages"]})
    fams = sorted({TAXONOMY["tag_family"][p] for p in c["paradigms"]})
    en = EN_CARDS.get(c["id"], c)
    search = " ".join([c["name"], c["company"], en["company"], c["summary"], en["summary"]]).lower()
    return (f'data-id="{E(c["id"])}" data-paradigms="{E("|".join(c["paradigms"]))}" data-families="{E("|".join(fams))}" data-stages="{E("|".join(stages))}" '
            f'data-evidence="{E(c["evidence_level"])}" data-prod="{int(c["evidence_level"] == "production_described")}" data-official="{int(has_official(c))}" '
            f'data-era="{c["era"]}" data-search="{E(search)}"' + (f' data-cites="{CITES[c["id"]]["count"]}"' if c["id"] in CITES else ""))
EN_CARDS = {}   # id -> English card, for search across both languages

def stage_tag(s): return s if LANG == "en" else STAGE_LABEL[s]

def card_html(c, root):
    tags = "".join(f'<span class="tag">{E(p)}</span>' for p in c["paradigms"])
    stages = sorted({s["stage"] for s in c["stages"]})
    st = "".join(f'<span class="tag stage">{E(stage_tag(s))}</span>' for s in stages)
    ns = len(c["sources"])
    cit = f' &middot; {E(T("card.citations", n=format(CITES[c["id"]]["count"], ",")))}' if c["id"] in CITES else ""
    return f"""<div class="card era-{c['era']}" {card_attrs(c)}>
<div class="co">{E(c['company'])} &middot; {c['year']}</div>
<h3><a href="{root}systems/{E(c['id'])}/">{E(c['name'])}</a></h3>
<div><span class="badge b-{E(c['evidence_level'])}">{E(EVID[c['evidence_level']])}</span>{code_badge(c)}</div>
<p>{E(c['tldr'].strip())}</p>
<div class="tags">{tags}</div><div class="tags">{st}</div>
<div class="foot"><span>{E(T("card.sources_one" if ns == 1 else "card.sources_many", n=ns))}{cit}</span><label><input type="checkbox" class="cmp"> {E(T("card.compare"))}</label></div></div>"""

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
    return f'<div class="timeline" id="timeline" hidden><div class="tl-head"><div class="tl-y"></div>{head}</div>{rows}<p class="unk tl-note">{E(T("timeline.note"))}</p></div>'

SITE = {}

def subscribe_box(source, heading=None, compact=False):
    """Real Beehiiv embed (form id in data/site.yaml). The loader script renders the form in place; attribution.js (in page())
    forwards UTM params. noscript / no-JS fallback is the hosted subscribe page. `source` is not sent (the embed has no hidden fields);
    attribution comes from Beehiiv's own referrer/UTM capture. The Beehiiv form itself is rendered by Beehiiv, in its own language."""
    nl = SITE.get("newsletter") or {}
    form_id = str(nl.get("form_id") or "")
    pub = str(nl.get("public_url") or "https://recarch.beehiiv.com").rstrip("/")
    loader = str(nl.get("embed_url") or "https://subscribe-forms.beehiiv.com/v3/loader.js")
    heading = heading or T("sub.heading_default")
    return f"""<div class="nlband{' compact' if compact else ''}" data-source="{E(source)}"><h2>{E(heading)}</h2><p>{E(SUB_COPY)}</p>
<div class="nl-embed"><script async src="{E(loader)}" data-beehiiv-form="{E(form_id)}"></script>
<noscript><p><a class="btn" href="{E(pub)}/subscribe">{E(T("sub.noscript"))}</a></p></noscript></div>
<p class="sub-fine">{E(T("sub.fine"))} <a href="{E(pub)}/subscribe">{E(T("sub.noscript"))}</a> &middot; <a href="{{ROOT}}feed.xml">{E(T("sub.rss"))}</a></p></div>"""

def events(cards, site, issues, off=()):
    """Every dated change on the site, newest first. kind: added | updated | site | issue."""
    ev = []
    for c in cards:
        ev.append({"date": c["added_on"], "kind": "added", "title": c["name"], "note": f"{c['company']} \u00b7 {c['surface']}", "path": f"systems/{c['id']}/", "key": f"added:{c['id']}", "summary": c["summary"].strip()})
        for n, u in enumerate(c.get("updates") or []):
            ev.append({"date": u["date"], "kind": "updated", "title": c["name"], "note": u["note"], "path": f"systems/{c['id']}/", "key": f"update:{c['id']}:{n}", "summary": u["note"]})
    for c in off:   # retired or superseded cards: their added/updated events are dropped, one status event stays
        word = T("kind.retired") if card_status(c) == "retired" else T("status.superseded")
        line = T("status.line", word=word, reason=c["status_reason"].strip())
        ev.append({"date": c["status_date"], "kind": "retired", "title": c["name"], "note": line, "path": f"systems/{c.get('superseded_by') or c['id']}/", "key": f"status:{c['id']}", "summary": line})
    for n, e in enumerate(site.get("events") or []):
        ev.append({"date": e["date"], "kind": "site", "title": e["title"], "note": e.get("note", ""), "path": "changelog/", "key": f"site:{n}", "summary": e.get("note", "")})
    for i in issues:
        ev.append({"date": i["date"], "kind": "issue", "title": i["title"], "note": i["summary"], "path": f"newsletter/{i['slug']}/", "key": f"issue:{i['slug']}", "summary": i["summary"]})
    order = {"issue": 0, "site": 1, "retired": 2, "updated": 3, "added": 4}
    return sorted(ev, key=lambda e: (e["date"], -order[e["kind"]], e["title"]), reverse=True)

def rel_date(d, today):
    n = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(d)).days
    return T("js.today") if n <= 0 else T("js.yesterday") if n == 1 else T("js.days_ago", n=n)

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
    pill = f'<span class="pill">{E(T("car.week", na=na, nu=nu))}</span>' if week else f'<span class="pill quiet">{E(T("car.quiet"))}</span>'
    sel = carousel_select(cards or [], today, size, window); n = len(sel)
    slides = ""
    for i, it in enumerate(sel):
        c = it["card"]
        note = f'<p class="slide-note"><b>{E(T("car.update"))}</b> {E(it["note"])}</p>' if it["note"] else ""
        slides += f"""<article class="slide era-{c['era']}" role="group" aria-roledescription="slide" aria-label="{E(T('car.slide_of', i=i + 1, n=n))}" data-i="{i}" data-id="{E(c['id'])}"><div class="slide-meta"><span class="era-badge era-{c['era']}">{E(ERAS[c['era']])}</span><span class="k k-{it['kind']}">{E(KIND_LABEL[it['kind']])}</span><time datetime="{it['date']}" data-date="{it['date']}">{rel_date(it['date'], today)}</time></div>
<h3><a href="{root}systems/{E(c['id'])}/">{E(c['name'])}</a></h3><div class="co">{E(c['company'])}</div><p class="slide-tldr">{E(c['tldr'].strip())}</p>{note}<a class="slide-more" href="{root}systems/{E(c['id'])}/">{E(T('car.read'))} &rarr;</a></article>"""
    dots = "".join(f'<button type="button" class="dot" data-go="{i}" aria-label="{E(T("car.go", n=i + 1))}" aria-current="{"true" if i == 0 else "false"}"></button>' for i in range(n))
    return f"""<section class="carousel" aria-roledescription="carousel" aria-label="{E(T('car.aria'))}" data-autoplay="5000" data-count="{n}"><div class="car-h"><h2>{E(T('car.title'))}</h2>{pill}<span class="strip-links"><a href="{root}changelog/">{E(T('car.full_changelog'))}</a> &middot; <a href="{root}feed.xml">RSS</a></span></div>
<div class="car-body"><button type="button" class="car-btn car-prev" aria-label="{E(T('car.prev'))}">&#8249;</button><div class="car-view" tabindex="0" aria-live="off"><div class="car-track">{slides}</div></div><button type="button" class="car-btn car-next" aria-label="{E(T('car.next'))}">&#8250;</button></div>
<div class="car-foot"><div class="car-dots">{dots}</div><button type="button" class="car-pause" aria-pressed="false">{E(T('js.pause'))}</button></div></section>"""

def changelog_page(ev):
    root = "../"; by = {}
    for e in ev: by.setdefault(e["date"], []).append(e)
    sec = ""
    for d, items in by.items():
        lis = "".join(f'<li><span class="k k-{e["kind"]}">{E(KIND_LABEL[e["kind"]])}</span> <a href="{root}{E(e["path"])}">{E(e["title"])}</a><div class="unk" style="font-style:normal">{E(e["note"])}</div></li>' for e in items)
        sec += f'<section class="blk"><h2><time datetime="{d}">{d}</time></h2><ul class="clean changelog">{lis}</ul></section>'
    body = f"""<div class="wrap"><article class="sys"><h1>{E(T('nav.changelog'))}</h1><p class="lead">{T('changelog.lead', rss=f'<a href="{root}feed.xml">{E(T("changelog.rss_text"))}</a>', digest=f'<a href="{root}newsletter/">{E(T("changelog.digest_text"))}</a>')}</p>
{sec}{subscribe_box("changelog").replace("{ROOT}", root)}</article></div>"""
    return page(T("changelog.title"), T("changelog.desc"), body, root, "changelog/")

def feed_xml(ev):
    def ts(d): return f"{d}T00:00:00+08:00"   # dates are day-precision; Asia/Shanghai
    top = ev[:100]; pre = lang_prefix(LANG); base = f"{SITE_URL}/{pre}"
    upd = ts(top[0]["date"]) if top else ts(datetime.date.today().isoformat())
    out = ['<?xml version="1.0" encoding="utf-8"?>', f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{LANG_TAG[LANG]}">',
           f'<title>{E(T("feed.title"))}</title><subtitle>{E(T("feed.subtitle"))}</subtitle>',
           f'<id>{base}</id><link rel="self" type="application/atom+xml" href="{base}feed.xml"/><link rel="alternate" type="text/html" href="{base}"/><updated>{upd}</updated>',
           '<author><name>RecArch</name></author>']
    for e in top:
        label = T("feedkind." + e["kind"])
        out.append(f'<entry><title>{E(label)}{": " if LANG == "en" else "\uff1a"}{E(e["title"])}</title><id>tag:{SITE_URL.split("//")[-1]},{e["date"]}:{E(e["key"])}{"" if LANG == "en" else ":" + LANG}</id><link rel="alternate" type="text/html" href="{base}{E(e["path"])}"/><updated>{ts(e["date"])}</updated><category term="{e["kind"]}"/><summary>{E(e["summary"][:600])}</summary></entry>')
    return "\n".join(out) + "\n</feed>\n"

def md_paras(s):
    return "".join(f"<p>{E(p.strip())}</p>" for p in str(s).strip().split("\n\n") if p.strip())

def newsletter_page(issues, cards):
    root = "../"
    if issues:
        lis = "".join(f'<li><time datetime="{E(i["date"])}">{E(i["date"])}</time> <a href="{root}newsletter/{E(i["slug"])}/">{E(i["title"])}</a><div class="unk" style="font-style:normal">{E(i["summary"])}</div></li>' for i in issues)
        arch = f'<section class="blk"><h2>{E(T("nl.issues"))}</h2><ul class="clean changelog">{lis}</ul></section>'
    else:
        arch = f'<section class="blk"><h2>{E(T("nl.issues"))}</h2><p class="unk">{T("nl.none", feed=f'<a href="../feed.xml">{E(T("nl.none_feed"))}</a>')}</p></section>'
    body = f"""<div class="wrap"><article class="sys"><h1>{E(T('nl.h1'))}</h1><p class="lead">{E(SUB_COPY)} {E(T('nl.lead'))}</p>
{subscribe_box("newsletter")}<p class="sub-fine">{T('nl.past', link=f'<a href="{E(str((SITE.get("newsletter") or {}).get("public_url") or "https://recarch.beehiiv.com"))}">recarch.beehiiv.com</a>')}</p>{arch}</article></div>""".replace("{ROOT}", root)
    return page(T("nl.title"), T("nl.desc"), body, root, "newsletter/")

def issue_page(i, by_id):
    root = "../../"
    cs = "".join(f'<li><a href="{root}systems/{E(c)}/">{E(by_id[c]["name"])}</a> <span class="unk">{E(by_id[c]["company"])}, {by_id[c]["year"]}</span></li>' for c in i.get("cards") or [])
    ps = "".join(f'<li><a href="{E(p["url"])}" rel="noopener nofollow" target="_blank">{E(p["title"])}</a>' + (f' <span class="unk">&mdash; {E(p["note"])}</span>' if p.get("note") else "") + "</li>" for p in i.get("papers") or [])
    body = f"""<div class="wrap"><article class="sys"><div class="crumbs"><a href="{root}newsletter/">{E(T('nav.newsletter'))}</a> / {E(i['date'])}</div><h1>{E(i['title'])}</h1><p class="lead">{E(i['summary'])}</p>
<section class="blk">{md_paras(i['body'])}</section>
{f'<section class="blk"><h2>{E(T("nl.covered"))}</h2><ul class="clean">{cs}</ul></section>' if cs else ''}{f'<section class="blk"><h2>{E(T("nl.papers"))}</h2><ul class="clean">{ps}</ul></section>' if ps else ''}
{subscribe_box("issue:" + i["slug"], T("sub.heading_issue")).replace("{ROOT}", root)}</article></div>"""
    return page(T("nl.issue_title", title=i["title"]), i["summary"][:158], body, root, f"newsletter/{i['slug']}/")

def archive_html(off, root):
    """Small archive of retired and superseded cards: kept at their URL, not counted, not in the sitemap."""
    if not off: return ""
    lis = "".join(f'<li><a href="{root}systems/{E(c["id"])}/">{E(c["name"])}</a> <span class="unk">{E(short_company(c))}, {c["year"]}, {E(T("status.word_" + card_status(c)))} {E(c["status_date"])}</span><div class="stage-d">{E(c["status_reason"].strip())}</div></li>' for c in sorted(off, key=lambda c: (c["status_date"], c["name"]), reverse=True))
    return f'<details class="archive" id="archive"><summary>{E(T("archive.summary", n=len(off)))}</summary><ul class="clean">{lis}</ul></details>'

def home(cards, ev=(), today="", off=()):
    root = ""
    cards = [c for c in cards if is_active(c)]
    n = len(cards)
    used_p = [p for p in PARADIGMS if any(p in c["paradigms"] for c in cards)]
    fam = TAXONOMY["paradigm_families"]; sg = TAXONOMY["stage_groups"]
    fam_labels = {f["id"]: T("family." + f["id"]) for f in fam}; sg_labels = {g["id"]: T("stagegroup." + g["id"]) for g in sg}
    body = f"""<div class="wrap"><section class="hero"><div class="hero-l"><h1>{E(T('hero.h1'))}</h1>
<p>{E(T('hero.p'))}</p></div>
<div class="hero-r">{subscribe_box("home", T("sub.heading_default"), compact=True).replace("{ROOT}", root)}</div></section>
{strip(ev, root, today, cards)}
<section class="filters" aria-label="{E(T('home.filters'))}"><input id="q" class="search" type="search" placeholder="{E(T('home.search_ph'))}" aria-label="{E(T('home.search_aria'))}">
{chips("era", list(ERAS), ERAS)}{chips("stage", [g["id"] for g in sg], sg_labels)}{chips("family", [f["id"] for f in fam], fam_labels)}
<div class="toggles"><label class="tog"><input type="checkbox" id="f-prod"> {E(T('home.prod_only'))}</label><label class="tog"><input type="checkbox" id="f-official"> {E(T('home.has_code'))}</label></div>
<details id="more"><summary>{E(T('home.more'))}</summary>{chips("paradigm", used_p)}{chips("evidence", list(EVID), EVID)}</details></section>
<div class="meta-row"><span id="count" role="status" aria-live="polite">{E(T('home.count', n=n))}</span><button id="reset" class="linkbtn" type="button">{E(T('home.clear'))}</button>
<label class="sortl" id="sortwrap">{E(T('home.sort'))} <select id="sort" aria-label="{E(T('home.sort_aria'))}"><option value="default">{E(T('home.sort_default'))}</option><option value="cites">{E(T('home.sort_cites'))}</option></select></label>
<div class="seg" role="group" aria-label="{E(T('home.view'))}"><button type="button" data-view="list" aria-pressed="true">{E(T('home.view_list'))}</button><button type="button" data-view="timeline" aria-pressed="false">{E(T('home.view_timeline'))}</button></div></div>
<div class="grid" id="grid">{"".join(card_html(c, root) for c in cards)}</div>
{timeline_html(cards, root)}
<div id="empty" class="panel" hidden>{T('home.empty', btn=f'<button class="linkbtn" type="button" id="reset2">{E(T("home.empty_btn"))}</button>')}</div>
{archive_html(off, root)}</div>
<div class="cmpbar" id="cmpbar"><span id="cmpn"></span><a id="cmplink" href="compare/">{E(T('card.compare'))}</a></div>"""
    sr = sroot(root)
    return page(T("home.title"), T("home.desc"), body, root, "", scripts=f'{js_l10n()}<script src="{sr}static/carousel.js"></script><script src="{sr}static/app.js"></script>')

def kv(label, val):
    return f'<div class="fact"><small>{E(label)}</small>{val}</div>'


def has_official(c): return c["code"]["status"] in ("official_full","official_partial")

def short_company(c): return c["company"].split(" (")[0].split(" /")[0]
# ---- diagrams: data/diagrams/<id>.yaml -> inline SVG (one house style: inputs -> core -> outputs) ----
DIAGRAMS = {}
CITES = {}   # card id -> {count, source, source_url, fetched_on, ...} from data/citations.json (generated by scripts/citations.py)
BOX_W, GAP_X, PAD_X, TOP, LH = 144, 52, 16, 34, 16
KIND_STYLE = {"input": ("#f4f4f5", "#d4d4d8", "#18181b"), "module": ("#eef2ff", "#a5b4fc", "#312e81"), "output": ("#ecfdf5", "#6ee7b7", "#064e3b")}

def _wrap(t, n):
    """Wrap a diagram line. Latin text wraps at n characters; Chinese wraps by display width (a Chinese character counts 2)."""
    import textwrap
    if not CJK.search(t): return textwrap.wrap(t, n, break_long_words=False) or [""]
    lim = 18 if n <= 17 else 20; lines, cur, w = [], "", 0
    for tok in re.findall(r"[^\s\u3400-\u9fff\uff0c\u3002\u3001\uff1b\uff1a]+|[\u3400-\u9fff]|[\uff0c\u3002\u3001\uff1b\uff1a]|\s+", t):
        tw = len(tok) if tok.strip() and not CJK.match(tok) and tok[0] not in "\uff0c\u3002\u3001\uff1b\uff1a" else (2 if tok.strip() else 1)
        punct = tok[0] in "\uff0c\u3002\u3001\uff1b\uff1a"
        if w + tw > lim and cur and not punct:
            lines.append(cur.rstrip()); cur, w = "", 0
            if not tok.strip(): continue
        cur += tok; w += tw
    if cur.strip(): lines.append(cur.rstrip())
    return lines or [""]

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

# ---- deployment and cost block (every active card), see schema/schema.md "Deployment block" ----
NR = "not_reported"
DEP_SCALARS = ("ab_traffic", "ab_duration", "baseline", "training_compute", "serving_latency", "serving_qps", "inference_cost", "hardware")
DEP_KEYS = ("online_evidence", "scenario", "online_lifts", "basis", "checked_on") + DEP_SCALARS
DEP_OPTIONAL = ("notes", "fulltext_refs")
DEP_BASIS = ("card_content", "full_text")
_NUM = lambda t: set(re.findall(r"\d+(?:[.,]\d+)*", str(t).replace(",", "")))

def _dep_text(d):
    """All displayed text of a deployment block except fulltext_refs, the audit trail."""
    parts = [d.get("scenario", "")] + [d.get(k, "") for k in DEP_SCALARS] + list(d.get("notes") or [])
    if isinstance(d.get("online_lifts"), list): parts += [f'{x.get("metric", "")} {x.get("value", "")}' for x in d["online_lifts"] if isinstance(x, dict)]
    return " ".join(str(x) for x in parts if x != NR)

def check_deployment(cards):
    """Every active card needs a deployment block. A field is either the marker not_reported or real text, never a free-text 'not reported'.
    Numbers in the block must appear in the card's own other fields, or in fulltext_refs, which then requires basis full_text."""
    errs = []
    for c in cards:
        i, d = c["id"], c.get("deployment")
        if d is None:
            if is_active(c): errs.append(f"{i}: active card needs a deployment block")
            continue
        if not isinstance(d, dict): errs.append(f"{i}: deployment must be a mapping"); continue
        for k in DEP_KEYS:
            if k not in d: errs.append(f"{i}: deployment missing {k}")
        for k in d:
            if k not in DEP_KEYS + DEP_OPTIONAL: errs.append(f"{i}: deployment has unknown key {k}")
        ev = d.get("online_evidence")
        if ev not in DEP_EVID: errs.append(f"{i}: deployment.online_evidence must be one of {sorted(DEP_EVID)}")
        for k in ("scenario",) + DEP_SCALARS:
            v = d.get(k)
            if not (isinstance(v, str) and v.strip()): errs.append(f"{i}: deployment.{k} must be a non-empty string, or {NR}")
            elif v != NR and re.match(r"(?i)\s*(not reported|unknown|n/?a|none|tbd)\b", v): errs.append(f"{i}: deployment.{k} must use the marker {NR}, not free text {v!r}")
            elif k == "scenario" and v == NR: errs.append(f"{i}: deployment.scenario is required")
        lf = d.get("online_lifts")
        if lf != NR:
            if not (isinstance(lf, list) and lf): errs.append(f"{i}: deployment.online_lifts must be {NR} or a non-empty list")
            else:
                for x in lf:
                    if not (isinstance(x, dict) and set(x) == {"metric", "value"} and all(isinstance(x[a], str) and x[a].strip() and x[a] != NR for a in x)): errs.append(f"{i}: bad online_lifts entry {x}")
        if ev == "online_numbers" and lf == NR: errs.append(f"{i}: online_numbers needs online_lifts")
        if ev in ("online_qualitative", "deployed_only", "no_online_claim") and lf != NR: errs.append(f"{i}: {ev} must have online_lifts {NR}")
        online_rows = (c.get("results_table") or {}).get("online") or []
        if online_rows and ev in ("deployed_only", "no_online_claim"): errs.append(f"{i}: card has online result rows, so online_evidence cannot be {ev}")
        if d.get("basis") not in DEP_BASIS: errs.append(f"{i}: deployment.basis must be one of {DEP_BASIS}")
        co = d.get("checked_on")
        if not (isinstance(co, str) and valid_date(co) and co <= datetime.date.today().isoformat()): errs.append(f"{i}: deployment.checked_on must be a quoted YYYY-MM-DD date, not in the future")
        for k in DEP_OPTIONAL:
            v = d.get(k)
            if k in d and not (isinstance(v, list) and v and all(isinstance(x, str) and x.strip() for x in v)): errs.append(f"{i}: deployment.{k} must be a non-empty list of strings")
        pool = _NUM(json.dumps({k: v for k, v in c.items() if k != "deployment"}, ensure_ascii=False))
        extra = _NUM(_dep_text(d)) - pool
        if extra:
            refs = _NUM(" ".join(d.get("fulltext_refs") or []))
            if d.get("basis") != "full_text": errs.append(f"{i}: deployment numbers not found in the card: {sorted(extra)}; add fulltext_refs and set basis full_text")
            elif extra - refs: errs.append(f"{i}: deployment numbers not in the card or in fulltext_refs: {sorted(extra - refs)}")
    if errs: raise SystemExit("DEPLOYMENT BLOCK ERRORS:\n  " + "\n  ".join(errs))

def deployment_cov(cards):
    """Per-field count of reported (not not_reported) values over the cards that have the block."""
    ds = [c["deployment"] for c in cards if c.get("deployment")]
    cov = {k: sum(1 for d in ds if d[k] != NR) for k in ("online_lifts",) + DEP_SCALARS}
    cov["scenario"] = len(ds)
    return len(ds), cov

# ---- citations line (language-aware) ----
def cite_html(i):
    v = CITES.get(i)
    if not v: return ""   # no paper or no lookup: show nothing, never 0
    n = f'{v["count"]:,}'; note = f' <span class="cite-note">{E(v["note"])}</span>' if v.get("note") else ""
    nv = len(v["papers"]) if len(v["papers"]) > 1 else 0
    tot = (" " if LANG == "en" else "") + T("cite.tot", nv=nv) if nv else ""
    return '<p class="cites">' + T("cite.line", n=n, tot=tot, url=E(v["source_url"]), source=E(v["source"]), date=v["fetched_on"], note=note) + '</p>'

def vcount(i, name):
    """Small per-version citation breakdown for the version list on merged cards. Empty when there is no count."""
    v = CITES.get(i); row = next((x for x in (v or {}).get("papers", []) if x["name"] == name), None) if v and len(v.get("papers", [])) > 1 else None
    return f' <span class="cite-note">{E(T("card.citations", n=format(row["count"], ",")))}</span>' if row else ""

def sep(): return ", " if LANG == "en" else "\u3001"
def sp(): return " " if LANG == "en" else ""

# ---- diagram rendering ----
FONT_ZH = 'system-ui,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif'
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
    ff = FONT_ZH if LANG == "zh" else "sans-serif"
    style = f'<style>.dg-col{{font:700 10.5px {ff};letter-spacing:.08em;fill:#71717a}}.dg-t{{font:700 12.5px {ff}}}.dg-s{{font:12px {ff}}}.dg-e{{fill:none;stroke:#6366f1;stroke-width:1.6}}</style>'
    return f'viewBox="0 0 {W} {full:.0f}"', W, f'{defs}{style}{edges}{"".join(parts)}'

def diagram_html(i, g):
    vb, w, inner = diagram_svg(g); cap = g["caption"]
    return (f'<figure class="diagram"><div class="dg-scroll"><svg xmlns="http://www.w3.org/2000/svg" {vb} width="{w}" role="img" aria-label="{E(g["alt"])}" class="dg">{inner}</svg></div>'
            f'<figcaption>{T("diagram.cap", fig=E(cap["fig"]), url=E(cap["url"]), work=E(cap["work"]))}'
            + (f' {E(cap["note"])}' if cap.get("note") else "") + '</figcaption></figure>')

def deployment_html(c):
    d = c["deployment"]
    nr = f'<span class="unk">{E(T("nr"))}</span>'
    v = lambda k: nr if d[k] == NR else E(d[k])
    lifts = nr if d["online_lifts"] == NR else '<ul class="clean">' + "".join(f'<li>{E(x["metric"])}: <b>{E(x["value"])}</b></li>' for x in d["online_lifts"]) + '</ul>'
    rows = [(T("dep.evidence"), E(DEP_EVID[d["online_evidence"]])), (T("dep.scenario"), E(d["scenario"])), (T("dep.ab_traffic"), v("ab_traffic")), (T("dep.ab_duration"), v("ab_duration")),
            (T("dep.baseline"), v("baseline")), (T("dep.lifts"), lifts), (T("dep.compute"), v("training_compute")), (T("dep.latency"), v("serving_latency")),
            (T("dep.qps"), v("serving_qps")), (T("dep.cost"), v("inference_cost")), (T("dep.hardware"), v("hardware"))]
    t = '<div class="tbl-scroll"><table class="cmp dep"><tbody>' + "".join(f'<tr><th scope="row">{E(a)}</th><td>{b}</td></tr>' for a, b in rows) + '</tbody></table></div>'
    notes = '<ul class="clean">' + "".join(f"<li>{E(n)}</li>" for n in d["notes"]) + '</ul>' if d.get("notes") else ""
    how = T("dep.how_full") if d["basis"] == "full_text" else T("dep.how_card")
    return f'<section class="blk" id="deployment"><h2>{E(T("dep.h2"))}</h2>{t}{notes}<p class="stage-d">{E(T("dep.foot", date=d["checked_on"], how=how))}</p></section>'

# ---- topic pages: data/topics/<slug>.yaml (English) + data/i18n/zh/topics/<slug>.yaml (Chinese), see schema/schema.md "Topics" ----
def load_topics(by_id):
    """Each topic lists member card ids with a hand-written approach line, a framing text and difference sections.
    Tables are generated from the cards. Numbers in hand-written text must appear in the cited cards, and text has no parentheses."""
    errs, topics = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/topics/*.yaml"))):
        t = yaml.safe_load(open(f)); n = os.path.basename(f); t["slug"] = n[:-5]
        for k in ("title", "summary", "framing", "members", "differences"):
            if not t.get(k): errs.append(f"{n}: missing {k}")
        if errs and errs[-1].startswith(n): continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", t["slug"]): errs.append(f"{n}: slug must be lowercase words joined by hyphens")
        if len(t["summary"]) > 160: errs.append(f"{n}: summary is {len(t['summary'])} chars, max 160")
        if not (isinstance(t["framing"], list) and all(isinstance(x, str) and x.strip() for x in t["framing"])): errs.append(f"{n}: framing must be a list of paragraphs")
        mem = t["members"]; ids = [m.get("id") for m in mem if isinstance(m, dict)]
        if len(mem) < 3 or len(ids) != len(mem): errs.append(f"{n}: needs >= 3 members, each a mapping with id and approach")
        if len(set(ids)) != len(ids): errs.append(f"{n}: duplicate member id")
        pools = {}
        for m in mem:
            i = m.get("id"); c = by_id.get(i)
            if c is None or not is_active(c): errs.append(f"{n}: member {i} is not an active card"); continue
            if not str(m.get("approach", "")).strip(): errs.append(f"{n}: member {i} needs approach")
            pools[i] = _NUM(json.dumps(c, ensure_ascii=False))
            extra = _NUM(m.get("approach", "")) - pools[i]
            if extra: errs.append(f"{n}: approach of {i} has numbers not on the card: {sorted(extra)}")
        for sec in t["differences"]:
            if not (isinstance(sec, dict) and str(sec.get("heading", "")).strip() and str(sec.get("text", "")).strip() and isinstance(sec.get("cards"), list) and sec["cards"]): errs.append(f"{n}: each difference needs heading, text and cards"); continue
            bad = [i for i in sec["cards"] if i not in pools]
            if bad: errs.append(f"{n}: difference {sec['heading']!r} cites non-members {bad}"); continue
            extra = _NUM(sec["text"]) - set().union(*(pools[i] for i in sec["cards"]))
            if extra: errs.append(f"{n}: difference {sec['heading']!r} has numbers not on the cited cards: {sorted(extra)}")
        extra = _NUM(" ".join(t["framing"])) - set().union(*pools.values()) if pools else set()
        if extra: errs.append(f"{n}: framing has numbers not on any member card: {sorted(extra)}")
        alltext = " ".join([t["title"], t["summary"]] + t["framing"] + [m.get("approach", "") for m in mem] + [x for s_ in t["differences"] if isinstance(s_, dict) for x in (s_.get("heading", ""), s_.get("text", ""))])
        if re.search(r"[()]", alltext): errs.append(f"{n}: no parentheses in topic text")
        topics.append(t)
    if errs: raise SystemExit("TOPIC ERRORS:\n  " + "\n  ".join(errs))
    return topics

def zh_topics(topics, by_id, errs, warns):
    """Chinese topic texts. Same checks as the English ones: numbers in the Chinese prose must appear on the cited cards
    (the English numbers pool of those cards), no parentheses, and the Chinese file mirrors the English structure."""
    out = []
    for t in topics:
        n = f"zh/topics/{t['slug']}.yaml"; p = os.path.join(I18N, "zh", "topics", t["slug"] + ".yaml")
        if not os.path.exists(p):
            if not ALLOW_MISSING: errs.append(f"{n}: missing file")
            out.append(t); continue
        z = yaml.safe_load(open(p)); e0 = len(errs)
        for k in ("title", "summary", "framing", "members", "differences"):
            if not z.get(k): errs.append(f"{n}: missing {k}")
        if len(errs) > e0: out.append(t); continue
        if len(z["summary"]) > 100: errs.append(f"{n}: summary is {len(z['summary'])} chars, max 100")
        if len(z["framing"]) != len(t["framing"]): errs.append(f"{n}: framing needs {len(t['framing'])} paragraphs")
        if [m.get("id") for m in z["members"]] != [m["id"] for m in t["members"]]: errs.append(f"{n}: members must list the same ids in the same order")
        if len(z["differences"]) != len(t["differences"]): errs.append(f"{n}: differences needs {len(t['differences'])} entries")
        if len(errs) > e0: out.append(t); continue
        pools = {m["id"]: _NUM(json.dumps(by_id[m["id"]], ensure_ascii=False)) for m in t["members"]}
        allpool = set().union(*pools.values())
        srcs = {m["id"]: json.dumps(by_id[m["id"]], ensure_ascii=False) for m in t["members"]}
        def chk(label, text, pool, ids=None):
            if PARENS.search(text): errs.append(f"{n}: {label}: no parentheses in Chinese copy")
            extra, probs = zh_number_problems(text, " ".join(srcs[i] for i in (ids or srcs)), pool)
            if extra: errs.append(f"{n}: {label}: numbers not on the cited cards: {sorted(extra)}")
            for pr in probs: errs.append(f"{n}: {label}: {pr}")
            if not CJK.search(text): errs.append(f"{n}: {label}: not Chinese")
        chk("title", z["title"], allpool); chk("summary", z["summary"], allpool)
        for k, x in enumerate(z["framing"]): chk(f"framing.{k}", x, allpool)
        for m in z["members"]: chk(f"member {m['id']}", m["approach"], pools[m["id"]], [m["id"]])
        zt = dict(t); zt.update({"title": z["title"], "summary": z["summary"], "framing": z["framing"]})
        zt["members"] = [{"id": m["id"], "approach": zm["approach"]} for m, zm in zip(t["members"], z["members"])]
        zt["differences"] = []
        for k, (sec, zs) in enumerate(zip(t["differences"], z["differences"])):
            pool = set().union(*(pools[i] for i in sec["cards"]))
            chk(f"differences.{k}.heading", zs["heading"], pool, sec["cards"]); chk(f"differences.{k}.text", zs["text"], pool, sec["cards"])
            zt["differences"].append({"heading": zs["heading"], "text": zs["text"], "cards": sec["cards"]})
        out.append(zt)
    return out

def topic_page(t, by_id):
    root = "../../"
    nr = f'<span class="unk">{E(T("nr"))}</span>'
    link = lambda i: f'<a href="{root}systems/{E(i)}/">{E(by_id[i]["name"])}</a>'
    trs = ""
    for m in t["members"]:
        c = by_id[m["id"]]; d = c["deployment"]
        res = (('<ul class="clean">' + "".join(f'<li>{E(x["metric"])}: <b>{E(x["value"])}</b></li>' for x in d["online_lifts"][:2]) + '</ul>') if d["online_lifts"] != NR else E(DEP_EVID[d["online_evidence"]])) \
              + (f'<div class="stage-d">{E(T("topic.vs", b=d["baseline"]))}</div>' if d["baseline"] != NR and d["online_lifts"] != NR else "")
        trs += (f'<tr><td><b>{link(c["id"])}</b><div class="stage-d">{E(short_company(c))}, {c["year"]}</div></td><td>{E(m["approach"])}</td><td>{res}</td>'
                f'<td>{nr if d["serving_latency"] == NR else E(d["serving_latency"])}</td><td>{nr if d["hardware"] == NR else E(d["hardware"])}</td></tr>')
    table = (f'<div class="tbl-scroll"><table class="cmp restab topic"><thead><tr><th>{E(T("topic.th_system"))}</th><th>{E(T("topic.th_approach"))}</th><th>{E(T("topic.th_online"))}</th><th>{E(T("topic.th_latency"))}</th><th>{E(T("topic.th_hardware"))}</th></tr></thead><tbody>' + trs + '</tbody></table></div>'
             f'<p class="stage-d">{E(T("topic.foot"))}</p>')
    diffs = "".join(f'<section class="blk"><h2>{E(s_["heading"])}</h2><p>{E(s_["text"])}</p><p class="stage-d">{E(T("topic.cards"))} ' + sep().join(link(i) for i in s_["cards"]) + '</p></section>' for s_ in t["differences"])
    body = (f'<div class="wrap"><article class="sys"><div class="crumbs"><a href="{root}topics/">{E(T("nav.topics"))}</a> / {E(t["title"])}</div><h1>{E(t["title"])}</h1>'
            + "".join(f'<p class="lead">{E(p_)}</p>' for p_ in t["framing"]) + f'<section class="blk" id="table"><h2>{E(T("topic.compared"))}</h2>{table}</section>'
            + f'<h2 class="topic-h">{E(T("topic.differ"))}</h2>{diffs}'
            + f'<p><a class="btn" href="{root}compare/?ids=' + ",".join(m["id"] for m in t["members"][:3]) + f'">{E(T("topic.compare_btn"))}</a></p>'
            + subscribe_box("topic:" + t["slug"]).replace("{ROOT}", root) + '</article></div>')
    return page(T("topic.title", t=t["title"]), t["summary"], body, root, f'topics/{t["slug"]}/')

def topics_index(topics):
    root = "../"
    items = "".join(f'<li><a href="{root}topics/{E(t["slug"])}/"><b>{E(t["title"])}</b></a> <span class="stage-d">{E(T("home.count", n=len(t["members"])))}</span><div>{E(t["summary"])}</div></li>' for t in topics)
    body = (f'<div class="wrap"><article class="sys"><h1>{E(T("nav.topics"))}</h1><p class="lead">{E(T("topics.lead"))}</p>'
            f'<ul class="clean topics">{items}</ul></article></div>')
    return page(T("topics.title"), T("topics.desc"), body, root, "topics/")

def card_page(c):
    """Card detail page. Section order is fixed, the architecture block only when a diagram exists; tests/v2_order.test.js checks it."""
    root = "../../"; cd = c["code"]; st = card_status(c)
    unk = f'<span class="unk">{E(T("card.unk"))}</span>'
    ps = next(x for x in c["sources"] if x["url"] == c["primary_source"])
    paper_btn = f'<a class="btn" href="{E(ps["url"])}" rel="noopener nofollow" target="_blank">{E(T("card.paper") if ps["type"] == "paper" else T("card.primary"))}' + (f' <small>{E(c["venue"])}</small>' if c.get("venue") else "") + '</a>'
    off = [r for r in cd["repos"] if r["official"]]
    if off: code_btn = f'<a class="btn btn-code" href="{E(off[0]["url"])}" rel="noopener nofollow" target="_blank">{E(T("card.code"))} <small>{E(T("card.official"))}</small></a>'
    elif cd["repos"]: code_btn = f'<a class="btn btn-alt" href="{E(cd["repos"][0]["url"])}" rel="noopener nofollow" target="_blank">{E(T("card.code"))} <small>{E(T("card.unofficial"))}</small></a>'
    else: code_btn = f'<span class="btn btn-off" aria-disabled="true">{E(T("card.no_code"))}</span>'
    stage_names = []
    for s_ in c["stages"]:
        n_ = STAGE_LABEL.get(s_["stage"], s_["stage"])
        if n_ not in stage_names: stage_names.append(n_)
    stage_badges = "".join(f'<span class="badge b-stage">{E(n_)}</span>' for n_ in stage_names)
    venue = c.get("venue") or T("card.preprint")
    byline = f'{E(c["company"])} &middot; {c["year"]} &middot; {E(venue)}'
    cell = lambda label, val: f'<div class="kf"><small>{E(label)}</small><div>{val}</div></div>'
    code_cell = f'<span class="badge b-code-{E(cd["status"])}">{E(CODE_STATUS[cd["status"]])}</span>'
    has_dg = c["id"] in DIAGRAMS
    toc = ([("architecture", T("sec.architecture"))] if has_dg else []) + [("how-it-works", T("sec.how")), ("results", T("sec.results")), ("deployment", T("dep.h2")), ("details", T("sec.details")), ("limitations", T("sec.limits")), ("sources", T("sec.sources")), ("history", T("sec.history"))]
    toc_h = f'<nav class="toc" aria-label="{E(T("card.onpage"))}"><b>{E(T("card.onpage"))}</b>' + "".join(f'<a href="#{i}"' + (' onclick="document.getElementById(\'details\').open=true"' if i == "details" else "") + f'>{E(t)}</a>' for i, t in toc) + '</nav>'
    keyfacts = (f'<section class="keyfacts" id="key-facts" style="--kfspan:KFSPAN" aria-labelledby="h-key-facts"><h2 id="h-key-facts">{E(T("kf.h2"))}</h2><div class="kfgrid">'
        + cell(T("kf.stage"), E(" + ".join(stage_names))) + cell(T("kf.core"), E(c["core_idea"])) + cell(T("kf.deployed"), E(c["deployed_in"]))
        + cell(T("kf.scale"), E(c["scale_short"])) + cell(T("kf.result"), E(c["key_result"])) + cell(T("kf.code"), code_cell)
        + f'</div>{toc_h}</section>')
    arch = f'<section class="blk" id="architecture"><h2>{E(T("sec.architecture"))}</h2>{diagram_html(c["id"], DIAGRAMS[c["id"]])}</section>' if has_dg else ""
    stages = "".join(f'<div class="stagebox"><b>{E(STAGE_LABEL.get(s_["stage"], s_["stage"]))}</b><div>{E(s_.get("model_family") or T("card.unknown_word"))}</div><div class="stage-d">{E((s_.get("details") or "").strip())}</div></div>' for s_ in c["stages"])
    rt = c["results_table"]
    def rows(kind, label):
        r_ = rt.get(kind) or []
        if not r_: return ""
        return f'<tbody><tr class="grp"><th colspan="5">{E(label)}</th></tr>' + "".join(f'<tr><td>{E(r["setting"])}</td><td>{E(r["method"])}</td><td>{E(r["metric"])}</td><td class="num"><b>{E(r["result"])}</b></td><td>{E(r["versus"])}</td></tr>' for r in r_) + '</tbody>'
    table = (f'<div class="tbl-scroll"><table class="cmp restab"><thead><tr><th>{E(T("rt.setting"))}</th><th>{E(T("rt.method"))}</th><th>{E(T("rt.metric"))}</th><th>{E(T("rt.result"))}</th><th>{E(T("rt.versus"))}</th></tr></thead>'
             + rows("online", T("rt.online")) + rows("offline", T("rt.offline")) + rows("other", T("rt.other")) + '</table></div>') if any(rt.get(g) for g in ("online", "offline", "other")) else ""
    note = f'<p class="stage-d">{E(rt["note"])}</p>' if rt.get("note") else ""
    idt = c["id_tokenization"]
    idh = f'<p>{E(idt.get("approach") or "") or unk}</p>' + (f'<p class="stage-d">{E(idt["details"])}</p>' if idt.get("details") else "")
    tr = c["training"]; uw = T("card.unknown_word")
    trh = f'<ul class="clean"><li><b>{E(T("tr.mode"))}</b>{sp()}{E(tr.get("mode") or uw)}</li><li><b>{E(T("tr.obj"))}</b>{sp()}{E(sep().join(tr.get("objectives") or []) or uw)}</li>' + (f'<li>{E(tr["notes"])}</li>' if tr.get("notes") else "") + "</ul>"
    feats = "<ul class='clean'>" + "".join(f"<li>{E(f)}</li>" for f in c["features_signals"]) + "</ul>" if c["features_signals"] else unk
    sc = "<ul class='clean'>" + "".join(f'<li><b>{E(s_["metric"])}:</b> {E(str(s_["value"]))}</li>' for s_ in c["scale"]) + "</ul>" if c["scale"] else ""
    serving = f'<p>{E(c["serving_infra"]) if c["serving_infra"] else unk}</p>' + sc
    details = (f'<details id="details" class="tech"><summary><h2 id="h-details">{E(T("sec.details"))}</h2></summary>'
        f'<h3>{E(T("det.features"))}</h3>{feats}<h3>{E(T("det.training"))}</h3>{trh}<h3>{E(T("det.serving"))}</h3>{serving}<h3>{E(T("det.idtok"))}</h3>{idh}</details>')
    lim_items = [E(x) for x in c["caveats"]] + ([E(c["version_note"])] if c.get("version_note") else []) + ([f'<span class="unk">{E(T("lim.unknown", fields=sep().join(c["unknown_fields"])))}</span>'] if c["unknown_fields"] else [])
    limits = f'<section class="blk" id="limitations"><h2>{E(T("sec.limits"))}</h2><div class="caveat"><ul class="clean">{"".join(f"<li>{x}</li>" for x in lim_items)}</ul></div></section>' if lim_items else ""
    earlier = {v_["source"]: v_["name"] for v_ in (c.get("versions") or []) if v_["name"] != c.get("version")}
    srcs = "<ul class='clean'>" + "".join(f'<li><a href="{E(s_["url"])}" rel="noopener nofollow" target="_blank">{E(s_["title"])}</a> <span class="tag stage">{E(T("srctype." + s_["type"]))}</span>' + (f' <span class="tag stage">{E(T("card.other_version", v=earlier[s_["url"]]))}</span>' if s_["url"] in earlier else "") + '</li>' for s_ in c["sources"]) + "</ul>"
    repos = "".join(f'<li><a href="{E(r["url"])}" rel="noopener nofollow" target="_blank">{E(r["url"][len("https://github.com/"):])}</a> <span class="tag stage">{E(T("card.official") if r["official"] else T("card.unofficial"))}</span><div class="stage-d">{E(r["owner"])}{". " if LANG == "en" else "\u3002"}{E(r["note"])}</div></li>' for r in cd["repos"])
    codeblk = f'<h3>{E(T("card.code"))}</h3><ul class="clean">{repos}</ul>' if repos else f'<h3>{E(T("card.code"))}</h3><p class="unk">{E(cd.get("note") or T("card.no_code_found"))}</p>'
    h_items = [(c["added_on"], "added", T("hist.published"))] + [(u["date"], "updated", u["note"]) for u in c.get("updates") or []] + ([(c["status_date"], st, c["status_reason"].strip())] if st != "active" else [])
    vers = (f'<h3>{E(T("ver.h3"))}</h3><ul class="clean versions">' + "".join(f'<li><time datetime="{E(v_["first_public"])}">{E(v_["first_public"])}</time> <b>{E(v_["name"])}</b>' + (f' <span class="k k-added">{E(T("ver.here"))}</span>' if v_["name"] == c["version"] else "") + f' <a href="{E(v_["source"])}" rel="noopener nofollow" target="_blank">{E(T("ver.source"))}</a>' + vcount(c["id"], v_["name"]) + f'<div class="stage-d">{E(v_["note"])}</div></li>' for v_ in reversed(c["versions"])) + '</ul>') if c.get("versions") else ""
    cmp_btn = f'<p><a class="btn" href="{root}compare/?ids={E(c["id"])}">{E(T("hist.compare"))}</a></p>' if st == "active" else ""
    hist = (f'<section class="blk" id="history"><h2>{E(T("sec.history"))}</h2>' + vers + '<ul class="clean changelog">' + "".join(f'<li><time datetime="{d}">{d}</time> <span class="k k-{k}">{E(T("kind." + k) if k in KIND_LABEL else T("status.superseded"))}</span> {E(n)}</li>' for d, k, n in sorted(h_items, reverse=True))
            + f'</ul><p class="unk">{E(T("hist.verified", date=c["last_verified"]))}</p>'
            + f'{cmp_btn}</section>')
    if not limits: keyfacts = keyfacts.replace(f'<a href="#limitations">{E(T("sec.limits"))}</a>', "")
    if not c.get("deployment"): keyfacts = keyfacts.replace(f'<a href="#deployment">{E(T("dep.h2"))}</a>', "")
    keyfacts = keyfacts.replace("KFSPAN", str(6 + bool(arch) + bool(limits) + bool(c.get("deployment"))))
    sup = " " + T("status.replaced", href=f'{root}systems/{E(c["superseded_by"])}/', name=E(c["superseded_by"])) if c.get("superseded_by") else ""
    notice = (f'<aside class="status-note status-{st}" id="status-note" role="note"><b>{E(T("status.on_" + st, date=c["status_date"]))}</b> {E(c["status_reason"].strip())}{sup} '
              f'{E(T("status.stays"))}</aside>') if st != "active" else ""
    if c.get("versions"):
        latest_here = c["versions"][-1]["name"] == c["version"]
        vb = T("ver.badge_latest", v=E(c["version"]), n=len(c["versions"])) if latest_here else T("ver.badge_older", v=E(c["version"]), n=len(c["versions"]), latest=E(c["versions"][-1]["name"]))
        vbadge = f'<span class="badge b-version">{vb}</span>'
    else: vbadge = ""
    body = f"""<div class="wrap"><article class="sys v2"><div class="crumbs"><a href="{root}">{E(T('nav.systems'))}</a> / {E(short_company(c))}</div>{notice}
<header class="v2head" id="top"><h1>{E(c['name'])}</h1><p class="byline">{byline}</p>
<div class="tags" style="margin:0 0 14px"><span class="badge b-era b-era-{E(c['era'])}">{E(ERAS[c['era']])}</span>{stage_badges}<span class="badge b-{E(c['evidence_level'])}">{E(EVID[c['evidence_level']])}</span>{vbadge}</div>
<div class="tldr"><span class="tldr-l">TL;DR</span><p>{E(c['tldr'].strip())}</p></div>
<div class="actions">{paper_btn}{code_btn}</div>{cite_html(c["id"])}</header>
<div class="v2grid">{keyfacts}
{arch}
<section class="blk" id="how-it-works"><h2>{E(T('sec.how'))}</h2><p class="lead">{E(c['summary'].strip())}</p>{stages}</section>
<section class="blk" id="results"><h2>{E(T('sec.results'))}</h2>{table}{note}</section>
{deployment_html(c) if c.get("deployment") else ""}
<div id="subscribe">{subscribe_box("card:" + c["id"], T("sub.heading_card")).replace("{ROOT}", root)}</div>
{details}
{limits}
<section class="blk" id="sources"><h2>{E(T('sec.sources'))}</h2>{srcs}{codeblk}</section>
{hist}</div></article></div>"""
    title = T("card.title", name=c["name"], company=c["company"], year=c["year"])
    desc = T("card.desc", name=c["name"], company=c["company"], summary=c["summary"].strip())[:158]
    ld = {"@context":"https://schema.org","@type":"TechArticle","headline":c["name"],"inLanguage":LANG_TAG[LANG],"about":c["surface"],"datePublished":c["added_on"],"dateModified":c["last_verified"],
          "citation":[s_["url"] for s_ in c["sources"]],"publisher":{"@type":"Organization","name":"RecArch"}}
    head = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' + ('' if st == "active" else '<meta name="robots" content="noindex">')
    if st != "active": title = T("status.title_" + st, title=title)
    return page(title, desc, body, root, f"systems/{c['id']}/", extra_head=head)

def redirect_page(c):
    """Old URL of a card merged into another (status superseded): static redirect, canonical points at the merged card, in the same language."""
    to = c["superseded_by"]; canon = abs_url(LANG, f"systems/{to}/")
    return f"""<!doctype html><html lang="{LANG_TAG[LANG]}"><head><meta charset="utf-8"><title>{E(T("redirect.title", name=by_id_name(to)))}</title>
<link rel="canonical" href="{E(canon)}"><meta http-equiv="refresh" content="0; url=../{E(to)}/"><meta name="robots" content="noindex"></head>
<body><p>{T("redirect.text", old=E(c["name"]), href=f"../{E(to)}/", new=E(by_id_name(to)))}</p></body></html>"""

NAMES = {}
def by_id_name(i): return NAMES.get(i, i)

def compare_page():
    root = "../"
    body = f"""<div class="wrap"><article class="sys"><h1>{E(T('compare.h1'))}</h1><p class="lead">{E(T('compare.lead'))}</p>
<div id="picker" class="controls"></div><div id="out"></div>{subscribe_box("compare").replace("{ROOT}", root)}</article></div>"""
    return page(T("compare.title"), T("compare.desc"), body, root, "compare/", scripts=f'{js_l10n()}<script>window.RECARCH_ROOT="{root}"</script><script src="{sroot(root)}static/compare.js"></script>')

def sponsor_page():
    root = "../"
    body = f"""<div class="wrap"><article class="sys"><h1>{E(T('sponsor.h1'))}</h1><p class="lead">{E(T('sponsor.lead'))}</p>
<div class="panel"><span class="todo">{E(T('sponsor.todo'))}</span>
<p>{E(T('sponsor.p'))}</p>
<ul class="clean"><li>{E(T('sponsor.audience'))}</li><li>{E(T('sponsor.formats'))}</li><li>{E(T('sponsor.pricing'))} <span class="unk">{E(T('sponsor.notset'))}</span></li><li>{E(T('sponsor.contact'))} <span class="unk">{E(T('sponsor.todo_contact'))}</span></li></ul></div></article></div>"""
    return page(T("sponsor.title"), T("sponsor.desc"), body, root, "sponsor/")

def about_page(n):
    root = "../"
    body = f"""<div class="wrap"><article class="sys"><h1>{E(T('about.h1'))}</h1><p class="lead">{E(T('about.lead'))}</p>
<ul class="clean"><li>{E(T('about.l1'))}</li>
<li>{E(T('about.l2'))}</li>
<li>{E(T('about.l3'))}</li><li>{E(T('about.l4'))}</li></ul></article></div>"""
    return page(T("about.title"), T("about.desc"), body, root, "about/")

def write(path, content):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)

def not_found_page(root, bilingual):
    """404. GitHub Pages serves the root 404.html at any depth, so links use the site's absolute base path: zh first, English below."""
    base = (urlparse(SITE_URL).path.rstrip("/") + "/")
    if bilingual:
        body = (f'<div class="wrap"><article class="sys"><h1>{E(T("nf.h1"))}</h1><p><a href="{base}">{E(T("nf.back"))}</a></p>'
                f'<h2 lang="en" style="margin-top:28px">Not found</h2><p lang="en">That page does not exist. <a href="{base}en/">Back to all systems</a></p></article></div>')
    else:
        body = f'<div class="wrap"><article class="sys"><h1>{E(T("nf.h1"))}</h1><p><a href="{root}">{E(T("nf.back"))}</a></p></article></div>'
    return page(T("nf.title"), T("nf.h1"), body, root, "404.html", extra_head='<meta name="robots" content="noindex">')

def loc_site(site, lang):
    s = dict(site)
    if lang == "zh": s["events"] = [dict(e, title=e["title_zh"], note=e.get("note_zh", "")) for e in site.get("events") or []]
    return s

def loc_issue(i, lang):
    if lang == "en": return i
    z = dict(i); z.update(title=i["title_zh"], summary=i["summary_zh"], body=i["body_zh"])
    z["papers"] = [dict(p, note=p.get("note_zh", p.get("note"))) for p in i.get("papers") or []]
    return z

def check_site_zh(site, issues, errs, warns):
    for n, e in enumerate(site.get("events") or []):
        if not str(e.get("title_zh", "")).strip(): errs.append(f"site.yaml event {n}: missing title_zh")
        else: check_zh_text(f"site.yaml event {n} title_zh", e["title"], e["title_zh"], errs, warns)
        if e.get("note"):
            if not str(e.get("note_zh", "")).strip(): errs.append(f"site.yaml event {n}: missing note_zh")
            else: check_zh_text(f"site.yaml event {n} note_zh", e["note"], e["note_zh"], errs, warns)
    for i in issues:
        for k in ("title", "summary", "body"):
            if not str(i.get(k + "_zh", "")).strip(): errs.append(f"newsletter {i['slug']}: missing {k}_zh")
            else: check_zh_text(f"newsletter {i['slug']} {k}_zh", i[k], i[k + "_zh"], errs, warns)
        for n, p in enumerate(i.get("papers") or []):
            if p.get("note") and not str(p.get("note_zh", "")).strip(): errs.append(f"newsletter {i['slug']}: paper {n} needs note_zh")
            elif p.get("note"): check_zh_text(f"newsletter {i['slug']} paper {n} note_zh", p["note"], p["note_zh"], errs, warns)

def main():
    global SITE, EN_CARDS
    load_companies(); set_lang("en")
    allc = load_cards(); SITE = load_site(); check_v2(allc); check_deployment(allc); TAXONOMY.update(load_taxonomy()); diag_en = load_diagrams(allc); CITES.update(load_citations(allc))
    by_id = {c["id"]: c for c in allc}; issues = load_issues(by_id)
    topics = load_topics(by_id)
    # Chinese data: every required string present, no number or parenthesis the English source does not have
    errs, warns = [], []
    zcards = [zh_card(c, errs, warns) for c in allc]
    diag_zh = {i: zh_diagram(i, g, errs, warns) for i, g in diag_en.items()}
    topics_zh = zh_topics(topics, by_id, errs, warns); check_site_zh(SITE, issues, errs, warns)
    if errs: sys.exit(f"I18N ERRORS ({len(errs)}):\n  " + "\n  ".join(errs[:80]) + (f"\n  ... {len(errs) - 80} more" if len(errs) > 80 else ""))
    if warns:
        print(f"i18n: {len(warns)} fields where a number of the English text is not in the Chinese text (RECARCH_I18N_VERBOSE=1 lists them)")
        if os.environ.get("RECARCH_I18N_VERBOSE") == "1": print("\n".join("  " + w for w in warns))
    EN_CARDS.update(by_id)
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"))   # shared by both languages, at the site root
    today = datetime.date.today().isoformat(); urls = []; lastmod = None
    for lang in LANGS:
        set_lang(lang); pre = lang_prefix(lang)
        cl = zcards if lang == "zh" else allc
        DIAGRAMS.clear(); DIAGRAMS.update(diag_zh if lang == "zh" else diag_en)
        by_idl = {c["id"]: c for c in cl}; NAMES.clear(); NAMES.update({c["id"]: c["name"] for c in cl})
        cards = [c for c in cl if is_active(c)]; off = [c for c in cl if not is_active(c)]   # retired and superseded: page built, but no list, count, carousel, feed card event or sitemap entry
        issues_l = [loc_issue(i, lang) for i in issues]; ev = events(cards, loc_site(SITE, lang), issues_l, off)
        topics_l = topics_zh if lang == "zh" else topics
        w = lambda path, content: write(pre + path, content)
        w("index.html", home(cards, ev, today, off))
        for c in cl: w(f"systems/{c['id']}/index.html", redirect_page(c) if card_status(c) == "superseded" else card_page(c))
        w("topics/index.html", topics_index(topics_l))
        for t in topics_l: w(f"topics/{t['slug']}/index.html", topic_page(t, by_idl))
        w("compare/index.html", compare_page()); w("newsletter/index.html", newsletter_page(issues_l, cards))
        for i in issues_l: w(f"newsletter/{i['slug']}/index.html", issue_page(i, by_idl))
        w("changelog/index.html", changelog_page(ev)); w("feed.xml", feed_xml(ev))
        w("about/index.html", about_page(len(cards)))
        w("data/systems.json", json.dumps(cards, ensure_ascii=False))   # active only: compare picker
        if lang == "zh":
            lastmod = {"home": ev[0]["date"] if ev else today, "ev": ev[0]["date"], "issue": issues[0]["date"] if issues else ev[0]["date"], "cards": {c["id"]: c["last_verified"] for c in cards}}
            urls = [("", lastmod["home"])] + [(f"systems/{c['id']}/", c["last_verified"]) for c in cards] + [("changelog/", lastmod["ev"]), ("newsletter/", lastmod["issue"])] + [(f"newsletter/{i['slug']}/", i["date"]) for i in issues] + [("topics/", lastmod["ev"])] + [(f"topics/{t['slug']}/", lastmod["ev"]) for t in topics] + [("compare/", lastmod["ev"]), ("about/", lastmod["ev"])]
    # 404: GitHub Pages only serves the root file, so it is bilingual. en/404.html mirrors it for other hosts.
    base = (urlparse(SITE_URL).path.rstrip("/") + "/")
    set_lang("zh"); write("404.html", not_found_page(base, True))
    set_lang("en"); write("en/404.html", not_found_page(base + "en/", False))
    xh = lambda u: "".join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{abs_url(l, u)}"/>' for h, l in (("zh-CN", "zh"), ("en", "en"))) + f'<xhtml:link rel="alternate" hreflang="x-default" href="{abs_url("zh", u)}"/>'
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
          + "".join(f"<url><loc>{abs_url(l, u)}</loc><lastmod>{d}</lastmod>{xh(u)}</url>\n" for u, d in urls for l in LANGS) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"built {len(allc)} card pages, {len(allc) - len([c for c in allc if not is_active(c)])} active, {len([c for c in allc if not is_active(c)])} retired or superseded, in zh and en -> {OUT}")

set_lang("en")
if __name__ == "__main__": main()
