/* PORTAL-NEXT V2 -- Score REAL view-model mapping (Real Data Integration
   Foundation, Score Phase 2A, Gate 5).

   Reshapes the real operational_score_coparticipated_data payload into
   the SAME {sales, fins} shape score.adapter.js's own compute()
   already accepts for fixtures -- so the frozen calcScores() and
   score.js's existing render functions run UNCHANGED against either
   transport.

   Field mapping (Gate 5, exact contract -- calcScores() itself reads
   nothing beyond vendedor/loja/dept/familia/valorFinanciado/retorno/
   receitaSPF/spfQtd/plano, confirmed Phase 1 Gate 5/6):
     sales:   seller->vendedor, store->loja, department->dept,
              model->familia (via score.adapter.js's frozen
              familiaModelo(), NOT reimplemented here)
     finance: seller->vendedor, store->loja, department->dept,
              financed_value->valorFinanciado, return_value->retorno,
              spf_value->receitaSPF, spf_count->spfQtd, plan->plano

   FC-2.2 (GAP-003 real export, accepting FC-2.1's audit): modelo,
   cliente, chassi, data, parcelas, pmt, situacaoB3, valorVenda are now
   ALSO retained on the mapped sales/fins objects -- calcScores() still
   never reads them (the Gate 5 contract above is unchanged), they exist
   solely for score.js's exportCoparticipadosXlsx() to read later. FC-2.1
   proved this adds 0 new browser-side exposure: every one of these
   fields (or its masked equivalent) is already sent by this exact RPC to
   this exact caller today and already retained, field-for-field, by the
   sibling coparticipado-real-view-model.js's own buildSales()/buildFins()
   -- this mapping mirrors that proven one exactly, not a new
   representation:
     modelo:     r.model, RAW, no re-normalization (rate-table lookup's
                 own taxaKey() normalizes internally, same as Coparticipado)
     cliente:    hardcoded 'Operação protegida' -- the real RPC has no
                 client-identity field at all (contains_client_identity is
                 always false here); this is V1's own real production
                 masking convention, not new
     chassi:     r.operation_reference, a backend-masked reference, NEVER
                 a real chassis/VIN (contains_full_chassis is always
                 false) -- preserved verbatim, never combined/derived
     data:       parsed via the SAME window.NX_COPARTICIPADO_ADAPTER.
                 parseDate() Coparticipado's own real view-model already
                 uses -- reused, not reimplemented
     parcelas/pmt/situacaoB3/valorVenda: raw numeric/string pass-through,
                 same as Coparticipado's own mapping
     familia (on fins too, not just sales): matches V1's OWN real secure
                 adapter (score-coparticipated-secure-adapter.js), which
                 computes familia on finance records as well -- needed by
                 GAP-003's "Família do carro" column

   The original privacy-minimization comment this replaces was about
   scope discipline for calcScores() (the only consumer that existed on
   2026-09-04) -- not a decision that these fields were unsafe. FC-2.1's
   full reconstruction is in the FC-2.1 audit report.

   Row-set invariant (Gate 27, FC-2.2's own brief): this mapping produces
   the SAME sales/fins ROWS as before -- .map() over the identical
   payload.sales/payload.finance arrays, same length, same order, same
   filter (none). Only the per-row SHAPE gained fields; nothing about
   which rows are included changed.

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

  // FC-2.2: matches coparticipado-real-view-model.js's own hardcoded
  // 'Operação protegida' exactly -- the real RPC never returns a client-
  // identity field (contains_client_identity is always false), so this
  // is the constant every real row gets, never a derived/looked-up name.
  var CLIENTE_PROTEGIDO = 'Operação protegida';

  function realDate(v) {
    // Reused verbatim from the sibling module -- coparticipado-real-
    // view-model.js already proved this parser against this exact RPC's
    // date field; not reimplemented here.
    return window.NX_COPARTICIPADO_ADAPTER.parseDate(v);
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
        familia: A._internal.familiaModelo(r.model),
        // FC-2.2 (GAP-003 real export only -- calcScores() ignores these):
        cliente: CLIENTE_PROTEGIDO,
        modelo: r.model || 'NÃO INFORMADO',
        valorVenda: Number(r.sale_value) || 0,
        chassi: r.operation_reference || '',
        data: realDate(r.date)
      };
    });
  }

  function buildFins(rawFinance) {
    var A = window.NX_SCORE_ADAPTER;
    return (rawFinance || []).map(function (r) {
      return {
        vendedor: r.seller || '',
        loja: r.store || '',
        dept: mapDept(r.department),
        valorFinanciado: Number(r.financed_value) || 0,
        retorno: Number(r.return_value) || 0,
        receitaSPF: Number(r.spf_value) || 0,
        spfQtd: Number(r.spf_count) || 0,
        plano: r.plan || 'LINEAR',
        // FC-2.2 (GAP-003 real export only -- calcScores() ignores these).
        // `familia` here matches V1's OWN real secure adapter (score-
        // coparticipated-secure-adapter.js), which computes it on finance
        // records too, unlike coparticipado-real-view-model.js's own
        // buildFins() (which doesn't need it for its own render) -- GAP-003's
        // "Família do carro" column requires it, so it's included here
        // exactly as V1 proves it available (same familiaModelo(), already
        // used on sales above).
        familia: A._internal.familiaModelo(r.model),
        cliente: CLIENTE_PROTEGIDO,
        modelo: r.model || 'NÃO INFORMADO',
        valorVenda: Number(r.sale_value) || 0,
        parcelas: Number(r.installments) || 0,
        pmt: Number(r.installment_value) || 0,
        situacaoB3: r.status || '',
        chassi: r.operation_reference || '',
        data: realDate(r.date)
      };
    });
  }

  // FC-2.2 (Gate 19/14): rebuilds the SAME keyed rate lookup coparticipado-
  // real-view-model.js's own (private) buildTaxasCopart() does, over the
  // identical payload.rates[] array -- reusing the already-public
  // NX_COPARTICIPADO_ADAPTER.taxaKey() so the keys line up with
  // calcCoparticipacaoDetalhe()'s own internal lookup (score.js calls that
  // frozen function directly; no rebate math is reimplemented here, only
  // the raw-array-to-lookup-object reshape). `rate()` mirrors the sibling
  // file's own percent-or-fraction normalizer verbatim (a generic numeric
  // utility, not a business formula).
  function rate(v) {
    var n = Number(v) || 0;
    return n > 1 ? n / 100 : n;
  }

  function buildTaxasCopart(rawRates) {
    var CA = window.NX_COPARTICIPADO_ADAPTER;
    var lookup = {};
    (rawRates || []).forEach(function (r) {
      var key = CA.taxaKey(r.model);
      if (key) {
        lookup[key] = {
          modeloTabela: r.model,
          rebateTotal: rate(r.total_rebate),
          parteBrabus: rate(r.brabus_percent)
        };
      }
    });
    return lookup;
  }

  function buildRealResult(payload) {
    return {
      sales: buildSales(payload.sales),
      fins: buildFins(payload.finance),
      // FC-2.2: returned (not applied as a side effect on the shared
      // adapter here) so score.js can hold it in its own currentTaxasCopart,
      // the exact same pattern already used for fixture mode -- applied to
      // NX_COPARTICIPADO_ADAPTER only at export time, right before
      // calcCoparticipacaoDetalhe() needs it (Gate 15: one canonical
      // mapped shape, no parallel rich state).
      taxasCopart: buildTaxasCopart(payload.rates),
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
