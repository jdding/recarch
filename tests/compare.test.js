// Compare page: no alert(), an inline message for the 4th system, scenario/baseline/compute/QPS rows, translated tags in zh.
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/compare.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log("FAIL", m); } else console.log("ok  ", m); };
const js = fs.readFileSync(dist + "/static/compare.js", "utf8");
ok(!/\balert\s*\(/.test(js) && !/\bconfirm\s*\(/.test(js), "compare.js has no alert or confirm");
ok(!/alert\s*\(/.test(fs.readFileSync(dist + "/static/app.js", "utf8")), "app.js has no alert");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function run(lang) {
  const file = lang === "zh" ? "compare/index.html" : "en/compare/index.html", base = lang === "zh" ? "https://t.test/recarch/compare/" : "https://t.test/recarch/en/compare/";
  const all = JSON.parse(fs.readFileSync(dist + "/data/systems.json", "utf8"));
  const ids = all.slice(0, 5).map((c) => c.id);
  const dom = new JSDOM(fs.readFileSync(dist + "/" + file, "utf8"), { url: base + "?ids=" + ids.slice(0, 3).join(","), runScripts: "dangerously" });
  const w = dom.window; w.fetch = () => Promise.resolve({ json: () => Promise.resolve(all) }); w.eval(js); await wait(80);
  const d = w.document, msg = d.getElementById("cmpmsg"), sel = d.getElementById("add");
  ok(!!sel && d.querySelectorAll("table.cmp thead th[scope=col]").length === 3, `${lang}: three systems rendered`);
  ok(msg.hidden === true && (msg.getAttribute("role") === "status" || !!msg.getAttribute("aria-live")), `${lang}: message region is a hidden live region at first`);
  const labels = [...d.querySelectorAll("table.cmp th[scope=row]")].map((t) => t.textContent);
  const want = lang === "zh" ? ["场景", "对比基线", "训练算力", "服务吞吐"] : ["Scenario", "Compared with", "Training compute", "Serving throughput"];
  for (const l of want) ok(labels.includes(l), `${lang}: row "${l}" present (${labels.length} rows)`);
  const before = w.location.search; sel.value = ids[3]; sel.dispatchEvent(new w.Event("change"));
  ok(w.location.search === before, `${lang}: 4th system does not navigate`);
  ok(msg.hidden === false && msg.textContent.length > 10, `${lang}: inline message shown: ${msg.textContent}`);
  ok(lang === "zh" ? /[\u4e00-\u9fff]/.test(msg.textContent) : /up to 3/.test(msg.textContent), `${lang}: message is in the page language`);
  ok(sel.value === "", `${lang}: the select is reset`);
  const table = d.querySelector("table.cmp").textContent;
  if (lang === "zh") { const tags = [...d.querySelectorAll("table.cmp .tag")].map((t) => t.textContent); ok(tags.length > 0 && tags.every((t) => /[\u4e00-\u9fff]/.test(t) || /^[A-Z0-9 +\-\/]+$/.test(t)), `zh: paradigm tags translated: ${tags.slice(0, 4)}`); }
  ok(d.querySelectorAll("table.cmp th[scope=row]").length >= 24, `${lang}: row headers carry scope=row`);
}
(async () => { await run("zh"); await run("en"); console.log(fails ? `FAILED ${fails}` : "COMPARE: ALL PASS"); process.exit(fails ? 1 : 0); })();
