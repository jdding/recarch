// Run after `python3 build.py`: SITE_URL=https://jdding.github.io/recarch NODE_PATH=/tmp/jt/node_modules node tests/ai_layer.test.js [distRoot]
// CI-style provenance check for the AI-native outputs: llms.txt, llms-full.txt, cards.json, cards/<id>.md, in zh (site root) and en (/en/).
// Fails if any output holds text that is not derived from card fields: source-document paths, a fulltext block, or a number no card field has.
const fs = require("fs"), path = require("path");
const root = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const NUM = (t) => new Set(String(t).replace(/,/g, "").match(/\d+(?:[.,]\d+)*/g) || []);
const stripUrls = (t) => t.replace(/https?:\/\/[^\s)\]>"']+/g, " ");
const SITE = process.env.SITE_URL || "https://jdding.github.io/recarch";
const sub = (a, b) => [...a].filter((x) => !b.has(x));
const get = (o, p) => p.split(".").reduce((x, k) => (x == null ? undefined : x[k]), o);
const STRIP = ["fulltext", "needs_fulltext"];
const clean = (c) => { const d = { ...c }; STRIP.forEach((k) => delete d[k]); if (d.deployment) { d.deployment = { ...d.deployment }; delete d.deployment.fulltext_refs; delete d.deployment.basis; } return d; };
const faqState = {};
for (const f of fs.readdirSync(path.join(__dirname, "../data/faq")).filter((f) => f.endsWith(".yaml"))) faqState[f.slice(0, -5)] = /^reviewed: true\s*$/m.test(fs.readFileSync(path.join(__dirname, "../data/faq", f), "utf8"));

