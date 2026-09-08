/* PORTAL-NEXT V2 -- production runtime config (GL-1D, Go-Live deployment
   reconciliation), modeled directly on the Secure repo's own
   assets/js/portal-runtime-config.production.js: a hand-maintained,
   checked-in static file, loaded via a plain relative <script src>, no
   build-time substitution, no secret injection. Every value below is
   public-by-design client material -- safe to commit, exactly like
   Secure's own file. No service-role key, no OpenAI key, no private
   secret of any kind belongs here, ever.

   This file does NOT get loaded by index.html yet (see the deployment
   reconciliation report's own "index.html not yet updated" note) -- it
   exists, ready to be wired in behind an environment check (only on the
   eventual real production hostname, never unconditionally), once
   index.html's current collision with a parallel session's own edits is
   resolved. Until then this file has zero runtime effect.

   supabaseUrl / supabasePublishableKey / turnstileSiteKey: the SAME
   real, already-public values Secure's own tracked production config
   already ships today (same Supabase project, same Turnstile site key)
   -- reused deliberately, per GL-1 Gate 18, not invented. Safe by the
   same reasoning already established repo-wide: a Supabase publishable
   key and a Turnstile SITE key are both designed for client exposure;
   security is enforced by RLS/Edge-Function-side checks and by
   Cloudflare's own hostname binding on the Turnstile site key, not by
   hiding these values. */
window.NX_INTELLIGENCE_CONFIG = {
  // INTELLIGENCE_ONLY -- stays inert in this production file. Per GL-1
  // Gate 17: "Intelligence Text/Voice is NOT being activated in this
  // wave... Production config must preserve it as inert unless
  // explicitly authorized later." Flipping this to 'real_text' is a
  // separate, later, explicitly-authorized Go-Live gate for
  // Intelligence specifically -- never bundled into a deployment-
  // infrastructure change.
  mode: 'fixture',
  // SHARED -- the real Supabase project every real-data module
  // (Auth Foundation, Score, Coparticipado, Gestão, Dashbi, Painel
  // Master, Painel do Analista) needs to function against real data.
  supabaseUrl: 'https://yacqlelpzchcotgngwbh.supabase.co',
  supabasePublishableKey: 'sb_publishable__J96gDH1kOqlc4iFW24Z2Q_u_lWAg5_',
  // SHARED -- public Cloudflare Turnstile site key, reused verbatim
  // from Secure's own real production config (same Cloudflare Turnstile
  // registration). NOTE (GL-1 Gate 14/18): Turnstile site keys are
  // typically bound to specific hostnames in Cloudflare's own
  // dashboard (external to both repos) -- if V2's eventual production
  // hostname differs from Secure's, this exact site key may need a
  // corresponding hostname added in Cloudflare's Turnstile config, or a
  // new site key issued. That binding is a Human/Cloudflare checkpoint,
  // not something either repo's code can prove or resolve.
  turnstileSiteKey: '0x4AAAAAAEFmBWKvC-l1_CEs',
  // INTELLIGENCE_ONLY -- stays null; no real backend deployed yet
  // (see the Go-Live audit's own Intelligence Text findings). Never
  // populate this until Intelligence Text is independently authorized
  // to go live, with its own real deployment + real Human UAT.
  textEndpoint: null,
  // GL-1C -- deliberately EMPTY. The final V2 production hostname has
  // not been chosen by the Human yet (Go-Live Human checkpoint, Section
  // 15/16 of the deployment reconciliation report). An empty array
  // means assets/js/environment-guard.js will correctly classify this
  // production file's own real host as UNKNOWN_HOST (fail closed) until
  // a Human explicitly records the chosen hostname here. Do not invent
  // a hostname to make this "work" -- an empty allowlist is the
  // correct, safe, intended state today.
  authorizedHostnames: []
};
