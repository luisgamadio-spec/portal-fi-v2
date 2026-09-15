#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LATENCY-2C -- proves the homologation-only latency diagnostic
collector (assets/js/intelligence/intelligence-latency-diag.js):
automatic capture from the real Text/Voice [bai-timing] pipeline,
strict allowlist privacy, FIFO/max-100 buffer discipline, JSON export
shape, environment gating (no visible export control on an
UNKNOWN_HOST), and identity-change clearing (reuses
NX_INTELLIGENCE_STATE's own onOwnerChange, same mechanism SESSIONSEC1
already relies on).

Requires: `python -m http.server <port>` running from this worktree's
own root, with assets/js/intelligence-runtime-config.local.js ABSENT
for this run (D17 requirement).
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


SENSITIVE_MARKERS = {
    "auth_user_id": "AUTHUSER-SHOULD-NOT-APPEAR-9f31",
    "access_token": "Bearer-SHOULD-NOT-APPEAR-xyz",
    "authorization": "Bearer SHOULD-NOT-APPEAR-abc",
    "jwt": "eyJSHOULD.NOT.APPEAR",
    "prompt": "qual foi o salario do Douglas SHOULD-NOT-APPEAR",
    "reply": "o salario foi R$ SHOULD-NOT-APPEAR",
    "tool_arguments": {"seller": "SHOULD-NOT-APPEAR-SELLER"},
    "tool_result": {"salary": 999999},
    "email": "pessoa@SHOULD-NOT-APPEAR.com",
    "cpf": "123.456.789-00-SHOULD-NOT-APPEAR",
    "salary": 12345.67,
    "store": "SHOULD-NOT-APPEAR-STORE",
    "cookie": "session=SHOULD-NOT-APPEAR",
}

SAFE_RAW_WITH_SENSITIVE_NOISE = dict(SENSITIVE_MARKERS)
SAFE_RAW_WITH_SENSITIVE_NOISE.update({
    "correlation_id": "corr-latency2c-safe-1",
    "total_ui_ms": 1234,
    "network_plus_server_ms": 900,
    "client_parse_adapter_ms": 12,
    "render_ms": 5,
    "edge_latency_ms": 850,
    "rpc_total_ms": 15,
    "rpc_count": 1,
    "openai_model": "gpt-5.6-luna",
    "first_token_observable": False,
    "tool_used": True,
    "openai_retry_count": 1,
    "openai_retry_occurred": True,
    "edge_instance_age_ms": 42,
    "stage_ms": {
        "execution_path": "openai_tool_loop",
        "request_validation_ms": 3,
        "kill_switch_config_ms": 55,
        "authority_resolution_ms": 65,
        "tool_policy_ms": 2,
        "response_assembly_ms": 1,
        "openai_pass_ms": [300, 450],
        "openai_pass_count": 2
    }
})

FAKE_RESPONSE_BODY = {
    "reply": "resposta de teste latency2c",
    "blocks": None,
    "request_id": "r-latency2c-1",
    "scenario_reset": False,
    "_homolog_debug": {"tools_used": ["simular_financiamento"], "tool_call_count": 1, "calls": []},
    "_homolog_edge_timing": {
        "handler_entry_epoch_ms": 1000,
        "response_ready_epoch_ms": 1500,
        "instance_id": "inst-latency2c-test",
        "instance_age_ms": 42,
        "latency_ms": 500,
        "stage_ms": {
            "auth_ms": 80, "master_gate_ms": 60, "config_scope_ms": 120,
            "openai_pass_ms": [210, 30],
            "tool_dispatch_ms": [{"name": "simular_financiamento", "ms": 15}],
            "request_validation_ms": 3, "kill_switch_config_ms": 55, "authority_resolution_ms": 65,
            "tool_policy_ms": 2, "response_assembly_ms": 1, "execution_path": "openai_tool_loop",
            "openai_pass_count": 2
        },
        "prompt_profile": "full", "prompt_chars": 1234,
        "rpc_total_ms": 15, "rpc_count": 1, "tool_used": True,
        "openai_model": "gpt-5.6-luna", "first_token_observable": False,
        "openai_retry_count": 1, "openai_retry_occurred": True
    }
}


