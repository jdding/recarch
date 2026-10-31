// Share and icon metadata on every page: og:image/url/type, twitter:card, per-language og:locale, favicons, a real 1200x630 PNG.
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/meta.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist");
let fails = 0, n = 0; const ok = (c, m) => { n++; if (!c) { fails++; console.log("FAIL", m); } };
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(d + "/" + e.name) : [d + "/" + e.name]);
const pages = walk(dist).filter((f) => f.endsWith(".html")), rel = (f) => path.relative(dist, f);
const png = (f) => { const b = fs.readFileSync(f); return { sig: b.subarray(0, 8).toString("hex"), w: b.readUInt32BE(16), h: b.readUInt32BE(20), size: b.length }; };
for (const f of ["og-default.png", "og-default-zh.png"]) { const p = png(`${dist}/static/${f}`); ok(p.sig === "89504e470d0a1a0a" && p.w === 1200 && p.h === 630, `${f} is a 1200x630 PNG`); ok(p.size < 300000, `${f} is under 300 KB (${p.size})`); }
const fav = png(`${dist}/static/favicon.png`); ok(fav.w >= 32 && fav.w === fav.h, "favicon.png is square"); const ap = png(`${dist}/static/apple-touch-icon.png`); ok(ap.w === 180 && ap.h === 180, "apple-touch-icon is 180x180");
const ico = fs.readFileSync(`${dist}/static/favicon.ico`); ok(ico.readUInt16LE(0) === 0 && ico.readUInt16LE(2) === 1 && ico.readUInt16LE(4) >= 1, "favicon.ico has an icon header");
ok(/<svg/.test(fs.readFileSync(`${dist}/static/favicon.svg`, "utf8")), "favicon.svg exists");
let checked = 0;
for (const f of pages) {
  const raw = fs.readFileSync(f, "utf8"); if (/http-equiv="refresh"/.test(raw)) continue; checked++;
  const d = new JSDOM(raw).window.document, m = (k) => (d.querySelector(`meta[property="${k}"],meta[name="${k}"]`) || {}).content, en = rel(f).startsWith("en/") || rel(f) === "en";
  const name = rel(f);
  ok(m("og:type") === "website", `${name}: og:type`);
  ok(/^https?:\/\/[^/]+(\/[^/]+)*\/(static\/og-default(-zh)?\.png)$/.test(m("og:image") || ""), `${name}: og:image is an absolute default image: ${m("og:image")}`);
  ok(m("og:image") === m("twitter:image") && m("twitter:card") === "summary_large_image", `${name}: twitter:card is summary_large_image with the same image`);
  ok(m("og:image:width") === "1200" && m("og:image:height") === "630" && !!m("og:image:alt"), `${name}: image size and alt`);
  ok(/^https?:\/\//.test(m("og:url") || "") && m("og:url") === (d.querySelector("link[rel=canonical]") || {}).href, `${name}: og:url equals the canonical URL`);
  ok(m("og:locale") === (en ? "en_US" : "zh_CN"), `${name}: og:locale ${m("og:locale")}`);
  ok(m("og:image").endsWith(en ? "og-default.png" : "og-default-zh.png"), `${name}: the image matches the language`);
  ok((d.querySelector("meta[property='og:locale:alternate']") || {}).content === (en ? "zh_CN" : "en_US"), `${name}: og:locale:alternate`);
  ok(!!m("og:title") && !!m("og:description") && !!m("twitter:title"), `${name}: title and description`);
  ok(m("og:description").length <= 200 && (m("og:description").length < 100 || /[…。.]$/.test(m("og:description"))), `${name}: description is short and ends cleanly`);
  for (const sel of ["link[rel=icon][type='image/svg+xml']", "link[rel=icon][type='image/png']", "link[rel='shortcut icon']", "link[rel=apple-touch-icon]"]) ok(!!d.querySelector(sel), `${name}: ${sel}`);
  for (const a of d.querySelectorAll("link[rel*=icon]")) { const h = a.getAttribute("href"); const t = h.startsWith("/") ? dist + h.replace(/^\/[^/]+(?=\/static)/, "") : path.join(path.dirname(f), h); ok(fs.existsSync(t.replace(/\?.*/, "")), `${name}: icon file exists ${h}`); }
}
ok(checked >= 150, `${checked} pages checked`);
console.log(fails ? `FAILED ${fails} of ${n}` : `META: ${n} checks passed`); process.exit(fails ? 1 : 0);