for (const lang of ["zh", "en"]) {
  const d = lang === "zh" ? root : path.join(root, "en"), pre = lang === "zh" ? "" : "en/";
  const sys = JSON.parse(fs.readFileSync(`${d}/data/systems.json`, "utf8")); const ids = sys.map((c) => c.id).sort();
  const L = (m) => `${lang}: ${m}`;
  // --- llms.txt, llmstxt.org shape
  const ll = fs.readFileSync(`${d}/llms.txt`, "utf8"); const lines = ll.split("\n");
  ok(/^# \S/.test(lines[0]), L("llms.txt starts with an H1"));
  ok(/^> \S/m.test(ll) && ll.indexOf("> ") < ll.indexOf("\n## "), L("llms.txt has a blockquote summary before the first H2"));
  ok((ll.match(/^## /gm) || []).length >= 3, L("llms.txt has H2 sections of link lists"));
  const cardLines = lines.filter((l) => l.includes(`/${pre}cards/`) && l.startsWith("- ["));
  ok(cardLines.length === ids.length, L(`llms.txt has one line per card, ${ids.length}, found ${cardLines.length}`));
  const linked = cardLines.map((l) => (l.match(/\]\(([^)]+)\)/) || [])[1]);
  ok(eq(linked.map((u) => u.split("/").pop().replace(/\.md$/, "")).sort(), ids), L("llms.txt links the .md of every active card and nothing else"));
  ok(cardLines.every((l) => /^- \[[^\]]+\]\(https?:[^)]+\.md\): \S/.test(l)), L("each card line is [title](md url): summary"));
  ok(linked.every((u) => u.startsWith(`${SITE}/${pre}cards/`) && fs.existsSync(`${d}/cards/${u.split("/").pop()}`)), L("every linked .md exists in the build"));
  ok(lines.some((l) => l.startsWith("## ")) && !lines.some((l) => /^#{3,}/.test(l)), L("llms.txt uses only H1 and H2"));
  // --- cards.json
  const cj = JSON.parse(fs.readFileSync(`${d}/cards.json`, "utf8"));
  ok(cj.schema_version === "1.0" && cj.count === ids.length && cj.cards.length === ids.length, L("cards.json has schema_version 1.0 and every active card"));
  ok(eq(cj.cards.map((c) => c.id).sort(), ids), L("cards.json ids equal the active card ids"));
  const NRW = lang === "zh" ? "未报告" : "not reported";
  const byId = Object.fromEntries(sys.map((c) => [c.id, c]));
  for (const c of cj.cards) {
    ok(Array.isArray(c.facts) && c.facts.length > 0, L(`${c.id}: facts present`));
    for (const f of c.facts) {
      const v = get(c, f.source);
      ok(typeof f.source === "string" && v !== undefined, L(`${c.id}: fact source ${f.source} resolves in the entry`));
      if (f.reported === false) ok(f.value == null && f.status === NRW && v === NRW, L(`${c.id}: ${f.source} is marked ${NRW}, no invented value`));
      else ok(String(v) === String(f.value), L(`${c.id}: fact ${f.source} value equals the field`));
    }
    for (const k of STRIP) ok(!(k in c), L(`${c.id}: no ${k}`));
    ok(!c.deployment || !("fulltext_refs" in c.deployment), L(`${c.id}: no deployment.fulltext_refs`));
    // every card number comes from the site's own card data
    const bad = sub(NUM(stripUrls(JSON.stringify({ ...c, facts: undefined, faq: undefined, url: undefined, md_url: undefined }))), NUM(JSON.stringify(clean(byId[c.id])) + " " + JSON.stringify(cj.cards.length)));
    ok(bad.length === 0, L(`${c.id}: cards.json numbers all in card fields, extra ${bad}`));
    ok(c.url === `${SITE}/${pre}systems/${c.id}/` && c.md_url === `${SITE}/${pre}cards/${c.id}.md`, L(`${c.id}: page and md URLs`));
  }
  // --- cards/<id>.md
  const mds = fs.readdirSync(`${d}/cards`).filter((f) => f.endsWith(".md")).map((f) => f.slice(0, -3)).sort();
  ok(eq(mds, ids), L("one .md per active card"));
  const pool = {}; let all = new Set();
  for (const id of ids) {
    const md = fs.readFileSync(`${d}/cards/${id}.md`, "utf8");
    pool[id] = NUM(JSON.stringify(clean(byId[id]))); pool[id].forEach((x) => all.add(x));
    ok(md.startsWith(`# ${byId[id].name}\n`), L(`${id}.md: H1 is the card name`));
    const bad = sub(NUM(stripUrls(md)), pool[id]);
    ok(bad.length === 0, L(`${id}.md: numbers not on the card: ${bad}`));
    ok(/RecArch/.test(md) && (lang === "zh" ? /与论文作者无关/.test(md) : /not affiliated with the paper authors/.test(md)), L(`${id}.md: carries the unaffiliated notice`));
    if (lang === "zh") { // glue text added by the exporter has no parentheses: the md has no more than the card fields themselves, source lines and URLs aside
      const P = (t) => (t.match(/[()（）]/g) || []).length, body = md.split("\n").filter((l) => !/^- \[.*\]\(https?:.*\)$/.test(l) && !/^- https?:/.test(l)).join("\n");
      ok(P(stripUrls(body)) <= P(JSON.stringify({ ...clean(byId[id]), sources: [] })), L(`${id}.md: no parentheses added to Chinese copy`));
    }
    const unrep = (byId[id].deployment || {}).serving_latency; if (unrep === "not_reported") ok(md.includes(`${lang === "zh" ? "服务延迟" : "Serving latency"}: ${NRW}`) || md.includes(`服务延迟: ${NRW}`), L(`${id}.md: unreported latency stays ${NRW}`));
  }
  // --- no source-document trace anywhere in the AI outputs
  const files = ["llms.txt", "llms-full.txt", "cards.json", ...mds.map((m) => `cards/${m}.md`)];
  for (const f of files) {
    const t = fs.readFileSync(`${d}/${f}`, "utf8"), u = stripUrls(t);
    ok(!/zotero/i.test(t) && !/站长/.test(t), L(`${f}: no zotero or maintainer words`));
    ok(!/\.pdf\b/i.test(u) && !/\blocal_pdf\b|\bpdf_url\b|\bfulltext\b|sections_read/.test(t), L(`${f}: no pdf file reference or fulltext block outside source URLs`));
    ok(!/(^|[\s"'(])(\/home\/|\/Users\/|\/workspace\/|[A-Za-z]:\\)/.test(u), L(`${f}: no local file path`));
  }
  const full = fs.readFileSync(`${d}/llms-full.txt`, "utf8");
  const badFull = sub(NUM(stripUrls(full)), all);
  ok(badFull.length === 0, L(`llms-full.txt numbers all on cards, extra ${badFull.slice(0, 8)}`));
  ok(ids.every((id) => full.includes(`# ${byId[id].name}\n`)), L("llms-full.txt holds every card"));
  // --- FAQ gate: shown only for reviewed: true
  for (const id of ids) {
    const page = fs.readFileSync(`${d}/systems/${id}/index.html`, "utf8"), rev = faqState[id] === true;
    ok(rev === /id="faq"/.test(page), L(`${id}: FAQ section on the page iff reviewed`));
    const card = cj.cards.find((c) => c.id === id), md = fs.readFileSync(`${d}/cards/${id}.md`, "utf8");
    ok(rev === (card.faq && card.faq.length > 0) || (rev && card.faq === undefined), L(`${id}: cards.json faq iff reviewed`));
    ok(rev === /^## (FAQ|常见问题)$/m.test(md), L(`${id}: md FAQ iff reviewed`));
  }
  // --- /ai/ page
  const ai = fs.readFileSync(`${d}/ai/index.html`, "utf8");
  ok(/<h1>(在你的 AI 里用 RecArch|Use RecArch in your AI)<\/h1>/.test(ai), L("/ai/ page title"));
  ok(/claude mcp add --transport http recarch https?:\/\//.test(ai) && /mcpServers/.test(ai) && /Add custom MCP server|添加自定义连接器|Add custom connector/.test(ai), L("/ai/ page has Claude, Cursor and ChatGPT setup"));
  ok(/mcp\.recarch\.example\/mcp/.test(ai) || process.env.RECARCH_MCP_URL, L("/ai/ page uses the placeholder MCP URL until a real one is set"));
  ok(!/虚拟通讯作者|virtual corresponding author/i.test(ai + full), L("no impersonation framing"));
}
function eq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
// shared files
const skill = fs.readFileSync(`${root}/skill/recarch/SKILL.md`, "utf8");
ok(/^---\nname: recarch\ndescription: .+\n---/.test(skill) && !/zotero/i.test(skill), "skill/recarch/SKILL.md has frontmatter and no zotero");
const sm = fs.readFileSync(`${root}/sitemap.xml`, "utf8");
ok(/\/ai\/<\/loc>/.test(sm), "sitemap lists /ai/");
console.log(fails ? `${fails} FAILED of ${checks}` : `ai_layer: ${checks} checks passed`); process.exit(fails ? 1 : 0);
