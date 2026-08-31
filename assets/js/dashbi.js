/* PORTAL-NEXT V2 -- Dashbi (Análise Geral do Grupo) module UI.
   Business logic: assets/js/adapters/dashbi.adapter.js (byte-identical
   extraction -- see docs/DASHBI-FUNCTION-MAP.md, DASHBI-DATA-
   CONTRACT.md, DASHBI-MODEL-ANALYSIS-CONTRACT.md). This file only
   renders.

   Real production surface migrated (verified by direct source read of
   origin/main:modules/analise-geral-grupo-secure-original-layout.html
   render()/kpiMetricsFor()/renderModelos()):
     - Grupo/Novos/Seminovos core KPIs: Vendas, Financiamentos, Share,
       Produção, Receita (+SPF, total), Retorno (kpiMetricsFor)
     - Classificação dos Planos (5 cards, same priority as Análise F&I/
       Coparticipado: SUBSIDIADO>REVERSÃO>COPARTICIPADO>BALÃO>LINEAR)
     - Model Analysis (Novos only) per família (OUTLANDER/TRITON/
       ECLIPSE CROSS): volume, financiada, penetração, produção,
       receita, ticket, retorno médio, prazo médio, PMT médio, and
       Entrada/Entrada Média/Entrada % (Gate 81 -- never hidden)
     - Store/period/vehicle-view filters (4 presets: mês atual/
       anterior/últimos 6 meses/último ano -- matches Coparticipado's
       preset set, NOT Gestão's 3-preset set -- verified, not presumed)
     - FECHAMENTO badge (isClosedMonthPeriod) -- present here, unlike
       Gestão (confirmed absent there)
     - Base02 discard/Entrada diagnostics surfaced as dev-only info
       (Gate 40/98 -- never in the base product experience)
     - Missing-seller hard-stop (Gate 9 real finding): if any resolved
       seller has no known loja, production aborts rendering entirely
       rather than showing a partial/wrong result -- V2 reproduces
       this exact behavior (results.blocked)
     - Selective analytical navigation (PORTAL-NEXT-07.2): Análise por
       Modelos/Ranking/Novos por Loja are mutually exclusive, one active
       at a time, mirroring production's own showTab() single-active-
       region switcher. Availability by view (from updateModelosTabVisibility,
       confirmed by direct source read): Grupo/Seminovos expose Visão
       Geral + Ranking only; Novos exposes all 4. Switching away from an
       unavailable mode falls back to Visão Geral -- applied uniformly to
       both Modelos and Novos por Loja, closing a real asymmetry in
       production's own code (only Modelos has an explicit fallback
       wired; Novos por Loja does not, apparently an oversight from when
       it was added in a later UX iteration).

   NOT migrated (Gate 20-21/137 deferred, real reasons -- see
   docs/DASHBI-FUNCTION-MAP.md):
     - The live secure-API path (operational_metrics RPC) -- 0 backend
       this Wave; production's own external adapter unconditionally
       overrides window.processar with this path on boot, but it only
       reshapes an ALREADY-aggregated backend payload (no classification/
       crossing logic to extract from it)
     - Excel/CSV file parsing -- 0 file I/O this Wave, fixtures supply
       already-shaped raw rows directly
     - lojaEfetivaPorMudancaPortal's live data source (a Supabase REST
       fetch) -- extracted byte-identical, but BRABUS_MUDANCAS_LOJA_
       VENDEDORES is never populated (0 backend), which deterministically
       reproduces the function's own no-override fallback
     - Ranking/medal cards, comparison-to-previous-period deltas, CSV
       export, the full multi-tab shell chrome -- presentation-layer,
       not reused as-is (V2 builds its own Red Precision presentation
       from the extracted data, same precedent as every prior module) */
