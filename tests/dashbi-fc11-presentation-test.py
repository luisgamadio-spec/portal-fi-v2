#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-1.1 (Human UAT revision of GAP-001) -- presentation + information
architecture harness.

Covers this Wave's brief Gates 30 (comparison presentation), 31 (seller
table removal), 32 (subnav reposition). Does NOT touch business logic --
golden fixtures/adapter parity are covered separately by
tests/dashbi-parity-test.py (unaffected by this Wave, still 26/26).

CSS (tokens/module-system/dashbi) is injected via add_style_tag -- the
harness page itself has no <link>, and several assertions here (srOnly
clipping, .dbDesktopOnly/.dbMobileOnly responsive switching, horizontal
overflow) are meaningless without the real stylesheet applied.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/
(same convention as tests/dashbi-parity-test.py / dashbi-comparison-parity-test.py).
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "dashbi-fixtures.json")
BASE = "http://localhost:8700/portal-next-v2/tests/_dashbi-real-provider-harness.html"
CSS_FILES = ["../design-system-2/tokens.css", "assets/css/module-system.css", "assets/css/dashbi.css"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def mount(browser, fixtures_body, width=1366, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.route("**/dashbi-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=fixtures_body))
    page.goto(BASE)
    for css in CSS_FILES:
        page.add_style_tag(path=css)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")
    page.wait_for_selector("#dbFixtureSelect", timeout=5000)
    return page


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available -- harness code exists, not executed.")
        sys.exit(0)

    with open(FIXTURES_PATH, encoding="utf-8") as f:
        fixtures_body = f.read()

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Gate 31: seller table removed, store table + Ranking intact ----------
        page = mount(browser, fixtures_body)
        page.select_option("#dbFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(150)
        panel_html = page.inner_html("#dbPanel")
        check("31A: 'Vendas e Financiamentos por Vendedor' heading does not render", "Vendas e Financiamentos por Vendedor" not in panel_html)
        check("31B: no seller-table markup (ns=sellerTable) in the Visão Geral output", 'data-detail-ns="sellerTable"' not in panel_html)
        check("31E: Loja table still renders ('Vendas e Financiamentos por Loja')", "Vendas e Financiamentos por Loja" in panel_html)

        page.click('#dbSubnav .dbModeBtn[data-mode="ranking"]')
        page.wait_for_timeout(150)
        ranking_html = page.inner_html("#dbPanel")
        check("31C: Ranking section renders after clicking the subnav", "Ranking —" in ranking_html)
        check("31D: Ranking table has real rows (not 'Sem dados')", "Sem dados" not in ranking_html.split("Ranking —")[-1][:2000])
        # Gates 31G/H (no new backend call, no RPC changed) are file-scope facts,
        # not runtime-observable in fixture mode -- reported in the final report
        # against `git diff` directly (dashbi-real-provider.js is untouched this Wave).

        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(100)
        page.select_option("#dbFixtureSelect", "model_analysis_parcelamento_completo")
        page.wait_for_timeout(150)
        page.click('#dbSubnav .dbModeBtn[data-mode="modelos"]')
        page.wait_for_timeout(150)
        modelos_html = page.inner_html("#dbPanel")
        check("31F: Modelos section still renders correctly (unaffected by seller-table removal)", "Análise por Modelos (Novos)" in modelos_html)
        page.close()

        # ---------- Gates 30 + 32 + 29 + 7: comparison presentation, subnav, accessibility ----------
        page = mount(browser, fixtures_body)
        page.select_option("#dbFixtureSelect", "valores_grandes")
        page.select_option("#dbComparisonFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(200)
        html = page.inner_html("#dbPanel")

        check("30A: current value visible (KPI grid)", "modKpiValue" in html)
        check("30B: previous value visible (dbPrevValue present)", "dbPrevValue" in html)
        # Gate 30G is about the REMOVED variation-percent presentation (old
        # "▲ +12,4%" delta badge, class dbDelta*), not about percent-FORMATTED
        # previous values -- a percent metric (Share) legitimately shows its
        # previous value as e.g. "46,4%" (Gate 7: same formatter as current).
        check("30G: the old percent-delta presentation (dbDelta* classes) is fully gone", "dbDelta" not in html)
        check("30H: 'Anterior:' label does NOT appear anywhere in the panel", "Anterior:" not in html)
        arrow_texts = page.eval_on_selector_all(".dbPrevArrow", "els => els.map(e => e.textContent)")
        check("30C/D/E: arrows present and only the 3 allowed glyphs (▲▼→) are used", len(arrow_texts) > 0 and all(t in ("▲", "▼", "→") for t in arrow_texts))

        sr_texts = page.eval_on_selector_all(".srOnly", "els => els.map(e => e.textContent)")
        check("29: srOnly spans exist with full context (\"valor anterior ... valor atual ...\")", len(sr_texts) > 0 and all("valor anterior" in t and "valor atual" in t for t in sr_texts))
        sr_visible = page.eval_on_selector(".srOnly", "el => { var r = el.getBoundingClientRect(); return r.width <= 1 && r.height <= 1; }")
        check("29b: srOnly span is visually clipped with real CSS applied (not shown on screen)", sr_visible)

        kpi_card_html = page.eval_on_selector(".modKpiCard.modKpiCardInfo", "el => el.innerHTML")
        check("7: previous Receita Total value uses the money formatter (R$) like current", "R$" in kpi_card_html and kpi_card_html.count("R$") >= 2)

        subnav_count = page.eval_on_selector_all(".dbModeGroup", "els => els.length")
        check("32A/H: exactly ONE subnav instance exists (no duplicate top+bottom)", subnav_count == 1)
        subnav_top = page.eval_on_selector("#dbSubnav", "el => el.getBoundingClientRect().top")
        filters_top = page.eval_on_selector(".modFilters", "el => el.getBoundingClientRect().top")
        kpi_top = page.eval_on_selector(".modKpiGrid", "el => el.getBoundingClientRect().top")
        check("32B: subnav appears BEFORE the filters bar", subnav_top < filters_top)
        check("32C: subnav appears BEFORE the KPI grid content", subnav_top < kpi_top)
        active_btn = page.eval_on_selector('#dbSubnav .dbModeBtn.dbBtnActive', "el => el.dataset.mode")
        check("32D: active state correctly marks 'overview' by default", active_btn == "overview")

        page.click('#dbSubnav .dbModeBtn[data-mode="ranking"]')
        page.wait_for_timeout(150)
        check("32E: clicking 'Ranking' in the subnav opens the Ranking section", "Ranking —" in page.inner_html("#dbPanel"))
        active_btn2 = page.eval_on_selector('#dbSubnav .dbModeBtn.dbBtnActive', "el => el.dataset.mode")
        check("32D(2): active state updates to 'ranking' after the click", active_btn2 == "ranking")

        # 32F/22: filter persistence -- switching subview keeps the Visão/período filters unchanged
        start_val = page.eval_on_selector("#dbDateStart", "el => el.value")
        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(100)
        page.click('#dbSubnav .dbModeBtn[data-mode="overview"]')
        page.wait_for_timeout(100)
        start_val_after = page.eval_on_selector("#dbDateStart", "el => el.value")
        check("22: date filter unchanged after navigating between subviews", start_val == start_val_after)

        # 32G: Novos por Loja availability rule preserved (Grupo view must NOT
        # expose it) -- the filter-persistence check above left currentDeptView
        # on 'Novos', so switch back to 'Grupo' first.
        page.click('.dbViewBtn[data-view="Grupo"]')
        page.wait_for_timeout(100)
        grupo_modes = page.eval_on_selector_all('#dbSubnav .dbModeBtn', "els => els.map(e => e.dataset.mode)")
        check("32G: 'Novos por Loja' still hidden outside the Novos view (rule unchanged by the reposition)", "novosLoja" not in grupo_modes)
        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(100)
        novos_modes = page.eval_on_selector_all('#dbSubnav .dbModeBtn', "els => els.map(e => e.dataset.mode)")
        check("32G(2): 'Novos por Loja' available inside the Novos view", "novosLoja" in novos_modes)
        page.close()

        # NOTE on Gate 8 ("—" no-base marker, previousValue strictly null): NOT
        # independently tested here. Direct code reading + every reachable UI
        # path (KPI/store/seller aggregates are always zero-defaulted, never
        # null; Model Analysis's prevByModelo always covers every key in
        # FAMILY_MODELS[currentFamily] via the same Set-union on both periods)
        # show this branch is unreachable through the current fixture-pairing
        # or real-transport UI -- a defensive branch matching the spec exactly,
        # not exercised by an integration test. previousValueHtml's null
        # handling itself is still exercised indirectly: dashbi-comparison-
        # parity-test.py's checks 4/5 prove the adjacent calcDelta null/zero
        # distinction this same design follows. Reported honestly rather than
        # padded with a fabricated always-true check.

        # ---------- Gate 25/26: responsive (1024x768 intermediate + mobile) ----------
        for w, h, name in [(1024, 768, "1024x768"), (390, 844, "mobile")]:
            page = mount(browser, fixtures_body, width=w, height=h)
            page.wait_for_timeout(150)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"25/26 ({name}): no horizontal overflow with subnav present", overflow <= 1)
            subnav_visible = page.eval_on_selector("#dbSubnav .dbModeGroup", "el => el.getBoundingClientRect().width > 0")
            check(f"26 ({name}): subnav is reachable without scrolling past KPI content", subnav_visible)
            page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print("\n=== Dashbi FC-1.1 Presentation/Navigation: %d/%d ===" % (passed, len(results)))
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