def part1_environment_gating(browser):
    # R -- an UNKNOWN_HOST (e.g. a real production domain this repo
    # never serves) must expose no visible export control at all, not
    # merely an inert one.
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    # Must win the race against shell.js's own real boot() (which calls
    # NX_INTELLIGENCE_VOICE.mount() unconditionally, building the diag
    # DOM once -- diagPanelBuilt then blocks any later rebuild).
    # environment-guard.js's OWN DOMContentLoaded listener unconditionally
    # re-overwrites window.NX_ENVIRONMENT (authoritative re-classification,
    # by its own design) -- since that listener is registered by a
    # script tag that loads before shell.js's, and add_init_script code
    # always runs before every page script (so a DOMContentLoaded
    # listener registered there always fires FIRST, i.e. BEFORE
    # environment-guard.js's own), there is no ordering that lets a
    # plain NX_ENVIRONMENT assignment survive both. Patching
    # NX_INTELLIGENCE_LATENCY_DIAG.isEnabled() itself instead sidesteps
    # that race entirely: this module's own script tag runs during
    # synchronous HTML parsing (like every other <script src>), which
    # completes before DOMContentLoaded fires at all -- so by the time
    # ANY DOMContentLoaded listener runs (including this one, which
    # still fires first), window.NX_INTELLIGENCE_LATENCY_DIAG already
    # exists and can be safely monkey-patched before shell.js's own
    # later-firing boot()/mount() ever calls into it.
    page.add_init_script("""
        document.addEventListener('DOMContentLoaded', function () {
            if (window.NX_INTELLIGENCE_LATENCY_DIAG) {
                window.NX_INTELLIGENCE_LATENCY_DIAG.isEnabled = function () { return false; };
            }
        });
    """)
    page.goto(BASE + "?voiceDiag=1#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    enabled_unknown = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.isEnabled()")
    check("R. isEnabled() is false (simulating UNKNOWN_HOST/production)", enabled_unknown is False, enabled_unknown)
    page.click("#baiVoiceDiagToggle")
    page.wait_for_timeout(150)
    check("R. No export control rendered in the DOM on UNKNOWN_HOST", page.locator("#baiLatencyDiagExport").count() == 0)
    check("R. No clear-diagnostic control rendered in the DOM on UNKNOWN_HOST", page.locator("#baiLatencyDiagClear").count() == 0)
    page.close()

    # Sanity: on LOCAL_DEV (this test server's own real classification)
    # the control DOES render.
    page2 = browser.new_page(viewport={"width": 1366, "height": 900})
    page2.goto(BASE + "?voiceDiag=1#/landing")
    page2.wait_for_selector("#landingNav", timeout=8000)
    env_name = page2.evaluate("window.NX_ENVIRONMENT && window.NX_ENVIRONMENT.name")
    page2.evaluate("window.NX_INTELLIGENCE_VOICE.mount();")
    page2.click("#baiVoiceDiagToggle")
    page2.wait_for_timeout(150)
    check(f"(sanity) export control renders on this test server's own real environment ({env_name})", page2.locator("#baiLatencyDiagExport").count() == 1, env_name)
    page2.close()


