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
  var conversation = []; // [{role, content, blocks, isError, provenance}]
  var listeners = [];

  // SESSIONSEC1 -- conversation OWNERSHIP. Every message above is only
  // ever meaningful in the context of the authenticated identity that
  // produced/received it. ownerAuthUserId is the stable auth user UUID
  // (auth-core.js's own Auth Context.authUserId, never profile/store/
  // department, never something a client module can set directly --
  // the only writer is clearForOwnerChange below, driven exclusively by
  // the canonical NX_AUTH_CORE event stream at the bottom of this
  // file). generation is bumped on every ownership change so an
  // in-flight async caller (a Text fetch, a Voice tool-call round trip)
  // can detect "the identity changed while I was waiting" and discard
  // its own late result instead of rendering/submitting it under the
  // wrong owner (Section 14 race protection).
  var ownerAuthUserId = null;
  var generation = 0;
  var ownerListeners = [];

  function freezeMsg(m) {
    return Object.freeze({
      role: m.role,
      content: m.content,
      blocks: m.blocks || null,
      isError: !!m.isError,
      // IA-MEGAUAT-WAVEB-RC1 -- system-issued provenance for an
      // assistant message ({source, tool} or null), carried alongside
      // content/blocks so a scenario_reset splice (spliceFromLastUser)
      // removes it together with the rest of that turn, same as every
      // other field here -- no separate array to keep in sync.
      provenance: m.provenance || null
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

  function notifyOwnerChange() {
    ownerListeners.forEach(function (fn) {
      try { fn(ownerAuthUserId, generation); } catch (e) { console.error('[intelligence-state] owner listener error', e); }
    });
  }

  // SESSIONSEC1 -- the ONE place conversation state is ever wiped for
  // an identity transition. FAIL CLOSED: called with a DIFFERENT key
  // than the current owner (including null, e.g. logout) always starts
  // a fresh conversation -- never migrates, never sanitizes-and-
  // continues the previous owner's messages (Section 8). Same-user
  // re-resolution (key unchanged) is a no-op here, preserving the
  // pre-existing route-navigation persistence this file's own header
  // comment documents -- this is not a general session-persistence
  // feature, it is the narrower "don't invent a new reset for an
  // identity that didn't actually change" case.
  function clearForOwnerChange(key) {
    if (key === ownerAuthUserId) return;
    ownerAuthUserId = key;
    generation++;
    conversation = [];
    textState = TEXT_STATES.CLOSED;
    notify();
    notifyOwnerChange();
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
    getSnapshot: snapshot,

    // SESSIONSEC1 -- ownership/race-protection API. getGeneration() is
    // meant to be captured by a caller BEFORE starting async work (a
    // Text send, a Voice tool call) and re-checked when that work
    // resolves; a mismatch means the authenticated identity changed in
    // between and the result must be silently dropped, never rendered
    // or submitted. onOwnerChange fires ONLY on a genuine identity
    // transition (never on every conversation mutation, unlike
    // onChange above) -- intelligence-voice.js's own session manager is
    // the first consumer, using it to hard-terminate a live
    // RTCPeerConnection/DataChannel/microphone the instant the
    // authenticated identity changes (Section 13).
    getOwnerAuthUserId: function () { return ownerAuthUserId; },
    getGeneration: function () { return generation; },
    onOwnerChange: function (fn) { ownerListeners.push(fn); }
  };

  // SESSIONSEC1 -- the SOLE source of the "current identity" signal:
  // NX_AUTH_CORE's own canonical state machine (auth-core.js), never a
  // second, parallel identity read. AUTHORIZED+context resolves to the
  // real auth user UUID (never profile/store/department -- Section 7's
  // explicit "must not be keyed only by profile" requirement); every
  // other state (SIGNED_OUT, SESSION_EXPIRED, mid-resolution, etc.)
  // resolves to null, i.e. "no owner" -- fail closed, matching Section
  // 8. AUTH_NOT_CONFIGURED (no real Supabase credentials on this host,
  // e.g. some local/dev contexts) gets its own stable sentinel key
  // rather than null so it does not repeatedly "change identity" back
  // and forth against a real SIGNED_OUT elsewhere in the same run.
  //
  // Registered directly at parse time (not deferred to DOMContentLoaded
  // like auth-core.js's own Supabase wiring) -- index.html loads
  // auth-core.js before this file, so window.NX_AUTH_CORE already
  // exists here; the `if` guard below only protects a standalone/test
  // harness that loads this file without auth-core.js at all.
  var lastOwnerKey; // intentionally undefined -- differs from any real key or null, so the first real transition always evaluates
  function identityKeyFor(state, context) {
    var STATES = window.NX_AUTH_CORE.STATES;
    if (state === STATES.AUTHORIZED && context) return context.authUserId;
    if (state === STATES.AUTH_NOT_CONFIGURED) return '__AUTH_NOT_CONFIGURED__';
    return null;
  }
  if (window.NX_AUTH_CORE && typeof window.NX_AUTH_CORE.onStateChange === 'function') {
    window.NX_AUTH_CORE.onStateChange(function (state, context) {
      var key = identityKeyFor(state, context);
      if (key !== lastOwnerKey) {
        lastOwnerKey = key;
        clearForOwnerChange(key);
      }
    });
  }
})();
