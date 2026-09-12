/* PORTAL-NEXT V2 — Brabus Intelligence VOICE session manager (IA-3H.1).

   ONE INTELLIGENCE CORE, TWO SURFACES. Voice is not a second assistant:
   this file owns ONLY the Realtime/WebRTC conversational layer (session
   lifecycle, microphone, audio output, turn detection, interruption) --
   every real business question still reaches the exact same governed
   transport Text already uses, window.NX_BRABUS_INTELLIGENCE_ADAPTER's
   own sendRealText(), calling the SAME portal-ai-homolog Edge Function
   with the Human's own real session. Zero financial calculation, zero
   tool-selection logic, zero copy of any business rule lives here --
   see bridgeToPortalIntelligence() below, the ONLY place this file
   touches "Brabus Intelligence" content, and even there it only relays.

   Ported BEHAVIORALLY (not copy-pasted) from the existing, already-
   proven V1 Realtime controller (portal-financiamento-brabus-secure /
   assets/js/portal-ai-realtime.js, IA-UAT-VOICE-02/03) -- same WebRTC
   session shape, same ephemeral-credential mint call, same governed
   tool bridge, same processedCallIds/latestCallId duplicate/stale-call
   protection, same cleanup discipline. Rewired onto V2's own module
   conventions: window.NX_INTELLIGENCE_CONFIG for endpoints (not a
   hardcoded SUPABASE_URL global), window.NX_AUTH.getAccessToken() for
   auth (not supabaseClient.auth.getSession() directly -- V2 never
   touches Supabase outside auth-boundary.js), and
   window.NX_INTELLIGENCE_STATE's own VOICE_STATES enum (already
   declared inert since IA-3E) for the state machine, instead of a
   second, parallel state object.

   Conversation turns are pushed into NX_INTELLIGENCE_STATE exactly like
   Text's own handleSend/applyResult do (assets/js/intelligence/
   intelligence-panel.js) -- the SAME #baiPanelConversation surface
   renders them automatically via its existing S.onChange subscription.
   There is no second transcript pane, and no Voice-specific renderer.

   Privacy: no raw audio, no full transcript, no JWT/credential of any
   kind is ever written to localStorage. The only persisted state is a
   bounded, sanitized diagnostics snapshot (see the DIAGNOSTICS section
   below) -- numbers, state names, and short error-class strings only. */
