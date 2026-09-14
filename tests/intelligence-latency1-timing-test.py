#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LATENCY-1 -- end-to-end delivery + privacy proof for the new latency
observability fields this Wave added, mirroring
intelligence-devtiming-stage-ms-test.py's own established technique
(stub window.fetch, one level below sendRealText, so the REAL
sendRealText -> REAL buildDevTiming -> REAL logDevTiming chain runs
unmodified end to end) rather than inventing a new harness.

Part A (TEXT): a representative portal-ai-homolog response shaped
exactly like this Wave's own server diff (_homolog_edge_timing.
rpc_total_ms/rpc_count/tool_used/openai_model/first_token_observable,
plus 5 new stage_ms fields: request_validation_ms/kill_switch_config_ms/
authority_resolution_ms/tool_policy_ms/response_assembly_ms) is
returned by a stubbed fetch; asserts every new field survives to the
final [bai-timing] console object, that the new network_plus_server_ms/
client_parse_adapter_ms/network_only_ms_approx client-side split is
computed, and that no prompt/reply/tool content ever leaks alongside
them (same security assertions the pre-existing devtiming tests make).

Part B (VOICE): reuses intelligence-voice-foundation-test.py's own
established fake-RTCPeerConnection/simulateRtEvent harness and
stub_send_real_text technique. Proves the new trace_id field on the
Voice bridge's own 'tool_call' diagnostic entry (assets/js/intelligence/
intelligence-voice.js) correlates to the SAME correlation_id the shared
adapter's _devTiming carried for that exact call -- and that it is
absent (never null/undefined) when _devTiming itself is absent.

Requires: `python -m http.server <port>` running from this worktree's
own root, with assets/js/intelligence-runtime-config.local.js ABSENT
for this run (same D17 requirement intelligence-voice-foundation-test.py
already documents).
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


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


# Shaped exactly like this Wave's own server diff to portal-ai-homolog's
# _homolog_edge_timing (LATENCY-1 fields alongside every pre-existing
# one, none removed -- additive-only, matching the real response shape).
FAKE_RESPONSE_BODY = {
    "reply": "resposta de teste latency-1",
    "blocks": None,
    "request_id": "r-latency1-1",
    "scenario_reset": False,
    "_homolog_debug": {"tools_used": ["simular_financiamento"], "tool_call_count": 1, "calls": []},
    "_homolog_edge_timing": {
        "handler_entry_epoch_ms": 1000,
        "response_ready_epoch_ms": 1500,
        "instance_id": "inst-latency1-test",
        "instance_age_ms": 42,
        "latency_ms": 500,
        "stage_ms": {
            "auth_ms": 80, "master_gate_ms": 60, "config_scope_ms": 120,
            "openai_pass_ms": [210, 30],
            "tool_dispatch_ms": [{"name": "simular_financiamento", "ms": 15}],
            "request_validation_ms": 3, "kill_switch_config_ms": 55, "authority_resolution_ms": 65,
            "tool_policy_ms": 2, "response_assembly_ms": 1
        },
        "prompt_profile": "finance", "prompt_chars": 1234,
        "rpc_total_ms": 15, "rpc_count": 1, "tool_used": True,
        "openai_model": "gpt-5.6-luna", "first_token_observable": False
    }
}


