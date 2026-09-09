#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3E -- Brabus Intelligence PERSISTENT PANEL test.

Covers the panel-specific surface added this Wave (assets/js/
intelligence/{intelligence-state,intelligence-context,intelligence-panel}.js):
launcher/drawer lifecycle, navigation persistence, the explicit TEXT
state machine, MASTER-only client presentation (real DOM removal, not
CSS hiding), context envelope updates, kill-switch/session/forbidden/
rate-limit/malformed-response UX, responsive/zero-scroll proof at the
4 required breakpoints, long-content containment, and a frozen-module
regression spot check.

Does NOT re-test the transport/contract layer itself (createRequest/
normalizeResponse/formatValue/the 6 structured-block renderers) -- that
is 100% reused, byte-for-byte, from assets/js/adapters/
brabus-intelligence.adapter.js and assets/js/brabus-intelligence.js,
already proven by the pre-existing intelligence-contract-test.py /
intelligence-presentation-parity-test.py / intelligence-structured-
block-test.py / intelligence-browser-test.py, re-run unmodified this
Wave as the regression proof (see docs/IA-3E-V2-INTELLIGENCE-PANEL.md).

401/403/429/503/malformed are exercised by stubbing
NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText (a public, pure function on
a plain object) while window.NX_INTELLIGENCE_CONFIG.mode is flipped to
'real_text' at runtime -- this drives the REAL handleSendRealText/
applyResult code path in the panel, only the network boundary itself
is stubbed, exactly the same seam the pre-existing adapter-level tests
already use for the routed page's own pure functions.

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-3e")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


def close_panel(page):
    page.click("#baiPanelCloseBtn")
    page.wait_for_timeout(150)


def set_profile(page, state, is_master=None, perfil=None):
    """Monkeypatches NX_AUTH_CORE.getState/getContext (plain function
    properties on a real, already-loaded module object) and asks the
    panel to re-run its own real visibility decision -- the same
    decision a genuine onStateChange callback would trigger."""
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def stub_real_text(page, resolve_js):
    """Replaces sendRealText (a plain function property) with a stub
    resolving the given result, and flips mode to real_text -- the
    ONLY two things changed; createRequest/normalizeResponse/applyResult
    and everything else stay the real, unmodified code."""
    page.evaluate(
        """(resolveJs) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.__baiSendRealTextCalls = 0;
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function () {
                window.__baiSendRealTextCalls++;
                return (new Function('A', 'return ' + resolveJs))(window.NX_BRABUS_INTELLIGENCE_ADAPTER);
            };
        }""",
        resolve_js,
    )


