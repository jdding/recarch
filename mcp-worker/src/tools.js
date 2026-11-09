import { z } from "zod";
import { buildIndex, search } from "./search.js";
import zh from "../data/cards.zh.json";
import en from "../data/cards.en.json";

const DATA = { zh, en };
const INDEX = {};
function idx(lang) { return (INDEX[lang] ||= buildIndex(DATA[lang].cards)); }
const byId = (lang, id) => DATA[lang].cards.find((c) => c.id === id);
export const NOTICE = {
  zh: "内容只来自 RecArch 卡片，是我们自己的解读，不含论文原文。RecArch 问答与论文作者无关，也不代表作者。未报告的数字就是未报告，不要补全。",
  en: "Content comes only from RecArch cards, our own interpretation, never text from the papers. RecArch is not affiliated with the paper authors and does not speak for them. A number marked not reported is not reported; do not fill it in.",
};
const text = (obj) => ({ content: [{ type: "text", text: typeof obj === "string" ? obj : JSON.stringify(obj, null, 1) }] });
const fail = (msg) => ({ isError: true, content: [{ type: "text", text: msg }] });
const LANG = z.enum(["zh", "en"]).default("en").describe("Language of the returned card text, zh or en");

export function register(server, ctx) {
  const ro = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };

  server.registerTool("search_cards", {
    title: "Search RecArch cards",
    description: "Keyword search over RecArch cards of industrial recommender, search and ranking systems. Returns ids, names, one-line summaries and links. An empty list means no card matches.",
    inputSchema: { query: z.string().min(1).max(200).describe("Keywords, a system name, a company or a technique"), lang: LANG, limit: z.number().int().min(1).max(10).default(5) },
    annotations: ro,
  }, async ({ query, lang, limit }) => {
    const hits = search(idx(lang), query, limit);
    await ctx.log({ event: hits.length ? "tool_result" : "zero_result", tool: "search_cards", query, results: hits.length });
    return text({ notice: NOTICE[lang], query, count: hits.length, results: hits.map(({ card: c, score }) => ({ id: c.id, name: c.name, company: c.company, year: c.year, tldr: c.tldr, url: c.url, md_url: c.md_url, score })) });
  });

  server.registerTool("get_card", {
    title: "Get one RecArch card",
    description: "Return the full card for an id from search_cards. Every number in `facts` carries its source field path, or is marked not reported.",
    inputSchema: { id: z.string().min(1).max(120).regex(/^[a-z0-9][a-z0-9-]*$/, "card ids are lowercase words joined by hyphens"), lang: LANG },
    annotations: ro,
  }, async ({ id, lang }) => {
    const c = byId(lang, id);
    await ctx.log({ event: c ? "tool_result" : "zero_result", tool: "get_card", query: id, results: c ? 1 : 0 });
    if (!c) return fail(`No card with id ${id}. Use search_cards to find an id.`);
    return text({ notice: NOTICE[lang], card: c });
  });

  server.registerTool("compare_topic", {
    title: "Compare cards of a topic",
    description: "Side-by-side of reported fields for the members of a topic slug, or for two to five card ids. Differences in baseline, traffic and metric are listed per card; it does not rank. Call with neither argument to list topics.",
    inputSchema: { topic: z.string().max(120).optional().describe("Topic slug from the topic list"), ids: z.array(z.string().max(120)).min(2).max(5).optional(), lang: LANG },
    annotations: ro,
  }, async ({ topic, ids, lang }) => {
    const d = DATA[lang];
    if (!topic && !ids) {
      await ctx.log({ event: "tool_result", tool: "compare_topic", query: "", results: d.topics.length });
      return text({ notice: NOTICE[lang], topics: d.topics.map((t) => ({ slug: t.slug, title: t.title, summary: t.summary, url: t.url, members: t.members.map((m) => m.id) })) });
    }
    let t = null, list = ids;
    if (topic) {
      t = d.topics.find((x) => x.slug === topic);
      if (!t) { await ctx.log({ event: "zero_result", tool: "compare_topic", query: topic, results: 0 }); return fail(`No topic ${topic}. Available: ${d.topics.map((x) => x.slug).join(", ")}`); }
      list = t.members.map((m) => m.id);
    }
    const cards = list.map((i) => byId(lang, i)); const missing = list.filter((_, k) => !cards[k]);
    if (missing.length) { await ctx.log({ event: "zero_result", tool: "compare_topic", query: missing.join(","), results: 0 }); return fail(`Unknown card ids: ${missing.join(", ")}`); }
    await ctx.log({ event: "tool_result", tool: "compare_topic", query: topic || list.join(","), results: cards.length });
    const row = (c) => ({
      id: c.id, name: c.name, company: c.company, year: c.year, url: c.url, approach: t?.members.find((m) => m.id === c.id)?.approach, evidence: c.evidence_label, key_result: c.key_result, scale_short: c.scale_short,
      baseline: c.deployment?.baseline, ab_duration: c.deployment?.ab_duration, ab_traffic: c.deployment?.ab_traffic, results_online: c.results_table?.online, caveats: c.caveats,
    });
    return text({ notice: NOTICE[lang], note: lang === "zh" ? "各卡片的基线、流量、时长和指标不同，不能直接按单个数字排名。" : "Baselines, traffic, durations and metrics differ per card; do not rank on a single number.", topic: t && { slug: t.slug, title: t.title, framing: t.framing, differences: t.differences, decisions: t.decisions }, cards: cards.map(row) });
  });
}
