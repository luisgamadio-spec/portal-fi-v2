/* PORTAL-NEXT V2 — Brabus Intelligence VOICE FOCUS MODE (IA-3H.2).

   ONE INTELLIGENCE CORE, TWO SURFACES -- this file owns ONLY the Voice
   conversational PRESENTATION layer (a dedicated, deliberate visual
   surface while a Voice session is active). It never touches business
   logic, the governed tool bridge, the WebRTC session lifecycle, or the
   shared conversation store's own content -- all of that already lives
   in intelligence-voice.js (session manager) and intelligence-state.js
   (the single shared conversation/state store both Text and Voice
   render from). This file is a second SUBSCRIBER to that same existing
   state (NX_INTELLIGENCE_STATE.onChange), exactly like intelligence-
   panel.js's own updateVoiceButton() -- never a second conversation
   store, never a second WebRTC session, never a second governed bridge.

   Forensic note (IA-3H.2 Section 5): no prior animated/audio-reactive
   Voice presence was found anywhere in this codebase or its known
   sibling locations (see this Wave's own report) -- the LAB-only
   portal-ai-voice-studio.js has real WebRTC audio but only ever shows
   plain status TEXT, never any animation. Everything in this file is
   new, built directly against the real, already-proven VOICE_STATES
   enum and the real remote/mic MediaStreams intelligence-voice.js
   already captures for the real session (never a second capture).

   Privacy: no raw audio persisted, no waveform persisted, no
   transcript persisted beyond what intelligence-state.js's own
   conversation array already holds (unchanged, read-only here). The
   AnalyserNode reads are ephemeral, in-memory, per-frame numbers only,
   discarded immediately after driving one CSS custom property. */