def part_a_text(page):
    page.evaluate(
        """() => {
            window.__baiTimingCalls = [];
            var origLog = console.log.bind(console);
            console.log = function () {
                var args = Array.prototype.slice.call(arguments);
                if (args[0] === '[bai-timing]') window.__baiTimingCalls.push(args[1]);
                return origLog.apply(console, args);
            };
        }"""
    )
    page.evaluate(
        """([body]) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_INTELLIGENCE_CONFIG.textEndpoint = 'https://fake.local/portal-ai-homolog';
            window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = 'fake-key';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = {
                readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }])
            };
            window.__origFetch = window.fetch;
            window.fetch = function (url) {
                // Real fetch(): the returned Promise resolves BEFORE the
                // body is read (resp.json() is a second, later await) --
                // this stub matches that shape so the new
                // network_plus_server_ms / client_parse_adapter_ms split
                // (added this Wave around that exact real gap) is
                // genuinely exercised, not just a same-tick resolution.
                return new Promise(function (resolve) {
                    setTimeout(function () {
                        resolve({ ok: true, status: 200, json: function () {
                            return new Promise(function (resolveJson) {
                                setTimeout(function () { resolveJson(body); }, 5);
                            });
                        } });
                    }, 5);
                });
            };
        }""",
        [FAKE_RESPONSE_BODY],
    )

    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)
    page.fill("#baiPanelInput", "teste latency-1 end-to-end")
    page.click("#baiPanelSendBtn")
    page.wait_for_timeout(400)

    timing_calls = page.evaluate("window.__baiTimingCalls")
    check("A. [bai-timing] emitted exactly once", isinstance(timing_calls, list) and len(timing_calls) == 1, timing_calls)
    t = timing_calls[0] if timing_calls else {}
    line = json.dumps(t)
    stage = t.get("stage_ms") or {}

    check("A. stage_ms.request_validation_ms == 3 (new field survives)", stage.get("request_validation_ms") == 3, stage)
    check("A. stage_ms.kill_switch_config_ms == 55 (new field survives)", stage.get("kill_switch_config_ms") == 55, stage)
    check("A. stage_ms.authority_resolution_ms == 65 (new field survives)", stage.get("authority_resolution_ms") == 65, stage)
    check("A. stage_ms.tool_policy_ms == 2 (new field survives)", stage.get("tool_policy_ms") == 2, stage)
    check("A. stage_ms.response_assembly_ms == 1 (new field survives)", stage.get("response_assembly_ms") == 1, stage)
    check("A. rpc_total_ms == 15 (new sibling field survives)", t.get("rpc_total_ms") == 15, t)
    check("A. rpc_count == 1 (new sibling field survives)", t.get("rpc_count") == 1, t)
    check("A. tool_used == True (new sibling field survives)", t.get("tool_used") is True, t)
    check("A. openai_model == 'gpt-5.6-luna' (unaltered model, safe metadata)", t.get("openai_model") == "gpt-5.6-luna", t)
    check("A. first_token_observable == False (honest, non-streaming Responses API)", t.get("first_token_observable") is False, t)

    check("A. network_plus_server_ms present and non-negative", isinstance(t.get("network_plus_server_ms"), (int, float)) and t["network_plus_server_ms"] >= 0, t)
    check("A. client_parse_adapter_ms present and non-negative", isinstance(t.get("client_parse_adapter_ms"), (int, float)) and t["client_parse_adapter_ms"] >= 0, t)
    check("A. network_only_ms_approx computed from network_plus_server_ms - edge_internal_ms", t.get("network_only_ms_approx") == t.get("network_plus_server_ms") - t.get("edge_internal_ms"), t)

    check("A. pre-existing stage_ms fields still present alongside the new ones (additive-only)", stage.get("auth_ms") == 80 and stage.get("config_scope_ms") == 120, stage)
    check("A. pre-existing prompt_profile/prompt_chars still present", t.get("prompt_profile") == "finance" and t.get("prompt_chars") == 1234, t)

    check("A. no prompt text leaked into [bai-timing]", "teste latency-1 end-to-end" not in line, line)
    check("A. no reply text leaked into [bai-timing]", "resposta de teste latency-1" not in line, line)
    check("A. no tool arguments/results leaked (only name+ms per stage entry)", '"args"' not in line and '"result"' not in line and '"output"' not in line, line)

    page.evaluate("window.fetch = window.__origFetch;")


