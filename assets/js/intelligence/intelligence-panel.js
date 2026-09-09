/* PORTAL-NEXT V2 — Brabus Intelligence PERSISTENT PANEL (IA-3E).

   The "operating intelligence layer" experience (IA-3E Section 12/62):
   a shell-level launcher + drawer, mounted ONCE into #nxOverlayRoot by
   shell.js's boot() — NOT into #nxContentOutlet, which
   dispatchModule() rewrites on every route change. Because this
   module's own DOM is never touched by route dispatch, and its
   conversation lives in intelligence-state.js's own module-level
   store (not this file's render() closure), the conversation survives
   navigating between modules — the routed full page
   (assets/js/brabus-intelligence.js, #/brabus-intelligence) still
   exists unchanged alongside this, as a separate, already Human-
   approved experience; this file does not replace it, per Section 10
   "do not create duplicate Intelligence UI" this reuses its adapter
   and its two exported pure renderers (renderAssistantProse,
   renderStructuredBlock) instead of reimplementing Markdown/block
   rendering a second time.

   Transport is UNCHANGED: window.NX_BRABUS_INTELLIGENCE_ADAPTER (the
   same contract-tested adapter the routed page uses) is the only
   thing that ever calls fetch — this file never calls fetch/XHR
   itself, matching the existing module's own zero-business-logic
   discipline. */
