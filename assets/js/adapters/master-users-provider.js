/* PORTAL-NEXT V2 -- Painel Master / Usuários REAL data provider
   (Painel Master Phase 2A).

   THIN transport boundary, same principle as every other real-provider
   in this codebase (gestao/dashbi/coparticipado/score-real-provider.js):
   this file's only job is calling the real, already-audited admin RPCs
   (Phase 0/1 audit; full bodies captured in
   docs/MASTER-USERS-RPC-CONTRACT-CAPTURE.md) and returning their raw
   payload (or a classified error) -- no PII minimization, no lifecycle
   derivation, no business decision. All of that lives in
   master-users-view-model.js. This file does not decide MASTER --
   every RPC below re-verifies server-side (is_master()/inline check)
   regardless of what the route guard (shell.js) already enforced.

   MUTATION FREEZE (Phase 2A, Gate 16/47): inviteUser/updateUserAuthorization/
   resendInvite below are fully wired against the real, audited RPC
   contract -- but this phase's own execution NEVER calls them for real
   (only exercised via mocked Playwright tests, tests/master-users-*.py).
   loadMasterUsersData is the one function actually invoked against the
   real backend this phase, and it is read-only.

   Reuses the EXISTING Auth Foundation session (window.NX_AUTH), same as
   every other real provider -- no independent Supabase client. */
(function () {
  'use strict';

  // Gate 22 runtime-state vocabulary (extended for Usuários' own
  // mutation-specific outcomes): LOADING/SUCCESS/EMPTY/AUTH_DENIED/
  // SESSION_EXPIRED/VALIDATION_ERROR/DUPLICATE_USER/CONFLICT/RPC_ERROR/
  // NETWORK_ERROR/TIMEOUT/MALFORMED_RESPONSE.
  function classifyError(code, httpStatus, message) {
    if (code === '42501') return 'AUTH_DENIED';
    if (code === '22023') return 'VALIDATION_ERROR';
    if (code === '23505') return 'DUPLICATE_USER';
    if (code === '55000') return 'CONFLICT'; // master_reenviar_convite's "already delivered" case
    if (code === 'P0002') return 'RPC_ERROR'; // not found
    if (httpStatus === 401 || httpStatus === 403) return 'SESSION_EXPIRED';
    return 'RPC_ERROR';
  }

  function hasValidUsersShape(data) {
    return !!data && typeof data === 'object' && Array.isArray(data.users);
  }

  var DEFAULT_TIMEOUT_MS = 15000;

  function callRpc(fnName, params, signal) {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (!cfg.supabaseUrl || !cfg.supabasePublishableKey) {
      return Promise.reject({ state: 'RPC_ERROR', message: 'Configuração real ausente neste ambiente.' });
    }
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      return Promise.reject({ state: 'SESSION_EXPIRED', message: 'Sessão indisponível.' });
    }

    return window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) return Promise.reject({ state: 'SESSION_EXPIRED', message: 'Sessão expirada.' });

      var timeoutController = null;
      var effectiveSignal = signal;
      if (!effectiveSignal && typeof AbortController === 'function') {
        timeoutController = new AbortController();
        effectiveSignal = timeoutController.signal;
      }
      var timer = timeoutController
        ? setTimeout(function () { timeoutController.abort(); }, DEFAULT_TIMEOUT_MS)
        : null;

      return fetch(cfg.supabaseUrl + '/rest/v1/rpc/' + fnName, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': cfg.supabasePublishableKey,
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(params || {}),
        signal: effectiveSignal
      }).then(function (resp) {
        if (timer) clearTimeout(timer);
        return resp.json().catch(function () { return null; }).then(function (body) {
          if (!resp.ok) {
            var code = body && body.code;
            return Promise.reject({ state: classifyError(code, resp.status, body && body.message), message: (body && body.message) || 'Erro ao processar solicitação.' });
          }
          return body;
        });
      }, function (err) {
        if (timer) clearTimeout(timer);
        if (err && err.name === 'AbortError') {
          if (signal && signal.aborted) return Promise.reject({ state: 'ABORTED', message: 'Requisição cancelada.' });
          return Promise.reject({ state: 'TIMEOUT', message: 'Tempo de resposta excedido.' });
        }
        return Promise.reject({ state: 'NETWORK_ERROR', message: 'Falha de rede.' });
      });
    });
  }

  // Read-only. The one function this phase actually calls against the
  // real backend (Gate 41). Merges master_admin_security_data()'s
  // `users` array with master_listar_convites()'s rows (matched by
  // usuario_id) so the view-model can derive invite/lifecycle state
  // without a second round-trip per row.
  function loadMasterUsersData(params) {
    params = params || {};
    return Promise.all([
      callRpc('master_admin_security_data', {}, params.signal),
      callRpc('master_listar_convites', {}, params.signal)
    ]).then(function (results) {
      var security = results[0];
      var convites = results[1];
      if (!hasValidUsersShape(security) || !Array.isArray(convites)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return { users: security.users, convites: convites };
    });
  }

  // WIRED, NOT EXECUTED THIS PHASE (Gate 16/47). Exact param shape per
  // docs/MASTER-USERS-RPC-CONTRACT-CAPTURE.md.
  function inviteUser(fields, params) {
    params = params || {};
    return callRpc('master_convidar_usuario', {
      p_cpf: fields.cpf, p_nome: fields.nome, p_perfil: fields.perfil,
      p_loja: fields.loja || null, p_email: fields.email,
      p_nbs: fields.nbs || null, p_status: fields.status || null
    }, params.signal);
  }

  // WIRED, NOT EXECUTED THIS PHASE. Full-row overwrite per the RPC's
  // own real contract -- caller must always send all 4 fields.
  function updateUserAuthorization(fields, params) {
    params = params || {};
    return callRpc('master_atualizar_autorizacao_usuario', {
      p_usuario_id: fields.usuarioId, p_perfil: fields.perfil,
      p_loja: fields.loja, p_status: fields.status, p_ativo: fields.ativo
    }, params.signal);
  }

  // WIRED, NOT EXECUTED THIS PHASE.
  function resendInvite(conviteId, params) {
    params = params || {};
    return callRpc('master_reenviar_convite', { p_convite_id: conviteId }, params.signal);
  }

  window.NX_MASTER_USERS_PROVIDER = {
    loadMasterUsersData: loadMasterUsersData,
    inviteUser: inviteUser,
    updateUserAuthorization: updateUserAuthorization,
    resendInvite: resendInvite
  };
})();