VOICE_INIT_SCRIPT = """
(function () {
  window.__dcSent = [];
  function FakePC() {
    this.connectionState = 'new'; this.ontrack = null; this.onconnectionstatechange = null;
    window.__lastPc = this;
  }
  FakePC.prototype.addTrack = function () {};
  FakePC.prototype.createDataChannel = function () {
    var dc = { readyState: 'connecting', onopen: null, onmessage: null, onclose: null,
      send: function (s) { window.__dcSent.push(JSON.parse(s)); } };
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
    var track = { kind: 'audio', enabled: true, onended: null, _stopped: false, stop: function () { this._stopped = true; } };
    return Promise.resolve({ getTracks: function () { return [track]; } });
  };
  var origFetch = window.fetch;
  window.fetch = function (url, opts) {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (cfg.voiceRealtimeEndpoint && String(url).indexOf(cfg.voiceRealtimeEndpoint) === 0) {
      return Promise.resolve({ ok: true, json: function () { return Promise.resolve({ value: 'fake-ephemeral-NEVER-A-REAL-KEY-xyz', expires_at: Math.floor(Date.now() / 1000) + 600, model: 'gpt-realtime-2.1', applied: {} }); } });
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


def part_b_voice(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.add_init_script(VOICE_INIT_SCRIPT)
    page.goto(BASE + "#/landing")
    page.wait_for_timeout(500)
    set_profile(page, "AUTHORIZED", True, "MASTER")
    configure_voice(page)
    page.evaluate("window.NX_INTELLIGENCE_VOICE.mount();")
    page.evaluate("() => { try { localStorage.removeItem('baiVoiceDiagV2'); } catch (e) {} }")

    # A response WITH _devTiming.correlation_id -- proves the trace_id is
    # carried through onto the Voice bridge's own diagnostic entry.
    stub_send_real_text(
        page,
        "Promise.resolve({response: A.normalizeResponse({reply:'13 vendas no mes anterior.', blocks:null, request_id:'r1', scenario_reset:false}), "
        "_devTiming: {correlation_id: 'trace-voice-latency1-abc123'}})"
    )
    page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
    page.wait_for_timeout(150)
    page.evaluate("window.__simulateRtEvent({type:'session.created'});")
    page.wait_for_timeout(80)
    page.evaluate("""() => {
        window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
        window.__simulateRtEvent({type:'conversation.item.input_audio_transcription.completed', transcript:'Qual foi o resultado do mes passado?'});
        window.__simulateRtEvent({type:'response.done', response:{output:[
            {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-latency1-1', arguments: JSON.stringify({message:'Qual foi o resultado do mes passado?'})}
        ]}});
    }""")
    page.wait_for_timeout(250)

    diag = page.evaluate("window.NX_INTELLIGENCE_VOICE.diagnostics()")
    events = (diag or {}).get("events", []) if isinstance(diag, dict) else []
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    check("B. exactly one 'tool_call' diagnostic entry recorded", len(tool_calls) == 1, events)
    if tool_calls:
        check("B. trace_id on the diagnostic entry matches this call's own correlation_id from _devTiming", tool_calls[0].get("trace_id") == "trace-voice-latency1-abc123", tool_calls[0])
        check("B. diagnostic entry still carries its pre-existing ms/ok/turn fields (additive-only)", isinstance(tool_calls[0].get("ms"), (int, float)) and tool_calls[0].get("ok") is True, tool_calls[0])
    diag_line = json.dumps(events)
    check("B. no reply/prompt content leaked into Voice diagnostics", "13 vendas" not in diag_line and "Qual foi o resultado" not in diag_line, diag_line)

    page.evaluate("window.NX_INTELLIGENCE_VOICE.end();")
    page.wait_for_timeout(100)

    # Second call, this time WITHOUT _devTiming at all -- trace_id must
    # be absent (never a literal "null" string leaking a stray value),
    # same discipline diagPush's own type-guard already enforces for
    # every other optional field.
    stub_send_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:'ok.', blocks:null, request_id:'r2', scenario_reset:false})})")
    page.evaluate("() => { try { localStorage.removeItem('baiVoiceDiagV2'); } catch (e) {} }")
    page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
    page.wait_for_timeout(150)
    page.evaluate("window.__simulateRtEvent({type:'session.created'});")
    page.wait_for_timeout(80)
    page.evaluate("""() => {
        window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
        window.__simulateRtEvent({type:'conversation.item.input_audio_transcription.completed', transcript:'de novo'});
        window.__simulateRtEvent({type:'response.done', response:{output:[
            {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-latency1-2', arguments: JSON.stringify({message:'de novo'})}
        ]}});
    }""")
    page.wait_for_timeout(250)
    diag2 = page.evaluate("window.NX_INTELLIGENCE_VOICE.diagnostics()")
    events2 = (diag2 or {}).get("events", []) if isinstance(diag2, dict) else []
    tool_calls2 = [e for e in events2 if e.get("type") == "tool_call"]
    check("B. second call (no _devTiming) still recorded", len(tool_calls2) == 1, events2)
    if tool_calls2:
        check("B. trace_id key absent (not null-as-string) when _devTiming is absent", "trace_id" not in tool_calls2[0], tool_calls2[0])

    page.close()


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        part_a_text(page)
        page.close()

        part_b_voice(browser)

        browser.close()

    n_pass = sum(1 for _, ok in results if ok)
    n_fail = sum(1 for _, ok in results if not ok)
    print(f"\n=== LATENCY-1 Timing Fields End-to-End + Privacy Test: {n_pass}/{len(results)} ===")
    print("RESULT: " + ("PASS" if n_fail == 0 else "FAIL"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
