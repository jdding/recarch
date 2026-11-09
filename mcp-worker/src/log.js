// Privacy-preserving usage log. Never stores the raw IP.
// Record shape: { ts, day, event, tool, session, query?, results? }. Written with console.log (Workers Logs) and, when bound, Analytics Engine.
export function dayOf(d = new Date()) { return d.toISOString().slice(0, 10); }

export async function sessionHash(ip, day, salt = "") {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${ip || "unknown"}|${day}|${salt}`));
  return [...new Uint8Array(buf)].slice(0, 8).map((x) => x.toString(16).padStart(2, "0")).join("");
}

// In-memory counters of this isolate, readable at /_stats only when DEBUG_STATS=1. Real numbers come from Analytics Engine or Workers Logs.
export const MEM = { days: {}, tools: {}, sessions: {}, zero: [] };

export function record(env, rec) {
  const day = rec.day;
  // "calls" = JSON-RPC messages that reached /mcp; per-tool counts = tools/call messages only
  if (rec.event === "rpc") {
    MEM.days[day] = (MEM.days[day] || 0) + 1;
    if (rec.tool) { const k = `${day}:${rec.tool}`; MEM.tools[k] = (MEM.tools[k] || 0) + 1; }
  }
  (MEM.sessions[day] ||= new Set()).add(rec.session);
  if (rec.event === "zero_result" && MEM.zero.length < 200) MEM.zero.push({ day, tool: rec.tool, query: rec.query });
  console.log(JSON.stringify({ app: "recarch-mcp", ...rec }));
  try {
    env.ANALYTICS?.writeDataPoint({ indexes: [rec.session], blobs: [day, rec.event, rec.tool || "", rec.method || "", (rec.query || "").slice(0, 200)], doubles: [1, rec.results ?? 0] });
  } catch { /* logging must never break a request */ }
}

export function stats() {
  return { days: MEM.days, tools: MEM.tools, sessions_per_day: Object.fromEntries(Object.entries(MEM.sessions).map(([d, s]) => [d, s.size])), zero_result_queries: MEM.zero };
}
