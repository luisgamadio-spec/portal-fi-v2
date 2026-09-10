/* PORTAL-NEXT V2 — Brabus Intelligence STATE (IA-3E).

   Single source of truth for the persistent Intelligence panel's
   conversation and explicit TEXT state machine, plus an inert
   VOICE-ready state enum (architecture only — no transition into any
   VOICE_* state happens anywhere in this codebase this Wave; Voice
   itself has not started, see docs/IA-3E-V2-INTELLIGENCE-PANEL.md).

   Lives in its own module-level closure (not a page controller's
   render() closure) specifically so state SURVIVES route navigation —
   this is the mechanism that makes conversation persistence (Section
   21/57 of the IA-3E brief) possible without a database/localStorage:
   this script tag runs exactly once per page load, same as any other
   shell-level singleton (auth-core.js, network-guard.js), and
   intelligence-panel.js mounts into #nxOverlayRoot once, never
   recreated by shell.js's per-route dispatchModule().

   This file owns ZERO business logic, ZERO network calls, ZERO DOM —
   pure state + pub/sub, mirroring auth-core.js's own architecture
   (Object.freeze'd snapshots so a caller cannot mutate state through a
   held reference — the same spoofing concern auth-core.js's own
   Gate 21 comment documents, applied here to conversation state). */
(function () {
  'use strict';

  // Explicit TEXT state machine (IA-3E Section 13/16). SENDING and
  // THINKING are both real, distinct states even though the current
  // (non-streaming) backend contract collapses them into one network
  // round trip in practice — SENDING covers the outgoing request being
  // built/dispatched, THINKING covers the wait for a response once the
  // request has left the browser. No STREAMING transition is ever
  // fired today (backend returns one JSON body, never token deltas) —
  // the state exists so a real future streaming contract would not
  // require inventing a new enum value, per Section 16's explicit "do
  // not fake token streaming" instruction.
  var TEXT_STATES = {
    CLOSED: 'CLOSED',
    OPEN_IDLE: 'OPEN_IDLE',
    COMPOSING: 'COMPOSING',
    SENDING: 'SENDING',
    THINKING: 'THINKING',
    STREAMING: 'STREAMING',
    COMPLETE: 'COMPLETE',
    ERROR: 'ERROR',
    DISABLED: 'DISABLED',
    SESSION_EXPIRED: 'SESSION_EXPIRED',
    FORBIDDEN: 'FORBIDDEN'
  };

  // Voice-ready state architecture (IA-3E Section 17, activated IA-3H.1).
  // Reserved so a future Voice wave could slot in without redesigning
  // this store — that Wave is this one; see setVoiceState() below and
  // assets/js/intelligence/intelligence-voice.js, its only caller.
  var VOICE_STATES = {
    VOICE_IDLE: 'VOICE_IDLE',
    VOICE_CONNECTING: 'VOICE_CONNECTING',
    VOICE_LISTENING: 'VOICE_LISTENING',
    VOICE_THINKING: 'VOICE_THINKING',
    VOICE_SPEAKING: 'VOICE_SPEAKING',
    VOICE_INTERRUPTED: 'VOICE_INTERRUPTED',
    VOICE_ERROR: 'VOICE_ERROR',
    VOICE_DISCONNECTED: 'VOICE_DISCONNECTED'
  };

  var textState = TEXT_STATES.CLOSED;
  var voiceState = VOICE_STATES.VOICE_DISCONNECTED; // never transitions this Wave
  var conversation = []; // [{role, content, blocks, isError}]
  var listeners = [];

  function freezeMsg(m) {
    return Object.freeze({
      role: m.role,
      content: m.content,
      blocks: m.blocks || null,
      isError: !!m.isError
    });
  }

  function snapshot() {
    return Object.freeze({
      textState: textState,
      voiceState: voiceState,
      conversation: Object.freeze(conversation.slice())
    });
  }

  function notify() {
    var snap = snapshot();
    listeners.forEach(function (fn) {
      try { fn(snap); } catch (e) { console.error('[intelligence-state] listener error', e); }
    });
  }

  window.NX_INTELLIGENCE_STATE = {
    TEXT_STATES: TEXT_STATES,
    VOICE_STATES: VOICE_STATES,

    getTextState: function () { return textState; },
    setTextState: function (next) {
      if (!TEXT_STATES.hasOwnProperty(next)) {
        throw new Error('[intelligence-state] unknown TEXT state: ' + next);
      }
      textState = next;
      notify();
    },

    // IA-3H.1 -- the enum itself (VOICE_STATES, above) already existed
    // as inert architecture since IA-3E; this is the first Wave that
    // actually transitions it, via intelligence-voice.js's own session
    // manager. Same validate/assign/notify shape as setTextState — one
    // explicit state machine, not ad hoc booleans (Section 10).
    getVoiceState: function () { return voiceState; },
    setVoiceState: function (next) {
      if (!VOICE_STATES.hasOwnProperty(next)) {
        throw new Error('[intelligence-state] unknown VOICE state: ' + next);
      }
      voiceState = next;
      notify();
    },

    getConversation: function () { return conversation.slice(); },
    pushMessage: function (msg) {
      conversation.push(freezeMsg(msg));
      notify();
    },
    resetConversation: function () {
      conversation = [];
      notify();
    },
    // Mirrors the routed page's own scenario_reset handling exactly
    // (brabus-intelligence.js's applyResult) — prune back to the
    // triggering user turn. Never invents new reset semantics.
    spliceFromLastUser: function () {
      var lastUserIdx = -1;
      for (var i = conversation.length - 1; i >= 0; i--) {
        if (conversation[i].role === 'user') { lastUserIdx = i; break; }
      }
      if (lastUserIdx > 0) conversation = conversation.slice(lastUserIdx);
    },

    onChange: function (fn) { listeners.push(fn); },
    getSnapshot: snapshot
  };
})();
