/* PORTAL-NEXT V2 -- Painel Master / Histórico de Competências
   view-model (Painel Master Phase PM-5H).

   PRESENTATION LOGIC ONLY -- no RPC transport (assets/js/adapters/
   master-competence-history-provider.js owns that), no DOM.

   Real business object (PM-5G/PM-5H, reconstructed from real Git
   sources -- see the provider's own header comment for exact
   citations): a `fechamentos_comissao` row has id/periodo_id/
   nome_periodo/data_inicio/data_fim/versao/status/ativo/fechado_por/
   fechado_em/reaberto_por/reaberto_em/criado_em/observacao (a text
   column that is normally JSON with the official summary totals, but
   AT LEAST ONE real historical row has plain free text instead --
   confirmed real finding from portal-ai/index.ts's own Parte AQ
   comment -- so parsing it must never throw, only degrade to "no
   summary available"). A `snapshot_comissoes` row has nome/perfil/
   loja/departamento/vendidas/financiadas/share/producao/retorno/
   spf_extra/spf_liquido/rentabilidade_total/faixa/comissao/detalhes
   (jsonb: comissao_principal/comissao_spf/comissao_total -- comissao_
   principal/comissao_spf do NOT exist as their own columns, only
   inside detalhes, confirmed real finding, same source).

   NO FINANCIAL FORMULA LIVES HERE. Every function in this file either
   (a) formats an already-persisted value for display, or (b) performs
   a plain arithmetic SUM/comparison of already-persisted values purely
   to detect a data-integrity problem -- never a commission/share/
   rentabilidade/faixa calculation. The two integrity checks below
   (checkSnapshotIntegrity / isStructurallyInconsistent) are DIRECT
   ports of the exact real, already-ground-truth-audited logic found in
   portal-financiamento-brabus-secure's own production code
   (supabase/functions/portal-ai/index.ts's checkSnapshotIntegrity, and
   supabase/migrations/20260824040000_..._snapshot_inconsistente.sql's
   own server-side fail-closed criterion respectively) -- reused
   verbatim, not reinvented, specifically so this screen can show a
   real inconsistency warning proactively in the viewer (V1 itself only
   ever surfaced this at export time, never in "Ver snapshot" -- PM-5H
   Gate 13 explicitly asks for the earlier, more visible warning). */
