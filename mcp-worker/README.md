# RecArch MCP server

Read-only remote MCP server for the RecArch card library. A Cloudflare Worker, Streamable HTTP, no auth, stateless. Nothing is deployed from this folder until you run the deploy steps below.

Tools, all annotated `readOnlyHint`:

| Tool | Arguments | Returns |
| --- | --- | --- |
| `search_cards` | `query`, `lang` zh or en, `limit` 1 to 10 | BM25 hits with id, name, company, year, one-line summary, links. Empty list when nothing matches. |
| `get_card` | `id`, `lang` | The full published card. `facts` lists every number with its source field path, or marks it not reported. |
| `compare_topic` | `topic` slug or `ids` 2 to 5, `lang`; no arguments lists topics | Side-by-side of baseline, A/B duration, traffic, online results and caveats per card. It never ranks. |

The bundled data is the site's own `cards.json` of each language. It holds our interpretation fields only. Unreviewed FAQ is never in it, and there is no source document text anywhere.

## Run locally

```bash
cd mcp-worker
npm install
(cd .. && SITE_URL=https://jdding.github.io/recarch python3 build.py)   # produces ../dist/cards.json
npm run sync-data                                                          # copies both languages into data/
npm test                                                                   # search and hash unit tests
npx wrangler dev --var DEBUG_STATS:1 &                                     # http://localhost:8787/mcp
STATS_URL=http://localhost:8787/_stats node test/client.mjs                # SDK client, exercises all 3 tools and the logging
npx @modelcontextprotocol/inspector --cli http://localhost:8787/mcp --transport http --method tools/list
```

`/_stats` exists only when `DEBUG_STATS=1`, which `wrangler.toml` sets to 0.

## Deploy later

Needs a Cloudflare account. Do these once the owner has approved the account and the domain.

1. Sign up at dash.cloudflare.com, free plan is enough.
2. `npx wrangler login`, which opens a browser to authorize.
3. Optional, usage analytics: in the dashboard open Workers and Pages, Analytics Engine, enable it, then uncomment the `[[analytics_engine_datasets]]` block in `wrangler.toml`.
4. Optional, hash salt: `npx wrangler secret put SALT` and enter any random string.
5. `npm run deploy`. It runs `sync-data` first, so rebuild the site before deploying whenever cards change. The first deploy prints a `https://recarch-mcp.<account>.workers.dev` address. Check `/healthz` and run `node test/client.mjs https://recarch-mcp.<account>.workers.dev/mcp`.
6. Custom domain, once the domain's DNS is on Cloudflare: uncomment `routes` in `wrangler.toml` with `pattern = "mcp.<domain>"` and `custom_domain = true`, deploy again. Cloudflare creates the DNS record and the certificate. Then set `workers_dev = false`.
7. Rebuild the site with the real URL so the pages, `llms.txt` and the skill carry it: `RECARCH_MCP_URL=https://mcp.<domain>/mcp python3 build.py`.
8. Recommended: a Cloudflare rate limiting rule on `mcp.<domain>`, for example 60 requests per minute per IP, in Security, WAF, Rate limiting rules.

Workers free plan allows 100,000 requests a day, far above what a card library needs.

## What is logged

Per JSON-RPC message that reaches `/mcp`: day, method, tool name for `tools/call`, and an anonymous session id. For a search or lookup with no result: the query text and the tool. Nothing else. The raw IP is never stored. The session id is the first 8 bytes of SHA-256 of `IP|day|SALT`, so it cannot be linked across days.

Records go to Workers Logs as one JSON line each (`{"app":"recarch-mcp","event":"rpc",...}`) and, when bound, to Analytics Engine. Example queries, run in the dashboard SQL API:

```sql
-- calls per day
SELECT blob1 AS day, count() AS calls FROM recarch_mcp WHERE blob2 = 'rpc' GROUP BY day ORDER BY day;
-- calls per tool
SELECT blob3 AS tool, count() AS calls FROM recarch_mcp WHERE blob2 = 'rpc' AND blob3 != '' GROUP BY tool;
-- anonymous sessions per day
SELECT blob1 AS day, count(DISTINCT index1) AS sessions FROM recarch_mcp GROUP BY day;
-- searches with no result
SELECT blob1 AS day, blob5 AS query FROM recarch_mcp WHERE blob2 = 'zero_result' ORDER BY day DESC LIMIT 100;
```

Zero-result queries show which cards or topics to write next.

## Notes

- workers.dev addresses are unreliable from mainland China. Use a custom domain on Cloudflare for users there.
- The server is stateless, so there are no sessions to expire and it scales to zero.
- Tool results are card text. Clients should treat them as data; the server instructions say so too.
