/* PORTAL-NEXT V2 — Brabus Intelligence runtime config (IA-V2-2).

   COMMITTED DEFAULTS ONLY — safe on every host, including a
   production-looking one (Gate 8 feature containment: this is what
   ships if nothing else overrides it). `mode: 'fixture'` means the
   module behaves exactly as IA-V2-1 shipped it — 0 network calls,
   synthetic contract data, fixture banner visible.

   A real backend endpoint is NEVER hardcoded here. Real/local-homolog
   transport is opt-in only, via
   assets/js/intelligence-runtime-config.local.js (gitignored, loaded
   only on localhost/127.0.0.1 — see index.html — same convention the
   Secure repo already uses for its own portal-runtime-config.local.js).
   That file does not exist unless a developer creates it from
   assets/js/intelligence-runtime-config.example.js for their own
   machine. */
window.NX_INTELLIGENCE_CONFIG = {
  // 'fixture' | 'real_text' -- anything other than exactly 'real_text'
  // is treated as fixture mode (fail-closed, see Gate 8).
  mode: 'fixture',
  supabaseUrl: null,
  supabasePublishableKey: null,
  // Full URL to the portal-ai-homolog TEXT function. Kept as its own
  // field (not derived as supabaseUrl + '/functions/v1/...') because
  // this LOCAL harness runs the mock Supabase Auth/REST boundary and
  // the real, unmodified portal-ai-homolog Deno process as two
  // separate local origins (no real Supabase project exists to unify
  // them under one URL locally) -- see docs/IA-V2-2-TEXT-INTEGRATION.md
  // for why that split doesn't weaken the CORS evidence this phase
  // gathers (the browser still calls the real function's real origin
  // directly, cross-origin, exercising its actual unmodified CORS
  // check for real).
  textEndpoint: null
};
