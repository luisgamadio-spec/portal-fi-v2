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
     approved page uses — never duplicated/reimplemented here).
     ============================================================ */

  function messageHtml(msg) {
    var roleClass = msg.role === 'user' ? 'baiMessageUser' : 'baiMessageAssistant';
    var roleLabel = msg.role === 'user' ? 'Você' : 'Brabus Intelligence';
    var isAssistantProse = msg.role !== 'user' && !msg.isError;
    var bubbleContent = isAssistantProse ? P.renderAssistantProse(msg.content) : esc(msg.content);
    var bubbleClass = 'baiBubble' + (msg.isError ? ' baiBubbleError' : '') + (isAssistantProse ? ' baiBubbleMd' : '');
    var bubble = '<div class="' + bubbleClass + '">' + bubbleContent + '</div>';
    var blocksHtml = '';
    if (Array.isArray(msg.blocks) && msg.blocks.length) {
      blocksHtml = '<div class="baiStructuredRegion">' + msg.blocks.map(P.renderStructuredBlock).join('') + '</div>';
    }
    return '<div class="baiMessage ' + roleClass + '"><span class="baiRoleLabel">' + esc(roleLabel) + '</span>' + bubble + blocksHtml + '</div>';
  }

  function loadingHtml() {
    return '<div class="baiMessage baiMessageAssistant"><div class="baiBubble baiBubbleLoading modLoadingState">' +
      '<span class="modLoadingDot" aria-hidden="true"></span>Analisando os dados do Portal…</div></div>';
  }

  function renderConversation() {
    var el = document.getElementById('baiPanelConversation');
    if (!el) return;
    var snap = S.getSnapshot();
    var busy = snap.textState === S.TEXT_STATES.SENDING || snap.textState === S.TEXT_STATES.THINKING;
    if (snap.conversation.length === 0 && !busy) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = snap.conversation.map(messageHtml).join('') + (busy ? loadingHtml() : '');
    el.scrollTop = el.scrollHeight;
  }

  function updateContextChip() {
    var chip = document.getElementById('baiPanelContextChip');
    if (!chip) return;
    var desc = C.describe();
    if (desc) { chip.hidden = false; chip.textContent = 'Contexto: ' + desc; }
    else { chip.hidden = true; chip.textContent = ''; }
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
      return;
    }
    var normalized = result.response;
    if (normalized.scenario_reset) S.spliceFromLastUser();
    S.pushMessage({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
    // COMPLETE is a momentary signal (Section 13), not a resting
    // composer-disabled state -- settle to OPEN_IDLE right after.
    S.setTextState(S.TEXT_STATES.COMPLETE);
    renderConversation();
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

  function handleSendRealText(text, priorTurns) {
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      return;
    }
    window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) { applyResult({ error: { status: 401, message: 'Sessão expirada — entre novamente.' } }); return; }
      return A.sendRealText(text, priorTurns, token).then(applyResult);
    }).catch(function () {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
    });
  }

  function handleSend(text) {
    if (!text) return;
    var st = S.getTextState();
    if (st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING) return;
    S.pushMessage({ role: 'user', content: text, blocks: null, isError: false });
    S.setTextState(S.TEXT_STATES.SENDING);
    applyPersistentState(S.TEXT_STATES.SENDING);
    renderConversation();
    var priorTurns = S.getConversation().slice(0, -1);
    S.setTextState(S.TEXT_STATES.THINKING);
    applyPersistentState(S.TEXT_STATES.THINKING);
    if (P.isRealTextMode()) handleSendRealText(text, priorTurns);
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
    if (input) { input.value = ''; input.focus(); }
  }

  /* ============================================================
     COMPOSER
     ============================================================ */

  function wireComposer() {
    var input = document.getElementById('baiPanelInput');
    var btn = document.getElementById('baiPanelSendBtn');
    function submit() {
      var text = (input.value || '').trim();
      if (!text) return;
      input.value = '';
      handleSend(text);
    }
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', function (e) {
      // Enter submits; Shift+Enter inserts a newline (Section 36),
      // matching the routed page's own composer exactly.
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    input.addEventListener('input', function () {
      var st = S.getTextState();
      if (st === S.TEXT_STATES.OPEN_IDLE || st === S.TEXT_STATES.COMPLETE || st === S.TEXT_STATES.ERROR) {
        S.setTextState(S.TEXT_STATES.COMPOSING);
      }
    });
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
    return '<aside class="baiPanelDrawer" id="baiPanelDrawer" role="dialog" aria-modal="false" aria-label="Brabus Intelligence" hidden>' +
      '<div class="baiPanelHeader">' +
      '<div><span class="modEyebrow">INTELLIGENCE</span><h2 class="baiPanelTitle">Brabus Intelligence</h2>' +
      '<p class="baiPanelContextChip" id="baiPanelContextChip" hidden></p></div>' +
      '<div class="baiPanelHeaderActions">' +
      '<button type="button" class="modBtn modBtnGhost" id="baiPanelNewChatBtn">Nova conversa</button>' +
      '<button type="button" class="baiPanelCloseBtn" id="baiPanelCloseBtn" aria-label="Fechar Brabus Intelligence">&times;</button>' +
      '</div></div>' +
      '<div class="baiPanelBody"><div class="baiConversation" id="baiPanelConversation" aria-live="polite" aria-atomic="false"></div></div>' +
      '<div class="baiComposer baiPanelComposer">' +
      '<textarea id="baiPanelInput" class="baiComposerInput" aria-label="Pergunta para a Brabus Intelligence" placeholder="Pergunte sobre financiamento, resultado, score ou condição financeira..." rows="1"></textarea>' +
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
