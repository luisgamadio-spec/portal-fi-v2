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

  // Gate 4-5: real production scale is 0-1000 (calcScores' own
  // Math.round(Math.max(0,Math.min(1000,score))) clamp — not
  // presumed, read directly from the extracted source). Meter
  // proportion is a DETERMINISTIC, display-only derivation from the
  // already-final (post-confidence-dampening) score — it never
  // touches the raw score, ranking, or sort order (Gate 18-19).
  var SCORE_SCALE_MAX = 1000;
  function meterPct(score) {
    return Math.max(0, Math.min(100, (score / SCORE_SCALE_MAX) * 100));
  }

  // PORTAL-NEXT-07.6.4 — human UAT rejected the 07.6/07.6.2 approach of
  // transforming the desktop <table> itself into a mobile layout (via
  // CSS, however deterministic) three times in a row. Replaced with two
  // independent renderers fed by the SAME `rows` array — no
  // recomputation, no duplicated business logic. Only one is visible at
  // a time (CSS display:none on the inactive one, score.css); the
  // mobile renderer uses plain div markup, not table/tr/td, so no
  // legacy column geometry can ever reach it again.
  function scoreMeterHtml(r) {
    var pct = meterPct(r.score);
    return '<span class="scMeterTrack" role="img" aria-label="Score ' + r.score + ' de ' + SCORE_SCALE_MAX + '"><span class="scMeterFill" style="width:' + pct.toFixed(1) + '%"></span></span>';
  }

  function renderDesktopTable(rows) {
    var body = rows.map(function (r, i) {
      return '<tr tabindex="0" role="button" data-key="' + esc(rowKey(r)) + '" aria-label="Ver detalhamento de ' + esc(r.vendedor) + '">' +
        '<td class="scRankCol">' + (i + 1) + '</td>' +
        '<td class="scNameCell"><span class="scNameText" title="' + esc(r.vendedor) + '">' + esc(r.vendedor) + '</span></td>' +
        '<td>' + esc(r.loja) + '</td>' +
        '<td>' + esc(r.dept) + '</td>' +
        '<td class="scNumCol"><span class="scScoreCell">' + scoreMeterHtml(r) +
          '<span>' + r.score + '</span>' +
          '</span></td>' +
        '<td class="scNumCol">' + (r.fin || 0) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="scDesktopOnly"><div class="scTableWrap"><table class="scTable">' +
      '<thead><tr><th scope="col">#</th><th scope="col">Vendedor</th><th scope="col">Loja</th><th scope="col">Depto</th><th scope="col">Score</th><th scope="col">Financ.</th></tr></thead>' +
      '<tbody>' + body + '</tbody></table></div></div>';
  }

  function renderMobileCards(rows) {
    var cards = rows.map(function (r, i) {
      return '<div class="scMobileCard" tabindex="0" role="button" data-key="' + esc(rowKey(r)) + '" aria-label="Ver detalhamento de ' + esc(r.vendedor) + '">' +
        '<div class="scMobileRank">#' + (i + 1) + '</div>' +
        '<div class="scMobileName">' + esc(r.vendedor) + '</div>' +
        '<div class="scMobileSub">' + esc(r.loja) + ' · ' + esc(r.dept) + '</div>' +
        '<div class="scMobileScoreBlock">' +
          '<div class="scMobileLabel">Score</div>' +
          '<div class="scMobileScoreRow"><span class="scMobileScoreValue">' + r.score + '</span>' + scoreMeterHtml(r) + '</div>' +
        '</div>' +
        '<div class="scMobileField"><div class="scMobileLabel">Financ.</div><div class="scMobileValue">' + (r.fin || 0) + '</div></div>' +
        '</div>';
    }).join('');
    return '<div class="scMobileOnly">' + cards + '</div>';
  }

  function renderTable(rows) {
    return renderDesktopTable(rows) + renderMobileCards(rows);
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
      // whichever renderer is currently visible (desktop table row or
      // mobile card) carries the same data-key -- query both, focus
      // whichever exists (display:none elements are simply skipped).
      var row = document.querySelector('.scTable tbody tr[data-key="' + CSS.escape(returnFocusKey) + '"], .scMobileCard[data-key="' + CSS.escape(returnFocusKey) + '"]');
      if (row) row.focus();
    }
  }

  function wireTableInteraction() {
    document.querySelectorAll('.scTable tbody tr, .scMobileCard').forEach(function (tr) {
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
