#!/usr/bin/env python3
"""FAQ and eval checks. Run: python3 tests/faq_validator_test.py   (no build needed, reads data/ and eval/ only)
1. every stored FAQ item passes the same validator that generated it: numbers string-match the cited fields of the card
2. the validator rejects invented numbers, empty answers and Chinese parentheses
3. the reviewed gate: files with reviewed: false publish nothing, true publishes, drop hides one item
4. eval/faq_eval.jsonl matches data/faq, eval/adversarial.jsonl has about 100 prompts across the five categories
"""
import json, os, sys, copy, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
import yaml, build, ailayer, gen_faq
fails = checks = 0
def ok(c, m):
    global fails, checks
    checks += 1
    if not c: fails += 1; print("FAIL", m)

build.load_companies(); build.set_lang("en")
allc = build.load_cards(); build.SITE = build.load_site(); build.check_v2(allc); build.check_deployment(allc); build.TAXONOMY.update(build.load_taxonomy())
errs, warns = [], []
en = {c["id"]: c for c in allc if build.is_active(c)}
zh = {c["id"]: build.zh_card(c, errs, warns) for c in allc}
ok(not errs, f"zh cards load: {errs[:2]}")

files = sorted(glob.glob("data/faq/*.yaml"))
ok(len(files) == len(en), f"one FAQ file per active card, {len(en)} cards, {len(files)} files")
total = 0
for f in files:
    d = yaml.safe_load(open(f, encoding="utf-8")); cid = d["id"]
    ok(cid in en and f.endswith(cid + ".yaml"), f"{f}: id matches an active card")
    ok(isinstance(d["reviewed"], bool), f"{f}: reviewed is a bool")
    ok(5 <= len(d["items"]) <= 10, f"{cid}: about 8 items, got {len(d['items'])}")
    for it in d["items"]:
        total += 1
        for lang, c, q, a in (("en", en[cid], it["q_en"], it["a_en"]), ("zh", zh[cid], it["q_zh"], it["a_zh"])):
            why = gen_faq.validate(c, lang, q, a, it["fields"])
            ok(why is None, f"{cid}/{it['key']}/{lang}: {why}")
            # independent re-check without the generator's helper: each answer number appears as text in a cited field or the name
            blob = json.dumps([gen_faq.get(c, p) for p in it["fields"]] + [c["name"], c["company"]], ensure_ascii=False).replace(",", "")
            for n in ailayer.numbers(a): ok(n in blob, f"{cid}/{it['key']}/{lang}: number {n} is a substring of the cited fields")
        ok(all(gen_faq.get(en[cid], p) is not None for p in it["fields"]), f"{cid}/{it['key']}: cited field paths exist")
ok(total >= 600, f"at least 600 items across the cards, got {total}")

# validator rejects bad candidates
c = en["airbnb-listing-embeddings-2018"]; z = zh["airbnb-listing-embeddings-2018"]
ok(gen_faq.validate(c, "en", "Q?", "CTR rose 20%.", ["tldr"]) is None, "valid answer passes")
ok("number" in (gen_faq.validate(c, "en", "Q?", "CTR rose 35%.", ["tldr"]) or ""), "invented number is rejected")
ok("number" in (gen_faq.validate(c, "en", "Q?", "Latency is 12 ms.", ["deployment.serving_latency"]) or ""), "a number for an unreported field is rejected")
ok(gen_faq.validate(c, "en", "Q?", "  ", ["tldr"]) == "empty answer", "empty answer is rejected")
ok("parentheses" in (gen_faq.validate(z, "zh", "问？", "提高了 20%（见表）。", ["tldr"]) or ""), "Chinese parentheses are rejected")
ok("number" in (gen_faq.validate(z, "zh", "2030 年的问题？", "提高 20%。", ["tldr"]) or ""), "invented number in the question is rejected")

# reviewed gate
saved = copy.deepcopy(ailayer.FAQ)
try:
    items = [{"key": "k1", "q_en": "Q1", "a_en": "A1", "q_zh": "问一", "a_zh": "答一", "fields": ["tldr"]}, {"key": "k2", "q_en": "Q2", "a_en": "A2", "q_zh": "问二", "a_zh": "答二", "fields": ["tldr"]}]
    ailayer.set_faq({"x": {"reviewed": False, "drop": set(), "items": items}})
    ok(ailayer.published_faq("x", "en") == [] and ailayer.faq_section("x", "en", str) == "", "reviewed: false publishes nothing")
    ailayer.set_faq({"x": {"reviewed": True, "drop": set(), "items": items}})
    ok(len(ailayer.published_faq("x", "zh")) == 2 and 'id="faq"' in ailayer.faq_section("x", "zh", str), "reviewed: true publishes")
    ailayer.set_faq({"x": {"reviewed": True, "drop": {"k1"}, "items": items}})
    ok([i["key"] for i in ailayer.published_faq("x", "en")] == ["k2"], "drop hides a single item")
    ailayer.set_faq({})
    ok(ailayer.published_faq("missing", "en") == [], "card without a FAQ file publishes nothing")
finally:
    ailayer.set_faq(saved)

# eval files
ev = [json.loads(l) for l in open("eval/faq_eval.jsonl", encoding="utf-8")]
ok(len(ev) == total, f"faq_eval.jsonl has every item, {len(ev)} vs {total}")
ok(all(e["reviewed"] is False or isinstance(e["reviewed"], bool) for e in ev) and len({e["id"] for e in ev}) == len(ev), "eval ids unique")
adv = [json.loads(l) for l in open("eval/adversarial.jsonl", encoding="utf-8")]
cats = {a["category"] for a in adv}
ok(len(adv) >= 95, f"about 100 adversarial prompts, got {len(adv)}")
ok(cats == {"out_of_scope", "unreported_trap", "cross_card", "prompt_injection", "pdf_request"}, f"five categories, got {cats}")
ok(all(a["prompt_en"] and a["prompt_zh"] and a["expect"].get("behavior") for a in adv), "every prompt has en, zh and an expected behavior")
ok(all(i in en for a in adv for i in a["card_ids"]), "adversarial card ids are active cards")
for a in adv:
    if a["category"] == "unreported_trap":
        f = a["expect"]["field"].split(".", 1)[1]; ok(en[a["card_ids"][0]]["deployment"].get(f) == "not_reported", f"{a['id']}: trap field really is unreported on the card")
sp = open("faq-spotcheck.md", encoding="utf-8").read()
ok(sp.count("\n## ") == 30, f"spot-check file has 30 items, got {sp.count(chr(10) + '## ')}")
print(f"faq: {checks} checks, {fails} failed"); sys.exit(1 if fails else 0)
