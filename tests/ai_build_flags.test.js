// Build-time switches of the AI layer, each checked by building a copy of the repo into a temp dir.
//  - RECARCH_CF_BEACON_TOKEN unset: no analytics script anywhere. Set: one Cloudflare beacon per html page. Malformed: build fails.
//  - RECARCH_MCP_URL replaces the placeholder in the /ai/ page, llms.txt and the skill.
//  - reviewed: true on one FAQ file shows that FAQ on the page, in the md and in cards.json; every other card stays without one.
// Run: SITE_URL=https://jdding.github.io/recarch node tests/ai_build_flags.test.js   (needs python3 and PyYAML)
const fs = require("fs"), path = require("path"), os = require("os"), cp = require("child_process");
const repo = path.join(__dirname, ".."); const SITE = process.env.SITE_URL || "https://jdding.github.io/recarch";
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "recarch-flags-"));
const copy = path.join(tmp, "repo");
fs.cpSync(repo, copy, { recursive: true, filter: (s) => !/\/(dist|node_modules|mcp-worker|__pycache__|\.git)(\/|$)/.test(s) });
const build = (out, env = {}) => cp.spawnSync("python3", ["build.py"], { cwd: copy, env: { ...process.env, SITE_URL: SITE, RECARCH_OUT: out, RECARCH_CF_BEACON_TOKEN: "", RECARCH_MCP_URL: "", ...env }, encoding: "utf8" });
const htmls = (d) => { const o = []; (function w(p) { for (const e of fs.readdirSync(p, { withFileTypes: true })) { const q = path.join(p, e.name); if (e.isDirectory()) w(q); else if (q.endsWith(".html")) o.push(q); } })(d); return o; };
const TOKEN = "0123456789abcdef0123456789abcdef";

let out = path.join(tmp, "off"); let r = build(out);
ok(r.status === 0, "default build succeeds: " + (r.stderr || "").slice(0, 200));
ok(htmls(out).every((f) => !/cloudflareinsights|data-cf-beacon/.test(fs.readFileSync(f, "utf8"))), "analytics is off by default: no beacon in any page");
ok(/mcp\.recarch\.example\/mcp/.test(fs.readFileSync(`${out}/ai/index.html`, "utf8")), "placeholder MCP URL by default");

out = path.join(tmp, "on"); r = build(out, { RECARCH_CF_BEACON_TOKEN: TOKEN, RECARCH_MCP_URL: "https://mcp.example.org/mcp" });
ok(r.status === 0, "build with token succeeds");
const pages = htmls(out); const withBeacon = pages.filter((f) => fs.readFileSync(f, "utf8").includes(`data-cf-beacon='{"token": "${TOKEN}"}'`));
ok(pages.length > 100 && withBeacon.length === pages.length, `beacon on every page, ${withBeacon.length} of ${pages.length}`);
ok(pages.every((f) => (fs.readFileSync(f, "utf8").match(/static\.cloudflareinsights\.com\/beacon\.min\.js/g) || []).length === (f === path.join(out, "404.html") ? 2 : 1)), "exactly one beacon per page (the root 404 also embeds the English 404 as a string, so two)");
ok(!/cloudflareinsights|TOKEN/.test(fs.readFileSync(`${out}/llms.txt`, "utf8") + fs.readFileSync(`${out}/cards.json`, "utf8")), "token never reaches the data files");
const ai = fs.readFileSync(`${out}/ai/index.html`, "utf8");
ok(ai.includes("https://mcp.example.org/mcp") && !/mcp\.recarch\.example/.test(ai) && !/尚未启用/.test(ai), "RECARCH_MCP_URL replaces the placeholder and removes the not-live banner");
ok(/https:\/\/mcp\.example\.org\/mcp/.test(fs.readFileSync(`${out}/llms.txt`, "utf8")) && /https:\/\/mcp\.example\.org\/mcp/.test(fs.readFileSync(`${out}/skill/recarch/SKILL.md`, "utf8")), "llms.txt and the skill carry the real MCP URL");
r = build(path.join(tmp, "bad"), { RECARCH_CF_BEACON_TOKEN: "<script>alert(1)</script>" });
ok(r.status !== 0 && /RECARCH_CF_BEACON_TOKEN/.test(String(r.stderr) + String(r.stdout)), "malformed token fails the build instead of injecting it");

// FAQ gate, positive case: in the copy, set every FAQ file to reviewed: false, then flip one to true
for (const f of fs.readdirSync(`${copy}/data/faq`)) { const q = `${copy}/data/faq/${f}`; fs.writeFileSync(q, fs.readFileSync(q, "utf8").replace(/^reviewed: true$/m, "reviewed: false")); }
const id = "airbnb-listing-embeddings-2018", yf = `${copy}/data/faq/${id}.yaml`;
fs.writeFileSync(yf, fs.readFileSync(yf, "utf8").replace(/^reviewed: false$/m, "reviewed: true"));
out = path.join(tmp, "faq"); r = build(out); ok(r.status === 0, "build with one reviewed FAQ succeeds");
for (const [d, pre] of [[out, ""], [`${out}/en`, "en/"]]) {
  const page = fs.readFileSync(`${d}/systems/${id}/index.html`, "utf8");
  ok(/id="faq"/.test(page) && (page.match(/class="faq-i"/g) || []).length >= 5, `${pre || "zh"}: reviewed FAQ renders on the card page`);
  ok(page.indexOf('id="faq"') > page.indexOf('id="sources"') && page.indexOf('id="faq"') < page.indexOf('id="history"'), `${pre || "zh"}: FAQ sits between sources and history`);
  const cj = JSON.parse(fs.readFileSync(`${d}/cards.json`, "utf8")); const withFaq = cj.cards.filter((c) => c.faq && c.faq.length);
  ok(withFaq.length === 1 && withFaq[0].id === id, `${pre || "zh"}: only the reviewed card has faq in cards.json`);
  ok(/^## (FAQ|常见问题)$/m.test(fs.readFileSync(`${d}/cards/${id}.md`, "utf8")), `${pre || "zh"}: md has the FAQ`);
  const other = fs.readdirSync(`${d}/systems`).find((x) => x !== id); ok(!/id="faq"/.test(fs.readFileSync(`${d}/systems/${other}/index.html`, "utf8")), `${pre || "zh"}: unreviewed cards show no FAQ`);
}
fs.rmSync(tmp, { recursive: true, force: true });
console.log(fails ? `${fails} FAILED of ${checks}` : `ai_build_flags: ${checks} checks passed`); process.exit(fails ? 1 : 0);
