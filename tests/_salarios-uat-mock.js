/* RH-5B -- mock installer for tests/_salarios-uat-harness.html. Runs
   INSIDE the iframe, spliced in before every real script tag. Installs
   a pre-authenticated synthetic session (no login form, no real
   credentials anywhere) and intercepts window.fetch for exactly the
   RPC/config URLs this module calls -- every other request (real CSS/
   JS/font assets) passes through untouched to the real static server.
   SYNTHETIC DATA ONLY, never a real Supabase project. */
(function () {
  'use strict';

  var payload = window.__RH5B_UAT_PAYLOAD__ || {};
  var profile = payload.profile || 'MASTER';
  var statusByProfile = { MASTER: 'MASTER', RH: 'RH', GERENTE: 'GERENTE', ANALISTA: 'NOVOS', VENDEDOR: 'NOVOS' };

  window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://uat.invalid', supabasePublishableKey: 'uat-key', textEndpoint: null };

  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  var fakeSession = { access_token: 'uat-token', user: { id: 'uat-auth-user' } };
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
          if (name === 'usuario_logado_fi') {
            return ok([{ usuario_id: 'uat-u1', auth_user_id: 'uat-auth-user', nome: 'UAT ' + profile, perfil: profile, loja: 'TODAS', status: statusByProfile[profile] || profile, ativo: true }]);
          }
          if (name === 'portal_modulos_permitidos') return ok(['comissoes']);
          return ok(null);
        }
      };
    }
  };

  function jsonResponse(status, body) {
    return new Response(JSON.stringify(body), { status: status, headers: { 'Content-Type': 'application/json' } });
  }

  var realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';

    if (url.indexOf('assets/js/intelligence-runtime-config.js') !== -1) {
      return Promise.resolve(new Response('/* uat mock */', { status: 200, headers: { 'Content-Type': 'application/javascript' } }));
    }
    if (url.indexOf('/rest/v1/rpc/operational_commission_periods') !== -1) return Promise.resolve(jsonResponse(200, payload.periods));
    if (url.indexOf('/rest/v1/rpc/operational_commission_metrics') !== -1) return Promise.resolve(jsonResponse(200, payload.metrics));
    if (url.indexOf('/rest/v1/rpc/operational_analyst_commission_metrics_v2') !== -1) return Promise.resolve(jsonResponse(200, payload.analyst));
    if (url.indexOf('/rest/v1/rpc/operational_salary_manager_directory') !== -1) return Promise.resolve(jsonResponse(200, payload.directory));
    if (url.indexOf('/rest/v1/rpc/operational_salary_details') !== -1) return Promise.resolve(jsonResponse(200, payload.details));
    // RH-5B.3
    if (url.indexOf('/rest/v1/rpc/operational_portal_config') !== -1) return Promise.resolve(jsonResponse(200, payload.config));
    // RH-5C.1 -- MASTER-only in the real backend; harness mocks return
    // the real payload regardless of selected profile (matching every
    // other RPC mock here), since this file's job is presenting real
    // rendering logic, not re-testing server-side authorization (that
    // is proven live, see this Wave's own report).
    if (url.indexOf('/rest/v1/rpc/operational_gestor_fi_commission') !== -1) return Promise.resolve(jsonResponse(200, payload.gestorFi));
    if (url.indexOf('/rest/v1/rpc/operational_commission_faixa_rows') !== -1) return Promise.resolve(jsonResponse(200, payload.faixaRows));
    if (url.indexOf('/rest/v1/rpc/master_commission_closings') !== -1) return Promise.resolve(jsonResponse(200, payload.closings));

    if (url.indexOf('/rest/v1/rpc/master_commission_snapshot_export') !== -1) {
      var closingIdExp = closingIdFromBody(init);
      var rowsExp = payload.snapshots[closingIdExp] || { rows: [] };
      var allBroken = rowsExp.rows.length === 0 || rowsExp.rows.every(function (r) { return (Number(r.comissao) || 0) === 0 && (r.detalhes === null || r.detalhes === undefined); });
      if (allBroken) {
        return Promise.resolve(jsonResponse(400, { code: '22023', message: 'Exportação bloqueada: o fechamento desta competência possui um snapshot histórico inconsistente. Procure a Administração/RH F&I.' }));
      }
      return Promise.resolve(jsonResponse(200, rowsExp));
    }
    if (url.indexOf('/rest/v1/rpc/master_commission_snapshot') !== -1) {
      var closingId = closingIdFromBody(init);
      return Promise.resolve(jsonResponse(200, payload.snapshots[closingId] || { rows: [] }));
    }
    if (url.indexOf('/rest/v1/rpc/master_commission_operational_detail') !== -1) return Promise.resolve(jsonResponse(200, payload.opDetail));

    return realFetch(input, init);
  };

  function closingIdFromBody(init) {
    try {
      var body = JSON.parse((init && init.body) || '{}');
      return body.p_closing_id;
    } catch (e) { return null; }
  }

  // Auto-navigate straight to the module once authenticated -- no login
  // form, no click needed (Gate 53: open -> already on the real page).
  var poll = setInterval(function () {
    if (window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTHORIZED') {
      clearInterval(poll);
      location.hash = '#/salarios-comissoes';
    }
  }, 50);
})();
