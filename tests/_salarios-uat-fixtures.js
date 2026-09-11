/* RH-5B -- synthetic fixture data for the local Salários & Comissões
   UAT harness (tests/_salarios-uat-harness.html). SYNTHETIC ONLY -- no
   real employee name, CPF, salary, or commission value. Shapes mirror
   the real, live-proven RPC contracts (RH-1..RH-5A) exactly. */
(function () {
  'use strict';

  var PERIODS = { rows: [
    { id: 'p1', nome_periodo: '21/07 a 20/08', data_inicio: '2026-07-21', data_fim: '2026-08-20', status: 'ABERTO', periodo_atual: true, ativo: true, criado_por: 'seed' },
    { id: 'p2', nome_periodo: '21/06 a 20/07', data_inicio: '2026-06-21', data_fim: '2026-07-20', status: 'FECHADO', periodo_atual: false, ativo: true, criado_por: 'seed' }
  ] };

  var METRICS = {
    scope: { profile: 'MASTER', departments: ['NOVOS', 'SEMINOVOS'], is_master: true, is_director: false, is_seller: false, store: null },
    period_start: '2026-07-21', period_end: '2026-08-20', spf_net_percent: 70,
    eligibility_rule: 'ACTIVE_VENDEDOR_ONLY', plan_priority_rule: 'SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR',
    contains_personal_documents: false, contains_client_identity: false, contains_chassis: false,
    totals: { sold_count: 128, financed_count: 96, share_percent: 75.0, production_value: 4520000.55, return_value: 231000.10, spf_count: 40, spf_value: 61000.0, spf_net_value: 42700.0, profitability_value: 273700.10 },
    rows: [
      { seller_id: 's1', seller_name: 'Vendedor Exemplo A', store: 'BANDEIRANTES CENTRO', department: 'NOVOS', sold_count: 12, sales_value: 900000, financed_count: 9, share_percent: 75.0, production_value: 4500000.0, return_value: 230000.0, spf_count: 4, spf_value: 6000.0, spf_net_value: 4200.0, profitability_value: 272000.0, plan_breakdown: [] },
      { seller_id: 's2', seller_name: 'Vendedor Exemplo B', store: 'ABC', department: 'NOVOS', sold_count: 8, sales_value: 600000, financed_count: 5, share_percent: 62.5, production_value: 250000.0, return_value: 11000.0, spf_count: 2, spf_value: 3000.0, spf_net_value: 2100.0, profitability_value: 13100.0, plan_breakdown: [] },
      { seller_id: 's3', seller_name: 'Vendedor Exemplo C', store: 'GASTAO', department: 'SEMINOVOS', sold_count: 6, sales_value: 300000, financed_count: 4, share_percent: 66.7, production_value: 180000.0, return_value: 9000.0, spf_count: 1, spf_value: 1500.0, spf_net_value: 1050.0, profitability_value: 10050.0, plan_breakdown: [] }
    ]
  };

  var ANALYST = {
    absence_aware: true, contains_personal_documents: false, contains_client_identity: false, contains_chassis: false,
    rows: [{ analyst_name: 'Analista Exemplo', store: 'ABC', sold_count: 20, financed_count: 15, production_value: 700000.0, return_value: 34000.0, spf_count: 5, spf_value: 7500.0, transfer: false, covered_start: null, covered_end: null, coverage_id: null }]
  };

  var DIRECTORY = {
    period_start: '2026-07-21', period_end: '2026-08-20', assignment_source: 'ACTIVE_PORTAL_PROFILE',
    rows: [{ store: 'ABC', department: 'NOVOS', manager_name: 'Gerente Exemplo' }], ambiguous_assignments: 0,
    contains_client_identity: false, contains_personal_documents: false, contains_operational_identifiers: false
  };

  // RH-5F: full field set (financed_value/return_considered/spf_70/
  // modality etc), matching operational_salary_details' real live row
  // shape re-traced this Wave -- previously this fixture only carried
  // the handful of fields the OLD modal rendered; the module itself
  // already handles a missing field gracefully ('-'), but a demo/UAT
  // harness should show the real, now-enriched presentation.
  var DETAILS = {
    scope: METRICS.scope, period_start: '2026-07-21', period_end: '2026-08-20', seller_filter: 's1', seller_count: 2, row_count: 2, row_limit: 2000, truncated: false,
    rows: [
      // RH-5F.1: store + included_in_commission added -- required by the
      // new Analyst Details window-filter (openAnalystDetails() matches
      // on op.store and only counts included_in_commission:true rows).
      { date: '2026-08-01', finance_date: '2026-08-03', store: 'ABC', department: 'NOVOS', vehicle_model: 'ECLIPSE CROSS', chassis_masked: '******T12345', financed: true, financed_value: 240000.0, installments: 48, installment_value: 5200.0, modality: 'CDC', return_gross: 5400.0, return_considered: 5400.0, spf_count: 1, spf_gross: 1200.0, spf_considered: 1200.0, spf_70: 840.0, operation_profitability: 6240.0, included_in_commission: true, applied_rule: 'FAIXA CONSOLIDADA DO VENDEDOR' },
      { date: '2026-08-05', finance_date: null, store: 'ABC', department: 'NOVOS', vehicle_model: 'L200 TRITON', chassis_masked: '******T99887', financed: false, financed_value: 0, installments: null, installment_value: null, modality: '', return_gross: 0, return_considered: 0, spf_count: 0, spf_gross: 0, spf_considered: 0, spf_70: 0, operation_profitability: 0, included_in_commission: true, applied_rule: 'FAIXA CONSOLIDADA DO VENDEDOR' }
    ],
    contains_client_identity: false, contains_personal_documents: false, contains_full_chassis: false, contains_masked_chassis: true, contains_chassis: false, contains_nbs: false
  };

  function closingRow(id, historicalDetailStatus) {
    return { id: id, periodo_id: 'per-1', nome_periodo: '21/07 a 20/08', data_inicio: '2026-07-21', data_fim: '2026-08-20',
      versao: 1, status: 'FECHADO', fechado_por: 'seed-user', fechado_em: '2026-08-21T00:00:00Z', reaberto_por: null, reaberto_em: null,
      observacao: null, ativo: true, criado_por: 'seed-user', criado_em: '2026-08-21T00:00:00Z', atualizado_em: '2026-08-21T00:00:00Z',
      sales_batch_id: 'b1', finance_batch_id: 'b2', spf_batch_id: 'b3', snapshot_payload_hash: 'hash',
      commission_engine_version: 'commission-secure-v1', historical_detail_status: historicalDetailStatus };
  }
  function snapshotRow(fechamentoId, comissao, detalhes) {
    return { id: 'snap-' + fechamentoId, fechamento_id: fechamentoId, periodo_id: 'per-1', nome_periodo: '21/07 a 20/08',
      data_inicio: '2026-07-21', data_fim: '2026-08-20', nome: 'Vendedor Exemplo A', perfil: 'VENDEDOR', loja: 'ABC', departamento: 'NOVOS',
      vendidas: 5, financiadas: 3, share: 60.0, producao: 100000.0, retorno: 5000.0, spf_extra: 1000.0, spf_liquido: 700.0,
      rentabilidade_total: 5700.0, faixa: 'A', comissao: comissao, detalhes: detalhes, criado_em: '2026-08-21T00:00:00Z' };
  }

  var CLOSING_COMPLETE = closingRow('c-complete', 'COMPLETE');
  var CLOSING_LEGACY = closingRow('c-legacy', null);
  var CLOSING_BROKEN = closingRow('c-broken', null);
  var CLOSINGS_ALL = { rows: [CLOSING_COMPLETE, CLOSING_LEGACY, CLOSING_BROKEN] };
  var ROWS_COMPLETE = { rows: [snapshotRow('c-complete', 500.0, { faixa: 'A' })] };
  var ROWS_LEGACY = { rows: [snapshotRow('c-legacy', 300.0, { faixa: 'B' })] };
  var ROWS_BROKEN = { rows: [snapshotRow('c-broken', 0, null), snapshotRow('c-broken', 0, null)] };

  var OP_DETAIL_COMPLETE = { completeness: 'COMPLETE', rows: [
    { kind: 'CHASSIS', store: 'ABC', department: 'NOVOS', seller_user_id: 'u1', seller_name: 'Vendedor Exemplo A',
      sale_date: '2026-08-01', chassis_masked: '******T12345', vehicle_model: 'ECLIPSE CROSS', financed: true,
      finance_date: '2026-08-02', sale_value: 100000.0, financed_value: 90000.0, return_considered: 5000.0,
      included_in_commission: true, operation_date: null, operation_code: null, bank: null, finance_code: null,
      optional_name: null, spf_bruto: null, spf_liquido: null }
  ] };

  // RH-5B.3: operational_portal_config()'s real {rows:[{chave,valor}]}
  // shape, at the confirmed live production defaults.
  var CONFIG = { rows: [
    { chave: 'share_minimo', valor: '40' }, { chave: 'spf_liquido_percentual', valor: '70' },
    { chave: 'bonus_spf_analista', valor: '150' }, { chave: 'limite_retorno_novos', valor: '12000' },
    { chave: 'limite_retorno_seminovos', valor: '8000' },
    { chave: 'vendedor_faixa_baixo_share_baixo', valor: '10' }, { chave: 'vendedor_faixa_baixo_share_alto', valor: '15' },
    { chave: 'vendedor_faixa_alto_share_baixo', valor: '15' }, { chave: 'vendedor_faixa_alto_share_alto', valor: '20' },
    { chave: 'gerente_faixa_share_baixo', valor: '3' }, { chave: 'gerente_faixa_share_alto', valor: '4' },
    { chave: 'analista_faixa_share_baixo', valor: '3.5' }, { chave: 'analista_faixa_share_alto', valor: '4.5' }
  ] };

  // RH-5C.1: operational_gestor_fi_commission()'s real {pronto,...}
  // shape -- synthetic values, arithmetic consistent with the real
  // config above (share=75>=40 -> faixa 0.30%).
  var GESTOR_FI_READY = {
    pronto: true, period_start: '2026-07-21', period_end: '2026-08-20', beneficiary_name: 'Gestor F&I Exemplo',
    vendidas: 128, financiadas: 96, share: 75.0, producao: 4520000.55, retorno: 231000.10, spf: 61000.0,
    spf_qty: 40, spf_liquido: 42700.0, base: 273700.10, faixa: 0.003, comissao_principal: 821.1003,
    bonus_spf: 1200, comissao_final: 2021.1003, contains_client_identity: false, contains_personal_documents: false
  };
  var GESTOR_FI_NOT_READY = { pronto: false, motivo: 'NENHUM_BENEFICIARIO_CONFIGURADO' };

  // RH-5C.1: operational_commission_faixa_rows()'s real {rows:[...]}
  // shape -- one badge per real METRICS/ANALYST/DIRECTORY row above.
  // RH-5F.1: comissao_principal/comissao_spf/comissao_total, matching
  // the real live shape after operational_commission_faixa_rows'
  // additive projection change.
  var FAIXA_ROWS = { rows: [
    { perfil: 'VENDEDOR', seller_id: 's1', store: 'BANDEIRANTES CENTRO', department: 'NOVOS', faixa: 0.2, faixa_level: 'MAXIMA', share_tier: 'ALTO', retorno_tier: 'ALTO', comissao_principal: 54400.0, comissao_spf: 0, comissao_total: 54400.0 },
    { perfil: 'VENDEDOR', seller_id: 's2', store: 'ABC', department: 'NOVOS', faixa: 0.15, faixa_level: 'INTERMEDIARIA', share_tier: 'ALTO', retorno_tier: 'BAIXO', comissao_principal: 1965.0, comissao_spf: 0, comissao_total: 1965.0 },
    { perfil: 'VENDEDOR', seller_id: 's3', store: 'GASTAO', department: 'SEMINOVOS', faixa: 0.1, faixa_level: 'MINIMA', share_tier: 'ALTO', retorno_tier: 'BAIXO', comissao_principal: 1005.0, comissao_spf: 0, comissao_total: 1005.0 },
    { perfil: 'GERENTE', store: 'ABC', department: 'NOVOS', faixa: 0.04, faixa_level: 'MAXIMA', share_tier: 'ALTO', retorno_tier: null, comissao_principal: 10928.0, comissao_spf: 0, comissao_total: 10928.0 },
    { perfil: 'ANALISTA', store: 'ABC', faixa: 0.035, faixa_level: 'MINIMA', share_tier: 'BAIXO', retorno_tier: null, comissao_principal: 1435.0, comissao_spf: 750.0, comissao_total: 2185.0 }
  ], contains_client_identity: false, contains_personal_documents: false };

  window.NX_RH5B_UAT_FIXTURES = {
    PERIODS: PERIODS, METRICS: METRICS, ANALYST: ANALYST, DIRECTORY: DIRECTORY, DETAILS: DETAILS,
    CLOSINGS_ALL: CLOSINGS_ALL, ROWS_COMPLETE: ROWS_COMPLETE, ROWS_LEGACY: ROWS_LEGACY, ROWS_BROKEN: ROWS_BROKEN,
    OP_DETAIL_COMPLETE: OP_DETAIL_COMPLETE, CONFIG: CONFIG,
    GESTOR_FI_READY: GESTOR_FI_READY, GESTOR_FI_NOT_READY: GESTOR_FI_NOT_READY, FAIXA_ROWS: FAIXA_ROWS
  };
})();
