import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { register } from "./tools.js";
import { dayOf, sessionHash, record, stats } from "./log.js";

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
  "access-control-allow-headers": "content-type, accept, mcp-session-id, mcp-protocol-version, last-event-id",
  "access-control-expose-headers": "mcp-session-id",
};
const json = (o, status = 200) => new Response(JSON.stringify(o, null, 1), { status, headers: { "content-type": "application/json; charset=utf-8", ...CORS } });

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (url.pathname === "/" || url.pathname === "/healthz") {
      return json({ name: "RecArch MCP", transport: "streamable-http", endpoint: `${url.origin}/mcp`, tools: ["search_cards", "get_card", "compare_topic"], read_only: true, auth: "none", site: env.SITE_URL, notice: "Not affiliated with the paper authors." });
    }
    if (url.pathname === "/_stats" && env.DEBUG_STATS === "1") return json(stats());
    if (url.pathname !== "/mcp") return json({ error: "not found" }, 404);

    const day = dayOf();
    const session = await sessionHash(request.headers.get("cf-connecting-ip"), day, env.SALT || "");
    // One log record per JSON-RPC message: the method, and for tools/call the tool name. Bodies and arguments are not logged here.
    if (request.method === "POST") {
      try {
        const body = await request.clone().json();
        for (const m of Array.isArray(body) ? body : [body]) record(env, { ts: Date.now(), day, event: "rpc", method: m.method, tool: m.method === "tools/call" ? m.params?.name : undefined, session });
      } catch { record(env, { ts: Date.now(), day, event: "bad_json", session }); }
    }
    // Stateless: a fresh server and transport per request, nothing to persist between calls.
    const server = new McpServer({ name: "recarch", version: "0.1.0" }, { instructions: "RecArch cards of industrial recommender, search and ranking systems. Search first, then get_card. Quote numbers exactly, and say not reported for anything the card marks so. Not affiliated with the paper authors." });
    register(server, { log: async (r) => record(env, { ts: Date.now(), day, session, ...r }) });
    const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    await server.connect(transport);
    const res = await transport.handleRequest(request);
    const h = new Headers(res.headers); for (const [k, v] of Object.entries(CORS)) h.set(k, v);
    return new Response(res.body, { status: res.status, headers: h });
  },
};
