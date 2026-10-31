// Run: python3 tests/carousel_fixture.py /tmp/car-fixtures && NODE_PATH=/tmp/jt/node_modules node tests/carousel.test.js /tmp/car-fixtures /path/to/dist/static
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dir = process.argv[2] || "/tmp/car-fixtures", st = process.argv[3] || path.join(__dirname, "../dist/static");
const meta = JSON.parse(fs.readFileSync(dir + "/meta.json")), js = fs.readFileSync(st + "/carousel.js", "utf8");
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log("FAIL", m); } else console.log("ok  ", m); };
function load(name, reduced) {
  const html = fs.readFileSync(dir + `/${name}.html`, "utf8").replace(/<script[^>]*><\/script>/, "").replace(/<link[^>]*>/, "");
  const dom = new JSDOM(html, { runScripts: "outside-only", pretendToBeVisual: true }); const w = dom.window; const timers = [];
  w.setInterval = (f, d) => { timers.push({ f, d, on: true }); return timers.length; }; w.clearInterval = (id) => { if (timers[id - 1]) timers[id - 1].on = false; };
  if (reduced !== undefined) w.matchMedia = (q) => ({ matches: reduced && /reduce/.test(q) });
  w.eval(js); return { w, d: w.document, timers, live: () => timers.filter((t) => t.on) };
}
const cur = (d) => [...d.querySelectorAll(".dot")].findIndex((x) => x.getAttribute("aria-current") === "true");
const ev = (w, el, type, props) => { const e = new w.Event(type, { bubbles: true }); Object.assign(e, props || {}); el.dispatchEvent(e); };
for (const name of ["recent0", "recent3", "recent10", "few4"]) {
  const m = meta[name], { w, d, live } = load(name, false), n = m.ids.length;
  const slides = [...d.querySelectorAll(".slide")];
  ok(slides.length === n && n === (name === "few4" ? 4 : 6), `${name}: ${n} slides`);
  ok(JSON.stringify(slides.map((s) => s.dataset.id)) === JSON.stringify(m.ids), `${name}: order ${m.ids.join(",")}`);
  ok(d.querySelectorAll(".dot").length === n, `${name}: ${n} dots`);
  ok(live().length === 1 && live()[0].d === 5000, `${name}: autoplay every 5000ms`);
  ok(slides.every((s) => s.querySelector(".era-badge") && s.querySelector(".k") && s.querySelector("time") && s.querySelector("a[href$='/']") && s.querySelector(".slide-tldr")), `${name}: slide has era/kind/date/tldr/link`);
  ok(JSON.stringify([...d.querySelectorAll(".slide .k")].map((k) => k.textContent.toLowerCase())) === JSON.stringify(m.kinds), `${name}: Added/Updated badges`);
  ok([...d.querySelectorAll(".slide")].every((s, i) => (s.querySelector(".slide-note") != null) === (m.kinds[i] === "updated")), `${name}: update note only on Updated slides`);
  ok(d.querySelector(".pill") && d.querySelector("a[href='changelog/']"), `${name}: week badge + changelog link`);
}
{ // behaviour on 6 slides
  const { w, d, live } = load("recent3", false), car = d.querySelector(".carousel"), t = live()[0];
  ok(cur(d) === 0, "starts on slide 1"); t.f(); ok(cur(d) === 1, "tick advances");
  ev(w, car, "mouseenter"); t.f(); ok(cur(d) === 1, "paused on hover"); ev(w, car, "mouseleave"); t.f(); ok(cur(d) === 2, "resumes after hover");
  ev(w, car, "focusin"); t.f(); ok(cur(d) === 2, "paused on focus"); ev(w, car, "focusout");
  ev(w, car, "touchstart", { touches: [{ clientX: 200, clientY: 10 }] }); const cnt0 = cur(d); live().forEach((x) => x.f()); ok(cur(d) === cnt0, "paused on touch");
  ev(w, car, "touchend", { changedTouches: [{ clientX: 100, clientY: 12 }] }); ok(cur(d) === 3, "swipe left -> next");
  ev(w, car, "touchstart", { touches: [{ clientX: 100, clientY: 10 }] }); ev(w, car, "touchend", { changedTouches: [{ clientX: 220, clientY: 10 }] }); ok(cur(d) === 2, "swipe right -> prev");
  ev(w, car, "touchstart", { touches: [{ clientX: 100, clientY: 10 }] }); ev(w, car, "touchend", { changedTouches: [{ clientX: 110, clientY: 10 }] }); ok(cur(d) === 2, "tiny swipe ignored");
  d.querySelector(".car-next").click(); ok(cur(d) === 3, "next button"); d.querySelector(".car-prev").click(); d.querySelector(".car-prev").click(); d.querySelector(".car-prev").click(); d.querySelector(".car-prev").click(); ok(cur(d) === 5, "prev wraps to last");
  d.querySelector(".car-next").click(); ok(cur(d) === 0, "next wraps to first");
  d.querySelectorAll(".dot")[4].click(); ok(cur(d) === 4, "dot jumps");
  ev(w, car, "keydown", { key: "ArrowRight" }); ok(cur(d) === 5, "ArrowRight"); ev(w, car, "keydown", { key: "ArrowLeft" }); ok(cur(d) === 4, "ArrowLeft");
  ok(d.querySelector(".car-track").style.transform === "translateX(-400%)", "track translated");
  ok(d.querySelectorAll(".slide")[4].getAttribute("aria-hidden") === "false" && d.querySelectorAll(".slide")[0].getAttribute("aria-hidden") === "true", "aria-hidden on inactive slides");
  const pb = d.querySelector(".car-pause"); pb.click(); const c1 = cur(d); live().forEach((x) => x.f()); ok(cur(d) === c1, "Pause button stops autoplay"); pb.click(); live().forEach((x) => x.f()); ok(cur(d) !== c1, "Play button resumes");
}
{ const { d, live } = load("recent3", true); ok(live().length === 0, "prefers-reduced-motion: no autoplay timer"); ok(d.querySelector(".carousel").dataset.autoplaying === "false", "reduced: flagged not autoplaying"); }
{ const { d } = load("recent3", false); const t = d.querySelector(".slide time"); ok(/^(today|yesterday|\d+ days ago)$/.test(t.textContent), "relative date text: " + t.textContent); }
console.log(fails ? `FAILED ${fails}` : "CAROUSEL: ALL PASS"); process.exit(fails ? 1 : 0);
