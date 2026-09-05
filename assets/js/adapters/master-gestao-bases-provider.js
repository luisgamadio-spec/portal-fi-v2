/* PORTAL-NEXT V2 -- Painel Master / Gestão de Bases REAL data provider
   (Painel Master Phase PM-5C).

   THIN transport boundary, same principle and shape as
   master-pendencias-provider.js/master-audit-provider.js/master-users-
   provider.js/master-acessos-provider.js -- own independent callRpc(),
   no shared coupling to any other admin concern's fetch lifecycle.

   Real contract (PM-5C forensics, docs/MASTER-GESTAO-BASES-RPC-
   CONTRACT-CAPTURE.md): 8 real, already-deployed, already-audited
   MASTER-only RPCs recovered live from production (pg_get_functiondef,
   read-only) since most predate this repo's migration history and
   were never committed to Git (same 74/135-function gap documented in
   supabase/baseline/README.md) -- no new backend, no RPC created or
   wrapped here. All 5 underlying tables (portal_import_batches,
   portal_sales, portal_finance_operations, portal_spf_operations,
   portal_sellers) are RLS-enabled with ZERO policies defined -- direct
   table access is denied outright for every role; every call below
   goes through an RPC name, never a `.from(...)` table reference, and
   every RPC independently re-checks `is_master()` server-side
   regardless of anything this file or the router does (defense in
   depth, confirmed by direct inspection of each function body, not
   assumed).

   `master_operational_import_spf` and `master_operational_enrich_
   analytics` are deliberately NOT exposed here: V1's own frontend
   never calls them directly either (import_spf is only ever invoked
   server-side, from inside applyBase03's own transaction;
   enrich_analytics is confirmed dead code, superseded by applyBase03,
   per master-gestao-bases.js's own comment in the legacy app) --
   exposing them here would be inventing a second, unused call path.

   Business-level failures are NOT a `{ok:false}` JSON body here (this
   RPC family raises real Postgres exceptions via `raise exception ...
   using errcode = ...`, unlike Pendências' `{ok, codigo}` convention)
   -- they surface as a normal PostgREST HTTP error, already handled by
   classifyError/the non-ok branch below; `body.message` is the real,
   already-human-language backend text (Portuguese), passed through
   verbatim, never re-worded or replaced with a raw stack trace.

   HOMOLOGATION MODE (Gate 36/38/65 -- ported verbatim from V1's own
   already-proven safety mechanism, master-gestao-bases.js's gbRpc/
   GB_HOMOLOGATION_MODE): this whole RPC family writes real operational
   data (sales/finance/SPF/sellers), and V1 already solved "how do you
   let someone safely click through the entire import flow, including
   Confirmar, without ever risking a real write" with a deny-by-default
   gate keyed on the exact production hostname -- not a client-guessed
   "am I in a test" flag. Any hostname other than the real production
   ones (the SAME Supabase project backs both V1 and V2, so V1's own
   proven allowlist is reused unchanged, not re-invented) auto-simulates
   every write RPC and returns a plausible same-shaped fake response,
   logging a console.warn -- never reaching the network. This makes the
   Human's own local V2 UAT (localhost, the established dev-server
   convention) automatically non-destructive by construction, even if a
   real production file is selected, and makes every automated test in
   this codebase's harness (never running on those hostnames) safe by
   the same construction, not merely by convention/care. */
