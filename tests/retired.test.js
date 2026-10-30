// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/retired.test.js [dist]
// Retired and superseded cards: page stays reachable with a notice and noindex, but they are absent from the home list, count, timeline,
// carousel, compare data, feed card events and sitemap; they are listed in the home archive. Never deleted.
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist"), D = path.join(__dirname, "../data/systems");
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const files = fs.readdirSync(D).filter((f) => f.endsWith(".yaml"));
const meta = files.map((f) => { const t = fs.readFileSync(`${D}/${f}`, "utf8"); const m = t.match(/^status: (\w+)\s*$/m); return { id: f.slice(0, -5), st: m ? m[1] : "active", to: (t.match(/^superseded_by: (\S+)\s*$/m) || [])[1], versions: (t.match(/^  - name: /gm) || []).length, reason: (t.match(/^status_reason: "(.*)"\s*$/m) || [])[1] }; });
const off = meta.filter((x) => x.st !== "active"), act = meta.filter((x) => x.st === "active");
ok(off.length >= 1, `at least one non-active card to test, found ${off.length}`);
ok(off.every((x) => x.st === "retired" || x.st === "superseded"), "status values are active, superseded or retired");
const home = new JSDOM(fs.readFileSync(`${dist}/index.html`, "utf8")).window.document;
const gridIds = [...home.querySelectorAll("#grid .card")].map((c) => c.dataset.id);
ok(gridIds.length === act.length, `home grid lists ${act.length} active cards, found ${gridIds.length}`);
ok(home.getElementById("count").textContent.trim() === `${act.length} systems`, `home count reads "${act.length} systems", got "${home.getElementById("count").textContent.trim()}"`);
const homeHtml = fs.readFileSync(`${dist}/index.html`, "utf8");
const tl = home.querySelector("#timeline, .timeline"); 
const slides = [...home.querySelectorAll(".carousel .slide")].map((s) => s.dataset.id);
const arch = home.querySelector("details#archive");
ok(!!arch, "home has an archive section");
const archLinks = arch ? [...arch.querySelectorAll("li a")].map((a) => a.getAttribute("href")) : [];
const sitemap = fs.readFileSync(`${dist}/sitemap.xml`, "utf8"), feed = fs.readFileSync(`${dist}/feed.xml`, "utf8");
const sysJson = JSON.parse(fs.readFileSync(`${dist}/data/systems.json`, "utf8")).map((c) => c.id);
ok(sysJson.length === act.length, `compare data holds ${act.length} active cards, found ${sysJson.length}`);
const clog = fs.readFileSync(`${dist}/changelog/index.html`, "utf8");
for (const x of off) {
  ok(!gridIds.includes(x.id), `${x.id}: not in the home grid`);
  ok(!slides.includes(x.id), `${x.id}: not in the carousel`);
  ok(!home.querySelector(`.timeline a[href="systems/${x.id}/"], #timeline a[href="systems/${x.id}/"]`), `${x.id}: not in the timeline`);
  ok(archLinks.includes(`systems/${x.id}/`), `${x.id}: listed in the archive`);
  ok(!sitemap.includes(`/systems/${x.id}/`), `${x.id}: not in the sitemap`);
  ok(!sysJson.includes(x.id), `${x.id}: not in compare data`);
  ok(!feed.includes(`added:${x.id}`) && !feed.includes(`update:${x.id}`), `${x.id}: no added or updated entry in the feed`);
  ok(clog.includes(`systems/${x.to || x.id}/`) && /Retired|Superseded/.test(clog), `${x.id}: the changelog keeps one status entry`);
  const f = `${dist}/systems/${x.id}/index.html`;
  ok(fs.existsSync(f), `${x.id}: page still built`); if (!fs.existsSync(f)) continue;
  ok(fs.existsSync(`${D}/${x.id}.yaml`), `${x.id}: card file kept`);
  const d = new JSDOM(fs.readFileSync(f, "utf8")).window.document;
  if (x.st === "superseded") { // merged into another card: static redirect page
    const tgt = act.find((a) => a.id === x.to);
    ok(!!tgt, `${x.id}: superseded_by ${x.to} is an active card`);
    const rf = d.querySelector('meta[http-equiv="refresh"]'), cn = d.querySelector('link[rel="canonical"]');
    ok(!!rf && rf.content === `0; url=../${x.to}/`, `${x.id}: meta refresh points to ${x.to}`);
    ok(!!cn && /^https?:\/\/[^/]+(\/[^/]+)*\/systems\/[^/]+\/$/.test(cn.href) && cn.href.endsWith(`/systems/${x.to}/`), `${x.id}: canonical is the merged card`);
    ok(!!d.querySelector('meta[name="robots"][content="noindex"]'), `${x.id}: redirect page is noindex`);
    ok(!!d.querySelector(`a[href="../${x.to}/"]`), `${x.id}: redirect page links to ${x.to}`);
    ok(fs.existsSync(`${dist}/systems/${x.to}/index.html`), `${x.id}: target page exists`);
    const td = new JSDOM(fs.readFileSync(`${dist}/systems/${x.to}/index.html`, "utf8")).window.document;
    ok(td.querySelectorAll("#history .versions li").length >= 2, `${x.to}: merged card lists its versions`);
    ok(!!td.querySelector(".b-version"), `${x.to}: merged card shows the version badge`);
    ok(td.querySelectorAll("#sources .tag").length >= 1 && /other version/.test(td.getElementById("sources").textContent), `${x.to}: other versions appear as sources`);
    continue;
  }
  const note = d.getElementById("status-note");
  ok(!!note && /Retired|Superseded/.test(note.textContent), `${x.id}: notice shown`);
  ok(!!note && note.textContent.replace(/\s+/g, " ").includes(x.reason.slice(0, 60)), `${x.id}: notice carries the reason`);
  ok(!!d.querySelector('meta[name="robots"][content="noindex"]'), `${x.id}: noindex`);
  ok(/^(Retired|Superseded):/.test(d.title), `${x.id}: title starts with the status`);
  ok(!d.querySelector('a[href*="compare/?ids="]'), `${x.id}: no compare button`);
  ok(!!d.querySelector("#history .k-retired, #history .k-superseded"), `${x.id}: history records the status change`);
}
for (const x of act.slice(0, 5)) {
  ok(sitemap.includes(`/systems/${x.id}/`), `${x.id}: active card in the sitemap`);
  const d = new JSDOM(fs.readFileSync(`${dist}/systems/${x.id}/index.html`, "utf8")).window.document;
  ok(!d.getElementById("status-note") && !d.querySelector('meta[name="robots"]'), `${x.id}: active page has no notice and no noindex`);
}
console.log(`${checks - fails}/${checks} checks passed, ${off.length} non-active cards, ${act.length} active`);
process.exit(fails ? 1 : 0);
