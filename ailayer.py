"""RecArch AI-native layer: machine-readable outputs, FAQ gate, Agent Skill copy.

Everything published here is derived from our own interpretation fields of a card (see PUBLIC_*). Nothing from source PDFs is read or written:
the card dict has no PDF text, and the `fulltext` block and `deployment.fulltext_refs` are never copied.

Used by build.py via a few hooks: faq_section() for card pages, build_ai_outputs() once per language, ai_page() for /ai/.
Data: data/faq/<id>.yaml (written by scripts/gen_faq.py, published only when `reviewed: true`).
"""
import copy, datetime, glob, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_VERSION = "1.0"
NR = "not_reported"
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
CJK = re.compile(r"[\u3400-\u9fff]")
PARENS = re.compile(r"[()\uff08\uff09]")
MCP_PLACEHOLDER = "https://mcp.recarch.example/mcp"

def numbers(text):
    """Same number tokens as build._NUM: digits with inner . or , groups, commas stripped first."""
    return set(NUM_RE.findall(str(text).replace(",", "")))

def mcp_url(): return os.environ.get("RECARCH_MCP_URL", "").strip().rstrip("/") or MCP_PLACEHOLDER
def mcp_is_placeholder(): return mcp_url() == MCP_PLACEHOLDER

# ---------------------------------------------------------------- FAQ data

FAQ_KEYS = ("key", "q_en", "a_en", "q_zh", "a_zh", "fields")

