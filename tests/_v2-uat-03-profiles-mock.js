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

  // V2-UAT-04 (Section 6 of this Wave's own brief: "AUTH CONTEXT !=
  // PERMISSION CONTEXT != SALARY DATA FIXTURES"). Root cause of Human
  // Finding B: salarios-comissoes.js is 100% role-correct on its own
  // (canSeeGestor/canSeeGestorFi/canSeeOwnCommission/canSeeScopeCommission
  // all read the REAL, correctly-mocked NX_AUTH_CORE context) -- but its
  // "Resumo/Equipe" section is BY DESIGN never role-filtered client-side
  // (file header: "every profile that reaches this module at all...
  // operational_commission_metrics' own server-side scope already
  // restricts which rows come back"). It TRUSTS the RPC to have already
  // scoped the rows -- exactly like every real profile does in
  // production. This mock was previously handing back fx.METRICS/
  // fx.DIRECTORY/fx.ANALYST unconditionally (the SAME multi-store,
  // RH-5B-era fixture built for a MASTER demo) for every one of the 6
  // profiles, so an ANALISTA session saw a MASTER-shaped, cross-store
  // team roster. Fixed by building a per-scenario SCOPED response
  // instead, using each scenario's own real (perfil, loja, status) --
  // ONE parametrized builder, not six hardcoded branches (brief
  // Section 8: "Não criar seis hacks").
  //
  // Real, documented scope rule this follows (salarios-comissoes.js
  // canSeeScopeCommission's own comment, H-SAL-1/H-SAL-3): "ANALISTA
  // reviews sellers in her own Salary-authorized store scope; GERENTE
  // reviews their own team." VENDEDOR is themselves only (no team
  // concept). DIRETOR/RH are corporate-wide within their own
  // department, no single-store restriction (mirrors RH-2's own
  // documented operational_current_scope() shape, generalized). No
  // store name is invented anywhere below beyond the 3 real, already-
  // audited lojas already used by this harness's own PROFILES table
  // (NACOES/EUROPA/BANDEIRANTES).
  function scopedSalaryFixtures(p) {
    var perfil = p.perfil, loja = p.loja, status = p.status;
    var isDiretor = perfil.indexOf('DIRETOR') === 0;
    var isGerente = perfil === 'GERENTE';
    var isAnalista = perfil === 'ANALISTA';
    var isVendedor = perfil === 'VENDEDOR';
    var departments = isDiretor ? [status] : (status ? status.split('/') : ['NOVOS', 'SEMINOVOS']);
    var scopeStore = (isAnalista || isGerente || isVendedor) ? loja : null;

    function sellerRow(name, store, dept) {
      return {
        seller_id: 'uat-seller-' + name.replace(/\s+/g, '-').toLowerCase(), seller_name: name, store: store, department: dept,
        sold_count: 6, sales_value: 300000, financed_count: 4, share_percent: 66.7, production_value: 180000.0,
        return_value: 9000.0, spf_count: 1, spf_value: 1500.0, spf_net_value: 1050.0, profitability_value: 10050.0, plan_breakdown: []
      };
    }

    var rows;
    if (isDiretor) {
      rows = [sellerRow('Vendedor UAT Europa', 'EUROPA', departments[0]), sellerRow('Vendedor UAT Bandeirantes', 'BANDEIRANTES', departments[0])];
    } else if (scopeStore) {
      rows = [sellerRow('Vendedor UAT ' + scopeStore, scopeStore, departments[0])];
    } else {
      rows = [];
    }

    var totals = rows.reduce(function (acc, r) {
      acc.sold_count += r.sold_count; acc.financed_count += r.financed_count; acc.production_value += r.production_value;
      acc.return_value += r.return_value; acc.spf_value += r.spf_value; acc.spf_net_value += r.spf_net_value;
      acc.profitability_value += r.profitability_value; return acc;
    }, { sold_count: 0, financed_count: 0, share_percent: rows.length ? 66.7 : 0, production_value: 0, return_value: 0, spf_count: rows.length, spf_value: 0, spf_net_value: 0, profitability_value: 0 });

    var metrics = {
      // No is_master/is_director/is_seller field is ever true here
      // unless the scenario's own real perfil says so -- this is the
      // exact field a MASTER-shaped fixture previously hardcoded to
      // true regardless of profile.
      scope: { profile: perfil, departments: departments, is_master: false, is_director: isDiretor, is_seller: isVendedor, store: scopeStore },
      period_start: '2026-07-21', period_end: '2026-08-20', spf_net_percent: 70,
      eligibility_rule: 'ACTIVE_VENDEDOR_ONLY', plan_priority_rule: 'SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR',
      contains_personal_documents: false, contains_client_identity: false, contains_chassis: false,
      totals: totals, rows: rows
    };

    // faixa/faixa_level/comissao_total are what faixaCellHtml()/
    // comissaoTotalCellHtml() (salarios-comissoes.js:1082-1097) actually
    // read off a matched row -- without them the match still succeeds
    // (store/perfil/transfer align) but renders "NaN%" for a genuinely
    // missing field, a cosmetic gap in this synthetic fixture, not a
    // scope leak.
    function withFaixa(r) { return Object.assign({ faixa: 0.02, faixa_level: 'INTERMEDIARIA', comissao_total: r.profitability_value }, r); }

    // canSeeOwnCommission (VENDEDOR/GERENTE/ANALISTA only) -- her own
    // personal "Comissão" figure, never a MASTER/RH-wide one.
    var ownCommission = { rows: rows.map(function (r) { return withFaixa(Object.assign({ perfil: perfil }, r)); }), comissao_total: totals.profitability_value, profile: perfil };
    // canSeeScopeCommission (ANALISTA/GERENTE only) -- her own store's
    // team; empty for VENDEDOR/DIRETOR (real rule: "Never VENDEDOR --
    // no team concept for a seller"; DIRETOR uses the Equipe/metrics
    // view above, not this personal-scope RPC).
    var scopeCommission = (isAnalista || isGerente)
      ? { rows: rows.map(function (r) { return withFaixa(Object.assign({ perfil: 'VENDEDOR' }, r)); }), team_comissao_total: totals.profitability_value, profile: perfil }
      : { rows: [], team_comissao_total: 0, profile: perfil };

    var analyst = {
      absence_aware: true, contains_personal_documents: false, contains_client_identity: false, contains_chassis: false,
      rows: isAnalista ? [{
        analyst_name: p.nome, store: loja, sold_count: totals.sold_count, financed_count: totals.financed_count,
        production_value: totals.production_value, return_value: totals.return_value, spf_count: totals.spf_count, spf_value: totals.spf_value,
        transfer: false, covered_start: null, covered_end: null, coverage_id: null
      }] : []
    };

    var directory = {
      period_start: '2026-07-21', period_end: '2026-08-20', assignment_source: 'ACTIVE_PORTAL_PROFILE',
      rows: (isGerente || isDiretor) ? [{ store: scopeStore || departments[0], department: departments[0], manager_name: p.nome }] : [],
      ambiguous_assignments: 0, contains_client_identity: false, contains_personal_documents: false, contains_operational_identifiers: false
    };

    return { METRICS: metrics, ANALYST: analyst, DIRECTORY: directory, OWN_COMMISSION: ownCommission, SCOPE_COMMISSION: scopeCommission };
  }

  var scoped = scopedSalaryFixtures(payload);

  var realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';

    if (url.indexOf('assets/js/intelligence-runtime-config.js') !== -1) {
      return Promise.resolve(new Response('/* v2-uat-03 mock */', { status: 200, headers: { 'Content-Type': 'application/javascript' } }));
    }

    // Salários & Comissões. PERMISSION_CONTEXT (which sections can
    // render at all) is decided entirely by the real, unmodified
    // canSeeXxx(ctx) checks reading the correctly-mocked NX_AUTH_CORE
    // context above -- untouched by this block. SALARY DATA FIXTURES
    // (what those sections CONTAIN) are now scoped per-scenario
    // (scopedSalaryFixtures(), above) instead of reusing one blanket
    // MASTER-shaped dataset for every profile -- that reuse was Human
    // Finding B's real root cause. Period list/config/faixa-reference
    // (profile-independent, or MASTER-only-and-never-invoked-by-a-non-
    // MASTER canSeeGestorFi/canSeeHistorico check) still reuse the
    // EXISTING, already-approved RH-5B fixtures verbatim.
    if (fx) {
      if (url.indexOf('/rest/v1/rpc/operational_commission_periods') !== -1) return Promise.resolve(jsonResponse(200, fx.PERIODS));
      if (url.indexOf('/rest/v1/rpc/operational_commission_metrics') !== -1) return Promise.resolve(jsonResponse(200, scoped.METRICS));
      if (url.indexOf('/rest/v1/rpc/operational_analyst_commission_metrics_v2') !== -1) return Promise.resolve(jsonResponse(200, scoped.ANALYST));
      if (url.indexOf('/rest/v1/rpc/operational_salary_manager_directory') !== -1) return Promise.resolve(jsonResponse(200, scoped.DIRECTORY));
      if (url.indexOf('/rest/v1/rpc/operational_own_commission_summary') !== -1) return Promise.resolve(jsonResponse(200, scoped.OWN_COMMISSION));
      if (url.indexOf('/rest/v1/rpc/operational_scope_commission_rows') !== -1) return Promise.resolve(jsonResponse(200, scoped.SCOPE_COMMISSION));
      if (url.indexOf('/rest/v1/rpc/operational_salary_details') !== -1) return Promise.resolve(jsonResponse(200, fx.DETAILS));
      if (url.indexOf('/rest/v1/rpc/operational_portal_config') !== -1) return Promise.resolve(jsonResponse(200, fx.CONFIG));
      // MASTER-only server-side (42501 for any other profile) -- the
      // module itself never even calls these unless canSeeGestorFi(ctx)/
      // canSeeHistorico(ctx) is true, both of which require
      // ctx.isMaster===true, which is never true for any of the 6
      // named scenarios. Reusing the RH-5B fixture verbatim here is
      // inert, not a leak (dead code path for every scenario this
      // harness has).
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
