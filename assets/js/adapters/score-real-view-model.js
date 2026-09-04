/* PORTAL-NEXT V2 -- Score REAL view-model mapping (Real Data Integration
   Foundation, Score Phase 2A, Gate 5).

   Reshapes the real operational_score_coparticipated_data payload into
   the SAME {sales, fins} shape score.adapter.js's own compute()
   already accepts for fixtures -- so the frozen calcScores() and
   score.js's existing render functions run UNCHANGED against either
   transport.

   Field mapping (Gate 5, exact contract -- calcScores() itself reads
   nothing beyond these fields, confirmed Phase 1 Gate 5/6):
     sales:   seller->vendedor, store->loja, department->dept,
              model->familia (via score.adapter.js's frozen
              familiaModelo(), NOT reimplemented here)
     finance: seller->vendedor, store->loja, department->dept,
              financed_value->valorFinanciado, return_value->retorno,
              spf_value->receitaSPF, spf_count->spfQtd, plan->plano

   Privacy minimization (Gate 13): fields the real RPC carries but
   calcScores()/score.js never read (operation_reference, sale_value,
   installments, installment_value, balloon_value, status, client
   identity) are deliberately NOT copied into the mapped output at all
   -- omission by construction, not a filter applied after the fact.

   Department mapping is strict (Gate 5): NOVOS/SEMINOVOS are the only
   accepted real values; anything else throws a MALFORMED_RESPONSE
   diagnostic rather than silently passing an unmapped value through to
   the frozen engine's own department-keyed weight lookup. */
(function () {
  'use strict';

  var DEPT_MAP = { NOVOS: 'Novos', SEMINOVOS: 'Seminovos' };

  function mapDept(d) {
    var mapped = DEPT_MAP[d];
    if (!mapped) {
      var err = new Error('Departamento inesperado no payload real: ' + JSON.stringify(d));
      err.state = 'MALFORMED_RESPONSE';
      throw err;
    }
    return mapped;
  }

  function buildSales(rawSales) {
    var A = window.NX_SCORE_ADAPTER;
    return (rawSales || []).map(function (r) {
      return {
        vendedor: r.seller || '',
        loja: r.store || '',
        dept: mapDept(r.department),
        // Gate 8 (Phase 1): familiaModelo() is proven to operate
        // correctly on the RAW model string -- no canonicalization step.
        familia: A._internal.familiaModelo(r.model)
      };
    });
  }

  function buildFins(rawFinance) {
    return (rawFinance || []).map(function (r) {
      return {
        vendedor: r.seller || '',
        loja: r.store || '',
        dept: mapDept(r.department),
        valorFinanciado: Number(r.financed_value) || 0,
        retorno: Number(r.return_value) || 0,
        receitaSPF: Number(r.spf_value) || 0,
        spfQtd: Number(r.spf_count) || 0,
        plano: r.plan || 'LINEAR'
      };
    });
  }

  function buildRealResult(payload) {
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

  window.NX_SCORE_REAL_VIEW_MODEL = {
    buildRealResult: buildRealResult
  };
})();