def load_faq(card_ids):
    """data/faq/<id>.yaml -> {id: {"reviewed": bool, "drop": set, "items": [...]}}. Structure errors stop the build."""
    import yaml
    out, errs = {}, []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/faq/*.yaml"))):
        n = os.path.basename(f); d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        i = n[:-5]
        if d.get("id") != i: errs.append(f"faq/{n}: id must equal filename"); continue
        if i not in card_ids: continue     # FAQ of a retired or unknown card is never published
        if not isinstance(d.get("reviewed"), bool): errs.append(f"faq/{n}: reviewed must be true or false")
        keys = set()
        for k, it in enumerate(d.get("items") or []):
            miss = [x for x in FAQ_KEYS if not it.get(x)]
            if miss: errs.append(f"faq/{n}: item {k} missing {miss}")
            if it.get("key") in keys: errs.append(f"faq/{n}: duplicate item key {it.get('key')}")
            keys.add(it.get("key"))
            if PARENS.search(str(it.get("q_zh", "")) + str(it.get("a_zh", ""))): errs.append(f"faq/{n}: item {k}: no parentheses in Chinese copy")
        out[i] = {"reviewed": d.get("reviewed") is True, "drop": set(d.get("drop") or []), "items": d.get("items") or []}
    if errs: raise SystemExit("FAQ ERRORS:\n  " + "\n  ".join(errs))
    return out

FAQ = {}
def set_faq(f): FAQ.clear(); FAQ.update(f)

def published_faq(card_id, lang):
    """The only way FAQ text reaches any output: file reviewed: true, item not in `drop`."""
    e = FAQ.get(card_id)
    if not e or not e["reviewed"]: return []
    sfx = "zh" if lang == "zh" else "en"
    return [{"key": it["key"], "q": it["q_" + sfx], "a": it["a_" + sfx], "fields": it["fields"]} for it in e["items"] if it["key"] not in e["drop"]]

FAQ_HEAD = {"zh": "常见问题", "en": "Frequently asked questions"}
FAQ_NOTE = {"zh": "这些问答由卡片字段整理而成，答案里的数字都来自上面的卡片内容。", "en": "These answers are assembled from the card fields above; every number comes from the card."}
def faq_section(card_id, lang, E):
    items = published_faq(card_id, lang)
    if not items: return ""
    body = "".join(f'<details class="faq-i"><summary>{E(x["q"])}</summary><p>{E(x["a"])}</p></details>' for x in items)
    return f'<section class="blk faq" id="faq"><h2>{E(FAQ_HEAD[lang])}</h2><p class="stage-d">{E(FAQ_NOTE[lang])}</p>{body}</section>'

# ---------------------------------------------------------------- the public card

def _nr(v, nr_label):
    return nr_label if v == NR else v

def public_card(c, L, lang, site_url, nr_label):
    """Whitelist of published fields. L = label tables of the language (era, evid, code, depev, stage)."""
    pre = "" if lang == "zh" else "en/"
    d = c.get("deployment") or {}
    dep = {}
    for k in ("online_evidence", "scenario", "ab_traffic", "ab_duration", "baseline", "training_compute", "serving_latency", "serving_qps", "inference_cost", "hardware"):
        if k in d: dep[k] = _nr(d[k], nr_label)
    if dep.get("online_evidence") in L["depev"]: dep["online_evidence_label"] = L["depev"][dep["online_evidence"]]
    if isinstance(d.get("online_lifts"), list): dep["online_lifts"] = [dict(x) for x in d["online_lifts"]]
    elif "online_lifts" in d: dep["online_lifts"] = nr_label
    if d.get("notes"): dep["notes"] = list(d["notes"])
    cd = c.get("code") or {}
    card = {
        "id": c["id"], "name": c["name"], "company": c["company"], "surface": c.get("surface"), "year": c["year"], "first_public": c.get("first_public"),
        "venue": c.get("venue"), "system_type": c["system_type"],
        "era": c["era"], "era_label": L["era"][c["era"]], "era_reason": c.get("era_reason"),
        "evidence_level": c["evidence_level"], "evidence_label": L["evid"][c["evidence_level"]],
        "tldr": c["tldr"].strip(), "summary": c["summary"].strip(), "core_idea": c.get("core_idea"), "deployed_in": c.get("deployed_in"),
        "scale_short": c.get("scale_short"), "key_result": c.get("key_result"), "paradigms": list(c.get("paradigms") or []),
        "stages": [{"stage": s["stage"], "stage_label": L["stage"].get(s["stage"], s["stage"]), "model_family": s.get("model_family"), "details": (s.get("details") or "").strip()} for s in c["stages"]],
        "id_tokenization": dict(c.get("id_tokenization") or {}), "features_signals": list(c.get("features_signals") or []),
        "training": dict(c.get("training") or {}), "serving_infra": c.get("serving_infra"),
        "scale": [dict(x) for x in c.get("scale") or []], "results_reported": c.get("results_reported"),
        "results_table": copy.deepcopy(c.get("results_table") or {}), "deployment": dep,
        "caveats": list(c.get("caveats") or []), "unknown_fields": list(c.get("unknown_fields") or []),
        "code": {"status": cd.get("status"), "status_label": L["code"].get(cd.get("status")), "repos": [{k: r.get(k) for k in ("url", "official", "owner", "note")} for r in cd.get("repos") or []]},
        "sources": [{"title": s["title"], "url": s["url"], "type": s["type"]} for s in c["sources"]], "primary_source": c["primary_source"],
        "version_note": c.get("version_note"), "added_on": c["added_on"], "last_verified": c["last_verified"],
        "updates": [dict(u) for u in c.get("updates") or []],
        "url": f"{site_url}/{pre}systems/{c['id']}/", "md_url": f"{site_url}/{pre}cards/{c['id']}.md",
    }
    card["facts"] = facts(card, nr_label)
    card["faq"] = [{"q": x["q"], "a": x["a"], "fields": x["fields"]} for x in published_faq(c["id"], lang)]
    return {k: v for k, v in card.items() if v is not None}

def facts(card, nr_label):
    """Every numeric statement of the card with the path of the field it comes from, or the not-reported marker. Paths resolve inside the card entry."""
    out = [{"label": "year", "value": card["year"], "source": "year"}, {"label": "first_public", "value": card["first_public"], "source": "first_public"}]
    for i, s in enumerate(card.get("scale") or []):
        out.append({"label": s["metric"], "value": s.get("value"), "source": f"scale.{i}.value"})
    for g in ("online", "offline", "other"):
        for i, r in enumerate((card.get("results_table") or {}).get(g) or []):
            out.append({"label": f'{r.get("metric")} | {r.get("setting")}', "value": r.get("result"), "versus": r.get("versus"), "group": g, "source": f"results_table.{g}.{i}.result"})
    dep = card.get("deployment") or {}
    lifts = dep.get("online_lifts")
    if isinstance(lifts, list):
        for i, x in enumerate(lifts): out.append({"label": x["metric"], "value": x["value"], "source": f"deployment.online_lifts.{i}.value"})
    for k in ("ab_traffic", "ab_duration", "training_compute", "serving_latency", "serving_qps", "inference_cost", "hardware"):
        if k in dep:
            v = dep[k]
            out.append({"label": k, "value": None if v == nr_label else v, "reported": v != nr_label, "source": f"deployment.{k}", **({"status": nr_label} if v == nr_label else {})})
    return out

# ---------------------------------------------------------------- Markdown

MD = {
 "zh": {"by": "公司", "year": "年份", "venue": "发表", "preprint": "预印本", "era": "时代", "evid": "证据等级", "type": "类型", "page": "网页", "verified": "最近核对", "summary": "它是怎么做的", "stages": "所处阶段与模型",
        "idtok": "ID 与 token 化", "features": "输入特征", "training": "训练", "serving": "服务与规模", "results": "报告的结果", "deploy": "上线证据", "caveats": "读结果时要注意", "unknown": "文中未报告",
        "code": "代码", "sources": "来源", "faq": "常见问题", "scope": "说明", "nr": "未报告", "mode": "训练方式", "obj": "训练目标", "official": "官方", "unofficial": "非官方", "key": "核心思路", "dep": "部署场景",
        "online": "线上", "offline": "离线", "other": "其他", "vs": "对比", "notes": "备注", "unaff": "本文件由 RecArch 依据公开来源整理，只含我们自己的解读，不含论文原文。RecArch 问答与论文作者无关，也不代表作者。数字只来自卡片字段，未报告的写作未报告。"},
 "en": {"by": "Company", "year": "Year", "venue": "Venue", "preprint": "Preprint", "era": "Era", "evid": "Evidence level", "type": "Type", "page": "Page", "verified": "Last verified", "summary": "How it works", "stages": "Stages and models",
        "idtok": "IDs and tokenization", "features": "Input features", "training": "Training", "serving": "Serving and scale", "results": "Reported results", "deploy": "Deployment evidence", "caveats": "Caveats when reading the results", "unknown": "Not reported",
        "code": "Code", "sources": "Sources", "faq": "FAQ", "scope": "Notice", "nr": "not reported", "mode": "Mode", "obj": "Objectives", "official": "official", "unofficial": "unofficial", "key": "Core idea", "dep": "Deployment scenario",
        "online": "Online", "offline": "Offline", "other": "Other", "vs": "versus", "notes": "Notes", "unaff": "This file is written by RecArch from public sources. It holds our own interpretation only, never text from the papers. The RecArch Q&A is not affiliated with the paper authors and does not speak for them. Numbers come only from the card fields; anything not reported is marked as such."},
}
DEP_LABEL = {
 "zh": {"ab_traffic": "A/B 流量", "ab_duration": "A/B 时长", "baseline": "对比基线", "training_compute": "训练算力", "serving_latency": "服务延迟", "serving_qps": "服务 QPS", "inference_cost": "推理成本", "hardware": "硬件"},
 "en": {"ab_traffic": "A/B traffic", "ab_duration": "A/B duration", "baseline": "Baseline", "training_compute": "Training compute", "serving_latency": "Serving latency", "serving_qps": "Serving QPS", "inference_cost": "Inference cost", "hardware": "Hardware"},
}

def card_md(card, lang):
    m = MD[lang]; nr = m["nr"]; o = []
    a = o.append; sep = "\n"
    a(f'# {card["name"]}'); a(""); a(f'> {card["tldr"]}'); a("")
    a(f'- {m["by"]}: {card["company"]}'); a(f'- {m["year"]}: {card["year"]} ({card["first_public"]})' if lang == "en" else f'- {m["year"]}: {card["year"]}，{card["first_public"]}')
    a(f'- {m["venue"]}: {card.get("venue") or m["preprint"]}'); a(f'- {m["era"]}: {card["era_label"]}'); a(f'- {m["evid"]}: {card["evidence_label"]}')
    a(f'- {m["page"]}: {card["url"]}'); a(f'- {m["verified"]}: {card["last_verified"]}'); a("")
    if card.get("core_idea"): a(f'**{m["key"]}**: {card["core_idea"]}'); a("")
    a(f'## {m["summary"]}'); a(""); a(card["summary"]); a("")
    a(f'## {m["stages"]}'); a("")
    for s in card["stages"]:
        a(f'- **{s["stage_label"]}**: {s.get("model_family") or nr}'); 
        if s.get("details"): a(f'  {s["details"]}')
    a("")
    idt = card.get("id_tokenization") or {}
    if idt.get("approach") or idt.get("details"):
        a(f'## {m["idtok"]}'); a("")
        if idt.get("approach"): a(idt["approach"]); a("")
        if idt.get("details"): a(idt["details"]); a("")
    if card.get("features_signals"):
        a(f'## {m["features"]}'); a("")
        for f in card["features_signals"]: a(f"- {f}")
        a("")
    tr = card.get("training") or {}
    if tr:
        a(f'## {m["training"]}'); a("")
        if tr.get("mode"): a(f'- {m["mode"]}: {tr["mode"]}')
        if tr.get("objectives"): a(f'- {m["obj"]}: ' + "; ".join(tr["objectives"]))
        if tr.get("notes"): a(f'- {tr["notes"]}')
        a("")
    if card.get("serving_infra") or card.get("scale"):
        a(f'## {m["serving"]}'); a("")
        if card.get("serving_infra"): a(card["serving_infra"]); a("")
        for s in card.get("scale") or []: a(f'- {s["metric"]}: {s.get("value")}')
        a("")
    a(f'## {m["results"]}'); a("")
    if card.get("results_reported"): a(card["results_reported"]); a("")
    rt = card.get("results_table") or {}
    for g in ("online", "offline", "other"):
        for r in rt.get(g) or []:
            a(f'- [{m[g]}] {r["setting"]}: {r["method"]}, {r["metric"]} {r["result"]}, {m["vs"]} {r["versus"]}')
    a("")
    dep = card.get("deployment") or {}
    if dep:
        a(f'## {m["deploy"]}'); a("")
        a(f'- {m["evid"]}: {dep.get("online_evidence_label", "")}')
        if dep.get("scenario"): a(f'- {m["dep"]}: {dep["scenario"]}')
        for k in ("ab_duration", "ab_traffic", "baseline", "training_compute", "serving_latency", "serving_qps", "inference_cost", "hardware"):
            if k in dep: a(f'- {DEP_LABEL[lang][k]}: {dep[k]}')
        if isinstance(dep.get("online_lifts"), list):
            for x in dep["online_lifts"]: a(f'- {x["metric"]}: {x["value"]}')
        for x in dep.get("notes") or []: a(f"- {x}")
        a("")
    if card.get("caveats") or card.get("version_note"):
        a(f'## {m["caveats"]}'); a("")
        for x in card.get("caveats") or []: a(f"- {x}")
        if card.get("version_note"): a(f'- {card["version_note"]}')
        a("")
    if card.get("unknown_fields"):
        a(f'## {m["unknown"]}'); a("")
        for x in card["unknown_fields"]: a(f"- {x}")
        a("")
    a(f'## {m["code"]}'); a(""); a(f'- {card["code"].get("status_label")}')
    for r in card["code"]["repos"]: a(f'- {r["url"]} ({m["official"] if r["official"] else m["unofficial"]}): {r["note"]}' if lang == "en" else f'- {r["url"]}，{m["official"] if r["official"] else m["unofficial"]}：{r["note"]}')
    a("")
    a(f'## {m["sources"]}'); a("")
    for s in card["sources"]: a(f'- [{s["title"]}]({s["url"]})')
    a("")
    if card.get("faq"):
        a(f'## {m["faq"]}'); a("")
        for x in card["faq"]: a(f'**{x["q"]}**'); a(""); a(x["a"]); a("")
    a("---"); a(m["unaff"]); a("")
    return sep.join(o)

def topic_md(t, lang, site_url):
    pre = "" if lang == "zh" else "en/"
    o = [f'# {t["title"]}', "", f'> {t["summary"]}', "", f'{site_url}/{pre}topics/{t["slug"]}/', "", t["problem"], "", t["question"], ""]
    o += [*t["framing"], ""]
    for m in t["members"]: o.append(f'- {m["id"]}: {m["approach"]}')
    o.append("")
    for d in t["decisions"]: o.append(f'- {d["when"]} {d["then"]} [{", ".join(d["cards"])}]')
    o.append("")
    for s in t["differences"]: o += [f'### {s["heading"]}', "", s["text"], f'[{", ".join(s["cards"])}]', ""]
    return "\n".join(o)

# ---------------------------------------------------------------- llms.txt, llms-full.txt, cards.json

HEAD = {
 "zh": {"title": "RecArch", "blurb": "RecArch 是工业推荐、搜索和排序系统的结构化架构库，每张卡片依据公开来源的全文整理，未报告的信息一律写作未报告。以下内容只含我们自己的解读，不含论文原文。RecArch 问答与论文作者无关，也不代表作者。",
        "cards": "系统卡片", "topics": "专题", "optional": "可选", "full": "全部卡片的 Markdown 合集，只含我们的解读", "json": "结构化数据，每个数字字段带来源字段路径或未报告", "mcp": "只读 MCP 服务，工具为 search_cards、get_card、compare_topic", "ai": "在你的 AI 里用 RecArch", "skill": "Agent Skill 包", "en": "English version"},
 "en": {"title": "RecArch", "blurb": "RecArch is a structured database of industrial recommender, search and ranking architectures. Every card is written from the full text of its public sources and anything unreported is marked not reported. This content holds our own interpretation only, never text from the papers. The RecArch Q&A is not affiliated with the paper authors and does not speak for them.",
        "cards": "System cards", "topics": "Topics", "optional": "Optional", "full": "All cards as one Markdown file, our interpretation only", "json": "Structured data; every numeric field carries its source field path or not reported", "mcp": "Read-only MCP server with the tools search_cards, get_card and compare_topic", "ai": "Use RecArch in your AI", "skill": "Agent Skill pack", "en": "中文版"},
}

def oneline(s): return " ".join(str(s).split())

def llms_txt(cards, topics, lang, site_url):
    h = HEAD[lang]; pre = "" if lang == "zh" else "en/"; other = f"{site_url}/" + ("en/llms.txt" if lang == "zh" else "llms.txt")
    o = [f'# {h["title"]}', "", f'> {h["blurb"]}', "", f'## {h["cards"]}', ""]
    for c in cards: o.append(f'- [{c["name"]}, {c["company"]}, {c["year"]}]({c["md_url"]}): {oneline(c["tldr"])}')
    o += ["", f'## {h["topics"]}', ""]
    for t in topics: o.append(f'- [{t["title"]}]({site_url}/{pre}topics/{t["slug"]}/): {oneline(t["summary"])}')
    o += ["", f'## {h["optional"]}', "",
          f'- [llms-full.txt]({site_url}/{pre}llms-full.txt): {h["full"]}', f'- [cards.json]({site_url}/{pre}cards.json): {h["json"]}',
          f'- [{h["ai"]}]({site_url}/{pre}ai/)', f'- [{h["skill"]}]({site_url}/skill/recarch/SKILL.md)', f'- [{h["en"]}]({other})', ""]
    if not mcp_is_placeholder(): o.insert(-1, f'- [MCP]({mcp_url()}): {h["mcp"]}')
    return "\n".join(o)

def llms_full(cards, topics, lang, site_url):
    h = HEAD[lang]; o = [f'# {h["title"]}', "", f'> {h["blurb"]}', ""]
    for t in topics: o += ["", topic_md(t, lang, site_url), "", "-----", ""]
    for c in cards: o += ["", card_md(c, lang), "-----", ""]
    return "\n".join(o)

def cards_json(cards, topics, lang, site_url, generated):
    pre = "" if lang == "zh" else "en/"
    return {"schema_version": SCHEMA_VERSION, "site": "RecArch", "language": "zh-CN" if lang == "zh" else "en", "base_url": f"{site_url}/{pre}", "generated": generated,
            "notice": HEAD[lang]["blurb"], "count": len(cards),
            "numeric_fields": ("每个数字都在 facts 里带 source，即它在本条目里的字段路径；没有报告的数字写作未报告。" if lang == "zh" else "Every number appears in facts with `source`, the field path inside this entry; a number the source does not report is marked not reported."),
            "cards": cards,
            "topics": [{"slug": t["slug"], "title": t["title"], "summary": t["summary"], "problem": t["problem"], "question": t["question"], "framing": t["framing"],
                        "members": t["members"], "decisions": t["decisions"], "differences": t["differences"], "url": f'{site_url}/{pre}topics/{t["slug"]}/'} for t in topics]}

def build_ai_outputs(write, lang, active_cards, topics, L, site_url, nr_label):
    """Called once per language by build.main(). `write(path, text)` is relative to the language root."""
    cards = [public_card(c, L, lang, site_url, nr_label) for c in active_cards]
    generated = max(c["last_verified"] for c in cards)
    for c in cards: write(f"cards/{c['id']}.md", card_md(c, lang))
    write("llms.txt", llms_txt(cards, topics, lang, site_url)); write("llms-full.txt", llms_full(cards, topics, lang, site_url))
    write("cards.json", json.dumps(cards_json(cards, topics, lang, site_url, generated), ensure_ascii=False, indent=1) + "\n")
    return cards

# ---------------------------------------------------------------- Skill, analytics, /ai/ page

def render_skill(out_dir):
    src = os.path.join(ROOT, "skill", "recarch", "SKILL.md")
    if not os.path.exists(src): return
    t = open(src, encoding="utf-8").read().replace(MCP_PLACEHOLDER, mcp_url()).replace("https://jdding.github.io/recarch", os.environ.get("SITE_URL", "https://jdding.github.io/recarch").rstrip("/"))
    os.makedirs(os.path.join(out_dir, "skill", "recarch"), exist_ok=True)
    open(os.path.join(out_dir, "skill", "recarch", "SKILL.md"), "w", encoding="utf-8").write(t)

def analytics_snippet():
    """Cloudflare Web Analytics beacon, only when RECARCH_CF_BEACON_TOKEN is set. Default: off, nothing is injected."""
    tok = os.environ.get("RECARCH_CF_BEACON_TOKEN", "").strip()
    if not tok: return ""
    if not re.fullmatch(r"[A-Za-z0-9]{16,64}", tok): raise SystemExit("RECARCH_CF_BEACON_TOKEN must be the 32-character token from Cloudflare Web Analytics")
    return f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{{"token": "{tok}"}}\'></script>'

PAGE = {
 "zh": {
  "title": "在你的 AI 里用 RecArch", "desc": "把 RecArch 接进 Claude、Cursor 或 ChatGPT，直接查询卡片、对比专题。",
  "lead": "RecArch 的每张卡片都可以被你自己的 AI 助手直接查询。推理费用由你自己的模型承担，RecArch 只提供我们整理的卡片内容。",
  "pending": "接入地址尚未启用。下面的 MCP 地址是占位符，域名和服务上线后会替换成真实地址。",
  "what_h": "这是什么", "what": "一个只读的 MCP 服务，提供三个工具：search_cards 按关键词搜卡片，get_card 取一张卡片的完整内容，compare_topic 按专题或按卡片对比。它读到的只有我们自己的解读，不含论文原文。",
  "notice_h": "关于 RecArch 问答", "notice": "RecArch 问答是依据卡片内容回答问题的卡片助手，与论文作者无关，也不代表作者。它不能替代原文。答案里的数字只来自卡片字段，卡片写作未报告的内容它也只会回答未报告。发现错误请到反馈页面提交纠错。",
  "mcp_h": "接入 MCP", "mcp_note": "地址是占位符，上线前请不要照抄。",
  "claude_h": "Claude", "claude_a": "Claude 网页版或桌面版：设置，连接器，添加自定义连接器，名称填 RecArch，地址填下面这一行。", "claude_b": "Claude Code 命令行：",
  "cursor_h": "Cursor", "cursor_a": "把下面的内容加入 ~/.cursor/mcp.json，项目级配置放在 .cursor/mcp.json：",
  "chatgpt_h": "ChatGPT", "chatgpt_a": "ChatGPT 网页版：Plugins，加号，Add custom MCP server，名称填 RecArch，连接地址填下面这一行，认证选 No authentication，勾选风险提示后创建。是否可用取决于你的套餐和工作区策略。",
  "nomcp_h": "不接 MCP 也能用", "nomcp": "把下面任意一个链接发给你的 AI，请它按内容回答。llms.txt 是索引，llms-full.txt 是全部卡片，cards.json 是带来源字段路径的结构化数据。",
  "skill_h": "安装 Agent Skill", "skill": "Skill 包告诉你的 AI 怎样查询 RecArch、怎样引用卡片、遇到未报告的数字怎么办。下载 SKILL.md，放进 ~/.claude/skills/recarch/ 目录即可，其他支持 Agent Skills 的工具放进各自的 skills 目录。",
  "skill_link": "下载 SKILL.md", "privacy_h": "数据与隐私", "privacy": "服务只读，不需要登录。服务端只记录每天的调用次数、各工具的调用次数、一个由 IP 和日期混合后单向哈希得到的匿名会话标识，以及没有搜到结果的关键词，不保存 IP 原文。",
  "links": "数据入口", "ls": "索引", "lf": "全部卡片", "lj": "结构化数据"},
 "en": {
  "title": "Use RecArch in your AI", "desc": "Connect RecArch to Claude, Cursor or ChatGPT to query cards and compare topics directly.",
  "lead": "Every RecArch card can be queried directly by your own AI assistant. Inference runs on your own model and bill; RecArch only serves the card content we wrote.",
  "pending": "The connection address is not live yet. The MCP URL below is a placeholder and will be replaced once the domain and the service are up.",
  "what_h": "What this is", "what": "A read-only MCP server with three tools: search_cards finds cards by keyword, get_card returns one full card, compare_topic compares a topic or a set of cards. It reads only our own interpretation, never text from the papers.",
  "notice_h": "About the RecArch Q&A", "notice": "The RecArch Q&A is a card assistant that answers from card content. It is not affiliated with the paper authors and does not speak for them, and it is no substitute for the paper. Numbers in its answers come only from card fields; what a card marks as not reported stays not reported. Please report mistakes through the feedback link.",
  "mcp_h": "Connect over MCP", "mcp_note": "The URL is a placeholder; do not copy it before launch.",
  "claude_h": "Claude", "claude_a": "Claude on web or desktop: Settings, Connectors, Add custom connector, name it RecArch and paste the URL below.", "claude_b": "Claude Code in the terminal:",
  "cursor_h": "Cursor", "cursor_a": "Add this to ~/.cursor/mcp.json, or to .cursor/mcp.json for one project:",
  "chatgpt_h": "ChatGPT", "chatgpt_a": "ChatGPT on the web: Plugins, the plus button, Add custom MCP server, name it RecArch, paste the URL below, choose No authentication, accept the risk notice and create it. Availability depends on your plan and workspace policy.",
  "nomcp_h": "Without MCP", "nomcp": "Send any of these links to your AI and ask it to answer from the content. llms.txt is the index, llms-full.txt holds all cards, cards.json is structured data with source field paths.",
  "skill_h": "Install the Agent Skill", "skill": "The skill tells your AI how to query RecArch, how to cite cards and what to do with numbers a card marks as not reported. Download SKILL.md into ~/.claude/skills/recarch/; other tools that support Agent Skills use their own skills folder.",
  "skill_link": "Download SKILL.md", "privacy_h": "Data and privacy", "privacy": "The service is read-only and needs no sign-in. The server only logs daily call counts, per-tool counts, an anonymous session id made by one-way hashing the IP with the date, and queries that returned nothing. The raw IP is never stored.",
  "links": "Data entry points", "ls": "Index", "lf": "All cards", "lj": "Structured data"},
}

def ai_page_body(lang, site_url, E):
    p = PAGE[lang]; pre = "" if lang == "zh" else "en/"; url = mcp_url()
    if lang == "zh":
        for k, v in p.items():
            txt = re.sub(r"[A-Za-z_~./\-]+", "", v)
            if PARENS.search(txt) or PARENS.search(v): raise SystemExit(f"ai page zh copy has parentheses: {k}")
    cj = json.dumps({"mcpServers": {"recarch": {"url": url}}}, indent=2)
    pending = f'<p class="caveat"><b>{E(p["pending"])}</b></p>' if mcp_is_placeholder() else ""
    code = lambda s: f'<pre class="code"><code>{E(s)}</code></pre>'
    return f"""<div class="wrap"><article class="sys ai"><h1>{E(p["title"])}</h1><p class="lead">{E(p["lead"])}</p>{pending}
<section class="blk" id="what"><h2>{E(p["what_h"])}</h2><p>{E(p["what"])}</p></section>
<section class="blk" id="notice"><h2>{E(p["notice_h"])}</h2><p>{E(p["notice"])}</p></section>
<section class="blk" id="mcp"><h2>{E(p["mcp_h"])}</h2><p class="stage-d">{E(p["mcp_note"])}</p>
<h3>{E(p["claude_h"])}</h3><p>{E(p["claude_a"])}</p>{code(url)}<p>{E(p["claude_b"])}</p>{code("claude mcp add --transport http recarch " + url)}
<h3>{E(p["cursor_h"])}</h3><p>{E(p["cursor_a"])}</p>{code(cj)}
<h3>{E(p["chatgpt_h"])}</h3><p>{E(p["chatgpt_a"])}</p>{code(url)}</section>
<section class="blk" id="nomcp"><h2>{E(p["nomcp_h"])}</h2><p>{E(p["nomcp"])}</p><ul class="clean"><li><a href="{E(site_url)}/{pre}llms.txt">llms.txt</a> {E(p["ls"])}</li><li><a href="{E(site_url)}/{pre}llms-full.txt">llms-full.txt</a> {E(p["lf"])}</li><li><a href="{E(site_url)}/{pre}cards.json">cards.json</a> {E(p["lj"])}</li></ul></section>
<section class="blk" id="skill"><h2>{E(p["skill_h"])}</h2><p>{E(p["skill"])}</p><p><a class="btn" href="{E(site_url)}/skill/recarch/SKILL.md">{E(p["skill_link"])}</a></p></section>
<section class="blk" id="privacy"><h2>{E(p["privacy_h"])}</h2><p>{E(p["privacy"])}</p></section></article></div>"""
