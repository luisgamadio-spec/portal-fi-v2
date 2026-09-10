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
   Voice presence was found anywhere IN THIS REPOSITORY (or the sibling
   locations checked at the time). IA-3H.2.1B later located the actual
   original source OUTSIDE this repo, in the non-git PORTAL-FI-DESIGN-
   LAB\facelift-prototype-01 directory (voice-orb.js), matching a
   recovered Human screenshot -- the Human's real selection from that
   old lab was "Fluid Aperture". The presence below is a faithful port
   of that ONE recovered algorithm (drawFluidAperture's exact
   deformation formula) onto the real, already-proven VOICE_STATES
   enum and the real remote/mic MediaStreams intelligence-voice.js
   already captures for the real session (never a second capture) --
   none of the OLD prototype's own runtime, LAB panel, demo
   conversation, or mic handling is reused, only the visual primitive.

   Privacy: no raw audio persisted, no waveform persisted, no
   transcript persisted beyond what intelligence-state.js's own
   conversation array already holds (unchanged, read-only here). The
   AnalyserNode reads are ephemeral, in-memory, per-frame numbers only,
   discarded immediately after driving one Canvas 2D redraw. */
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

  // ---------- Fluid Aperture presence (IA-3H.2.1B) ----------
  // Ported from the recovered facelift-prototype-01/voice-orb.js's
  // drawFluidAperture: a closed circular silhouette deformed by two
  // sine harmonics, plus a small inner "seam" arc accent -- the exact
  // formula the Human selected, now driven by the REAL amplitude/state
  // authority above instead of the old LAB's own demo/mic simulation.
  var orbCanvas = null, orbCtx = null, orbW = 0, orbH = 0;
  var orbColors = null;
  var interruptedAt = null; // brief-contraction transition marker (Section 23)

  // ---------- Ambient line field (Section 15) ----------
  // A minimal, self-contained re-implementation of the recovered
  // "parametric_reactive" ambient technique (design-motion-lab-03/
  // parametric-catalog.js#parametricReactive) -- 3 large, very thin,
  // very-low-opacity Lissajous ribbons. That old engine file itself is
  // NOT imported (no resurrected old runtime); only the technique is
  // reproduced natively, here, gated to Focus Mode's own visibility.
  var ambientCanvas = null, ambientCtx = null, ambientRafId = null, ambientW = 0, ambientH = 0;
  var AMBIENT_RIBBONS = [{ a: 3, b: 2, phase: 0 }, { a: 2, b: 5, phase: 1.4 }, { a: 5, b: 4, phase: 2.8 }];

  function orbRgba(hex, a) {
    hex = String(hex || '').trim();
    if (hex.charAt(0) !== '#' || hex.length < 7) return 'rgba(238,75,87,' + a + ')'; // accent-primary fallback
    var r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }

  // IA-3H.2.1C fix: the recovered original's drawFluidAperture uses TWO
  // distinct reds -- the deeper, more saturated --color-brand-red
  // (#c1121f) for the main contour, and the lighter --color-accent-
  // primary (#ee4b57) only for the smaller inner seam accent. The
  // IA-3H.2.1B port collapsed both onto accent-primary alone, which is
  // the real, evidenced root cause of the Human's "muted/desaturated"
  // feedback -- restoring the original's own two-red split, not an
  // arbitrary new value, is the fix (brief Section 14: "use the
  // strongest appropriate red already available").
  function ensureOrbColors() {
    if (orbColors) return orbColors;
    var css = getComputedStyle(document.documentElement);
    orbColors = {
      brand: (css.getPropertyValue('--color-brand-red').trim() || '#c1121f'),
      primary: (css.getPropertyValue('--color-accent-primary').trim() || '#ee4b57'),
      critical: (css.getPropertyValue('--color-critical').trim() || '#e2543a')
    };
    return orbColors;
  }

  // Current canonical VOICE_STATES -> {breathe, direction} -- same
  // shape/numbers as the recovered original's STATE_META, remapped
  // onto the real 8-state machine (never a duplicate state authority).
  function orbMetaForState(state) {
    var VS = S.VOICE_STATES;
    switch (state) {
      case VS.VOICE_CONNECTING: return { breathe: 0.4, direction: 0, gathering: true };
      case VS.VOICE_LISTENING: return { breathe: 0.3, direction: -1 };
      case VS.VOICE_THINKING: return { breathe: 0.5, direction: 0, traveling: true };
      case VS.VOICE_SPEAKING: return { breathe: 0.3, direction: 1 };
      case VS.VOICE_INTERRUPTED: return { breathe: 0.3, direction: -1, interrupted: true };
      case VS.VOICE_ERROR: return { breathe: 0.12, direction: 0, error: true };
      default: return { breathe: 0.15, direction: 0 }; // idle-shaped fallback; Focus Mode itself is hidden at IDLE
    }
  }

  // Returns true only when the backing bitmap was actually reallocated.
  // Setting canvas.width/height ALWAYS clears the bitmap per spec, even
  // when reassigned to the SAME value -- so a redundant call (e.g. the
  // ResizeObserver below firing its usual "initial observation" report
  // for a size that was already handled synchronously) must be a no-op,
  // or it silently wipes whatever was just drawn.
  function resizeOrbCanvas() {
    if (!orbCanvas) return false;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = orbCanvas.clientWidth, h = orbCanvas.clientHeight;
    if (w <= 0 || h <= 0) return false;
    if (w === orbW && h === orbH && orbCanvas.width === w * dpr) return false;
    orbW = w; orbH = h;
    orbCanvas.width = orbW * dpr; orbCanvas.height = orbH * dpr;
    orbCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return true;
  }

  function drawFluidAperture(t, state, amp) {
    if (!orbCtx || orbW <= 0 || orbH <= 0) return;
    var meta = orbMetaForState(state);
    var c = ensureOrbColors();
    var cx = orbW / 2, cy = orbH / 2, R = Math.min(orbW, orbH) * 0.42;
    var energy = amp;
    var breathe = Math.sin(t * 0.001) * 0.03 * meta.breathe;

    // Section 23: a brief, controlled contraction on entering
    // INTERRUPTED -- a phase break, not a violent glitch -- easing back
    // to the normal silhouette within ~260ms.
    var Rmod = R;
    if (meta.interrupted && interruptedAt !== null) {
      var age = t - interruptedAt;
      if (age >= 0 && age < 260) Rmod = R * (1 - 0.08 * (1 - age / 260));
    }

    orbCtx.clearRect(0, 0, orbW, orbH);
    orbCtx.beginPath();
    var pts = 48;
    for (var s = 0; s <= pts; s++) {
      var a = (s / pts) * Math.PI * 2;
      var deform = Math.sin(a * 3 + t * 0.0007) * 0.10 + Math.sin(a * 5 - t * 0.0005) * 0.05;
      var r = Rmod * (1 + breathe + deform * (0.4 + energy * 1.1) * (meta.direction >= 0 ? 1 : 0.6));
      if (meta.direction < 0) r = Rmod * (1 + breathe + deform * 0.35 - energy * 0.06);
      var x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * 0.94;
      if (s === 0) orbCtx.moveTo(x, y); else orbCtx.lineTo(x, y);
    }
    orbCtx.closePath();
    orbCtx.strokeStyle = orbRgba(meta.error ? c.critical : c.brand, 0.85);
    orbCtx.lineWidth = 1.7 + energy * 1.2;
    orbCtx.stroke();

    // Inner seam accent -- opens/closes with energy. THINKING lets it
    // slowly migrate around the aperture ("traveling phase", Section
    // 21); CONNECTING lets its span gently gather/release ("controlled
    // anticipation", Section 19 -- deliberately not a spinner).
    var seamCenter = Math.PI / 2;
    if (meta.traveling) seamCenter += Math.sin(t * 0.0003) * 0.6;
    var openAngle = 0.25 + energy * 0.5 * (meta.direction >= 0 ? 1 : 0.4);
    if (meta.gathering) openAngle *= 0.6 + Math.sin(t * 0.0015) * 0.15;
    orbCtx.beginPath();
    orbCtx.arc(cx, cy, Rmod * 0.55, seamCenter - openAngle, seamCenter + openAngle);
    orbCtx.strokeStyle = orbRgba(c.primary, meta.error ? 0.85 : 0.55);
    orbCtx.lineWidth = 1.2;
    orbCtx.stroke();
  }

  function resizeAmbientCanvas() {
    if (!ambientCanvas) return false;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = ambientCanvas.clientWidth, h = ambientCanvas.clientHeight;
    if (w <= 0 || h <= 0) return false;
    if (w === ambientW && h === ambientH && ambientCanvas.width === w * dpr) return false;
    ambientW = w; ambientH = h;
    ambientCanvas.width = ambientW * dpr; ambientCanvas.height = ambientH * dpr;
    ambientCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return true;
  }

  function drawAmbientFrame(t) {
    if (!ambientCtx || ambientW <= 0 || ambientH <= 0) return;
    var c = ensureOrbColors();
    ambientCtx.clearRect(0, 0, ambientW, ambientH);
    AMBIENT_RIBBONS.forEach(function (r, i) {
      var tt = t * 0.00007 + r.phase;
      ambientCtx.beginPath();
      var steps = 70;
      for (var s = 0; s <= steps; s++) {
        var u = (s / steps) * Math.PI * 2;
        var x = ambientW / 2 + Math.sin(r.a * u + tt) * ambientW * 0.42;
        var y = ambientH / 2 + Math.sin(r.b * u) * ambientH * 0.36;
        if (s === 0) ambientCtx.moveTo(x, y); else ambientCtx.lineTo(x, y);
      }
      // IA-3H.2.1C: opacity trimmed slightly (was 0.09/0.07/0.05) -- the
      // same values read visually stronger against the newly darkened
      // panel (Section 17: "re-evaluate ambient opacity" after the
      // panel/aperture contrast changes below), so this keeps the field
      // perceived "mostly subconsciously" rather than competing.
      ambientCtx.strokeStyle = orbRgba(c.primary, Math.max(0.015, 0.07 - i * 0.017));
      ambientCtx.lineWidth = 0.8;
      ambientCtx.stroke();
    });
  }

  function ambientLoop(ts) {
    drawAmbientFrame(ts);
    ambientRafId = requestAnimationFrame(ambientLoop);
  }

  function startAmbient() {
    if (!ambientCanvas || ambientRafId !== null) return;
    resizeAmbientCanvas();
    if (reduceMotionPreferred()) { drawAmbientFrame(0); return; } // one static frame, no loop
    ambientRafId = requestAnimationFrame(ambientLoop);
  }

  function stopAmbient() {
    if (ambientRafId !== null) { cancelAnimationFrame(ambientRafId); ambientRafId = null; }
    if (ambientCtx && ambientW > 0) ambientCtx.clearRect(0, 0, ambientW, ambientH);
  }

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
    if (orbCtx && orbW > 0) orbCtx.clearRect(0, 0, orbW, orbH);
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

  function animationLoop(ts) {
    var state = S.getVoiceState();
    var VS = S.VOICE_STATES;
    var t = ts || performance.now();
    if (reduceMotionPreferred()) { drawFluidAperture(t, state, 0); rafId = null; return; } // status text alone carries state (Section 27)
    var amp = 0;
    if (state === VS.VOICE_SPEAKING && remoteAnalyser) amp = readAmplitude(remoteAnalyser);
    else if ((state === VS.VOICE_LISTENING || state === VS.VOICE_INTERRUPTED) && micAnalyser) amp = readAmplitude(micAnalyser);
    drawFluidAperture(t, state, amp);
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
    if (lastRenderedVoiceState !== VS.VOICE_INTERRUPTED && state === VS.VOICE_INTERRUPTED) interruptedAt = performance.now();
    lastRenderedVoiceState = state;
    if (wasInactive && state === VS.VOICE_CONNECTING) visible = true;

    root.hidden = !visible;
    if (!visible) {
      teardownAudioGraph();
      stopAmbient();
      return;
    }

    resizeOrbCanvas(); // safe/no-op if the size is already current (see its own doc comment)
    startAmbient();

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
        '<canvas class="baiVoiceFocusAmbientCanvas" id="baiVoiceFocusAmbientCanvas" aria-hidden="true"></canvas>' +
        '<div class="baiVoiceFocusPanel" role="dialog" aria-modal="false" aria-label="Conversa por voz com a Brabus Intelligence">' +
          '<header class="baiVoiceFocusHeader">' +
            '<span class="baiVoiceFocusTitle">Brabus Intelligence</span>' +
            '<button type="button" class="baiVoiceFocusCloseBtn" id="baiVoiceFocusCloseBtn" aria-label="Encerrar conversa por voz">&times;</button>' +
          '</header>' +
          '<div class="baiVoiceFocusStage">' +
            '<div class="baiVoiceFocusPresence" id="baiVoiceFocusPresence" aria-hidden="true">' +
              '<canvas class="baiVoiceFocusOrbCanvas" id="baiVoiceFocusOrbCanvas"></canvas>' +
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

    orbCanvas = document.getElementById('baiVoiceFocusOrbCanvas');
    orbCtx = orbCanvas.getContext('2d');
    ambientCanvas = document.getElementById('baiVoiceFocusAmbientCanvas');
    ambientCtx = ambientCanvas.getContext('2d');
    if (typeof ResizeObserver !== 'undefined') {
      // A genuine size change (e.g. crossing a responsive breakpoint
      // while Focus Mode is open) reallocates the bitmap, which clears
      // it -- redraw once immediately so a reduced-motion session
      // (single static frame, no rAF loop to self-heal on the next
      // tick) never observes a blank orb after a resize.
      var ro = new ResizeObserver(function () {
        var orbResized = resizeOrbCanvas();
        var ambientResized = resizeAmbientCanvas();
        var focusRoot = document.getElementById('baiVoiceFocusRoot');
        if (!focusRoot || focusRoot.hidden || !S) return;
        if (orbResized) drawFluidAperture(performance.now(), S.getVoiceState(), 0);
        if (ambientResized) drawAmbientFrame(performance.now());
      });
      ro.observe(orbCanvas);
      ro.observe(ambientCanvas);
    }
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
