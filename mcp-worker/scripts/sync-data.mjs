// Copy the published cards.json of both languages from the site build into the Worker bundle.
// Only the published file is read. It never contains source documents, and unreviewed FAQ is absent from it.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const dist = process.env.RECARCH_DIST || path.join(here, "../../dist");
const out = path.join(here, "../data");
fs.mkdirSync(out, { recursive: true });
for (const [lang, rel] of [["zh", "cards.json"], ["en", "en/cards.json"]]) {
  const src = path.join(dist, rel);
  if (!fs.existsSync(src)) { console.error(`missing ${src}, run python3 build.py first`); process.exit(1); }
  const j = JSON.parse(fs.readFileSync(src, "utf8"));
  if (j.schema_version !== "1.0") { console.error(`unexpected schema_version ${j.schema_version}`); process.exit(1); }
  fs.writeFileSync(path.join(out, `cards.${lang}.json`), JSON.stringify(j));
  console.log(`cards.${lang}.json: ${j.count} cards, generated ${j.generated}`);
}
