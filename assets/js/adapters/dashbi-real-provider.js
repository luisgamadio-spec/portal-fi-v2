/* PORTAL-NEXT V2 -- Dashbi REAL data provider (Real Data Integration
   Foundation, Dashbi Phase 2).

   THIN transport boundary, same principle as gestao-real-provider.js
   (Gate B2): this file's only job is calling the real, already-proven
   operational_metrics / operational_model_metrics RPCs and returning
   their raw payloads (or a classified error) -- no financial
   calculation, no scope calculation, no permission calculation, no
   plan/model classification. All of that is 100% backend-owned
   (Dashbi Phase 1 contract audit) or, for the thin presentation
   reshape (ticket derivation, model-name normalization), lives in
   dashbi-real-view-model.js -- never here.

   p_group_view is ALWAYS sent as true (Dashbi Phase 2, Stage A, Gate
   A5 -- DASHBI_GROUP_VIEW_AUTHORITY_V1, frozen): the real RPC's own
   server-side gate (profile IN ('ANALISTA','VENDEDOR') AND
   portal_modulos_permitidos() ? 'dashbi') decides whether this
   actually elevates scope; for MASTER/DIRETOR/GERENTE it is a no-op.
   The frontend never computes or overrides scope itself -- exactly
   V1's own real production adapter's pattern
   (analise-geral-grupo-secure-adapter.js fetchMetrics()).

   Reuses the EXISTING Auth Foundation session (window.NX_AUTH), same
   as gestao-real-provider.js -- no independent Supabase client. */
(function () {
  'use strict';

  function classifyError(code, httpStatus) {
    if (code === '42501') return 'PERMISSION_DENIED';
    if (code === '22023') return 'INVALID_FILTER';
    if (code === 'P0002') return 'SCOPE_EMPTY';
    if (code === '57014') return 'BACKEND_ERROR';
    if (httpStatus === 401 || httpStatus === 403) return 'SESSION_EXPIRED';
    return 'BACKEND_ERROR';
  }

  // Same anti-leak guard family as gestao-real-provider.js (Gate B14) --
  // both real Dashbi RPCs self-declare contains_personal_documents/
  // client_identity/chassis: false (Phase 1, Gate 14); their presence
  // would mean either a wrong RPC got called or the contract changed
  // underneath this integration without re-auditing it.
  var SENSITIVE_KEYS = ['client_identity', 'personal_documents', 'cpf', 'chassis', 'customer_name', 'customer_document'];
  function hasSensitiveShape(data) {
    if (!data || typeof data !== 'object') return false;
    if (SENSITIVE_KEYS.some(function (k) { return Object.prototype.hasOwnProperty.call(data, k); })) return true;
    if (data.contains_personal_documents || data.contains_client_identity || data.contains_chassis) return true;
    return false;
  }

  function hasValidRowsShape(data) {
    return !!data && typeof data === 'object' && Array.isArray(data.rows);
  }

  function callRpc(rpcName, start, end) {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (!cfg.supabaseUrl || !cfg.supabasePublishableKey) {
      return Promise.reject({ state: 'BACKEND_ERROR', message: 'Configuração real ausente neste ambiente.' });
    }
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      return Promise.reject({ state: 'SESSION_EXPIRED', message: 'Sessão indisponível.' });
    }

    return window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) return Promise.reject({ state: 'SESSION_EXPIRED', message: 'Sessão expirada.' });

      return fetch(cfg.supabaseUrl + '/rest/v1/rpc/' + rpcName, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': cfg.supabasePublishableKey,
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ p_start: start, p_end: end, p_group_view: true })
      }).then(function (resp) {
        return resp.json().catch(function () { return null; }).then(function (body) {
          if (!resp.ok) {
            var code = body && body.code;
            return Promise.reject({ state: classifyError(code, resp.status), message: (body && body.message) || 'Erro ao carregar dados.' });
          }
          if (hasSensitiveShape(body) || !hasValidRowsShape(body)) {
            return Promise.reject({ state: 'BACKEND_ERROR', message: 'Resposta inesperada do servidor.' });
          }
          return body;
        });
      }, function () {
        return Promise.reject({ state: 'BACKEND_ERROR', message: 'Falha de rede.' });
      });
    });
  }

  // Both real RPCs fetched together (Gate B3 -- operational_metrics for
  // store/seller/department structures, operational_model_metrics for
  // model-level views, never feeding model presentation from
  // operational_metrics rows the way V1's own secure adapter does --
  // DASHBI_V1_MODEL_INTEGRATION_DEFECT_NOT_REPLICATED).
  function loadDashbiReal(params) {
    params = params || {};
    if (!params.start || !params.end) {
      return Promise.reject({ state: 'INVALID_FILTER', message: 'Informe um período válido.' });
    }
    return Promise.all([
      callRpc('operational_metrics', params.start, params.end),
      callRpc('operational_model_metrics', params.start, params.end)
    ]).then(function (results) {
      return { metrics: results[0], modelMetrics: results[1] };
    });
  }

  window.NX_DASHBI_REAL_PROVIDER = {
    loadDashbiReal: loadDashbiReal
  };
})();