def part2_privacy_allowlist_buffer(page):
    # G/H/I/J/K -- deliberately poison a raw entry with every forbidden
    # field category and confirm NONE of it survives capture().
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")
    page.evaluate("(raw) => window.NX_INTELLIGENCE_LATENCY_DIAG.capture(raw, 'text')", SAFE_RAW_WITH_SENSITIVE_NOISE)
    entries = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")
    check("(setup) exactly one entry captured for the privacy probe", len(entries) == 1, entries)
    line = json.dumps(entries)
    for key, marker in SENSITIVE_MARKERS.items():
        marker_str = json.dumps(marker)
        present = marker_str in line or (isinstance(marker, str) and marker in line)
        check(f"G/H/I/J/K. forbidden field '{key}' absent from captured entry", not present, line[:300])
    check("(sanity) safe correlation_id DID survive", entries[0].get("correlation_id") == "corr-latency2c-safe-1", entries[0])
    check("(sanity) safe stage timing DID survive", entries[0].get("request_validation_ms") == 3, entries[0])
    check("(sanity) openai_retry_count DID survive", entries[0].get("openai_retry_count") == 1, entries[0])

    # L/M -- FIFO + max 100.
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")
    page.evaluate("""() => {
        for (let i = 0; i < 105; i++) {
            window.NX_INTELLIGENCE_LATENCY_DIAG.capture({ correlation_id: 'seq-' + i, total_ui_ms: i }, 'text');
        }
    }""")
    after_105 = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")
    check("L. buffer caps at exactly 100 entries", len(after_105) == 100, len(after_105))
    check("M. FIFO: oldest entries (seq-0..seq-4) were evicted", after_105[0].get("correlation_id") == "seq-5", after_105[0])
    check("M. FIFO: newest entry (seq-104) is the last one", after_105[-1].get("correlation_id") == "seq-104", after_105[-1])

    # N -- clear().
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")
    check("N. clear() empties the buffer", len(page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")) == 0)

    # Q -- export JSON schema.
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.capture({correlation_id: 'corr-export-1', total_ui_ms: 10}, 'text');")
    exported = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.exportJson()")
    parsed = json.loads(exported)
    check("Q. export has schema_version", parsed.get("schema_version") == 1, parsed)
    check("Q. export has exported_at", isinstance(parsed.get("exported_at"), str) and len(parsed["exported_at"]) > 0)
    check("Q. export environment == HOMOLOGATION", parsed.get("environment") == "HOMOLOGATION", parsed.get("environment"))
    check("Q. export entry_count matches entries length", parsed.get("entry_count") == len(parsed.get("entries", [])), parsed)
    check("Q. export contains only the allowlisted top-level keys", set(parsed.keys()) == {"schema_version", "exported_at", "environment", "environment_hostname", "entry_count", "entries"}, set(parsed.keys()))
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")


def part3_real_text_capture(page):
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
            window.fetch = function (url) {
                return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
            };
            window.NX_INTELLIGENCE_LATENCY_DIAG.clear();
        }""",
        [FAKE_RESPONSE_BODY],
    )
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)
    page.fill("#baiPanelInput", "teste latency2c captura real")
    page.click("#baiPanelSendBtn")
    page.wait_for_timeout(400)

    entries = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")
    check("A. One completed Text request creates exactly one diagnostic entry", len(entries) == 1, entries)
    if entries:
        e = entries[0]
        check("C. correlation_id survives into the captured entry", isinstance(e.get("correlation_id"), str) and len(e["correlation_id"]) > 0, e)
        check("D. server timing survives (edge_total_ms, request_validation_ms, etc.)", e.get("edge_total_ms") == 500 and e.get("request_validation_ms") == 3 and e.get("authority_resolution_ms") == 65, e)
        check("E. OpenAI pass timing survives (openai_pass_ms, openai_total_ms)", e.get("openai_pass_ms") == [210, 30] and e.get("openai_total_ms") == 240, e)
        check("F. retry count survives", e.get("openai_retry_count") == 1 and e.get("openai_retry_occurred") is True, e)
        check("(surface) surface tagged 'text'", e.get("surface") == "text", e)
        check("(external gap) external_unaccounted_ms derived honestly", isinstance(e.get("external_unaccounted_ms"), (int, float)), e)
    line = json.dumps(entries)
    check("G/H. no prompt/reply text leaked into the captured entry", "teste latency2c captura real" not in line and "resposta de teste latency2c" not in line, line[:300])
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")


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


def part4_real_voice_capture(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.add_init_script(VOICE_INIT_SCRIPT)
    page.goto(BASE + "#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    set_profile(page, "AUTHORIZED", True, "MASTER")
    page.evaluate(
        """(endpoint) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint = endpoint;
            window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey || 'fake-anon-key';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-access-token') };
        }""",
        "http://fake-voice-endpoint.local/",
    )
    page.evaluate("window.NX_INTELLIGENCE_VOICE.mount();")
    page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.clear();")

    # stub_send_real_text, same technique as intelligence-voice-
    # foundation-test.py / intelligence-latency1-timing-test.py --
    # resolves with a real-shaped _devTiming object so the bridge's own
    # capture() hand-off is exercised end to end.
    page.evaluate(
        """(resolveJs) => {
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function (message, conversation, token, clientTiming, surface) {
                return (new Function('A', 'return ' + resolveJs))(window.NX_BRABUS_INTELLIGENCE_ADAPTER);
            };
        }""",
        "Promise.resolve({response: A.normalizeResponse({reply:'13 vendas no mes anterior.', blocks:null, request_id:'r1', scenario_reset:false}), "
        "_devTiming: {correlation_id: 'trace-latency2c-voice-1', edge_latency_ms: 420, rpc_total_ms: 10, rpc_count: 1, "
        "openai_model: 'gpt-5.6-luna', first_token_observable: false, openai_retry_count: 0, openai_retry_occurred: false, "
        "stage_ms: {execution_path: 'openai_tool_loop', request_validation_ms: 2, kill_switch_config_ms: 40, authority_resolution_ms: 45, "
        "tool_policy_ms: 1, response_assembly_ms: 1, openai_pass_ms: [180], openai_pass_count: 1}}})"
    )
    page.evaluate("window.NX_INTELLIGENCE_VOICE.start();")
    page.wait_for_timeout(150)
    page.evaluate("window.__simulateRtEvent({type:'session.created'});")
    page.wait_for_timeout(80)
    page.evaluate("""() => {
        window.__simulateRtEvent({type:'input_audio_buffer.speech_stopped'});
        window.__simulateRtEvent({type:'conversation.item.input_audio_transcription.completed', transcript:'Qual foi o resultado do mes passado?'});
        window.__simulateRtEvent({type:'response.done', response:{output:[
            {type:'function_call', name:'consultar_portal_intelligence', call_id:'call-l2c-1', arguments: JSON.stringify({message:'Qual foi o resultado do mes passado?'})}
        ]}});
    }""")
    page.wait_for_timeout(250)

    entries = page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")
    check("B. Voice business request creates exactly one diagnostic entry", len(entries) == 1, entries)
    if entries:
        e = entries[0]
        check("B. entry surface tagged 'voice'", e.get("surface") == "voice", e)
        check("B. correlation_id survives for Voice too", e.get("correlation_id") == "trace-latency2c-voice-1", e)
        check("B. server timing survives for Voice too", e.get("edge_total_ms") == 420 and e.get("authority_resolution_ms") == 45, e)
        check("B. voice_tool_bridge_ms is present (already reliably measured)", isinstance(e.get("voice_tool_bridge_ms"), (int, float)), e)
    line = json.dumps(entries)
    check("B. no reply/prompt content leaked into the Voice-origin entry", "13 vendas" not in line and "resultado do mes passado" not in line, line[:300])

    page.close()


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        part1_environment_gating(browser)
        part4_real_voice_capture(browser)

        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_selector("#landingNav", timeout=8000)
        set_profile(page, "AUTHORIZED", True, "MASTER")

        part2_privacy_allowlist_buffer(page)
        part3_real_text_capture(page)
        page.close()

        # O/P -- identity transition clears diagnostics (real
        # NX_AUTH_CORE lifecycle, same robust technique SESSIONSEC1's
        # own test established). Own FRESH page -- set_profile() above
        # monkey-patched NX_AUTH_CORE.getState/getContext to hardcoded
        # closures on the previous page; once overridden that way, a
        # REAL login()/logout() call still updates auth-core.js's own
        # internal state (and still correctly drives
        # NX_INTELLIGENCE_STATE's identity-owner tracking, which reads
        # the listener's own arguments, not a fresh getState() call) --
        # but THIS test's own wait_for_function below, which does call
        # getState()/getContext() directly, would be reading the
        # stale hardcoded closures forever. A fresh page never applies
        # that override in the first place.
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_selector("#landingNav", timeout=8000)
        page.evaluate(
            """(() => {
                window.__uatFakeSession = null;
                window.__uatPendingProfile = null;
                window.NX_AUTH = {
                    isAuthConfigured: true,
                    getSession: () => Promise.resolve(window.__uatFakeSession),
                    signIn: () => { window.__uatFakeSession = { user: { id: (window.__uatPendingProfile || {}).authUserId } }; return Promise.resolve(); },
                    signOut: () => { window.__uatFakeSession = null; return Promise.resolve(); },
                    resolveAuthorizedProfile: () => Promise.resolve(window.__uatPendingProfile),
                    resolveAllowedModules: () => Promise.resolve(['dashbi']),
                    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? 'uat-token' : null),
                    onAuthStateChange: () => {}
                };
            })"""
        )
        user_a = {"userId": "row-l2c-a", "authUserId": "AUTHUSER-L2C-A", "nome": "A", "perfil": "VENDEDOR", "loja": "BARRA FUNDA", "status": "NOVOS", "ativo": True}
        user_b = {"userId": "row-l2c-b", "authUserId": "AUTHUSER-L2C-B", "nome": "B", "perfil": "VENDEDOR", "loja": "EUROPA", "status": "NOVOS", "ativo": True}

        page.evaluate("(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('x@test.invalid','x','c'); }", user_a)
        page.wait_for_function("(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id", arg=user_a["authUserId"], timeout=5000)
        page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.capture({correlation_id: 'corr-identity-a'}, 'text');")
        check("(setup) entry captured under USER A", len(page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")) == 1)

        page.evaluate("window.NX_AUTH_CORE.logout()")
        page.wait_for_function("() => window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=5000)
        check("O. Logout clears the latency diagnostic buffer", len(page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")) == 0)

        page.evaluate("(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('x@test.invalid','x','c'); }", user_a)
        page.wait_for_function("(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id", arg=user_a["authUserId"], timeout=5000)
        page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.capture({correlation_id: 'corr-identity-a2'}, 'text');")
        page.evaluate("(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('y@test.invalid','x','c'); }", user_b)
        page.wait_for_function("(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id", arg=user_b["authUserId"], timeout=5000)
        check("P. Different authenticated user clears the latency diagnostic buffer", len(page.evaluate("window.NX_INTELLIGENCE_LATENCY_DIAG.getEntries()")) == 0)

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("W. Zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

        page.close()
        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== LATENCY-2C: Safe Homolog Latency Capture ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