(function () {
  'use strict';

  var S, A; // intelligence-state, adapter -- assigned in mount()

  var VOICE_TOOL_NAME = 'consultar_portal_intelligence';

  // VOICE-UAT-02 -- the mint call (portal-realtime-homolog, Secure repo,
  // READ-ONLY this Wave) never requests input audio transcription: its
  // own sessionConfig.audio.input only ever sets `turn_detection` (see
  // that file's real source, read directly this Wave), never
  // `transcription`. Per OpenAI's own Realtime API docs (client-events
  // reference, session.update / session.audio.input.transcription),
  // transcription of the HUMAN's own speech is opt-in -- with it never
  // requested, `conversation.item.input_audio_transcription.completed`
  // (the only event this file listens to for the user's final turn,
  // see handleServerEvent below) never fires on a real session. The
  // assistant's own spoken turn is unaffected (it comes from the
  // model's own response.output, always present), which is exactly why
  // only assistant-sounding text was ever rendering for the Human --
  // not a duplication regression, not a render bug: the user turn was
  // never being captured at all. Fixed here, in the writable V2
  // frontend only (no Secure change, per this Wave's boundary), via a
  // session.update sent right after the data channel opens --
  // documented as mergeable at any time without resending voice/
  // turn_detection/instructions/tools (OpenAI's own docs: "Only the
  // fields that are present in the session.update are updated"). Model
  // choice: OpenAI's own realtime-transcription guide's stated starting
  // recommendation, never invented.
  var VOICE_TRANSCRIPTION_MODEL = 'gpt-live-transcribe';

  var pc = null;
  var dc = null;
  var micStream = null;
  var remoteAudioEl = null;
  var processedCallIds = Object.create(null);
  var latestCallId = null;
  var pendingUserTranscript = null;
  // VOICE-UAT-03 -- correlates a structured result (financing_card/
  // cash_conversion_card/settlement_card, already computed by the SAME
  // backend Text uses) to the SPECIFIC tool call it came from, so it
  // can be attached to that call's own eventual final assistant turn
  // (response.done's own !hadFunctionCall branch, below) without
  // reviving the duplicate-render bug VOICE-UAT-01B fixed: stashed only
  // when NOT stale at bridge-resolution time (same latestCallId check
  // handleFunctionCall's own caller already applies), and consumed only
  // if STILL not stale at the moment a final assistant turn actually
  // renders -- closes the gap a stash-time-only check would leave open
  // (call A resolves and stashes, then call B supersedes it before A's
  // own response.done fires; never "last card wins" globally).
  var pendingAssistantBlocksCallId = null;
  var pendingAssistantBlocks = null;
  var turnTimer = null;
  var active = false; // true only once the WebRTC data channel is open
  var startGeneration = 0; // incremented by doEnd() -- invalidates an in-flight doStart() chain (manual cancel while CONNECTING)
  var sessionId = null; // opaque per-session id, never an identity -- diagnostics/correlation only
  var sessionStartAt = null;

  /* ============================================================
     DIAGNOSTICS -- Human must NEVER need DevTools/console/terminal to
     retrieve this (Section 38). Two retrieval paths, both safe:
       A. window.NX_INTELLIGENCE_VOICE.diagnostics() -- a plain read,
          for an automated harness or Codex to call without asking a
          Human to do anything;
       B. a tiny, always-present DEV-ONLY toggle+panel (mirrors
          assets/js/design-trace.js's own #nxDesignTraceToggle/
          #nxDesignTrace convention exactly), so a Human CAN look at it
          visually without ever opening DevTools, though this Wave's
          own UAT script never asks them to.
     Bounded (Section 41): schema_version + a capped ring buffer of the
     last DIAG_MAX_EVENTS events, each a plain object of numbers/short
     strings only. Allowed fields only (Section 40) -- never audio,
     transcript, JWT, cookie, OpenAI key, ephemeral credential, email,
     user id, or any business payload. ============================ */

  var DIAG_KEY = 'baiVoiceDiagV2';
  var DIAG_SCHEMA_VERSION = 1;
  var DIAG_MAX_EVENTS = 20;
  var diagEvents = [];

  function diagPush(type, extra) {
    var entry = { t: Date.now(), type: String(type) };
    if (extra) {
      for (var k in extra) {
        if (!Object.prototype.hasOwnProperty.call(extra, k)) continue;
        var v = extra[k];
        // Defense in depth: only numbers/booleans/short strings ever
        // enter the ring buffer, regardless of what a future caller
        // passes -- this function is the one choke point every event
        // flows through.
        if (typeof v === 'number' || typeof v === 'boolean') entry[k] = v;
        else if (typeof v === 'string') entry[k] = v.slice(0, 120);
      }
    }
    diagEvents.push(entry);
    if (diagEvents.length > DIAG_MAX_EVENTS) diagEvents.shift();
    persistDiag();
    renderDiagPanel();
  }

  function persistDiag() {
    try {
      var snapshot = {
        schema_version: DIAG_SCHEMA_VERSION,
        updated_at: new Date().toISOString(),
        session_id: sessionId,
        state: S ? S.getVoiceState() : null,
        events: diagEvents
      };
      localStorage.setItem(DIAG_KEY, JSON.stringify(snapshot));
    } catch (e) { /* storage unavailable/full -- diagnostics are best-effort, never block the real session */ }
  }

  function readDiag() {
    try { return JSON.parse(localStorage.getItem(DIAG_KEY) || 'null'); } catch (e) { return null; }
  }

  function clearDiag() {
    diagEvents = [];
    try { localStorage.removeItem(DIAG_KEY); } catch (e) { /* ignore */ }
    renderDiagPanel();
  }

  var diagPanelBuilt = false;

  function buildDiagDom() {
    if (diagPanelBuilt) return;
    var root = document.getElementById('nxOverlayRoot');
    if (!root) return;
    var wrap = document.createElement('div');
    wrap.className = 'baiVoiceDiagRoot';
    wrap.innerHTML =
      '<button type="button" class="baiVoiceDiagToggle" id="baiVoiceDiagToggle" aria-expanded="false" aria-controls="baiVoiceDiagPanel">Voice Diag</button>' +
      '<aside class="baiVoiceDiagPanel" id="baiVoiceDiagPanel" hidden aria-label="Voice diagnostics (dev only)">' +
        '<div class="baiVoiceDiagHeader"><h2>Voice Diagnostics (dev only)</h2>' +
        '<button type="button" id="baiVoiceDiagClear">Limpar</button></div>' +
        '<pre id="baiVoiceDiagBody"></pre>' +
      '</aside>';
    root.appendChild(wrap);
    document.getElementById('baiVoiceDiagToggle').addEventListener('click', function () {
      var panel = document.getElementById('baiVoiceDiagPanel');
      var wasHidden = panel.hasAttribute('hidden');
      if (wasHidden) { panel.removeAttribute('hidden'); renderDiagPanel(); } else panel.setAttribute('hidden', '');
      document.getElementById('baiVoiceDiagToggle').setAttribute('aria-expanded', wasHidden ? 'true' : 'false');
    });
    document.getElementById('baiVoiceDiagClear').addEventListener('click', function () { clearDiag(); });
    diagPanelBuilt = true;
  }

  function renderDiagPanel() {
    var body = document.getElementById('baiVoiceDiagBody');
    if (!body) return;
    var snap = readDiag();
    body.textContent = snap ? JSON.stringify(snap, null, 2) : '(sem dados)';
  }

  /* ============================================================
     STATE MACHINE -- reuses NX_INTELLIGENCE_STATE's own VOICE_STATES
     enum (declared inert since IA-3E; this is the first Wave that
     transitions it). VOICE_IDLE/VOICE_DISCONNECTED both mean "not
     active" for this controller's own purposes (ready to start).
     ============================================================ */

  function setV(state) {
    if (S) S.setVoiceState(state);
    diagPush('state', { state: state });
  }

  function isInactiveState(st) {
    var VS = S.VOICE_STATES;
    return st === VS.VOICE_DISCONNECTED || st === VS.VOICE_IDLE || st === VS.VOICE_ERROR;
  }

  /* ============================================================
     GOVERNED TOOL BRIDGE (Section 19/20/21/22) -- the ONLY function in
     this file that touches Brabus Intelligence content. Calls the
     EXACT SAME A.sendRealText() Text's own handleSendRealText() calls,
     with a freshly-read access token and the real conversation history
     -- same endpoint, same auth context, same semantic scope, same
     error-message mapping. No business logic, no arithmetic, no
     duplicated transport.
     ============================================================ */

  function stripMarkdown(text) {
    return String(text || '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^[-•]\s+/gm, '')
      .replace(/\[([^\]]+)\]\(https?:\/\/[^\s)]+\)/g, '$1')
      .replace(/\n{2,}/g, '. ')
      .replace(/\n/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  function appendTurn(role, content, blocks) {
    if (!content) return;
    S.pushMessage({ role: role, content: content, blocks: blocks || null, isError: false });
  }

  // IA-3H.1A D1 fix -- found live by this Wave's own barge-in test: a
  // tool call superseded by a newer turn (latestCallId moved on) was
  // correctly never SPOKEN back to Realtime, but its assistant answer
  // was still being pushed onto the shared conversation store
  // unconditionally, a few lines before the caller's own staleness
  // check ever ran -- a real defect (a withdrawn/interrupted question
  // would still show its answer on screen, silently mismatched against
  // what was actually spoken). Fixed by accepting the tool's own callId
  // here and re-checking `callId === latestCallId` immediately before
  // the assistant push, the same guard handleFunctionCall's caller
  // already applies before speaking it -- one staleness check, applied
  // at both points it matters, not two independent implementations of
  // it. The user's own turn is NOT gated by this check: asking a
  // question is a real historical fact even if superseded before an
  // answer arrives, and hiding it would misrepresent what was actually
  // said (matches V1's own transcript-everything-spoken philosophy).
  //
  // VOICE-UAT-01B -- `opts.silent` (default false): ported behaviorally
  // from the same fix in V1's portal-ai-ui.js (baiSend's own `silent`
  // option), for the exact same real duplication forensic, confirmed
  // present here too by direct code reading: this function pushed a
  // user AND an assistant turn via S.pushMessage unconditionally, while
  // handleServerEvent's own response.done (!hadFunctionCall branch,
  // below) SEPARATELY pushes the Realtime model's own spoken
  // restatement of that same exchange via appendTurn -- same
  // S.pushMessage sink, two independent callers, one logical voice
  // turn. handleFunctionCall (the only caller for a tool-using turn)
  // now passes {silent:true} -- this function becomes pure "call
  // sendRealText, return {spoken, ok, stale}", no state-store side
  // effect. Text's own handleSend/applyResult (intelligence-panel.js)
  // never calls this function at all, so they are entirely unaffected.
  function bridgeToPortalIntelligence(message, callId, opts) {
    var silent = !!(opts && opts.silent);
    var t0 = Date.now();
    // Same ordering as intelligence-panel.js's own handleSend: push the
    // user's turn onto the SHARED conversation BEFORE sending, then
    // read prior turns excluding the one just pushed (createRequest
    // slices the last MAX_HISTORY itself -- this file never resends
    // more than Text already would for the same conversation length).
    // In silent mode, nothing is pushed here -- response.done's own
    // !hadFunctionCall branch is the single render path for this turn,
    // using the conversation as it already stood before this call, so
    // `prior` must read the FULL current conversation (never slice off
    // a turn that was never pushed).
    if (!silent) S.pushMessage({ role: 'user', content: message, blocks: null, isError: false });
    var prior = silent ? S.getConversation() : S.getConversation().slice(0, -1);
    // IA-3H.1C.3 -- same sanitized turn-sequence number Text's own
    // handleSendRealText computes (a plain count, never content), and
    // the SAME _devTiming hook (buildDevTiming, already proven for
    // Text) reused here rather than inventing a second timing shape --
    // this bridge previously only ever measured one end-to-end number
    // (the diagPush('tool_call',...) ms below), with no visibility into
    // which stage (client round trip vs. Edge-internal processing)
    // dominates a slow turn.
    var turnIndex = prior.filter(function (m) { return m.role === 'user'; }).length + 1;
    return window.NX_AUTH.getAccessToken().then(function (token) {
      // IA-3H.1C.4 -- declares this call as the trusted internal Voice
      // bridge (never a user-typed Text submission) via the literal
      // 'voice' string, becoming the x-nx-intelligence-surface header
      // the server's own surface-authority check reads. This is the
      // ONLY call site in this file that ever passes a 5th argument to
      // sendRealText -- D14's own load-bearing requirement (Section 12
      // of its brief): this bridge must keep working under Text=false/
      // Voice=true, which it does because it declares "voice", gated on
      // ia_voz_habilitada alone, never on the Text composer's own flag.
      return A.sendRealText(message, prior, token, { uiSubmitAt: t0, turnIndex: turnIndex }, 'voice');
    }).then(function (result) {
      diagPush('tool_call', { ms: Date.now() - t0, ok: !result.error, turn: turnIndex });
      if (result._devTiming) {
        // Same shape/prefix as intelligence-panel.js's own logDevTiming
        // -- numbers, a random correlation id, and an opaque Edge
        // instance id only, never prompt/reply content. Not extracted
        // into a shared helper across these two sibling files (neither
        // imports the other -- matches this codebase's existing
        // module-boundary convention), but intentionally the exact same
        // three lines/shape, not a new logging format.
        var out = {};
        for (var k in result._devTiming) out[k] = result._devTiming[k];
        var now = Date.now();
        if (result._devTiming.client_receive_at) out.render_ms = now - result._devTiming.client_receive_at;
        out.total_ui_ms = now - t0;
        // eslint-disable-next-line no-console
        console.log('[bai-timing]', out);
      }
      var stale = callId !== latestCallId;
      if (result.error) {
        if (!stale && !silent) S.pushMessage({ role: 'assistant', content: result.error.message, blocks: null, isError: true });
        return { spoken: result.error.message, ok: false, stale: stale, blocks: null };
      }
      var normalized = result.response;
      if (normalized.scenario_reset) S.spliceFromLastUser();
      // The ORIGINAL reply (with Markdown) is what renders on-screen,
      // via the SAME renderer Text uses -- only the value spoken back
      // to the Realtime session is stripped for natural TTS delivery
      // (mechanical text transform only, never a second model call,
      // never a changed fact). VOICE-UAT-01B -- gated on !silent too:
      // handleServerEvent's own response.done (!hadFunctionCall branch)
      // is the single render path for a tool-using voice turn, from the
      // real spoken transcript, once the post-tool response arrives.
      if (!stale && !silent) S.pushMessage({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
      // VOICE-UAT-03 -- `blocks` (financing_card/cash_conversion_card/
      // settlement_card, the EXACT same structured result Text's own
      // applyResult already attaches) is returned here even in silent
      // mode, so handleFunctionCall's own caller can correlate it to
      // this call's eventual final assistant turn -- this function
      // itself never pushes it in silent mode (no duplication risk
      // reintroduced; the silent/!stale gate above is unchanged).
      return { spoken: stripMarkdown(normalized.reply), ok: true, stale: stale, blocks: normalized.blocks || null };
    });
  }

  /* ============================================================
     REALTIME EVENT HANDLING -- ported behaviorally from V1's
     dc.onmessage handler (handleServerEvent/handleFunctionCall).
     ============================================================ */

  function sendEvent(obj) {
    if (dc && dc.readyState === 'open') dc.send(JSON.stringify(obj));
  }

  function handleFunctionCall(item) {
    var callId = item.call_id;
    if (!callId || processedCallIds[callId]) return; // never process the same call_id twice (Section 32)
    processedCallIds[callId] = true;
    latestCallId = callId; // any older in-flight call's result is discarded below once it resolves

    var args = {};
    try { args = JSON.parse(item.arguments || '{}'); } catch (e) { /* args stays {} */ }
    var message = typeof args.message === 'string' ? args.message.trim() : '';
    if (!message) {
      sendEvent({ type: 'conversation.item.create', item: { type: 'function_call_output', call_id: callId, output: JSON.stringify({ erro: 'Pergunta vazia.' }) } });
      sendEvent({ type: 'response.create' });
      return;
    }

    setV(S.VOICE_STATES.VOICE_THINKING);
    // VOICE-UAT-01B -- silent:true: this bridge call's result is
    // consumed ONLY as function_call_output data for the Realtime model
    // to speak -- handleServerEvent's own response.done handler (below)
    // is the single place this exchange gets pushed into the shared
    // conversation store, from the real spoken transcript.
    bridgeToPortalIntelligence(message, callId, { silent: true }).then(function (outcome) {
      // Interrupted/superseded by a newer turn while the bridge call
      // was in flight -- discard silently, never inject a stale answer
      // into a conversation that has already moved on (Section 32).
      if (callId !== latestCallId) return;
      // VOICE-UAT-03 -- stash this call's own structured result,
      // correlated by callId, for response.done's own !hadFunctionCall
      // branch to attach to THIS call's eventual final assistant turn.
      // Re-checked again at consumption time (not just here) against
      // whatever latestCallId is THEN -- this stash alone does not
      // guarantee the card survives to render; it only survives if
      // still the latest call when that later event actually arrives.
      pendingAssistantBlocksCallId = callId;
      pendingAssistantBlocks = outcome.blocks || null;
      var output = outcome.ok
        ? JSON.stringify({ resposta: outcome.spoken })
        : JSON.stringify({ erro: outcome.spoken || 'Não consegui consultar os dados do Portal agora.' });
      sendEvent({ type: 'conversation.item.create', item: { type: 'function_call_output', call_id: callId, output: output } });
      sendEvent({ type: 'response.create' });
    });
  }

  function extractAssistantTranscript(responseObj) {
    var out = responseObj && responseObj.output;
    if (!Array.isArray(out)) return '';
    var parts = [];
    out.forEach(function (item) {
      if (item.type === 'message' && item.role === 'assistant' && Array.isArray(item.content)) {
        item.content.forEach(function (c) {
          if (typeof c.transcript === 'string' && c.transcript) parts.push(c.transcript);
        });
      }
    });
    return parts.join(' ').trim();
  }

  function handleServerEvent(evt) {
    if (!evt || typeof evt.type !== 'string') return;
    var VS = S.VOICE_STATES;

    if (evt.type === 'session.created' || evt.type === 'session.updated') {
      if (S.getVoiceState() === VS.VOICE_CONNECTING) {
        setV(VS.VOICE_LISTENING);
        diagPush('connected', { connect_ms: Date.now() - sessionStartAt });
      }
      return;
    }
    if (evt.type === 'input_audio_buffer.speech_started') {
      setV(S.getVoiceState() === VS.VOICE_SPEAKING ? VS.VOICE_INTERRUPTED : VS.VOICE_LISTENING);
      return;
    }
    if (evt.type === 'input_audio_buffer.speech_stopped') {
      setV(VS.VOICE_THINKING);
      turnTimer = { speechStoppedAt: Date.now() };
      return;
    }
    if (evt.type.indexOf('input_audio_transcription') >= 0 && evt.type.indexOf('completed') >= 0) {
      var userText = typeof evt.transcript === 'string' ? evt.transcript.trim() : '';
      // VOICE-UAT-01B -- this used to also check `!evt._consumedByToolCall`,
      // a guard never actually assigned anywhere in this file (a dead
      // check, always true, ported as-is from V1's own pre-fix state).
      // The real fix is bridgeToPortalIntelligence's own `silent` option
      // above, which stops the tool-bridge call from pushing its own
      // turns at all -- this single real transcript is the only user-
      // turn render for every turn now (tool-using or social).
      if (userText) pendingUserTranscript = userText;
      return;
    }
    if (evt.type === 'response.created') {
      setV(VS.VOICE_THINKING);
      return;
    }
    if (evt.type === 'output_audio_buffer.started') {
      setV(VS.VOICE_SPEAKING);
      if (turnTimer && !turnTimer.firstAudioAt) {
        turnTimer.firstAudioAt = Date.now();
        diagPush('first_audio', { ms: turnTimer.firstAudioAt - turnTimer.speechStoppedAt });
      }
      return;
    }
    if (evt.type === 'response.done') {
      var resp = evt.response || {};
      var output = Array.isArray(resp.output) ? resp.output : [];
      var hadFunctionCall = false;
      output.forEach(function (item) {
        if (item.type === 'function_call' && item.name === VOICE_TOOL_NAME) {
          hadFunctionCall = true;
          handleFunctionCall(item);
        }
      });
      if (!hadFunctionCall) {
        // Social turn (no tool) -- both sides go through the SAME
        // shared conversation surface as a tool turn would.
        if (pendingUserTranscript) { appendTurn('user', pendingUserTranscript); pendingUserTranscript = null; }
        var assistantText = extractAssistantTranscript(resp);
        // VOICE-UAT-03 -- attach the structured result ONLY if it was
        // stashed for the call that is STILL latestCallId right now
        // (never merely "was latest when stashed") -- a barge-in that
        // superseded it in between means this response.done either
        // belongs to the NEWER call (whose own stash, if any, has a
        // matching callId) or is a stray/social turn with nothing to
        // attach. Cleared unconditionally either way: a card is never
        // allowed to leak into a later, unrelated turn.
        var blocksForThisTurn = (pendingAssistantBlocksCallId !== null && pendingAssistantBlocksCallId === latestCallId) ? pendingAssistantBlocks : null;
        pendingAssistantBlocksCallId = null;
        pendingAssistantBlocks = null;
        if (assistantText) appendTurn('assistant', assistantText, blocksForThisTurn);
        setV(VS.VOICE_LISTENING);
        diagPush('turn_done', { had_tool: false });
        turnTimer = null;
      } else {
        diagPush('turn_done', { had_tool: true });
      }
      return;
    }
    if (evt.type === 'error') {
      diagPush('server_error_event');
    }
  }

  /* ============================================================
     SESSION LIFECYCLE -- ported behaviorally from V1's baiRealtimeStart/
     endInternally. Same ephemeral-credential mint call (now via
     NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint instead of a
     hardcoded SUPABASE_URL), same WebRTC offer/answer against OpenAI's
     own /v1/realtime/calls using ONLY the short-lived mint value as
     Bearer -- the long-lived OPENAI_API_KEY never reaches this file or
     any browser code (it lives exclusively inside portal-realtime-
     homolog, server-side).
     ============================================================ */

  function doStart() {
    if (active) return;
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      diagPush('error', { error_class: 'auth_unavailable' });
      setV(S.VOICE_STATES.VOICE_ERROR);
      return;
    }
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (!cfg.voiceRealtimeEndpoint || !cfg.supabasePublishableKey) {
      diagPush('error', { error_class: 'config_missing' });
      setV(S.VOICE_STATES.VOICE_ERROR);
      return;
    }

    var myGeneration = ++startGeneration;
    function stillCurrent() { return myGeneration === startGeneration; }

    sessionId = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : (String(Date.now()) + '-' + Math.random().toString(16).slice(2));
    sessionStartAt = Date.now();
    diagEvents = [];
    diagPush('start', { session_id: sessionId });
    setV(S.VOICE_STATES.VOICE_CONNECTING);

    window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) throw new Error('no-session');
      return fetch(cfg.voiceRealtimeEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'apikey': cfg.supabasePublishableKey, 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({})
      });
    }).then(function (resp) {
      if (!resp.ok) throw new Error('mint-failed-' + resp.status);
      return resp.json();
    }).then(function (mint) {
      return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
        .then(function (stream) {
          diagPush('mic_ready', { ms: Date.now() - sessionStartAt });
          return { mint: mint, stream: stream };
        });
    }).then(function (pair) {
      if (!stillCurrent()) {
        // Manually cancelled while CONNECTING (Section 33/34) -- never
        // resurrect a session the Human already ended; release the mic
        // immediately, touch nothing else.
        pair.stream.getTracks().forEach(function (t) { t.stop(); });
        return;
      }
      micStream = pair.stream;
      pc = new RTCPeerConnection();

      remoteAudioEl = document.createElement('audio');
      remoteAudioEl.autoplay = true;
      // Attached to the document (off-screen, zero layout impact) --
      // a never-inserted <audio> element does not reliably fire
      // 'onplaying' in Chromium (V1's own live finding).
      remoteAudioEl.style.position = 'absolute';
      remoteAudioEl.style.width = '0';
      remoteAudioEl.style.height = '0';
      remoteAudioEl.style.opacity = '0';
      remoteAudioEl.style.pointerEvents = 'none';
      document.body.appendChild(remoteAudioEl);
      pc.ontrack = function (ev) { remoteAudioEl.srcObject = ev.streams[0]; };

      micStream.getTracks().forEach(function (track) {
        pc.addTrack(track, micStream);
        // Closes IA-3H's own D3 debt: a track that ends on its own
        // (device unplugged/revoked mid-session) must end the session
        // safely -- never silently, never via a retry loop.
        track.onended = function () {
          if (active) {
            diagPush('error', { error_class: 'device_lost' });
            endInternally(S.VOICE_STATES.VOICE_ERROR);
          }
        };
      });

      dc = pc.createDataChannel('oai-events');
      dc.onmessage = function (ev) {
        var parsed;
        try { parsed = JSON.parse(ev.data); } catch (e) { return; }
        try { handleServerEvent(parsed); } catch (e) { console.error('[intelligence-voice] erro ao processar evento', parsed && parsed.type, e); }
      };
      dc.onopen = function () {
        active = true;
        // VOICE-UAT-02 -- partial session.update: only `audio.input.
        // transcription` is present, so voice/turn_detection/
        // instructions/tools (all set server-side by the mint call)
        // are left exactly as they already are, per OpenAI's own
        // documented partial-merge contract for this event.
        sendEvent({ type: 'session.update', session: { type: 'realtime', audio: { input: { transcription: { model: VOICE_TRANSCRIPTION_MODEL } } } } });
        diagPush('transcription_requested', { model_len: VOICE_TRANSCRIPTION_MODEL.length });
      };
      dc.onclose = function () { if (active) endInternally(S.VOICE_STATES.VOICE_DISCONNECTED); };

      pc.onconnectionstatechange = function () {
        if (pc && (pc.connectionState === 'failed' || pc.connectionState === 'disconnected')) {
          // IA-3H's own D4 debt: a safe, bounded baseline -- the
          // session ends, the Human can manually start again. No
          // automatic reconnect loop of any kind.
          diagPush('error', { error_class: 'connection_' + pc.connectionState });
          endInternally(S.VOICE_STATES.VOICE_ERROR);
        }
      };

      return pc.createOffer().then(function (offer) {
        return pc.setLocalDescription(offer).then(function () {
          return fetch('https://api.openai.com/v1/realtime/calls', {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + pair.mint.value, 'Content-Type': 'application/sdp' },
            body: offer.sdp
          });
        });
      }).then(function (sdpResp) {
        if (!sdpResp.ok) throw new Error('sdp-failed-' + sdpResp.status);
        return sdpResp.text();
      }).then(function (answerSdp) {
        return pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      });
    }).catch(function (err) {
      if (!stillCurrent()) return;
      // err.message here is always one of a small set of internal
      // markers ('no-session', 'mint-failed-<status>', 'sdp-failed-
      // <status>') or a standard DOM exception name from getUserMedia
      // (e.g. NotAllowedError/NotFoundError) -- never request/response
      // content.
      diagPush('error', { error_class: String(err && err.message ? err.message : 'unknown_error').slice(0, 80) });
      endInternally(S.VOICE_STATES.VOICE_ERROR);
    });
  }

  function endInternally(finalState) {
    active = false;
    if (dc) { try { dc.close(); } catch (e) { /* ignore */ } dc = null; }
    if (pc) { try { pc.close(); } catch (e) { /* ignore */ } pc = null; }
    if (micStream) { micStream.getTracks().forEach(function (t) { t.onended = null; t.stop(); }); micStream = null; }
    if (remoteAudioEl) {
      try { remoteAudioEl.srcObject = null; } catch (e) { /* ignore */ }
      try { if (remoteAudioEl.parentNode) remoteAudioEl.parentNode.removeChild(remoteAudioEl); } catch (e) { /* ignore */ }
      remoteAudioEl = null;
    }
    processedCallIds = Object.create(null);
    latestCallId = null;
    pendingUserTranscript = null;
    pendingAssistantBlocksCallId = null;
    pendingAssistantBlocks = null;
    turnTimer = null;
    setV(finalState || S.VOICE_STATES.VOICE_DISCONNECTED);
    diagPush('ended', { end_reason: finalState || S.VOICE_STATES.VOICE_DISCONNECTED });
    // The conversation itself is never touched here -- same discipline
    // as Text's own closePanel(): ending the session is not a reset.
  }

  function doEnd() {
    startGeneration++; // invalidates any doStart() chain still in flight
    if (!active && !pc) {
      setV(S.VOICE_STATES.VOICE_DISCONNECTED);
      diagPush('ended', { end_reason: 'cancelled_while_connecting' });
      return;
    }
    endInternally(S.VOICE_STATES.VOICE_DISCONNECTED);
  }

  function toggle() {
    if (isInactiveState(S.getVoiceState())) doStart();
    else doEnd();
  }

  /* ============================================================
     MOUNT
     ============================================================ */

  // IA-3H.2.1C: the "Voice Diag" toggle/panel is a dev-only affordance
  // that must never appear in normal product UI (Human explicitly
  // rejected its permanent visibility) -- but this Wave must not
  // destroy the underlying diagnostics themselves (diagPush/persistDiag
  // keep recording to localStorage regardless, unconditionally, for
  // NX_INTELLIGENCE_VOICE.diagnostics()/.clearDiagnostics() and any
  // future harness to read). Gating on LOCAL_DEV alone would NOT hide
  // it during a normal localhost session (this Wave's own Human UAT is
  // itself on localhost) -- an explicit, deliberate opt-in query
  // parameter is the only signal that distinguishes "someone is
  // intentionally debugging Voice right now" from ordinary use.
  function diagUiRequested() {
    try {
      return typeof URLSearchParams !== 'undefined' &&
        new URLSearchParams(window.location.search).get('voiceDiag') === '1';
    } catch (e) { return false; }
  }

  function mount() {
    if (!window.NX_BRABUS_INTELLIGENCE_ADAPTER || !window.NX_INTELLIGENCE_STATE) {
      console.error('[intelligence-voice] a required dependency is missing -- not mounting');
      return;
    }
    A = window.NX_BRABUS_INTELLIGENCE_ADAPTER;
    S = window.NX_INTELLIGENCE_STATE;
    if (diagUiRequested()) buildDiagDom();
  }

  window.NX_INTELLIGENCE_VOICE = {
    VOICE_TOOL_NAME: VOICE_TOOL_NAME,
    mount: mount,
    start: function () { doStart(); },
    end: function () { doEnd(); },
    toggle: toggle,
    isActive: function () { return active; },
    diagnostics: readDiag,
    clearDiagnostics: clearDiag,
    // IA-3H.2 -- read-only references for intelligence-voice-focus.js's
    // own, entirely separate visualization layer (a second, independent
    // consumer of the SAME already-captured MediaStreams -- attaching a
    // Web Audio AnalyserNode to a stream does not remove it from this
    // file's own <audio> element playback or WebRTC track usage, and
    // this file never mutates either stream). Never a new capture,
    // never persisted, never sent anywhere -- see intelligence-voice-
    // focus.js's own privacy discipline. null whenever no session is
    // active, exactly mirroring isActive()'s own truthfulness.
    getRemoteAudioElement: function () { return remoteAudioEl; },
    getMicStream: function () { return micStream; }
  };
})();
