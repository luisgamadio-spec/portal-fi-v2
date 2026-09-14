// LATENCY-1 -- boots the REAL, unmodified (well, instrumented THIS
// SAME Wave, never business-logic-modified) portal-ai-homolog/index.ts
// against the local mock backend's OpenAI/Supabase boundaries, exactly
// like bootstrap-text.ts's own established technique (same
// fetch-patch.ts, same import_map.json) -- a new file rather than a
// repair of bootstrap-text.ts/bootstrap-text-real.ts (out of this
// Wave's surgical scope; bootstrap-text-real.ts, referenced by
// tests/intelligence-kill-switch-test.py, does not exist on disk under
// this name -- a pre-existing, unrelated defect noted in this Wave's
// own report, not fixed here).
//
// V2_INTELLIGENCE_SOURCE defaults to the CURRENT Secure repo path (the
// actual writable repository this Wave instruments), not
// bootstrap-text.ts's own stale default (a different, older worktree
// path) -- override via env var if ever needed.
//
// Run (from this directory):
//   V2_TEXT_PORT=18801 V2_MOCK_BASE=http://127.0.0.1:18790 \
//   SUPABASE_URL=http://127.0.0.1:18790 SUPABASE_ANON_KEY=v2-anon-key \
//   SUPABASE_SERVICE_ROLE_KEY=v2-service-key OPENAI_API_KEY=v2-dummy-key \
//   deno run --allow-net --allow-env --allow-read --import-map=import_map.json bootstrap-latency1.ts
import "./fetch-patch.ts";

const INTELLIGENCE_SOURCE = Deno.env.get("V2_INTELLIGENCE_SOURCE") ||
  "C:/Projetos/portal-financiamento-brabus-secure-ia3b/supabase/functions/portal-ai-homolog/index.ts";

await import("file:///" + INTELLIGENCE_SOURCE.replace(/^\/+/, ""));
