#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-01 -- Default current-month period (Análise Geral do Grupo /
Análise F&I do Grupo) + stable category navigation (Landing).

PART A/B/C: dashbi.js/gestao.js's real INITIAL period authority
(ensureDefaultPeriod()) now defaults to the current local month (day
01) through today in real mode, instead of a hardcoded constant never
derived from any real date. Real local-Date mocking (via
add_init_script, before any page script runs) drives the browser's own
`new Date()`/`Date.now()` to a fixed instant, so the REAL module code
is exercised, never a hand-copied re-implementation of its date math.

PART D-I: landing.js's category nav -- HOVER = PREVIEW, CLICK =
PERSISTENT SELECTION. Real pointer/keyboard events against the real
router-served page (not a fixture harness) prove a click-locked
category survives incidental hover traversal, matching the Human's own
reported irritation (accidental category swap while moving from the
clicked category toward its own module list).

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE_ROOT = f"http://127.0.0.1:{PORT}/index.html"
DASHBI_HARNESS = f"http://127.0.0.1:{PORT}/tests/_dashbi-real-provider-harness.html"
GESTAO_HARNESS = f"http://127.0.0.1:{PORT}/tests/fixtures/_gestao-real-provider-harness.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


# ============================================================
# PART A/B/C helpers -- real local-Date mocking
# ============================================================

def fixed_date_script(year, month, day, hour=15):
    # month here is 1-indexed (human); JS Date's own month is 0-indexed.
    # Only the no-arg `new Date()` / `Date.now()` paths are frozen --
    # `new Date(y, m, d)` (explicit args, exactly what ensureDefaultPeriod/
    # computePeriodPreset/sameDayPreviousMonth all use internally) still
    # constructs a REAL Date via the original constructor, so the actual
    # module code's own calendar arithmetic is exercised unmodified.
    return f"""
(function () {{
  var FIXED = new Date({year}, {month - 1}, {day}, {hour}, 0, 0);
  var _RealDate = Date;
  function FakeDate(...args) {{
    if (args.length === 0) return new _RealDate(FIXED.getTime());
    return new _RealDate(...args);
  }}
  FakeDate.now = function () {{ return FIXED.getTime(); }};
  FakeDate.prototype = _RealDate.prototype;
  Object.setPrototypeOf(FakeDate, _RealDate);
  window.Date = FakeDate;
}})();
"""


AUTH_CONFIGURED_SCRIPT = """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null
};
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve('mock-token'); } };
"""


def new_dashbi_page(browser, y, m, d):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(fixed_date_script(y, m, d))
    page.add_init_script(AUTH_CONFIGURED_SCRIPT)
    # RPCs are allowed to fail/hang here -- these assertions only ever
    # read the synchronously-populated #dbDateStart/#dbDateEnd input
    # values, never the async panel data.
    page.route("**/rest/v1/rpc/**", lambda route: route.abort())
    return page


def new_gestao_page(browser, y, m, d):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(fixed_date_script(y, m, d))
    page.add_init_script(AUTH_CONFIGURED_SCRIPT)
    page.route("**/rest/v1/rpc/**", lambda route: route.abort())
    return page


def mount_dashbi(page):
    page.goto(DASHBI_HARNESS)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")


def mount_gestao(page):
    page.goto(GESTAO_HARNESS)
    page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
    page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")


# ============================================================
# PART D-I helpers -- Landing category navigation
# ============================================================

