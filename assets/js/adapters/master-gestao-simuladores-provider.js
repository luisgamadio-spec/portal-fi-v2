/* PORTAL-NEXT V2 -- Painel Master / Gestão dos Simuladores REAL data
   provider (Painel Master Phase PM-5D).

   THIN transport boundary, same principle and shape as
   master-gestao-bases-provider.js -- own independent callRpc(), no
   shared coupling to any other admin concern's fetch lifecycle.

   Real contract (PM-5D forensics): 10 write RPCs (one is overloaded --
   master_simulador_commit_coparticipado has a 6-arg AND a 7-arg
   signature live in production; this file ALWAYS sends p_linhas_
   coeficiente as an explicit key, even when empty, so PostgREST always
   resolves the 7-arg overload -- the exact same shape V1's own
   montarArgs always sends, never the ambiguous 6-arg one) + 1 read
   (master_simulador_listar_bases), recovered live from production via
   pg_get_functiondef (read-only) since NONE of these 11 functions, nor
   the 10 underlying simulador_* tables, exist anywhere in this
   codebase's Git history (a bigger gap than Gestão de Bases' own 74/
   135-function gap -- here it is the entire capability). Every commit
   RPC was individually confirmed to start with `if not is_master()
   then raise exception ... '42501'`, and all 10 underlying tables have
   RLS enabled with ZERO policies -- direct table access denied for
   every role, same proven pattern as Gestão de Bases.

   HOMOLOGATION MODE: ported verbatim from V1's own already-proven
   mechanism (master-gestao-simuladores.js's gsRpc/GS_HOMOLOGATION_MODE)
   -- identical hostname allowlist, identical rule (every REAL write is
   blocked off the two real production hosts; a dry-run, p_dry_run:true,
   is a pure read and is NEVER blocked, matching the real RPC bodies
   confirmed live: the dry-run branch never reaches an INSERT/UPDATE
   statement in any of them). This makes local/test environments
   non-destructive by construction, exactly as it does for Gestão de
   Bases -- confirmed independently for this capability, not assumed. */
