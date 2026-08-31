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
  function tableHtml(headers, bodyRows, numericFrom) {
    return '<div class="dbTableWrap"><table class="dbTable"><thead><tr>' + headerRow(headers, numericFrom) + '</tr></thead>' +
      '<tbody>' + (bodyRows.length ? bodyRows.join('') : '<tr><td colspan="' + headers.length + '" class="dbMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
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

  function storeTableHtml(A, results) {
    var A_ = results.aggs;
    var lojas = Object.keys(A_.vendasLoja);
    var finLojaMap = A_.finLoja;
    var body = lojas.sort(function (a, b) { return (A_.vendasLoja[b].qtd || 0) - (A_.vendasLoja[a].qtd || 0); }).map(function (loja) {
      var v = A_.vendasLoja[loja] || { qtd: 0 };
      var f = finLojaMap[loja] || { qtd: 0, producao: 0, receita: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      return row([loja, v.qtd, f.qtd, A.pct(share), A.money(f.producao || 0), A.money(f.receita || 0)]);
    });
    return tableHtml(['Loja', 'Vendas', 'Financiamentos', 'Share', 'Produção', 'Receita'], body);
  }

  function sellerTableHtml(A, results) {
    var A_ = results.aggs;
    var keys = Object.keys(A_.vendasVendDept);
    var body = keys.sort(function (a, b) { return (A_.vendasVendDept[b].qtd || 0) - (A_.vendasVendDept[a].qtd || 0); }).map(function (key) {
      var parts = key.split(' | ');
      var v = A_.vendasVendDept[key] || { qtd: 0 };
      var f = A_.finVendDept[key] || { qtd: 0, producao: 0 };
      var share = v.qtd ? f.qtd / v.qtd : 0;
      return row([parts[0], parts[1] || '', v.qtd, f.qtd, A.pct(share), A.money(f.producao || 0)]);
    });
    return tableHtml(['Vendedor', 'Depto', 'Vendas', 'Financiamentos', 'Share', 'Produção'], body, 2);
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

  function modelAnalysisHtml(A, results) {
    var modelRows = A.modelRowsUnified(results, currentFamily);
    var planRows = A.planRowsByModel(results, currentFamily);
    var modelBody = modelRows.map(function (r) {
      return row([r.Modelo, r.volume, r.financiada, A.pct(r.penetracao), A.money(r.producao), A.money(r.receitaTotal),
        A.money(r.ticket), A.pct(r.retornoMedio), r.entradaQtd, A.money(r.entradaMed), A.pct(r.entradaPct)]);
    });
    var planBody = planRows.map(function (r) {
      return row([r.Modelo, r.Financiamentos, r.Linear, r.Balao, r.Coparticipado, r.Subsidiado, r.Reversao]);
    });
    return '<div class="dbModelSection">' +
      '<h2 style="margin-top:0">Análise por Modelos (Novos)</h2>' +
      '<p class="dbMuted">Selecione uma família para abrir os indicadores específicos dos modelos Novos.</p>' +
      vehicleSelectorHtml() +
      '<p class="dbMuted">Vendas/Financiamentos/Produção/Receita/Ticket/Retorno por modelo, mais os indicadores de Entrada (Entrada, Entrada Média, Entrada %) — nunca ocultos.</p>' +
      tableHtml(['Modelo', 'Vendas', 'Financiamentos', 'Penetração', 'Produção', 'Receita Total', 'Ticket', 'Retorno Médio', 'Entrada Qtd', 'Entrada Média', 'Entrada %'], modelBody) +
      '<h2>Mix de Planos por Modelo</h2>' +
      tableHtml(['Modelo', 'Financiamentos', 'Linear', 'Balão', 'Coparticipado', 'Subsidiado', 'Reversão'], planBody) +
      '</div>';
  }

  function rankingRowHtml(A, list, kind) {
    return list.map(function (r, i) {
      var nome = r.Nome, sub = '';
      if (kind === 'vendedor') {
        var parts = String(r.Nome || '').split(' | ');
        nome = parts[0] || r.Nome;
        sub = parts.length > 1 ? parts.slice(1).join(' · ') : '';
      }
      return '<tr><td>' + (i + 1) + 'º</td><td>' + esc(nome) + (sub ? '<div class="dbTableSub">' + esc(sub) + '</div>' : '') + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.vendas)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.fin)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.pct(r.penetracao)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.money(r.receitaTotal)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.money(r.producao)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.pct(r.retorno)) + '</td></tr>';
    }).join('');
  }

  function rankingTableHtml(A, title, list, kind) {
    if (!list.length) return '<h3 class="dbSubHeading">' + esc(title) + '</h3><p class="dbMuted">Sem dados.</p>';
    return '<h3 class="dbSubHeading">' + esc(title) + '</h3>' +
      '<div class="dbTableWrap"><table class="dbTable"><thead><tr>' +
      headerRow(['#', 'Nome', 'Vendas', 'Financiamentos', 'Penetração', 'Receita Total', 'Produção', 'Retorno'], 2) +
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
    var body = rows.map(function (r) {
      var cls = r._total ? ' class="dbTotalRow"' : '';
      return '<tr' + cls + '><td>' + esc(r.Loja) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Vendidos)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Financiados)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Balao)) + '</td>' +
        '<td class="dbNumCol">' + esc(A.pct(r.BalaoPct)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Subsidiada)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Coparticipada)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Reversao)) + '</td>' +
        '<td class="dbNumCol">' + esc(String(r.Linear)) + '</td>' +
        '<td>' + esc(r.PlanoDestaque || '-') + '</td></tr>';
    }).join('');
    return '<div class="dbNovosLojaSection">' +
      '<h2 style="margin-top:0">Novos por Loja</h2>' +
      '<p class="dbMuted">Leitura por loja/unidade considerando apenas veículos Novos, respeitando o período selecionado.</p>' +
      '<div class="dbTableWrap"><table class="dbTable"><thead><tr>' +
      headerRow(['Loja', 'Vendidos', 'Financiados', 'Balão', '% Balão', 'Subsidiada', 'Coparticipada', 'Reversão', 'Linear', 'Plano Destaque'], 1) +
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

    var isNovos = currentDeptView === 'Novos';

    var html =
      '<div class="dbKpiGridPrimary">' +
      kpiPrimary('Vendas', kpi.vendas, currentDeptView) +
      kpiPrimary('Financiamentos', kpi.fins, 'Share ' + A.pct(kpi.share)) +
      kpiPrimary('Produção', A.money(kpi.producao)) +
      kpiPrimary('Receita', A.money(kpi.receita), 'SPF ' + A.money(kpi.receitaSPF) + ' · Total ' + A.money(kpi.receitaTotal)) +
      kpiPrimary('Retorno', A.pct(kpi.retorno)) +
      '</div>' +
      (closed ? '<div class="dbFechamentoBar"><span class="dbFechamento">FECHAMENTO</span><span class="dbMuted">Período filtrado corresponde a um mês fechado.</span></div>' : '') +

      (isNovos ?
        '<h2>Classificação dos Planos</h2>' +
        '<div class="dbPlanGrid">' + ['SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO', 'BALÃO', 'LINEAR'].map(function (t) { return planCardHtml(A, t, counts[t]); }).join('') + '</div>' +
        '<p class="dbMuted">Classificação oficial por operação, mesma prioridade de Análise F&I do Grupo e Coparticipado: Código IF 999 ou SUBSIDIADO; Código IF 777 ou REVERSÃO; TC Devolvida 1 ou COPARTICIPADO; Balão PMT maior que zero; demais = LINEAR. Exibida somente em Novos (mesma visibilidade da Análise por Modelos em produção — ambas vivem dentro da mesma seção/aba real).</p>'
        : '') +

      '<h2>Vendas e Financiamentos por Loja</h2>' + storeTableHtml(A, out) +

      '<h2>Vendas e Financiamentos por Vendedor</h2>' + sellerTableHtml(A, out) +

      (isNovos ? modelAnalysisHtml(A, out) : '') +

      rankingHtml(A, out, salesView, finsView) +

      (isNovos ? novosLojaHtml(A, out) : '') +

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
