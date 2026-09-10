#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3H.1 -- Brabus Intelligence VOICE responsive / zero-overflow test.

Proves the new Voice entry control (inside the already Human-approved
drawer's composer) introduces zero horizontal overflow at the 4
required breakpoints (1366/1024/900/480), both at page level and at
drawer/composer/status level, including while the Voice button is in
an active (longer-label) state and while the dev-only diagnostics panel
is open. Does not open any real/faked WebRTC session -- pure layout
proof, flags stay false throughout (Section 53).

Requires: `python -m http.server <port>` running from this worktree's
own root.
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


# Same fixed-position-blind-spot-aware overflow probe as
# tests/intelligence-panel-test.py's own TRUE_OVERFLOW_JS, extended to
# also scan the dev-only Voice diagnostics root (a sibling of the
# drawer under #nxOverlayRoot, not covered by a #baiLauncherRoot-scoped
# selector).
TRUE_OVERFLOW_JS = """
() => {
    var vw = window.innerWidth;
    var worst = 0, worstSel = null;
    document.querySelectorAll('#baiLauncherRoot *, .baiVoiceDiagRoot *').forEach(el => {
        var r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        var over = Math.max(0, r.right - vw) + Math.max(0, -r.left);
        if (over > worst) { worst = over; worstSel = el.className || el.tagName; }
    });
    return { worst: worst, worstSel: String(worstSel) };
}
"""


def true_overflow(page):
    return page.evaluate(TRUE_OVERFLOW_JS)


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


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        errors = []

        BREAKPOINTS = [1366, 1024, 900, 480]
        for w in BREAKPOINTS:
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(BASE + "#/landing")
            page.wait_for_timeout(500)
            set_profile(page, "AUTHORIZED", True, "MASTER")
            open_panel(page)

            page_overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            drawer_overflow = page.evaluate("(function(){var el=document.getElementById('baiPanelDrawer'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
            composer_overflow = page.evaluate("(function(){var el=document.querySelector('.baiPanelComposer'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
            check(f"{w}px: page overflow 0", page_overflow <= 0, page_overflow)
            check(f"{w}px: drawer overflow 0", drawer_overflow <= 0, drawer_overflow)
            check(f"{w}px: composer overflow 0 (Voice button + Send button both fit)", composer_overflow <= 0, composer_overflow)

            btn = page.locator("#baiPanelVoiceBtn")
            check(f"{w}px: Voice button present and tappable (non-zero box)", btn.count() == 1 and btn.bounding_box()["height"] > 0)
            send_box = page.locator("#baiPanelSendBtn").bounding_box()
            voice_box = btn.bounding_box()
            check(f"{w}px: Voice button does not overlap the Send button", voice_box["x"] + voice_box["width"] <= send_box["x"] + 1, (voice_box, send_box))

            # Force the longest label state ("Erro — tentar de novo") --
            # the widest text this control ever shows -- to prove the
            # ellipsis/max-width guard actually holds under real layout,
            # not just under the default short "Voz" label.
            page.evaluate("""() => {
                window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_ERROR');
            }""")
            page.wait_for_timeout(80)
            ov_error_state = true_overflow(page)
            check(f"{w}px: no true viewport overflow with the longest Voice label (ERROR state)", ov_error_state["worst"] <= 0.5, ov_error_state)
            composer_overflow_2 = page.evaluate("(function(){var el=document.querySelector('.baiPanelComposer'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
            check(f"{w}px: composer still non-overflowing in the longest-label state", composer_overflow_2 <= 0, composer_overflow_2)
            page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_DISCONNECTED');")

            # Dev-only diagnostics panel (sibling of the drawer, not part
            # of the approved UI) -- must also never overflow.
            page.click("#baiVoiceDiagToggle")
            page.wait_for_timeout(100)
            ov_diag = true_overflow(page)
            check(f"{w}px: Voice diagnostics dev panel introduces no true viewport overflow", ov_diag["worst"] <= 0.5, ov_diag)
            diag_panel_overflow = page.evaluate("(function(){var el=document.getElementById('baiVoiceDiagPanel'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
            check(f"{w}px: Voice diagnostics panel itself has no internal overflow", diag_panel_overflow <= 0, diag_panel_overflow)
            page.click("#baiVoiceDiagToggle")

            if w == 480:
                check("480px: Voice button remains reachable alongside the mobile full-screen backdrop", page.locator("#baiPanelBackdrop").is_visible() and voice_box["width"] > 0)

            page.close()

        browser.close()

    unexplained = [e for e in errors if "Failed to load resource" not in e]
    check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence VOICE Responsive Test (IA-3H.1): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