(function () {
  'use strict';

  var GS_PRODUCTION_HOSTS = ['luisgamadio-spec.github.io', 'brabus.blistiq.com.br'];
  function gsIsProductionHost() {
    var h = ((typeof location !== 'undefined' && location.hostname) || '').toLowerCase();
    return GS_PRODUCTION_HOSTS.indexOf(h) !== -1;
  }
  var GS_HOMOLOGATION_MODE = !gsIsProductionHost();
  var GS_COMMIT_RPC_NAMES = {
    master_simulador_commit_linear: true,
    master_simulador_commit_taxas_subsidiadas: true,
    master_simulador_commit_taxa_botao: true,
    master_simulador_commit_balao_zerokm: true,
    master_simulador_commit_balao_seminovos: true,
    master_simulador_commit_antecipacao: true,
    master_simulador_commit_financiamento_seminovo: true,
    master_simulador_commit_coparticipado: true,
    master_simulador_commit_semestral_triton_outlander: true,
    master_simulador_commit_coeficientes_coparticipado: true
  };
  // dry-run (read, never writes) stays allowed even in homologation --
  // only a real write (p_dry_run !== true) is intercepted.
  function gsIsBlockedWrite(name, params) {
    return !!GS_COMMIT_RPC_NAMES[name] && !(params && params.p_dry_run === true);
  }
  function gsSimulateWrite(name, params) {
    if (typeof console !== 'undefined' && console.warn) {
      console.warn('[Gestão dos Simuladores] MODO HOMOLOGAÇÃO — escrita bloqueada: ' + name, params);
    }
    var fakeUuid = '00000000-0000-4000-8000-' + Math.random().toString(16).slice(2).padEnd(12, '0').slice(0, 12);
    return { ok: true, simulated: true, batch_id: fakeUuid };
  }

  function classifyError(code, httpStatus) {
    if (code === '42501') return 'AUTH_DENIED';
    if (httpStatus === 401 || httpStatus === 403) return 'SESSION_EXPIRED';
    return 'RPC_ERROR';
  }

  var DEFAULT_TIMEOUT_MS = 20000;

  function callRpc(fnName, params, signal) {
    if (GS_HOMOLOGATION_MODE && gsIsBlockedWrite(fnName, params)) {
      return Promise.resolve(gsSimulateWrite(fnName, params));
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

  // ---------- status/read ----------
  function listarBases(params) {
    params = params || {};
    return callRpc('master_simulador_listar_bases', {}, params.signal).then(function (data) {
      if (!Array.isArray(data)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data;
    });
  }

  // ---------- commit (each called twice by the controller: dry_run
  // true for preview, then false after explicit confirm) ----------
  function commitLinear(args, params) { params = params || {}; return callRpc('master_simulador_commit_linear', args, params.signal); }
  function commitTaxasSubsidiadas(args, params) { params = params || {}; return callRpc('master_simulador_commit_taxas_subsidiadas', args, params.signal); }
  function commitTaxaBotao(args, params) { params = params || {}; return callRpc('master_simulador_commit_taxa_botao', args, params.signal); }
  function commitBalaoZeroKm(args, params) { params = params || {}; return callRpc('master_simulador_commit_balao_zerokm', args, params.signal); }
  function commitBalaoSeminovos(args, params) { params = params || {}; return callRpc('master_simulador_commit_balao_seminovos', args, params.signal); }
  function commitAntecipacao(args, params) { params = params || {}; return callRpc('master_simulador_commit_antecipacao', args, params.signal); }
  function commitFinanciamentoSeminovo(args, params) { params = params || {}; return callRpc('master_simulador_commit_financiamento_seminovo', args, params.signal); }
  function commitCoparticipado(args, params) {
    params = params || {};
    // Always include p_linhas_coeficiente explicitly (even []) -- the
    // exact V1 behavior (montarArgs) that deterministically resolves
    // PostgREST to the 7-arg overload, never the ambiguous 6-arg one.
    var full = Object.assign({ p_linhas_coeficiente: [] }, args);
    return callRpc('master_simulador_commit_coparticipado', full, params.signal);
  }
  function commitSemestralTritonOutlander(args, params) { params = params || {}; return callRpc('master_simulador_commit_semestral_triton_outlander', args, params.signal); }
  function commitCoeficientesCoparticipado(args, params) { params = params || {}; return callRpc('master_simulador_commit_coeficientes_coparticipado', args, params.signal); }

  var RPC_BY_NAME = {
    master_simulador_commit_linear: commitLinear,
    master_simulador_commit_taxas_subsidiadas: commitTaxasSubsidiadas,
    master_simulador_commit_taxa_botao: commitTaxaBotao,
    master_simulador_commit_balao_zerokm: commitBalaoZeroKm,
    master_simulador_commit_balao_seminovos: commitBalaoSeminovos,
    master_simulador_commit_antecipacao: commitAntecipacao,
    master_simulador_commit_financiamento_seminovo: commitFinanciamentoSeminovo,
    master_simulador_commit_coparticipado: commitCoparticipado,
    master_simulador_commit_semestral_triton_outlander: commitSemestralTritonOutlander,
    master_simulador_commit_coeficientes_coparticipado: commitCoeficientesCoparticipado
  };
  // Generic dispatch by RPC name (the view-model's catalog names the RPC
  // per family; this avoids a second, parallel name->function map living
  // in shell-admin.js that could silently drift from this one).
  function commit(rpcName, args, params) {
    var fn = RPC_BY_NAME[rpcName];
    if (!fn) return Promise.reject({ state: 'RPC_ERROR', message: 'RPC de simulador desconhecida: ' + rpcName });
    return fn(args, params);
  }

  window.NX_MASTER_GESTAO_SIMULADORES_PROVIDER = {
    listarBases: listarBases,
    commit: commit,
    isHomologationMode: function () { return GS_HOMOLOGATION_MODE; }
  };
})();
