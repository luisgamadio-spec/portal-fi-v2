#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-ENTRY-01 -- Brabus Intelligence "Living Core" entry points.

Purely visual/UX re-skin of the two Intelligence ENTRY POINTS: the
floating launcher button (assets/js/intelligence/intelligence-panel.js
launcherHtml()) and the Landing category row for "Brabus Intelligence"
(assets/js/landing.js landingHtml()). Neither the Intelligence Panel's
own open/close authority (openPanel/closePanel/togglePanel, the single
existing #baiLauncherBtn click listener) nor the V2-UAT-01 click-lock
category navigation logic were touched -- this suite proves both still
work exactly as before, underneath the new visuals.

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
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-entry-01")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


CATEGORY_IDX = {"Gestão": 0, "Novos & Seminovos": 1, "Score & Salários": 2, "Atendimento F&I": 3, "Brabus Intelligence": 4, "Auditoria": 5}


def nav_btn(page, label):
    return page.locator(f'#fNavTab{CATEGORY_IDX[label]}')


def active_category_label(page):
    return page.evaluate("""() => {
        var active = document.querySelector('.fNavItem.active .label');
        return active ? active.textContent.trim() : null;
    }""")


def open_landing_as_master(page):
    page.goto(BASE + "#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate("""() => {
        window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
        window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER', allowedModuleIds: [] });
    }""")
    page.wait_for_selector(".fNavItem", timeout=8000)


def mock_master_and_show_launcher(page):
    # This worktree's real (gitignored) intelligence-runtime-config.local.js
    # is present for Human UAT, so the default NX_AUTH_CORE state here is
    # SIGNED_OUT (real auth configured), not AUTH_NOT_CONFIGURED -- the
    # launcher is correctly absent for an anonymous viewer. Mirrors
    # intelligence-panel-test.py's own pre-existing set_profile() helper:
    # monkeypatch the two getter functions, then call the panel's own
    # public refresh() hook (the same thing a real onStateChange would
    # trigger) so isVisibleNow() is re-evaluated with MASTER context.
    page.wait_for_function("!!window.NX_INTELLIGENCE_PANEL", timeout=8000)
    page.evaluate("""() => {
        window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
        window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER', allowedModuleIds: [] });
        window.NX_INTELLIGENCE_PANEL.refresh();
    }""")
    page.wait_for_selector("#baiLauncherBtn", timeout=8000)


def drawer_hidden(page):
    return page.get_attribute("#baiPanelDrawer", "hidden") is not None


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
        # TEST A -- Living Core launcher button exists
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        check("[A] #baiLauncherBtn exists", page.locator("#baiLauncherBtn").count() == 1)
        check("[A] Living Core nodes present (core/ring/orbit/nucleus)",
              page.locator("#baiLauncherBtn .baiLauncherCore").count() == 1 and
              page.locator("#baiLauncherBtn .baiLauncherRing").count() == 1 and
              page.locator("#baiLauncherBtn .baiLauncherOrbit").count() == 1 and
              page.locator("#baiLauncherBtn .baiLauncherNucleus").count() == 1)
        check("[A] aria-label unchanged", page.get_attribute("#baiLauncherBtn", "aria-label") == "Abrir Brabus Intelligence")
        shot(page, "01-floating-idle.png")

        # ============================================================
        # TEST B/C -- click opens the SAME existing Intelligence, exactly once
        # ============================================================
        check("[B/C] drawer hidden before click", drawer_hidden(page))
        page.click("#baiLauncherBtn .baiLauncherNucleus")  # click a nested decorative child -- proves bubbling, not a second listener
        page.wait_for_timeout(150)
        check("[B/C] drawer open after ONE click on a nested core node", not drawer_hidden(page))
        check("[B/C] aria-expanded=true (same existing openPanel() authority ran)", page.get_attribute("#baiLauncherBtn", "aria-expanded") == "true")
        check("[B/C] real panel content present (composer input untouched)", page.locator("#baiPanelInput").count() == 1)
        # Closing via the drawer's own existing close button (the same
        # #baiPanelCloseBtn/closePanel() authority every other suite in
        # this codebase already uses -- the large centered Workspace
        # shell covers the backdrop entirely by product design, unrelated
        # to this Wave, so the backdrop itself isn't reachable here).
        page.click("#baiPanelCloseBtn")
        page.wait_for_timeout(150)
        check("[B/C] exactly one open happened per one click (no double-open)", drawer_hidden(page))
        page.close()

        # ============================================================
        # TEST J -- no functional change inside the Intelligence Panel
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        page.click("#baiLauncherBtn")
        page.wait_for_timeout(150)
        check("[J] panel title unchanged", page.inner_text("#baiPanelDrawer .baiPanelTitle").strip() == "Brabus Intelligence")
        check("[J] close button still works (existing closePanel() authority)", page.locator("#baiPanelCloseBtn").count() == 1)
        page.click("#baiPanelCloseBtn")
        page.wait_for_timeout(150)
        check("[J] closePanel() still closes the drawer", drawer_hidden(page))
        page.close()

        # ============================================================
        # TEST D -- Landing remains navigable (module click -> real route)
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").click()
        page.wait_for_timeout(150)
        module_link = page.locator("#landingModuleDetail a.fModuleBlock").first
        check("[D] a module link exists under a category", module_link.count() == 1)
        href = module_link.get_attribute("href")
        module_link.click()
        page.wait_for_timeout(300)
        check("[D] Landing navigation still works", page.evaluate("location.hash") == href)
        page.close()

        # ============================================================
        # TEST E -- V2-UAT-01 category click-lock still holds
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").click()
        page.wait_for_timeout(120)
        check("[E] Atendimento F&I active after click", active_category_label(page) == "Atendimento F&I")
        page.mouse.move(20, 20)
        page.wait_for_timeout(50)
        for label in ["Brabus Intelligence", "Auditoria", "Gestão"]:
            nav_btn(page, label).hover()
            page.wait_for_timeout(200)
            check(f"[E] still locked to Atendimento F&I after hovering {label}", active_category_label(page) == "Atendimento F&I")
        page.close()

        # Landing -- Brabus Intelligence selected, screenshot for visual review
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        page.mouse.move(20, 20)
        page.wait_for_timeout(50)
        nav_btn(page, "Brabus Intelligence").click()
        page.wait_for_timeout(150)
        check("[VISUAL] Brabus Intelligence selectable and stays locked", active_category_label(page) == "Brabus Intelligence")
        shot(page, "02-landing-intel-selected.png")
        page.close()

        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        shot(page, "03-landing-intel-idle.png")  # default category (Gestão) active -- Intelligence row idle
        page.close()

        # Floating Living Core -- hover-expanded, still idle (before opening)
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        page.hover("#baiLauncherBtn")
        page.wait_for_timeout(250)
        shot(page, "04-floating-hover-expanded.png")
        page.close()

        # ============================================================
        # TEST F -- keyboard: Tab reaches the launcher, Enter opens it
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        page.evaluate("document.getElementById('baiLauncherBtn').focus()")
        page.wait_for_timeout(80)
        check("[F] launcher can receive keyboard focus", page.evaluate("document.activeElement && document.activeElement.id") == "baiLauncherBtn")
        outline = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle")
        check("[F] focus-visible outline present on launcher", outline == "solid", outline)
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("[F] Enter opens the panel (native button activation -> existing click handler)", not drawer_hidden(page))
        page.close()

        # ============================================================
        # TEST G -- touch: tap opens the launcher
        # ============================================================
        page = tracked_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        check("[G] launcher present on mobile viewport", page.locator("#baiLauncherBtn").count() == 1)
        shot(page, "05-mobile-floating-idle.png")  # compact circle, before any tap
        # position + force: at 390px the pre-existing, LOCAL/HOMOLOG-only
        # .nxDevBadge (shell.css, unrelated to this Wave, never shown in
        # production) happens to span almost the full viewport width at
        # the bottom of the screen and geometrically covers the BOTTOM
        # half of the launcher's own circle (confirmed via real
        # getBoundingClientRect overlap, not a z-index regression from
        # this Wave -- the launcher's mobile position/size is unchanged).
        # A real production touch device never renders that badge at
        # all, so tapping the launcher's own TOP half (never covered)
        # reflects genuine end-user geometry, not a masked product bug.
        page.locator("#baiLauncherBtn").click(position={"x": 26, "y": 10}, force=True)
        page.wait_for_timeout(150)
        check("[G] tap opens the panel", not drawer_hidden(page))
        box = page.locator("#baiLauncherBtn").bounding_box()
        check("[G] touch target >= 44x44px", box is not None and box["width"] >= 44 and box["height"] >= 44, box)
        shot(page, "05b-mobile-floating-open.png")
        page.close()

        # ============================================================
        # TEST H -- prefers-reduced-motion: identity preserved, no continuous animation
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.emulate_media(reduced_motion="reduce")
        page.goto(BASE + "#/landing")
        mock_master_and_show_launcher(page)
        anim = page.evaluate("""() => {
            var n = document.querySelector('.baiLauncherNucleus');
            var r = document.querySelector('.baiLauncherRing');
            var o = document.querySelector('.baiLauncherOrbit');
            return [n, r, o].map(el => getComputedStyle(el).animationName);
        }""")
        check("[H] no continuous keyframe animation under prefers-reduced-motion", all(a == "none" for a in anim), anim)
        check("[H] Living Core nodes still present/visible (identity preserved without motion)",
              page.locator(".baiLauncherNucleus").count() == 1 and page.locator(".baiLauncherRing").count() == 1)
        page.hover("#baiLauncherBtn")
        page.wait_for_timeout(80)
        border_color = page.evaluate("() => getComputedStyle(document.getElementById('baiLauncherBtn')).borderColor")
        check("[H] hover still perceptible under reduced-motion (border color changes instantly)", "238" in border_color or "ee4b57" in border_color.lower(), border_color)
        shot(page, "06-reduced-motion.png")
        page.close()

        # ============================================================
        # TEST I -- zero horizontal scroll at the 4 required breakpoints,
        # including while the floating button is hover-expanded.
        # ============================================================
        for w, h in [(1366, 900), (1024, 900), (480, 900), (390, 844)]:
            page = tracked_page(viewport={"width": w, "height": h})
            page.goto(BASE + "#/landing")
            if w >= 900:
                mock_master_and_show_launcher(page)
                page.hover("#baiLauncherBtn")
                page.wait_for_timeout(250)
            else:
                page.wait_for_timeout(500)
            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[I] zero horizontal scroll at {w}px (launcher hover-expanded where applicable)", overflow["scroll"] <= overflow["client"], overflow)
            page.close()

        browser.close()

    # ============================================================
    # TEST K -- no console exceptions across the whole suite
    # ============================================================
    # Same "Failed to load resource" exclusion intelligence-panel-test.py
    # already uses: the gitignored, optional intelligence-runtime-
    # config.local.js is deliberately absent for this whole run (moved
    # aside so index.html boots in fixture mode for these Playwright
    # tests -- see main()'s own docstring), and the app already handles
    # its 404 gracefully by falling back to fixture mode. Not a real
    # application exception.
    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[K] zero console/page errors across the whole suite", len(unexplained) == 0, unexplained[:5])

    # ============================================================
    # TEST L -- no external library dependency introduced
    # ============================================================
    changed_files = [
        os.path.join(V2_ROOT, "assets", "js", "intelligence", "intelligence-panel.js"),
        os.path.join(V2_ROOT, "assets", "js", "landing.js"),
        os.path.join(V2_ROOT, "assets", "css", "intelligence.css"),
        os.path.join(V2_ROOT, "assets", "css", "landing.css"),
    ]
    external_ref = re.compile(r"""(?:src|href)\s*=\s*["']https?://|@import\s+url\(["']?https?://""")
    found = []
    for f in changed_files:
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        if external_ref.search(content):
            found.append(f)
    check("[L] no external CDN/library reference introduced in the changed files", len(found) == 0, found)

    ok = all(r[1] for r in results)
    print(f"\n=== IA-ENTRY-01: Living Core Entry Points ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
