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

  // Score Phase 2A (Real Data Integration Foundation) -- the ONE place
  // transport is decided, same rule as gestao.js/dashbi.js/
  // coparticipado.js's own isRealTransport(). renderSeq/realResult/
  // currentAbortController guard against a stale/superseded async
  // response overwriting a newer one. Score has no product filter UI
  // (Phase 1, confirmed) and Gate 6 (Phase 2A) proved a direct, real,
  // evidence-based default period (SCORE_DATE_CONTRACT_DIRECT) -- so,
  // unlike Coparticipado, there is no date/store/dept state to track
  // here; the real provider applies its own proven default internally.
  function isRealTransport() {
    return !!(window.NX_AUTH && window.NX_AUTH.isAuthConfigured);
  }
  var renderSeq = 0;
  var realResult = null;
  var currentAbortController = null;

  // Gate 8 runtime-state vocabulary (LOADING/SUCCESS/EMPTY/AUTH_DENIED/
  // SESSION_EXPIRED/RPC_ERROR/TIMEOUT/MALFORMED_RESPONSE). EMPTY is not
  // a distinct error state here -- a SUCCESS with zero rows already
  // renders the existing "Nenhum vendedor encontrado" empty state via
  // renderTable() below, same as fixture mode's own empty-fixture case.
  var STATE_COPY = {
    AUTH_DENIED: { title: 'Sem permissão', body: 'Sua conta não tem acesso a esta análise.' },
    SESSION_EXPIRED: { title: 'Sessão expirada', body: 'Entre novamente para continuar.' },
    RPC_ERROR: { title: 'Não foi possível carregar', body: 'Não foi possível carregar o ranking agora. Tente novamente.' },
    TIMEOUT: { title: 'Tempo excedido', body: 'A resposta demorou demais. Tente novamente.' },
    MALFORMED_RESPONSE: { title: 'Não foi possível carregar', body: 'Resposta inesperada do servidor.' }
  };
  function loadingHtml() {
    return '<div class="modLoadingState"><span class="modLoadingDot"></span>Carregando ranking...</div>';
  }
  function errorStateHtml(state, message) {
    var copy = STATE_COPY[state] || STATE_COPY.RPC_ERROR;
    return '<div class="modErrorState"><div class="modStateTitle">' + esc(copy.title) + '</div>' + esc(copy.body) + '</div>';
  }

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

  // PORTAL-NEXT-07.7B — the ONE authoritative Score Band classifier
  // (Gate 2), consumed identically by the desktop and mobile renderers
  // below (Gate 9 — no duplicated threshold logic). HUMAN-APPROVED
  // absolute boundaries (PORTAL-NEXT-07.7A Option 1, selected by human
  // decision — see docs/SCORE-BAND-DISCOVERY-07-7A.md and
  // docs/SCORE-BAND-NORMATIVE-07-7B.md): fixed on the FINAL 0-1000
  // score, never relative to the current seller population/period.
  // Descending-order checks make the ranges mutually exclusive without
  // needing upper-bound comparisons; the final `null` covers anything
  // that isn't a finite score in [0,1000] (negative, which the engine's
  // own clamp already prevents, but guarded here defensively too).
  //
  // Invalid/non-finite Score contract (Gate 5): a NaN/Infinity/-Infinity/
  // null/undefined Score returns `null` — it is NEVER classified into a
  // real band. This is a presentation-layer safety net; it stays in
  // place even though the specific receitaSPF-driven NaN defect
  // documented in PORTAL-NEXT-07.7A's Gate 19 was subsequently fixed at
  // the adapter boundary (PORTAL-NEXT-07.7C, see
  // docs/SCORE-RECEITA-SPF-NONFINITE-07-7C.md) — any other genuinely
  // invalid/non-finite Score must still resolve to no band, not a
  // fabricated one.
  var SCORE_BANDS = [
    { min: 900, max: 1000, label: 'ELITE', cls: 'scBandElite' },
    { min: 750, max: 899, label: 'ALTA PERFORMANCE', cls: 'scBandAlta' },
    { min: 550, max: 749, label: 'PERFORMANCE', cls: 'scBandPerformance' },
    { min: 300, max: 549, label: 'DESENVOLVIMENTO', cls: 'scBandDesenvolvimento' },
    { min: 0, max: 299, label: 'CRÍTICO', cls: 'scBandCritico' }
  ];
  function classifyScoreBand(score) {
    if (typeof score !== 'number' || !isFinite(score)) return null;
    for (var i = 0; i < SCORE_BANDS.length; i++) {
      if (score >= SCORE_BANDS[i].min) return SCORE_BANDS[i];
    }
    return null; // score < 0 -- outside every defined band
  }
  function scoreBandHtml(score, extraClass) {
    var band = classifyScoreBand(score);
    if (!band) return '';
    return '<span class="scBand ' + band.cls + (extraClass ? ' ' + extraClass : '') + '">' + esc(band.label) + '</span>';
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
        '<td class="modNumCol"><span class="scScoreCell">' +
          '<span class="scScoreValueRow">' + scoreMeterHtml(r) + '<span>' + r.score + '</span></span>' +
          scoreBandHtml(r.score) +
          '</span></td>' +
        '<td class="modNumCol">' + (r.fin || 0) + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="scDesktopOnly"><div class="modTableWrap"><table class="modTable scTable">' +
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
          '<div class="scMobileScoreValue">' + r.score + '</div>' +
          scoreBandHtml(r.score, 'scMobileBand') +
          '<div class="scMobileScoreRow">' + scoreMeterHtml(r) + '</div>' +
        '</div>' +
        '<div class="scMobileField"><div class="scMobileLabel">Financ.</div><div class="scMobileValue">' + (r.fin || 0) + '</div></div>' +
        '</div>';
    }).join('');
    return '<div class="scMobileOnly">' + cards + '</div>';
  }

  function renderTable(rows) {
    if (!rows.length) {
      return '<div class="modEmptyState"><div class="modStateTitle">Nenhum vendedor encontrado</div>Nenhum registro disponível para o cenário atual.</div>';
    }
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

  function renderPanel(rows) {
    currentRows = rows;
    var tableHtml = renderTable(currentRows);
    var detailRow = currentDetailKey ? currentRows.filter(function (r) { return rowKey(r) === currentDetailKey; })[0] : null;

    document.getElementById('scTableRegion').innerHTML = tableHtml;
    document.getElementById('scDetailRegion').innerHTML = detailRow ? renderDetail(detailRow) : '';

    wireTableInteraction();
  }

  function render() {
    if (!isRealTransport()) {
      var fixtureSelect = document.getElementById('scFixtureSelect');
      var currentId = fixtureSelect ? fixtureSelect.value : FIXTURE_IDS[0];
      var caseData = fixturesData.filter(function (c) { return c.id === currentId; })[0];
      renderPanel(window.NX_SCORE_ADAPTER.compute(caseData.sales, caseData.fins));
      return;
    }
    if (realResult) { renderPanel(realResult); return; }
    loadReal();
  }

  // Fetch -> validated raw payload -> minimal field mapping + canonical
  // familiaModelo() (score-real-view-model.js) -> existing
  // normalizeFinInput() + FROZEN calcScores() (NX_SCORE_ADAPTER.compute,
  // untouched) -> existing presentation. No calculation happens in this
  // file or in the view-model (Gate: PROIBIDO duplicar calcScores()).
  function loadReal() {
    if (currentAbortController) currentAbortController.abort();
    var controller = new AbortController();
    currentAbortController = controller;
    var mySeq = ++renderSeq;
    var region = document.getElementById('scTableRegion');
    if (region) region.innerHTML = loadingHtml();
    var detailRegion = document.getElementById('scDetailRegion');
    if (detailRegion) detailRegion.innerHTML = '';

    window.NX_SCORE_REAL_PROVIDER.loadScoreReal({ signal: controller.signal }).then(
      function (payload) {
        if (mySeq !== renderSeq) return;
        var mapped;
        try {
          mapped = window.NX_SCORE_REAL_VIEW_MODEL.buildRealResult(payload);
        } catch (e) {
          var r2 = document.getElementById('scTableRegion');
          if (r2) r2.innerHTML = errorStateHtml(e && e.state, e && e.message);
          return;
        }
        realResult = window.NX_SCORE_ADAPTER.compute(mapped.sales, mapped.fins);
        renderPanel(realResult);
      },
      function (err) {
        if (mySeq !== renderSeq) return;
        if (err && err.state === 'ABORTED') return; // not a user-facing error -- superseded request
        var region2 = document.getElementById('scTableRegion');
        if (region2) region2.innerHTML = errorStateHtml(err && err.state, err && err.message);
      }
    );
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
    // PORTAL-NEXT-07.7B — exposed read-only for deterministic band
    // boundary/invalid-input testing (tests/score-band-test.py), same
    // pattern already used for window.NX_SCORE_ADAPTER's business
    // functions. Returns {min,max,label,cls} or null -- never a bare
    // string -- so a test can assert on `.label` explicitly rather
    // than guessing a return shape.
    classifyScoreBand: classifyScoreBand,
    // Gate 20/21 (Phase 2A): the dev-only fixture selector must never
    // appear in real mode, same isRealTransport()-gated shell principle
    // already used by gestao.js/dashbi.js/coparticipado.js.
    render: function (outlet) {
      function paintShell(isFixtureMode) {
        currentDetailKey = null;
        var fixtureBanner = '';
        if (isFixtureMode) {
          var options = FIXTURE_IDS.map(function (id) { return '<option value="' + id + '">' + id + '</option>'; }).join('');
          fixtureBanner = '<div class="modFixtureBanner"><span class="modFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
            '<label for="scFixtureSelect">fixture:</label>' +
            '<select id="scFixtureSelect">' + options + '</select></div>';
        }
        outlet.innerHTML =
          '<div class="scPage">' +
          '<div class="modPageHeader"><div class="modHeaderMain"><h1 class="modTitle">Análise de Score Vendedores</h1><p class="modSubtitle">Ranking de performance F&amp;I por vendedor.</p></div></div>' +
          fixtureBanner +
          '<div id="scTableRegion"></div>' +
          '<div id="scDetailRegion"></div>' +
          '</div>';
        if (isFixtureMode) {
          document.getElementById('scFixtureSelect').addEventListener('change', render);
        }
        render();
      }

      if (isRealTransport()) {
        paintShell(false);
        return Promise.resolve();
      }
      return loadFixtures().then(function () { paintShell(true); });
    }
  };
})();
