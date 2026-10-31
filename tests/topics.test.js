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
const sitemap = fs.readFileSync([path.join(dist, "sitemap.xml"), path.join(dist, "../sitemap.xml")].find((f) => fs.existsSync(f)), "utf8");
const idx = dom(`${dist}/topics/index.html`);
ok([...idx.querySelectorAll("nav a")].some((a) => a.textContent === "Topics" || a.textContent === "专题"), "nav has a Topics entry");
ok(![...idx.querySelectorAll("a")].some((a) => /sponsor\//.test(a.getAttribute("href") || "")), "no sponsor link on the topics index");
ok(!sitemap.includes("/sponsor/"), "no sponsor page in the sitemap");
ok(idx.querySelectorAll(".ttiles .ttile").length === slugs.length, "index has one rich tile per topic");
for (const s of slugs) {
  const y = fs.readFileSync(`${T}/${s}.yaml`, "utf8");
  const members = [...y.matchAll(/^\s+- id: (\S+)/gm)].map((m) => m[1]);
  ok(members.length >= 3, `${s}: at least 3 members`);
  const tile = idx.querySelector(`.ttile a[href$="topics/${s}/"]`);
  ok(!!tile, `${s}: listed on the topics index as a tile`);
  if (tile) {
    ok(!!tile.querySelector(".ttile-p"), `${s}: index tile shows the problem statement`);
    ok(tile.querySelectorAll(".stat").length >= 2, `${s}: index tile has stats`);
    ok(tile.querySelectorAll(".marks .mono").length >= 3, `${s}: index tile has company marks`);
    ok(!!tile.querySelector(".mixbar"), `${s}: index tile has the era mix bar`);
    ok(tile.querySelector(".stat b").textContent === String(members.length), `${s}: index tile system count equals members`);
  }
  ok(sitemap.includes(`/topics/${s}/`), `${s}: in the sitemap`);
  const f = `${dist}/topics/${s}/index.html`; ok(fs.existsSync(f), `${s}: page built`); if (!fs.existsSync(f)) continue;
  const d = dom(f);
  ok(d.querySelectorAll("h1").length === 1, `${s}: one h1`);
  ok(!!d.querySelector("p.lead"), `${s}: framing paragraph`);
  const rows = [...d.querySelectorAll("table.topic tbody tr")];
  ok(rows.length === members.length, `${s}: table has ${members.length} rows, found ${rows.length}`);
  ok([...d.querySelectorAll("table.topic thead th")].map((t) => t.textContent).join("|").match(/^(System|系统)\|(Approach|做法)/), `${s}: table header`);
  ok(!!d.querySelector("h2.topic-h"), `${s}: how the approaches differ section`);
  const links = [...d.querySelectorAll("a[href*='systems/']")].map((a) => a.getAttribute("href"));
  for (const id of members) {
    ok(actIds.has(id), `${s}: member ${id} is an active card`);
    ok(links.includes(`../../systems/${id}/`), `${s}: links to ${id}`);
    ok(fs.existsSync(`${dist}/systems/${id}/index.html`), `${s}: card page ${id} exists`);
  }
  ok(!!d.querySelector("a[href*='compare/?ids=']"), `${s}: compare button`);
  // redesign elements
  const hero = d.querySelector("header.thero");
  ok(!!hero && !!hero.querySelector("h1") && !!hero.querySelector("p.problem") && hero.querySelector("p.problem").textContent.trim().length > 20, `${s}: hero with problem statement`);
  ok(!!hero && !!hero.querySelector(".keyq p") && /\?|？/.test(hero.querySelector(".keyq p").textContent), `${s}: key question is a question`);
  const stats = [...d.querySelectorAll(".thero .stat b")].map((b) => b.textContent);
  ok(stats.length === 4 && stats[0] === String(members.length), `${s}: hero stats start with the system count`);
  ok(/^\d{4}\D+\d{4}$/.test(stats[1] || ""), `${s}: hero shows a year span`);
  const jumps = [...d.querySelectorAll("nav.jump a")].map((a) => a.getAttribute("href"));
  ok(jumps.length >= 5, `${s}: jump links`);
  for (const h of jumps) ok(!!d.getElementById(h.slice(1)), `${s}: jump target ${h} exists`);
  const decs = [...d.querySelectorAll("#decide .dec")];
  ok(decs.length >= 3, `${s}: decision guide has entries`);
  for (const e of decs) ok(!!e.querySelector(".dec-if") && !!e.querySelector(".dec-then") && e.querySelectorAll(".plinks a[href*='systems/']").length >= 1, `${s}: decision entry has if, then and card links`);
  const tiles = [...d.querySelectorAll("#systems .tile")];
  ok(tiles.length === members.length, `${s}: one tile per member, found ${tiles.length}`);
  for (const t of tiles) ok(!!t.querySelector(".mono") && !!t.querySelector(".era-badge") && /\b(19|20)\d\d\b/.test((t.querySelector(".co") || {}).textContent || "") && !!t.querySelector("a[href*='systems/']"), `${s}: tile has company mark, era badge, year and link`);
  const ly = [...d.querySelectorAll("#lineage .ly-i")];
  ok(ly.length === members.length, `${s}: lineage lists every member once, found ${ly.length}`);
  const yrs = [...d.querySelectorAll("#lineage .ly-y")].map((e) => +e.textContent);
  ok(yrs.length >= 2 && yrs.every((v, i) => i === 0 || v > yrs[i - 1]), `${s}: lineage years ascend`);
  const cav = d.querySelector("p.caveat#note");
  ok(!!cav && /not comparable|不能跨行直接比较/.test(cav.textContent), `${s}: online lifts not comparable note is visible above the table`);
  const wrap = d.querySelector(".tbl-topic");
  ok(!!wrap && wrap.getAttribute("tabindex") === "0" && wrap.getAttribute("role") === "region", `${s}: table scroll box is keyboard reachable`);
  ok(rows.every((r) => r.querySelector("th[scope=row]") && r.querySelectorAll("td").length === 4), `${s}: row headers and four data cells per row`);
  ok(rows.every((r) => [...r.querySelectorAll("td.nrc")].every((c) => c.querySelector(".unk"))), `${s}: unreported cells use the muted marker`);
  ok(d.querySelectorAll(".lifts b").length >= 1, `${s}: reported lift numbers are highlighted`);
  ok(d.querySelectorAll("#related .rtile").length >= 1, `${s}: related topics strip`);
  ok(![...d.querySelectorAll("#related a")].some((a) => a.getAttribute("href").includes(`topics/${s}/`)), `${s}: related strip does not link to itself`);
  ok(!!d.querySelector(".nlband[data-source^='topic:']"), `${s}: subscribe box`);
  ok(![...d.querySelectorAll("a")].some((a) => /sponsor\//.test(a.getAttribute("href") || "")), `${s}: no sponsor link`);
}
console.log(`${checks - fails}/${checks} checks passed`); process.exit(fails ? 1 : 0);
