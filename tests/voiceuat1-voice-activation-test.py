#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VOICE-UAT-1 -- proves the ONLY change this wave makes
(assets/js/intelligence-runtime-config.production.js's own
voiceRealtimeEndpoint, previously null) correctly and safely activates
the ALREADY-EXISTING Voice frontend bridge
(assets/js/intelligence/intelligence-voice.js, unmodified) on the exact
GitHub Pages homologation runtime shape, without:
  - ever completing a real WebRTC/microphone session (no fake Human
    audio approval -- the mint fetch is intercepted and stubbed to a
    controlled failure, which the real code already handles safely,
    proving request construction + fail-closed behavior without ever
    reaching getUserMedia/RTCPeerConnection);
  - exposing any private secret (OPENAI_API_KEY-shaped or service-role-
    shaped string) anywhere in the served bundle;
  - regressing Text, Living Core, or the zero-horizontal-scroll rule.

Uses the exact same direct-index.html-load, real-runtime-machinery
technique as SEC-1C.2/SEC-1C.3's own tests (NX_ENVIRONMENT/
NX_INTELLIGENCE_CONFIG substituted for what the real hostname's own
script tags produce -- nothing else faked).

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

PORT = os.environ.get("VOICEUAT1_TEST_PORT", "8712")
BASE = f"http://127.0.0.1:{PORT}"

