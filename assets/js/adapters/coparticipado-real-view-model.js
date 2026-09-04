/* PORTAL-NEXT V2 -- Coparticipado REAL view-model mapping (Real Data
   Integration Foundation, Coparticipado Phase 2, Gate 13/14/15/16).

   Reshapes the real operational_score_coparticipated_data payload into
   the SAME {sales, fins} shape coparticipado.adapter.js's own compute()
   already produces for fixtures -- so coparticipado.js's existing
   render functions (renderCoparticipadosTable/renderSubsidiadosTable/
   populateStoreOptions/applyFilters) run UNCHANGED against either
   transport.

   Unlike Gestão (synthetic per-unit reconstruction) or Dashbi (a
   hybrid), this is a DIRECT, row-for-row mapping: the real RPC already
   returns one JSON record per financing operation (Phase 1B, Gate 5 --
   proven the canonical record grain), fully classified and matched
   server-side. This file therefore does NOT call, and must NEVER call,
   classifyPlan()/matchB3()/buildB3Index()/processFins()/processSales()/
   isTCcoparticipado()/isSituacaoCoparticipadoValida() -- those remain
   fixture/historical-parity code only (Phase 1B, Gate 4/14). `plano`
   comes directly from the server's own `plan` field, unmodified.

   Privacy (Gate 14): the real backend deliberately never returns client
   identity (contains_client_identity: false) or a full chassis
   (contains_full_chassis: false) -- matching real V1 production's own
   secure adapter (score-coparticipated-secure-adapter.js), cliente is
   hardcoded to "Operação protegida" and chassi/chassiResumido both use
   only the server-masked operation_reference, verbatim, never combined
   or derived to approximate a real identity/chassis.

   Rebate/Coparticipação (Gate 16): reuses the existing, already-
   extracted, formula-frozen calcCoparticipacaoDetalhe()/findTaxaCopart()
   over the real finance[]+rates[] arrays -- proven still legitimately
   client-side in real V1 production itself (Phase 1, Gate 7), not a
   reclassification. DATA.taxasCopart is populated from the real
   rates[] array using the same taxaKey() the fixture engine's own
   findTaxaCopart() will use internally to look them back up. */
(function () {
  'use strict';

  var DEPT_MAP = { NOVOS: 'Novos', SEMINOVOS: 'Seminovos' };
  function mapDept(d) { return DEPT_MAP[d] || d; }

  // Same defensive percent-or-fraction normalization real V1 production's
  // own secure adapter applies to total_rebate/brabus_percent (rate() in
  // score-coparticipated-secure-adapter.js) -- not a new rule.
  function rate(v) {
    var n = Number(v) || 0;
    return n > 1 ? n / 100 : n;
  }

  function buildTaxasCopart(rawRates) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    var lookup = {};
    (rawRates || []).forEach(function (r) {
      var key = A.taxaKey(r.model);
      if (key) {
        lookup[key] = {
          modeloTabela: r.model,
          rebateTotal: rate(r.total_rebate),
          parteBrabus: rate(r.brabus_percent),
          linha: 0
        };
      }
    });
    return lookup;
  }

  function buildSales(rawSales) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    return (rawSales || []).map(function (r) {
      return {
        cliente: 'Operação protegida',
        vendedor: r.seller || '',
        loja: r.store || '',
        dept: mapDept(r.department),
        modelo: r.model || 'NÃO INFORMADO',
        valorVenda: Number(r.sale_value) || 0,
        chassi: r.operation_reference || '',
        chassiResumido: r.operation_reference || '',
        data: A.parseDate(r.date)
      };
    });
  }

  function buildFins(rawFinance) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    return (rawFinance || []).map(function (r) {
      var fin = {
        cliente: 'Operação protegida',
        vendedor: r.seller || '',
        loja: r.store || '',
        dept: mapDept(r.department),
        modelo: r.model || 'NÃO INFORMADO',
        valorFinanciado: Number(r.financed_value) || 0,
        retorno: Number(r.return_value) || 0,
        receitaSPF: Number(r.spf_value) || 0,
        spfQtd: Number(r.spf_count) || 0,
        parcelas: Number(r.installments) || 0,
        pmt: Number(r.installment_value) || 0,
        balaoValor: r.plan === 'BALÃO' ? (Number(r.balloon_value) || 0) : 0,
        // Gate 15 -- server-authoritative, never reclassified client-side.
        plano: r.plan || 'LINEAR',
        situacaoB3: r.status || '',
        matchedB3: true,
        chassi: r.operation_reference || '',
        chassiResumido: r.operation_reference || '',
        data: A.parseDate(r.date)
      };
      if (fin.plano === 'COPARTICIPADO') {
        fin.coparticipacaoDetalhe = A.calcCoparticipacaoDetalhe(fin);
      }
      return fin;
    });
  }

  function buildRealResult(payload) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    // Must run before buildFins(): calcCoparticipacaoDetalhe()/
    // findTaxaCopart() read DATA.taxasCopart internally, not as a
    // parameter (same module-level-state contract the fixture path
    // already relies on via compute()).
    A.setTaxasCopart(buildTaxasCopart(payload.rates));
    return {
      sales: buildSales(payload.sales),
      fins: buildFins(payload.finance),
      sourceInfo: {
        source: 'REAL_BACKEND',
        scope: payload.scope,
        period_start: payload.period_start,
        period_end: payload.period_end
      }
    };
  }

  window.NX_COPARTICIPADO_REAL_VIEW_MODEL = {
    buildRealResult: buildRealResult
  };
})();
