// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/retired.test.js [dist/en]
// Retired and superseded cards are never published, in either language: no page, no archive section, no status events (changelog, feed,
// home latest updates, carousel), no entry in compare data, topics, sitemap or any link. Their YAML stays in data/systems/ (status logic and admission rules stay).
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist/en"), D = path.join(__dirname, "../data/systems");
const root = path.join(dist, "..").replace(/\/en\/?$/, ""), roots = [root, path.join(root, "en")];
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const files = fs.readdirSync(D).filter((f) => f.endsWith(".yaml"));
const meta = files.map((f) => { const t = fs.readFileSync(`${D}/${f}`, "utf8"); const m = t.match(/^status: (\w+)\s*$/m); return { id: f.slice(0, -5), st: m ? m[1] : "active" }; });
const off = meta.filter((x) => x.st !== "active"), act = meta.filter((x) => x.st === "active");
ok(off.length >= 1, `at least one non-active card to test, found ${off.length}`);
ok(off.every((x) => x.st === "retired" || x.st === "superseded"), "status values are active, superseded or retired");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
const all = walk(root).filter((f) => /\.(html|xml|json|js|txt|css)$/.test(f)).map((f) => ({ f, t: fs.readFileSync(f, "utf8") }));
for (const x of off) {
  ok(fs.existsSync(`${D}/${x.id}.yaml`), `${x.id}: data file kept`);
  for (const r of roots) ok(!fs.existsSync(`${r}/systems/${x.id}`), `${x.id}: no page in ${path.relative(root, r) || "zh"}`);
  const hit = all.filter((a) => a.t.includes(x.id)).map((a) => path.relative(root, a.f));
  ok(!hit.length, `${x.id}: id appears nowhere in the build (${hit.slice(0, 3).join(", ")})`);
}
for (const r of roots) {
  const tag = path.relative(root, r) || "zh";
  const dirs = fs.readdirSync(`${r}/systems`).sort();
  ok(JSON.stringify(dirs) === JSON.stringify(act.map((a) => a.id).sort()), `${tag}: systems/ holds exactly the ${act.length} active cards, found ${dirs.length}`);
  const html = fs.readFileSync(`${r}/index.html`, "utf8"), home = new JSDOM(html).window.document;
  ok(!home.querySelector("details#archive, .archive"), `${tag}: no archive section on the home page`);
  ok([...home.querySelectorAll("#grid .card")].length === act.length, `${tag}: home grid lists ${act.length} active cards`);
  const sysJson = JSON.parse(fs.readFileSync(`${r}/data/systems.json`, "utf8")).map((c) => c.id);
  ok(JSON.stringify(sysJson.slice().sort()) === JSON.stringify(act.map((a) => a.id).sort()), `${tag}: compare data holds exactly the active cards`);
  const feed = fs.readFileSync(`${r}/feed.xml`, "utf8"), clog = fs.readFileSync(`${r}/changelog/index.html`, "utf8");
  ok(!/status:/.test(feed) && !/k-retired|k-superseded/.test(clog + html), `${tag}: no status events in feed, changelog or home`);
  ok(!/(Retired|Superseded|retired|superseded|已退役|已被取代|归档)/.test(feed + clog.replace(/<script[\s\S]*?<\/script>/g, "")), `${tag}: no retired or superseded wording in feed or changelog`);
  ok(!/Archive:|归档：/.test(html), `${tag}: no archive wording on the home page`);
  const slides = [...home.querySelectorAll(".carousel .slide")].map((s) => s.dataset.id);
  ok(slides.every((i) => act.some((a) => a.id === i)), `${tag}: carousel holds only active cards`);
  // every internal card link on every page resolves to an active card
  for (const a of all.filter((a) => a.f.startsWith(r + "/") && a.f.endsWith(".html") && (r !== root || !a.f.startsWith(root + "/en/")))) {
    for (const m of a.t.matchAll(/href="[^"#]*?systems\/([^\/"#?]+)\//g)) if (!act.some((x) => x.id === m[1])) ok(false, `${path.relative(root, a.f)}: link to non-active card ${m[1]}`);
  }
}
const sitemap = fs.readFileSync(`${root}/sitemap.xml`, "utf8");
for (const x of act.slice(0, 5)) ok(sitemap.includes(`/systems/${x.id}/`), `${x.id}: active card in the sitemap`);
ok(!/status-note|noindex/.test(all.filter((a) => a.f.includes("/systems/")).map((a) => a.t).join("")), "no card page carries a status notice or noindex");
console.log(`${checks - fails}/${checks} checks passed, ${off.length} non-active cards unpublished, ${act.length} active`);
process.exit(fails ? 1 : 0);