REAL_TEXT_ENDPOINT = "https://yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-ai-homolog"
REAL_VOICE_ENDPOINT = "https://yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-realtime-homolog"
REAL_ANON_KEY = "sb_publishable__J96gDH1kOqlc4iFW24Z2Q_u_lWAg5_"  # public by design, matches committed config

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def open_landing_as_vendedor(page, env_override, intel_config_override):
    """Same technique as SEC-1C.2/SEC-1C.3's own tests -- real bootstrap
    machinery, only NX_ENVIRONMENT/NX_INTELLIGENCE_CONFIG and the auth
    context substituted for what the real host/session would produce."""
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    allowed_modules = ["dashbi", "simuladorCompleto", "comissoes"]
    page.evaluate(
        """([envOverride, cfgOverride, allowedModuleIds]) => {
            window.NX_AUTH_CORE.getState = () => 'SIGNED_OUT';
            window.NX_AUTH_CORE.getContext = () => null;
            if (window.NX_INTELLIGENCE_PANEL) window.NX_INTELLIGENCE_PANEL.refresh();

            window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
            window.NX_AUTH_CORE.getContext = () => Object.freeze({
                isMaster: false, perfil: 'VENDEDOR', allowedModuleIds,
                nome: 'UAT VENDEDOR', loja: 'BARRA FUNDA', status: 'NOVOS'
            });
            if (envOverride) window.NX_ENVIRONMENT = Object.assign({}, window.NX_ENVIRONMENT, envOverride);
            if (cfgOverride) window.NX_INTELLIGENCE_CONFIG = Object.assign({}, window.NX_INTELLIGENCE_CONFIG, cfgOverride);
            if (window.NX_INTELLIGENCE_PANEL) window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [env_override, intel_config_override, allowed_modules]
    )
    page.wait_for_selector(".fNavItem", timeout=8000)


def open_panel(page):
    launcher = page.locator("#baiLauncherBtn")
    assert launcher.count() == 1, "Living Core launcher missing -- cannot proceed"
    launcher.click(position={"x": 13, "y": 10}, force=True)
    page.wait_for_timeout(400)


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []

    # ============================================================
    # 0. STATIC CONFIG PROOF -- no browser needed. Confirms the exact,
    # single file this wave changed, and that no secret was introduced
    # anywhere in the tracked frontend bundle this test can reach.
    # ============================================================
    cfg_path = os.path.join(V2_ROOT, "assets", "js", "intelligence-runtime-config.production.js")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg_source = f.read()
    check("0. voiceRealtimeEndpoint is non-null in the production config file", "voiceRealtimeEndpoint: 'https://" in cfg_source)
    check("0. voiceRealtimeEndpoint targets portal-realtime-homolog specifically", "functions/v1/portal-realtime-homolog'" in cfg_source)
    check("0. voiceRealtimeEndpoint derived from the SAME supabaseUrl as textEndpoint (one project)", "yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-realtime-homolog" in cfg_source)

    secret_patterns = [re.compile(r"sk-[A-Za-z0-9]{20,}"), re.compile(r"sb_secret_"), re.compile(r"service_role", re.I)]
    leaked = [p.pattern for p in secret_patterns if p.search(cfg_source)]
    check("0. no OpenAI-key-shaped or service-role-shaped string in the production config file", len(leaked) == 0, leaked)

    for fname in ["intelligence-runtime-config.js", "index.html"]:
        with open(os.path.join(V2_ROOT, fname if fname == "index.html" else os.path.join("assets", "js", fname)), "r", encoding="utf-8") as f:
            src = f.read()
        leaked = [p.pattern for p in secret_patterns if p.search(src)]
        check(f"0. no secret-shaped string in {fname}", len(leaked) == 0, leaked)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def tracked_page(**kw):
            pg = browser.new_page(**kw)
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(str(e)))
            return pg

        # ============================================================
        # 1. GITHUB-PAGES-HOMOLOG RUNTIME SHAPE -- Voice control
        # initializes, request construction proven, fails safely.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        env = {"name": "AUTHORIZED_PRODUCTION", "hostname": "luisgamadio-spec.github.io", "allowed": True, "production": True}
        cfg = {
            "mode": "real_text",
            "textEndpoint": REAL_TEXT_ENDPOINT,
            "voiceRealtimeEndpoint": REAL_VOICE_ENDPOINT,
            "supabasePublishableKey": REAL_ANON_KEY,
            "supabaseUrl": "https://yacqlelpzchcotgngwbh.supabase.co",
            "authorizedHostnames": ["luisgamadio-spec.github.io"]
        }
        open_landing_as_vendedor(page, env, cfg)
        open_panel(page)

        cfg_seen = page.evaluate("window.NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint")
        check("1. window.NX_INTELLIGENCE_CONFIG.voiceRealtimeEndpoint resolves to the real endpoint at runtime", cfg_seen == REAL_VOICE_ENDPOINT, cfg_seen)

        mounted = page.evaluate("""() => {
            if (window.NX_INTELLIGENCE_VOICE && typeof window.NX_INTELLIGENCE_VOICE.mount === 'function') {
                window.NX_INTELLIGENCE_VOICE.mount();
                return true;
            }
            return false;
        }""")
        check("1. Voice control module (window.NX_INTELLIGENCE_VOICE) is present and mounts without error", mounted is True, mounted)

        # Request-construction + fail-safe proof: stub NX_AUTH with a
        # SYNTHETIC test-only token (never real) and intercept
        # window.fetch, returning a controlled non-OK response for the
        # mint call -- the real doStart() already throws on !resp.ok,
        # BEFORE ever calling getUserMedia/RTCPeerConnection (confirmed
        # by direct read this Wave), so this proves both request
        # correctness and safe failure handling without any fake
        # microphone/audio Human approval.
        page.evaluate("""() => {
            window.__uatCapturedFetch = null;
            window.__origFetch = window.fetch;
            window.fetch = function (url, opts) {
                var u = String(url);
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_voz_habilitada', valor: 'true' }, { chave: 'ia_texto_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                if (u === '%s') {
                    window.__uatCapturedFetch = { url: u, headers: Object.assign({}, opts.headers), body: opts.body };
                    return Promise.resolve(new Response(JSON.stringify({ error: 'stubbed, intentionally not ok' }), { status: 503 }));
                }
                return window.__origFetch(url, opts);
            };
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('uat-synthetic-test-token-not-a-real-credential') };
            window.NX_INTELLIGENCE_VOICE.start();
        }""" % REAL_VOICE_ENDPOINT)
        page.wait_for_timeout(500)
        captured = page.evaluate("window.__uatCapturedFetch")
        voice_state = page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")
        page.evaluate("window.fetch = window.__origFetch")

        check("1. Voice start() calls fetch on the EXACT configured voiceRealtimeEndpoint",
              captured is not None and captured["url"] == REAL_VOICE_ENDPOINT,
              {"url": captured["url"] if captured else None})
        auth_ok = bool(captured) and captured["headers"].get("Authorization") == "Bearer uat-synthetic-test-token-not-a-real-credential"
        check("1. mint request carries Authorization: Bearer <session token> (synthetic test token, never a real credential)", auth_ok)
        body_str = (captured or {}).get("body") or ""
        check("1. mint request body carries NO profile/store/department parameter (matches existing, unmodified bridge)", body_str in ("{}", "", None), body_str)
        check("1. a failed mint is handled safely: voice state lands on VOICE_ERROR (never a crash, never a silent hang)", voice_state == "VOICE_ERROR", voice_state)

        unexplained_1 = [e for e in console_errors if "Failed to load resource" not in e]
        check("1. zero unexplained console/page errors from the Voice start attempt", len(unexplained_1) == 0, unexplained_1[:5])

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("1. zero horizontal scroll (PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE)", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        # ============================================================
        # 1B. TEXT + LIVING CORE REGRESSION -- own fresh page (never
        # reusing the page a Voice start attempt already ran on, so a
        # Voice-triggered UI-state transition can never be mistaken for
        # a Text regression).
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_vendedor(page, env, cfg)
        open_panel(page)
        page.evaluate("""() => {
            window.__uatCapturedFetch2 = null;
            window.fetch = function (url, opts) {
                var u = String(url);
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_texto_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                window.__uatCapturedFetch2 = { url: u, headers: Object.assign({}, opts.headers) };
                return Promise.resolve(new Response(JSON.stringify({ reply: 'stub-reply-text-regression', blocks: null, request_id: 'stub' }), { status: 200 }));
            };
            // sendRealText() reads window.NX_AUTH.getAccessToken() same
            // as Voice's own bridge -- this is a fresh page, never
            // stubbed yet (Section 1's own stub lived on a page already
            // closed above).
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('uat-synthetic-test-token-not-a-real-credential') };
        }""")
        page.locator("#baiPanelInput").fill("Qual foi o resultado do mes passado?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_timeout(700)
        captured2 = page.evaluate("window.__uatCapturedFetch2")
        check("1B. Text composer still reaches portal-ai-homolog unaffected (parity, no regression)", captured2 is not None and captured2["url"] == REAL_TEXT_ENDPOINT, captured2)
        conv_text = page.locator("#baiPanelConversation").inner_text()
        check("1B. Living Core conversation surface still renders the reply", "stub-reply-text-regression" in conv_text, conv_text[:200])
        page.close()

        # ============================================================
        # 2. NO-SESSION FAIL-CLOSED -- getAccessToken() resolves falsy
        # -> immediate VOICE_ERROR, fetch never attempted.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_vendedor(page, env, cfg)
        open_panel(page)
        page.evaluate("""() => {
            window.__uatCapturedFetch3 = null;
            window.fetch = function (url, opts) {
                window.__uatCapturedFetch3 = { url: String(url) };
                return window.__origFetch ? window.__origFetch(url, opts) : Promise.reject(new Error('unexpected fetch'));
            };
            window.NX_AUTH = { getAccessToken: () => Promise.resolve(null) };
            window.NX_INTELLIGENCE_VOICE.mount();
            window.NX_INTELLIGENCE_VOICE.start();
        }""")
        page.wait_for_timeout(300)
        voice_state_2 = page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")
        captured3 = page.evaluate("window.__uatCapturedFetch3")
        check("2. no session (getAccessToken -> null) -> VOICE_ERROR, never attempts the mint fetch at all", voice_state_2 == "VOICE_ERROR" and captured3 is None, {"state": voice_state_2, "fetch": captured3})
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors overall", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== VOICE-UAT-1: V2 Homolog Voice Activation ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
