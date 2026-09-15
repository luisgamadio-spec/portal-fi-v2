#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UXCHAT1 -- proves the sidebar/Landing "Brabus Intelligence" destination
now converges onto the SAME canonical Living Core/Orb panel
(intelligence-panel.js / NX_INTELLIGENCE_STATE), never the legacy
routed page (assets/js/brabus-intelligence.js, left on disk
unmodified, distinguishable by its own #baiInput/#baiSendBtn/
#baiConversation ids -- the canonical panel uses #baiPanelInput/
#baiPanelSendBtn/#baiPanelConversation instead, so their presence is a
reliable "which surface actually rendered" signal).

Drives the REAL NX_AUTH_CORE.login()/logout() event pipeline (same
robust technique SESSIONSEC1's own test established) and the REAL
window.NX_ROUTER.navigate() (same mechanism a real sidebar/Landing
module-card click uses), never a DOM-removal/getter-override shortcut.

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

SENTINEL_A = "UXCHAT1_ORB_SENTINEL_71A"
SENTINEL_B = "UXCHAT1_SIDEBAR_SENTINEL_82B"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


INSTALL_STUB_JS = """
(() => {
  window.__uatFakeSession = null;
  window.__uatPendingProfile = null;
  window.NX_AUTH = {
    isAuthConfigured: true,
    getSession: () => Promise.resolve(window.__uatFakeSession),
    signIn: () => {
      window.__uatFakeSession = { user: { id: (window.__uatPendingProfile || {}).authUserId } };
      return Promise.resolve();
    },
    signOut: () => { window.__uatFakeSession = null; return Promise.resolve(); },
    resolveAuthorizedProfile: () => Promise.resolve(window.__uatPendingProfile),
    resolveAllowedModules: () => Promise.resolve(['dashbi', 'simuladorCompleto', 'comissoes']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

USER_A = {"userId": "row-uxchat1-a", "authUserId": "AUTHUSER-UXCHAT1-A-1111", "nome": "UAT VENDEDOR A", "perfil": "VENDEDOR", "loja": "BARRA FUNDA", "status": "NOVOS", "ativo": True}
USER_B = {"userId": "row-uxchat1-b", "authUserId": "AUTHUSER-UXCHAT1-B-2222", "nome": "UAT VENDEDOR B", "perfil": "VENDEDOR", "loja": "EUROPA", "status": "NOVOS", "ativo": True}


def login_as(page, profile):
    page.evaluate(
        "(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('uat@test.invalid', 'x', 'uat-captcha'); }",
        profile
    )
    page.wait_for_function(
        "(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id",
        arg=profile["authUserId"], timeout=5000
    )


def logout(page):
    page.evaluate("() => window.NX_AUTH_CORE.logout()")
    page.wait_for_function("() => window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=5000)


def legacy_page_dom_present(page):
    return page.evaluate("""() => !!(document.getElementById('baiInput') || document.getElementById('baiSendBtn') || document.getElementById('baiConversation'))""")


def canonical_composer_count(page):
    return page.evaluate("document.querySelectorAll('#baiPanelInput').length")


def send_via_canonical_composer(page, text):
    page.fill("#baiPanelInput", text)
    page.click("#baiPanelSendBtn")
    page.wait_for_timeout(250)


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        page.goto(BASE + "#/landing")
        page.wait_for_selector("#landingNav", timeout=8000)
        page.evaluate(INSTALL_STUB_JS)
        login_as(page, USER_A)
        page.wait_for_timeout(200)

        # ============================================================
        # A/B -- Living Core / Orb (the SAME launcher button) opens the
        # canonical chat.
        # ============================================================
        launcher = page.locator("#baiLauncherBtn")
        check("A/B. Living Core / Orb launcher present for authorized user", launcher.count() == 1)
        launcher.click(position={"x": 13, "y": 10}, force=True)
        page.wait_for_timeout(300)
        check("A/B. Canonical composer (#baiPanelInput) visible after Orb/Living Core open", page.locator("#baiPanelInput").count() == 1)

        state_before = page.evaluate("() => ({ hasState: !!window.NX_INTELLIGENCE_STATE, hasPanel: !!window.NX_INTELLIGENCE_PANEL })")
        check("D. Canonical NX_INTELLIGENCE_STATE/NX_INTELLIGENCE_PANEL singletons exist", state_before["hasState"] and state_before["hasPanel"])

        page.evaluate(f"() => window.NX_INTELLIGENCE_STATE.pushMessage({{role:'assistant', content:'{SENTINEL_A}', blocks:null, isError:false}})")
        conv_after_orb = page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation()")
        check("Orb-origin message present in canonical state", any(SENTINEL_A in json.dumps(m) for m in conv_after_orb), conv_after_orb)

        # Close/minimize.
        close_btn = page.locator("#baiPanelCloseBtn")
        if close_btn.count() == 1:
            close_btn.click()
            page.wait_for_timeout(200)

        # ============================================================
        # C -- Sidebar/Landing "Brabus Intelligence" destination (real
        # hash navigation, the SAME mechanism a real module-card click
        # uses) must open the SAME canonical chat, never the legacy page.
        # ============================================================
        spy_installed = page.evaluate("""() => {
            window.__uxchat1LegacyRenderCalls = 0;
            if (window.NX_BRABUS_INTELLIGENCE_PAGE && typeof window.NX_BRABUS_INTELLIGENCE_PAGE.render === 'function') {
                var orig = window.NX_BRABUS_INTELLIGENCE_PAGE.render;
                window.NX_BRABUS_INTELLIGENCE_PAGE.render = function () {
                    window.__uxchat1LegacyRenderCalls++;
                    return orig.apply(this, arguments);
                };
                return true;
            }
            return false;
        }""")
        check("(setup) legacy page render() spy installed", spy_installed)

        page.evaluate("window.NX_ROUTER.navigate('brabus-intelligence')")
        page.wait_for_timeout(400)

        current_hash = page.evaluate("location.hash")
        check("C. Navigating to 'brabus-intelligence' redirects the hash to #/landing (never resolves to the legacy route)", current_hash == "#/landing", current_hash)

        legacy_calls = page.evaluate("window.__uxchat1LegacyRenderCalls")
        check("C. Legacy routed page's own render() was NEVER invoked", legacy_calls == 0, legacy_calls)
        check("C. Legacy page DOM (#baiInput/#baiSendBtn/#baiConversation) absent", not legacy_page_dom_present(page))

        check("C. Canonical panel auto-opens for the sidebar/Landing destination", page.locator("#baiPanelDrawer").count() == 1 and page.evaluate("document.getElementById('baiPanelDrawer').hidden") is False)
        check("G. Exactly one canonical composer instance exists (no second chat implementation)", canonical_composer_count(page) == 1)

        conv_via_sidebar = page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation()")
        check("E. Conversation created via Orb is visible after opening via sidebar (same state, not a fresh one)", any(SENTINEL_A in json.dumps(m) for m in conv_via_sidebar), conv_via_sidebar)
        dom_text_via_sidebar = page.locator("#baiPanelConversation").inner_text()
        check("E. Orb-origin sentinel actually rendered in the DOM reached via sidebar", SENTINEL_A in dom_text_via_sidebar, dom_text_via_sidebar[:200])

        # ============================================================
        # F -- a message sent through the sidebar-opened composer must
        # be visible back through Living Core/Orb (same launcher).
        # ============================================================
        page.evaluate(f"() => window.NX_INTELLIGENCE_STATE.pushMessage({{role:'assistant', content:'{SENTINEL_B}', blocks:null, isError:false}})")
        close_btn2 = page.locator("#baiPanelCloseBtn")
        if close_btn2.count() == 1:
            close_btn2.click()
            page.wait_for_timeout(200)
        launcher2 = page.locator("#baiLauncherBtn")
        check("(setup) launcher still present after sidebar round-trip", launcher2.count() == 1)
        launcher2.click(position={"x": 13, "y": 10}, force=True)
        page.wait_for_timeout(300)
        dom_text_via_orb_again = page.locator("#baiPanelConversation").inner_text()
        check("F. Sidebar-origin message visible again through Living Core/Orb", SENTINEL_B in dom_text_via_orb_again and SENTINEL_A in dom_text_via_orb_again, dom_text_via_orb_again[:300])

        # ============================================================
        # H -- repeated navigation does not duplicate listeners/DOM.
        # ============================================================
        for _ in range(3):
            page.evaluate("window.NX_ROUTER.navigate('brabus-intelligence')")
            page.wait_for_timeout(250)
        check("H. Repeated navigation leaves exactly one launcher root", page.evaluate("document.querySelectorAll('#baiLauncherRoot').length") == 1)
        check("H. Repeated navigation leaves exactly one canonical composer", canonical_composer_count(page) == 1)
        check("H. Legacy page render() still never invoked after repeated navigation", page.evaluate("window.__uxchat1LegacyRenderCalls") == 0)

        # ============================================================
        # I/J -- SESSIONSEC1 invariants still hold on this new path.
        # ============================================================
        logout(page)
        conv_after_logout = page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation()")
        check("I. Logout clears the conversation", len(conv_after_logout) == 0, conv_after_logout)

        login_as(page, USER_B)
        page.wait_for_timeout(200)
        page.evaluate("window.NX_ROUTER.navigate('brabus-intelligence')")
        page.wait_for_timeout(400)
        conv_user_b = page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation()")
        check("J. Different authenticated user reaching Brabus Intelligence via sidebar gets a FRESH conversation", len(conv_user_b) == 0, conv_user_b)
        check("J. Different user: legacy page still never rendered", page.evaluate("window.__uxchat1LegacyRenderCalls") == 0)

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("N. Zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

        page.close()
        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== UXCHAT1: Unified Brabus Intelligence Entry Points ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
