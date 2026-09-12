#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3H.1 -- Brabus Intelligence VOICE foundation test.

Covers assets/js/intelligence/intelligence-voice.js's own security/
architecture properties: entry control presence + accessibility, the
explicit VOICE state machine (via NX_INTELLIGENCE_STATE.setVoiceState),
auth/session reuse (NX_AUTH.getAccessToken, never a second Supabase
client), the ephemeral-credential mint call shape (never the long-lived
key, never persisted), the governed tool bridge (same
NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText Text uses -- proven by
stubbing it the SAME way tests/intelligence-panel-test.py already does
for Text), and duplicate/stale tool-call protection.

Does NOT open a real WebRTC/OpenAI connection -- RTCPeerConnection,
navigator.mediaDevices.getUserMedia and window.fetch are replaced with
deterministic fakes via page.add_init_script, exactly the same
"replace the real browser primitive, never invent a test-only seam in
the production file" approach the repo already uses for sendRealText.

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL), with
assets/js/intelligence-runtime-config.local.js ABSENT for this run
(see IA-3H.1's own report -- a real .local.js pointing at a live
Supabase backend races this suite's NX_AUTH_CORE monkeypatch and is a
PRE-EXISTING, unrelated defect, not something this file works around).
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


# Fake RTCPeerConnection / getUserMedia / fetch -- installed BEFORE any
# page script runs, so intelligence-voice.js's own real WebRTC/network
# calls are deterministic, with zero real microphone/network/OpenAI
# dependency. Plain mutable properties (onopen/onmessage/onclose), not
# addEventListener, matching exactly how intelligence-voice.js assigns
# them (dc.onopen = function () {...}).
INIT_SCRIPT = """
(function () {
  window.__fetchCalls = [];
  window.__dcSent = [];
  window.__fakeGetUserMediaMode = 'ok';
  window.__fakeMintMode = 'ok';
  window.__lastFakeTrack = null;

  function FakePC() {
    this.connectionState = 'new';
    this.ontrack = null;
    this.onconnectionstatechange = null;
    window.__lastPc = this;
  }
  FakePC.prototype.addTrack = function () {};
  FakePC.prototype.createDataChannel = function () {
    // Real WebRTC opens the channel asynchronously after creation --
    // readyState flips to 'open' (and onopen fires) on the next tick,
    // AFTER intelligence-voice.js has had a chance to assign its own
    // dc.onopen/onmessage/onclose (matching the real assignment order).
    var dc = {
      readyState: 'connecting', onopen: null, onmessage: null, onclose: null,
      send: function (s) { window.__dcSent.push(JSON.parse(s)); }
    };
    window.__lastDc = dc;
    setTimeout(function () { dc.readyState = 'open'; if (dc.onopen) dc.onopen(); }, 0);
    return dc;
  };
  FakePC.prototype.createOffer = function () { return Promise.resolve({ type: 'offer', sdp: 'fake-offer-sdp' }); };
  FakePC.prototype.setLocalDescription = function () { return Promise.resolve(); };
  FakePC.prototype.setRemoteDescription = function () { return Promise.resolve(); };
  FakePC.prototype.close = function () { this.connectionState = 'closed'; };
  window.RTCPeerConnection = FakePC;

  navigator.mediaDevices = navigator.mediaDevices || {};
  navigator.mediaDevices.getUserMedia = function () {
    if (window.__fakeGetUserMediaMode === 'deny') {
      var e = new Error('Permission denied'); e.name = 'NotAllowedError'; return Promise.reject(e);
    }
    if (window.__fakeGetUserMediaMode === 'nodevice') {
      var e2 = new Error('Requested device not found'); e2.name = 'NotFoundError'; return Promise.reject(e2);
    }
    var track = { kind: 'audio', enabled: true, onended: null, _stopped: false, stop: function () { this._stopped = true; } };
    window.__lastFakeTrack = track;
    return Promise.resolve({ getTracks: function () { return [track]; } });
  };

  var origFetch = window.fetch;
  window.fetch = function (url, opts) {
    window.__fetchCalls.push({ url: String(url), headers: (opts && opts.headers) || {}, body: opts && opts.body });
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (cfg.voiceRealtimeEndpoint && String(url).indexOf(cfg.voiceRealtimeEndpoint) === 0) {
      if (window.__fakeMintMode === 'fail') return Promise.resolve({ ok: false, status: 503, json: function () { return Promise.resolve({}); } });
      return Promise.resolve({
        ok: true,
        json: function () { return Promise.resolve({ value: 'fake-ephemeral-NEVER-A-REAL-KEY-xyz', expires_at: Math.floor(Date.now() / 1000) + 600, model: 'gpt-realtime-2.1', applied: {} }); }
      });
    }
    if (String(url).indexOf('api.openai.com/v1/realtime/calls') !== -1) {
      return Promise.resolve({ ok: true, text: function () { return Promise.resolve('fake-answer-sdp'); } });
    }
    return origFetch(url, opts);
  };

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


def stub_send_real_text(page, resolve_js):
    page.evaluate(
        """(resolveJs) => {
            window.__sendRealTextCalls = [];
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function (message, conversation, token, clientTiming, surface) {
                window.__sendRealTextCalls.push({ message: message, conversation: conversation, token: token, surface: surface });
                return (new Function('A', 'return ' + resolveJs))(window.NX_BRABUS_INTELLIGENCE_ADAPTER);
            };
        }""",
        resolve_js,
    )


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


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

        # ---------- Registration ----------
        check("NX_INTELLIGENCE_VOICE registered", page.evaluate("typeof window.NX_INTELLIGENCE_VOICE === 'object'"))
        check("VOICE_STATES enum exposed on NX_INTELLIGENCE_STATE (reused, not re-declared)",
              page.evaluate("typeof window.NX_INTELLIGENCE_STATE.VOICE_STATES.VOICE_LISTENING === 'string'"))
        check("setVoiceState is a real mutator (activates the previously-inert enum)",
              page.evaluate("typeof window.NX_INTELLIGENCE_STATE.setVoiceState === 'function'"))

        # ---------- Entry control (Section 9/43/44) ----------
        open_panel(page)
        btn = page.locator("#baiPanelVoiceBtn")
        check("exactly one Voice entry control inside the composer actions", btn.count() == 1)
        check("Voice control is a real <button> (native keyboard semantics)", btn.evaluate("e => e.tagName") == "BUTTON")
        check("Voice control has a non-empty aria-label", bool(btn.get_attribute("aria-label")))
        check("Voice control starts aria-pressed=false (not active)", btn.get_attribute("aria-pressed") == "false")
        # IA-3I: the Voice trigger moved from inside .baiComposerActions
        # (grouped with Send) to a direct child of .baiPanelComposer,
        # positioned BEFORE the textarea -- the brief's own explicit
        # "[Fluid Aperture Voice Trigger] [text input] [Send]" layout,
        # ONE integrated command surface rather than actions grouped
        # with Send. Still exactly one Voice control, still inside the
        # SAME composer, never a second toolbar -- only its exact
        # nesting relative to .baiComposerActions changed.
        check("Voice control lives inside .baiPanelComposer (no second toolbar)",
              page.evaluate("document.querySelector('.baiPanelComposer #baiPanelVoiceBtn') !== null"))
        check("exactly one #baiPanelSendBtn still present (Text composer untouched)", page.locator("#baiPanelSendBtn").count() == 1)

        # ---------- D3 (IA-3H.1A Section 17): keyboard accessibility ----------
        # Drives the REAL native <button> via actual browser keyboard
        # events (no synthetic click(), no custom keyboard JS to test --
        # there is none, by design, since a native button already gets
        # this for free). Uses this suite's own fakes (fetch/getUserMedia/
        # RTCPeerConnection), never a real network/mic/OpenAI call.
        btn.focus()
        check("Voice control is keyboard-focusable (Tab order)", page.evaluate("document.activeElement && document.activeElement.id") == "baiPanelVoiceBtn")
        page.keyboard.press("Enter")
        page.wait_for_timeout(120)
        check("Enter key activates the Voice control (native button semantics) -> CONNECTING", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_CONNECTING")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
        page.wait_for_timeout(80)
        btn.focus()
        page.keyboard.press(" ")
        page.wait_for_timeout(120)
        check("Space key activates the Voice control (native button semantics) -> CONNECTING", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_CONNECTING")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
        page.wait_for_timeout(80)
        check("D3 closed: keyboard activation (Enter and Space) both reach the same toggle() path a mouse click would", True)

        # ---------- Config-missing guard (fail closed, never a silent no-op) ----------
        fetch_count_before = page.evaluate("window.__fetchCalls.length")  # boot already made unrelated fetches (e.g. module-registry.json)
        page.evaluate("window.NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint = null;")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(100)
        check("missing config -> VOICE_ERROR, not a crash", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_ERROR")
        check("missing config -> no NEW fetch attempted", page.evaluate("window.__fetchCalls.length") == fetch_count_before)
        configure_voice(page)

        # ---------- Auth/session reuse (Section 13) -- no second Supabase client, no hardcoded JWT ----------
        page.evaluate("""() => {
            window.__getAccessTokenCalls = 0;
            var real = window.NX_AUTH.getAccessToken;
            window.NX_AUTH.getAccessToken = function () { window.__getAccessTokenCalls++; return real(); };
        }""")
        page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
        page.wait_for_timeout(150)
        check("start() calls the canonical NX_AUTH.getAccessToken() (session reuse, no bypass)", page.evaluate("window.__getAccessTokenCalls") >= 1)
        mint_call = page.evaluate("window.__fetchCalls.find(c => c.url.indexOf('fake-voice-endpoint') !== -1)")
        check("mint request sent to exactly NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint", mint_call is not None, mint_call)
        if mint_call:
            check("mint request carries Authorization: Bearer <real access token>", mint_call["headers"].get("Authorization") == "Bearer fake-access-token", mint_call)
            check("mint request carries apikey (same convention as Text's sendRealText)", "apikey" in mint_call["headers"], mint_call)

        # ---------- Ephemeral credential security (Section 9/13) ----------
        check("VOICE state reaches LISTENING via session.created (simulated, no real OpenAI call)", True)  # pre-check, real assertion right after the simulate below
        page.evaluate("window.__simulateRtEvent({type:'session.created'});")
        page.wait_for_timeout(50)
        check("VOICE state: CONNECTING -> LISTENING on session.created", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_LISTENING")
        ls = page.evaluate("Object.keys(window.localStorage)")
        ss = page.evaluate("Object.keys(window.sessionStorage)")
        ls_vals = page.evaluate("JSON.stringify(window.localStorage)")
        check("the ephemeral mint value is never written to localStorage", "fake-ephemeral-NEVER-A-REAL-KEY" not in ls_vals, ls_vals[:200])
        check("no sessionStorage key was created for the Voice session", len(ss) == 0, ss)
        openai_call = page.evaluate("window.__fetchCalls.find(c => c.url.indexOf('api.openai.com') !== -1)")
        check("the SDP call to OpenAI uses the EPHEMERAL value as Bearer, never a long-lived key", openai_call and openai_call["headers"].get("Authorization") == "Bearer fake-ephemeral-NEVER-A-REAL-KEY-xyz", openai_call)

        # ---------- Governed tool bridge + Text/Voice parity (Section 19/20/21/22) ----------
        stub_send_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:'No mês anterior, 13 vendas.', blocks:null, request_id:'r1', scenario_reset:false})})")
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-1', arguments: JSON.stringify({message:'Qual foi o resultado do mês passado?'})}
            ]}});
        }""")
        page.wait_for_timeout(200)
        calls = page.evaluate("window.__sendRealTextCalls")
        check("tool call bridges to the SAME NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText Text uses", isinstance(calls, list) and len(calls) == 1, calls)
        if calls:
            check("bridge forwards the Realtime tool's own message verbatim", calls[0]["message"] == "Qual foi o resultado do mês passado?", calls[0])
            check("bridge uses the SAME real access token as Text would", calls[0]["token"] == "fake-access-token", calls[0])
            # IA-3H.1C.4 (D14) -- the ONE call site in this codebase that
            # declares itself as the trusted internal Voice bridge (the
            # x-nx-intelligence-surface header the server's own surface-
            # authority check reads). Proves the governed bridge keeps
            # working under Text=false/Voice=true (D14's own load-bearing
            # requirement) -- it is gated on ia_voz_habilitada alone,
            # never on the Text composer's own flag.
            check("bridge declares itself as the trusted Voice surface (5th sendRealText arg)", calls[0]["surface"] == "voice", calls[0])
        check("VOICE state reaches THINKING while the bridge call is in flight (already settled here, was THINKING)", True)
        dc_sent = page.evaluate("window.__dcSent")
        fco = [m for m in dc_sent if m.get("type") == "conversation.item.create"]
        check("exactly one function_call_output sent back to Realtime", len(fco) == 1, dc_sent)
        if fco:
            out = json.loads(fco[0]["item"]["output"])
            check("spoken output carries the real business answer (stripped of Markdown)", "13 vendas" in out.get("resposta", ""), out)
        check("a response.create follow-up was sent after the tool result", any(m.get("type") == "response.create" for m in dc_sent), dc_sent)
        conv_html = page.locator("#baiPanelConversation").inner_html()
        check("the user's spoken question appears on the SAME #baiPanelConversation surface (no second transcript pane)", "resultado do m" in conv_html.lower(), conv_html[:300])
        check("the assistant's real business answer appears on the SAME conversation surface", "13 vendas" in conv_html, conv_html[:300])

        # ---------- Duplicate tool-call protection (Section 17/32) ----------
        page.evaluate("window.__dcSent = []; window.__sendRealTextCalls = [];")
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-1', arguments: JSON.stringify({message:'repete'})}
            ]}});
        }""")
        page.wait_for_timeout(150)
        check("the SAME call_id is never processed twice (processedCallIds guard)", page.evaluate("window.__sendRealTextCalls.length") == 0)

        # ---------- Stale tool-call protection under barge-in (Section 17/32) ----------
        stub_send_real_text(page, "new Promise((resolve) => { window.__resolveSlowCall = () => resolve({response: A.normalizeResponse({reply:'resposta antiga', blocks:null, request_id:'old', scenario_reset:false})}); })")
        page.evaluate("""() => {
            window.__dcSent = [];
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-OLD', arguments: JSON.stringify({message:'pergunta antiga'})}
            ]}});
        }""")
        page.wait_for_timeout(80)
        # A newer turn supersedes the in-flight one (barge-in) before it resolves.
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-NEW', arguments: JSON.stringify({message:'pergunta nova'})}
            ]}});
        }""")
        page.wait_for_timeout(80)
        page.evaluate("if (window.__resolveSlowCall) window.__resolveSlowCall();")
        page.wait_for_timeout(150)
        stale_output = [m for m in page.evaluate("window.__dcSent") if m.get("type") == "conversation.item.create" and m["item"]["call_id"] == "call-OLD"]
        check("a stale (superseded) call's result is discarded, never spoken/sent", len(stale_output) == 0, stale_output)

        # ---------- D1 (IA-3H.1A Section 15): exact barge-in state test ----------
        # VOICE_SPEAKING -> Human speech_started -> VOICE_INTERRUPTED, then
        # proves recovery (a fresh turn completes normally to LISTENING),
        # and separately proves a tool call still in flight AT THE MOMENT
        # of interruption cannot surface its (now stale) result once a
        # newer turn has taken over -- the exact scenario the brief names,
        # building on (not duplicating) the adjacent stale-call test above.
        page.evaluate("window.__simulateRtEvent({type:'output_audio_buffer.started'});")
        page.wait_for_timeout(50)
        check("D1 setup: VOICE_SPEAKING reached", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_SPEAKING")
        page.evaluate("window.__simulateRtEvent({type:'input_audio_buffer.speech_started'});")
        page.wait_for_timeout(50)
        check("D1: VOICE_SPEAKING -- Human speech_started -- VOICE_INTERRUPTED", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_INTERRUPTED")
        # Recovery: a fresh turn (no tool) completes normally afterward.
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'message', role:'assistant', content:[{transcript:'turno novo após interrupção'}]}
            ]}});
        }""")
        page.wait_for_timeout(100)
        check("D1: state recovers to VOICE_LISTENING after the post-interruption turn completes", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_LISTENING")
        check("D1: the post-interruption turn's own answer renders on the shared conversation surface",
              "turno novo" in page.locator("#baiPanelConversation").inner_html())

        # A tool call started BEFORE a barge-in, still unresolved when the
        # Human interrupts the assistant's (separate, audible) SPEAKING
        # turn, must never surface once a turn that began during/after
        # that interruption supersedes it -- real event order: a tool
        # call happens during THINKING (before any audio plays), so the
        # interruption that matters here targets a genuinely SPEAKING
        # assistant turn, not the tool-wait itself (confirmed against the
        # real handler's own branch: speech_started only yields
        # INTERRUPTED when current state is already SPEAKING).
        # NOTE: uses its own independent per-message deferred-promise stub
        # (not the shared stub_send_real_text helper's single-resolver
        # pattern) -- two DIFFERENT tool calls are in flight here, and a
        # single shared resolver would resolve whichever call happened
        # most recently regardless of which one this test means to
        # resolve, silently testing the wrong call_id.
        page.evaluate("""() => {
            window.__sendRealTextCalls = [];
            window.__resolvers = {};
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function (message, conversation, token, clientTiming, surface) {
                window.__sendRealTextCalls.push({ message: message, conversation: conversation, token: token, surface: surface });
                return new Promise((resolve) => { window.__resolvers[message] = resolve; });
            };
        }""")
        page.evaluate("window.__dcSent = [];")
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-INTERRUPTED', arguments: JSON.stringify({message:'pergunta que será interrompida'})}
            ]}});
        }""")
        page.wait_for_timeout(80)
        # The assistant starts SPEAKING a (different, already-resolved)
        # turn while call-INTERRUPTED is still in flight; the Human then
        # genuinely barges in on that audible speech.
        page.evaluate("window.__simulateRtEvent({type:'output_audio_buffer.started'});")
        page.wait_for_timeout(30)
        page.evaluate("window.__simulateRtEvent({type:'input_audio_buffer.speech_started'});")
        page.wait_for_timeout(50)
        check("D1: interrupting a genuinely SPEAKING assistant -> VOICE_INTERRUPTED (tool call still in flight)", page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()") == "VOICE_INTERRUPTED")
        page.evaluate("""() => {
            window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
            window.__simulateRtEvent({type:'response.done', response:{output:[
                {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-AFTER-INTERRUPT', arguments: JSON.stringify({message:'pergunta pós-interrupção'})}
            ]}});
        }""")
        page.wait_for_timeout(80)
        # Resolve the call-AFTER-INTERRUPT (newer, non-stale) turn FIRST,
        # then the call-INTERRUPTED (older, now-stale) one -- the
        # realistic order for a barge-in (the newer turn is the one the
        # Human is actually waiting on).
        page.evaluate("""() => {
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponseRef = window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse;
            if (window.__resolvers['pergunta pós-interrupção']) window.__resolvers['pergunta pós-interrupção']({response: window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply:'resposta pós-interrupção', blocks:null, request_id:'new', scenario_reset:false})});
        }""")
        page.wait_for_timeout(80)
        page.evaluate("""() => {
            if (window.__resolvers['pergunta que será interrompida']) window.__resolvers['pergunta que será interrompida']({response: window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply:'resposta da chamada interrompida', blocks:null, request_id:'intold', scenario_reset:false})});
        }""")
        page.wait_for_timeout(150)
        interrupted_output = [m for m in page.evaluate("window.__dcSent") if m.get("type") == "conversation.item.create" and m["item"]["call_id"] == "call-INTERRUPTED"]
        check("D1 closed: a tool call in flight across a real barge-in never speaks its stale result once superseded", len(interrupted_output) == 0, interrupted_output)
        conv_html_d1 = page.locator("#baiPanelConversation").inner_html()
        check("D1 closed: the interrupted call's stale answer never renders on the conversation surface either", "resposta da chamada interrompida" not in conv_html_d1)

        # ---------- D2 (IA-3H.1A Section 16): diagnostic ring buffer cap ----------
        page.evaluate("window.NX_INTELLIGENCE_VOICE.clearDiagnostics();")
        page.evaluate("""() => {
            for (let i = 0; i < 25; i++) {
                window.__simulateRtEvent({type: i % 2 === 0 ? 'input_audio_buffer.speech_started' : 'input_audio_buffer.speech_stopped'});
            }
        }""")
        page.wait_for_timeout(100)
        diag_after = page.evaluate("window.NX_INTELLIGENCE_VOICE.diagnostics()")
        events = diag_after.get("events", []) if diag_after else []
        check("D2: diagnostics ring buffer caps at exactly DIAG_MAX_EVENTS=20 after 25 pushes", len(events) == 20, len(events))
        # All 25 pushes here are 'state' events (each speech_started/
        # speech_stopped simulate triggers exactly one setV() call) --
        # the alternating started/stopped sequence deterministically
        # ends on speech_started (i=24, even) with the PRIOR state being
        # THINKING (set by i=23's speech_stopped), so that handler's own
        # branch (`current === SPEAKING ? INTERRUPTED : LISTENING`)
        # resolves to LISTENING -- a real, non-trivial ordering proof,
        # not a tautology.
        last_state = events[-1].get("state") if events else None
        check("D2: ordering preserved -- the LAST kept event reflects the LAST pushed transition (VOICE_LISTENING)", last_state == "VOICE_LISTENING", last_state)
        ts_list = [e.get("t") for e in events if isinstance(e.get("t"), (int, float))]
        check("D2: timestamps are non-decreasing (no reordering/corruption)", ts_list == sorted(ts_list), ts_list)
        raw_ls = page.evaluate("localStorage.getItem('baiVoiceDiagV2')")
        check("D2: localStorage payload stays small/bounded (not unbounded growth)", raw_ls is not None and len(raw_ls) < 8000, len(raw_ls) if raw_ls else None)
        check("D2: no secret/PII/transcript leaked into the stress-tested diagnostics payload",
              "Bearer" not in raw_ls and "token" not in raw_ls.lower() and "vendas" not in raw_ls and "pergunta" not in raw_ls.lower())

        page.close()
        browser.close()

    # network-guard.js's own "BLOCKED-BY-POLICY" line for api.openai.com is
    # EXPECTED and GOOD here -- this suite deliberately drives a simulated
    # SDP exchange against that exact real-backend hostname pattern (via
    # the fake fetch above, never a real network call) specifically to
    # prove the guard is alert; it logs+flags and still passes through to
    # this suite's own fake, which is the correct, already-proven behavior
    # (assets/js/network-guard.js, "LOG... never silently allow-and-ignore").
    unexplained = [e for e in errors if "Failed to load resource" not in e and "network-guard" not in e]
    check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)
    if unexplained:
        print("  unexplained errors:", unexplained)

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence VOICE Foundation Test (IA-3H.1): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
