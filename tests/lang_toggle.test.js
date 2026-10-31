// The language link must carry the live URL state, including filters applied after load (app.js rewrites the URL with history.replaceState).
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/lang_toggle.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log("FAIL", m); } else console.log("ok  ", m); };
const appjs = fs.readFileSync(dist + "/static/app.js", "utf8");
function load(file, url, app = true) {
  const dom = new JSDOM(fs.readFileSync(dist + "/" + file, "utf8"), { url, runScripts: "dangerously", pretendToBeVisual: true });
  if (app) dom.window.eval(appjs); return dom.window;
}
const fire = (w, el, t) => el.dispatchEvent(new w.Event(t, { bubbles: true }));
for (const [file, base, twin] of [["index.html", "https://t.test/recarch/", "en/"], ["en/index.html", "https://t.test/recarch/en/", "../"]]) {
  const w = load(file, base), d = w.document, a = d.querySelector(".langsw a");
  ok(a.getAttribute("href") === twin, `${file}: starts as the plain twin link ${twin}`);
  const q = d.getElementById("q"); q.value = "tiger"; fire(w, q, "input");
  ok(w.location.search === "?q=tiger", `${file}: app.js put the search in the URL (${w.location.search})`);
  fire(w, a, "mouseenter"); ok(a.getAttribute("href") === twin + "?q=tiger", `${file}: hover picks up the search, got ${a.getAttribute("href")}`);
  const chip = d.querySelector(".group[data-group=era] .chip"); chip.click();
  fire(w, a, "click"); ok(/^[^?]*\?q=tiger&era=/.test(a.getAttribute("href")) && a.getAttribute("href").startsWith(twin), `${file}: click picks up search and filter, got ${a.getAttribute("href")}`);
  fire(w, a, "focus"); fire(w, a, "contextmenu"); fire(w, a, "auxclick");
  ok((a.getAttribute("href").match(/\?/g) || []).length === 1, `${file}: repeated updates never stack a second query string`);
  w.history.replaceState(null, "", w.location.pathname + "#x"); fire(w, a, "mouseenter");
  ok(a.getAttribute("href") === twin + "#x", `${file}: cleared filters and a hash: ${a.getAttribute("href")}`);
}
{ const w = load("systems/din-alibaba-2017/index.html", "https://t.test/recarch/systems/din-alibaba-2017/#results", false), a = w.document.querySelector(".langsw a");
  ok(a.getAttribute("href").endsWith("#results"), "card page: the hash is carried over at load: " + a.getAttribute("href")); }
console.log(fails ? `FAILED ${fails}` : "LANG TOGGLE: ALL PASS"); process.exit(fails ? 1 : 0);
