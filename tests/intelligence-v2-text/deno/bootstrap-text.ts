// IA-V2-2 -- boots the REAL, unmodified
// portal-ai-homolog/index.ts (read directly from the Intelligence
// authority repository -- READ ONLY, never copied) against the local
// mock backend for its OpenAI/Supabase boundaries. Its own real,
// unmodified CORS check (ALLOWED_ORIGINS.has(origin)) is exercised for
// real when a browser at http://localhost:8080 calls it directly,
// cross-origin -- see docs/IA-V2-2-TEXT-INTEGRATION.md.
//
// Run (from this directory):
//   V2_TEXT_PORT=8801 V2_MOCK_BASE=http://127.0.0.1:8790 \
//   SUPABASE_URL=http://127.0.0.1:8790 SUPABASE_ANON_KEY=v2-anon-key \
//   SUPABASE_SERVICE_ROLE_KEY=v2-service-key OPENAI_API_KEY=v2-dummy-key \
//   deno run --allow-net --allow-env --import-map=import_map.json bootstrap-text.ts
import "./fetch-patch.ts";

const INTELLIGENCE_SOURCE = Deno.env.get("V2_INTELLIGENCE_SOURCE") ||
  "C:/Projetos/ia-reconciliation-v2-local/supabase/functions/portal-ai-homolog/index.ts";

await import("file:///" + INTELLIGENCE_SOURCE.replace(/^\/+/, ""));