def open_landing_as_master(page):
    page.goto(BASE_ROOT + "#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate("""() => {
        window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
        window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER', allowedModuleIds: [] });
    }""")
    # Landing's own real content is fetched async (config/landing-groups.json);
    # #landingNav existing already proves it resolved and wireLanding() ran.
    page.wait_for_selector(".fNavItem", timeout=8000)


CATEGORY_IDX = {"Gestão": 0, "Novos & Seminovos": 1, "Score & Salários": 2, "Atendimento F&I": 3, "Brabus Intelligence": 4, "Auditoria": 5}


def nav_btn(page, label):
    return page.locator(f'#fNavTab{CATEGORY_IDX[label]}')


def active_category_label(page):
    # .fNavItem's own markup is `<span class="idx">01</span><span
    # class="label">Gestão</span>` -- read the dedicated .label span,
    # never the button's raw textContent (which would concatenate the
    # zero-padded index number with no separator, e.g. "01Gestão").
    return page.evaluate("""() => {
        var active = document.querySelector('.fNavItem.active .label');
        return active ? active.textContent.trim() : null;
    }""")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ============================================================
        # TEST A -- Análise Geral (dashbi.js) default period
        # ============================================================
        page = new_dashbi_page(browser, 2026, 9, 12)
        mount_dashbi(page)
        check("[A] start = 2026-09-01", page.input_value("#dbDateStart") == "2026-09-01", page.input_value("#dbDateStart"))
        check("[A] end = 2026-09-12", page.input_value("#dbDateEnd") == "2026-09-12", page.input_value("#dbDateEnd"))
        check("[A] 'Mês atual' preset shows active (visual default, not silently CUSTOM)", "dbBtnActive" in (page.get_attribute(".dbPresetBtn[data-preset='currentMonth']", "class") or ""))
        # ---- manual override survives a normal rerender/filter interaction ----
        page.fill("#dbDateStart", "2026-08-01")
        page.fill("#dbDateEnd", "2026-08-31")
        page.wait_for_timeout(100)
        page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")  # re-entry / rerender
        check("[A] manual start survives rerender: 2026-08-01", page.input_value("#dbDateStart") == "2026-08-01", page.input_value("#dbDateStart"))
        check("[A] manual end survives rerender: 2026-08-31", page.input_value("#dbDateEnd") == "2026-08-31", page.input_value("#dbDateEnd"))
        page.close()

        # ============================================================
        # TEST B -- Análise F&I (gestao.js) default period
        # ============================================================
        page = new_gestao_page(browser, 2026, 9, 12)
        mount_gestao(page)
        check("[B] start = 2026-09-01", page.input_value("#geDateStart") == "2026-09-01", page.input_value("#geDateStart"))
        check("[B] end = 2026-09-12", page.input_value("#geDateEnd") == "2026-09-12", page.input_value("#geDateEnd"))
        check("[B] 'Mês atual' preset shows active", "gePresetActive" in (page.get_attribute(".gePresetBtn[data-preset='CURRENT_MONTH']", "class") or ""))
        page.fill("#geDateStart", "2026-08-01")
        page.fill("#geDateEnd", "2026-08-31")
        page.wait_for_timeout(100)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        check("[B] manual start survives rerender: 2026-08-01", page.input_value("#geDateStart") == "2026-08-01", page.input_value("#geDateStart"))
        check("[B] manual end survives rerender: 2026-08-31", page.input_value("#geDateEnd") == "2026-08-31", page.input_value("#geDateEnd"))
        page.close()

        # ============================================================
        # TEST C -- month/year boundary, no UTC drift
        # ============================================================
        for (y, m, d, exp_start, exp_end) in [
            (2026, 10, 1, "2026-10-01", "2026-10-01"),
            (2027, 1, 5, "2027-01-01", "2027-01-05"),
        ]:
            page = new_dashbi_page(browser, y, m, d)
            mount_dashbi(page)
            check(f"[C] dashbi {y}-{m:02d}-{d:02d}: start = {exp_start}", page.input_value("#dbDateStart") == exp_start, page.input_value("#dbDateStart"))
            check(f"[C] dashbi {y}-{m:02d}-{d:02d}: end = {exp_end}", page.input_value("#dbDateEnd") == exp_end, page.input_value("#dbDateEnd"))
            page.close()
            page = new_gestao_page(browser, y, m, d)
            mount_gestao(page)
            check(f"[C] gestao {y}-{m:02d}-{d:02d}: start = {exp_start}", page.input_value("#geDateStart") == exp_start, page.input_value("#geDateStart"))
            check(f"[C] gestao {y}-{m:02d}-{d:02d}: end = {exp_end}", page.input_value("#geDateEnd") == exp_end, page.input_value("#geDateEnd"))
            page.close()

        # ============================================================
        # TEST D -- hover preview (no click yet), no flicker
        # ============================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        check("[D] default category active on fresh landing (Gestão)", active_category_label(page) == "Gestão", active_category_label(page))
        # AUTH FOUNDATION Phase 2E's own pre-existing pointerHasMoved guard
        # (unrelated to this Wave, kept untouched) only starts honoring
        # mouseenter after a genuine mousemove has been observed anywhere
        # on the document -- exactly like a real Human's pointer already
        # having moved around the page before ever reaching the nav.
        # A neutral warm-up move (never touching a nav item) satisfies it
        # without exercising anything this Wave changed.
        page.mouse.move(20, 20)
        page.wait_for_timeout(50)
        nav_btn(page, "Atendimento F&I").hover()
        page.wait_for_timeout(200)
        check("[D] hover previews Atendimento F&I (no click yet, restrained-intent preview still works)", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        nav_btn(page, "Brabus Intelligence").hover()
        page.wait_for_timeout(200)
        check("[D] hover previews Brabus Intelligence next (still unlocked)", active_category_label(page) == "Brabus Intelligence", active_category_label(page))
        page.close()

        # ============================================================
        # TEST E -- click lock: incidental hover afterward must not swap
        # ============================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").click()
        page.wait_for_timeout(150)
        check("[E] Atendimento F&I active after click", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        for label in ["Brabus Intelligence", "Auditoria", "Score & Salários", "Gestão", "Novos & Seminovos"]:
            nav_btn(page, label).hover()
            page.wait_for_timeout(200)  # longer than HOVER_INTENT_MS -- proves it's the LOCK, not merely a short debounce, holding the panel
            check(f"[E] still Atendimento F&I after hovering {label}", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        # traverse toward the right-side module list, the Human's own exact path
        detail = page.locator("#landingModuleDetail")
        box = detail.bounding_box()
        if box:
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=10)
            page.wait_for_timeout(200)
        check("[E] still Atendimento F&I after moving toward the module list", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        page.close()

        # ============================================================
        # TEST F -- change lock: clicking a DIFFERENT category re-locks
        # ============================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").click()
        page.wait_for_timeout(100)
        nav_btn(page, "Brabus Intelligence").click()
        page.wait_for_timeout(100)
        check("[F] Brabus Intelligence active+locked after clicking it", active_category_label(page) == "Brabus Intelligence", active_category_label(page))
        nav_btn(page, "Gestão").hover()
        page.wait_for_timeout(200)
        check("[F] Brabus Intelligence remains active after hovering elsewhere", active_category_label(page) == "Brabus Intelligence", active_category_label(page))
        page.close()

        # ============================================================
        # TEST G -- clicking a right-side module navigates immediately,
        # no category switch first, no extra click.
        # ============================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").click()
        page.wait_for_timeout(150)
        module_link = page.locator("#landingModuleDetail a.fModuleBlock").first
        check("[G] a real, clickable module link exists under the locked category", module_link.count() == 1)
        href = module_link.get_attribute("href")
        module_link.click()
        page.wait_for_timeout(300)
        check("[G] navigation occurred exactly once (hash matches the clicked module's own href)", page.evaluate("location.hash") == href, (page.evaluate("location.hash"), href))
        page.close()

        # ============================================================
        # TEST H -- keyboard: Tab + Enter/Space locks, focus-visible, module reachable
        # ============================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").focus()
        page.wait_for_timeout(80)
        check("[H] Tab-focus alone still PREVIEWS (not yet locked)", active_category_label(page) == "Atendimento F&I")
        outline = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle")
        check("[H] focus-visible outline present", outline == "solid", outline)
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        check("[H] Enter locks Atendimento F&I", active_category_label(page) == "Atendimento F&I")
        nav_btn(page, "Auditoria").hover()
        page.wait_for_timeout(200)
        check("[H] still locked to Atendimento F&I after a hover elsewhere post-Enter", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        check("[H] module remains reachable (real link still present)", page.locator("#landingModuleDetail a.fModuleBlock").count() >= 1)
        page.close()

        # ============================================================
        # TEST I -- mobile: tap = persistent selection, zero horizontal scroll
        # ============================================================
        page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        open_landing_as_master(page)
        nav_btn(page, "Atendimento F&I").tap()
        page.wait_for_timeout(150)
        check("[I] tap selects Atendimento F&I persistently", active_category_label(page) == "Atendimento F&I", active_category_label(page))
        module_link_mobile = page.locator("#landingModuleDetail a.fModuleBlock").first
        check("[I] module reachable on mobile after tap (no double-tap needed)", module_link_mobile.count() == 1)
        href_mobile = module_link_mobile.get_attribute("href")
        module_link_mobile.tap()
        page.wait_for_timeout(300)
        check("[I] tap on module navigates normally", page.evaluate("location.hash") == href_mobile)
        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("[I] zero horizontal scroll at 390px", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        browser.close()

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-01: Default Period + Landing Nav ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
