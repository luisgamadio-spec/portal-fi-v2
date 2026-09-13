/* V2-UAT-03 -- mock installer for tests/_v2-uat-03-profiles-harness.html.
   Runs INSIDE the iframe, spliced in before every real script tag --
   same proven technique as tests/_salarios-uat-mock.js (RH-5B), only
   generalized from "one module, one profile dropdown" to "the whole
   Portal, six fixed named-profile scenarios." Installs a
   pre-authenticated synthetic session (no login form, no real
   credentials, no real employee password anywhere) and intercepts
   window.fetch for exactly the RPC/config URLs needed -- every other
   request (real CSS/JS/font assets) passes through untouched to the
   real static file server. SYNTHETIC DATA ONLY, never a real Supabase
   project (supabaseUrl below is a fake, unreachable host).

   This file is NEVER referenced by index.html/shell.js/config/*.json
   -- it only ever runs when explicitly spliced into an iframe by the
   dedicated harness page, so the normal Portal (:8080/index.html) is
   completely unaffected by this file's mere presence on disk. */
(function () {
  'use strict';

  var payload = window.__V2UAT03_PAYLOAD__ || {};
  var profile = payload.perfil || 'ANALISTA';

  window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://v2uat03.invalid', supabasePublishableKey: 'uat-key', textEndpoint: null };

  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  var fakeSession = { access_token: 'uat-token', user: { id: 'uat-auth-user-' + (payload.key || 'x') } };
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          getSession: function () { return ok({ session: fakeSession }); },
          signInWithPassword: function () { return ok({ session: fakeSession }); },
          onAuthStateChange: function () { return { data: { subscription: { unsubscribe: function () {} } } } },
          signOut: function () { return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          // The one RPC auth-boundary.js's resolveAfterSession() calls
          // to build the REAL, unmodified frozen context object --
          // profile/loja/status come straight from this payload, never
          // computed client-side.
          if (name === 'usuario_logado_fi') {
            return ok([{
              usuario_id: 'uat-' + (payload.key || 'x'), auth_user_id: fakeSession.user.id,
              // V2-UAT-03B: loja is now always an explicit, real, audited
              // value per scenario (including a genuine null for Rodrigo,
              // who has no store-specific assignment) -- no '|| TODAS'
              // fallback, which would have silently replaced a real null
              // with a placeholder.
              nome: payload.nome, perfil: payload.perfil, loja: payload.loja,
              status: payload.status || null, ativo: true
            }]);
          }
          // Drives every PERMISSION_MATRIX module's real, unmodified
          // isModuleAuthorized() check (auth-core.js) -- see this
          // harness's own payload table for exactly which permissionIds
          // are granted per scenario, and this Wave's report for which
          // of those are code-VERIFIED vs. a labeled UAT assumption.
          if (name === 'portal_modulos_permitidos') return ok(payload.allowedModuleIds || []);
          return ok(null);
        }
      };
    }
  };

  function jsonResponse(status, body) {
    return new Response(JSON.stringify(body), { status: status, headers: { 'Content-Type': 'application/json' } });
  }

  var fx = window.NX_RH5B_UAT_FIXTURES; // reused byte-identical, see harness comment

  var realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';

    if (url.indexOf('assets/js/intelligence-runtime-config.js') !== -1) {
      return Promise.resolve(new Response('/* v2-uat-03 mock */', { status: 200, headers: { 'Content-Type': 'application/javascript' } }));
    }

    // Salários & Comissões: reuse the EXISTING, already-approved RH-5B
    // synthetic fixtures verbatim (tests/_salarios-uat-fixtures.js) so
    // this module keeps rendering real-looking data under this harness
    // too, unconditionally (same RH-5C.1 precedent: this file's job is
    // presenting the real rendering logic, not re-testing server-side
    // authorization -- that already has its own real RPC gate, and
    // module VISIBILITY on Landing/nav is governed by
    // portal_modulos_permitidos() above, independent of this).
    if (fx) {
      if (url.indexOf('/rest/v1/rpc/operational_commission_periods') !== -1) return Promise.resolve(jsonResponse(200, fx.PERIODS));
      if (url.indexOf('/rest/v1/rpc/operational_commission_metrics') !== -1) return Promise.resolve(jsonResponse(200, fx.METRICS));
      if (url.indexOf('/rest/v1/rpc/operational_analyst_commission_metrics_v2') !== -1) return Promise.resolve(jsonResponse(200, fx.ANALYST));
      if (url.indexOf('/rest/v1/rpc/operational_salary_manager_directory') !== -1) return Promise.resolve(jsonResponse(200, fx.DIRECTORY));
      if (url.indexOf('/rest/v1/rpc/operational_salary_details') !== -1) return Promise.resolve(jsonResponse(200, fx.DETAILS));
      if (url.indexOf('/rest/v1/rpc/operational_portal_config') !== -1) return Promise.resolve(jsonResponse(200, fx.CONFIG));
      if (url.indexOf('/rest/v1/rpc/operational_commission_faixa_rows') !== -1) return Promise.resolve(jsonResponse(200, fx.FAIXA_ROWS));
      if (url.indexOf('/rest/v1/rpc/master_commission_closings') !== -1) return Promise.resolve(jsonResponse(200, fx.CLOSINGS_ALL));
      if (url.indexOf('/rest/v1/rpc/operational_gestor_fi_commission') !== -1) {
        return Promise.resolve(jsonResponse(200, profile === 'MASTER' ? fx.GESTOR_FI_READY : fx.GESTOR_FI_NOT_READY));
      }
    }

    // Every other RPC (dashbi/gestao/score/coparticipado/simuladores/
    // painel-analista-fi/central-atendimento-fi/brabus-intelligence) is
    // intentionally NOT mocked here -- this Wave is a VISIBILITY UAT
    // (which modules appear/hide per profile), not a full real-data
    // integration. Those requests fall through to realFetch, which
    // resolves against the fake v2uat03.invalid host and fails
    // harmlessly -- each module's own already-tested/approved
    // empty/error state renders instead of real figures. Never a
    // fabricated success for logic this harness doesn't own.
    return realFetch(input, init);
  };

  // Auto-navigate to Landing once authenticated -- the Human explores
  // every module's visibility from there, not just one route.
  var poll = setInterval(function () {
    if (window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTHORIZED') {
      clearInterval(poll);
      location.hash = '#/landing';
    }
  }, 50);
})();
