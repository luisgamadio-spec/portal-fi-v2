/* PORTAL-NEXT V2 -- production runtime config (GL-1D, Go-Live deployment
   reconciliation), modeled directly on the Secure repo's own
   assets/js/portal-runtime-config.production.js: a hand-maintained,
   checked-in static file, loaded via a plain relative <script src>, no
   build-time substitution, no secret injection. Every value below is
   public-by-design client material -- safe to commit, exactly like
   Secure's own file. No service-role key, no OpenAI key, no private
   secret of any kind belongs here, ever.

   GL-1J: wired into index.html behind an exact-hostname check (see
   index.html's own host-conditional loader) -- loads ONLY on
   luisgamadio-spec.github.io, the proven GitHub Pages homologation
   hostname (GL-1I.1). Everywhere else (localhost, any other host) this
   file is never requested and has zero runtime effect.

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
  // INTELLIGENCE_ONLY -- TEXT activated in SEC-1C.3; Voice activated in
  // VOICE-UAT-1, the separate, later, explicitly-authorized Go-Live
  // gate GL-1 Gate 17's own comment anticipated. This is still the
  // controlled homologation activation (server-side profile gate,
  // portal-ai-homolog/portal-realtime-homolog's own
  // SEC1C_HOMOLOG_ALLOWED_PROFILES/VOICESEC1_ALLOWED_PROFILES, now
  // MASTER/ANALISTA/VENDEDOR/GERENTE/DIRETOR NOVOS -- unaffected by
  // this file either way) -- NOT a general production cutover.
  mode: 'real_text',
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
  // INTELLIGENCE_ONLY -- SEC-1C.3: the real, already-deployed
  // portal-ai-homolog TEXT function, derived from the SAME supabaseUrl
  // above (one project, never a second/duplicated project identity;
  // matches this whole codebase's own "textEndpoint is its own field,
  // not derived at runtime" convention purely because a local harness
  // needs the split -- on a real host like this one, the two values
  // are the same project by construction). Backend already hardened
  // (SEC-1A/SEC-1B) and gated to MASTER/ANALISTA/VENDEDOR/GERENTE/
  // DIRETOR NOVOS (SEC-1C through SEC-1G) -- unaffected by this file
  // either way.
  textEndpoint: 'https://yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-ai-homolog',
  // INTELLIGENCE_ONLY (VOICE-UAT-1) -- the real, already-deployed
  // portal-realtime-homolog ephemeral-credential mint function, same
  // "derived from the same supabaseUrl above" pattern as textEndpoint
  // immediately above -- one project, never a second identity. Backend
  // authority already converged onto Text's own approved profile
  // matrix and proven server-side this Wave (VOICE-SEC-1: MASTER/
  // ANALISTA/VENDEDOR/GERENTE/DIRETOR NOVOS; RH and DIRETOR SEMINOVOS
  // still blocked, unaffected by this file either way). This is the
  // ONLY change this Wave makes -- no visual/UX/model/VAD/prompt
  // change, no new parameter added to the mint request body
  // (intelligence-voice.js's own fetch already sends only the real
  // session token, unchanged). Populating this field is exactly what
  // unblocks intelligence-voice.js's own existing fail-closed guard
  // (`if (!cfg.voiceRealtimeEndpoint || !cfg.supabasePublishableKey)`)
  // -- no other file needs to change for Voice to activate.
  voiceRealtimeEndpoint: 'https://yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-realtime-homolog',
  // GL-1J -- authorizes EXACTLY the proven GitHub Pages homologation
  // hostname (GL-1I.1's REAL_HOMOLOGATION_HOSTNAME, confirmed live via
  // GitHub's own Pages API, not guessed). This is a technical
  // homologation environment, NOT the official brabus.blistiq.com.br
  // production domain -- that domain is untouched and would require its
  // own separate, later, explicitly-authorized Human cutover decision.
  // Exact string match only (assets/js/environment-guard.js uses
  // indexOf, not a pattern) -- no wildcard, no *.github.io.
  authorizedHostnames: ['luisgamadio-spec.github.io']
};
