// End-to-end check with the official MCP SDK client against a running Worker (wrangler dev).
//   node test/client.mjs [http://localhost:8787/mcp]
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
const url = process.argv[2] || "http://localhost:8787/mcp";
let fails = 0; const ok = (c, m) => { console.log(c ? "ok  " : "FAIL", m); if (!c) fails++; };
const client = new Client({ name: "recarch-test", version: "0.0.1" });
await client.connect(new StreamableHTTPClientTransport(new URL(url)));
const tools = (await client.listTools()).tools.map((t) => t.name).sort();
ok(JSON.stringify(tools) === JSON.stringify(["compare_topic", "get_card", "search_cards"]), `tools/list -> ${tools.join(", ")}`);
const readOnly = (await client.listTools()).tools.every((t) => t.annotations?.readOnlyHint === true);
ok(readOnly, "all tools are annotated readOnlyHint");
const call = async (name, args) => { const r = await client.callTool({ name, arguments: args }); return { r, j: r.isError ? null : JSON.parse(r.content[0].text), t: r.content[0].text }; };

let { j } = await call("search_cards", { query: "Airbnb search ranking embeddings", lang: "en", limit: 3 });
console.log("  search_cards en ->", j.results.map((x) => x.id).join(", "));
ok(j.count > 0 && j.results[0].id.startsWith("airbnb"), "search_cards finds an Airbnb card first for an Airbnb query");
const id = j.results[0].id;
({ j } = await call("search_cards", { query: "生成式召回 美团", lang: "zh", limit: 3 }));
console.log("  search_cards zh ->", j.results.map((x) => x.id).join(", "));
ok(j.count > 0, "search_cards zh returns results for a Chinese query");
({ j } = await call("search_cards", { query: "zzqxjv nonexistent thing", lang: "en" }));
ok(j.count === 0 && Array.isArray(j.results), "search_cards returns an empty list, not an error, for no match");

({ j } = await call("get_card", { id, lang: "en" }));
ok(j.card.id === id && Array.isArray(j.card.facts) && j.card.facts.every((f) => f.source), `get_card ${id}: facts all carry a source path`);
ok(!/zotero/i.test(JSON.stringify(j)) && !("fulltext" in j.card), "get_card has no fulltext field and no zotero path");
const zh = (await call("get_card", { id, lang: "zh" })).j;
ok(/[\u4e00-\u9fff]/.test(zh.card.tldr), "get_card zh returns the Chinese card");
const bad = await call("get_card", { id: "no-such-card-1999", lang: "en" });
ok(bad.r.isError === true, "get_card unknown id -> isError with a hint");
const inj = await client.callTool({ name: "get_card", arguments: { id: "../../etc/passwd", lang: "en" } }).then((r) => r, (e) => ({ isError: true, e: String(e) }));
ok(inj.isError === true, "get_card rejects a path-traversal id");

({ j } = await call("compare_topic", {}));
const slug = j.topics[0].slug; console.log("  topics ->", j.topics.map((t) => t.slug).join(", "));
ok(j.topics.length >= 1, "compare_topic with no arguments lists topics");
({ j } = await call("compare_topic", { topic: slug, lang: "en" }));
ok(j.cards.length >= 3 && j.cards.every((c) => c.id && c.url), `compare_topic ${slug}: ${j.cards.length} cards in the table`);
({ j } = await call("compare_topic", { ids: [id, j.cards[0].id], lang: "en" }));
ok(j.cards.length === 2 && j.topic === null, "compare_topic by two card ids");
const nt = await call("compare_topic", { topic: "no-such-topic" });
ok(nt.r.isError === true, "compare_topic unknown topic -> isError");
await client.close();
if (process.env.STATS_URL) {
  const s = await (await fetch(process.env.STATS_URL)).json(); console.log("  /_stats ->", JSON.stringify(s));
  ok(s.zero_result_queries.some((z) => z.query.includes("zzqxjv")), "zero-result query is logged");
  ok(Object.values(s.sessions_per_day).every((n) => n >= 1), "anonymous session count is recorded");
}
console.log(fails ? `${fails} FAILED` : "all passed"); process.exit(fails ? 1 : 0);
