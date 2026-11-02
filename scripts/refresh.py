#!/usr/bin/env python3
"""RecArch refresh stub.

Pulls candidate posts from company engineering-blog feeds and arXiv cs.IR, filters by recsys keywords,
and APPENDS new candidates to review_queue.jsonl with status "pending". It never touches data/systems/ and never publishes.
A human reviews each candidate, reads the source, then writes a card by hand.

Usage: python3 scripts/refresh.py [--days 14] [--no-arxiv]
Stdlib only. Feed URLs are best-effort and may change; failures are reported, not fatal.
"""
import argparse, datetime as dt, json, os, re, sys, urllib.request, urllib.parse, xml.parsers.expat
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "review_queue.jsonl")
MAX_FEED_BYTES = 5_000_000
# TODO: verify each URL before relying on it; add/remove feeds as needed.
FEEDS = {
    "Netflix": "https://netflixtechblog.com/feed",
    "Pinterest": "https://medium.com/feed/pinterest-engineering",
    "DoorDash": "https://careersatdoordash.com/engineering-blog/feed/",
    "Airbnb": "https://medium.com/feed/airbnb-engineering",
    "Spotify": "https://engineering.atspotify.com/feed/",
    "Meta Engineering": "https://engineering.fb.com/feed/",
    "Instacart": "https://tech.instacart.com/feed",
    "Etsy": "https://www.etsy.com/codeascraft/rss",
}
# Checked 2026-11-02. Neither site publishes a working first-party feed anymore, so they are not fetched.
DISABLED = {
    "Uber": "https://www.uber.com/en-US/blog/engineering/rss/ redirects to https://www.uber.com/us/en/blog/engineering/rss/, which returns HTTP 406 with the default headers and HTTP 404 for every Accept value tried (rss/atom/xml/html and a browser User-Agent). https://www.uber.com/us/en/blog/ has no RSS or Atom alternate link, and https://eng.uber.com/feed/ is gone. No first-party replacement.",
    "LinkedIn": "https://engineering.linkedin.com/blog.rss.html returns HTTP 404 (down since 2024). https://www.linkedin.com/blog/engineering and its /rss, /feed.xml and .rss paths also 404, and the HTML has no RSS or Atom link. No first-party replacement.",
}
KEYWORDS = re.compile(r"recommend|ranking|retriev|search relevance|personaliz|two[- ]tower|embedding|semantic id|generative retriev|click-through|CTR|feed ranking|home ?feed", re.I)
ARXIV = "https://export.arxiv.org/api/query?search_query=cat:cs.IR&sortBy=submittedDate&sortOrder=descending&max_results=60"
UA = {"User-Agent": "RecArchRefresh/0.1 (review-queue builder; contact: TODO)"}

def _allowed_hosts():
    return {(urllib.parse.urlsplit(u).hostname or "").lower().rstrip(".") for u in list(FEEDS.values()) + [ARXIV]}

def _check_url(url):
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme != "https" or host not in _allowed_hosts() or parts.username or parts.password:
        raise ValueError(f"refusing URL outside the feed allowlist: {url}")

class _GuardRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

_OPENER = urllib.request.build_opener(_GuardRedirect)

def get(url, timeout=25):
    _check_url(url)
    with _OPENER.open(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        _check_url(r.geturl())
        data = r.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError(f"feed exceeds {MAX_FEED_BYTES} bytes")
    return data

def _queue_path():
    root = os.path.realpath(ROOT)
    dest = os.path.realpath(QUEUE)
    if os.path.commonpath([root, dest]) != root or os.path.basename(dest) != "review_queue.jsonl":
        raise SystemExit("review queue must stay at review_queue.jsonl in the repo root")
    return dest

def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def _parse_xml(xml_bytes):
    """Parse a feed with entity declarations refused.

    xml.etree.ElementTree expands internal entities (billion laughs) on this interpreter.
    External entities are not loaded, but a remote feed must not be able to expand entities either.
    The C accelerator XMLParser does not expose its expat parser, so this uses expat directly.
    """
    target = ET.TreeBuilder()
    parser = xml.parsers.expat.ParserCreate(None, "}")
    parser.StartElementHandler = target.start
    parser.EndElementHandler = target.end
    parser.CharacterDataHandler = target.data
    def _entity(*_a):
        raise ValueError("XML entity declarations are disabled")
    parser.EntityDeclHandler = _entity
    parser.ExternalEntityRefHandler = lambda *_a: False
    parser.Parse(xml_bytes, True)
    return target.close()

def parse_feed(xml_bytes, source):
    root = _parse_xml(xml_bytes)
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"): continue
        g = lambda n: next((strip(c.text) for c in it if c.tag.split("}")[-1] == n and c.text), "")
        link = g("link")
        if not link:
            for c in it:
                if c.tag.split("}")[-1] == "link" and c.get("href"): link = c.get("href"); break
        out.append({"source": source, "title": g("title"), "url": link,
                    "published": g("pubDate") or g("published") or g("updated"),
                    "summary": (g("description") or g("summary"))[:400]})
    return out

def arxiv_candidates():
    out = []
    for e in parse_feed(get(ARXIV), "arXiv cs.IR"):
        e["title"] = re.sub(r"\s+", " ", e["title"])
        out.append(e)
    return out

def recent(published, days):
    if not published: return True
    from email.utils import parsedate_to_datetime
    try: d = parsedate_to_datetime(published)
    except Exception:
        try: d = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
        except Exception: return True
    if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
    return d >= dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=14); ap.add_argument("--no-arxiv", action="store_true")
    a = ap.parse_args()
    seen = set()
    queue = _queue_path()
    if os.path.exists(queue):
        for line in open(queue):
            try: seen.add(json.loads(line)["url"])
            except Exception: pass
    cands, errors = [], []
    for name, why in DISABLED.items():
        print(f"  feed disabled: {name}: {why}", file=sys.stderr)
    for name, url in FEEDS.items():
        try: cands += parse_feed(get(url), name)
        except Exception as e: errors.append(f"{name}: {type(e).__name__}: {e}")
    if not a.no_arxiv:
        try: cands += arxiv_candidates()
        except Exception as e: errors.append(f"arXiv: {type(e).__name__}: {e}")
    new = 0
    with open(queue, "a", encoding="utf-8") as f:
        for c in cands:
            if not c["url"] or c["url"] in seen: continue
            if not KEYWORDS.search(c["title"] + " " + c["summary"]): continue
            if not recent(c["published"], a.days): continue
            c.update({"status": "pending", "queued_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")})
            f.write(json.dumps(c, ensure_ascii=False) + "\n"); seen.add(c["url"]); new += 1
    print(f"candidates fetched: {len(cands)}; new queued: {new}; queue: {queue}")
    for e in errors: print("  feed error:", e, file=sys.stderr)

if __name__ == "__main__": main()