(function () {
  'use strict';

  function fmtDateBR(isoDate) {
    if (!isoDate || typeof isoDate !== 'string') return '-';
    var m = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return isoDate;
    return m[3] + '/' + m[2] + '/' + m[1];
  }

  // Full timestamp (fechado_em/reaberto_em/criado_em) -- pure string
  // slicing of the ISO-8601 value the RPC already returns, same
  // date-safety discipline as fmtDateBR (never a Date object/
  // toISOString, never a timezone conversion).
  function fmtDateTimeBR(iso) {
    if (!iso || typeof iso !== 'string') return '-';
    var m = iso.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (!m) return fmtDateBR(iso);
    return m[3] + '/' + m[2] + '/' + m[1] + ' ' + m[4] + ':' + m[5];
  }

  function fmtMoney(n) {
    var v = Number(n) || 0;
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  // Parte AQ (portal-ai/index.ts) -- at least one real historical
  // fechamento has "observacao" as legacy free text (e.g. "Primeiro
  // fechamento oficial de teste. | Reabertura: teste"), not the JSON
  // object with official totals. Never throw -- treat as absent.
  function parseObservacao(raw) {
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      return (typeof parsed === 'object' && parsed !== null) ? parsed : null;
    } catch (e) {
      return null;
    }
  }

  // Parte P/CM (portal-ai/index.ts) -- comissao_principal/comissao_spf
  // live ONLY inside the jsonb "detalhes" column; "comissao" (top
  // level) duplicates detalhes.comissao_total. Ported verbatim.
  function commissionTotals(row) {
    var d = (row && row.detalhes) || {};
    var total = Number(d.comissao_total != null ? d.comissao_total : (row ? row.comissao : 0)) || 0;
    var spf = Number(d.comissao_spf != null ? d.comissao_spf : 0) || 0;
    var principal = Number(d.comissao_principal != null ? d.comissao_principal : (total - spf)) || 0;
    return { principal: round2(principal), spf: round2(spf), total: round2(total) };
  }

  function round2(n) {
    return Math.round((Number(n) || 0) * 100) / 100;
  }

  // Parte CK/AQ (portal-ai/index.ts) -- direct port of the real,
  // already-audited divergence check: sum of every row's own total
  // vs. the fechamento's own persisted official total (from
  // observacao.comissao_total). DIVERGENTE when the two disagree by
  // more than R$1 -- never "fixed", only surfaced.
  function checkSnapshotIntegrity(rows, observacao) {
    var rowSum = round2((rows || []).reduce(function (s, r) { return s + commissionTotals(r).total; }, 0));
    var official = (observacao && typeof observacao.comissao_total === 'number') ? round2(observacao.comissao_total) : null;
    if (official === null) return { status: 'SEM_REFERENCIA', rowSumTotal: rowSum, officialTotal: null, diff: null };
    var diff = round2(Math.abs(rowSum - official));
    return { status: diff > 1 ? 'DIVERGENTE' : 'OK', rowSumTotal: rowSum, officialTotal: official, diff: diff };
  }

  // Direct port of master_commission_snapshot_export's own real
  // server-side fail-closed criterion (supabase/migrations/
  // 20260824040000_incidente_p2_rhdp_failclosed_snapshot_
  // inconsistente.sql): blocks when there are zero rows, OR when
  // EVERY row has comissao=0 AND detalhes IS NULL simultaneously.
  // Partial zeros (e.g. a seller with no production that period) are
  // legitimate and never trip this -- ported verbatim, not guessed.
  function isStructurallyInconsistent(rows) {
    var list = rows || [];
    if (list.length === 0) return true;
    var allZeroAndNull = list.every(function (r) {
      return (Number(r.comissao) || 0) === 0 && (r.detalhes === null || r.detalhes === undefined);
    });
    return allZeroAndNull;
  }

  var STATUS_LABELS = { FECHADO: 'Fechado', REABERTO: 'Reaberto' };
  function statusLabel(status) {
    var s = String(status || '').toUpperCase();
    return STATUS_LABELS[s] || (status || '-');
  }

  // Most recent period first, most recent version first within a
  // period -- matches the "current state on top" convention already
  // used by Períodos/Férias-Ausências/Mudança de Loja's own sort
  // helpers, never hides older versions (PM-5H Gate 15).
  function sortClosings(rows) {
    return (rows || []).slice().sort(function (a, b) {
      var da = a.data_fim || '', db = b.data_fim || '';
      if (da !== db) return da < db ? 1 : -1;
      return (Number(b.versao) || 0) - (Number(a.versao) || 0);
    });
  }

  var PROFILE_ORDER = ['VENDEDOR', 'GERENTE', 'ANALISTA', 'GESTOR F&I'];
  function sortSnapshotRows(rows) {
    return (rows || []).slice().sort(function (a, b) {
      var pa = PROFILE_ORDER.indexOf(String(a.perfil || '').toUpperCase());
      var pb = PROFILE_ORDER.indexOf(String(b.perfil || '').toUpperCase());
      if (pa === -1) pa = PROFILE_ORDER.length;
      if (pb === -1) pb = PROFILE_ORDER.length;
      if (pa !== pb) return pa - pb;
      var la = String(a.loja || ''), lb = String(b.loja || '');
      if (la !== lb) return la < lb ? -1 : 1;
      return String(a.nome || '').localeCompare(String(b.nome || ''));
    });
  }

  // Presentation-only reshape for the Excel export (real, already-
  // persisted snapshot fields, one row per person -- no computation).
  function xlsxRows(rows) {
    return (rows || []).map(function (r) {
      var t = commissionTotals(r);
      return {
        'Loja': r.loja || '', 'Perfil': r.perfil || '', 'Nome': r.nome || '',
        'Departamento': r.departamento || '', 'Vendidas': Number(r.vendidas) || 0,
        'Financiadas': Number(r.financiadas) || 0, 'Share': Number(r.share) || 0,
        'Produção': round2(r.producao), 'Retorno': round2(r.retorno),
        'SPF Extra': round2(r.spf_extra), 'SPF Líquido': round2(r.spf_liquido),
        'Rentabilidade Total': round2(r.rentabilidade_total), 'Faixa': Number(r.faixa) || 0,
        'Comissão Principal': t.principal, 'Comissão SPF': t.spf, 'Comissão Total': t.total
      };
    });
  }

  window.NX_MASTER_COMPETENCE_HISTORY_VM = {
    fmtDateBR: fmtDateBR,
    fmtDateTimeBR: fmtDateTimeBR,
    fmtMoney: fmtMoney,
    parseObservacao: parseObservacao,
    commissionTotals: commissionTotals,
    checkSnapshotIntegrity: checkSnapshotIntegrity,
    isStructurallyInconsistent: isStructurallyInconsistent,
    statusLabel: statusLabel,
    sortClosings: sortClosings,
    sortSnapshotRows: sortSnapshotRows,
    xlsxRows: xlsxRows
  };
})();