(function () {
  'use strict';

  var A, P, S, C; // assigned in mount(): adapter, page (render helpers), state store, context provider

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var FIXTURE_LATENCY_MS = 150;

  /* ============================================================
     VISIBILITY — MASTER-only presentation (Section 15/18/19/49).
     Reads ONLY window.NX_AUTH_CORE's own existing, server-derived
     Auth Context (Object.freeze'd there, see auth-core.js) — never
     localStorage, DOM, a URL param, or anything this file invents.
     Non-visible means the launcher/drawer DOM does not exist at all
     (removed from the tree, not CSS-hidden) — a test can assert
     document.getElementById('baiLauncherRoot') === null. ============ */

  function isVisibleNow() {
    var AC = window.NX_AUTH_CORE;
    if (!AC) return false;
    var state = AC.getState();
    var STATES = AC.STATES;
    var authorized;
    // AUTH_NOT_CONFIGURED mirrors every other module's own convention
    // (auth-core.js's isModuleAuthorized) — no real Supabase Auth
    // wired on this host, so the pre-Auth-Foundation behavior applies.
    if (state === STATES.AUTH_NOT_CONFIGURED) authorized = true;
    else if (state === STATES.AUTHORIZED) {
      var ctx = AC.getContext();
      authorized = !!(ctx && ctx.isMaster === true);
    } else authorized = false;
    if (!authorized) return false;
    // Never stack the persistent launcher on top of the routed,
    // dedicated Intelligence page itself (#/brabus-intelligence,
    // unchanged this Wave) — a second, redundant Intelligence surface
    // on its own page would be confusing UX, not a feature, and the
    // two composers sharing the same .baiComposer content class (by
    // design, for visual consistency) would otherwise sit stacked in
    // the same document. Suppressed by ROUTE, not by page identity, so
    // it also covers direct hash navigation, not only launcher clicks.
    if (C) {
      var ctxSnap = C.getSnapshot();
      if (ctxSnap && ctxSnap.route === 'brabus-intelligence') return false;
    }
    return true;
  }

  /* ============================================================
     RENDERING — reuses NX_BRABUS_INTELLIGENCE_PAGE's own exported
     renderAssistantProse/renderStructuredBlock (the exact same
     Markdown-safety and structured-block logic the routed, Human-
     approved page uses — never duplicated/reimplemented here) for
     every block type EXCEPT the compact `metrics` type, which gets
     its own presentation-only "evidence" treatment below (IA-3E.4).
     Every other type (comparison/ranking/operations/score_*) still
     goes through P.renderStructuredBlock completely unchanged.
     ============================================================ */

  /* ---------- Compact metrics evidence (IA-3E.4) ----------
     Human found the generic 2-column KPI grid still read as a "mini
     dashboard" even after IA-3E.3's alignment fix, with a redundant
     block heading ("GRUPO — MÊS ANTERIOR · mês anterior") repeating
     what the prose above it already said. This groups a metrics
     block's own items into two presentation lanes using metadata the
     block ALREADY carries on every item — item.format — never an
     invented business rule:
       - format === 'currency'  -> a "financial fact" (label above
         value, 2 per row) — the only values a Human actually reads
         as money and wants aligned/scannable;
       - anything else (int/percent/text/date/null) -> a compact,
         wrapping inline "strip" chip ("13 Vendas") — volume/share/
         count-shaped facts that read naturally as a phrase.
     This is why it generalizes to 2-6+ metrics of any real block
     without hardcoding this fixture's 5 specific keys: the grouping
     rule is the same regardless of which/how-many items a block has.
     No value is ever dropped — every item in block.items renders
     somewhere, either as a chip or as a fact. Only the `metrics` type
     is handled here (Section 15/35) — comparison/ranking/operations/
     score_* keep using the shared renderer's own presentation. */

  function isFinancialItem(item) {
    return !!item && item.format === 'currency';
  }

  function metricChipHtml(item) {
    var f = A.formatValue(item.value, item.format);
    return '<span class="baiMetricChip"><strong>' + esc(f.text) + '</strong> ' + esc(item.label) + '</span>';
  }

  function metricFactHtml(item) {
    var f = A.formatValue(item.value, item.format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiMetricFact"><p class="baiMetricFactLabel">' + esc(item.label) + '</p>' +
      '<p class="baiMetricFactValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function compactMetricsHtml(block) {
    var items = Array.isArray(block.items) ? block.items : [];
    var strip = items.filter(function (it) { return !isFinancialItem(it); });
    var facts = items.filter(isFinancialItem);
    // The block's own title/period is NOT dropped -- it is real
    // semantic context (e.g. which group/period this answer covers)
    // -- just not visually repeated when the prose already says it.
    // Screen-reader-only, same clip-rect technique as the role labels
    // (Section 5/19/13: "preserve semantic information for
    // accessibility... do not display redundant title/subtitle").
    var headingParts = [block.title, block.period_label].filter(function (v) { return !!v; });
    var headingSr = headingParts.length ? '<span class="baiSrOnly">' + esc(headingParts.join(' — ')) + '</span>' : '';
    var stripHtml = strip.length ? '<div class="baiMetricStrip">' + strip.map(metricChipHtml).join('') + '</div>' : '';
    var factsHtml = facts.length ? '<div class="baiMetricFacts">' + facts.map(metricFactHtml).join('') + '</div>' : '';
    if (!strip.length && !facts.length) {
      return '<div class="baiCompactMetrics">' + headingSr + '<p class="modMuted">Sem itens para exibir.</p></div>';
    }
    return '<div class="baiCompactMetrics">' + headingSr + stripHtml + factsHtml + '</div>';
  }

  function renderOneBlock(block) {
    return block && block.type === 'metrics' ? compactMetricsHtml(block) : P.renderStructuredBlock(block);
  }

  function messageHtml(msg) {
    var isUser = msg.role === 'user';
    var roleClass = isUser ? 'baiMessageUser' : 'baiMessageAssistant';
    var roleLabel = isUser ? 'Você' : 'Brabus Intelligence';
    var labelHtml = '<span class="baiRoleLabel">' + esc(roleLabel) + '</span>';

    if (isUser || msg.isError) {
      // User turns and error turns keep the plain bubble treatment --
      // there is no metrics/evidence to cohere them with.
      var plainClass = 'baiBubble' + (msg.isError ? ' baiBubbleError' : '');
      return '<div class="baiMessage ' + roleClass + '">' + labelHtml +
        '<div class="' + plainClass + '">' + esc(msg.content) + '</div></div>';
    }

    // A real assistant answer (IA-3E.3 Section 11 -- conversation
    // first, data second): prose renders DIRECTLY on the conversation
    // surface, no card. Optional structured facts follow as a subtly
    // divided secondary section (intelligence.css's .baiAnswerMetrics),
    // never a second competing bordered box. The structured-block
    // markup itself (P.renderStructuredBlock) is 100% the shared,
    // unmodified renderer -- only the wrapper it sits in here differs.
    var proseHtml = '<div class="baiAnswerProse baiBubbleMd">' + P.renderAssistantProse(msg.content) + '</div>';
    var metricsHtml = '';
    if (Array.isArray(msg.blocks) && msg.blocks.length) {
      metricsHtml = '<div class="baiAnswerMetrics">' + msg.blocks.map(renderOneBlock).join('') + '</div>';
    }
    return '<div class="baiMessage ' + roleClass + '">' + labelHtml + proseHtml + metricsHtml + '</div>';
  }

  function loadingHtml() {
    return '<div class="baiMessage baiMessageAssistant"><div class="baiBubble baiBubbleLoading modLoadingState">' +
      '<span class="modLoadingDot" aria-hidden="true"></span>Analisando os dados do Portal…</div></div>';
  }

  var NEAR_BOTTOM_THRESHOLD_PX = 80;

  function renderConversation() {
    var el = document.getElementById('baiPanelConversation');
    if (!el) return;
    // .baiPanelBody is the real `overflow-y:auto` container (see the
    // scroll-target bugfix below) -- read its scroll position BEFORE
    // re-rendering, so a Human who deliberately scrolled up to reread
    // an earlier turn isn't yanked back down by a new message arriving
    // (IA-3E.3 Section 26, a soft, deterministic improvement over the
    // IA-3E.2-disclosed D1 limitation): only auto-scroll if they were
    // already near the bottom.
    var scrollHost = el.closest('.baiPanelBody') || el;
    var wasNearBottom = (scrollHost.scrollHeight - scrollHost.scrollTop - scrollHost.clientHeight) <= NEAR_BOTTOM_THRESHOLD_PX;

    var snap = S.getSnapshot();
    var busy = snap.textState === S.TEXT_STATES.SENDING || snap.textState === S.TEXT_STATES.THINKING;
    if (snap.conversation.length === 0 && !busy) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = snap.conversation.map(messageHtml).join('') + (busy ? loadingHtml() : '');
    // BUGFIX (found live during IA-3E.2's own long-conversation check):
    // #baiPanelConversation itself never overflows -- it grows freely
    // inside .baiPanelBody. Setting scrollTop on the wrong (non-
    // scrolling) element silently did nothing -- the newest message
    // was reachable only by a human manually scrolling. Scroll the
    // real container instead, and only when appropriate (above).
    if (wasNearBottom) scrollHost.scrollTop = scrollHost.scrollHeight;
  }

  function updateContextChip() {
    var chip = document.getElementById('baiPanelContextChip');
    if (!chip) return;
    var desc = C.describe();
    if (desc) {
      chip.hidden = false;
      // A small dot + "Analisando: X" reads as a subtle status line,
      // not a technical "Contexto:" label (IA-3E.2 Section 10) --
      // still presentation-only, still never sent anywhere (esc()
      // used since desc can include a module-published, non-backend-
      // trusted string via publish()).
      chip.innerHTML = '<span class="baiPanelContextDot" aria-hidden="true"></span>' +
        '<span class="baiPanelContextText">Analisando: ' + esc(desc) + '</span>';
    } else {
      chip.hidden = true;
      chip.innerHTML = '';
    }
  }

  /* ============================================================
     STICKY STATUS (DISABLED/SESSION_EXPIRED/FORBIDDEN) — Section 16/
     40/41/50/51/52: a clean, non-technical status line, composer
     disabled while stuck, NEVER an automatic retry/timer — the only
     way out is a deliberate human action ("Nova conversa" or a fresh
     send once the underlying condition has genuinely changed).
     ============================================================ */

  function statusLineFor(state) {
    if (state === S.TEXT_STATES.DISABLED) return 'Brabus Intelligence está temporariamente indisponível.';
    if (state === S.TEXT_STATES.SESSION_EXPIRED) return 'Sessão expirada — entre novamente para continuar.';
    if (state === S.TEXT_STATES.FORBIDDEN) return 'Este recurso não está disponível para o seu perfil.';
    return '';
  }

  function setComposerEnabled(enabled) {
    var input = document.getElementById('baiPanelInput');
    var btn = document.getElementById('baiPanelSendBtn');
    if (input) input.disabled = !enabled;
    if (btn) btn.disabled = !enabled;
  }

  function applyPersistentState(state) {
    var line = document.getElementById('baiPanelStatusLine');
    var msg = statusLineFor(state);
    if (line) {
      if (msg) { line.hidden = false; line.textContent = msg; }
      else { line.hidden = true; line.textContent = ''; }
    }
    var locked = state === S.TEXT_STATES.DISABLED || state === S.TEXT_STATES.SESSION_EXPIRED ||
      state === S.TEXT_STATES.FORBIDDEN || state === S.TEXT_STATES.SENDING || state === S.TEXT_STATES.THINKING;
    setComposerEnabled(!locked);
  }

  /* ============================================================
     SEND FLOW — mirrors brabus-intelligence.js's own applyResult/
     handleSendFixture/handleSendRealText contract-for-contract (same
     adapter calls, same error-status mapping), rewritten to drive the
     explicit TEXT_STATES machine instead of two closure booleans.
     ============================================================ */

  // IA-3G.5A -- dev-only console diagnostic (never rendered, never
  // part of the approved drawer UI -- Section 23's own "console;
  // dedicated dev object" allowance). Only fires when `result._devTiming`
  // is present, which only ever happens for a real_text response that
  // carried the homolog-only `_homolog_edge_timing` field -- absent for
  // fixture mode, absent for any error short-circuited before fetch,
  // and (by construction, since this repo never modified the real
  // production Edge Function) absent for production. Logs numbers,
  // a random correlation id, and an opaque instance id only -- no
  // prompt, no reply text, no business data.
  function logDevTiming(devTiming, renderCompleteAt) {
    if (!devTiming) return;
    var out = {};
    for (var k in devTiming) out[k] = devTiming[k];
    if (devTiming.client_receive_at) out.render_ms = renderCompleteAt - devTiming.client_receive_at;
    if (devTiming.ui_submit_at) out.total_ui_ms = renderCompleteAt - devTiming.ui_submit_at;
    // eslint-disable-next-line no-console
    console.log('[bai-timing]', out);
  }

  function applyResult(result) {
    if (result.error) {
      var status = result.error.status;
      S.pushMessage({ role: 'assistant', content: result.error.message, blocks: null, isError: true });
      if (status === 503) S.setTextState(S.TEXT_STATES.DISABLED);
      else if (status === 401) S.setTextState(S.TEXT_STATES.SESSION_EXPIRED);
      else if (status === 403) S.setTextState(S.TEXT_STATES.FORBIDDEN);
      else S.setTextState(S.TEXT_STATES.ERROR);
      applyPersistentState(S.getTextState());
      renderConversation();
      logDevTiming(result._devTiming, Date.now());
      return;
    }
    var normalized = result.response;
    if (normalized.scenario_reset) S.spliceFromLastUser();
    S.pushMessage({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
    // COMPLETE is a momentary signal (Section 13), not a resting
    // composer-disabled state -- settle to OPEN_IDLE right after.
    S.setTextState(S.TEXT_STATES.COMPLETE);
    renderConversation();
    logDevTiming(result._devTiming, Date.now());
    S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
  }

  function handleSendFixture(text, priorTurns) {
    A.createRequest(text, priorTurns); // models the contract shape even though nothing is sent (Gate 15/32, matching the routed page)
    setTimeout(function () {
      var scenario = A.resolveFixtureScenario(text);
      if (!scenario) {
        S.pushMessage({ role: 'assistant', isError: false, blocks: null, content: 'Não tenho um cenário de teste para essa pergunta neste protótipo local — isso não indica uma falha do contrato, apenas que este fixture não cobre esta frase.' });
        S.setTextState(S.TEXT_STATES.OPEN_IDLE);
        applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
        renderConversation();
        return;
      }
      if (scenario.error) { applyResult({ error: scenario.error }); return; }
      applyResult({ response: A.normalizeResponse(scenario.response) });
    }, FIXTURE_LATENCY_MS);
  }

  function handleSendRealText(text, priorTurns, uiSubmitAt) {
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      return;
    }
    // IA-3G.5A -- getAccessToken() calls the real Supabase SDK's own
    // auth.getSession(), which can silently perform a real network
    // token-refresh call before resolving (supabase-js's own documented
    // behavior when the current access token is expired/near-expiry) --
    // a plausible pre-fetch delay entirely invisible to Edge-side
    // instrumentation. Measured here, separately from the fetch() that
    // follows, specifically to test that hypothesis with real numbers.
    var t_getToken = Date.now();
    window.NX_AUTH.getAccessToken().then(function (token) {
      var getTokenMs = Date.now() - t_getToken;
      if (!token) { applyResult({ error: { status: 401, message: 'Sessão expirada — entre novamente.' } }); return; }
      return A.sendRealText(text, priorTurns, token, { uiSubmitAt: uiSubmitAt, getTokenMs: getTokenMs }).then(applyResult);
    }).catch(function () {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
    });
  }

  function handleSend(text) {
    if (!text) return;
    // IA-3G.5A -- captured as the very first line, before any state
    // change or DOM work, so it marks the true moment the Human's
    // action was received by this code.
    var uiSubmitAt = Date.now();
    var st = S.getTextState();
    if (st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING) return;
    S.pushMessage({ role: 'user', content: text, blocks: null, isError: false });
    S.setTextState(S.TEXT_STATES.SENDING);
    applyPersistentState(S.TEXT_STATES.SENDING);
    renderConversation();
    var priorTurns = S.getConversation().slice(0, -1);
    S.setTextState(S.TEXT_STATES.THINKING);
    applyPersistentState(S.TEXT_STATES.THINKING);
    if (P.isRealTextMode()) handleSendRealText(text, priorTurns, uiSubmitAt);
    else handleSendFixture(text, priorTurns);
  }

  function onNovaConversa() {
    var st = S.getTextState();
    if (st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING) return;
    S.resetConversation();
    S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
    renderConversation();
    var input = document.getElementById('baiPanelInput');
    if (input) { input.value = ''; autoGrowComposer(input); input.focus(); }
  }

  /* ============================================================
     COMPOSER — auto-grow (IA-3E.2 Section 14, high priority). A
     static `rows="1"` + fixed CSS height was the exact cause of the
     Human-reported white native scrollbar: any wrapped second line
     immediately overflowed a textarea whose height never changed,
     forcing the browser's own default scrollbar UI to appear. This
     resizes the element itself (bounded [MIN,MAX]) so the browser's
     internal scrollbar only ever appears once content genuinely
     exceeds MAX_COMPOSER_HEIGHT — and even then it is CSS-styled
     (intelligence.css's scrollbar-width/::-webkit-scrollbar rules),
     never the stark default.
     ============================================================ */

  var MIN_COMPOSER_HEIGHT = 40;
  var MAX_COMPOSER_HEIGHT = 132; // must match intelligence.css's .baiComposerInput max-height

  function autoGrowComposer(el) {
    el.style.height = 'auto';
    var next = Math.min(Math.max(el.scrollHeight, MIN_COMPOSER_HEIGHT), MAX_COMPOSER_HEIGHT);
    el.style.height = next + 'px';
  }

  function wireComposer() {
    var input = document.getElementById('baiPanelInput');
    var btn = document.getElementById('baiPanelSendBtn');
    function submit() {
      var text = (input.value || '').trim();
      if (!text) return;
      input.value = '';
      autoGrowComposer(input);
      handleSend(text);
    }
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', function (e) {
      // Enter submits; Shift+Enter inserts a newline (Section 36),
      // matching the routed page's own composer exactly.
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    input.addEventListener('input', function () {
      autoGrowComposer(input);
      var st = S.getTextState();
      if (st === S.TEXT_STATES.OPEN_IDLE || st === S.TEXT_STATES.COMPLETE || st === S.TEXT_STATES.ERROR) {
        S.setTextState(S.TEXT_STATES.COMPOSING);
      }
    });
    autoGrowComposer(input);
  }

  /* ============================================================
     OPEN / CLOSE
     ============================================================ */

  function openPanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    var backdrop = document.getElementById('baiPanelBackdrop');
    var launcherBtn = document.getElementById('baiLauncherBtn');
    if (drawer) drawer.hidden = false;
    if (backdrop) backdrop.hidden = false;
    if (launcherBtn) launcherBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('bai-panel-open');
    if (S.getTextState() === S.TEXT_STATES.CLOSED) S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.getTextState());
    renderConversation();
    updateContextChip();
    var input = document.getElementById('baiPanelInput');
    if (input) input.focus();
  }

  function closePanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    var backdrop = document.getElementById('baiPanelBackdrop');
    var launcherBtn = document.getElementById('baiLauncherBtn');
    if (drawer) drawer.hidden = true;
    if (backdrop) backdrop.hidden = true;
    if (launcherBtn) { launcherBtn.setAttribute('aria-expanded', 'false'); launcherBtn.focus(); }
    document.body.classList.remove('bai-panel-open');
    // Closing never discards the conversation (intelligence-state.js's
    // own store is untouched) — only the panel's own visibility state
    // resets, matching a real "minimize", not a reset (Section 12).
    S.setTextState(S.TEXT_STATES.CLOSED);
  }

  function togglePanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    if (drawer && !drawer.hidden) closePanel();
    else openPanel();
  }

  /* ============================================================
     DOM BUILD / VISIBILITY LIFECYCLE
     ============================================================ */

  function launcherHtml() {
    return '<button type="button" class="baiLauncherBtn" id="baiLauncherBtn" aria-expanded="false" aria-controls="baiPanelDrawer" aria-label="Abrir Brabus Intelligence">' +
      '<span class="baiLauncherIcon" aria-hidden="true">&#10022;</span></button>' +
      '<div class="baiPanelBackdrop" id="baiPanelBackdrop" hidden></div>';
  }

  function panelHtml() {
    // No "INTELLIGENCE" eyebrow badge -- the title directly below it
    // already said the same thing (IA-3E.2 Section 8's own finding E);
    // removed from markup entirely, not just visually hidden.
    //
    // IA-3G.3 -- transport provenance (Section 22). The drawer had NO
    // way to tell a fixture-mode session apart from a real_text one --
    // the routed page has its own fixtureBannerHtml(), but this panel
    // never did. Found live: a local UAT scratchpad file
    // (intelligence-runtime-config.local.js, gitignored) went missing
    // between Waves, silently reverting the whole page to the
    // committed 'fixture' default, and the Human's screenshot -- a
    // perfectly plausible-looking synthetic answer -- gave no visible
    // signal that had happened. Two layers, both inert on any
    // non-real_text-configured host in production (mode there is
    // always the committed 'fixture' default, so this never renders
    // there either -- it's not a localhost-only check, it's a
    // mode-only one, exactly like the routed page's own banner):
    //   1. a data-nx-transport attribute (fixture|real_text) on the
    //      drawer root -- zero visual footprint, lets a test or a
    //      developer's own console check prove the mode directly;
    //   2. a small text line, visible ONLY in fixture mode (mirrors
    //      the routed page's fixtureBannerHtml() convention exactly),
    //      so a Human doing local UAT sees it, not just an automated
    //      test -- completely absent from the DOM in real_text mode,
    //      so the Human-approved real-mode drawer is untouched.
    var transportMode = (P && P.isRealTextMode()) ? 'real_text' : 'fixture';
    // Reuses .modFixtureBanner as-is (module-system.css) -- the SAME
    // shared "dev tooling, not production UI" visual language every
    // other module's own fixture banner already uses, rather than
    // inventing a second, competing visual treatment for the same
    // concept.
    var provenanceBannerHtml = transportMode === 'fixture'
      ? '<p class="modFixtureBanner baiPanelProvenanceBanner" id="baiPanelProvenanceBanner" style="margin:0 var(--bai-rail);border-radius:var(--radius-sm)">Modo de teste local — respostas não vêm do servidor real.</p>'
      : '';
    return '<aside class="baiPanelDrawer" id="baiPanelDrawer" role="dialog" aria-modal="false" aria-label="Brabus Intelligence" data-nx-transport="' + transportMode + '" hidden>' +
      '<div class="baiPanelHeader">' +
      '<div><h2 class="baiPanelTitle">Brabus Intelligence</h2>' +
      '<p class="baiPanelContextChip" id="baiPanelContextChip" hidden></p></div>' +
      '<div class="baiPanelHeaderActions">' +
      '<button type="button" class="modBtn modBtnGhost" id="baiPanelNewChatBtn">Nova conversa</button>' +
      '<button type="button" class="baiPanelCloseBtn" id="baiPanelCloseBtn" aria-label="Fechar Brabus Intelligence">&times;</button>' +
      '</div></div>' +
      provenanceBannerHtml +
      '<div class="baiPanelBody"><div class="baiConversation" id="baiPanelConversation" aria-live="polite" aria-atomic="false"></div></div>' +
      '<div class="baiComposer baiPanelComposer">' +
      '<textarea id="baiPanelInput" class="baiComposerInput" aria-label="Pergunta para a Brabus Intelligence" placeholder="Pergunte sobre financiamento, resultado ou score..." rows="1"></textarea>' +
      '<div class="baiComposerActions"><button type="button" class="modBtn modBtnPrimary" id="baiPanelSendBtn">Enviar</button></div>' +
      '</div>' +
      '<p class="baiPanelStatusLine" id="baiPanelStatusLine" hidden></p>' +
      '</aside>';
  }

  var panelBuilt = false;

  function buildPanelDom() {
    if (panelBuilt) return;
    var root = document.getElementById('nxOverlayRoot');
    if (!root) return;
    var wrap = document.createElement('div');
    wrap.className = 'baiLauncherRoot';
    wrap.id = 'baiLauncherRoot';
    wrap.innerHTML = launcherHtml() + panelHtml();
    root.appendChild(wrap);

    wireComposer();
    document.getElementById('baiPanelNewChatBtn').addEventListener('click', onNovaConversa);
    document.getElementById('baiPanelCloseBtn').addEventListener('click', closePanel);
    document.getElementById('baiPanelBackdrop').addEventListener('click', closePanel);
    document.getElementById('baiLauncherBtn').addEventListener('click', togglePanel);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var drawer = document.getElementById('baiPanelDrawer');
        if (drawer && !drawer.hidden) closePanel();
      }
    });

    S.onChange(function () { renderConversation(); });
    C.onChange(function () { updateContextChip(); });

    panelBuilt = true;
    renderConversation();
    applyPersistentState(S.getTextState());
    updateContextChip();
  }

  function refreshVisibility() {
    var visible = isVisibleNow();
    var existing = document.getElementById('baiLauncherRoot');
    if (visible) {
      if (!existing) buildPanelDom();
    } else if (existing) {
      // Real removal (Section 49: "do not rely only on CSS hiding"),
      // not display:none — a non-MASTER/unauthenticated viewer has no
      // Intelligence DOM node anywhere in the document at all.
      existing.parentNode.removeChild(existing);
      panelBuilt = false;
      document.body.classList.remove('bai-panel-open');
      S.setTextState(S.TEXT_STATES.CLOSED);
    }
  }

  window.NX_INTELLIGENCE_PANEL = {
    mount: function () {
      if (!window.NX_BRABUS_INTELLIGENCE_ADAPTER || !window.NX_BRABUS_INTELLIGENCE_PAGE ||
        !window.NX_INTELLIGENCE_STATE || !window.NX_INTELLIGENCE_CONTEXT) {
        console.error('[intelligence-panel] a required dependency is missing — not mounting');
        return;
      }
      A = window.NX_BRABUS_INTELLIGENCE_ADAPTER;
      P = window.NX_BRABUS_INTELLIGENCE_PAGE;
      S = window.NX_INTELLIGENCE_STATE;
      C = window.NX_INTELLIGENCE_CONTEXT;
      if (window.NX_AUTH_CORE) window.NX_AUTH_CORE.onStateChange(function () { refreshVisibility(); });
      // Route changes can also flip visibility (entering/leaving
      // #/brabus-intelligence, see isVisibleNow's route suppression
      // above) — always active, independent of whether the panel DOM
      // has been built yet (buildPanelDom's own C.onChange only wires
      // the context CHIP, once the panel exists).
      C.onChange(function () { refreshVisibility(); });
      refreshVisibility();
    },
    // exposed for tests
    isVisibleNow: isVisibleNow,
    openPanel: function () { openPanel(); },
    closePanel: function () { closePanel(); },
    // Test-only hook: re-runs the same visibility decision mount()'s
    // own onStateChange listener runs on a real auth transition. Real
    // callers never need this — production visibility changes are
    // driven exclusively by genuine NX_AUTH_CORE state transitions.
    refresh: function () { refreshVisibility(); }
  };
})();