(function () {
  'use strict';

  var FAMILIES = ['OUTLANDER', 'TRITON', 'ECLIPSE CROSS'];

  var fixturesData = null;
  var currentFixtureId = 'multi_loja_vendedor';
  var currentDeptView = 'Grupo';
  var currentFamily = 'OUTLANDER';
  var currentPreset = 'CUSTOM';
  var currentDateStart = '2026-01-01';
  var currentDateEnd = '2026-12-31';

  // PORTAL-NEXT-07.2 — selective analytical navigation. Mirrors production's
  // own single-active-region tab switcher (showTab(): exactly one of
  // share/modelos/ranking/novosLoja gets display:block, the rest
  // display:none) plus its per-view tab availability (updateModelosTabVisibility():
  // modelosTab/novosLojaTab hidden outside Novos; rankingTab never gated).
  // 'overview' stands in for production's default "Share / Retorno" tab,
  // which V2 never built as a distinct surface — its content is the
  // always-on store/seller tables already rendered below the KPIs.
  var MODES_BY_VIEW = {
    Grupo: ['overview', 'ranking'],
    Novos: ['overview', 'modelos', 'ranking', 'novosLoja'],
    Seminovos: ['overview', 'ranking']
  };
  var MODE_LABELS = { overview: 'Visão Geral', modelos: 'Análise por Modelos', ranking: 'Ranking', novosLoja: 'Novos por Loja' };
  var currentMode = 'overview';

  function modesForView(view) { return MODES_BY_VIEW[view] || MODES_BY_VIEW.Grupo; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  function loadFixtures() {
    if (fixturesData) return Promise.resolve(fixturesData);
    return fetch('tests/fixtures/dashbi-fixtures.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { fixturesData = data.cases; return fixturesData; });
  }

  function headerRow(headers, numericFrom) {
    numericFrom = numericFrom == null ? 1 : numericFrom;
    return headers.map(function (h, i) {
      return '<th' + (i >= numericFrom ? ' class="dbNumCol"' : '') + '>' + esc(h) + '</th>';
    }).join('');
  }
  function row(cells) {
    return '<tr><td>' + esc(cells[0]) + '</td>' + cells.slice(1).map(function (c) { return '<td class="dbNumCol">' + esc(String(c)) + '</td>'; }).join('') + '</tr>';
  }
  function tableHtml(headers, bodyRows, numericFrom, wrapText) {
    // wrapText (PORTAL-NEXT-07.4): for small text-only tables (e.g.
    // Inconsistências TRITON) a "+ Detalhes" split isn't warranted — letting
    // long values (long names) wrap onto multiple lines within their cell
    // is simpler and satisfies the no-horizontal-scroll directive just as
    // well as the primary/detail pattern used for comparison tables.
    return '<div class="dbTableWrap"><table class="dbTable' + (wrapText ? ' dbTableWrapText' : '') + '"><thead><tr>' + headerRow(headers, numericFrom) + '</tr></thead>' +
      '<tbody>' + (bodyRows.length ? bodyRows.join('') : '<tr><td colspan="' + headers.length + '" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  // PORTAL-NEXT-07.4 — global no-horizontal-scroll directive: material
  // information must never require horizontal scrolling to reach.
  // Shared "primary row + inline vertical detail" component, reused by
  // every Dashbi table wide enough to have needed a scrollbar (store/
  // seller/Ranking/Novos-por-Loja/plan tables/Model Analysis). A row's
  // "+ Detalhes" toggles a namespaced key in expandedKeys; render()
  // rebuilds the whole panel on toggle (same pattern already used for
  // every other interaction in this file), so expanded rows persist
  // across period/fixture changes (fresh data, same open state) but are
  // explicitly reset on family switch (Gate 16/44) via resetExpanded().
  var expandedKeys = {};
  function isExpanded(ns, key) { return !!(expandedKeys[ns] && expandedKeys[ns][String(key)]); }
  function toggleExpanded(ns, key) {
    if (!expandedKeys[ns]) expandedKeys[ns] = {};
    var k = String(key);
    if (expandedKeys[ns][k]) delete expandedKeys[ns][k];
    else expandedKeys[ns][k] = true;
  }
  function resetExpanded(ns) { expandedKeys[ns] = {}; }

  function detailDomId(ns, key) { return 'db-detail-' + ns + '-' + String(key).replace(/[^a-zA-Z0-9_-]/g, '_'); }

  function detailToggleHtml(ns, key) {
    var open = isExpanded(ns, key);
    return '<button type="button" class="dbDetailToggle" data-detail-ns="' + esc(ns) + '" data-detail-key="' + esc(String(key)) +
      '" aria-expanded="' + (open ? 'true' : 'false') + '" aria-controls="' + detailDomId(ns, key) + '">' + (open ? '− Detalhes' : '+ Detalhes') + '</button>';
  }

  // groups: [{label, items:[{label, value}]}] — value is pre-formatted HTML/text.
  function detailRowHtml(ns, key, colspan, groups) {
    if (!isExpanded(ns, key)) return '';
    var body = groups.map(function (g) {
      return '<div class="dbDetailGroup"><div class="dbDetailGroupLabel">' + esc(g.label) + '</div>' +
        '<div class="dbDetailGroupItems">' + g.items.map(function (it) {
          return '<div class="dbDetailItem"><span class="dbDetailK">' + esc(it.label) + '</span><span class="dbDetailV">' + it.value + '</span></div>';
        }).join('') + '</div></div>';
    }).join('');
    return '<tr id="' + detailDomId(ns, key) + '" class="dbDetailRow"><td colspan="' + colspan + '"><div class="dbDetailPanel">' + body + '</div></td></tr>';
  }

  function kpiPrimary(label, value, hint) {
    return '<div class="dbKpiCardPrimary"><div class="dbK">' + esc(label) + '</div><div class="dbV">' + value + '</div>' + (hint ? '<div class="dbHint">' + hint + '</div>' : '') + '</div>';
  }

  function buildFixtureInput(id) {
    var c = fixturesData.filter(function (x) { return x.id === id; })[0];
    return {
      b1HistRows: c.b1HistRows, b2HistRows: c.b2HistRows,
      b1NovaRows: c.b1NovaRows, b2NovaRows: c.b2NovaRows,
      b3Rows: c.b3Rows, vendorRows: c.vendorRows
    };
  }

  function planCardHtml(A, tipo, count) {
    var cls = { 'LINEAR': 'planLinear', 'BALÃO': 'planBalao', 'SUBSIDIADO': 'planSubsidiado', 'REVERSÃO': 'planReversao', 'COPARTICIPADO': 'planCoparticipado' }[tipo] || '';
    return '<div class="dbPlanCard ' + cls + '"><div class="dbK">' + esc(tipo) + '</div><div class="dbV">' + (count || 0) + '</div></div>';
  }

  // PORTAL-NEXT-07.4 — a primary row (identity + fast-comparison numeric
  // columns + toggle) followed by its detail row when expanded. colspan
  // covers the FULL primary column count (identity + numeric + toggle),
  // so the detail panel spans the whole table width.
  function expandableRow(ns, key, primaryCells, numericFrom, colspan, detailGroups) {
    return '<tr><td>' + esc(String(primaryCells[0])) + '</td>' +
      primaryCells.slice(1).map(function (c, i) { return '<td' + (i + 1 >= numericFrom ? ' class="dbNumCol"' : '') + '>' + esc(String(c)) + '</td>'; }).join('') +
      '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
      detailRowHtml(ns, key, colspan, detailGroups);
  }

  function expandableTableHtml(headers, numericFrom, bodyRowsHtml, colCount) {
    return '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' + headerRow(headers.concat(['']), numericFrom) + '</tr></thead>' +
      '<tbody>' + (bodyRowsHtml.length ? bodyRowsHtml.join('') : '<tr><td colspan="' + colCount + '" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  function storeTableHtml(A, results) {
    var A_ = results.aggs;
    var lojas = Object.keys(A_.vendasLoja);
    var finLojaMap = A_.finLoja;
    var ns = 'storeTable';
    var body = lojas.sort(function (a, b) { return (A_.vendasLoja[b].qtd || 0) - (A_.vendasLoja[a].qtd || 0); }).map(function (loja) {
      var v = A_.vendasLoja[loja] || { qtd: 0 };
      var f = finLojaMap[loja] || { qtd: 0, producao: 0, receita: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      return expandableRow(ns, loja, [loja, v.qtd, f.qtd, A.pct(share)], 1, 5, [
        { label: 'Financeiro', items: [
          { label: 'Produção', value: esc(A.money(f.producao || 0)) },
          { label: 'Receita', value: esc(A.money(f.receita || 0)) }
        ] }
      ]);
    });
    return expandableTableHtml(['Loja', 'Vendas', 'Financiamentos', 'Share'], 1, body, 5);
  }

  function sellerTableHtml(A, results) {
    var A_ = results.aggs;
    var keys = Object.keys(A_.vendasVendDept);
    var ns = 'sellerTable';
    var body = keys.sort(function (a, b) { return (A_.vendasVendDept[b].qtd || 0) - (A_.vendasVendDept[a].qtd || 0); }).map(function (key) {
      var parts = key.split(' | ');
      var v = A_.vendasVendDept[key] || { qtd: 0 };
      var f = A_.finVendDept[key] || { qtd: 0, producao: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      return expandableRow(ns, key, [parts[0], v.qtd, f.qtd, A.pct(share)], 1, 5, [
        { label: 'Detalhe', items: [
          { label: 'Depto', value: esc(parts[1] || '') },
          { label: 'Produção', value: esc(A.money(f.producao || 0)) }
        ] }
      ]);
    });
    return expandableTableHtml(['Vendedor', 'Vendas', 'Financiamentos', 'Share'], 1, body, 5);
  }

  var VEHICLE_IMAGES = {
    OUTLANDER: 'assets/img/vehicles/outlander.png',
    'ECLIPSE CROSS': 'assets/img/vehicles/eclipse_cross.png',
    TRITON: 'assets/img/vehicles/triton.png'
  };

  function vehicleSelectorHtml() {
    return '<div class="dbVehicleSelector" role="group" aria-label="Selecionar família de modelo">' +
      FAMILIES.map(function (f) {
        var active = f === currentFamily;
        return '<button type="button" class="dbVehicleCard' + (active ? ' dbVehicleCardActive' : '') +
          '" data-family="' + esc(f) + '" aria-pressed="' + (active ? 'true' : 'false') + '">' +
          '<span class="dbVehicleImgWrap"><img src="' + esc(VEHICLE_IMAGES[f]) + '" alt="" loading="lazy"></span>' +
          '<span class="dbVehicleName">' + esc(f) + (active ? ' <span class="dbVehicleCheck" aria-hidden="true">&#10003;</span>' : '') + '</span>' +
          '</button>';
      }).join('') +
      '</div>';
  }

  function modeNavHtml() {
    var available = modesForView(currentDeptView);
    return '<div class="dbModeGroup" role="group" aria-label="Análise complementar">' +
      available.map(function (m) {
        var active = m === currentMode;
        return '<button type="button" class="dbBtn dbModeBtn' + (active ? ' dbBtnActive' : '') +
          '" data-mode="' + esc(m) + '" aria-pressed="' + (active ? 'true' : 'false') + '">' + esc(MODE_LABELS[m]) + '</button>';
      }).join('') +
      '</div>';
  }

  // PORTAL-NEXT-07.3 — full production column contract for "Indicadores por
  // modelo" (18 fields, origin/main lines 4088-4107), plus Entrada Qtd
  // (already on modelRowsUnified's row, EXTRA_IN_V2, kept — see
  // docs/MODEL-ANALYSIS-PRODUCTION-VS-V2.md). Group labels are purely
  // presentational (Gate 25/50) — every column still maps 1:1 to a single
  // production label, no new business category. Rendered as one wide table
  // with a sticky Modelo column + horizontal scroll, NOT the card+modal
  // shape production currently uses for this data — see
  // docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md's "Presentation decision"
  // (data-table.md forbids cardifying tabular data; HUMAN REVIEW REQUIRED
  // on this choice, flagged there).
  var MODEL_TABLE_COLUMNS = [
    { group: null, key: 'Modelo', label: 'Modelo' },
    { group: 'Volume', key: 'volume', label: 'Volume', f: function (A, v) { return A.num(v); } },
    { group: 'Volume', key: 'financiada', label: 'Financiamentos', f: function (A, v) { return A.num(v); } },
    { group: 'Volume', key: 'penetracao', label: 'Penetração', f: function (A, v) { return A.pct(v); }, penetracao: true },
    { group: 'Financeiro', key: 'producao', label: 'Produção', f: function (A, v) { return A.money(v); } },
    { group: 'Financeiro', key: 'receita', label: 'Receita', f: function (A, v) { return A.money(v); } },
    { group: 'Financeiro', key: 'receitaSPF', label: 'Receita SPF', f: function (A, v) { return A.money(v); } },
    { group: 'Financeiro', key: 'receitaTotal', label: 'Receita Total', f: function (A, v) { return A.money(v); } },
    { group: 'Financeiro', key: 'ticket', label: 'Ticket Médio', f: function (A, v) { return A.money(v); } },
    { group: 'Retorno', key: 'retornoMedio', label: 'Retorno Médio', f: function (A, v) { return A.pct(v); } },
    { group: 'Parcelamento', key: 'prazoMedio', label: 'Prazo Médio', f: function (A, v) { return A.num(v, 1) + 'x'; } },
    { group: 'Parcelamento', key: 'pmtMed', label: 'Parcela Média', f: function (A, v) { return A.money(v); } },
    { group: 'Entrada', key: 'entradaMed', label: 'Entrada Média', f: function (A, v) { return A.money(v); } },
    { group: 'Entrada', key: 'entradaPct', label: 'Entrada %', f: function (A, v) { return A.pct(v); } },
    { group: 'Planos', key: 'subsidiadoQtd', label: 'Qtd Subsidiado', f: function (A, v) { return A.num(v); } },
    { group: 'Planos', key: 'reversaoQtd', label: 'Qtd Reversão', f: function (A, v) { return A.num(v); } },
    { group: 'Planos', key: 'coparticipadoQtd', label: 'Qtd Coparticipado', f: function (A, v) { return A.num(v); } },
    { group: 'Planos', key: 'balaoQtd', label: 'Qtd Balão', f: function (A, v) { return A.num(v); } },
    { group: 'Planos', key: 'linearQtd', label: 'Qtd Linear', f: function (A, v) { return A.num(v); } },
    { group: 'Planos', key: 'balaoMed', label: 'Balão Médio', f: function (A, v) { return A.money(v); } }
  ];
  // PORTAL-NEXT-07.4.1 — "Entrada Qtd" removed from the UI (Gate 0): it was
  // never a production-visible metric, only the internal eligible-record
  // COUNT that Entrada Média/% divide by (modelExtraMetrics's entradaQtd,
  // still computed and still on every row — untouched, still feeds those
  // two real metrics exactly as before). subsidiadoQtd/coparticipadoQtd
  // added to PLANOS (Gate 1-7): audited aggregate()'s own compVals (already
  // extracted byte-identical) and found it computes coparticipadoQtd/
  // subsidiadoQtd on the SAME compModelo aggregation, same population, same
  // mutually-exclusive classifiers (isFinSubsidiado/isFinCoparticipado) as
  // linearQtd/balaoQtd — production's own modelRowsUnified just doesn't
  // surface those two fields into its row shape (confirmed by direct
  // source read, not an extraction gap). Sourced here from planRowsByModel
  // (already extracted, already on-page one section below) for the
  // matching Modelo, not a new business-logic extraction. Order follows
  // the official classification priority (SUBSIDIADO>REVERSÃO>
  // COPARTICIPADO>BALÃO>LINEAR), per the human's stated preference.

  function penetracaoCellHtml(A, v) {
    var cls = v < 0.40 ? 'dbPenetracaoBaixa' : 'dbPenetracaoOk';
    return '<span class="' + cls + '">' + esc(A.pct(v)) + '</span>';
  }

  // PORTAL-NEXT-07.4 — the 07.3 wide table (18 columns, grouped headers)
  // scrolled horizontally at EVERY viewport including 1920px — the human
  // global no-horizontal-scroll directive rejects this. Recomposed as a
  // compact primary comparison row (Volume/Financiamentos/Penetração
  // always; Produção/Receita Total/Ticket Médio/Retorno Médio added at
  // >=768px via CSS, .dbDesktopCol) + a "+ Detalhes" inline expansion
  // covering every remaining field, grouped exactly as production's own
  // family miniGrid groups them (Financeiro/Parcelamento/Entrada/Planos)
  // — presentational grouping only, 0 change to any formula/population
  // (see docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md). The desktop-only
  // columns are ALSO always present in the detail panel (small
  // redundancy, not a completeness gap) so mobile users find every
  // metric in exactly one place regardless of viewport.
  var MODEL_PRIMARY_ALWAYS = ['volume', 'financiada', 'penetracao'];
  var MODEL_PRIMARY_DESKTOP = ['producao', 'receitaTotal', 'ticket', 'retornoMedio'];

  function modelCellHtml(A, c, r) {
    var val = r[c.key];
    return c.penetracao ? penetracaoCellHtml(A, val) : esc(String(c.f(A, val)));
  }

  function modelPrimaryDetailTableHtml(A, modelRows) {
    var byKey = {};
    MODEL_TABLE_COLUMNS.forEach(function (c) { byKey[c.key] = c; });
    var alwaysCols = MODEL_PRIMARY_ALWAYS.map(function (k) { return byKey[k]; });
    var desktopCols = MODEL_PRIMARY_DESKTOP.map(function (k) { return byKey[k]; });
    var primaryKeys = MODEL_PRIMARY_ALWAYS.concat(MODEL_PRIMARY_DESKTOP);
    var detailCols = MODEL_TABLE_COLUMNS.slice(1).filter(function (c) { return primaryKeys.indexOf(c.key) === -1; });
    var detailGroupsByLabel = {};
    var detailGroupOrder = [];
    // Financeiro/Retorno detail also repeats the desktop-only primary
    // columns, so they stay reachable via + Detalhes at every viewport.
    desktopCols.concat(detailCols).forEach(function (c) {
      if (!detailGroupsByLabel[c.group]) { detailGroupsByLabel[c.group] = []; detailGroupOrder.push(c.group); }
      detailGroupsByLabel[c.group].push(c);
    });

    var headCells = '<th scope="col">Modelo</th>' +
      alwaysCols.map(function (c) { return '<th class="dbNumCol" scope="col">' + esc(c.label) + '</th>'; }).join('') +
      desktopCols.map(function (c) { return '<th class="dbNumCol dbDesktopCol" scope="col">' + esc(c.label) + '</th>'; }).join('') +
      '<th scope="col"></th>';
    var colspan = 1 + alwaysCols.length + desktopCols.length + 1;
    var ns = 'modelIndicators';
    var body = modelRows.map(function (r) {
      var key = r.Modelo;
      var groups = detailGroupOrder.map(function (label) {
        return { label: label, items: detailGroupsByLabel[label].map(function (c) { return { label: c.label, value: modelCellHtml(A, c, r) }; }) };
      });
      return '<tr><td>' + esc(r.Modelo) + '</td>' +
        alwaysCols.map(function (c) { return '<td class="dbNumCol">' + modelCellHtml(A, c, r) + '</td>'; }).join('') +
        desktopCols.map(function (c) { return '<td class="dbNumCol dbDesktopCol">' + modelCellHtml(A, c, r) + '</td>'; }).join('') +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
        detailRowHtml(ns, key, colspan, groups);
    }).join('');
    return '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' + headCells + '</tr></thead>' +
      '<tbody>' + (body || '<tr><td colspan="' + colspan + '" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  function familyMetricGridHtml(A, results, modelRows) {
    var totals = modelRows.reduce(function (a, r) {
      a.volume += r.volume; a.financiada += r.financiada; a.producao += r.producao;
      a.receita += r.receita; a.receitaSPF += r.receitaSPF; a.receitaTotal += r.receitaTotal;
      return a;
    }, { volume: 0, financiada: 0, producao: 0, receita: 0, receitaSPF: 0, receitaTotal: 0 });
    var pen = totals.volume ? totals.financiada / totals.volume : 0;
    var ticket = totals.financiada ? totals.producao / totals.financiada : 0;
    var extraFam = A.familyExtraMetrics(results, modelRows);
    function box(label, value) { return '<div class="dbFamilyMetricBox"><div class="dbK">' + esc(label) + '</div><div class="dbV">' + value + '</div></div>'; }
    return '<div class="dbFamilyMetricGrid">' +
      box('Volume vendido', A.num(totals.volume)) +
      box('Financiamentos', A.num(totals.financiada)) +
      box('Penetração', A.pct(pen)) +
      box('Produção', A.money(totals.producao)) +
      box('Receita', A.money(totals.receita)) +
      box('Receita SPF', A.money(totals.receitaSPF)) +
      box('Receita Total', A.money(totals.receitaTotal)) +
      box('Ticket médio', A.money(ticket)) +
      box('Média de retorno', A.pct(extraFam.retornoMedio)) +
      box('Prazo médio', A.num(extraFam.prazoMedio, 1) + 'x') +
      box('Média de parcela', A.money(extraFam.pmtMed)) +
      box('Entrada média', A.money(extraFam.entradaMed)) +
      box('% Entrada médio', A.pct(extraFam.entradaPct)) +
      '</div>';
  }

  // PORTAL-NEXT-07.4 — plan-mix tables (12 fields: label + 5 pairs of
  // count/%) scrolled horizontally up to 768px. Primary: label +
  // Financiamentos + Linear + Balão (the 2 most common plan types);
  // detail: every remaining count/% pair, 0 change to any value.
  function planPctPrimaryHeaders(labelHeader) { return [labelHeader, 'Financiamentos', 'Linear', 'Balão', '']; }
  function planPctBodyRow(A, ns, r, labelValue) {
    var key = labelValue;
    return '<tr><td>' + esc(labelValue) + '</td>' +
      '<td class="dbNumCol">' + esc(String(r.Financiamentos)) + '</td>' +
      '<td class="dbNumCol">' + esc(String(r.Linear)) + '</td>' +
      '<td class="dbNumCol">' + esc(String(r.Balao)) + '</td>' +
      '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
      detailRowHtml(ns, key, 5, [
        { label: 'Percentuais', items: [
          { label: 'Linear %', value: esc(A.pct(r.LinearPct)) },
          { label: 'Balão %', value: esc(A.pct(r.BalaoPct)) }
        ] },
        { label: 'Coparticipado / Subsidiado / Reversão', items: [
          { label: 'Coparticipado', value: esc(String(r.Coparticipado)) },
          { label: 'Coparticipado %', value: esc(A.pct(r.CoparticipadoPct)) },
          { label: 'Subsidiado', value: esc(String(r.Subsidiado)) },
          { label: 'Subsidiado %', value: esc(A.pct(r.SubsidiadoPct)) },
          { label: 'Reversão', value: esc(String(r.Reversao)) },
          { label: 'Reversão %', value: esc(A.pct(r.ReversaoPct)) }
        ] }
      ]);
  }
  function planPctTableHtml(A, ns, labelHeader, rows, labelKey) {
    var body = rows.map(function (r) { return planPctBodyRow(A, ns, r, r[labelKey]); }).join('');
    return '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' +
      headerRow(planPctPrimaryHeaders(labelHeader), 1) +
      '</tr></thead><tbody>' + (body || '<tr><td colspan="5" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  function planClassificationHtml(A, counts) {
    return '<h2 style="margin-top:0">Classificação dos Planos</h2>' +
      '<div class="dbPlanGrid">' + ['SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO', 'BALÃO', 'LINEAR'].map(function (t) { return planCardHtml(A, t, counts[t]); }).join('') + '</div>' +
      '<p class="dbMuted">Classificação oficial por operação, mesma prioridade de Análise F&I do Grupo e Coparticipado: Código IF 999 ou SUBSIDIADO; Código IF 777 ou REVERSÃO; TC Devolvida 1 ou COPARTICIPADO; Balão PMT maior que zero; demais = LINEAR. Faz parte da Análise por Modelos em produção (mesma seção/aba real), não uma visão geral separada.</p>';
  }

  function modelAnalysisHtml(A, results, counts) {
    var modelRows = A.modelRowsUnified(results, currentFamily);
    var planRows = A.planRowsByModel(results, currentFamily);
    // PORTAL-NEXT-07.4.1 — merge Subsidiado/Coparticipado counts (already
    // extracted, already computed by planRowsByModel for this same family)
    // onto modelRowsUnified's rows by matching Modelo, so the PLANOS detail
    // group can show all 5 categories. Presentation-only merge — neither
    // function's own output is altered, no new calculation introduced. A
    // model with no matching planRows entry (not in FAMILY_MODELS' static
    // list) gets 0 for both, consistent with how that model already has no
    // row at all in the "Quantidade por tipo de plano / Modelo" table.
    var planByModelo = {};
    planRows.forEach(function (r) { planByModelo[r.Modelo] = r; });
    modelRows.forEach(function (r) {
      var p = planByModelo[r.Modelo];
      r.subsidiadoQtd = p ? p.Subsidiado : 0;
      r.coparticipadoQtd = p ? p.Coparticipado : 0;
    });
    var planTotalRows = A.planTotalRowsForFamily(results, currentFamily);
    var planStoreRows = A.planRowsByStoreForFamily(results, currentFamily);
    var specialRows = A.specialPlanDetailRows(results, currentFamily);
    var tritonRows = A.inconsistenciaTritonRows(results);

    var specialNs = 'specialPlan';
    var specialBody = specialRows.map(function (r, i) {
      var key = r.Loja + '-' + r.Modelo + '-' + i;
      return '<tr><td>' + esc(r.Loja) + '</td><td>' + esc(r.Modelo) + '</td><td>' + esc(r.Plano) + '</td>' +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(specialNs, key) + '</td></tr>' +
        detailRowHtml(specialNs, key, 4, [
          { label: 'Detalhe', items: [
            { label: 'Cliente', value: esc(r.Cliente) },
            { label: 'Produção', value: esc(A.money(r.Producao)) },
            { label: 'Receita', value: esc(A.money(r.Receita)) }
          ] }
        ]);
    }).join('');

    var tritonHtml = '';
    if (tritonRows.length) {
      var tritonBody = tritonRows.map(function (r) {
        return '<tr><td>' + esc(r.Base) + '</td><td>' + esc(r.Cliente) + '</td><td>' + esc(r.ModeloOriginal) + '</td><td>' + esc(r.Vendedor) + '</td></tr>';
      }).join('');
      tritonHtml = '<h3 class="dbSubHeading">Inconsistências TRITON</h3>' +
        '<p class="dbMuted">Registros classificados como TRITON com o modelo original divergente entre as bases — sinalizado, não corrigido automaticamente.</p>' +
        tableHtml(['Base', 'Cliente', 'Modelo original', 'Vendedor'], tritonBody ? [tritonBody] : [], 1, true);
    }

    return '<div class="dbModelSection">' +
      planClassificationHtml(A, counts) +
      '<h2>Análise por Modelos (Novos)</h2>' +
      '<p class="dbMuted">Selecione uma família para abrir os indicadores específicos dos modelos Novos.</p>' +
      vehicleSelectorHtml() +
      familyMetricGridHtml(A, results, modelRows) +
      '<h3 class="dbSubHeading">' + esc(currentFamily) + ' · Indicadores por modelo</h3>' +
      '<p class="dbMuted">Volume/Financiamentos/Penetração por modelo — clique em "+ Detalhes" para abrir Produção/Receita/Ticket/Retorno/Parcelamento (Prazo Médio, Parcela Média)/Entrada/Planos (Qtd Linear/Balão/Reversão, Balão Médio). Nenhuma métrica fica escondida, sem rolagem lateral.</p>' +
      modelPrimaryDetailTableHtml(A, modelRows) +
      tritonHtml +
      '<h3 class="dbSubHeading">' + esc(currentFamily) + ' · Resumo tipos de plano</h3>' +
      planPctTableHtml(A, 'planTotal', 'Família', planTotalRows, 'Família') +
      '<h3 class="dbSubHeading">' + esc(currentFamily) + ' · Quantidade por tipo de plano / Modelo</h3>' +
      planPctTableHtml(A, 'planModel', 'Modelo', planRows, 'Modelo') +
      '<h3 class="dbSubHeading">' + esc(currentFamily) + ' · Quantidade por tipo de plano / Loja</h3>' +
      planPctTableHtml(A, 'planStore', 'Loja', planStoreRows, 'Loja') +
      '<h3 class="dbSubHeading">' + esc(currentFamily) + ' · Detalhe Coparticipado / Subsidiado / Reversão</h3>' +
      expandableTableHtml(['Loja', 'Modelo', 'Plano'], 3, specialBody ? [specialBody] : [], 4) +
      '</div>';
  }

  function rankingRowHtml(A, list, kind) {
    var ns = 'ranking-' + kind;
    return list.map(function (r, i) {
      var nome = r.Nome, sub = '';
      if (kind === 'vendedor') {
        var parts = String(r.Nome || '').split(' | ');
        nome = parts[0] || r.Nome;
        sub = parts.length > 1 ? parts.slice(1).join(' · ') : '';
      }
      var key = kind + '-' + i;
      return '<tr><td>' + (i + 1) + 'º</td><td>' + esc(nome) + (sub ? '<div class="dbTableSub">' + esc(sub) + '</div>' : '') + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.vendas)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.fin)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.money(r.receitaTotal)) + '</td>' +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
        detailRowHtml(ns, key, 6, [
          { label: 'Detalhe', items: [
            { label: 'Penetração', value: esc(A.pct(r.penetracao)) },
            { label: 'Produção', value: esc(A.money(r.producao)) },
            { label: 'Retorno', value: esc(A.pct(r.retorno)) }
          ] }
        ]);
    }).join('');
  }

  function rankingTableHtml(A, title, list, kind) {
    if (!list.length) return '<h3 class="dbSubHeading">' + esc(title) + '</h3><p class="dbMuted">Sem dados.</p>';
    return '<h3 class="dbSubHeading">' + esc(title) + '</h3>' +
      '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' +
      headerRow(['#', 'Nome', 'Vendas', 'Financiamentos', 'Receita Total', ''], 2) +
      '</tr></thead><tbody>' + rankingRowHtml(A, list, kind) + '</tbody></table></div>';
  }

  function rankingHtml(A, out, salesView, finsView) {
    var vendedores = A.rankingFromViews(salesView, finsView, 'vendedor').slice(0, 10);
    var lojas = A.rankingFromViews(salesView, finsView, 'loja').slice(0, 10);
    var depts = A.rankingFromViews(salesView, finsView, 'dept').slice(0, 10);
    return '<div class="dbRankingSection">' +
      '<h2 style="margin-top:0">Ranking — ' + esc(currentDeptView) + '</h2>' +
      '<p class="dbMuted">Top 10, ordenado por maior Receita Total captada no período selecionado.</p>' +
      rankingTableHtml(A, 'Vendedores', vendedores, 'vendedor') +
      rankingTableHtml(A, 'Lojas', lojas, 'loja') +
      rankingTableHtml(A, 'Departamentos', depts, 'dept') +
      '</div>';
  }

  function novosLojaHtml(A, out) {
    var rows = A.buildNovosLojaRows(out);
    var ns = 'novosLoja';
    var body = rows.map(function (r, i) {
      var cls = r._total ? ' class="dbTotalRow"' : '';
      var key = r._total ? 'total' : (r.Loja + '-' + i);
      return '<tr' + cls + '><td>' + esc(r.Loja) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Vendidos)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Financiados)) + '</td>' +
        '<td>' + esc(r.PlanoDestaque || '-') + '</td>' +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
        detailRowHtml(ns, key, 5, [
          { label: 'Planos', items: [
            { label: 'Balão', value: esc(String(r.Balao)) },
            { label: '% Balão', value: esc(A.pct(r.BalaoPct)) },
            { label: 'Subsidiada', value: esc(String(r.Subsidiada)) },
            { label: 'Coparticipada', value: esc(String(r.Coparticipada)) },
            { label: 'Reversão', value: esc(String(r.Reversao)) },
            { label: 'Linear', value: esc(String(r.Linear)) }
          ] }
        ]);
    }).join('');
    return '<div class="dbNovosLojaSection">' +
      '<h2 style="margin-top:0">Novos por Loja</h2>' +
      '<p class="dbMuted">Leitura por loja/unidade considerando apenas veículos Novos, respeitando o período selecionado.</p>' +
      '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' +
      headerRow(['Loja', 'Vendidos', 'Financiados', 'Plano Destaque', ''], 1) +
      '</tr></thead><tbody>' + body + '</tbody></table></div>' +
      '</div>';
  }

  function render() {
    var A = window.NX_DASHBI_ADAPTER;
    var input = buildFixtureInput(currentFixtureId);
    var out = A.compute(input);
    var panel = document.getElementById('dbPanel');

    if (out.blocked) {
      panel.innerHTML = '<div class="dbBlockedNotice"><b>Atenção:</b> existem ' + out.missingSellers.length +
        ' vendedor(es)/NBS não localizados na Base de Vendedores: ' + out.missingSellers.map(esc).join(', ') +
        '. A produção real também interrompe o processamento neste caso (mesmo comportamento reproduzido aqui — nenhum resultado parcial é exibido).</div>';
      return;
    }

    var kpi = A.kpiMetricsFor(out, currentDeptView);
    var period = { min: null, max: null };
    var closed = false;
    if (currentPreset === 'CUSTOM' || currentPreset === 'lastMonth') {
      closed = A.isClosedMonthPeriod({ min: new Date(currentDateStart + 'T00:00:00'), max: new Date(currentDateEnd + 'T00:00:00') });
    }

    var counts = { LINEAR: 0, 'BALÃO': 0, COPARTICIPADO: 0, SUBSIDIADO: 0, 'REVERSÃO': 0 };
    (out.fins || []).forEach(function (f) {
      var k = A.planoKeyOperacao(f);
      counts[k] = (counts[k] || 0) + 1;
    });

    var salesView = currentDeptView === 'Grupo' ? out.sales : out.sales.filter(function (x) { return x.dept === currentDeptView; });
    var finsView = currentDeptView === 'Grupo' ? out.fins : out.fins.filter(function (x) { return x.dept === currentDeptView; });

    // Reset to a valid mode if the current one is unavailable in this view
    // (e.g. leaving Novos while Model Analysis or Novos por Loja was active).
    // Production's own code (updateModelosTabVisibility) only wires this
    // fallback for the Modelos tab, not for Novos por Loja -- a real,
    // asymmetric gap confirmed by direct source read, not a deliberate rule
    // (Novos por Loja was added in a later UX iteration and the same
    // fallback branch was never extended to it). V2 applies the fallback
    // uniformly to both, closing that gap rather than reproducing it,
    // per this Wave's explicit "no blank page, no stale content" gate.
    if (modesForView(currentDeptView).indexOf(currentMode) === -1) currentMode = 'overview';

    var complementaryHtml = '';
    if (currentMode === 'modelos') complementaryHtml = modelAnalysisHtml(A, out, counts);
    else if (currentMode === 'ranking') complementaryHtml = rankingHtml(A, out, salesView, finsView);
    else if (currentMode === 'novosLoja') complementaryHtml = novosLojaHtml(A, out);
    else complementaryHtml = '<p class="dbMuted dbModeHint">Selecione uma análise complementar acima (Análise por Modelos, Ranking ou Novos por Loja) para abrir seus indicadores.</p>';

    var html =
      '<div class="dbKpiGridPrimary">' +
      kpiPrimary('Vendas', kpi.vendas, currentDeptView) +
      kpiPrimary('Financiamentos', kpi.fins, 'Share ' + A.pct(kpi.share)) +
      kpiPrimary('Produção', A.money(kpi.producao)) +
      kpiPrimary('Receita', A.money(kpi.receita), 'SPF ' + A.money(kpi.receitaSPF) + ' · Total ' + A.money(kpi.receitaTotal)) +
      kpiPrimary('Retorno', A.pct(kpi.retorno)) +
      '</div>' +
      (closed ? '<div class="dbFechamentoBar"><span class="dbFechamento">FECHAMENTO</span><span class="dbMuted">Período filtrado corresponde a um mês fechado.</span></div>' : '') +

      '<h2>Vendas e Financiamentos por Loja</h2>' + storeTableHtml(A, out) +

      '<h2>Vendas e Financiamentos por Vendedor</h2>' + sellerTableHtml(A, out) +

      modeNavHtml() +
      complementaryHtml +

      '<h2>Diagnóstico (dev only)</h2>' +
      '<p class="dbMuted">DADOS DE TESTE — não faz parte da experiência final. sourceInfo: <span class="dbDiagJson">' + esc(JSON.stringify(out.sourceInfo)) + '</span></p>' +
      '<p class="dbMuted">Entrada (bases novas): total financiamentos ' + out.entradaDiagnostic.totalFinanciamentos +
      ' · chassis localizados ' + out.entradaDiagnostic.chassisLocalizados +
      ' · não localizados ' + out.entradaDiagnostic.chassisNaoLocalizados +
      ' · taxa de sucesso ' + A.pct(out.entradaDiagnostic.taxaSucesso) + '</p>';

    panel.innerHTML = html;
  }

  function applyPresetAndRender(preset) {
    currentPreset = preset;
    var today = new Date(2026, 7, 30); // fixed reference date (NEXT_LOCAL fixture mode -- deterministic)
    var start, end = today;
    if (preset === 'currentMonth') start = new Date(today.getFullYear(), today.getMonth(), 1);
    else if (preset === 'lastMonth') { start = new Date(today.getFullYear(), today.getMonth() - 1, 1); end = new Date(today.getFullYear(), today.getMonth(), 0); }
    else if (preset === 'last6') start = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    else if (preset === 'lastYear') start = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
    if (start) {
      currentDateStart = start.toISOString().slice(0, 10);
      currentDateEnd = end.toISOString().slice(0, 10);
      document.getElementById('dbDateStart').value = currentDateStart;
      document.getElementById('dbDateEnd').value = currentDateEnd;
    }
    document.querySelectorAll('.dbPresetBtn').forEach(function (b) { b.classList.toggle('dbBtnActive', b.dataset.preset === preset); });
    render();
  }

  function wireEvents() {
    document.getElementById('dbFixtureSelect').addEventListener('change', function (e) { currentFixtureId = e.target.value; render(); });
    document.getElementById('dbDateStart').addEventListener('change', function (e) { currentDateStart = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.dbPresetBtn').forEach(function (b) { b.classList.remove('dbBtnActive'); }); render(); });
    document.getElementById('dbDateEnd').addEventListener('change', function (e) { currentDateEnd = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.dbPresetBtn').forEach(function (b) { b.classList.remove('dbBtnActive'); }); render(); });
    document.querySelectorAll('.dbPresetBtn').forEach(function (btn) { btn.addEventListener('click', function () { applyPresetAndRender(btn.dataset.preset); }); });
    document.querySelectorAll('.dbViewBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        currentDeptView = btn.dataset.view;
        document.querySelectorAll('.dbViewBtn').forEach(function (b) { b.classList.toggle('dbBtnActive', b === btn); });
        render();
      });
    });
    // .dbVehicleCard is re-created on every render() (it lives inside the
    // Model Analysis section, not the static filter bar), so it is wired
    // via delegation on the persistent #dbPanel container rather than a
    // one-time querySelectorAll like the static filter controls above.
    document.getElementById('dbPanel').addEventListener('click', function (e) {
      var btn = e.target.closest('.dbVehicleCard');
      if (!btn) return;
      currentFamily = btn.dataset.family;
      // Gate 16/44 (PORTAL-NEXT-07.4): reset expanded model detail rows on
      // family switch — a safe default, since no production/V2 authority
      // supports persisting expansion across a different model set.
      resetExpanded('modelIndicators');
      render();
    });
    // .dbModeBtn is re-created every render() too (its own available set
    // depends on currentDeptView), same delegation pattern as the vehicle
    // cards above.
    document.getElementById('dbPanel').addEventListener('click', function (e) {
      var btn = e.target.closest('.dbModeBtn');
      if (!btn) return;
      currentMode = btn.dataset.mode;
      render();
    });
    // PORTAL-NEXT-07.4 — shared "+ Detalhes" toggle, delegated (every
    // detail button is re-created on each render()).
    document.getElementById('dbPanel').addEventListener('click', function (e) {
      var btn = e.target.closest('.dbDetailToggle');
      if (!btn) return;
      toggleExpanded(btn.dataset.detailNs, btn.dataset.detailKey);
      render();
    });
  }

  window.NX_DASHBI_PAGE = {
    render: function (outlet) {
      return loadFixtures().then(function () {
        var fixtureOptions = fixturesData.map(function (c) { return '<option value="' + esc(c.id) + '"' + (c.id === currentFixtureId ? ' selected' : '') + '>' + esc(c.id) + '</option>'; }).join('');
        outlet.innerHTML =
          '<div class="dbPage">' +
          '<div class="dbHeader"><div><h1>Análise Geral do Grupo</h1><p>Visão analítica geral do Grupo Brabus Mitsubishi.</p></div></div>' +
          '<div class="dbFixtureBar"><span class="dbFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
          '<label for="dbFixtureSelect">fixture:</label><select id="dbFixtureSelect">' + fixtureOptions + '</select></div>' +
          '<div class="dbFilters">' +
          '<div class="dbField"><label>Visão</label><div class="dbViewGroup">' +
          '<button type="button" class="dbBtn dbViewBtn dbBtnActive" data-view="Grupo">Grupo</button>' +
          '<button type="button" class="dbBtn dbViewBtn" data-view="Novos">Novos</button>' +
          '<button type="button" class="dbBtn dbViewBtn" data-view="Seminovos">Seminovos</button>' +
          '</div></div>' +
          '<div class="dbField"><label>Período rápido</label><div class="dbPresetGroup">' +
          '<button type="button" class="dbBtn dbPresetBtn" data-preset="currentMonth">Mês atual</button>' +
          '<button type="button" class="dbBtn dbPresetBtn" data-preset="lastMonth">Mês anterior</button>' +
          '<button type="button" class="dbBtn dbPresetBtn" data-preset="last6">Últimos 6 meses</button>' +
          '<button type="button" class="dbBtn dbPresetBtn" data-preset="lastYear">Último ano</button>' +
          '</div></div>' +
          '<div class="dbField"><label for="dbDateStart">Data inicial</label><input id="dbDateStart" type="date" value="' + currentDateStart + '"></div>' +
          '<div class="dbField"><label for="dbDateEnd">Data final</label><input id="dbDateEnd" type="date" value="' + currentDateEnd + '"></div>' +
          '</div>' +
          '<div id="dbPanel"></div>' +
          '</div>';
        wireEvents();
        render();
      });
    }
  };
})();