(function () {
  'use strict';

  var S, V; // intelligence-state, intelligence-voice -- assigned in mount()
  var built = false;
  var dismissed = false; // "Voltar ao texto" -- hides Focus Mode without ending the session
  var lastRenderedVoiceState = null;

  // ---------- Audio-reactive presence (Section 11/12) ----------
  // Exactly one AudioContext + up to two AnalyserNodes (remote/mic) for
  // the lifetime of one Voice session -- created lazily on first real
  // need, torn down deterministically on every inactive transition
  // (Section 41: "no duplicate analyser on restart, no leak after end").
  var audioCtx = null;
  var remoteAnalyser = null;
  var micAnalyser = null;
  var remoteSourceNode = null;
  var micSourceNode = null;
  var rafId = null;
  var ampBuf = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function teardownAudioGraph() {
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    try { if (remoteSourceNode) remoteSourceNode.disconnect(); } catch (e) { /* ignore */ }
    try { if (micSourceNode) micSourceNode.disconnect(); } catch (e) { /* ignore */ }
    remoteSourceNode = null; micSourceNode = null;
    remoteAnalyser = null; micAnalyser = null;
    if (audioCtx) { try { audioCtx.close(); } catch (e) { /* ignore */ } audioCtx = null; }
    ampBuf = null;
    setAmplitude(0);
  }

  function ensureAudioGraph() {
    if (audioCtx) return true;
    if (typeof AudioContext === 'undefined' && typeof window.webkitAudioContext === 'undefined') return false;
    var AC = window.AudioContext || window.webkitAudioContext;
    try {
      audioCtx = new AC();
    } catch (e) {
      audioCtx = null;
      return false;
    }
    return true;
  }

  // Lazily attaches an AnalyserNode to the given MediaStream -- a
  // SEPARATE, independent consumer of the SAME stream intelligence-
  // voice.js already captured for the real session; never a new
  // getUserMedia() call, never a second WebRTC track, and this never
  // affects the <audio> element's own native playback (srcObject
  // playback and a Web Audio graph node are independent consumers of
  // the same MediaStream).
  function attachAnalyser(stream) {
    if (!stream || !ensureAudioGraph()) return null;
    try {
      var source = audioCtx.createMediaStreamSource(stream);
      var analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.6;
      source.connect(analyser);
      return { source: source, analyser: analyser };
    } catch (e) {
      return null;
    }
  }

  function setAmplitude(v) {
    var stage = document.getElementById('baiVoiceFocusPresence');
    if (stage) stage.style.setProperty('--bai-focus-amp', String(Math.max(0, Math.min(1, v))));
  }

  function readAmplitude(analyser) {
    if (!analyser) return 0;
    if (!ampBuf || ampBuf.length !== analyser.frequencyBinCount) ampBuf = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(ampBuf);
    var sum = 0;
    for (var i = 0; i < ampBuf.length; i++) sum += ampBuf[i];
    var avg = sum / (ampBuf.length * 255); // 0..1
    return avg;
  }

  function reduceMotionPreferred() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function animationLoop() {
    var state = S.getVoiceState();
    var VS = S.VOICE_STATES;
    if (reduceMotionPreferred()) { setAmplitude(0); rafId = null; return; } // status text alone carries state (Section 27)
    var amp = 0;
    if (state === VS.VOICE_SPEAKING && remoteAnalyser) amp = readAmplitude(remoteAnalyser);
    else if ((state === VS.VOICE_LISTENING || state === VS.VOICE_INTERRUPTED) && micAnalyser) amp = readAmplitude(micAnalyser);
    setAmplitude(amp);
    rafId = requestAnimationFrame(animationLoop);
  }

  function ensureAnalysersForState(state) {
    var VS = S.VOICE_STATES;
    if (state === VS.VOICE_SPEAKING && !remoteAnalyser) {
      var remoteEl = V.getRemoteAudioElement && V.getRemoteAudioElement();
      var remoteStream = remoteEl && remoteEl.srcObject;
      var r = attachAnalyser(remoteStream);
      if (r) { remoteSourceNode = r.source; remoteAnalyser = r.analyser; }
    }
    if ((state === VS.VOICE_LISTENING || state === VS.VOICE_INTERRUPTED) && !micAnalyser) {
      var micStream = V.getMicStream && V.getMicStream();
      var m = attachAnalyser(micStream);
      if (m) { micSourceNode = m.source; micAnalyser = m.analyser; }
    }
    if (rafId === null) rafId = requestAnimationFrame(animationLoop);
  }

  // ---------- Status / visual state (Section 9/10) ----------
  var STATUS_BY_STATE = {
    VOICE_CONNECTING: 'Conectando…',
    VOICE_LISTENING: 'Ouvindo',
    VOICE_THINKING: 'Pensando…',
    VOICE_SPEAKING: 'Falando',
    // Interruption transitions immediately back to a listening-shaped
    // visual (Section 15: "no frozen animation, no stale Falando") --
    // the real state machine itself already moves on to LISTENING/
    // THINKING right after per intelligence-voice.js's own handling;
    // this is only the one-frame label for VOICE_INTERRUPTED itself.
    VOICE_INTERRUPTED: 'Ouvindo',
    VOICE_ERROR: 'Erro — tentar de novo'
  };

  function stateSuffix(state) {
    return state ? state.replace('VOICE_', '') : 'IDLE';
  }

  function isFocusVisibleState(state) {
    var VS = S.VOICE_STATES;
    return state !== VS.VOICE_DISCONNECTED && state !== VS.VOICE_IDLE;
  }

  function render() {
    var root = document.getElementById('baiVoiceFocusRoot');
    if (!root || !S) return;
    var state = S.getVoiceState();
    var VS = S.VOICE_STATES;
    var visible = isFocusVisibleState(state) && !dismissed;

    // A fresh session start (transition FROM an inactive state INTO
    // CONNECTING) clears a prior "Voltar ao texto" dismissal -- the
    // Human explicitly starting a new conversation should see it again.
    var wasInactive = lastRenderedVoiceState === null || lastRenderedVoiceState === VS.VOICE_DISCONNECTED || lastRenderedVoiceState === VS.VOICE_IDLE;
    if (wasInactive && state === VS.VOICE_CONNECTING) dismissed = false;
    lastRenderedVoiceState = state;
    if (wasInactive && state === VS.VOICE_CONNECTING) visible = true;

    root.hidden = !visible;
    if (!visible) {
      teardownAudioGraph();
      return;
    }

    var presence = document.getElementById('baiVoiceFocusPresence');
    var statusEl = document.getElementById('baiVoiceFocusStatus');
    if (presence) presence.className = 'baiVoiceFocusPresence baiVoiceFocusState' + stateSuffix(state);
    if (statusEl) statusEl.textContent = STATUS_BY_STATE[state] || 'Conectando…';

    renderTranscriptPreview();
    ensureAnalysersForState(state);
    if (state === VS.VOICE_ERROR || state === VS.VOICE_DISCONNECTED) teardownAudioGraph();
  }

  // Latest human/assistant utterance only (Section 18: "avoid becoming a
  // scrolling text chat" -- full history stays in the drawer/Text
  // surface, unchanged, this only previews the newest exchange).
  function renderTranscriptPreview() {
    var el = document.getElementById('baiVoiceFocusTranscript');
    if (!el || !S) return;
    var conv = S.getConversation();
    var last = conv.length ? conv[conv.length - 1] : null;
    if (!last) { el.innerHTML = ''; return; }
    var roleLabel = last.role === 'user' ? 'Você' : 'Brabus Intelligence';
    el.innerHTML = '<span class="baiVoiceFocusTranscriptRole">' + esc(roleLabel) + '</span>' +
      '<span class="baiVoiceFocusTranscriptText">' + esc(last.content || '') + '</span>';
  }

  function onTextBtn() {
    dismissed = true;
    render();
  }

  function onEndBtn() {
    if (V) V.end();
  }

  function buildDom() {
    if (built) return;
    var root = document.getElementById('nxOverlayRoot');
    if (!root) return;
    var wrap = document.createElement('div');
    wrap.className = 'baiVoiceFocusRoot';
    wrap.id = 'baiVoiceFocusRoot';
    wrap.hidden = true;
    wrap.innerHTML =
      '<div class="baiVoiceFocusOverlay" id="baiVoiceFocusOverlay">' +
        '<div class="baiVoiceFocusPanel" role="dialog" aria-modal="false" aria-label="Conversa por voz com a Brabus Intelligence">' +
          '<header class="baiVoiceFocusHeader">' +
            '<span class="baiVoiceFocusTitle">Brabus Intelligence</span>' +
            '<button type="button" class="baiVoiceFocusCloseBtn" id="baiVoiceFocusCloseBtn" aria-label="Encerrar conversa por voz">&times;</button>' +
          '</header>' +
          '<div class="baiVoiceFocusStage">' +
            '<div class="baiVoiceFocusPresence" id="baiVoiceFocusPresence" aria-hidden="true">' +
              '<span class="baiVoiceFocusPresenceRing"></span>' +
              '<span class="baiVoiceFocusPresenceCore"></span>' +
            '</div>' +
            '<p class="baiVoiceFocusStatus" id="baiVoiceFocusStatus" role="status" aria-live="polite">Conectando…</p>' +
          '</div>' +
          '<div class="baiVoiceFocusTranscript" id="baiVoiceFocusTranscript"></div>' +
          '<div class="baiVoiceFocusControls">' +
            '<button type="button" class="baiVoiceFocusTextBtn" id="baiVoiceFocusTextBtn">Voltar ao texto</button>' +
            '<button type="button" class="baiVoiceFocusEndBtn" id="baiVoiceFocusEndBtn">Encerrar</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    root.appendChild(wrap);
    document.getElementById('baiVoiceFocusCloseBtn').addEventListener('click', onEndBtn);
    document.getElementById('baiVoiceFocusEndBtn').addEventListener('click', onEndBtn);
    document.getElementById('baiVoiceFocusTextBtn').addEventListener('click', onTextBtn);
    built = true;
  }

  function mount() {
    if (!window.NX_INTELLIGENCE_STATE || !window.NX_INTELLIGENCE_VOICE) {
      console.error('[intelligence-voice-focus] a required dependency is missing -- not mounting');
      return;
    }
    S = window.NX_INTELLIGENCE_STATE;
    V = window.NX_INTELLIGENCE_VOICE;
    buildDom();
    S.onChange(function () { render(); });
  }

  window.NX_INTELLIGENCE_VOICE_FOCUS = {
    mount: mount,
    // exposed for tests, DOM-independent state helpers
    isVisibleForState: isFocusVisibleState,
    statusForState: function (state) { return STATUS_BY_STATE[state] || 'Conectando…'; }
  };
})();
