/* PORTAL-NEXT V2 — Supabase runtime config (IA-V2-2, ownership
   clarified AUTH FOUNDATION Phase 2C Gate 3-4).

   NAMING NOTE: despite the filename, `supabaseUrl` and
   `supabasePublishableKey` are SHARED, general-Portal values — since
   AUTH FOUNDATION Phase 2B, assets/js/auth-boundary.js reads ONLY
   these two fields (never `.mode`) to decide whether real Supabase
   Auth is available for the WHOLE app (login, session, every
   PERMISSION_MATRIX/MASTER_ONLY/ANALISTA_OR_MASTER route), not just
   Intelligence. `mode` and `textEndpoint` remain INTELLIGENCE_ONLY —
   no other consumer reads them. Kept as one file (not split) because
   a real deployment only ever has ONE real Supabase project either
   way; splitting would just require keeping two files' supabaseUrl/
   supabasePublishableKey in sync for no safety benefit. Do not add an
   Intelligence-specific field here that Auth Foundation would need to
   duplicate elsewhere.

   COMMITTED DEFAULTS ONLY — safe on every host, including a
   production-looking one (Gate 8 feature containment: this is what
   ships if nothing else overrides it, and is also what makes
   Auth Foundation's own guard stay fully inert -- AUTH_NOT_CONFIGURED
   -- absent a local override). `mode: 'fixture'` means Intelligence
   specifically behaves exactly as IA-V2-1 shipped it — 0 network
   calls, synthetic contract data, fixture banner visible.

   A real backend endpoint is NEVER hardcoded here. Real/local-homolog
   transport (for Intelligence AND, as of Phase 2B, general Auth) is
   opt-in only, via assets/js/intelligence-runtime-config.local.js
   (gitignored, loaded only on localhost/127.0.0.1 — see index.html —
   same convention the Secure repo already uses for its own
   portal-runtime-config.local.js). That file does not exist unless a
   developer creates it from
   assets/js/intelligence-runtime-config.example.js for their own
   machine — and doing so now activates the Auth Foundation login/
   route guard for their whole local session, not only Intelligence
   (AUTH FOUNDATION Phase 2C Gate 2 finding). */
window.NX_INTELLIGENCE_CONFIG = {
  // INTELLIGENCE_ONLY. 'fixture' | 'real_text' -- anything other than
  // exactly 'real_text' is treated as fixture mode (fail-closed, see
  // Gate 8). assets/js/auth-boundary.js never reads this field.
  mode: 'fixture',
  // SHARED (AUTH FOUNDATION Phase 2B+): the general Portal V2
  // Supabase connection -- consumed by auth-boundary.js for ALL auth
  // (login, session, module permissions), and by Intelligence's own
  // adapter for its Edge Function's anon-key header. One project,
  // one pair of values, one file -- not duplicated elsewhere.
  supabaseUrl: null,
  supabasePublishableKey: null,
  // SHARED (AUTH FOUNDATION Phase 3B): public Cloudflare Turnstile
  // site key (not a secret -- Turnstile's own design). null/absent
  // here means Login never loads Cloudflare at all and forwards no
  // captchaToken -- the default committed state and every mock/
  // fixture-mode host, matching Gate 14/20's zero-Cloudflare-
  // dependency requirement for deterministic testing.
  turnstileSiteKey: null,
  // INTELLIGENCE_ONLY. Full URL to the portal-ai-homolog TEXT
  // function. Kept as its own field (not derived as
  // supabaseUrl + '/functions/v1/...') because
  // this LOCAL harness runs the mock Supabase Auth/REST boundary and
  // the real, unmodified portal-ai-homolog Deno process as two
  // separate local origins (no real Supabase project exists to unify
  // them under one URL locally) -- see docs/IA-V2-2-TEXT-INTEGRATION.md
  // for why that split doesn't weaken the CORS evidence this phase
  // gathers (the browser still calls the real function's real origin
  // directly, cross-origin, exercising its actual unmodified CORS
  // check for real).
  textEndpoint: null,
  // SHARED (GL-1C, Go-Live deployment reconciliation): the explicit
  // hostname allowlist assets/js/environment-guard.js consults to
  // decide AUTHORIZED_PRODUCTION vs UNKNOWN_HOST. Deliberately empty by
  // default -- committing a real hostname here is a Human decision made
  // once V2's actual deployment identity is chosen (Go-Live Human
  // checkpoint), never invented ahead of that decision. An empty array
  // means every non-local-dev host is UNKNOWN_HOST (fail closed), which
  // is the correct, safe behavior until that Human decision is made and
  // recorded in a real intelligence-runtime-config.production.js.
  authorizedHostnames: []
};
