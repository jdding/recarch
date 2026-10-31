// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/topics.test.js [dist]
// Topic pages: index, one page per data/topics/*.yaml, a generated table with one row per member, working card links,
// nav entry, sitemap entries; plus every active card has a deployment block in compare data.
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist/en"), T = path.join(__dirname, "../data/topics");
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const dom = (f) => new JSDOM(fs.readFileSync(f, "utf8")).window.document;
const slugs = fs.readdirSync(T).filter((f) => f.endsWith(".yaml")).map((f) => f.slice(0, -5));
ok(slugs.length >= 2, `at least 2 topics, found ${slugs.length}`);
const sysJson = JSON.parse(fs.readFileSync(`${dist}/data/systems.json`, "utf8")), actIds = new Set(sysJson.map((c) => c.id));
ok(sysJson.every((c) => c.deployment && c.deployment.scenario), "every active card carries a deployment block in compare data");
const sitemap = fs.readFileSync(path.join(dist, "../sitemap.xml"), "utf8");
const idx = dom(`${dist}/topics/index.html`);
ok([...idx.querySelectorAll("nav a")].some((a) => a.textContent === "Topics"), "nav has a Topics entry");
for (const s of slugs) {
  const y = fs.readFileSync(`${T}/${s}.yaml`, "utf8");
  const members = [...y.matchAll(/^\s+- id: (\S+)/gm)].map((m) => m[1]);
  ok(members.length >= 3, `${s}: at least 3 members`);
  ok(!!idx.querySelector(`a[href$="topics/${s}/"]`), `${s}: listed on the topics index`);
  ok(sitemap.includes(`/topics/${s}/`), `${s}: in the sitemap`);
  const f = `${dist}/topics/${s}/index.html`; ok(fs.existsSync(f), `${s}: page built`); if (!fs.existsSync(f)) continue;
  const d = dom(f);
  ok(d.querySelectorAll("h1").length === 1, `${s}: one h1`);
  ok(!!d.querySelector("p.lead"), `${s}: framing paragraph`);
  const rows = [...d.querySelectorAll("table.topic tbody tr")];
  ok(rows.length === members.length, `${s}: table has ${members.length} rows, found ${rows.length}`);
  ok([...d.querySelectorAll("table.topic thead th")].map((t) => t.textContent).join("|").startsWith("System|Approach"), `${s}: table header`);
  ok(!!d.querySelector("h2.topic-h"), `${s}: how the approaches differ section`);
  const links = [...d.querySelectorAll("a[href*='systems/']")].map((a) => a.getAttribute("href"));
  for (const id of members) {
    ok(actIds.has(id), `${s}: member ${id} is an active card`);
    ok(links.includes(`../../systems/${id}/`), `${s}: links to ${id}`);
    ok(fs.existsSync(`${dist}/systems/${id}/index.html`), `${s}: card page ${id} exists`);
  }
  ok(!!d.querySelector("a[href*='compare/?ids=']"), `${s}: compare button`);
}
console.log(`${checks - fails}/${checks} checks passed`); process.exit(fails ? 1 : 0);
