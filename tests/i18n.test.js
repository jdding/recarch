// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/i18n.test.js [dist]
// Bilingual site: zh at the root, en under /en/. Checks twins, toggles, hreflang/canonical/lang, sitemap, 404, broken links,
// untranslated UI strings in zh pages, and the client scripts running with zh labels.
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = path.resolve(process.argv[2] || path.join(__dirname, "../dist"));
const SITE = (process.env.SITE_URL || "https://recarch.example").replace(/\/+$/, ""), BASE = new URL(SITE + "/").pathname.replace(/\/$/, "");
let fails = 0, checks = 0; const ok = (c, m) => { checks++; if (!c) { fails++; if (fails < 60) console.log("FAIL", m); } };
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => { const p = path.join(d, e.name); return e.isDirectory() ? walk(p) : [p]; });
const htmlOf = (lang) => walk(lang === "en" ? path.join(dist, "en") : dist).filter((f) => f.endsWith(".html") && (lang === "en" || !path.relative(dist, f).startsWith("en" + path.sep)));
const rel = (f) => path.relative(dist, f).split(path.sep).join("/");
const zhPages = htmlOf("zh"), enPages = htmlOf("en");
ok(zhPages.length > 80 && enPages.length > 80, `pages: zh ${zhPages.length}, en ${enPages.length}`);
const zhSet = new Set(zhPages.map(rel)), enSet = new Set(enPages.map((f) => rel(f).slice(3)));
for (const r of zhSet) ok(enSet.has(r), `zh page ${r} has an en twin`);
for (const r of enSet) ok(zhSet.has(r), `en page en/${r} has a zh twin`);
const urlPath = (r) => BASE + "/" + r.replace(/(^|\/)index\.html$/, "$1");
const parse = (f) => new JSDOM(fs.readFileSync(f, "utf8")).window.document;
const toFile = (p) => { // site path (with base) -> file in dist, or null
  p = decodeURIComponent(p); if (!p.startsWith(BASE + "/") && p !== BASE) return null; p = p.slice(BASE.length);
  let f = path.join(dist, p); if (p.endsWith("/") || p === "") f = path.join(f, "index.html"); return fs.existsSync(f) && fs.statSync(f).isFile() ? f : (fs.existsSync(path.join(f, "index.html")) ? path.join(f, "index.html") : null);
};
const idsCache = {}; const idsOf = (f) => idsCache[f] || (idsCache[f] = new Set([...parse(f).querySelectorAll("[id]")].map((e) => e.id)));
// UI strings: key || en || zh
const ui = fs.readFileSync(path.join(__dirname, "../data/i18n/ui.txt"), "utf8").split("\n").filter((l) => l.trim() && !l.startsWith("#")).map((l) => l.split(" || "));
const uiUntranslated = ui.filter(([k, en, zh]) => en && zh && en.trim() !== zh.trim() && !/\{/.test(en) && !k.startsWith("js.") && /[a-z]{3,}/.test(en) && en.length >= 6 && !/\bhref=/.test(en)).map(([k, en]) => [k, en.trim()]);
let broken = 0, togglesChecked = 0, redirects = 0;
const stripNon = (doc) => { doc.querySelectorAll("script,style,code,pre,[lang=en],.nl-embed").forEach((e) => e.remove()); return doc.body.textContent; };
for (const [lang, pages] of [["zh", zhPages], ["en", enPages]]) {
  for (const f of pages) {
    const r = rel(f), twin = lang === "zh" ? "en/" + r : r.slice(3), is404 = /(^|\/)404\.html$/.test(r);
    const d = parse(f), html = d.documentElement, url = SITE + urlPath(r).slice(BASE.length), tw = SITE + urlPath(twin).slice(BASE.length);
    ok(html.getAttribute("lang") === (lang === "zh" ? "zh-CN" : "en"), `${r}: html lang`);
    const refresh = d.querySelector('meta[http-equiv=refresh]');
    if (refresh) { // redirect stub of a merged card: same-language canonical, existing target, noindex
      const tgt = refresh.content.split("url=")[1], tf = toFile(new URL(tgt, "http://x" + urlPath(r)).pathname);
      ok(!!tf && (rel(tf).startsWith("en/") === (lang === "en")), `${r}: redirect target ${tgt} exists in ${lang}`);
      const cn = d.querySelector("link[rel=canonical]"); ok(cn && cn.href === SITE + urlPath(tf ? rel(tf) : "").slice(BASE.length), `${r}: redirect canonical is the target in ${lang}`);
      ok(!!d.querySelector('meta[name=robots][content*=noindex]'), `${r}: redirect is noindex`); redirects++; continue;
    }
    ok(!!d.querySelector("title") && d.querySelector("title").textContent.trim().length > 0, `${r}: title`);
    const canon = d.querySelector('link[rel=canonical]'); ok(canon && canon.href === url, `${r}: canonical ${canon && canon.href} vs ${url}`);
    const alt = {}; d.querySelectorAll("link[rel=alternate][hreflang]").forEach((a) => (alt[a.getAttribute("hreflang")] = a.getAttribute("href")));
    const zhU = lang === "zh" ? url : tw, enU = lang === "zh" ? tw : url;
    ok(alt["zh-CN"] === zhU && alt.en === enU && alt["x-default"] === zhU, `${r}: hreflang alternates ${JSON.stringify(alt)}`);
    ok(!is404 || !!d.querySelector('meta[name=robots][content*=noindex]'), `${r}: 404 is noindex`);
    // toggle
    const sw = [...d.querySelectorAll(".langsw a")]; ok(sw.length === 1, `${r}: one language toggle link`);
    for (const a of sw) {
      ok(a.getAttribute("hreflang") === (lang === "zh" ? "en" : "zh-CN"), `${r}: toggle hreflang`);
      const target = new URL(a.getAttribute("href"), "http://x" + urlPath(r) + (is404 ? "" : "")).pathname; togglesChecked++;
      const tf = toFile(target); ok(tf === path.join(dist, twin) || (tf && rel(tf) === twin), `${r}: toggle -> ${target} resolves to ${twin}, got ${tf && rel(tf)}`);
    }
    ok(d.querySelectorAll(".langsw .on").length === 1, `${r}: current language marked`);
    // links
    const here = "http://x" + urlPath(r);
    for (const el of d.querySelectorAll("a[href],link[href],script[src],img[src]")) {
      const v = el.getAttribute("href") || el.getAttribute("src"); if (!v || /^(https?:|mailto:|data:|javascript:|\/\/)/.test(v)) continue;
      let u; try { u = new URL(v, here); } catch (e) { ok(false, `${r}: bad url ${v}`); continue; }
      if (u.pathname.endsWith("feed.xml") || u.pathname.endsWith("/")) { /* fall through, still resolved below */ }
      const tf = toFile(u.pathname); if (!tf) { broken++; ok(false, `${r}: broken link ${v}`); continue; }
      if (u.hash.length > 1 && tf.endsWith(".html")) { const id = decodeURIComponent(u.hash.slice(1)); if (!idsOf(tf).has(id)) { broken++; ok(false, `${r}: missing anchor ${v}`); } }
      // links stay in the same language
      if (el.tagName === "A" && !el.closest(".langsw") && tf.endsWith(".html")) {
        const inEn = rel(tf).startsWith("en/"); ok(inEn === (lang === "en") || is404, `${r}: link ${v} leaves the ${lang} site`);
      }
    }
    // untranslated UI in zh
    if (lang === "zh" && !is404) { const dz = parse(f); const seen = new Set(uiUntranslated.map(([k, en]) => en));
      for (const e of dz.querySelectorAll("header.site a, header.site button, footer a, nav a, th, button, label, .chip, .crumbs a, .btn, h2, h3, option, summary")) { if (e.closest("[lang=en]") || e.closest(".nl-embed")) continue; const t = e.textContent.trim(); ok(!seen.has(t), `${r}: untranslated UI string in <${e.tagName.toLowerCase()}>: "${t}"`); }
      ok(!/Not reported/.test(stripNon(parse(f))), `${r}: "Not reported" in zh page`); }
    if (lang === "en") { const txt = parse(f).body.textContent; ok(!/[\u4e00-\u9fff]/.test(txt.replace(/中文/g, "")) || is404 || /\/(about|newsletter)\//.test("/" + r), `${r}: Chinese text in an en page`); }
  }
}
// en pages have no CJK except the 中文 toggle (strict form)
for (const f of enPages) { const d = parse(f); d.querySelectorAll(".langsw,script,style").forEach((e) => e.remove()); ok(!/[\u4e00-\u9fff]/.test(d.body.textContent), `${rel(f)}: contains Chinese characters`); }
// 404: bilingual at the root, English under /en/, base path on assets
{ const z = fs.readFileSync(path.join(dist, "404.html"), "utf8"), e = fs.readFileSync(path.join(dist, "en/404.html"), "utf8");
  ok(z.includes(`href="${BASE}/static/style.css"`) && e.includes(`href="${BASE}/static/style.css"`), "404 pages use the base path for assets");
  ok(z.includes(`href="${BASE}/"`) && z.includes(`href="${BASE}/en/"`), "root 404 links home in both languages");
  ok(e.includes(`href="${BASE}/en/"`) && e.includes(`href="${BASE}/404.html"`), "en 404 links to /en/ and toggles to the root 404");
  ok(/lang="en"/.test(z) && /页面未找到/.test(z) && /Not found/.test(z), "root 404 shows both languages");
  ok(/Not found/.test(e) && !/页面未找到/.test(e.replace(/<span class="langsw".*?<\/span>/, "")), "en 404 is English"); }
// sitemap
{ const sm = fs.readFileSync(path.join(dist, "sitemap.xml"), "utf8"); const urls = [...sm.matchAll(/<url><loc>([^<]+)<\/loc>(.*?)<\/url>/g)];
  const isRedirect = (r) => /name="robots" content="noindex"/.test(fs.readFileSync(path.join(dist, r), "utf8")); const nRed = [...zhSet].filter(isRedirect).length;
  const locs = new Set(urls.map((m) => m[1])); ok(urls.length === 2 * (zhSet.size - nRed), `sitemap lists every indexable page (not 404, retired, redirect stubs) in both languages: ${urls.length}`);
  for (const r of zhSet) { if (/404\.html$/.test(r) || isRedirect(r)) continue; const zu = SITE + urlPath(r).slice(BASE.length), eu = SITE + urlPath("en/" + r).slice(BASE.length);
    ok(locs.has(zu) && locs.has(eu), `sitemap has both languages of ${r}`);
    const m = urls.find((x) => x[1] === zu); ok(m && m[2].includes(`hreflang="zh-CN" href="${zu}"`) && m[2].includes(`hreflang="en" href="${eu}"`) && m[2].includes(`hreflang="x-default" href="${zu}"`), `sitemap alternates for ${r}`); }
  ok(!/404/.test(sm), "sitemap omits 404");
  const rb = fs.readFileSync(path.join(dist, "robots.txt"), "utf8"); ok(rb.includes(SITE + "/sitemap.xml"), "robots.txt points at the sitemap"); }
// per-language data and feeds
for (const l of ["", "en/"]) { ok(fs.existsSync(path.join(dist, l + "feed.xml")) && fs.existsSync(path.join(dist, l + "data/systems.json")), `${l || "zh/"} feed and data exist`); }
{ const zj = JSON.parse(fs.readFileSync(path.join(dist, "data/systems.json"), "utf8")), ej = JSON.parse(fs.readFileSync(path.join(dist, "en/data/systems.json"), "utf8"));
  ok(zj.length === ej.length && zj.length > 50, `systems.json same length in both languages: ${zj.length}`);
  ok(zj.every((c, i) => c.id === ej[i].id), "systems.json same order");
  ok(zj.some((c) => /[\u4e00-\u9fff]/.test(c.deployment.scenario)), "zh systems.json has Chinese text"); }
// client scripts in zh
const L10N = (f) => { const m = fs.readFileSync(f, "utf8").match(/<script>(window\.RECARCH_L10N=.*?)<\/script>/); return m && m[1]; };
const js = (n) => fs.readFileSync(path.join(dist, "static", n), "utf8");
(async () => {
  for (const [lang, base] of [["zh", dist], ["en", path.join(dist, "en")]]) {
    const html = fs.readFileSync(path.join(base, "index.html"), "utf8");
    const dom = new JSDOM(html, { runScripts: "outside-only", url: SITE + (lang === "en" ? "/en/" : "/") }); const w = dom.window; w.alert = () => {};
    w.eval(L10N(path.join(base, "index.html"))); w.eval(js("app.js")); const D = w.document;
    const cnt = D.getElementById("count").textContent; const n = D.querySelectorAll("#grid .card").length;
    ok(lang === "zh" ? new RegExp(`^${n} 个系统`).test(cnt) : new RegExp(`^${n} systems`).test(cnt), `${lang}: app.js count label "${cnt}"`);
    const q = D.getElementById("q"); q.value = "tiger"; q.dispatchEvent(new w.Event("input", { bubbles: true }));
    const c2 = D.getElementById("count").textContent; ok(lang === "zh" ? /^\d+ \/ \d+ 个系统/.test(c2) : /^\d+ of \d+ systems/.test(c2), `${lang}: filtered count "${c2}"`);
    const links = [...D.querySelectorAll("#grid .card a[href]")].map((a) => a.getAttribute("href")).filter((h) => /systems\//.test(h)); ok(links.length > 0 && links.every((h) => !h.startsWith("/") && !h.includes("/en/")), `${lang}: card links stay relative to this language root`);
    // compare
    const cf = path.join(base, "compare/index.html"), chtml = fs.readFileSync(cf, "utf8");
    const cd = JSON.parse(fs.readFileSync(path.join(base, "data/systems.json"), "utf8")); const a = cd[0].id, b = cd[1].id;
    const cdom = new JSDOM(chtml, { runScripts: "outside-only", url: `${SITE}${lang === "en" ? "/en" : ""}/compare/?ids=${a},${b}` }); const cw = cdom.window;
    cw.fetch = () => Promise.resolve({ json: () => Promise.resolve(cd) }); cw.RECARCH_ROOT = "../"; cw.eval(L10N(cf)); cw.eval(js("compare.js"));
    await new Promise((r) => setTimeout(r, 300));
    const th = [...cw.document.querySelectorAll("#out th, #out td:first-child")].map((e) => e.textContent).join("|");
    ok(lang === "zh" ? /线上收益/.test(th) && /A\/B 流量/.test(th) && !/Online lifts/.test(th) : /Online lifts/.test(th) && /A\/B traffic/.test(th), `${lang}: compare rows localized`);
    const hrefs = [...cw.document.querySelectorAll("#out a[href]")].map((x) => x.getAttribute("href")); ok(hrefs.length > 0 && hrefs.every((h) => !h.startsWith("/") && !h.includes("/en/") ), `${lang}: compare links relative to this language root`);
    ok(!/undefined|\{n\}|\{y\}/.test(cw.document.getElementById("out").textContent), `${lang}: compare has no unfilled placeholders`);
  }
  console.log(`${checks - fails}/${checks} checks passed, ${zhPages.length} zh pages, ${enPages.length} en pages, ${togglesChecked} toggles resolved, ${redirects} redirect stubs, ${broken} broken links`);
  process.exit(fails ? 1 : 0);
})();
