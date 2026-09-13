#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEC-1C.3 -- Human UAT found the Living Core panel (now correctly
visible for real ANALISTA, per SEC-1C.2) still answering from LOCAL
FIXTURE data on the published homologation
(https://luisgamadio-spec.github.io/portal-fi-v2/), never reaching the
real, deployed portal-ai-homolog -- a false-positive-security-UAT risk:
the panel looked fully functional and answered every question,
including the adversarial ones, from synthetic data.

Root cause: assets/js/intelligence-runtime-config.production.js (the
ONLY config file loaded on that exact hostname) deliberately shipped
mode: 'fixture' / textEndpoint: null since an earlier wave (GL-1 Gate
17), pending "a separate, later, explicitly-authorized Go-Live gate for
Intelligence specifically" -- this wave IS that gate. Fixed by flipping
those two fields (voiceRealtimeEndpoint stays null -- Voice is
untouched, still MASTER-only, still a separate later gate).

This file proves, without ever authenticating for real (no real
Camile/luuis.guga session is used or fabricated -- SEC-1C's own
standing prohibition), three required states:

  1. GITHUB-PAGES-HOMOLOG RUNTIME SHAPE (NX_ENVIRONMENT=
     AUTHORIZED_PRODUCTION + the real production config's own
     mode/textEndpoint) -> real provider selected, fixture banner
     absent, request construction proven correct (endpoint +
     Authorization header), all without a real backend round trip.

  2. EXPLICIT LOCAL FIXTURE MODE (NX_ENVIRONMENT=LOCAL_DEV, mode left
     at the committed 'fixture' default) -> fixture still works exactly
     as before, unaffected by this wave's fail-closed addition.

  3. BROKEN/MISCONFIGURED HOMOLOG (NX_ENVIRONMENT=AUTHORIZED_PRODUCTION
     but mode/textEndpoint NOT correctly wired) -> fails CLOSED: a
     visible "indisponível" message, in both the drawer and the routed
     page, and sending a message never reaches fixture data.

Uses the same direct-index.html-load, real-runtime-machinery technique
as SEC-1C.2's own test (never a hash-navigation shortcut, never a
hand-copied duplicate of environment-guard.js's own hostname logic --
only NX_ENVIRONMENT/NX_INTELLIGENCE_CONFIG themselves are substituted,
exactly what a real host's own script tags would have produced).

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "sec1c3")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"

REAL_TEXT_ENDPOINT = "https://yacqlelpzchcotgngwbh.supabase.co/functions/v1/portal-ai-homolog"
REAL_ANON_KEY = "sb_publishable__J96gDH1kOqlc4iFW24Z2Q_u_lWAg5_"  # public by design, matches committed config

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


