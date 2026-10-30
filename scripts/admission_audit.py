#!/usr/bin/env python3
"""Admission audit per docs/admission.md. Run from the repo root:  python3 scripts/admission_audit.py [--all]
Active cards only. Judged per system: a merged card (one with `versions:`) uses the SUM of all its versions' citations
(data/citations.json `count`, which scripts/citations.py computes) and official code for any version counts toward the arXiv-only exemption.
Statuses: 达标 (pass), 豁免通过 (pass by an exemption), 边缘 (borderline), 不达标 (fails)."""
import collections, datetime, glob, json, re, sys, yaml
today = datetime.date.today()
cit = json.load(open("data/citations.json"))
cards = [yaml.safe_load(open(f)) for f in sorted(glob.glob("data/systems/*.yaml"))]
MAIN = re.compile(r'^(KDD|RecSys 20\d\d$|RecSys 20\d\d \(?[^wl]|WWW|SIGIR|CIKM|WSDM|NeurIPS|ICML|ICLR|AAAI|IJCAI|ACL|IEEE Internet|ACM TMIS)')

def months_since(fp):
    y, m = map(int, str(fp).split("-")[:2]); return (today.year - y) * 12 + (today.month - m)

def audit(c):
    n = (cit.get(c["id"]) or {}).get("count")          # system-level total
    papers = (cit.get(c["id"]) or {}).get("papers") or []
    split = " + ".join(str(p["count"]) for p in papers) if len(papers) > 1 else None
    shown = f"{n}，各版本 {split}" if split else str(n)
    v = str(c.get("venue") or ""); ev = c.get("evidence_level"); code = (c.get("code") or {}).get("status")
    st = {s.get("type") for s in c.get("sources", [])}
    blog = bool(st & {"engineering_blog", "documentation", "press"}) and "paper" not in st
    canon = n is not None and n >= 500
    fail, soft, ex = [], [], []
    if ev == "research_only": (ex if canon else fail).append(f"论文无线上证据，被引 {shown}" + ("，按被引 500 以上豁免" if canon else ""))
    if ev == "open_source_reference": (ex if canon else soft).append("只有开源参考实现，无论文级线上数据" + (f"，被引 {shown}，豁免" if canon else ""))
    if c.get("system_type") == "research" and ev != "research_only": soft.append("模型组件而非完整系统")
    if not v and "paper" in st and not blog and "engineering_blog" not in st:
        m = months_since(c["first_public"])
        if m < 12: ex.append("仅 arXiv，首次公开不足 12 个月，观察期")
        elif code == "official_full": ex.append("仅 arXiv，但有官方完整代码，例外通过")
        elif (n or 0) >= 50: ex.append(f"仅 arXiv，被引 {shown} 达 50 以上，例外通过")
        else: soft.append(f"仅 arXiv 已 {m} 个月，被引 {shown}，无官方完整代码")
    if v and not MAIN.match(v):
        if canon: ex.append(f"来源 {v.split(' (')[0]} 非主会场，被引 {shown}，豁免")
        else: soft.append("来源非主会场：" + v.split(" (")[0] + (" 工作坊" if re.search("workshop|ORSUM|DLRS", v, re.I) else ""))
    status = "不达标" if fail else "边缘" if soft else "豁免通过" if ex else "达标"
    return dict(id=c["id"], status=status, total=n, per_version=[(p["name"], p["count"]) for p in papers] if len(papers) > 1 else None, fail=fail, soft=soft, ex=ex)

if __name__ == "__main__":
    use = [c for c in cards if sys.argv[1:] == ["--all"] or c.get("status", "active") == "active"]
    rows = [audit(c) for c in use]
    print("cards", len(rows), dict(collections.Counter(r["status"] for r in rows)))
    for r in rows:
        if r["status"] != "达标": print(r["status"], r["id"], r["total"], r["per_version"] or "", "|", "；".join(r["fail"] + r["soft"] + r["ex"]))
