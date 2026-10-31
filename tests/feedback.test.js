// Feedback through GitHub Issues only: prefilled links on every card and in every footer, bilingual issue templates, no e-mail address anywhere.
// Run after `python3 build.py`: NODE_PATH=/tmp/jt/node_modules node tests/feedback.test.js [dist]
const { JSDOM } = require("jsdom"); const fs = require("fs"); const path = require("path");
const dist = process.argv[2] || path.join(__dirname, "../dist"), repoRoot = path.join(__dirname, "..");
let fails = 0, n = 0; const ok = (c, m) => { n++; if (!c) { fails++; console.log("FAIL", m); } };
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(d + "/" + e.name) : [d + "/" + e.name]);
const files = walk(dist), html = files.filter((f) => f.endsWith(".html"));
const REPO = "https://github.com/jdding/recarch/issues/new?";
const doc = (f) => new JSDOM(fs.readFileSync(f, "utf8")).window.document;
const issueLinks = (d) => [...d.querySelectorAll("a[href^='" + REPO + "']")].map((a) => new URL(a.href));
// templates
const tdir = path.join(repoRoot, ".github/ISSUE_TEMPLATE");
const tpl = {}; for (const f of ["error-report.md", "system-request.md"]) { ok(fs.existsSync(path.join(tdir, f)), `template ${f} exists`); tpl[f] = fs.existsSync(path.join(tdir, f)) ? fs.readFileSync(path.join(tdir, f), "utf8") : ""; }
ok(fs.existsSync(path.join(tdir, "config.yml")), "ISSUE_TEMPLATE/config.yml exists");
for (const [f, t] of Object.entries(tpl)) {
  ok(/^---\nname: .+\nabout: .+\ntitle: ".+"\nlabels: .+\n---\n/.test(t), `${f}: front matter name/about/title/labels`);
  const heads = t.match(/^### .+$/gm) || []; ok(heads.length >= 3, `${f}: has section headings`);
  ok(heads.every((h) => /[\u4e00-\u9fff]/.test(h) && /[A-Za-z]/.test(h)), `${f}: every heading is bilingual`);
  ok(!/[\w.+-]+@[\w-]+\.\w+/.test(t) && !/mailto:/.test(t), `${f}: no e-mail address`);
}
// card pages: links with the card id in the title and the template headings in the body, in both languages
let cards = 0;
for (const lang of ["", "en/"]) {
  for (const id of fs.readdirSync(`${dist}/${lang}systems`)) {
    const f = `${dist}/${lang}systems/${id}/index.html`; if (!fs.existsSync(f) || /http-equiv="refresh"/.test(fs.readFileSync(f, "utf8"))) continue;
    cards++; const d = doc(f), L = issueLinks(d.querySelector("#history") || d.body);
    const err = L.find((u) => u.searchParams.get("title").startsWith("[Error 纠错] ")), req = L.find((u) => u.searchParams.get("title").startsWith("[Request 收录]"));
    ok(!!err && err.searchParams.get("title") === "[Error 纠错] " + id, `${lang}${id}: error link title carries the card id`);
    ok(!!err && err.searchParams.get("body").includes("**Card 卡片**: " + id) && err.searchParams.get("body").includes("/systems/" + id + "/"), `${lang}${id}: error body names the card and its page`);
    ok(!!err && (tpl["error-report.md"].match(/^### .+$/gm) || []).every((h) => err.searchParams.get("body").includes(h)), `${lang}${id}: error body has every template heading`);
    ok(!!req && (tpl["system-request.md"].match(/^### .+$/gm) || []).every((h) => req.searchParams.get("body").includes(h)), `${lang}${id}: request body has every template heading`);
    ok(!d.body.textContent.includes("Spotted an error? Email") && !/placeholder/i.test(d.querySelector("#history").textContent), `${lang}${id}: old placeholder text is gone`);
    ok(d.querySelector("#history .fb-line a[target=_blank][rel~=noopener]"), `${lang}${id}: links open safely`);
  }
}
ok(cards >= 70 * 2, `checked ${cards} card pages`);
// footer on every page, about page section
for (const f of html) { const d = doc(f); if (/http-equiv="refresh"/.test(d.head.innerHTML)) continue; ok(issueLinks(d.querySelector("footer.site")).length === 2, `${path.relative(dist, f)}: footer has both feedback links`); }
for (const f of ["about/index.html", "en/about/index.html"]) { const d = doc(`${dist}/${f}`), a = d.querySelector("#feedback");
  ok(!!a && issueLinks(a).length === 2, `${f}: about page feedback section with both links`); }
const zhAbout = doc(`${dist}/about/index.html`).querySelector("#feedback").textContent, enAbout = doc(`${dist}/en/about/index.html`).querySelector("#feedback").textContent;
ok(/纠错/.test(zhAbout) && /申请收录/.test(zhAbout), "zh about uses 纠错 and 申请收录"); ok(/Report an error/.test(enAbout) && /Request a system/.test(enAbout), "en about uses Report an error and Request a system");
// no e-mail address in any published file
for (const f of files.filter((x) => /\.(html|json|xml|js|txt)$/.test(x))) { const t = fs.readFileSync(f, "utf8"); ok(!/mailto:/i.test(t), `${path.relative(dist, f)}: no mailto`); }
const emails = []; for (const f of html) for (const m of fs.readFileSync(f, "utf8").replace(/<script[\s\S]*?<\/script>/g, "").matchAll(/[\w.+-]+@[\w-]+\.[A-Za-z]{2,}/g)) emails.push(m[0]); ok(emails.length === 0, "no e-mail address in page text: " + emails.slice(0, 3));
console.log(fails ? `FAILED ${fails} of ${n}` : `FEEDBACK: ${n} checks passed`); process.exit(fails ? 1 : 0);
