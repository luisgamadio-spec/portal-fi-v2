/* PORTAL-NEXT V2 -- Painel Master / Configurações REAL data provider
   (Painel Master Phase PM-5E).

   THIN transport boundary, same principle and shape as every sibling
   Painel Master provider -- own independent callRpc(), no shared
   coupling to any other admin concern's fetch lifecycle.

   Real contract (PM-5E forensics): exactly 2 real, already-deployed
   RPCs -- `operational_portal_config()` (read, general-authenticated,
   NOT MASTER-only -- every profile's own dashboard reads the same
   commission-tier constants) and `master_update_portal_config(p_key,
   p_value, p_description)` (write, confirmed MASTER-only both via a
   real `usuarios`/`perfil='MASTER'` check inside the function body AND
   via RLS on the underlying `public.configuracoes` table -- read live
   via pg_get_functiondef, not assumed). The write RPC independently
   re-validates the exact 13-key allowlist server-side (this file's own
   CONFIG_KEYS list is for display/UX only, never the authority) plus a
   numeric range (0-1e9) and, for any key whose name contains "share"/
   "percentual"/"faixa", an additional 0-100 cap -- and writes a real,
   human-readable before/after row into `public.auditoria` on every
   successful save.

   NO HOMOLOGATION-MODE GATE EXISTS FOR THIS CAPABILITY (PM-5E Gate 39
   finding, confirmed by direct code reading of the live RPC and of
   every V1 call site -- unlike Gestão de Bases/Simuladores, there is no
   hostname allowlist, no dry-run concept, no write-simulation anywhere
   in this contract). A save through this provider on ANY host,
   including localhost, is a REAL write against the real backend. This
   file does not fabricate a safety net V1 itself does not have --
   automated tests must mock this provider's transport at the network
   layer (never calling the real RPC), exactly as done here. */
(function () {
  'use strict';

  function classifyError(code, httpStatus) {
    if (code === '42501') return 'AUTH_DENIED';
    if (httpStatus === 401 || httpStatus === 403) return 'SESSION_EXPIRED';
    return 'RPC_ERROR';
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
            return Promise.reject({ state: classifyError(code, resp.status), codigo: code, message: (body && body.message) || 'Erro ao processar solicitação.' });
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

  function readConfig(params) {
    params = params || {};
    return callRpc('operational_portal_config', {}, params.signal).then(function (data) {
      if (!data || !Array.isArray(data.rows)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data.rows;
    });
  }

  function updateConfig(key, value, description, params) {
    params = params || {};
    return callRpc('master_update_portal_config', {
      p_key: key, p_value: value, p_description: description || ''
    }, params.signal);
  }

  window.NX_MASTER_CONFIG_PROVIDER = {
    readConfig: readConfig,
    updateConfig: updateConfig
  };
})();
