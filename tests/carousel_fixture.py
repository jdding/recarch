"""Selection tests for the home carousel (pure Python) + writes HTML fixtures for tests/carousel.test.js.
Run: python3 tests/carousel_fixture.py /tmp/car-fixtures"""
import datetime, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build

TODAY = "2026-10-30"
def day(n): return (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=n)).isoformat()
def card(i, added, upd=None):
    return {"id": f"c{i:02d}", "name": f"Card {i}", "company": "Co", "era": ["classic", "deep", "generative"][i % 3], "tldr": f"tldr {i}", "added_on": day(added),
            "updates": [{"date": day(d), "note": f"note {i}"} for d in (upd or [])]}
def scenario(name, cards, expect_ids, expect_recent_n):
    sel = build.carousel_select(cards, TODAY, 6, 7)
    ids = [x["card"]["id"] for x in sel]
    assert ids == expect_ids, (name, ids, expect_ids)
    assert sum(x["recent"] for x in sel) == expect_recent_n, (name, [x["recent"] for x in sel])
    return sel

def main(out):
    os.makedirs(out, exist_ok=True); build.SITE = {"carousel_size": 6, "carousel_window_days": 7}
    sc = {}
    # 0 recent: everything older than 7 days -> pure backfill, newest activity first (an old update counts)
    c0 = [card(i, 20 + i) for i in range(8)]; c0[5]["updates"] = [{"date": day(9), "note": "n"}]
    sc["recent0"] = (c0, ["c05", "c00", "c01", "c02", "c03", "c04"], 0)
    # 3 recent (one via an update on an old card) + backfill 3
    c3 = [card(0, 1), card(1, 30, [2]), card(2, 6)] + [card(i, 10 + i) for i in range(3, 12)]
    sc["recent3"] = (c3, ["c00", "c01", "c02", "c03", "c04", "c05"], 3)
    # 10 recent -> capped at 6, newest first; ties: updated before added, then id desc-stable
    c10 = [card(i, i % 7) for i in range(10)]
    ids10 = ["c07", "c00", "c08", "c01", "c09", "c02"]  # days 0,0,1,1,2,2; ties broken by id descending
    sc["recent10"] = (c10, ids10, 6)
    sc["few4"] = ([card(i, i) for i in range(4)], ["c03", "c02", "c01", "c00"][::-1], 4)
    # window boundary: exactly 7 days old is NOT recent (strictly within last 7 days)
    meta = {}
    for name, (cards, ids, nrec) in sc.items():
        sel = build.carousel_select(cards, TODAY, 6, 7)
        if name == "few4": ids = [x["card"]["id"] for x in sel]; assert len(ids) == 4
        scenario(name, cards, ids, nrec)
        html = build.strip([], "", TODAY, cards)
        open(os.path.join(out, name + ".html"), "w").write(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/static/style.css"><body style="max-width:900px;margin:20px auto">{html}<script src="/static/carousel.js"></script>')
        meta[name] = {"ids": ids, "recent": nrec, "kinds": [x["kind"] for x in sel]}
    assert build.carousel_select([card(0, 7)], TODAY)[0]["recent"] is False and build.carousel_select([card(0, 6)], TODAY)[0]["recent"] is True
    assert build.carousel_select([], TODAY) == []
    open(os.path.join(out, "meta.json"), "w").write(json.dumps(meta))
    print("python selection tests: ALL PASS", {k: v["ids"] for k, v in meta.items()})

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/car-fixtures")
