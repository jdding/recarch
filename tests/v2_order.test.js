// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/v2_order.test.js [dist]
// Cited by is optional, blog-only cards have none. Every card page uses the v2 layout with a fixed section order. The architecture block exists only for cards with a diagram.
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const _F = require("fs"), _D = __dirname + "/../data/systems", _Y = _F.readdirSync(_D).filter((f) => f.endsWith(".yaml")), N_SUP = _Y.filter((f) => /^status: superseded\s*$/m.test(_F.readFileSync(_D + "/" + f, "utf8"))).length, N_CARDS = _Y.length, N_GEN = _Y.filter((f) => /^era: generative\s*$/m.test(_F.readFileSync(_D + "/" + f, "utf8"))).length;
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; console.log("FAIL", m); } };
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const ids = fs.readdirSync(`${dist}/systems`).filter((d) => fs.existsSync(`${dist}/systems/${d}/index.html`)).sort();
ok(ids.length === N_CARDS, `${N_CARDS} card pages, found ${ids.length}`);
// merged-away (superseded) cards are static redirect pages, not v2 layouts; retired.test.js checks them
const redirects = ids.filter((id) => /http-equiv="refresh"/.test(fs.readFileSync(`${dist}/systems/${id}/index.html`, "utf8")));
ok(redirects.length === N_SUP, `${N_SUP} superseded cards are redirect pages, found ${redirects.length}`);
const base = ["top", "key-facts", "how-it-works", "results", "subscribe", "details", "limitations", "sources", "history"];
const cellNames = ["Stage", "Core idea", "Deployed in", "Scale", "Headline result", "Code status"];
let withDiagram = [];
for (const id of ids.filter((i) => !redirects.includes(i))) {
  const d = new JSDOM(fs.readFileSync(`${dist}/systems/${id}/index.html`, "utf8")).window.document;
  const art = d.querySelector("article.sys.v2");
  ok(!!art, `${id}: uses the v2 layout`); if (!art) continue;
  const seen = [...art.querySelectorAll("[id]")].map((e) => e.id).filter((i) => [...base, "architecture"].includes(i));
  const hasArch = seen.includes("architecture");
  const hasLim = seen.includes("limitations");
  const want = base.filter((i) => i !== "limitations" || hasLim);
  if (hasArch) want.splice(2, 0, "architecture");
  ok(eq(seen, want), `${id}: sections in order, got ${seen.join(" > ")}`);
  if (hasArch) {
    withDiagram.push(id);
    ok(!!d.querySelector("#architecture figure.diagram svg"), `${id}: architecture holds a diagram`);
  } else {
    ok(!d.querySelector(".diagram, #architecture, .toc a[href='#architecture']"), `${id}: no empty diagram box or TOC link`);
  }
  const toc = [...d.querySelectorAll(".toc a")].map((a) => a.getAttribute("href").slice(1));
  ok(toc.every((t) => !!d.getElementById(t)), `${id}: every TOC link has a target`);
  const det = d.querySelector("#details");
  ok(det.tagName === "DETAILS" && !det.hasAttribute("open"), `${id}: technical details collapsed`);
  ok(eq([...d.querySelectorAll("#key-facts .kf small")].map((e) => e.textContent), cellNames), `${id}: 6 key fact cells in order`);
  ok([...d.querySelectorAll("#key-facts .kf")].every((k) => k.querySelector("div").textContent.trim().length > 0), `${id}: no empty key fact cell`);
  ok(!/\(|\)/.test(d.querySelector("#key-facts .kfgrid").textContent), `${id}: no parentheses in key facts`);
  const groups = [...d.querySelectorAll("#results tr.grp th")].map((e) => e.textContent);
  const rank = { "Online": 0, "Offline": 1, "Reported, type not stated": 2 };
  ok(groups.every((g, i) => g in rank && (i === 0 || rank[g] > rank[groups[i - 1]])), `${id}: result groups in order, got ${groups.join(" | ")}`);
  ok(groups.length > 0 || !!d.querySelector("#results p.stage-d"), `${id}: results show a table or a note`);
  ok(d.querySelector("#results table.restab") ? d.querySelectorAll("#results table.restab tbody tr:not(.grp)").length > 0 : true, `${id}: no empty results table`);
  const head = art.querySelector("header.v2head");
  ok(!!head.querySelector("h1") && !!head.querySelector(".byline") && !!head.querySelector(".tldr") && head.querySelectorAll(".actions .btn, .actions .btn-off").length === 2, `${id}: header has name, byline, TL;DR and two buttons`);
}
ok(withDiagram.length === 3, `exactly 3 diagram cards, found ${withDiagram.length}`);
console.log(`${checks - fails}/${checks} checks passed over ${ids.length} cards, diagrams: ${withDiagram.join(", ")}`);
process.exit(fails ? 1 : 0);