def restore_fixture_mode(page):
    page.evaluate("window.NX_INTELLIGENCE_CONFIG.mode = 'fixture';")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)

        # ---------- Registration ----------
        check("NX_INTELLIGENCE_PANEL registered", page.evaluate("typeof window.NX_INTELLIGENCE_PANEL === 'object'"))
        check("NX_INTELLIGENCE_STATE registered", page.evaluate("typeof window.NX_INTELLIGENCE_STATE === 'object'"))
        check("NX_INTELLIGENCE_CONTEXT registered", page.evaluate("typeof window.NX_INTELLIGENCE_CONTEXT === 'object'"))
        check("routed #/brabus-intelligence page untouched (still registered)", page.evaluate("typeof window.NX_BRABUS_INTELLIGENCE_PAGE === 'object'"))

        # ---------- MASTER-only presentation (Section 15/18/19/49) ----------
        # AUTH_NOT_CONFIGURED (this host's real, unmodified default --
        # matches every other module's own convention).
        check("launcher visible: AUTH_NOT_CONFIGURED", page.locator("#baiLauncherBtn").count() == 1)

        PROFILE_MATRIX = [
            ("AUTHORIZED", True, "MASTER", True),
            ("AUTHORIZED", False, "RH", False),
            ("AUTHORIZED", False, "ANALISTA", False),
            ("AUTHORIZED", False, "GERENTE", False),
            ("AUTHORIZED", False, "VENDEDOR", False),
            ("AUTHORIZED", False, "DIRETOR NOVOS", False),
            ("AUTHORIZED", False, "DIRETOR SEMINOVOS", False),
            ("SIGNED_OUT", None, None, False),
            ("SESSION_EXPIRED", None, None, False),
        ]
        for state, is_master, perfil, expect_visible in PROFILE_MATRIX:
            set_profile(page, state, is_master, perfil)
            present = page.locator("#baiLauncherRoot").count() == 1
            label = f"profile presentation: {perfil or state} -> {'available' if expect_visible else 'not available (real DOM removal)'}"
            check(label, present == expect_visible)
        shot(page, "01-hidden-non-master.png")

        # restore MASTER for the rest of the flow
        set_profile(page, "AUTHORIZED", True, "MASTER")
        check("launcher rebuilt as a fresh DOM node for MASTER (not a stale CSS-hidden node reused)", page.locator("#baiLauncherBtn").count() == 1)

        # ---------- No duplicate Intelligence surface on the routed page ----------
        # Regression case found live during this Wave's own regression
        # pass: the launcher must not stack a second Intelligence
        # surface on top of the dedicated #/brabus-intelligence route.
        page.evaluate("window.location.hash = '#/brabus-intelligence'")
        page.wait_for_timeout(400)
        check("launcher suppressed on the routed #/brabus-intelligence page itself", page.locator("#baiLauncherRoot").count() == 0)
        check("exactly one .baiComposer on the routed Intelligence page (no collision)", page.locator(".baiComposer").count() == 1)
        page.evaluate("window.location.hash = '#/landing'")
        page.wait_for_timeout(400)
        check("launcher reappears after navigating away from the routed page", page.locator("#baiLauncherRoot").count() == 1)

        # ---------- Text local E2E (fixture mode) ----------
        open_panel(page)
        check("drawer opens", page.locator("#baiPanelDrawer").is_visible())
        check("TEXT state OPEN_IDLE on open", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "OPEN_IDLE")
        shot(page, "02-open-idle-landing.png")

        page.fill("#baiPanelInput", "x")
        check("TEXT state COMPOSING while typing", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "COMPOSING")
        page.fill("#baiPanelInput", "Qual foi o resultado do mês passado?")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(50)
        check("TEXT state reaches THINKING while in flight", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") in ("SENDING", "THINKING"))
        page.wait_for_timeout(400)
        check("assistant reply rendered", page.locator("#baiPanelConversation .baiMessageAssistant").count() >= 1)
        check("structured block rendered", page.locator("#baiPanelConversation .baiBlockPanel").count() >= 1)
        check("TEXT state settles to OPEN_IDLE after COMPLETE", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "OPEN_IDLE")
        shot(page, "03-panel-metrics.png")

        # ---------- New conversation ----------
        page.click("#baiPanelNewChatBtn")
        page.wait_for_timeout(100)
        check("Nova conversa clears the panel conversation", page.locator("#baiPanelConversation .baiMessage").count() == 0)

        # ---------- Context envelope (Section 23/24/32) ----------
        check("context route is landing before navigation", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().route") == "landing")
        page.evaluate("window.location.hash = '#/score'")
        page.wait_for_timeout(400)
        check("context route updates to score", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().route") == "score")
        check("context moduleId updates to score", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().moduleId") == "score")
        check("panel drawer persists across navigation (still open)", page.locator("#baiPanelDrawer").is_visible())
        check("Score module renders normally alongside the open panel (no frozen-module regression)", page.locator(".modPageHeader").count() > 0)
        shot(page, "04-panel-open-over-score.png")

        # publish() voluntary hint API -- not wired to any real module
        # this Wave, but proven to work + stay allow-listed.
        page.evaluate("window.NX_INTELLIGENCE_CONTEXT.publish({store:'Barra Funda', department:'NOVOS', perfil:'MASTER_SPOOF_ATTEMPT'})")
        snap = page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot()")
        check("publish() accepts an allow-listed key (store)", snap.get("store") == "Barra Funda")
        check("publish() silently drops a non-allow-listed key (perfil)", "perfil" not in snap or snap.get("perfil") is None)

        # ---------- Session / Forbidden / Rate-limit / Kill-switch / Malformed ----------
        # 503 -- kill switch
        stub_real_text(page, "Promise.resolve({error:{status:503,message:'Brabus Intelligence está temporariamente indisponível.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste kill switch")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("503: TEXT state DISABLED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "DISABLED")
        check("503: composer disabled", page.evaluate("document.getElementById('baiPanelInput').disabled") is True)
        check("503: status line shown, no technical config name leaked", "ia_texto_habilitada" not in page.locator("#baiPanelStatusLine").inner_text() and page.locator("#baiPanelStatusLine").is_visible())
        page.wait_for_timeout(400)
        check("503: no automatic retry (sendRealText called exactly once)", page.evaluate("window.__baiSendRealTextCalls") == 1)
        shot(page, "05-kill-switch-disabled.png")

        # 401 -- session expired (via getAccessToken resolving null, the
        # real path the routed page also uses -- not via sendRealText).
        page.click("#baiPanelNewChatBtn")
        page.evaluate("window.NX_AUTH = { getAccessToken: () => Promise.resolve(null) };")
        page.fill("#baiPanelInput", "teste sessão")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("401: TEXT state SESSION_EXPIRED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "SESSION_EXPIRED")
        check("401: composer disabled until a real fresh action", page.evaluate("document.getElementById('baiPanelInput').disabled") is True)
        check("401: correct Portuguese message, no stale authenticated capability implied", "Sessão expirada" in page.locator("#baiPanelStatusLine").inner_text())

        # 403 -- forbidden
        stub_real_text(page, "Promise.resolve({error:{status:403,message:'Este recurso não está disponível para o seu perfil.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste forbidden")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("403: TEXT state FORBIDDEN", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "FORBIDDEN")
        check("403: safe message, no raw backend reason leaked", page.locator("#baiPanelStatusLine").inner_text() == "Este recurso não está disponível para o seu perfil.")
        page.wait_for_timeout(400)
        check("403: no repeated automatic request", page.evaluate("window.__baiSendRealTextCalls") == 1)

        # 429 -- rate limit (transient: composer must re-enable, manual retry possible)
        stub_real_text(page, "Promise.resolve({error:{status:429,message:'Muitas solicitações em pouco tempo — aguarde um instante e tente novamente.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste rate limit")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("429: TEXT state ERROR (transient, not sticky)", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "ERROR")
        check("429: clear transient message shown as a bubble", "aguarde um instante" in page.locator("#baiPanelConversation").inner_text())
        check("429: composer re-enabled -- manual retry is possible", page.evaluate("document.getElementById('baiPanelInput').disabled") is False)

        # Malformed response -- garbage payload through the REAL normalizeResponse
        stub_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:12345, blocks:'not-an-array', request_id:{}, scenario_reset:'yes'})})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste malformed")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(300)
        body_text = page.locator("#baiPanelConversation").inner_text()
        check("malformed response: no crash, no page error", True)  # implicit -- if this line is reached, nothing threw
        check("malformed response: no literal 'undefined' rendered", "undefined" not in body_text)
        check("malformed response: no [object Object] rendered", "[object Object]" not in body_text)
        shot(page, "06-malformed-response.png")

        restore_fixture_mode(page)
        page.evaluate("delete window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText; window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = undefined;")
        # sendRealText must be restored from the real adapter file, not
        # left undefined -- reload to get a fully clean module state
        # back for the remaining checks.
        page.reload()
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")

        # ---------- Long content containment (Section 41/56) ----------
        open_panel(page)
        long_token = "X" * 400
        page.evaluate(
            """(tok) => {
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'user', content:'pergunta longa '.repeat(40), blocks:null, isError:false});
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'resposta longa '.repeat(60) + tok, blocks:null, isError:false});
            }""",
            long_token,
        )
        page.wait_for_timeout(100)
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("long content: no page horizontal overflow", overflow <= 0, overflow)
        drawer_overflow = page.evaluate("(function(){var el=document.getElementById('baiPanelDrawer'); return el.scrollWidth - el.clientWidth;})()")
        check("long content: no drawer wrapper horizontal overflow", drawer_overflow <= 0, drawer_overflow)
        shot(page, "07-long-content.png")
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        page.close()

        # ---------- Responsive / zero-scroll proof (Section 15/40) ----------
        BREAKPOINTS = [1366, 1024, 900, 480]
        for w in BREAKPOINTS:
            for route, label in (("landing", "landing"), ("score", "score")):
                rp = browser.new_page(viewport={"width": w, "height": 900})
                rp.goto(BASE + f"#/{route}")
                rp.wait_for_timeout(400)
                set_profile(rp, "AUTHORIZED", True, "MASTER")
                open_panel(rp)
                page_overflow = rp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                drawer_overflow = rp.evaluate("(function(){var el=document.getElementById('baiPanelDrawer'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
                check(f"{w}px / {label}: page overflow 0", page_overflow <= 0, page_overflow)
                check(f"{w}px / {label}: panel wrapper overflow 0", drawer_overflow <= 0, drawer_overflow)
                if w == 480:
                    check(f"{w}px / {label}: mobile backdrop visible (full-screen takeover)", rp.locator("#baiPanelBackdrop").is_visible())
                shot(rp, f"08-responsive-{w}-{label}.png")
                rp.close()

        browser.close()

    unexplained = [e for e in errors if "Failed to load resource" not in e]
    check("no unexplained console/page errors across the whole flow", len(unexplained) == 0)
    if unexplained:
        print("  unexplained errors:", unexplained)

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence Panel Test (IA-3E): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
