#!/usr/bin/env python3
"""RecArch refresh stub.

Pulls candidate posts from company engineering-blog feeds and arXiv cs.IR, filters by recsys keywords,
and APPENDS new candidates to review_queue.jsonl with status "pending". It never touches data/systems/ and never publishes.
A human reviews each candidate, reads the source, then writes a card by hand.

Usage: python3 scripts/refresh.py [--days 14] [--no-arxiv]
Stdlib only. Feed URLs are best-effort and may change; failures are reported, not fatal.
"""
import argparse, datetime as dt, json, os, re, sys, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "review_queue.jsonl")
# TODO: verify each URL before relying on it; add/remove feeds as needed.
FEEDS = {
    "Netflix": "https://netflixtechblog.com/feed",
    "Pinterest": "https://medium.com/feed/pinterest-engineering",
    "Uber": "https://www.uber.com/en-US/blog/engineering/rss/",
    "DoorDash": "https://careersatdoordash.com/engineering-blog/feed/",
    "Airbnb": "https://medium.com/feed/airbnb-engineering",
    "Spotify": "https://engineering.atspotify.com/feed/",
    "LinkedIn": "https://engineering.linkedin.com/blog.rss.html",
    "Meta Engineering": "https://engineering.fb.com/feed/",
    "Instacart": "https://tech.instacart.com/feed",
    "Etsy": "https://www.etsy.com/codeascraft/rss",
}
KEYWORDS = re.compile(r"recommend|ranking|retriev|search relevance|personaliz|two[- ]tower|embedding|semantic id|generative retriev|click-through|CTR|feed ranking|home ?feed", re.I)
ARXIV = "https://export.arxiv.org/api/query?search_query=cat:cs.IR&sortBy=submittedDate&sortOrder=descending&max_results=60"
UA = {"User-Agent": "RecArchRefresh/0.1 (review-queue builder; contact: TODO)"}

def get(url, timeout=25):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def strip(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def parse_feed(xml_bytes, source):
    root = ET.fromstring(xml_bytes)
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
    if os.path.exists(QUEUE):
        for line in open(QUEUE):
            try: seen.add(json.loads(line)["url"])
            except Exception: pass
    cands, errors = [], []
    for name, url in FEEDS.items():
        try: cands += parse_feed(get(url), name)
        except Exception as e: errors.append(f"{name}: {type(e).__name__}: {e}")
    if not a.no_arxiv:
        try: cands += arxiv_candidates()
        except Exception as e: errors.append(f"arXiv: {type(e).__name__}: {e}")
    new = 0
    with open(QUEUE, "a", encoding="utf-8") as f:
        for c in cands:
            if not c["url"] or c["url"] in seen: continue
            if not KEYWORDS.search(c["title"] + " " + c["summary"]): continue
            if not recent(c["published"], a.days): continue
            c.update({"status": "pending", "queued_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")})
            f.write(json.dumps(c, ensure_ascii=False) + "\n"); seen.add(c["url"]); new += 1
    print(f"candidates fetched: {len(cands)}; new queued: {new}; queue: {QUEUE}")
    for e in errors: print("  feed error:", e, file=sys.stderr)

if __name__ == "__main__": main()
