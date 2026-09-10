#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3H.1 -- Brabus Intelligence VOICE lifecycle test.

Covers assets/js/intelligence/intelligence-voice.js's own session
lifecycle properties: microphone permission (granted/denied/no device),
device loss mid-session (closes IA-3H's own D3 debt), connection
failure (IA-3H's own D4 debt -- safe bounded baseline, no auto-
reconnect loop), manual end while CONNECTING (cancel before any
resource exists), cleanup (mic released, audio element removed, no
leak), and restart (start -> end -> start again, repeatedly).

Same fake RTCPeerConnection/getUserMedia/fetch approach as
intelligence-voice-foundation-test.py -- see that file's own header for
why (replace the real browser primitive, never invent a test-only seam
in the production file).

Requires: `python -m http.server <port>` running from this worktree's
own root, with assets/js/intelligence-runtime-config.local.js ABSENT
for this run (see IA-3H.1's own report for why).
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


INIT_SCRIPT = """
(function () {
  window.__fetchCalls = [];
  window.__dcSent = [];
  window.__fakeGetUserMediaMode = 'ok';
  window.__audioElCreated = 0;
  window.__audioElRemoved = 0;

  function FakePC() {
    this.connectionState = 'new';
    this.ontrack = null;
    this.onconnectionstatechange = null;
    this._closed = false;
    window.__lastPc = this;
  }
  FakePC.prototype.addTrack = function () {};
  FakePC.prototype.createDataChannel = function () {
    var dc = { readyState: 'connecting', onopen: null, onmessage: null, onclose: null, send: function (s) { window.__dcSent.push(JSON.parse(s)); } };
    window.__lastDc = dc;
    setTimeout(function () { if (!dc._closedEarly) { dc.readyState = 'open'; if (dc.onopen) dc.onopen(); } }, 0);
    return dc;
  };
  FakePC.prototype.createOffer = function () { return Promise.resolve({ type: 'offer', sdp: 'fake-offer-sdp' }); };
  FakePC.prototype.setLocalDescription = function () { return Promise.resolve(); };
  FakePC.prototype.setRemoteDescription = function () { return Promise.resolve(); };
  FakePC.prototype.close = function () { this.connectionState = 'closed'; this._closed = true; };
  window.RTCPeerConnection = FakePC;

  navigator.mediaDevices = navigator.mediaDevices || {};
  navigator.mediaDevices.getUserMedia = function () {
    window.__getUserMediaCallCount = (window.__getUserMediaCallCount || 0) + 1;
    if (window.__fakeGetUserMediaMode === 'deny') {
      var e = new Error('Permission denied'); e.name = 'NotAllowedError'; return Promise.reject(e);
    }
    if (window.__fakeGetUserMediaMode === 'nodevice') {
      var e2 = new Error('Requested device not found'); e2.name = 'NotFoundError'; return Promise.reject(e2);
    }
    var track = { kind: 'audio', enabled: true, onended: null, _stopped: false, stop: function () { this._stopped = true; } };
    window.__lastFakeTrack = track;
    window.__allFakeTracks = window.__allFakeTracks || [];
    window.__allFakeTracks.push(track);
    return Promise.resolve({ getTracks: function () { return [track]; } });
  };

  var origFetch = window.fetch;
  window.fetch = function (url, opts) {
    window.__fetchCalls.push({ url: String(url) });
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (cfg.voiceRealtimeEndpoint && String(url).indexOf(cfg.voiceRealtimeEndpoint) !== -1) {
      if (window.__fakeMintMode === 'fail') return Promise.resolve({ ok: false, status: 503, json: function () { return Promise.resolve({}); } });
      return Promise.resolve({ ok: true, json: function () { return Promise.resolve({ value: 'fake-ephemeral-xyz', expires_at: Math.floor(Date.now() / 1000) + 600, model: 'gpt-realtime-2.1', applied: {} }); } });
    }
    if (String(url).indexOf('api.openai.com/v1/realtime/calls') !== -1) {
      return Promise.resolve({ ok: true, text: function () { return Promise.resolve('fake-answer-sdp'); } });
    }
    return origFetch(url, opts);
  };

  // Tracks every <audio> element intelligence-voice.js creates/removes,
  // via a MutationObserver on <body> -- proves cleanup without coupling
  // to intelligence-voice.js's own internal variable names. An init
  // script runs before <body> exists, so the observer is attached once
  // DOMContentLoaded fires, same as any real page script would.
  document.addEventListener('DOMContentLoaded', function () {
    new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (n) { if (n.tagName === 'AUDIO') window.__audioElCreated++; });
        m.removedNodes.forEach(function (n) { if (n.tagName === 'AUDIO') window.__audioElRemoved++; });
      });
    }).observe(document.body, { childList: true });
  });

  window.__simulateRtEvent = function (evt) {
    if (window.__lastDc && window.__lastDc.onmessage) window.__lastDc.onmessage({ data: JSON.stringify(evt) });
  };
})();
"""


def set_profile(page, state, is_master=None, perfil=None):
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def configure_voice(page, endpoint="http://fake-voice-endpoint.local/"):
    page.evaluate(
        """(endpoint) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint = endpoint;
            window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey || 'fake-anon-key';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-access-token') };
        }""",
        endpoint,
    )


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


def voice_state(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script(INIT_SCRIPT)
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(500)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        configure_voice(page)
        open_panel(page)

        # ---------- Microphone permission: denied ----------
        page.evaluate("window.__fakeGetUserMediaMode = 'deny';")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(200)
        check("mic permission denied -> VOICE_ERROR (clean failure, no crash)", voice_state(page) == "VOICE_ERROR")
        diag = page.evaluate("window.NX_INTELLIGENCE_VOICE.diagnostics()")
        check("denied permission recorded in diagnostics as a short error class, never raw DOM exception object", diag and any(e.get("error_class") for e in diag.get("events", []) if e.get("type") == "error"), diag)

        # ---------- One Human action -> one permission attempt (no auto-repeat) ----------
        calls_before = page.evaluate("window.__getUserMediaCallCount")
        page.wait_for_timeout(300)
        check("no automatic repeated getUserMedia prompt after a denial", page.evaluate("window.__getUserMediaCallCount") == calls_before)

        # ---------- Microphone permission: no device ----------
        page.evaluate("window.__fakeGetUserMediaMode = 'nodevice';")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(200)
        check("no device found -> VOICE_ERROR (clean failure, no crash)", voice_state(page) == "VOICE_ERROR")

        # ---------- Manual cancel while CONNECTING (before any resource exists) ----------
        page.evaluate("window.__fakeGetUserMediaMode = 'ok';")
        page.evaluate("""() => {
            // A mint that never resolves within this test's window --
            // simulates the CONNECTING gap between click and any real
            // resource (mic/pc) existing yet.
            var origFetch = window.fetch;
            window.fetch = function (url, opts) {
                if (String(url).indexOf('fake-voice-endpoint') !== -1) return new Promise(function(){ /* never resolves */ });
                return origFetch(url, opts);
            };
        }""")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(80)
        check("state is CONNECTING before the mint resolves", voice_state(page) == "VOICE_CONNECTING")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
        page.wait_for_timeout(80)
        check("manual end while CONNECTING resolves to VOICE_DISCONNECTED, not stuck", voice_state(page) == "VOICE_DISCONNECTED")
        page.reload()
        page.wait_for_timeout(500)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        configure_voice(page)
        open_panel(page)

        # ---------- Full start -> cleanup proof ----------
        audio_created_before = page.evaluate("window.__audioElCreated")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(200)
        page.evaluate("window.__simulateRtEvent({type:'session.created'});")
        page.wait_for_timeout(80)
        check("session reaches LISTENING with a real (faked) WebRTC handshake", voice_state(page) == "VOICE_LISTENING")
        check("exactly one <audio> element created for this session", page.evaluate("window.__audioElCreated") - audio_created_before == 1)
        check("mic track is enabled (not muted) once connected", page.evaluate("window.__lastFakeTrack.enabled") is True)

        audio_removed_before = page.evaluate("window.__audioElRemoved")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
        page.wait_for_timeout(80)
        check("manual end -> VOICE_DISCONNECTED", voice_state(page) == "VOICE_DISCONNECTED")
        check("mic track stopped on end (device released)", page.evaluate("window.__lastFakeTrack._stopped") is True)
        check("the <audio> element is removed from the DOM on end (no orphan)", page.evaluate("window.__audioElRemoved") - audio_removed_before == 1)
        check("no audio element left in the document after end", page.evaluate("document.querySelectorAll('audio').length") == 0)

        # ---------- Device loss mid-session (closes IA-3H debt D3) ----------
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(200)
        page.evaluate("window.__simulateRtEvent({type:'session.created'});")
        page.wait_for_timeout(80)
        check("session LISTENING before simulated device loss", voice_state(page) == "VOICE_LISTENING")
        page.evaluate("if (window.__lastFakeTrack.onended) window.__lastFakeTrack.onended();")
        page.wait_for_timeout(80)
        check("a track ending on its own (device unplugged) ends the session safely, to VOICE_ERROR", voice_state(page) == "VOICE_ERROR")
        check("no audio element left after device-loss cleanup", page.evaluate("document.querySelectorAll('audio').length") == 0)
        diag2 = page.evaluate("window.NX_INTELLIGENCE_VOICE.diagnostics()")
        check("device_lost recorded as a sanitized error class in diagnostics", any(e.get("error_class") == "device_lost" for e in diag2.get("events", [])), diag2)

        # ---------- Connection failure (IA-3H debt D4 -- safe baseline, no auto-reconnect) ----------
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(200)
        page.evaluate("""() => {
            window.__lastPc.connectionState = 'failed';
            if (window.__lastPc.onconnectionstatechange) window.__lastPc.onconnectionstatechange();
        }""")
        page.wait_for_timeout(80)
        check("pc connectionState 'failed' ends the session to VOICE_ERROR", voice_state(page) == "VOICE_ERROR")
        start_calls_before = page.evaluate("window.__getUserMediaCallCount")
        page.wait_for_timeout(500)
        check("no automatic reconnect loop (no new getUserMedia call on its own)", page.evaluate("window.__getUserMediaCallCount") == start_calls_before)

        # ---------- Restart: start -> end -> start again, repeatedly ----------
        for i in range(3):
            page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
            page.wait_for_timeout(150)
            page.evaluate("window.__simulateRtEvent({type:'session.created'});")
            page.wait_for_timeout(60)
            check(f"restart {i+1}: reaches LISTENING", voice_state(page) == "VOICE_LISTENING")
            page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
            page.wait_for_timeout(60)
            check(f"restart {i+1}: cleanly ends to VOICE_DISCONNECTED", voice_state(page) == "VOICE_DISCONNECTED")
        check("restart loop leaves exactly 0 orphaned <audio> elements", page.evaluate("document.querySelectorAll('audio').length") == 0)
        check("restart loop leaves exactly 0 leaked (never-stopped) mic tracks", all(t for t in page.evaluate("window.__allFakeTracks.map(t => t._stopped)")))

        page.close()
        browser.close()

    unexplained = [e for e in errors if "Failed to load resource" not in e and "network-guard" not in e]
    check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence VOICE Lifecycle Test (IA-3H.1): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
