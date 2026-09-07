/* PM-5J -- byte-identical extraction of the REAL V1 (Authority) secure-
   mode AGGREGATION layer, portal-financiamento-brabus-secure/assets/js/
   portal-app.js, HEAD 4d8ce1d (branch hotfix/fandi-analista-group-scope;
   byte-identical for this file to ia-reconciliation-v2-local@908d028,
   re-confirmed this wave via `git diff 4d8ce1d 908d028 -- assets/js/
   portal-app.js` = empty).

   MUST be loaded in the same page AFTER commission-calc-v1-reference.js
   (this file reuses window.V1_REFERENCE.commissionCalc verbatim, never
   redeclares it, to avoid two "reference" copies drifting apart).

   Every function body below is copied VERBATIM from the cited line
   numbers -- the ONLY changes are: (1) `calcGestorFIGrupo()` here keeps
   its REAL original signature (no arguments, reads the same window-
   level state objects this file declares) -- unlike commission-calc-
   v1-reference.js's own copy, which deliberately parameterized it for
   the narrower formula-only PM-5I test; both are legitimate, clearly
   labeled extractions of the same real function at different levels of
   the real call graph. (2) `operationalMetricsKey()` drops its real
   DOM/date-range component (`operationalMetricsPeriod()` reads
   #dtIni/#dtFim) since this extraction's readiness-gate semantics only
   need internal CONSISTENCY between the fixture's own `.key` and this
   function's return value, never a real wall-clock period boundary --
   documented here, not silently changed. */