(function () {
  'use strict';

  var GB_PRODUCTION_HOSTS = ['luisgamadio-spec.github.io', 'brabus.blistiq.com.br'];
  function gbIsProductionHost() {
    var h = ((typeof location !== 'undefined' && location.hostname) || '').toLowerCase();
    return GB_PRODUCTION_HOSTS.indexOf(h) !== -1;
  }
  var GB_HOMOLOGATION_MODE = !gbIsProductionHost();
  var GB_WRITE_RPC_NAMES = {
    master_operational_begin_import: true,
    master_operational_import_sales: true,
    master_operational_import_finance: true,
    master_operational_import_sellers: true,
    master_operational_finalize_import: true
  };
  function gbIsBlockedWrite(name, params) {
    if (GB_WRITE_RPC_NAMES[name]) return true;
    // apply_base03 só escreve quando dryRun !== true -- a leitura
    // (diagnóstico prévio) continua liberada mesmo em homologação.
    if (name === 'master_operational_apply_base03' && params && params.p_dry_run !== true) return true;
    return false;
  }
  function gbSimulateWrite(name, params) {
    if (typeof console !== 'undefined' && console.warn) {
      console.warn('[Gestão de Bases] MODO HOMOLOGAÇÃO — escrita bloqueada: ' + name, params);
    }
    var fakeUuid = '00000000-0000-4000-8000-' + Math.random().toString(16).slice(2).padEnd(12, '0').slice(0, 12);
    switch (name) {
      case 'master_operational_begin_import':
        return fakeUuid;
      case 'master_operational_import_sales':
      case 'master_operational_import_finance':
      case 'master_operational_import_sellers':
        return Array.isArray(params && params.p_rows) ? params.p_rows.length : 0;
      case 'master_operational_finalize_import':
        return true;
      case 'master_operational_apply_base03':
        return {
          dry_run: false, simulated: true,
          finance_batch_id: fakeUuid, finance_rows_matched: 0,
          spf_batch_id: fakeUuid, spf_rows_received: 0, spf_accepted: 0, spf_rejected: 0
        };
      default:
        return null;
    }
  }

  function classifyError(code, httpStatus) {
    if (code === '42501') return 'AUTH_DENIED';
    if (httpStatus === 401 || httpStatus === 403) return 'SESSION_EXPIRED';
    return 'RPC_ERROR';
  }

  var DEFAULT_TIMEOUT_MS = 20000;

  function callRpc(fnName, params, signal) {
    if (GB_HOMOLOGATION_MODE && gbIsBlockedWrite(fnName, params)) {
      return Promise.resolve(gbSimulateWrite(fnName, params));
    }
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

  // ---------- batches (begin/finalize triad — Bases 01/02/Colaboradores) ----------
  function beginImport(sourceType, originalFilename, sourceSha256, rowsRead, params) {
    params = params || {};
    return callRpc('master_operational_begin_import', {
      p_source_type: sourceType, p_original_filename: originalFilename,
      p_source_sha256: sourceSha256, p_rows_read: rowsRead
    }, params.signal);
  }

  function importSales(batchId, rows, params) {
    params = params || {};
    return callRpc('master_operational_import_sales', { p_batch_id: batchId, p_rows: rows }, params.signal);
  }

  function importFinance(batchId, rows, params) {
    params = params || {};
    return callRpc('master_operational_import_finance', { p_batch_id: batchId, p_rows: rows }, params.signal);
  }

  function importSellers(batchId, rows, params) {
    params = params || {};
    return callRpc('master_operational_import_sellers', { p_batch_id: batchId, p_rows: rows }, params.signal);
  }

  function finalizeImport(batchId, rowsAccepted, rowsRejected, validationMessage, params) {
    params = params || {};
    return callRpc('master_operational_finalize_import', {
      p_batch_id: batchId, p_rows_accepted: rowsAccepted, p_rows_rejected: rowsRejected,
      p_validation_message: validationMessage || null
    }, params.signal);
  }

  // ---------- Base 03 (single atomic dry-run/commit call) ----------
  function applyBase03(originalFilename, sourceSha256, financeRows, spfRows, dryRun, params) {
    params = params || {};
    return callRpc('master_operational_apply_base03', {
      p_original_filename: originalFilename, p_source_sha256: sourceSha256,
      p_finance_rows: financeRows, p_spf_rows: spfRows, p_dry_run: !!dryRun
    }, params.signal);
  }

  // ---------- read/status ----------
  function hasValidBatchesShape(data) {
    return Array.isArray(data);
  }

  function listBatches(params) {
    params = params || {};
    return callRpc('master_operational_list_batches', {}, params.signal).then(function (data) {
      if (!hasValidBatchesShape(data)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data;
    });
  }

  function listSellers(params) {
    params = params || {};
    return callRpc('master_operational_list_sellers', {}, params.signal).then(function (data) {
      if (!hasValidBatchesShape(data)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data;
    });
  }

  function listSpfExtraBase02(params) {
    params = params || {};
    return callRpc('master_operational_list_spf_extra_base02', {}, params.signal).then(function (data) {
      if (!hasValidBatchesShape(data)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data;
    });
  }

  window.NX_MASTER_GESTAO_BASES_PROVIDER = {
    beginImport: beginImport,
    importSales: importSales,
    importFinance: importFinance,
    importSellers: importSellers,
    finalizeImport: finalizeImport,
    applyBase03: applyBase03,
    listBatches: listBatches,
    listSellers: listSellers,
    listSpfExtraBase02: listSpfExtraBase02,
    isHomologationMode: function () { return GB_HOMOLOGATION_MODE; }
  };
})();
