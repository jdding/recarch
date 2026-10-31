// Copy hygiene: no internal wording, no raw null/false, no untranslated tag ids or glossary labels on Chinese pages.
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/copy.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0, n = 0; const ok = (c, m) => { n++; if (!c) { fails++; console.log("FAIL", m); } };
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(d + "/" + e.name) : [d + "/" + e.name]);
const files = walk(dist), text = files.filter((f) => /\.(html|json|xml|js|css|txt|svg|webmanifest)$/.test(f)), rel = (f) => path.relative(dist, f);
for (const f of text) { const t = fs.readFileSync(f, "utf8"); ok(!/zotero/i.test(t) && !t.includes("站长"), `${rel(f)}: no Zotero or 站长 wording`); }
ok(!files.some((f) => /\.pdf$/i.test(f) || /zotero/i.test(f)), "no PDF or zotero file in dist");
const terms = fs.readFileSync(path.join(__dirname, "../data/i18n/zh/terms.txt"), "utf8").split("\n").filter((l) => l.trim() && !l.startsWith("#")).map((l) => l.split(" || ")[0].trim());
const ids = fs.readdirSync(dist + "/systems").filter((i) => fs.existsSync(`${dist}/systems/${i}/index.html`));
const leaf = (d) => [...d.querySelectorAll("main *")].filter((e) => !e.children.length && !e.closest("script,style,svg")).map((e) => e.textContent.trim()).filter(Boolean);
const slug = /^[a-z]+(-[a-z0-9]+)+$/;
let zhChecked = 0, lead = 0;
for (const lang of ["", "en/"]) {
  for (const id of ids) {
    const f = `${dist}/${lang}systems/${id}/index.html`; if (/http-equiv="refresh"/.test(fs.readFileSync(f, "utf8"))) continue;
    const d = new JSDOM(fs.readFileSync(f, "utf8")).window.document, vis = d.querySelector("main").textContent, L = leaf(d);
    ok(!/\b(null|None|undefined|NaN)\b/.test(vis) && !/\b(True|False|true|false)\b/.test(vis), `${lang}${id}: no raw null or boolean in visible text`);
    ok(!/published_version_checked|venue_year|evidence_level|results_reported|not_reported|model_family|id_tokenization/.test(vis), `${lang}${id}: no internal field name`);
    if (lang === "") {
      zhChecked++;
      ok(L.every((t) => !slug.test(t)), `${id}: zh tags and chips are translated: ${L.filter((t) => slug.test(t))}`);
      const cells = [...d.querySelectorAll("main th, main td, main b, main dt")].filter((e) => !e.children.length).map((e) => e.textContent.trim().replace(/:$/, ""));
      const bad = cells.filter((t) => terms.includes(t)); ok(bad.length === 0, `${id}: glossary labels translated in tables: ${bad}`);
      ok(!/\b(About|Over|Roughly) [-+\d]/.test(vis), `${id}: no English approximation word before a number`);
    }
  }
}
ok(zhChecked >= 70, `${zhChecked} zh cards checked`);
for (const f of ["index.html", "systems/index.html", "topics/index.html"].filter((x) => fs.existsSync(`${dist}/${x}`))) {
  const d = new JSDOM(fs.readFileSync(`${dist}/${f}`, "utf8")).window.document, chips = [...d.querySelectorAll(".chip, .tag, .badge")].map((e) => e.textContent.trim());
  ok(chips.every((t) => !slug.test(t)), `${f}: no raw tag id in chips: ${chips.filter((t) => slug.test(t))}`);
}
console.log(fails ? `FAILED ${fails} of ${n}` : `COPY: ${n} checks passed`); process.exit(fails ? 1 : 0);
