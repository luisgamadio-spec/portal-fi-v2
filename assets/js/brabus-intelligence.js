/* PORTAL-NEXT V2 — Brabus Intelligence page (IA-V2-1, real transport
   added IA-V2-2).

   Two transport modes, selected by window.NX_INTELLIGENCE_CONFIG.mode
   (default 'fixture', safe everywhere -- Gate 8 containment):
   'fixture' behaves exactly as IA-V2-1 shipped it (0 network calls,
   synthetic contract data, fixture banner visible). 'real_text' calls
   the real, unmodified portal-ai-homolog contract via
   NX_AUTH.getAccessToken() + A.sendRealText() -- this file still never
   calls fetch/XHR itself, that lives entirely in the adapter, and both
   modes converge on the exact same applyResult()/renderConversation()
   path below, so nothing about rendering forks between them. ZERO
   business logic either way: this file only builds/reads DOM and
   calls the adapter's pure formatting functions — every number/date/
   percent shown comes verbatim from a response object neither mode
   computes.

   Conversation state lives in this module's own closure, reset on
   every render() call — matching every other V2 module's lifecycle
   (no module in this repo preserves state across a route re-entry;
   inventing that here would be a new, unasked-for product decision,
   see IA-V2-PLAN-01 §STATE). */
(function () {
  'use strict';

  var A = window.NX_BRABUS_INTELLIGENCE_ADAPTER;

  var conversation = []; // [{role, content, blocks}]
  var sending = false;

  function isRealTextMode() {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    return cfg.mode === 'real_text';
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ============================================================
     STRUCTURED BLOCK RENDERER — renderStructuredBlock(block)
     dispatches by block.type into 6 presentation-only functions.
     Every value shown is read from block.items[].value via
     A.formatValue -- NONE of these functions performs arithmetic,
     derives a delta, or computes anything not already in the payload.
     ============================================================ */

  function metricItemHtml(item) {
    var f = A.formatValue(item.value, item.format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiMetricItem"><p class="modKpiLabel">' + esc(item.label) + '</p>' +
      '<p class="modKpiValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function renderMetrics(block) {
    var items = (block.items || []).map(metricItemHtml).join('');
    return blockPanelHtml(block, '<div class="baiMetricsGrid">' + items + '</div>');
  }

  function renderComparison(block) {
    function side(s) {
      if (!s) return '';
      var items = (s.items || []).map(metricItemHtml).join('');
      return '<div class="baiComparisonSide"><p class="baiComparisonSideLabel">' + esc(s.label) +
        (s.period_label ? ' <span class="modMuted" style="display:inline;margin:0">· ' + esc(s.period_label) + '</span>' : '') + '</p>' +
        '<div class="baiMetricsGrid">' + items + '</div></div>';
    }
    return blockPanelHtml(block, '<div class="baiComparisonGrid">' + side(block.a) + side(block.b) + '</div>', true);
  }

  function renderRanking(block) {
    var rows = (block.items || []).map(function (it) {
      var f = A.formatValue(it.value, it.format);
      var colClass = it.format === 'currency' ? 'modCurrencyCol' : (it.format === 'percent' ? 'modPercentCol' : 'modNumCol');
      return '<tr><td>' + esc(it.label) + '</td><td class="' + colClass + '">' + esc(f.text) + '</td></tr>';
    }).join('');
    var table = '<div class="modTableWrap"><table class="modTable"><thead><tr><th>' + esc(block.dimension || 'Item') + '</th><th>' + esc(block.metric || 'Valor') + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    return blockPanelHtml(block, table, true);
  }

  function renderOperations(block) {
    var rows = (block.items || []).map(function (it) {
      var f = A.formatValue(it.value, it.format);
      return '<div class="baiOperationRow"><span class="modMuted" style="margin:0">' + esc(it.label) + '</span><span>' + esc(f.text) + '</span></div>';
    }).join('');
    return blockPanelHtml(block, '<div class="baiOperationsList">' + rows + '</div>', true);
  }

  function renderScoreBreakdown(block) {
    // Presentation-only, shared KPI primitive -- NEVER calls into
    // score.adapter.js and NEVER recomputes a score (Gate 25 of
    // IA-V2-1): this block is authoritative for this module as-is.
    var items = (block.items || []).map(metricItemHtml).join('');
    return blockPanelHtml(block, '<div class="baiMetricsGrid">' + items + '</div>');
  }

  function renderScoreRanking(block) {
    var rows = (block.items || []).map(function (it, idx) {
      var f = A.formatValue(it.value, it.format);
      return '<tr><td class="modNumCol">' + (idx + 1) + '</td><td>' + esc(it.label) + '</td><td class="modNumCol">' + esc(f.text) + '</td></tr>';
    }).join('');
    var table = '<div class="modTableWrap"><table class="modTable"><thead><tr><th>#</th><th>Vendedor</th><th>Score</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    return blockPanelHtml(block, table, true);
  }

  var RENDERERS = {
    metrics: renderMetrics,
    comparison: renderComparison,
    ranking: renderRanking,
    operations: renderOperations,
    score_breakdown: renderScoreBreakdown,
    score_ranking: renderScoreRanking
  };

  function blockPanelHtml(block, bodyHtml, skipModPanelResult) {
    return '<div class="' + (skipModPanelResult ? '' : 'modPanelResult ') + 'baiBlockPanel">' +
      '<h2 class="baiBlockTitle">' + esc(block.title || 'Resultado') + '</h2>' +
      (block.period_label ? '<p class="baiBlockPeriod">' + esc(block.period_label) + '</p>' : '') +
      bodyHtml + '</div>';
  }

  function renderStructuredBlock(block) {
    var fn = RENDERERS[block.type];
    return fn ? fn(block) : '';
  }

  /* ============================================================
     CONVERSATION RENDERING
     ============================================================ */

  function messageHtml(msg) {
    var roleClass = msg.role === 'user' ? 'baiMessageUser' : 'baiMessageAssistant';
    var roleLabel = msg.role === 'user' ? 'Você' : 'Brabus Intelligence';
    var bubble = '<div class="baiBubble' + (msg.isError ? ' baiBubbleError' : '') + '">' + esc(msg.content) + '</div>';
    var blocksHtml = '';
    if (Array.isArray(msg.blocks) && msg.blocks.length) {
      blocksHtml = '<div class="baiStructuredRegion">' + msg.blocks.map(renderStructuredBlock).join('') + '</div>';
    }
    return '<div class="baiMessage ' + roleClass + '"><span class="baiRoleLabel">' + esc(roleLabel) + '</span>' + bubble + blocksHtml + '</div>';
  }

  function loadingHtml() {
    return '<div class="baiMessage baiMessageAssistant"><div class="baiBubble baiBubbleLoading modLoadingState">' +
      '<span class="modLoadingDot" aria-hidden="true"></span>Analisando os dados do Portal…</div></div>';
  }

  function renderConversation() {
    var el = document.getElementById('baiConversation');
    if (!el) return;
    if (conversation.length === 0) {
      // IA-V2-1-VISUAL-FIX-01 -- no empty-state panel, by explicit
      // human visual UAT request ("like opening ChatGPT": empty means
      // visually empty, not a bordered card announcing there's nothing
      // yet). .baiConversation's own min-height keeps the composer from
      // jumping up flush under the fixture banner; no other placeholder.
      el.innerHTML = '';
      // Returning to the empty state (Nova conversa) should return the
      // page to the top too -- otherwise the window can be left scrolled
      // to wherever the prior, now-cleared conversation had grown to.
      window.scrollTo(0, 0);
      return;
    }
    el.innerHTML = conversation.map(messageHtml).join('') + (sending ? loadingHtml() : '');
    // #baiConversation has no `overflow` of its own -- the whole page
    // grows and the WINDOW scrolls, not this element, so `el.scrollTop`
    // was a no-op (found live during IA-V2-1-VISUAL-QA-01's screenshot
    // pass: several captures came back showing an empty viewport
    // because the window hadn't followed new content into view).
    window.scrollTo(0, document.documentElement.scrollHeight);
  }

  /* ============================================================
     SEND FLOW — simulates the real request/response round trip
     against fixture data ONLY. A short, fixed, deterministic delay
     (150ms) stands in for real network latency, purely so the
     loading state is genuinely reachable/demonstrable and testable
     — never a multi-second wait, never randomized (Gate 37).
     ============================================================ */

  var FIXTURE_LATENCY_MS = 150;

  function setSending(state) {
    sending = state;
    var btn = document.getElementById('baiSendBtn');
    var input = document.getElementById('baiInput');
    if (btn) btn.disabled = state;
    if (input) input.disabled = state;
  }

  // Shared by BOTH transports -- the one place that turns a
  // {response}/{error} result into conversation state, so fixture and
  // real_text can never silently diverge in how they apply a result
  // (scenario_reset pruning, error-bubble styling, etc. all live here
  // exactly once).
  function applyResult(result) {
    setSending(false);
    if (result.error) {
      conversation.push({ role: 'assistant', content: result.error.message, blocks: null, isError: true });
      renderConversation();
      return;
    }
    var normalized = result.response;
    if (normalized.scenario_reset) {
      // Mirrors the real frontend's own scenario_reset handling:
      // prune back to just the triggering user turn, then append the
      // reply -- never invent new reset semantics (Gate 34).
      var lastUserIdx = -1;
      for (var i = conversation.length - 1; i >= 0; i--) {
        if (conversation[i].role === 'user') { lastUserIdx = i; break; }
      }
      if (lastUserIdx > 0) conversation = conversation.slice(lastUserIdx);
    }
    conversation.push({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
    renderConversation();
  }

  function handleSendFixture(text, priorTurns) {
    // Model the real request contract even though nothing is sent over
    // the network -- proves the shape is correct without needing a
    // live backend (Gate 15/32 of IA-V2-1).
    A.createRequest(text, priorTurns);

    setTimeout(function () {
      var scenario = A.resolveFixtureScenario(text);
      if (!scenario) {
        setSending(false);
        conversation.push({ role: 'assistant', content: 'Não tenho um cenário de teste para essa pergunta neste protótipo local — isso não indica uma falha do contrato, apenas que este fixture não cobre esta frase. Veja o seletor de cenários acima para os exemplos disponíveis.', blocks: null, isError: false });
        renderConversation();
        return;
      }
      if (scenario.error) {
        applyResult({ error: scenario.error });
        return;
      }
      applyResult({ response: A.normalizeResponse(scenario.response) });
    }, FIXTURE_LATENCY_MS);
  }

  function handleSendRealText(text, priorTurns) {
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      return;
    }
    window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) {
        applyResult({ error: { status: 401, message: 'Sessão expirada — entre novamente.' } });
        return;
      }
      return A.sendRealText(text, priorTurns, token).then(applyResult);
    }).catch(function () {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
    });
  }

  function handleSend(text) {
    if (sending || !text) return;
    conversation.push({ role: 'user', content: text });
    // setSending BEFORE renderConversation -- renderConversation's own
    // loading-bubble condition reads `sending`, so calling it first
    // would render with sending still false and the bubble would never
    // appear (found live during IA-V2-1-VISUAL-QA-01's loading-state
    // pass).
    setSending(true);
    renderConversation();

    var priorTurns = conversation.slice(0, -1);
    if (isRealTextMode()) handleSendRealText(text, priorTurns);
    else handleSendFixture(text, priorTurns);
  }

  function onNovaConversa() {
    if (sending) return;
    conversation = [];
    renderConversation();
    var input = document.getElementById('baiInput');
    if (input) { input.value = ''; input.focus(); }
  }

  /* ============================================================
     COMPOSER
     ============================================================ */

  function wireComposer() {
    var input = document.getElementById('baiInput');
    var btn = document.getElementById('baiSendBtn');
    function submit() {
      var text = (input.value || '').trim();
      if (!text) return;
      input.value = '';
      handleSend(text);
    }
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', function (e) {
      // Enter submits; Shift+Enter inserts a newline (Gate 12).
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });
  }

  function wireFixtureBanner() {
    var select = document.getElementById('baiFixtureSelect');
    var input = document.getElementById('baiInput');
    if (!select || !input) return;
    select.addEventListener('change', function () {
      var scenario = A.loadFixtureScenario(select.value);
      if (scenario) {
        input.value = scenario.prompt;
        input.focus();
      }
      select.value = '';
    });
  }

  /* ============================================================
     PAGE SHELL
     ============================================================ */

  function fixtureBannerHtml() {
    var options = A.SCENARIOS.map(function (s) {
      return '<option value="' + esc(s.id) + '">' + esc(s.description) + '</option>';
    }).join('');
    return '<div class="modFixtureBanner"><span class="modFixtureLabel">DADOS DE TESTE / CONTRATO LOCAL</span>' +
      '<span>Nenhum backend real conectado — respostas vêm de um contrato de fixture local.</span>' +
      '<label for="baiFixtureSelect">preencher com um cenário de exemplo:</label>' +
      '<select id="baiFixtureSelect"><option value="">— escolher —</option>' + options + '</select></div>';
  }

  function pageHtml() {
    // Gate 34/35 of IA-V2-2 -- the fixture banner/selector are dev/
    // test tooling that must never appear once REAL_TEXT is active;
    // the approved IA-V2-1 clean initial state is otherwise identical
    // either way (Gate 46 visual freeze).
    return '<div class="baiPage">' +
      '<div class="modPageHeader"><div class="modHeaderMain">' +
      '<span class="modEyebrow">INTELLIGENCE</span>' +
      '<h1 class="modTitle">Brabus Intelligence</h1>' +
      '<p class="modSubtitle">Assistente F&amp;I para análise, simulação e apoio comercial.</p>' +
      '</div><div class="modHeaderActions baiHeaderActions">' +
      '<button type="button" class="modBtn modBtnGhost" id="baiNewChatBtn">Nova conversa</button>' +
      '</div></div>' +
      (isRealTextMode() ? '' : fixtureBannerHtml()) +
      '<div class="baiWorkspace">' +
      '<div class="baiConversation" id="baiConversation" aria-live="polite" aria-atomic="false"></div>' +
      '<div class="baiComposer">' +
      '<textarea id="baiInput" class="baiComposerInput" aria-label="Pergunta para a Brabus Intelligence" placeholder="Pergunte sobre financiamento, resultado, score ou condição financeira..." rows="1"></textarea>' +
      '<div class="baiComposerActions"><button type="button" class="modBtn modBtnPrimary" id="baiSendBtn">Enviar</button></div>' +
      '</div></div></div>';
  }

  window.NX_BRABUS_INTELLIGENCE_PAGE = {
    render: function (outlet) {
      conversation = [];
      sending = false;
      outlet.innerHTML = pageHtml();
      wireComposer();
      wireFixtureBanner();
      document.getElementById('baiNewChatBtn').addEventListener('click', onNovaConversa);
      renderConversation();
      return Promise.resolve();
    },
    // exposed for tests, DOM-independent
    renderStructuredBlock: renderStructuredBlock,
    isRealTextMode: isRealTextMode
  };
})();
