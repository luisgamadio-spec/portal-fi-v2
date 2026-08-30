/* PORTAL-NEXT V2 — Score module UI.
   Business logic: assets/js/adapters/score.adapter.js (byte-identical
   extraction — see docs/SCORE-ENGINE-AUDIT.md). This file only
   renders. Real labels from production (Gate 57) — no invented
   marketing names. Table order = calcScores()'s own sort (score desc,
   fin desc) — NOT interactively re-sortable this Wave (data-table.md's
   Sortable Column visual indicator is UNRESOLVED; not invented). */
(function () {
  'use strict';

  var FIXTURE_IDS = ['low','high','very_low','middle','very_high','confidence_boundary','zero_values','missing_optional_data','large_values','long_name','tie_case','sorting_case'];
  var fixturesData = null;
  var currentRows = [];
  var currentDetailKey = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }
  function loadFixtures() {
    if (fixturesData) return Promise.resolve(fixturesData);
    return fetch('tests/fixtures/score-fixtures.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { fixturesData = data.cases; return fixturesData; });
  }

  function rowKey(r) { return r.vendedor + '|' + r.loja + '|' + r.dept; }

  function renderTable(rows) {
    var body = rows.map(function (r, i) {
      return '<tr tabindex="0" role="button" data-key="' + esc(rowKey(r)) + '" aria-label="Ver detalhamento de ' + esc(r.vendedor) + '">' +
        '<td class="scRankCol">' + (i + 1) + '</td>' +
        '<td class="scNameCell"><span class="scNameText" title="' + esc(r.vendedor) + '">' + esc(r.vendedor) + '</span></td>' +
        '<td>' + esc(r.loja) + '</td>' +
        '<td>' + esc(r.dept) + '</td>' +
        '<td class="scNumCol">' + r.score + '</td>' +
        '<td class="scNumCol">' + (r.fin || 0) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="scTableWrap"><table class="scTable">' +
      '<thead><tr><th scope="col">#</th><th scope="col">Vendedor</th><th scope="col">Loja</th><th scope="col">Depto</th><th scope="col">Score</th><th scope="col">Financ.</th></tr></thead>' +
      '<tbody>' + body + '</tbody></table></div>';
  }

  function renderDetail(row) {
    if (!row) return '';
    var criteria = (row.scoreBreakdown || []).map(function (c) {
      var widthPct = Math.max(0, Math.min(100, (c.pct || 0) * 100));
      return '<div class="scCriterion">' +
        '<div class="scCriterionTop"><span class="scCriterionName">' + esc(c.label) + '</span><span class="scCriterionPoints">' + c.points + ' / ' + c.max + ' pts</span></div>' +
        '<div class="scCriterionMeta"><span>' + esc(c.detail || '') + '</span></div>' +
        '<div class="scMeter"><span style="width:' + widthPct.toFixed(1) + '%"></span></div>' +
        (c.amostra ? '<p class="scAmostraNote">Amostra: ' + esc(c.amostra) + ' — pontuação proporcional à amostra até atingir confiança plena.</p>' : '') +
        '</div>';
    }).join('');
    return '<div class="scDetail" id="scDetail">' +
      '<div class="scDetailHead"><h2>' + esc(row.vendedor) + '</h2><span class="scDetailTotal">Total: ' + row.score + ' / 1000</span>' +
      '<button type="button" class="scCloseDetail" id="scCloseDetail">Fechar detalhamento</button></div>' +
      criteria +
      '</div>';
  }

  function render() {
    var fixtureSelect = document.getElementById('scFixtureSelect');
    var currentId = fixtureSelect ? fixtureSelect.value : FIXTURE_IDS[0];
    var caseData = fixturesData.filter(function (c) { return c.id === currentId; })[0];
    currentRows = window.NX_SCORE_ADAPTER.compute(caseData.sales, caseData.fins);

    var tableHtml = renderTable(currentRows);
    var detailRow = currentDetailKey ? currentRows.filter(function (r) { return rowKey(r) === currentDetailKey; })[0] : null;

    document.getElementById('scTableRegion').innerHTML = tableHtml;
    document.getElementById('scDetailRegion').innerHTML = detailRow ? renderDetail(detailRow) : '';

    wireTableInteraction();
  }

  function openDetail(key) {
    currentDetailKey = key;
    render();
    var closeBtn = document.getElementById('scCloseDetail');
    if (closeBtn) closeBtn.focus();
  }
  function closeDetail(returnFocusKey) {
    currentDetailKey = null;
    render();
    if (returnFocusKey) {
      var row = document.querySelector('.scTable tbody tr[data-key="' + CSS.escape(returnFocusKey) + '"]');
      if (row) row.focus();
    }
  }

  function wireTableInteraction() {
    document.querySelectorAll('.scTable tbody tr').forEach(function (tr) {
      tr.addEventListener('click', function () { openDetail(tr.getAttribute('data-key')); });
      tr.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDetail(tr.getAttribute('data-key')); }
      });
    });
    var closeBtn = document.getElementById('scCloseDetail');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { closeDetail(currentDetailKey); });
      closeBtn.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeDetail(currentDetailKey);
      });
    }
  }

  window.NX_SCORE_PAGE = {
    render: function (outlet) {
      return loadFixtures().then(function () {
        currentDetailKey = null;
        var options = FIXTURE_IDS.map(function (id) { return '<option value="' + id + '">' + id + '</option>'; }).join('');
        outlet.innerHTML =
          '<div class="scPage">' +
          '<div class="scHeader"><div><h1>Análise de Score Vendedores</h1><p>Ranking de performance F&amp;I por vendedor.</p></div></div>' +
          '<div class="scFixtureBar"><span class="scFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
          '<label for="scFixtureSelect">fixture:</label>' +
          '<select id="scFixtureSelect">' + options + '</select></div>' +
          '<div id="scTableRegion"></div>' +
          '<div id="scDetailRegion"></div>' +
          '</div>';
        document.getElementById('scFixtureSelect').addEventListener('change', render);
        render();
      });
    }
  };
})();