// portal-app.js:280, verbatim (needed by the manager-directory match).
function norm(s) {
  return (s || '').toString().normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

// portal-app.js:284, verbatim (used only inside the ANALISTA `obs` string).
function dataBR(d) { if (!d) return ''; const [y, m, day] = (d || '').split('-'); return `${day}/${m}/${y}`; }

// Simplified stand-in for portal-app.js:847-850's operationalMetricsKey()
// -- see file header note (2). Fixtures set `.key` to this exact
// constant so the real readiness checks below behave identically to a
// real "freshly loaded" state.
function operationalMetricsKey() { return 'PM5J_FIXTURE_KEY'; }

// Fixture-settable state containers -- REAL shape of the module-level
// globals portal-app.js itself mutates from its own RPC-loading
// functions (loadOperationalCommissionMetrics et al, not extracted here
// since they are pure network plumbing with zero financial logic).
window.OPERATIONAL_METRICS_STATE = { key: '', data: null, error: '' };
window.OPERATIONAL_ANALYST_METRICS_STATE = { key: '', rows: [], error: '' };
window.OPERATIONAL_MANAGER_DIRECTORY_STATE = { key: '', rows: [], error: '' };
window.MASTER_SECURITY_STATE = { data: null };

// portal-app.js:6285-6297, verbatim (real hardcoded UUID replaced by a
// SYNTHETIC constant for this test file only -- see PM-5J report for
// why the real UUID/name are never reproduced in this repo).
const GESTOR_FI_USUARIO_ID_SEGURO = 'PM5J-SYNTHETIC-GESTOR-UUID';
function gestorFIIdentidadeSegura() {
  const users = window.MASTER_SECURITY_STATE.data?.users || [];
  const gestor = users.find(u => u.id === GESTOR_FI_USUARIO_ID_SEGURO);
  if (!gestor || !gestor.ativo) return null;
  return gestor;
}

// portal-app.js:6252-6284, verbatim (REAL original signature, no
// parameters -- reads the same window-level state this file declares
// above, exactly like the real file reads its own module-level
// globals).
function calcGestorFIGrupo() {
  let t, pronto = true;
  const data = window.OPERATIONAL_METRICS_STATE.data;
  if (!data || window.OPERATIONAL_METRICS_STATE.key !== operationalMetricsKey()) {
    pronto = false;
    t = { vendidas: 0, financiadas: 0, producao: 0, retorno: 0, spf: 0, spfQty: 0 };
  } else {
    const g = data.totals || {};
    t = {
      vendidas: Number(g.sold_count) || 0,
      financiadas: Number(g.financed_count) || 0,
      producao: Number(g.production_value) || 0,
      retorno: Number(g.return_value) || 0,
      spf: Number(g.spf_value) || 0,
      spfQty: Number(g.spf_count) || 0
    };
  }
  const share = t.vendidas ? ((t.financiadas / t.vendidas) * 100) : 0;
  const faixa = share < 40 ? 0.0016 : 0.0030;
  const spfLiquido = (+t.spf || 0) * (window.V1_REFERENCE.cfgNum('spf_liquido_percentual') / 100);
  const base = (+t.retorno || 0) + spfLiquido;
  const comissaoPrincipal = base * faixa;
  const bonusSpf = (+t.spfQty || 0) * 30;
  const comissaoFinal = comissaoPrincipal + bonusSpf;
  return { ...t, share, faixa, spfLiquido, base, comissaoPrincipal, bonusSpf, comissaoFinal, pronto };
}

// portal-app.js:4890-4984, verbatim. commissionCalc() is
// window.V1_REFERENCE.commissionCalc (from commission-calc-v1-
// reference.js, loaded first) instead of a bare identifier -- the ONLY
// syntactic change, purely to avoid a duplicate declaration across the
// two reference files; the call sites and arguments are unchanged.
function calcularPreviewFechamentoCompetenciaSegura() {
  const commissionCalc = window.V1_REFERENCE.commissionCalc;
  const key = operationalMetricsKey();
  const vendState = window.OPERATIONAL_METRICS_STATE;
  const vendReady = !!(vendState.data && vendState.key === key && !vendState.error);
  const analystReady = !!(window.OPERATIONAL_ANALYST_METRICS_STATE.key === key && !window.OPERATIONAL_ANALYST_METRICS_STATE.error);
  const managerReady = !!(window.OPERATIONAL_MANAGER_DIRECTORY_STATE.key === key && !window.OPERATIONAL_MANAGER_DIRECTORY_STATE.error);
  const gestorIdentidade = gestorFIIdentidadeSegura();
  if (!vendReady || !analystReady || !managerReady || !gestorIdentidade) return null;

  const linhas = [];
  const vendRows = vendState.data.rows || [];

  vendRows.forEach(row => {
    const m = {
      vendidas: Number(row.sold_count) || 0,
      financiadas: Number(row.financed_count) || 0,
      producao: Number(row.production_value) || 0,
      retorno: Number(row.return_value) || 0,
      spf: Number(row.spf_value) || 0,
      spfQty: Number(row.spf_count) || 0,
      items: []
    };
    if (!(m.vendidas > 0 || m.financiadas > 0 || m.retorno > 0 || m.spf > 0)) return;
    const status = row.department || '';
    const c = commissionCalc(status, m, 'seller');
    linhas.push({ perfil: 'VENDEDOR', loja: row.store, nome: row.seller_name, status, m, c, comissao: c.comissaoTotal });
  });

  const gerenteBuckets = {};
  vendRows.forEach(row => {
    const dep = String(row.department || '').toUpperCase();
    const grupos = [];
    if (dep.includes('NOVOS')) grupos.push('NOVOS');
    if (dep.includes('SEMINOVOS')) grupos.push('SEMINOVOS');
    grupos.forEach(g => {
      const key2 = row.store + '|' + g;
      if (!gerenteBuckets[key2]) gerenteBuckets[key2] = { store: row.store, dep: g, m: { vendidas: 0, financiadas: 0, producao: 0, retorno: 0, spf: 0, spfQty: 0, items: [] } };
      const b = gerenteBuckets[key2].m;
      b.vendidas += Number(row.sold_count) || 0;
      b.financiadas += Number(row.financed_count) || 0;
      b.producao += Number(row.production_value) || 0;
      b.retorno += Number(row.return_value) || 0;
      b.spf += Number(row.spf_value) || 0;
      b.spfQty += Number(row.spf_count) || 0;
    });
  });
  const managerRows = window.OPERATIONAL_MANAGER_DIRECTORY_STATE.rows || [];
  Object.values(gerenteBuckets).forEach(b => {
    if (!(b.m.vendidas > 0 || b.m.financiadas > 0 || b.m.retorno > 0 || b.m.spf > 0)) return;
    const dir = managerRows.find(r => norm(r.store) === norm(b.store) && String(r.department || '').toUpperCase() === b.dep);
    const c = commissionCalc('GERENTE ' + b.dep, b.m, 'manager');
    linhas.push({ perfil: 'GERENTE', loja: b.store, nome: dir ? dir.manager_name : ('GERENTE ' + b.dep + ' NÃO LOCALIZADO'), status: 'GERENTE ' + b.dep, m: b.m, c, comissao: c.comissaoPrincipal });
  });

  const analystRows = window.OPERATIONAL_ANALYST_METRICS_STATE.rows || [];
  analystRows.forEach(row => {
    const m = {
      vendidas: Number(row.sold_count) || 0,
      financiadas: Number(row.financed_count) || 0,
      producao: Number(row.production_value) || 0,
      retorno: Number(row.return_value) || 0,
      spf: Number(row.spf_value) || 0,
      spfQty: Number(row.spf_count) || 0,
      items: []
    };
    const c = commissionCalc('ANALISTA', m, 'analyst');
    linhas.push({
      perfil: 'ANALISTA',
      loja: row.store,
      nome: row.analyst_name,
      status: row.transfer ? 'ANALISTA COBERTURA' : 'ANALISTA',
      m, c, comissao: c.comissaoTotal,
      obs: row.transfer ? `Cobertura ${dataBR(row.covered_start)} a ${dataBR(row.covered_end)} · redistribuído por operational_analyst_commission_metrics_v2` : ''
    });
  });

  const g = calcGestorFIGrupo();
  if (g.pronto && !linhas.some(l => String(l.perfil || '').toUpperCase().includes('GESTOR'))) {
    linhas.push({
      perfil: 'GESTOR F&I', loja: 'GRUPO', nome: gestorIdentidade.nome, cpf: gestorIdentidade.cpf, status: 'GESTOR F&I',
      m: { vendidas: g.vendidas || 0, financiadas: g.financiadas || 0, producao: g.producao || 0, retorno: g.retorno || 0, spf: g.spf || 0, spfQty: g.spfQty || 0, items: [] },
      c: { share: g.share || 0, spfLiquido: g.spfLiquido || 0, rentTotal: g.base || 0, faixa: g.faixa || 0, comissaoPrincipal: g.comissaoPrincipal || 0, comissaoSpf: g.bonusSpf || 0, comissaoTotal: g.comissaoFinal || 0 },
      comissao: g.comissaoFinal || 0, obs: 'Comissão Gestor F&I'
    });
  }

  let vendidas = 0, financiadas = 0, producao = 0, retorno = 0, spf = 0, comissaoPrevista = 0;
  linhas.forEach(l => { vendidas += +(l.m.vendidas || 0); financiadas += +(l.m.financiadas || 0); producao += +(l.m.producao || 0); retorno += +(l.m.retorno || 0); spf += +(l.m.spf || 0); comissaoPrevista += +(l.comissao || 0); });
  return { linhas, vendidas, financiadas, producao, retorno, spf, comissaoPrevista };
}

// portal-app.js:4496-4520, verbatim (periodo/document fallback replaced
// by an explicit `periodoOverride` parameter -- the real file reads
// module-global `PERIODO_SELECIONADO`/`document.getElementById`, this
// extraction takes the same shape explicitly instead, since a pure
// module has no DOM/global period state of its own).
function snapshotRowsPayload(preview, periodoOverride, fechamentoId = null) {
  const periodo = periodoOverride || {};
  return (preview.linhas || []).map(l => ({
    fechamento_id: fechamentoId,
    periodo_id: periodo.id || null,
    nome_periodo: periodo.nome_periodo || 'Datas manuais',
    data_inicio: periodo.data_inicio || '',
    data_fim: periodo.data_fim || '',
    loja: l.loja || '',
    perfil: l.perfil || '',
    nome: l.nome || '',
    status: l.status || '',
    vendidas: +(l.m?.vendidas || 0),
    financiadas: +(l.m?.financiadas || 0),
    share: +(l.c?.share || window.V1_REFERENCE.shareNum(l.m?.financiadas || 0, l.m?.vendidas || 0)),
    producao: +(l.m?.producao || 0),
    retorno: +(l.m?.retorno || 0),
    spf_extra: +(l.m?.spf || 0),
    spf_liquido: +(l.c?.spfLiquido || 0),
    rentabilidade_total: +(l.c?.rentTotal || 0),
    faixa: +(l.c?.faixa || 0),
    comissao_principal: +(l.c?.comissaoPrincipal || 0),
    comissao_spf: +(l.c?.comissaoSpf || 0),
    comissao_total: +(l.comissao || 0)
  }));
}

// portal-app.js:4535-4550, verbatim (the literal p_summary object built
// inline inside fecharCompetencia() -- extracted here as its own named
// function purely for testability; V1 itself never factors this out).
function buildSummaryPayloadV1(periodo, executivo, linhasCount, comissaoPrevista, fechadoPorCpf, fechadoPorNome) {
  return {
    periodo_id: periodo.id,
    nome_periodo: periodo.nome_periodo || '',
    data_inicio: periodo.data_inicio || '',
    data_fim: periodo.data_fim || '',
    status: 'FECHADO',
    fechado_por: fechadoPorCpf || '',
    fechado_por_nome: fechadoPorNome || '',
    qtd_vendida: executivo.vendidas,
    qtd_financiada: executivo.financiadas,
    producao_total: executivo.producao,
    retorno_total: executivo.retorno,
    spf_total: executivo.spf,
    linhas_snapshot: linhasCount,
    comissao_total: comissaoPrevista
  };
}

window.V1_AGGREGATION_REFERENCE = {
  setFixture(vendData, analystRows, managerRows, masterUsers, gestorAtivoUsuarioId) {
    const k = operationalMetricsKey();
    window.OPERATIONAL_METRICS_STATE = { key: k, data: vendData, error: '' };
    window.OPERATIONAL_ANALYST_METRICS_STATE = { key: k, rows: analystRows, error: '' };
    window.OPERATIONAL_MANAGER_DIRECTORY_STATE = { key: k, rows: managerRows, error: '' };
    window.MASTER_SECURITY_STATE = { data: { users: masterUsers } };
  },
  calcularPreviewFechamentoCompetenciaSegura,
  snapshotRowsPayload,
  buildSummaryPayloadV1,
  calcGestorFIGrupo,
  gestorFIIdentidadeSegura,
  GESTOR_FI_USUARIO_ID_SEGURO
};
