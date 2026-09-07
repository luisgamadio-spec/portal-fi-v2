/* PORTAL-NEXT V2 -- Painel Master / Histórico de Competências REAL data
   provider (Painel Master Phase PM-5H).

   THIN transport boundary, same shape as every sibling Painel Master
   provider. THIS PROVIDER IS STRICTLY READ-ONLY -- it exposes exactly
   3 functions, all of them reads (or a server-side fail-closed guard
   that itself never writes), and calls exactly 3 real RPCs:

     - master_commission_closings() -- lists every fechamentos_comissao
       row (all periods, all versions, both FECHADO and REABERTO).
     - master_commission_snapshot(p_closing_id) -- the frozen
       snapshot_comissoes rows for one specific closing.
     - master_commission_snapshot_export(p_closing_id) -- same data as
       above, but FAILS CLOSED (real 22023 error, never a silent empty
       result) when the snapshot is structurally inconsistent (all
       rows comissao=0 AND detalhes IS NULL, or zero rows) -- used
       ONLY for the official Export action, never for the viewer.

   Contract for these 3 functions was reconstructed in PM-5G/PM-5H from
   real, git-tracked SQL (master_commission_snapshot_export's full body
   is readable verbatim in portal-financiamento-brabus-secure's
   supabase/migrations/20260824040000_incidente_p2_rhdp_failclosed_
   snapshot_inconsistente.sql) and from real, already-ground-truth-
   audited production TypeScript that consumes the other two
   (supabase/functions/portal-ai/index.ts, "Fase IA-2C.5 -- Salários,
   Comissões e Competências", which documents the exact real return
   shape of both `master_commission_closings` and
   `master_commission_snapshot` field-by-field). The literal SQL bodies
   of `master_commission_closings`/`master_commission_snapshot`
   themselves are NOT in Git (confirmed absent by exhaustive grep across
   all 68 migrations) and this session has no live database/Management
   API/service-role credential available to inspect them directly
   (documented limitation, PM-5G/PM-5H final reports) -- their MASTER-
   only gating is inferred with high confidence from the zero-exception
   naming/security convention shared by every other `master_*` RPC
   whose body IS available (all of them, without a single counter-
   example, start with an inline `perfil='MASTER'`/`is_master()` check)
   plus the portal-ai edge function's own independent, service-role-
   verified MASTER gate for this exact data domain -- never assumed
   without stating this explicitly.

   Never call master_close_commission_period, master_reopen_commission_
   period, master_admin_manage, or any write/mutation RPC from this
   file -- enforced structurally by this file simply never importing/
   referencing them (see tests/master-competence-history-provider-
   test.py's read-only-proof check, which asserts on this file's own
   source text). */
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

  function listClosings(params) {
    params = params || {};
    return callRpc('master_commission_closings', {}, params.signal).then(function (data) {
      if (!data || !Array.isArray(data.rows)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data.rows;
    });
  }

  function getSnapshot(closingId, params) {
    params = params || {};
    return callRpc('master_commission_snapshot', { p_closing_id: closingId }, params.signal).then(function (data) {
      if (!data || !Array.isArray(data.rows)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data.rows;
    });
  }

  // Deliberately a SEPARATE call from getSnapshot -- never reuse
  // getSnapshot's (unguarded) rows for an official export. The real
  // fail-closed check lives server-side inside this RPC (raises a real
  // 22023 when every row is comissao=0 AND detalhes IS NULL, or when
  // there are zero rows) -- this function passes that rejection
  // through untouched, it never retries with getSnapshot as a
  // fallback.
  function exportSnapshot(closingId, params) {
    params = params || {};
    return callRpc('master_commission_snapshot_export', { p_closing_id: closingId }, params.signal).then(function (data) {
      if (!data || !Array.isArray(data.rows)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data.rows;
    });
  }

  window.NX_MASTER_COMPETENCE_HISTORY_PROVIDER = {
    listClosings: listClosings,
    getSnapshot: getSnapshot,
    exportSnapshot: exportSnapshot
  };
})();