def open_landing_as_analista(page, env_override, intel_config_override):
    """Direct index.html load, real NX_AUTH_CORE/NX_REGISTRY/
    NX_INTELLIGENCE_PANEL machinery -- only the bootstrap accessors and
    the two environment/config globals are substituted for what a real
    host would have produced (mirrors SEC-1C.2's own technique, plus
    NX_ENVIRONMENT/NX_INTELLIGENCE_CONFIG this wave newly needs)."""
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    allowed_modules = ["analiseScoreVendedores", "comissoes", "coparticipadoPortal", "dashbi", "gestao", "simuladorCompleto", "simuladorSeminovos"]
    page.evaluate(
        """([envOverride, cfgOverride, allowedModuleIds]) => {
            // buildPanelDom() (intelligence-panel.js) only ever builds the
            // drawer's own HTML (including the provenance banner /
            // data-nx-transport, both config-dependent) ONCE per DOM
            // instance -- guarded by its own private `panelBuilt` flag,
            // which only ITS OWN removal branch inside refreshVisibility()
            // resets. Since the launcher was already built once at real
            // page bootstrap (before this override), force a genuine
            // unauthorized->authorized transition -- the SAME real
            // sequence window.NX_AUTH_CORE.onStateChange drives in
            // production (e.g. a session expiring then a new one
            // starting) -- so refreshVisibility()'s own removal branch
            // runs first (clearing panelBuilt for real), THEN the desired
            // override rebuilds fresh. Never a hand-copied duplicate of
            // that internal state, and never a DOM removal this module's
            // own code didn't itself perform.
            window.NX_AUTH_CORE.getState = () => 'SIGNED_OUT';
            window.NX_AUTH_CORE.getContext = () => null;
            if (window.NX_INTELLIGENCE_PANEL) window.NX_INTELLIGENCE_PANEL.refresh();

            window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
            window.NX_AUTH_CORE.getContext = () => Object.freeze({
                isMaster: false, perfil: 'ANALISTA', allowedModuleIds,
                nome: 'UAT ANALISTA', loja: 'NACOES', status: 'NOVOS/SEMINOVOS'
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
    assert launcher.count() == 1, "Living Core launcher missing -- cannot proceed (see SEC-1C.2)"
    launcher.click(position={"x": 13, "y": 10}, force=True)
    page.wait_for_timeout(400)


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def tracked_page(**kw):
            pg = browser.new_page(**kw)
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(str(e)))
            return pg

        # ============================================================
        # 1. GITHUB-PAGES-HOMOLOG RUNTIME SHAPE -- real provider
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        env = {"name": "AUTHORIZED_PRODUCTION", "hostname": "luisgamadio-spec.github.io", "allowed": True, "production": True}
        cfg = {
            "mode": "real_text",
            "textEndpoint": REAL_TEXT_ENDPOINT,
            "supabasePublishableKey": REAL_ANON_KEY,
            "supabaseUrl": "https://yacqlelpzchcotgngwbh.supabase.co",
            "authorizedHostnames": ["luisgamadio-spec.github.io"]
        }
        open_landing_as_analista(page, env, cfg)
        open_panel(page)
        shot(page, "1-real-homolog-shape-open.png")

        is_real = page.evaluate("window.NX_BRABUS_INTELLIGENCE_PAGE.isRealTextMode()")
        is_misconfigured = page.evaluate("window.NX_BRABUS_INTELLIGENCE_PAGE.isHomologMisconfigured()")
        check("1. GH-Pages-homolog shape: isRealTextMode() true", is_real is True, is_real)
        check("1. GH-Pages-homolog shape: isHomologMisconfigured() false", is_misconfigured is False, is_misconfigured)

        transport_attr = page.get_attribute("#baiPanelDrawer", "data-nx-transport")
        check("1. drawer data-nx-transport = real_text", transport_attr == "real_text", transport_attr)

        banner_count = page.locator("#baiPanelProvenanceBanner").count()
        check("1. local-test/misconfigured banner ABSENT", banner_count == 0, banner_count)

        page_html = page.content()
        check("1. 'Modo de teste local' text absent from the DOM", "Modo de teste local" not in page_html)
        check("1. 'indisponível' text absent from the DOM (not misconfigured)", "indisponível" not in page_html.lower())

        # Request-construction proof (Section 15): stub NX_AUTH with a
        # SYNTHETIC, test-only token constant (never a real credential,
        # never printed) and intercept window.fetch to prove the real
        # adapter builds the exact right request -- endpoint +
        # Authorization header -- without ever making a real network
        # call (fetch is intercepted and short-circuited before any
        # real request leaves the browser).
        page.evaluate("""() => {
            window.__uatCapturedFetch = null;
            window.__origFetch = window.fetch;
            window.fetch = function (url, opts) {
                var u = String(url);
                // The panel's own client-side kill-switch pre-check
                // (isTextSurfaceEnabled(), via NX_MASTER_CONFIG_PROVIDER)
                // fires a REAL RPC call (operational_portal_config)
                // BEFORE sendRealText's own fetch -- must be answered
                // with a shape it accepts (ia_texto_habilitada=true) or
                // the panel fails closed and sendRealText never runs at
                // all. Only the ACTUAL target request (the real
                // textEndpoint) is captured for this test's own
                // assertions; every other fetch (this pre-check
                // included) gets whatever stub keeps the real flow
                // moving, never the captured one.
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_texto_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                window.__uatCapturedFetch = { url: u, headers: Object.assign({}, opts.headers) };
                return Promise.resolve(new Response(JSON.stringify({ reply: 'stub', blocks: null, request_id: 'stub' }), { status: 200 }));
            };
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('uat-synthetic-test-token-not-a-real-credential') };
        }""")
        page.locator("#baiPanelInput").fill("Qual foi o resultado do mês passado?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_timeout(700)
        captured = page.evaluate("window.__uatCapturedFetch")
        page.evaluate("window.fetch = window.__origFetch")

        check("1. real request targets portal-ai-homolog (not portal-ai, not fixture)",
              captured is not None and captured["url"] == REAL_TEXT_ENDPOINT,
              {"url": captured["url"] if captured else None})
        auth_header_present = bool(captured) and captured["headers"].get("Authorization") == "Bearer uat-synthetic-test-token-not-a-real-credential"
        check("1. request carries Authorization: Bearer <current session token> (synthetic test token, never a real credential)", auth_header_present)
        check("1. apikey header present (established config value, not duplicated)", bool(captured) and captured["headers"].get("apikey") == REAL_ANON_KEY)

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("1. zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        # ============================================================
        # 2. EXPLICIT LOCAL FIXTURE MODE -- unaffected by this wave
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        env = {"name": "LOCAL_DEV", "hostname": "127.0.0.1", "allowed": True, "production": False}
        cfg = {"mode": "fixture", "textEndpoint": None}
        open_landing_as_analista(page, env, cfg)
        open_panel(page)

        is_misconfigured = page.evaluate("window.NX_BRABUS_INTELLIGENCE_PAGE.isHomologMisconfigured()")
        check("2. LOCAL_DEV + fixture mode: isHomologMisconfigured() false (legitimate dev state)", is_misconfigured is False, is_misconfigured)
        transport_attr = page.get_attribute("#baiPanelDrawer", "data-nx-transport")
        check("2. drawer data-nx-transport = fixture", transport_attr == "fixture", transport_attr)
        banner_text = page.locator("#baiPanelProvenanceBanner").inner_text() if page.locator("#baiPanelProvenanceBanner").count() else ""
        check("2. fixture banner present and reads the expected local-test copy", "Modo de teste local" in banner_text, banner_text)

        page.locator("#baiPanelInput").fill("Qual foi o resultado do mês passado?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_timeout(1000)
        conv_text = page.locator("#baiPanelConversation").inner_text()
        check("2. fixture mode still answers from local fixture data (unaffected by this wave)", "13 vendas" in conv_text or "financiamentos" in conv_text, conv_text[:200])
        page.close()

        # ============================================================
        # 3. BROKEN/MISCONFIGURED HOMOLOG -- fail CLOSED
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        env = {"name": "AUTHORIZED_PRODUCTION", "hostname": "luisgamadio-spec.github.io", "allowed": True, "production": True}
        cfg = {"mode": "fixture", "textEndpoint": None}  # the EXACT prior-published defect, reproduced deliberately
        open_landing_as_analista(page, env, cfg)
        open_panel(page)
        shot(page, "3-misconfigured-open.png")

        is_misconfigured = page.evaluate("window.NX_BRABUS_INTELLIGENCE_PAGE.isHomologMisconfigured()")
        check("3. AUTHORIZED_PRODUCTION + mode=fixture: isHomologMisconfigured() true", is_misconfigured is True, is_misconfigured)
        transport_attr = page.get_attribute("#baiPanelDrawer", "data-nx-transport")
        check("3. drawer data-nx-transport = misconfigured", transport_attr == "misconfigured", transport_attr)
        banner_text = page.locator("#baiPanelProvenanceBanner").inner_text() if page.locator("#baiPanelProvenanceBanner").count() else ""
        check("3. visible fail-closed message shown (never silent)", "indisponível" in banner_text.lower(), banner_text)

        page.locator("#baiPanelInput").fill("Qual foi o resultado do mês passado?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_timeout(700)
        conv_text = page.locator("#baiPanelConversation").inner_text()
        check("3. sending does NOT return fixture data", "13 vendas" not in conv_text, conv_text[:200])
        check("3. sending returns the same visible fail-closed message as a conversation bubble", "indisponível" in conv_text.lower(), conv_text[:200])
        shot(page, "3-misconfigured-after-send.png")
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== SEC-1C.3: Real Provider Selection ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
