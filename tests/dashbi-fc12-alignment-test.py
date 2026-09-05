#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-1.2 (Human UAT defect A) -- comparison cell alignment structure harness.

Proves the presentation CONTRACT (Gate 31, this Wave's brief): current and
previous use separate semantic elements, the arrow is separate from the
previous number, no percent delta, no "Anterior:", tabular numerics, and a
table numeric-comparison alignment class exists. Also proves the actual
GEOMETRY (not just class presence): the previous number's right edge lands
on the same pixel as the current number's right edge, and the arrow sits
outside that shared edge without shifting either number -- this is what the
human actually complained about, so a class-only check would not be enough.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
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
        page = mount(browser, fixtures_body)
        page.select_option("#dbFixtureSelect", "valores_grandes")
        page.select_option("#dbComparisonFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(200)

        html = page.inner_html("#dbPanel")
        check("31 (structure): separate semantic elements for current (.dbNumCurrent) and previous (.dbPrevNum)", "dbNumCurrent" in html and "dbPrevNum" in html)
        check("31 (structure): arrow is its own element, separate from the previous number", '<span class="dbPrevArrow' in html)
        check("31 (structure): table numeric-comparison alignment class present", "dbNumCompare" in html)
        check("31 (no percent): no '%' delta character combination remains from the old badge (dbDelta* fully gone)", "dbDelta" not in html)
        check("31 (no label): 'Anterior:' does not appear", "Anterior:" not in html)

        tabular_current = page.eval_on_selector(".dbTable .dbNumCompare .dbNumCurrent", "el => getComputedStyle(el).fontVariantNumeric")
        tabular_prev = page.eval_on_selector(".dbTable .dbNumCompare .dbPrevNum", "el => getComputedStyle(el).fontVariantNumeric")
        check("21: tabular-nums applied to both the current and previous numbers in table cells", "tabular-nums" in (tabular_current or "") and "tabular-nums" in (tabular_prev or ""))

        display = page.eval_on_selector(".dbTable .dbNumCompare", "el => getComputedStyle(el).display")
        check("18: the comparison cell is a structured grid/box (not plain concatenated text)", display in ("grid", "inline-grid"))

        # ---------- Geometry: right edges actually align, arrow doesn't shift them ----------
        cell = page.query_selector(".dbTable tbody tr td:nth-child(5)")  # Produção Total column, first data row
        current_box = cell.eval_on_selector(".dbNumCurrent", "el => el.getBoundingClientRect()")
        prev_num_box = cell.eval_on_selector(".dbPrevNum", "el => el.getBoundingClientRect()")
        arrow_box = cell.eval_on_selector(".dbPrevArrow", "el => el.getBoundingClientRect()")
        check("19/20 (geometry): current and previous NUMBER share the same right edge (within 1px)", abs(current_box["right"] - prev_num_box["right"]) <= 1)
        check("20 (geometry): the arrow sits to the RIGHT of that shared edge, not inside it", arrow_box["left"] >= prev_num_box["right"] - 1)
        check("19 (geometry): previous number sits directly below current (stacked, not side-by-side)", prev_num_box["top"] > current_box["bottom"] - 2)

        # ---------- Model Analysis: same geometry check (Gate 25) ----------
        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(100)
        page.select_option("#dbFixtureSelect", "model_analysis_parcelamento_completo")
        page.wait_for_timeout(150)
        page.click('#dbSubnav .dbModeBtn[data-mode="modelos"]')
        page.select_option("#dbComparisonFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(250)
        model_cell = page.query_selector(".dbModelSection table tbody tr td:nth-child(5)")  # Produção column
        m_current = model_cell.eval_on_selector(".dbNumCurrent", "el => el.getBoundingClientRect()")
        m_prev = model_cell.eval_on_selector(".dbPrevNum", "el => el.getBoundingClientRect()")
        check("25 (geometry, Modelos): current and previous number share the same right edge", abs(m_current["right"] - m_prev["right"]) <= 1)
        check("27: no monetary value wraps into multiple lines (single-line current, single-line previous)", m_current["height"] < 20 and m_prev["height"] < 20)

        # ---------- No page-level horizontal overflow at any of the checked viewports (Gate 26) ----------
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("26: no page-level horizontal clipping introduced by the alignment fix", overflow <= 1)

        page.close()
        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print("\n=== Dashbi FC-1.2 Alignment Structure: %d/%d ===" % (passed, len(results)))
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
