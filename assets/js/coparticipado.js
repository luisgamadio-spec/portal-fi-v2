/* PORTAL-NEXT V2 -- Coparticipado module UI.
   Business logic: assets/js/adapters/coparticipado.adapter.js (byte-
   identical extraction -- see docs/COPARTICIPADO-ENGINE-AUDIT.md and
   docs/COPARTICIPADO-EXTRACTION-TRACE.md). This file only renders.

   Real production surface migrated (verified by direct source read of
   origin/main:modules/coparticipado.html, function renderCopa/
   renderSubsidiados/coparViewSwitcherHtml, lines ~548-566):
     - the "Visão Coparticipados" / "Visão Subsidiados" view switcher
       (Fase UX-Grupo-3.0, Item 3 -- both views share DATA.fins and the
       same r.plano field, no new classification)
     - Coparticipados table: Cliente/Vendedor/Loja/Modelo Base/Modelo
       Taxa/Valor Financiado/Rebate Total/Parte Brabus/Valor Rebate
       Total/Coparticipação/Situação/Data/Chassi (exact column order)
     - Subsidiados table + its 3-stat summary (Operações/Lojas/
       Vendedores) -- exact production text
     - Loja / Departamento (Grupo, Novos, Seminovos) + date-range
       filters, same predicate as currentFiltered()

   NOT migrated (Gate 57 deferred, real reasons -- see
   docs/COPARTICIPADO-EXTRACTION-TRACE.md):
     - "Diagnóstico" tab (renderVendorAlerts/collectUnknownVendors) --
       a vendor-registry data-quality feature orthogonal to the
       classification/crossing/exclusion/priority/filter/sort surface
       this Wave scopes; needs the real vendor registry backend.
     - openSellerDetails/openScoreDetails/the embedded stale calcScores
       -- confirmed DEAD CODE in production (no tab/section wires them
       into the real UI; #novos/#score are never shown, renderNovos()
       is a no-op). Not migrated, same as Score's own stale-code
       finding.
     - Row-level drill-down modal -- NOT APPLICABLE. Production's own
       Coparticipados/Subsidiados tables have no per-row detail modal;
       the row already IS the finest real granularity (one financing
       operation). No drill-down was invented here.
     - Export to Excel (exportarCoparticipados/exportarSubsidiados) --
       DEFERRED DEPENDENCY (needs xlsx-js-style, a real file-download
       flow; 0 backend/0 file I/O this Wave, same boundary as the
       Base01/02/03 Excel parsing already deferred in the audit doc). */
