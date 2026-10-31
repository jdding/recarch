// GitHub Pages serves only the root 404.html, at any depth. An /en/ path must show the English 404, any other path the Chinese one with the English fallback.
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/notfound.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log("FAIL", m); } else console.log("ok  ", m); };
const raw = fs.readFileSync(dist + "/404.html", "utf8");
const base = (raw.match(/var b=("[^"]*"),p=location/) || [])[1]; ok(!!base, "root 404 carries the site base path: " + base);
const B = base ? JSON.parse(base) : "/";
ok(/<html lang="zh/.test(raw) && /Not found/.test(raw) && /不存在|未找到|找不到/.test(raw), "no-JS fallback is bilingual: zh first, English below");
ok(/noindex/.test(raw), "404 is noindex");
// jsdom cannot replay document.open/write, so the calls are captured. A real browser ignores document.open while the parser is still running
// (that made the first version a silent no-op), so the stub fails the test if it is called before parsing has finished.
async function visit(p) {
  const calls = { html: null, early: false };
  const w = new JSDOM(raw, { url: "https://t.test" + p, runScripts: "dangerously", beforeParse(win) {
    const d = win.document;
    d.open = () => { if (d.readyState === "loading") calls.early = true; };
    d.write = (h) => { if (d.readyState === "loading") calls.early = true; calls.html = h; };
    d.close = () => {};
  } }).window;
  await new Promise((r) => w.addEventListener("load", r));
  return { w, calls, d: calls.html ? new JSDOM(calls.html).window.document : w.document };
}
(async () => {
for (const p of [B + "en/nope", B + "en/systems/zzz/", B + "en/a/b/c/d", B + "en"]) {
  const { calls, d } = await visit(p);
  ok(!!calls.html && !calls.early, `${p}: the English page is written after parsing, not during it`);
  ok(d.documentElement.lang === "en", `${p}: html lang is en (${d.documentElement.lang})`);
  ok(d.querySelector("h1").textContent === "Not found", `${p}: English heading (${d.querySelector("h1").textContent})`);
  ok(!/[\u4e00-\u9fff]/.test(d.body.textContent.replace(/中文|纠错|申请收录/g, "")), `${p}: no Chinese body text`);
  ok(!!d.querySelector(`a[href="${B}en/"]`), `${p}: link back to the English home`);
  ok(d.querySelector("link[rel=stylesheet]").getAttribute("href").startsWith(B), `${p}: assets use the absolute base path`);
}
for (const p of [B + "nope", B + "systems/zzz/", B + "english/x", B + "x/en/y"]) {
  const { calls, d } = await visit(p);
  ok(calls.html === null, `${p}: no swap, stays zh`);
  ok(d.documentElement.lang.startsWith("zh"), `${p}: html lang (${d.documentElement.lang})`);
  ok(d.querySelector("h2[lang=en]") && /Not found/.test(d.querySelector("h2[lang=en]").textContent), `${p}: English fallback line kept`);
}
const en = fs.readFileSync(dist + "/en/404.html", "utf8"); ok(/<html lang="en"/.test(en) && /Not found/.test(en), "en/404.html is the English page");
console.log(fails ? `FAILED ${fails}` : "NOT FOUND: ALL PASS"); process.exit(fails ? 1 : 0);
})();
