// Run: NODE_PATH=/tmp/jt/node_modules node tests/sort.test.js [dist]   (tests "Most cited" sort on the built home page)
const { JSDOM } = require("jsdom"); const fs = require("fs"); const dist = process.argv[2] || __dirname + "/../dist/en";
const html = fs.readFileSync(dist + "/index.html", "utf8"), js = fs.readFileSync(dist + "/../static/app.js", "utf8");
const _F = require("fs"), _D = __dirname + "/../data/systems", _Y = _F.readdirSync(_D).filter((f) => f.endsWith(".yaml") && !/^status: (retired|superseded)\s*$/m.test(_F.readFileSync(_D + "/" + f, "utf8"))), N_CARDS = _Y.length, N_GEN = _Y.filter((f) => /^era: generative\s*$/m.test(_F.readFileSync(_D + "/" + f, "utf8"))).length;
let fail = 0; const ok = (c, m) => { console.log(c ? "OK  " : "FAIL", m); if (!c) fail++; };
function mk(url) { const d = new JSDOM(html, { runScripts: "outside-only", url: url || "http://localhost/" }); d.window.alert = () => {}; d.window.eval(js); return d.window; }
let w = mk(), D = w.document; const ids = () => [...D.querySelectorAll("#grid .card")].map((c) => c.dataset.id);
const visIds = () => [...D.querySelectorAll("#grid .card")].filter((c) => !c.hidden).map((c) => c.dataset.id);
const sel = D.getElementById("sort"), set = (v) => { sel.value = v; sel.dispatchEvent(new w.Event("change", { bubbles: true })); };
const orig = ids(), cites = (id) => { const c = D.querySelector(`#grid .card[data-id="${id}"]`); return c.dataset.cites === undefined ? null : +c.dataset.cites; };
const withC = orig.filter((i) => cites(i) !== null), without = orig.filter((i) => cites(i) === null);
ok(withC.length > 40, `cards with counts: ${withC.length}, without: ${without.length}`);
ok([...sel.options].map((o) => o.value).join() === "default,cites" && sel.value === "default", "sort control: Default + Most cited, default selected");
set("cites"); let s = ids();
ok(s.length === N_CARDS, `all ${N_CARDS} cards still present`);
const cs = s.map(cites), firstNull = cs.indexOf(null);
ok(firstNull === withC.length && cs.slice(firstNull).every((x) => x === null), "cards without count are last (never treated as 0)");
ok(cs.slice(0, firstNull).every((x, i, a) => i === 0 || a[i - 1] >= x), "counted cards in descending order: top=" + s.slice(0, 3).map((i) => i + ":" + cites(i)).join(", "));
ok(JSON.stringify(s.slice(firstNull)) === JSON.stringify(without), "uncounted keep their default relative order");
ok(w.location.search === "?sort=cites", "URL has ?sort=cites: " + w.location.search);
// filter + sort
D.querySelector('.group[data-group=era] .chip[data-v="generative"]').click();
const v = visIds(), vc = v.map(cites).filter((x) => x !== null);
ok(v.length === N_GEN && vc.every((x, i) => i === 0 || vc[i - 1] >= x), `era filter + sort: ${N_GEN} visible, still sorted`);
D.getElementById("reset").click(); set("default");
ok(JSON.stringify(ids()) === JSON.stringify(orig), "Default restores original order"); ok(w.location.search === "", "URL cleared");
// deep link
w = mk("http://localhost/?sort=cites"); D = w.document;
ok(D.getElementById("sort").value === "cites" && JSON.stringify([...D.querySelectorAll("#grid .card")].map((c) => c.dataset.id)) === JSON.stringify(s), "?sort=cites deep link applies sort on load");
D.querySelector('.seg button[data-view="timeline"]').click();
ok(D.getElementById("sortwrap").hidden === true, "sort control hidden in timeline view");
console.log(fail ? "FAILED " + fail : "SORT: ALL PASS"); process.exit(fail ? 1 : 0);