(function () {
  'use strict';

  var fixturesData = null;
  var currentFixtureId = 'ALL';
  var currentView = 'COPARTICIPADO'; // matches production's currentCoparView default
  var currentStore = '';
  var currentDept = 'Grupo';
  var currentDateStart = '';
  var currentDateEnd = '2026-12-31';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  function loadFixtures() {
    if (fixturesData) return Promise.resolve(fixturesData);
    return fetch('tests/fixtures/coparticipado-fixtures.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { fixturesData = data.cases; return fixturesData; });
  }

  // "ALL" combines every fixture case's raw rows into one input, so the
  // Loja/Departamento/date filters and multi-scenario sort/total
  // behavior have real, varied data to operate over (any single case
  // is deliberately narrow -- one classification scenario each).
  // Individual cases remain selectable for isolated stress inspection
  // (Gate 43's Fixture Studio requirement).
  function buildFixtureInput(id) {
    if (id !== 'ALL') {
      var c = fixturesData.filter(function (x) { return x.id === id; })[0];
      return { vendorRows: c.vendorRows, taxasCopart: c.taxasCopart, b1Rows: c.b1Rows, b2Rows: c.b2Rows, b3Rows: c.b3Rows };
    }
    var vendorRows = [], taxasCopart = {}, b1Rows = [], b2Rows = [], b3Rows = [];
    var seenVendor = {};
    fixturesData.forEach(function (c) {
      (c.vendorRows || []).forEach(function (v) {
        var k = v.NBS || v.Nome;
        if (seenVendor[k]) return;
        seenVendor[k] = true;
        vendorRows.push(v);
      });
      Object.assign(taxasCopart, c.taxasCopart || {});
      b1Rows = b1Rows.concat(c.b1Rows || []);
      b2Rows = b2Rows.concat(c.b2Rows || []);
      b3Rows = b3Rows.concat(c.b3Rows || []);
    });
    return { vendorRows: vendorRows, taxasCopart: taxasCopart, b1Rows: b1Rows, b2Rows: b2Rows, b3Rows: b3Rows };
  }

  // Same predicate as production's currentFiltered() (origin/main,
  // line ~491): dateIn() is the byte-identical extracted function;
  // store/dept equality is copied verbatim from that same function's
  // own filter logic (no new rule invented).
  function applyFilters(fins) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    var start = currentDateStart ? A.parseDate(currentDateStart) : null;
    var end = currentDateEnd ? A.parseDate(currentDateEnd) : null;
    return fins.filter(function (r) {
      if (!A.dateIn(r, start, end)) return false;
      if (currentStore && r.loja !== currentStore) return false;
      if (currentDept !== 'Grupo' && r.dept !== currentDept) return false;
      return true;
    });
  }

  function renderCoparticipadosTable(fins) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    var rows = fins.filter(function (r) { return r.plano === 'COPARTICIPADO'; });
    var body = rows.map(function (r) {
      var c = r.coparticipacaoDetalhe || A.calcCoparticipacaoDetalhe(r);
      return '<tr>' +
        '<td>' + esc(r.cliente) + '</td>' +
        '<td>' + esc(r.vendedor) + '</td>' +
        '<td>' + esc(r.loja) + '</td>' +
        '<td>' + esc(r.modelo) + '</td>' +
        '<td>' + (c.modeloTabela ? esc(c.modeloTabela) : '<span class="cpWarn">Não encontrado</span>') + '</td>' +
        '<td class="cpNumCol">' + A.money(r.valorFinanciado) + '</td>' +
        '<td class="cpNumCol">' + (c.ok ? A.pct(c.rebateTotal) : '<span class="cpWarn">—</span>') + '</td>' +
        '<td class="cpNumCol">' + (c.ok ? A.pct(c.parteBrabus) : '<span class="cpWarn">—</span>') + '</td>' +
        '<td class="cpNumCol">' + (c.ok ? A.money(c.valorRebateTotal) : '<span class="cpWarn">—</span>') + '</td>' +
        '<td class="cpNumCol">' + (c.ok ? A.money(c.coparticipacao) : '<span class="cpWarn">Modelo não encontrado</span>') + '</td>' +
        '<td>' + esc(r.situacaoB3 || '') + '</td>' +
        '<td class="cpNumCol">' + esc(A.iso(r.data)) + '</td>' +
        '<td>' + esc(r.chassi) + '</td>' +
        '</tr>';
    }).join('');
    return '<h2>Planos Coparticipados</h2>' +
      '<p class="cpMuted">Coparticipação calculada pela tabela <b>taxa coparticipado.xlsx</b>: Modelo × Rebate Total × Rebate Parte Brabus.</p>' +
      '<div class="cpTableWrap"><table class="cpTable">' +
      '<thead><tr><th>Cliente</th><th>Vendedor</th><th>Loja</th><th>Modelo Base</th><th>Modelo Taxa</th><th>Valor Financiado</th><th>Rebate Total</th><th>Parte Brabus</th><th>Valor Rebate Total</th><th>Coparticipação</th><th>Situação</th><th>Data</th><th>Chassi</th></tr></thead>' +
      '<tbody>' + (body || '<tr><td colspan="13" class="cpMuted">Nenhum coparticipado encontrado no filtro atual.</td></tr>') + '</tbody></table></div>';
  }

  function renderSubsidiadosTable(fins) {
    var A = window.NX_COPARTICIPADO_ADAPTER;
    var rows = fins.filter(function (r) { return r.plano === 'SUBSIDIADO'; });
    var lojas = {}, vendedores = {};
    rows.forEach(function (r) { lojas[r.loja] = 1; vendedores[r.vendedor] = 1; });
    var body = rows.map(function (r) {
      return '<tr>' +
        '<td>' + esc(r.cliente) + '</td>' +
        '<td>' + esc(r.vendedor) + '</td>' +
        '<td>' + esc(r.loja) + '</td>' +
        '<td>' + esc(r.dept) + '</td>' +
        '<td>' + esc(r.modelo) + '</td>' +
        '<td class="cpNumCol">' + A.money(r.valorFinanciado) + '</td>' +
        '<td class="cpNumCol">' + A.money(r.retorno) + '</td>' +
        '<td class="cpNumCol">' + A.money(r.receitaSPF) + '</td>' +
        '<td>' + esc(r.situacaoB3 || '') + '</td>' +
        '<td class="cpNumCol">' + esc(A.iso(r.data)) + '</td>' +
        '<td>' + esc(r.chassi) + '</td>' +
        '</tr>';
    }).join('');
    return '<h2>Planos Subsidiados</h2>' +
      '<p class="cpMuted">Todas as operações classificadas como <b>SUBSIDIADO</b> no período (mesma regra oficial já usada nos indicadores do Portal: código IF = 999 ou "SUBSIDIADO" na Base 03).</p>' +
      '<div class="cpSummary">' +
      '<div class="cpSummaryItem"><div class="cpK">Operações</div><div class="cpV">' + A.num(rows.length) + '</div></div>' +
      '<div class="cpSummaryItem"><div class="cpK">Lojas</div><div class="cpV">' + A.num(Object.keys(lojas).length) + '</div></div>' +
      '<div class="cpSummaryItem"><div class="cpK">Vendedores</div><div class="cpV">' + A.num(Object.keys(vendedores).length) + '</div></div>' +
      '</div>' +
      '<div class="cpTableWrap"><table class="cpTable">' +
      '<thead><tr><th>Cliente</th><th>Vendedor</th><th>Loja</th><th>Departamento</th><th>Modelo</th><th>Valor Financiado</th><th>Retorno</th><th>SPF Extra</th><th>Situação</th><th>Data</th><th>Chassi</th></tr></thead>' +
      '<tbody>' + (body || '<tr><td colspan="11" class="cpMuted">Nenhum subsidiado encontrado no filtro atual.</td></tr>') + '</tbody></table></div>';
  }

  function populateStoreOptions(fins, sales) {
    var sel = document.getElementById('cpStoreFilter');
    if (!sel) return;
    var stores = {};
    sales.concat(fins).forEach(function (r) { if (r.loja) stores[r.loja] = 1; });
    var list = Object.keys(stores).sort(function (a, b) { return a.localeCompare(b); });
    var prev = currentStore;
    sel.innerHTML = '<option value="">Todas as lojas</option>' + list.map(function (s) {
      return '<option' + (s === prev ? ' selected' : '') + '>' + esc(s) + '</option>';
    }).join('');
  }

  function render() {
    var input = buildFixtureInput(currentFixtureId);
    var result = window.NX_COPARTICIPADO_ADAPTER.compute(input);
    var filteredFins = applyFilters(result.fins);

    populateStoreOptions(result.fins, result.sales);

    var switcherHtml =
      '<div class="cpViewSwitcher" role="tablist" aria-label="Visão">' +
      '<button type="button" class="cpTab' + (currentView === 'COPARTICIPADO' ? ' cpTabActive' : '') + '" role="tab" aria-selected="' + (currentView === 'COPARTICIPADO') + '" id="cpTabCopart">Visão Coparticipados</button>' +
      '<button type="button" class="cpTab' + (currentView === 'SUBSIDIADO' ? ' cpTabActive' : '') + '" role="tab" aria-selected="' + (currentView === 'SUBSIDIADO') + '" id="cpTabSubs">Visão Subsidiados</button>' +
      '</div>';

    var bodyHtml = currentView === 'SUBSIDIADO' ? renderSubsidiadosTable(filteredFins) : renderCoparticipadosTable(filteredFins);

    document.getElementById('cpPanel').innerHTML = switcherHtml + bodyHtml;

    document.getElementById('cpTabCopart').addEventListener('click', function () { currentView = 'COPARTICIPADO'; render(); });
    document.getElementById('cpTabSubs').addEventListener('click', function () { currentView = 'SUBSIDIADO'; render(); });
  }

  function wireFilterEvents() {
    document.getElementById('cpFixtureSelect').addEventListener('change', function (e) {
      currentFixtureId = e.target.value;
      render();
    });
    document.getElementById('cpStoreFilter').addEventListener('change', function (e) {
      currentStore = e.target.value;
      render();
    });
    document.getElementById('cpDeptFilter').addEventListener('change', function (e) {
      currentDept = e.target.value;
      render();
    });
    document.getElementById('cpDateStart').addEventListener('change', function (e) {
      currentDateStart = e.target.value;
      render();
    });
    document.getElementById('cpDateEnd').addEventListener('change', function (e) {
      currentDateEnd = e.target.value;
      render();
    });
  }

  window.NX_COPARTICIPADO_PAGE = {
    render: function (outlet) {
      return loadFixtures().then(function () {
        var options = ['<option value="ALL">combinado (todos os cenários)</option>'].concat(
          fixturesData.map(function (c) { return '<option value="' + esc(c.id) + '">' + esc(c.id) + '</option>'; })
        ).join('');
        outlet.innerHTML =
          '<div class="cpPage">' +
          '<div class="cpHeader"><div><h1>Gestão de Coparticipados &amp; Subsidiados</h1><p>Módulo financeiro · Portal F&amp;I Grupo Brabus Mitsubishi</p></div></div>' +
          '<div class="cpFixtureBar"><span class="cpFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
          '<label for="cpFixtureSelect">fixture:</label>' +
          '<select id="cpFixtureSelect">' + options + '</select></div>' +
          '<div class="cpFilters">' +
          '<div class="cpField"><label for="cpStoreFilter">Loja</label><select id="cpStoreFilter"><option value="">Todas as lojas</option></select></div>' +
          '<div class="cpField"><label for="cpDeptFilter">Departamento</label><select id="cpDeptFilter">' +
          '<option value="Grupo" selected>Grupo</option><option value="Novos">Novos</option><option value="Seminovos">Seminovos</option></select></div>' +
          '<div class="cpField"><label for="cpDateStart">Data inicial</label><input id="cpDateStart" type="date"></div>' +
          '<div class="cpField"><label for="cpDateEnd">Data final</label><input id="cpDateEnd" type="date" value="2026-12-31"></div>' +
          '</div>' +
          '<div class="cpPanel" id="cpPanel"></div>' +
          '</div>';
        wireFilterEvents();
        render();
      });
    }
  };
})();
