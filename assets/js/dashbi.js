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

  // Dashbi Phase 2 (Real Data Integration Foundation) -- the ONE place
  // transport is decided, same rule as gestao.js's own isRealTransport()
  // (Gate 4 there): real whenever Auth Foundation has a real session
  // configured, fixture otherwise. renderSeq/realOut guard against a
  // stale async response overwriting a newer one (period/preset changes
  // invalidate realOut and bump renderSeq via loadReal()).
  function isRealTransport() {
    return !!(window.NX_AUTH && window.NX_AUTH.isAuthConfigured);
  }
  var renderSeq = 0;
  var realOut = null;

  var STATE_COPY = {
    PERMISSION_DENIED: { title: 'Sem permissão', body: 'Sua conta não tem acesso a esta análise.' },
    INVALID_FILTER: { title: 'Filtro inválido', body: 'Verifique o período selecionado.' },
    SCOPE_EMPTY: { title: 'Nenhum lote disponível', body: 'Ainda não há dados validados para análise.' },
    BACKEND_ERROR: { title: 'Não foi possível carregar', body: 'Não foi possível carregar esse período. Tente selecionar um intervalo menor ou tente novamente.' },
    SESSION_EXPIRED: { title: 'Sessão expirada', body: 'Entre novamente para continuar.' }
  };
  function loadingHtml() {
    return '<div class="modLoadingState"><span class="modLoadingDot"></span>Carregando indicadores...</div>';
  }
  function errorStateHtml(state, message) {
    var copy = STATE_COPY[state] || STATE_COPY.BACKEND_ERROR;
    return '<div class="modErrorState"><div class="modStateTitle">' + esc(copy.title) + '</div>' + esc(copy.body) + '</div>';
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

  // PORTAL-NEXT-07.6.4 — idSuffix (optional) keeps the desktop and
  // mobile-card renderers' detail-panel DOM ids distinct when both
  // exist in the document at once (one visible, one display:none) —
  // every pre-existing call site omits it and gets byte-identical
  // output to before.
  function detailDomId(ns, key, idSuffix) { return 'db-detail-' + ns + '-' + String(key).replace(/[^a-zA-Z0-9_-]/g, '_') + (idSuffix || ''); }

  function detailToggleHtml(ns, key, idSuffix) {
    var open = isExpanded(ns, key);
    return '<button type="button" class="dbDetailToggle" data-detail-ns="' + esc(ns) + '" data-detail-key="' + esc(String(key)) +
      '" aria-expanded="' + (open ? 'true' : 'false') + '" aria-controls="' + detailDomId(ns, key, idSuffix) + '">' + (open ? '− Detalhes' : '+ Detalhes') + '</button>';
  }

  // groups: [{label, items:[{label, value}]}] — value is pre-formatted HTML/text.
  function detailGroupsHtml(groups) {
    return groups.map(function (g) {
      return '<div class="dbDetailGroup"><div class="dbDetailGroupLabel">' + esc(g.label) + '</div>' +
        '<div class="dbDetailGroupItems">' + g.items.map(function (it) {
          return '<div class="dbDetailItem"><span class="dbDetailK">' + esc(it.label) + '</span><span class="dbDetailV">' + it.value + '</span></div>';
        }).join('') + '</div></div>';
    }).join('');
  }
  function detailRowHtml(ns, key, colspan, groups) {
    if (!isExpanded(ns, key)) return '';
    return '<tr id="' + detailDomId(ns, key) + '" class="dbDetailRow"><td colspan="' + colspan + '"><div class="dbDetailPanel">' + detailGroupsHtml(groups) + '</div></td></tr>';
  }
  // PORTAL-NEXT-07.5 — same detail-panel body, without the <tr>/<td> wrapper,
  // for the KPI grid (a div grid, not a table) — reuses the identical
  // dbDetailPanel/dbDetailGroup markup and expandedKeys state machinery.
  // PORTAL-NEXT-07.6.4 — also reused as-is for every mobile card's own
  // detail panel (idSuffix keeps its DOM id distinct from the desktop
  // row's, since both share the same ns/key toggle state).
  function kpiDetailPanelHtml(ns, key, groups, idSuffix) {
    if (!isExpanded(ns, key)) return '';
    return '<div id="' + detailDomId(ns, key, idSuffix) + '" class="dbDetailPanel dbKpiDetailPanel">' + detailGroupsHtml(groups) + '</div>';
  }

  // PORTAL-NEXT-07.6.4 — human UAT rejected transforming the desktop
  // <table> into a mobile layout (07.6/07.6.2/07.6.3), even after that
  // last version was proven correct by every computed-style/DOM check
  // available — the human's actual browser result is authoritative
  // regardless. Strategy changed: a dedicated non-table mobile card
  // renderer, fed by the SAME already-computed row data as the desktop
  // table (no recalculation), for every table that shares this
  // component (store/seller/Ranking/Novos por Loja). Exactly one of
  // .dbDesktopOnly/.dbMobileOnly is visible at a time (dashbi.css);
  // Model Analysis's own tables (frozen, Gate 32) don't use this helper
  // and are untouched.
  function dbMobileField(label, valueHtml, extraClass) {
    return '<div class="dbMobileField' + (extraClass ? ' ' + extraClass : '') + '"><div class="dbMobileLabel">' + esc(label) + '</div><div class="dbMobileValue">' + valueHtml + '</div></div>';
  }
  function dbMobileCard(ns, key, identityText, subText, primaryFieldsHtml, detailGroups) {
    return '<div class="dbMobileCard">' +
      '<div class="dbMobileIdentity">' + esc(identityText) + '</div>' +
      (subText ? '<div class="dbMobileSub">' + esc(subText) + '</div>' : '') +
      '<div class="dbMobileFieldGrid">' + primaryFieldsHtml + '</div>' +
      detailToggleHtml(ns, key, '-m') +
      kpiDetailPanelHtml(ns, key, detailGroups, '-m') +
      '</div>';
  }
  function dbMobileListHtml(cards) {
    return '<div class="dbMobileOnly">' + cards.join('') + '</div>';
  }

  // Wave 3A: top-tier KPI grid migrated to the shared module-system.css
  // primitives (.modKpiCard/.modKpiLabel/.modKpiValue/.modKpiHint +
  // semantic modifiers) — visual result unchanged (same border/padding/
  // type scale the old .dbKpiCardPrimary/.dbK/.dbV/.dbHint rules already
  // produced), only the class vocabulary is now shared. Every OTHER
  // dashbi.css class (.dbPlanCard, .dbEntradaCard, .dbFamilyMetricBox,
  // tables, mobile cards, Model Analysis, etc.) is untouched — these 3
  // functions are the only callers of dbKpiCardPrimary/dbK/dbV/dbHint,
  // confirmed via grep before this edit.
  function kpiPrimary(label, value, hint) {
    return '<div class="modKpiCard"><div class="modKpiLabel">' + esc(label) + '</div><div class="modKpiValue">' + value + '</div>' + (hint ? '<div class="modKpiHint">' + hint + '</div>' : '') + '</div>';
  }

  // PORTAL-NEXT-07.5 — Share/Penetração threshold reconfirmed against the
  // current production authority (pctPenetracao, origin/main lines
  // 2788-2794, docs/DASHBI-KPI-CONTRACT.md): v<0.40 -> baixa, else ok. Not
  // assumed from a prior wave — re-checked against source this Wave.
  function shareEmphasisClass(v) { return v < 0.40 ? 'modKpiCardCritical' : 'modKpiCardSuccess'; }

  function kpiShareCardHtml(A, v) {
    var cls = shareEmphasisClass(v);
    var statusLabel = v < 0.40 ? 'Abaixo da meta (40%)' : 'Dentro da meta';
    return '<div class="modKpiCard ' + cls + '"><div class="modKpiLabel">Share</div><div class="modKpiValue">' + esc(A.pct(v)) + '</div><div class="modKpiHint">' + esc(statusLabel) + '</div></div>';
  }

  function kpiReceitaTotalCardHtml(A, v) {
    return '<div class="modKpiCard modKpiCardInfo"><div class="modKpiLabel">Receita Total</div><div class="modKpiValue">' + esc(A.money(v)) + '</div></div>';
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
  // PORTAL-NEXT-07.5 — a primary cell may be {raw:'<html>'} to carry
  // pre-formatted markup (e.g. the Share emphasis span) through unescaped;
  // every previously-existing caller keeps passing plain strings/numbers,
  // so cellHtml()'s plain-string branch is byte-identical to the old
  // behavior for them.
  function cellHtml(c) { return (c && typeof c === 'object' && 'raw' in c) ? c.raw : esc(String(c)); }

  // PORTAL-NEXT-07.5 — headers (optional) stamps each primary <td> with a
  // data-th label, consumed only by the opt-in .dbTableStackable mobile
  // recomposition (see dashbi.css) for tables carrying the new 5-metric
  // primary hierarchy. Omitted (undefined), every existing caller's markup
  // is byte-identical to before.
  function expandableRow(ns, key, primaryCells, numericFrom, colspan, detailGroups, headers) {
    function th(i) { return headers ? ' data-th="' + esc(headers[i]) + '"' : ''; }
    return '<tr><td' + th(0) + '>' + cellHtml(primaryCells[0]) + '</td>' +
      primaryCells.slice(1).map(function (c, i) { return '<td' + th(i + 1) + (i + 1 >= numericFrom ? ' class="dbNumCol"' : '') + '>' + cellHtml(c) + '</td>'; }).join('') +
      '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
      detailRowHtml(ns, key, colspan, detailGroups);
  }

  function expandableTableHtml(headers, numericFrom, bodyRowsHtml, colCount) {
    return '<div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' + headerRow(headers.concat(['']), numericFrom) + '</tr></thead>' +
      '<tbody>' + (bodyRowsHtml.length ? bodyRowsHtml.join('') : '<tr><td colspan="' + colCount + '" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  // PORTAL-NEXT-07.5 — retorno derived here with the exact same formula
  // already used by rowsFromAgg()/rankingFromViews() (receitaTotal/producao)
  // — a presentational reuse of an existing formula against data that was
  // already on finLoja/finVendDept, not a new business rule.
  function retornoFromFin(f) { return f.producao ? (f.receitaTotal || 0) / f.producao : 0; }

  var STORE_HEADERS = ['Loja', 'Vendas', 'Financiamentos', 'Share', 'Produção Total', 'Receita Total'];
  var SELLER_HEADERS = ['Vendedor', 'Vendas', 'Financiamentos', 'Share', 'Produção Total', 'Receita Total'];

  // PORTAL-NEXT-07.6.4 — shared by store/seller: the 5 primary metrics
  // as mobile-card fields (Vendas+Financiamentos paired, per the human's
  // own spec — both always a short integer; Share/Produção Total/
  // Receita Total each full width), built from the SAME v/f/share
  // values the desktop row already computed. No recalculation.
  function dbPrimaryMetricFieldsHtml(A, v, f, share) {
    return dbMobileField('Vendas', String(v.qtd), 'dbMobileFieldPair') +
      dbMobileField('Financiamentos', String(f.qtd), 'dbMobileFieldPair') +
      dbMobileField('Share', penetracaoCellHtml(A, share), 'dbMobileFieldEmph') +
      dbMobileField('Produção Total', esc(A.money(f.producao || 0))) +
      dbMobileField('Receita Total', esc(A.money(f.receitaTotal || 0)));
  }

  function storeTableHtml(A, results) {
    var A_ = results.aggs;
    var lojas = Object.keys(A_.vendasLoja);
    var finLojaMap = A_.finLoja;
    var ns = 'storeTable';
    var desktopRows = [];
    var mobileCards = [];
    lojas.sort(function (a, b) { return (A_.vendasLoja[b].qtd || 0) - (A_.vendasLoja[a].qtd || 0); }).forEach(function (loja) {
      var v = A_.vendasLoja[loja] || { qtd: 0 };
      var f = finLojaMap[loja] || { qtd: 0, producao: 0, receita: 0, receitaSPF: 0, receitaTotal: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      var detailGroups = [
        { label: 'Financeiro (complementar)', items: [
          { label: 'Receita', value: esc(A.money(f.receita || 0)) },
          { label: 'Receita SPF', value: esc(A.money(f.receitaSPF || 0)) },
          { label: 'Retorno', value: esc(A.pct(retornoFromFin(f))) }
        ] }
      ];
      desktopRows.push(expandableRow(ns, loja, [loja, v.qtd, f.qtd, { raw: penetracaoCellHtml(A, share) }, A.money(f.producao || 0), A.money(f.receitaTotal || 0)], 1, 7, detailGroups, STORE_HEADERS));
      mobileCards.push(dbMobileCard(ns, loja, loja, null, dbPrimaryMetricFieldsHtml(A, v, f, share), detailGroups));
    });
    return '<div class="dbDesktopOnly">' + expandableTableHtml(STORE_HEADERS, 1, desktopRows, 7) + '</div>' + dbMobileListHtml(mobileCards);
  }

  function sellerTableHtml(A, results) {
    var A_ = results.aggs;
    var keys = Object.keys(A_.vendasVendDept);
    var ns = 'sellerTable';
    var desktopRows = [];
    var mobileCards = [];
    keys.sort(function (a, b) { return (A_.vendasVendDept[b].qtd || 0) - (A_.vendasVendDept[a].qtd || 0); }).forEach(function (key) {
      var parts = key.split(' | ');
      var v = A_.vendasVendDept[key] || { qtd: 0 };
      var f = A_.finVendDept[key] || { qtd: 0, producao: 0, receita: 0, receitaSPF: 0, receitaTotal: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      var detailGroups = [
        { label: 'Detalhe', items: [
          { label: 'Depto', value: esc(parts[1] || '') },
          { label: 'Receita', value: esc(A.money(f.receita || 0)) },
          { label: 'Receita SPF', value: esc(A.money(f.receitaSPF || 0)) },
          { label: 'Retorno', value: esc(A.pct(retornoFromFin(f))) }
        ] }
      ];
      desktopRows.push(expandableRow(ns, key, [parts[0], v.qtd, f.qtd, { raw: penetracaoCellHtml(A, share) }, A.money(f.producao || 0), A.money(f.receitaTotal || 0)], 1, 7, detailGroups, SELLER_HEADERS));
      mobileCards.push(dbMobileCard(ns, key, parts[0], parts[1] || null, dbPrimaryMetricFieldsHtml(A, v, f, share), detailGroups));
    });
    return '<div class="dbDesktopOnly">' + expandableTableHtml(SELLER_HEADERS, 1, desktopRows, 7) + '</div>' + dbMobileListHtml(mobileCards);
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

  function planClassificationHtml(A, counts) {
    return '<h2 style="margin-top:0">Classificação dos Planos</h2>' +
      '<div class="dbPlanGrid">' + ['SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO', 'BALÃO', 'LINEAR'].map(function (t) { return planCardHtml(A, t, counts[t]); }).join('') + '</div>' +
      '<p class="dbMuted">Classificação oficial por operação, mesma prioridade de Análise F&I do Grupo e Coparticipado: Código IF 999 ou SUBSIDIADO; Código IF 777 ou REVERSÃO; TC Devolvida 1 ou COPARTICIPADO; Balão PMT maior que zero; demais = LINEAR. Faz parte da Análise por Modelos em produção (mesma seção/aba real), não uma visão geral separada.</p>';
  }

  function modelAnalysisHtml(A, results, counts, isReal) {
    // Dashbi Phase 2, Gate B3/B7: real transport builds modelRows DIRECTLY
    // from operational_model_metrics's own real per-model aggregates
    // (dashbi-real-view-model.js) rather than through modelRowsUnified()'s
    // fixture-oriented per-transaction reconstruction (which depends on raw
    // fields -- parcelas/pmt/chassi/valorVenda -- the real RPC deliberately
    // never returns). Real rows already carry correct subsidiadoQtd/
    // coparticipadoQtd (from the real plan_breakdown), so the fixture-only
    // planRowsByModel merge below must be skipped for real transport —
    // running it would silently zero those fields back out (planRowsByModel
    // reads results.fins, which real transport never populates with a
    // per-model dimension).
    var modelRows = isReal
      ? window.NX_DASHBI_REAL_VIEW_MODEL.modelRowsForFamily(results, currentFamily)
      : A.modelRowsUnified(results, currentFamily);
    if (!isReal) {
      var planRows = A.planRowsByModel(results, currentFamily);
      // PORTAL-NEXT-07.4.1 — merge Subsidiado/Coparticipado counts (already
      // extracted, already computed by planRowsByModel for this same family)
      // onto modelRowsUnified's rows by matching Modelo, so the PLANOS detail
      // group can show all 5 categories. Presentation-only merge — neither
      // function's own output is altered, no new calculation introduced. A
      // model with no matching planRows entry (not in FAMILY_MODELS' static
      // list) gets 0 for both. PORTAL-NEXT-07.5.1 removed this family's own
      // "Quantidade por tipo de plano / Modelo" table (redundant with this
      // same merge, per explicit human decision — see
      // docs/MODEL-ANALYSIS-REDUNDANT-SECTIONS-REMOVAL.md); planRows/
      // planRowsByModel itself stays, still required by this merge.
      var planByModelo = {};
      planRows.forEach(function (r) { planByModelo[r.Modelo] = r; });
      modelRows.forEach(function (r) {
        var p = planByModelo[r.Modelo];
        r.subsidiadoQtd = p ? p.Subsidiado : 0;
        r.coparticipadoQtd = p ? p.Coparticipado : 0;
      });
    }
    // inconsistenciaTritonRows() looks for a literal "INCONSISTÊNCIA
    // TRITON" sentinel modelo value that only Base01/Base02 cross-
    // validation (fixture-only, no equivalent for a single real source of
    // truth) ever produces -- safe to call unchanged, always empty for real.
    var tritonRows = A.inconsistenciaTritonRows(results);

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
      '</div>';
  }

  function rankingRowHtml(A, list, kind) {
    var ns = 'ranking-' + kind;
    var rows = [];
    var cards = [];
    list.forEach(function (r, i) {
      var nome = r.Nome, sub = '';
      if (kind === 'vendedor') {
        var parts = String(r.Nome || '').split(' | ');
        nome = parts[0] || r.Nome;
        sub = parts.length > 1 ? parts.slice(1).join(' · ') : '';
      }
      var key = kind + '-' + i;
      var detailGroups = [
        { label: 'Detalhe', items: [
          { label: 'Receita', value: esc(A.money(r.receita)) },
          { label: 'Receita SPF', value: esc(A.money(r.receitaSPF)) },
          { label: 'Retorno', value: esc(A.pct(r.retorno)) }
        ] }
      ];
      rows.push('<tr><td data-th="#">' + (i + 1) + 'º</td><td data-th="Nome">' + esc(nome) + (sub ? '<div class="dbTableSub">' + esc(sub) + '</div>' : '') + '</td>' +
        '<td class="dbNumCol" data-th="Vendas">' + esc(String(r.vendas)) + '</td>' +
        '<td class="dbNumCol" data-th="Financiamentos">' + esc(String(r.fin)) + '</td>' +
        '<td class="dbNumCol" data-th="Share">' + penetracaoCellHtml(A, r.penetracao) + '</td>' +
        '<td class="dbNumCol" data-th="Produção Total">' + esc(A.money(r.producao)) + '</td>' +
        '<td class="dbNumCol" data-th="Receita Total">' + esc(A.money(r.receitaTotal)) + '</td>' +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
        detailRowHtml(ns, key, 8, detailGroups));

      var primaryFieldsHtml =
        dbMobileField('Vendas', esc(String(r.vendas)), 'dbMobileFieldPair') +
        dbMobileField('Financiamentos', esc(String(r.fin)), 'dbMobileFieldPair') +
        dbMobileField('Share', penetracaoCellHtml(A, r.penetracao), 'dbMobileFieldEmph') +
        dbMobileField('Produção Total', esc(A.money(r.producao))) +
        dbMobileField('Receita Total', esc(A.money(r.receitaTotal)));
      cards.push(dbMobileCard(ns, key, (i + 1) + 'º ' + nome, sub || null, primaryFieldsHtml, detailGroups));
    });
    return { rowsHtml: rows.join(''), cards: cards };
  }

  function rankingTableHtml(A, title, list, kind) {
    if (!list.length) return '<h3 class="dbSubHeading">' + esc(title) + '</h3><p class="dbMuted">Sem dados.</p>';
    var built = rankingRowHtml(A, list, kind);
    return '<h3 class="dbSubHeading">' + esc(title) + '</h3>' +
      '<div class="dbDesktopOnly"><div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' +
      headerRow(['#', 'Nome', 'Vendas', 'Financiamentos', 'Share', 'Produção Total', 'Receita Total', ''], 2) +
      '</tr></thead><tbody>' + built.rowsHtml + '</tbody></table></div></div>' +
      dbMobileListHtml(built.cards);
  }

  // PORTAL-NEXT-07.5.2 — human decision: Ranking > Departamentos removed
  // from the rendered UI (not required in the final analytical
  // experience) — presentation-only. A.rankingFromViews() itself is
  // shared with Vendedores/Lojas (kept, called with 'vendedor'/'loja'
  // below) and stays untouched; only the 'dept' call + its render was
  // removed. vendasDept/finDept (the underlying department aggregation
  // in aggregate()) were already unused by any other V2 surface before
  // this change (see docs/DASHBI-ANALYTICAL-HIERARCHY-INVENTORY.md) and
  // remain in the adapter, untouched — no business logic deleted.
  function rankingHtml(A, out, salesView, finsView) {
    var vendedores = A.rankingFromViews(salesView, finsView, 'vendedor').slice(0, 10);
    var lojas = A.rankingFromViews(salesView, finsView, 'loja').slice(0, 10);
    return '<div class="dbRankingSection">' +
      '<h2 style="margin-top:0">Ranking — ' + esc(currentDeptView) + '</h2>' +
      '<p class="dbMuted">Top 10, ordenado por maior Receita Total captada no período selecionado.</p>' +
      rankingTableHtml(A, 'Vendedores', vendedores, 'vendedor') +
      rankingTableHtml(A, 'Lojas', lojas, 'loja') +
      '</div>';
  }

  function novosLojaHtml(A, out) {
    var rows = A.buildNovosLojaRows(out);
    var ns = 'novosLoja';
    var desktopRows = [];
    var mobileCards = [];
    rows.forEach(function (r, i) {
      var cls = r._total ? ' class="dbTotalRow"' : '';
      var key = r._total ? 'total' : (r.Loja + '-' + i);
      var share = r.Vendidos ? r.Financiados / r.Vendidos : 0;
      var detailGroups = [
        { label: 'Planos', items: [
          { label: 'Balão', value: esc(String(r.Balao)) },
          { label: '% Balão', value: esc(A.pct(r.BalaoPct)) },
          { label: 'Subsidiada', value: esc(String(r.Subsidiada)) },
          { label: 'Coparticipada', value: esc(String(r.Coparticipada)) },
          { label: 'Reversão', value: esc(String(r.Reversao)) },
          { label: 'Linear', value: esc(String(r.Linear)) }
        ] }
      ];
      desktopRows.push('<tr' + cls + '><td data-th="Loja">' + esc(r.Loja) + '</td>' +
        '<td class="dbNumCol" data-th="Vendidos">' + esc(String(r.Vendidos)) + '</td>' +
        '<td class="dbNumCol" data-th="Financiados">' + esc(String(r.Financiados)) + '</td>' +
        '<td class="dbNumCol" data-th="Share">' + penetracaoCellHtml(A, share) + '</td>' +
        '<td data-th="Plano Destaque">' + esc(r.PlanoDestaque || '-') + '</td>' +
        '<td class="dbDetailToggleCell">' + detailToggleHtml(ns, key) + '</td></tr>' +
        detailRowHtml(ns, key, 6, detailGroups));

      var primaryFieldsHtml =
        dbMobileField('Vendidos', esc(String(r.Vendidos)), 'dbMobileFieldPair') +
        dbMobileField('Financiados', esc(String(r.Financiados)), 'dbMobileFieldPair') +
        dbMobileField('Share', penetracaoCellHtml(A, share), 'dbMobileFieldEmph') +
        dbMobileField('Plano Destaque', esc(r.PlanoDestaque || '-'));
      var card = dbMobileCard(ns, key, r.Loja, null, primaryFieldsHtml, detailGroups);
      if (r._total) card = card.replace('class="dbMobileCard"', 'class="dbMobileCard dbMobileCardTotal"');
      mobileCards.push(card);
    });
    return '<div class="dbNovosLojaSection">' +
      '<h2 style="margin-top:0">Novos por Loja</h2>' +
      '<p class="dbMuted">Leitura por loja/unidade considerando apenas veículos Novos, respeitando o período selecionado.</p>' +
      '<div class="dbDesktopOnly"><div class="dbTableWrap"><table class="dbTable dbTableExpandable"><thead><tr>' +
      headerRow(['Loja', 'Vendidos', 'Financiados', 'Share', 'Plano Destaque', ''], 1) +
      '</tr></thead><tbody>' + desktopRows.join('') + '</tbody></table></div></div>' +
      dbMobileListHtml(mobileCards) +
      '</div>';
  }

  // Dashbi Phase 2 -- renderPanel draws a given, already-computed `out`
  // (fixture, via A.compute(), or real, via NX_DASHBI_REAL_VIEW_MODEL.
  // buildRealOut()) into #dbPanel. Kept transport-agnostic: every branch
  // that actually differs between fixture/real lives in modelAnalysisHtml
  // (Gate B7) or in the diagnostic footer below, gated by isReal.
  function renderPanel(out, isReal) {
    var A = window.NX_DASHBI_ADAPTER;
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
    if (currentMode === 'modelos') complementaryHtml = modelAnalysisHtml(A, out, counts, isReal);
    else if (currentMode === 'ranking') complementaryHtml = rankingHtml(A, out, salesView, finsView);
    else if (currentMode === 'novosLoja') complementaryHtml = novosLojaHtml(A, out);
    else complementaryHtml = '<p class="dbMuted dbModeHint">Selecione uma análise complementar acima (Análise por Modelos, Ranking ou Novos por Loja) para abrir seus indicadores.</p>';

    var html =
      '<div class="modKpiGrid">' +
      kpiPrimary('Vendas', kpi.vendas, currentDeptView) +
      kpiPrimary('Financiamentos', kpi.fins) +
      kpiShareCardHtml(A, kpi.share) +
      kpiPrimary('Produção Total', A.money(kpi.producao)) +
      kpiReceitaTotalCardHtml(A, kpi.receitaTotal) +
      '</div>' +
      '<div class="dbKpiDetailToggleWrap">' + detailToggleHtml('kpiDetail', 'main') + '</div>' +
      kpiDetailPanelHtml('kpiDetail', 'main', [
        { label: 'Complementares', items: [
          { label: 'Receita', value: esc(A.money(kpi.receita)) },
          { label: 'Receita SPF', value: esc(A.money(kpi.receitaSPF)) },
          { label: 'Retorno Médio', value: esc(A.pct(kpi.retorno)) }
        ] }
      ]) +
      (closed ? '<div class="dbFechamentoBar"><span class="dbFechamento">FECHAMENTO</span><span class="dbMuted">Período filtrado corresponde a um mês fechado.</span></div>' : '') +

      '<h2>Vendas e Financiamentos por Loja</h2>' + storeTableHtml(A, out) +

      '<h2>Vendas e Financiamentos por Vendedor</h2>' + sellerTableHtml(A, out) +

      modeNavHtml() +
      complementaryHtml +

      // Dashbi Phase 2D, Gate 8: DIAGNOSTIC_PRODUCTION_VISIBILITY_DEBT --
      // this footer (like the fixture one below it) is dev/localhost
      // tooling, not user-facing product; gated the same way
      // environment-guard.js's own consumers already are, so it never
      // reaches a real production host. Gate 7: scope.is_master here is
      // the RPC's own internal per-call analytical-scope flag (Dashbi
      // Phase 2D, Gate 3-6 -- proven GROUP_VIEW_EFFECTIVE_SCOPE, not the
      // authenticated identity), never renamed in the raw payload
      // (backend contract untouched -- Gate 7 Option A) but labeled here
      // so it can't be misread as Auth Context's own separate isMaster.
      ((isReal && (!window.NX_ENVIRONMENT || !window.NX_ENVIRONMENT.production))
        ? '<h2>Diagnóstico (dev only)</h2><p class="dbMuted">Fonte: backend real (operational_metrics / operational_model_metrics). "is_master" no escopo abaixo é o escopo analítico efetivo desta chamada (elevação de grupo autorizada pelo servidor), não a identidade autenticada. Escopo: <span class="dbDiagJson">' + esc(JSON.stringify(out.sourceInfo)) + '</span></p>'
        : (isReal ? '' :
          '<h2>Diagnóstico (dev only)</h2>' +
          '<p class="dbMuted">DADOS DE TESTE — não faz parte da experiência final. sourceInfo: <span class="dbDiagJson">' + esc(JSON.stringify(out.sourceInfo)) + '</span></p>' +
          '<p class="dbMuted">Entrada (bases novas): total financiamentos ' + out.entradaDiagnostic.totalFinanciamentos +
          ' · chassis localizados ' + out.entradaDiagnostic.chassisLocalizados +
          ' · não localizados ' + out.entradaDiagnostic.chassisNaoLocalizados +
          ' · taxa de sucesso ' + A.pct(out.entradaDiagnostic.taxaSucesso) + '</p>'));

    panel.innerHTML = html;
  }

  // Dashbi Phase 2, Gate B4/B5/B12 -- render() is the single entry point
  // every UI handler calls. Fixture path stays fully synchronous (Gate C2:
  // no behavior change, no accidental real network call). Real path fetches
  // both RPCs for the CURRENT period (p_start/p_end -- Gate B5, fixes the
  // fixture-era date-filter disconnect where currentDateStart/End never
  // actually constrained computation) and caches the result in realOut so
  // a mode/family/view/detail-toggle click (none of which change the
  // period) re-renders instantly without refetching. Date/preset changes
  // explicitly clear realOut (see wireEvents/applyPresetAndRender) to force
  // a fresh fetch. renderSeq guards a stale response from a superseded
  // fetch (same technique as gestao.js).
  function render() {
    if (!isRealTransport()) {
      var A = window.NX_DASHBI_ADAPTER;
      var input = buildFixtureInput(currentFixtureId);
      var out = A.compute(input);
      renderPanel(out, false);
      return;
    }
    if (realOut) { renderPanel(realOut, true); return; }
    loadReal();
  }

  function loadReal() {
    var mySeq = ++renderSeq;
    var panel = document.getElementById('dbPanel');
    if (panel) panel.innerHTML = loadingHtml();
    window.NX_DASHBI_REAL_PROVIDER.loadDashbiReal({ start: currentDateStart, end: currentDateEnd }).then(
      function (payload) {
        if (mySeq !== renderSeq) return;
        realOut = window.NX_DASHBI_REAL_VIEW_MODEL.buildRealOut(payload.metrics, payload.modelMetrics);
        renderPanel(realOut, true);
      },
      function (err) {
        if (mySeq !== renderSeq) return;
        var panel2 = document.getElementById('dbPanel');
        if (panel2) panel2.innerHTML = errorStateHtml(err && err.state, err && err.message);
      }
    );
  }

  function applyPresetAndRender(preset) {
    currentPreset = preset;
    var today = new Date(2026, 7, 30); // fixed reference date (NEXT_LOCAL fixture mode -- deterministic; real mode still uses it as "today" for preset math, matching V1's own real production behavior of computing presets off the actual current date -- see wireEvents note)
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
    realOut = null;
    render();
  }

  function wireEvents() {
    var fixtureSelect = document.getElementById('dbFixtureSelect');
    if (fixtureSelect) fixtureSelect.addEventListener('change', function (e) { currentFixtureId = e.target.value; render(); });
    document.getElementById('dbDateStart').addEventListener('change', function (e) { currentDateStart = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.dbPresetBtn').forEach(function (b) { b.classList.remove('dbBtnActive'); }); realOut = null; render(); });
    document.getElementById('dbDateEnd').addEventListener('change', function (e) { currentDateEnd = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.dbPresetBtn').forEach(function (b) { b.classList.remove('dbBtnActive'); }); realOut = null; render(); });
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

  // Dashbi Phase 2, Gate B4 -- pageShellHtml(isFixtureMode) keeps the
  // fixture banner/selector out of real mode's DOM entirely (no "DADOS DE
  // TESTE" label over real data), same principle as gestao.js's own
  // isRealTransport()-gated fixtureBanner.
  function pageShellHtml(isFixtureMode) {
    var fixtureBanner = '';
    if (isFixtureMode) {
      var fixtureOptions = fixturesData.map(function (c) { return '<option value="' + esc(c.id) + '"' + (c.id === currentFixtureId ? ' selected' : '') + '>' + esc(c.id) + '</option>'; }).join('');
      fixtureBanner = '<div class="modFixtureBanner"><span class="modFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
        '<label for="dbFixtureSelect">fixture:</label><select id="dbFixtureSelect">' + fixtureOptions + '</select></div>';
    }
    return '<div class="dbPage">' +
      '<div class="modPageHeader"><div class="modHeaderMain"><h1 class="modTitle">Análise Geral do Grupo</h1><p class="modSubtitle">Visão analítica geral do Grupo Brabus Mitsubishi.</p></div></div>' +
      fixtureBanner +
      '<div class="modFilters">' +
      '<div class="modField"><label>Visão</label><div class="dbViewGroup">' +
      '<button type="button" class="dbBtn dbViewBtn dbBtnActive" data-view="Grupo">Grupo</button>' +
      '<button type="button" class="dbBtn dbViewBtn" data-view="Novos">Novos</button>' +
      '<button type="button" class="dbBtn dbViewBtn" data-view="Seminovos">Seminovos</button>' +
      '</div></div>' +
      '<div class="modField"><label>Período rápido</label><div class="dbPresetGroup">' +
      '<button type="button" class="dbBtn dbPresetBtn" data-preset="currentMonth">Mês atual</button>' +
      '<button type="button" class="dbBtn dbPresetBtn" data-preset="lastMonth">Mês anterior</button>' +
      '<button type="button" class="dbBtn dbPresetBtn" data-preset="last6">Últimos 6 meses</button>' +
      '<button type="button" class="dbBtn dbPresetBtn" data-preset="lastYear">Último ano</button>' +
      '</div></div>' +
      '<div class="modField"><label for="dbDateStart">Data inicial</label><input id="dbDateStart" type="date" value="' + currentDateStart + '"></div>' +
      '<div class="modField"><label for="dbDateEnd">Data final</label><input id="dbDateEnd" type="date" value="' + currentDateEnd + '"></div>' +
      '</div>' +
      '<div id="dbPanel"></div>' +
      '</div>';
  }

  window.NX_DASHBI_PAGE = {
    render: function (outlet) {
      if (isRealTransport()) {
        outlet.innerHTML = pageShellHtml(false);
        wireEvents();
        render();
        return Promise.resolve();
      }
      return loadFixtures().then(function () {
        outlet.innerHTML = pageShellHtml(true);
        wireEvents();
        render();
      });
    }
  };
})();
