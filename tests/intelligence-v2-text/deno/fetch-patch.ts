// IA-V2-2 harness -- monkey-patches the GLOBAL fetch BEFORE dynamically
// importing the real, unmodified portal-ai-homolog source. Only the
// OpenAI external boundary is redirected (Gate 32: no safe local
// homolog OpenAI credentials available this phase, so this stays
// DETERMINISTIC_MODEL_BOUNDARY_E2E, disclosed as such throughout):
// any call to https://api.openai.com/* is rewritten to hit the local
// mock backend's /openai/* routes instead. The real source never
// knows -- it still calls the exact same OpenAI URL it calls in
// production.
//
// Nothing here touches Supabase URLs -- those are pointed at the mock
// backend simply via the SUPABASE_URL/SUPABASE_ANON_KEY/
// SUPABASE_SERVICE_ROLE_KEY env vars the harness sets before running
// this process, exactly the same knobs the real deployed function
// reads (no patching needed for that boundary).
//
// (Same technique as ia-reconciliation-v2-local's own
// tests/ai-uat-e2e/deno/fetch-patch.ts from IA-UAT-02 -- kept as its
// own copy here since the Intelligence repository stays read-only.)

const MOCK_BASE = Deno.env.get("V2_MOCK_BASE") || "http://127.0.0.1:8790";

const realFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const originalUrl = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  if (originalUrl.startsWith("https://api.openai.com/")) {
    const rewritten = MOCK_BASE + "/openai" + originalUrl.slice("https://api.openai.com".length);
    console.log(`[v2-fetch-patch] ${originalUrl} -> ${rewritten}`);
    if (input instanceof Request) {
      return realFetch(new Request(rewritten, input), init);
    }
    return realFetch(rewritten, init);
  }
  return realFetch(input as any, init);
}) as typeof fetch;
