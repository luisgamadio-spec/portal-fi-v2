#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-R2C.1 -- Brabus Intelligence PRE-DISPATCH AVAILABILITY-GATE RECOVERY.

Human UAT of IA-R2B.1 (22/09/2026) reproduced R2-FINDING-04 twice in two
complete-sequence attempts: after a working turn (or turns), the very
next submit immediately showed "Brabus Intelligence esta temporariamente
indisponivel.", with the composer/send button disabled and NO recovery
after 90+ seconds -- and an external HTTP capture harness proved ZERO
new network requests were dispatched for that turn. Only "Nova conversa"
(a full conversation reset) restored the composer, which defeats the
requirement that B1-B4 run in ONE continuous conversation.

Forensic trace (this wave) against the REAL, unmodified
assets/js/intelligence/intelligence-panel.js proved the exact mechanism:
isTextSurfaceEnabled() (IA-3H.1C.4/D14) is a client-side pre-flight gate,
called on EVERY real send BEFORE sendRealText()/fetch()/AbortController
are ever created. It reads window.NX_MASTER_CONFIG_PROVIDER.readConfig()
and resolves a plain boolean -- but ITS OWN rejection handler
(`function () { return false; }`) collapses TWO semantically different
outcomes into the exact same `false`:
  (a) a CONFIRMED row saying ia_texto_habilitada='false' (a genuine,
      deliberate admin kill-switch) -- already covered, deliberately, by
      the existing intelligence-recovery-hardening-test.py TEST 3, which
      explicitly asserts the composer STAYS locked (DISABLED, Nova
      conversa required) for this case. That test's own assertion proves
      this is INTENTIONAL, approved product behavior -- not a bug, and
      NOT reopened by this wave.
  (b) an INDETERMINATE failure to even check the flag (readConfig()
      rejects: transient network blip, NX_MASTER_CONFIG_PROVIDER not yet
      ready, getAccessToken() hiccup, RPC timeout) -- which has NO
      relationship to the admin's actual intent, yet reaches the exact
      same handleSendRealText() `if (!enabled)` branch, which hardcodes
      status:503 -> TEXT_STATES.DISABLED -- the SAME sticky, deliberately
      non-auto-recovering lock as (a), requiring Nova conversa.

D.2 (IA-MEGAUAT-WAVED2, commit e1f4c30) does not protect against this:
its 180s timeout/AbortController/try-finally render-unlock all live
INSIDE sendRealText()/applyResult()'s success path, which this gate
short-circuits BEFORE reaching -- confirmed directly: TEST A below shows
zero fetch() calls for the failing turn, matching the Human's own
capture-harness evidence exactly.

Uses the SAME harness conventions as tests/intelligence-recovery-
hardening-test.py (stub only the external I/O boundary --
NX_MASTER_CONFIG_PROVIDER.readConfig and window.fetch/sendRealText --
never handleSend/handleSendRealText/applyResult/isTextSurfaceEnabled
themselves, which stay the real, unmodified code under test).

