/* PORTAL-NEXT V2 -- Painel Master / Mudança de Loja - Vendedores REAL
   data provider (Painel Master Phase PM-5F).

   THIN transport boundary, same shape as every sibling Painel Master
   provider (see master-periodos-provider.js / master-absences-
   provider.js, the direct structural templates). Real contract,
   confirmed live by direct pg_get_functiondef inspection of the real
   backend in production project yacqlelpzchcotgngwbh: MASTER reads
   via `master_admin_reference_data()` (`.store_changes`); writes go
   through `master_admin_manage(p_entity='STORE_CHANGE', p_action,
   p_payload)` -- the SAME dispatcher already used by PERIOD/ABSENCE,
   confirmed byte-identical across both live-fetch attempts this
   phase. MASTER-only, backed by RLS on
   `public.mudancas_loja_vendedores` (INSERT/UPDATE both require
   is_master(); SELECT open to any authenticated profile -- several
   real commission/salary RPCs for other profiles read this table via
   resolve_store_temporal()).

   Payload keys below are the EXACT keys the live RPC body reads
   (pg_get_functiondef-confirmed, PM-5F Gate 34/35): seller_cpf,
   seller_login, seller_name, origin_store, destination_store,
   origin_start, origin_end, destination_start, notes,
   origin_department, destination_department. `notes` IS persisted
   here (unlike ABSENCE's dropped `observacao`).

   STRICT FORWARD-ONLY CHAIN MODEL (real, server-enforced, confirmed
   live -- not inferred from V1 UI copy): destination_start must be
   EXACTLY the day after origin_end (no gap, no overlap); the seller's
   most recent existing record (by data_inicio_destino desc, matched
   by CPF then exact name) constrains the new record's origin_store
   (must equal that record's loja_destino exactly), origin_start (not
   before that record's destination start), destination_start (must be
   strictly after it), and origin_department (must match that record's
   destination department if one is set). Old records are NEVER
   deactivated by a new one. `checkChainGuidance` below mirrors this
   purely for UX pre-check guidance (never authoritative -- the RPC
   re-validates regardless and is the only real gate). The real
   conflict error code for a chain violation is Postgres '23P01',
   mapped to the CONFLICT UI state below (distinct from '22023'
   generic validation and '42501' auth-denied).

   departamento_origem/departamento_destino are validated server-side
   against a HARD enum -- only 'NOVOS' or 'SEMINOVOS' (or empty/null)
   are accepted; anything else raises 22023. This is not a free-text
   field despite the underlying column being plain `text`.

   NO HOMOLOGATION-MODE GATE EXISTS FOR THIS CAPABILITY (independently
   confirmed live this phase for STORE_CHANGE specifically) -- every
   write here is REAL on any host, including localhost. Automated
   tests must mock this provider's transport at the network layer. */
(function () {
  'use strict';

  function classifyError(code, httpStatus) {
    if (code === '42501') return 'AUTH_DENIED';
    if (code === '23P01') return 'CONFLICT'; // real chain-validation conflict
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

  function listStoreChanges(params) {
    params = params || {};
    return callRpc('master_admin_reference_data', {}, params.signal).then(function (data) {
      if (!data || !Array.isArray(data.store_changes)) {
        return Promise.reject({ state: 'MALFORMED_RESPONSE', message: 'Resposta inesperada do servidor.' });
      }
      return data.store_changes;
    });
  }

  function manage(action, payload, params) {
    params = params || {};
    return callRpc('master_admin_manage', { p_entity: 'STORE_CHANGE', p_action: action, p_payload: payload || {} }, params.signal);
  }

  function createStoreChange(fields, params) {
    return manage('CREATE', {
      seller_cpf: fields.cpfVendedor,
      seller_login: fields.loginVendedor,
      seller_name: fields.nomeVendedor,
      origin_store: fields.lojaOrigem,
      destination_store: fields.lojaDestino,
      origin_start: fields.dataInicioOrigem,
      origin_end: fields.dataFimOrigem,
      destination_start: fields.dataInicioDestino,
      notes: fields.observacao,
      origin_department: fields.departamentoOrigem,
      destination_department: fields.departamentoDestino
    }, params);
  }
  function setDepartments(id, originDepartment, destinationDepartment, params) {
    return manage('SET_DEPARTMENTS', { id: id, origin_department: originDepartment, destination_department: destinationDepartment }, params);
  }
  function setActive(id, active, params) {
    return manage('SET_ACTIVE', { id: id, active: !!active }, params);
  }
  function archiveStoreChange(id, params) {
    return manage('ARCHIVE', { id: id }, params);
  }

  window.NX_MASTER_STORE_CHANGE_PROVIDER = {
    listStoreChanges: listStoreChanges,
    createStoreChange: createStoreChange,
    setDepartments: setDepartments,
    setActive: setActive,
    archiveStoreChange: archiveStoreChange
  };
})();