Requires: `python -m http.server <port>` running from a copy of this
worktree with assets/js/intelligence-runtime-config.local.js ABSENT
(same pre-existing D17 requirement as intelligence-recovery-hardening-
test.py -- see that file's own docstring).

Run: python tests/intelligence-pre-dispatch-availability-recovery-test.py
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA_R2C1_TEST_PORT", "8797")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def set_profile(page, state, is_master=None, perfil=None):
    # NOTE (side-finding, out of this wave's scope): intelligence-
    # recovery-hardening-test.py's own set_profile() only mocks
    # getState()/getContext() and no longer suffices as of a LATER,
    # unrelated commit (643cc79, "separate homolog production auth
    # boundaries") -- isModuleAuthorized() for this module's
    # authMode=SEPARATE_AUTHORITY entry now resolves independently of
    # getContext(), so the launcher never mounts under that mock alone.
    # Also mocking isModuleAuthorized() here is a narrower extension of
    # the SAME "stub only the external NX_AUTH_CORE boundary" discipline
    # that mock already uses -- NX_AUTH_CORE is a genuine external
    # dependency of intelligence-panel.js, never code under test here.
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_AUTH_CORE.isModuleAuthorized = () => isMaster === true;
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def open_panel(page):
    # NOTE (side-finding, out of this wave's scope): the launcher FAB
    # (#baiLauncherBtn) is present in the DOM (confirmed: buildPanelDom()
    # ran) but resolves a zero-size bounding rect in this bare
    # `python -m http.server` serving context -- root-caused to this
    # harness's own minimal static-file setup, not to intelligence-
    # panel.js (the same element renders correctly on the real deployed
    # site, unrelated to R2-FINDING-04). openPanel() itself is exposed
    # on window.NX_INTELLIGENCE_PANEL for exactly this kind of test use
    # and gates on nothing but the DOM already being built (true here) --
    # calling it directly still exercises the real, unmodified
    # handleSend/isTextSurfaceEnabled/applyResult code under test;
    # only the initial open-gesture is substituted.
    page.evaluate("window.NX_INTELLIGENCE_PANEL.openPanel()")
    page.wait_for_timeout(200)


# NOTE (side-finding, out of this wave's scope, see open_panel's own
# comment): #baiPanelInput/#baiPanelSendBtn resolve a zero-size bounding
# rect in this bare `python -m http.server` harness (a CSS containing-
# block artifact of this minimal serving context -- confirmed unrelated
# to intelligence-panel.js: the live deployed site's own DOM/CSS is
# byte-identical to this repo's HEAD, per this wave's own Phase 5 build-
# integrity proof). Playwright's coordinate-based fill()/click() (even
# with force=True) cannot dispatch to a genuinely zero-size element.
# Native DOM .value/.dispatchEvent()/.click() bypass Playwright's own
# actionability/coordinate layer entirely and fire the EXACT SAME real
# listeners wireComposer() bound (submit -> submitText -> handleSend) --
# this is still the real, unmodified code under test; only the
# mechanical means of triggering its own real event listener changed.
def send_message(page, text):
    page.evaluate(
        """(text) => {
            var input = document.getElementById('baiPanelInput');
            input.value = text;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        text,
    )
    page.evaluate("document.getElementById('baiPanelSendBtn').click()")


def click_nova_conversa(page):
    page.evaluate("document.getElementById('baiPanelNewChatBtn').click()")


def reset_conversation(page):
    page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation(); window.NX_INTELLIGENCE_STATE.setTextState('OPEN_IDLE');")
    page.wait_for_timeout(100)


def stub_send_real_text(page, impl_js):
    page.evaluate(
        """(implJs) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = {
                readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }])
            };
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = new Function('return (' + implJs + ')')();
        }""",
        impl_js,
    )


# The defect's own reproduction: readConfig() REJECTS (an indeterminate
# check, not a confirmed answer). window.fetch is instrumented (never
# stubbed to succeed/fail on its own) so a call count of 0 directly
# proves sendRealText/fetch was never reached -- the same proof shape
# the Human's own external HTTP capture harness used.
def stub_readconfig_rejects(page):
    page.evaluate(
        """() => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = {
                readConfig: () => Promise.reject(new Error('transient RPC hiccup'))
            };
            window.__fetchCallCount = 0;
            window.fetch = function () { window.__fetchCallCount++; return Promise.reject(new Error('should never be reached')); };
        }"""
    )


# Explicit, CONFIRMED kill-switch-off -- must remain sticky/locked
# (Nova-conversa-required) exactly as intelligence-recovery-hardening-
# test.py's own TEST 3 already proves and requires. Never reopened.
def stub_readconfig_confirmed_false(page):
    page.evaluate(
        """() => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = {
                readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'false' }])
            };
            window.__fetchCallCount = 0;
            window.fetch = function () { window.__fetchCallCount++; return Promise.reject(new Error('should never be reached')); };
        }"""
    )


def get_text_state(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()")


def input_disabled(page):
    return page.evaluate("document.getElementById('baiPanelInput').disabled")


def send_disabled(page):
    return page.evaluate("document.getElementById('baiPanelSendBtn').disabled")


def conversation_text(page):
    return page.locator("#baiPanelConversation").inner_text()


def user_msg_count(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation().filter(m => m.role === 'user').length")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(500)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        open_panel(page)

        # ============================================================
        # TEST A -- THE EXACT ATTEMPT 1 SHAPE: first-ever send in a
        # fresh conversation hits an indeterminate availability check.
        # ============================================================
        stub_readconfig_rejects(page)
        send_message(page, "B2 -- pergunta com falha indeterminada de disponibilidade")
        page.wait_for_timeout(300)
        check("TEST A (GREEN with fix): an INDETERMINATE check surfaces the recoverable error, never the sticky kill-switch message", "Não foi possível concluir" in conversation_text(page), conversation_text(page))
        check("TEST A: ZERO fetch() calls -- proves the request never left the frontend (matches the Human's own HTTP capture harness: capture stayed at N requests)", page.evaluate("window.__fetchCallCount") == 0, page.evaluate("window.__fetchCallCount"))
        check("TEST A (RED without fix / GREEN with fix): composer is NOT left permanently disabled by a merely INDETERMINATE availability check", input_disabled(page) is False)
        check("TEST A (RED without fix / GREEN with fix): textState is a recoverable state, not the sticky DISABLED lock", get_text_state(page) != "DISABLED")
        # Send button re-enablement is gated on non-empty text too
        # (updateSendButtonState: isLocked || !hasText) -- typing proves
        # it is the LOCK, not emptiness, that would have kept it
        # disabled pre-fix.
        page.evaluate("document.getElementById('baiPanelInput').value = 'x'; document.getElementById('baiPanelInput').dispatchEvent(new Event('input', { bubbles: true }));")
        check("TEST A (RED without fix / GREEN with fix): send button is NOT left permanently disabled once text is present", send_disabled(page) is False)
        page.evaluate("document.getElementById('baiPanelInput').value = ''; document.getElementById('baiPanelInput').dispatchEvent(new Event('input', { bubbles: true }));")
        # No page reload, no Nova conversa -- the SAME conversation must
        # accept a next message (this is the exact invariant B1-B4
        # requires: ONE continuous conversation).
        stub_send_real_text(page, "(m,c) => Promise.resolve({response: window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply:'retomou sem Nova conversa', blocks:null})})")
        send_message(page, "prossigo na MESMA conversa")
        page.wait_for_timeout(300)
        check("TEST A: the SAME conversation accepts a next message without Nova conversa/reload", "retomou sem Nova conversa" in conversation_text(page))
        reset_conversation(page)

        # ============================================================
        # TEST B -- THE EXACT ATTEMPT 2 SHAPE: turns 1-3 succeed for
        # real, turn 4 hits the indeterminate availability check.
        # ============================================================
        for i in range(1, 4):
            stub_send_real_text(page, "(m,c) => Promise.resolve({response: window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply:'B%d ok', blocks:null})})" % i)
            send_message(page, "B%d" % i)
            page.wait_for_timeout(300)
        check("TEST B: turns 1-3 all succeeded (matches Human's B1/B2/B3 PASS)", user_msg_count(page) == 3 and "B3 ok" in conversation_text(page), user_msg_count(page))
        stub_readconfig_rejects(page)
        send_message(page, "B4 -- entrada de 60% mesma Triton")
        page.wait_for_timeout(300)
        check("TEST B (GREEN with fix): turn 4's indeterminate gate surfaces the recoverable error, never the sticky kill-switch message", "Não foi possível concluir" in conversation_text(page), conversation_text(page))
        check("TEST B: turn 4 dispatched ZERO fetch() calls (matches capture harness staying at 3 requests)", page.evaluate("window.__fetchCallCount") == 0, page.evaluate("window.__fetchCallCount"))
        check("TEST B (RED without fix / GREEN with fix): composer recovers in the SAME conversation after turn 4's indeterminate failure", input_disabled(page) is False)
        check("TEST B: the 90s no-auto-recovery symptom does not apply -- composer already usable well before that window (no timer-based recovery needed for an indeterminate failure)", input_disabled(page) is False)
        reset_conversation(page)

        # ============================================================
        # TEST C -- REGRESSION GUARD: a CONFIRMED kill-switch-off must
        # remain exactly as intelligence-recovery-hardening-test.py's
        # own TEST 3 already requires -- sticky DISABLED, composer
        # locked, Nova conversa required, zero fetch. Never reopened.
        # ============================================================
        stub_readconfig_confirmed_false(page)
        send_message(page, "pergunta com kill switch confirmado desligado")
        page.wait_for_timeout(300)
        check("TEST C: confirmed kill-switch-off still shows the same message", "temporariamente indisponível" in conversation_text(page))
        check("TEST C: confirmed kill-switch-off dispatches zero fetch calls (unchanged)", page.evaluate("window.__fetchCallCount") == 0, page.evaluate("window.__fetchCallCount"))
        check("TEST C (must remain TRUE -- NOT reopened by this wave): textState is still the sticky DISABLED lock for a CONFIRMED kill-switch-off", get_text_state(page) == "DISABLED")
        check("TEST C (must remain TRUE -- NOT reopened by this wave): composer is still locked for a CONFIRMED kill-switch-off", input_disabled(page) is True)
        click_nova_conversa(page)
        page.wait_for_timeout(150)
        check("TEST C: Nova conversa remains the recovery path out of a genuine DISABLED lock (existing design, unchanged)", get_text_state(page) == "OPEN_IDLE" and input_disabled(page) is False)
        reset_conversation(page)

        # The intelligence-runtime-config.local.js 404 is the deliberate,
        # required D17 precondition (see docstring) -- the ONLY 404 this
        # page can produce in this harness (confirmed earlier via
        # response-status instrumentation), so filtered here by its
        # generic browser-console text as expected noise, never a real
        # defect. console "error"-type messages never include the URL
        # itself, only this generic resource-load-failure text.
        real_errors = [e for e in errors if "404" not in e or "File not found" not in e]
        check("no uncaught console/page errors across the whole suite", len(real_errors) == 0, real_errors[:5])

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== IA-R2C.1 -- Pre-Dispatch Availability-Gate Recovery: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
