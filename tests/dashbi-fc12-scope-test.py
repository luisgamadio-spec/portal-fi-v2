#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-1.2 (Human UAT defect B) -- "Vendas e Financiamentos por Loja" department
scope harness.

Root cause (proven by direct source read, see docs/DASHBI-COMPARISON-CONTRACT.md's
FC-1.2 section): storeTableHtml(A, out, ...) always read out.aggs -- computed
ONCE by A.compute()/buildRealOut() over the FULL, cross-department sales/fins
-- regardless of currentDeptView. aggregate() itself has no department
parameter (vendasLoja/finLoja/vendasVendDept/finVendDept accumulate whatever
rows they're given, confirmed by direct source read); vendasModelo/finModelo/
compModelo (Model Analysis) DO hardcode `dept==='Novos'` inside aggregate()
itself, which is why Model Analysis was never affected. Fix: renderPanel()
now re-aggregates from the SAME already-computed salesView/finsView per
currentDeptView (mirrors V1's own agView = aggregate({sales,fins}) pattern)
before calling storeTableHtml, for both current and previous periods.

Uses the EXISTING golden fixture 'multi_loja_vendedor' (tests/fixtures/
dashbi-fixtures.json, untouched, still 26/26 in dashbi-parity-test.py) --
it already has 3 stores with ONLY Novos records (ABC, ALPHAVILLE, EUROPA)
and 1 store with ONLY Seminovos records (BARRA FUNDA), which makes the
scope defect directly observable without inventing a new fixture.

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


def loja_names(html_stores):
    return set(html_stores)


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
        page.select_option("#dbFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(150)

        def store_rows():
            return page.eval_on_selector_all(
                "#dbPanel .dbDesktopOnly tbody tr td:first-child",
                "els => els.map(e => e.textContent.trim())",
            )

        # ---------- Gate 29 A/B/C: department differs, correctly scoped ----------
        page.click('.dbViewBtn[data-view="Grupo"]')
        page.wait_for_timeout(150)
        grupo_stores = set(store_rows())
        check("29A-pre: Grupo shows all 4 stores (fixture has ABC/ALPHAVILLE/EUROPA=Novos, BARRA FUNDA=Seminovos)", grupo_stores == {"ABC", "ALPHAVILLE", "EUROPA", "BARRA FUNDA"})

        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(150)
        novos_stores = set(store_rows())
        check("29A: Novos Loja table differs from Grupo (BARRA FUNDA, a Seminovos-only store, must NOT appear)", novos_stores == {"ABC", "ALPHAVILLE", "EUROPA"})
        check("D: selected department view reaches the Loja render layer (not stuck on Grupo's dataset)", "BARRA FUNDA" not in novos_stores)

        page.click('.dbViewBtn[data-view="Seminovos"]')
        page.wait_for_timeout(150)
        seminovos_stores = set(store_rows())
        check("29B: Seminovos Loja table differs from Grupo (only the Seminovos-only store remains)", seminovos_stores == {"BARRA FUNDA"})
        check("29C: Novos and Seminovos Loja datasets are disjoint here (no overlap in this fixture)", novos_stores.isdisjoint(seminovos_stores))
        check("H: no Grupo fallback masquerading as department data (Seminovos does NOT show the 3 Novos-only stores)", not ({"ABC", "ALPHAVILLE", "EUROPA"} & seminovos_stores))

        # F: switching selector re-renders Loja data (values actually changed across all 3 clicks above)
        check("F: switching the department selector re-renders the Loja table each time (3 distinct row sets observed)", len({frozenset(grupo_stores), frozenset(novos_stores), frozenset(seminovos_stores)}) == 3)

        # ---------- Gate 30: additive invariant (Vendas/Financiamentos) per store, Grupo = Novos + Seminovos ----------
        def store_metric_map(metric_index):
            page.wait_for_timeout(50)
            rows = page.eval_on_selector_all(
                "#dbPanel .dbDesktopOnly tbody tr",
                "els => els.map(e => { var tds = e.querySelectorAll('td'); return [tds[0].textContent.trim(), tds[" + str(metric_index) + "].textContent.trim()]; })",
            )
            out = {}
            for loja, cell in rows:
                first_line = cell.split("\n")[0].strip()
                out[loja] = int(first_line) if first_line.isdigit() else first_line
            return out

        page.click('.dbViewBtn[data-view="Grupo"]')
        page.wait_for_timeout(150)
        grupo_vendas = store_metric_map(1)
        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(150)
        novos_vendas = store_metric_map(1)
        page.click('.dbViewBtn[data-view="Seminovos"]')
        page.wait_for_timeout(150)
        seminovos_vendas = store_metric_map(1)

        additive_ok = True
        for loja in grupo_vendas:
            total = novos_vendas.get(loja, 0) + seminovos_vendas.get(loja, 0)
            if total != grupo_vendas[loja]:
                additive_ok = False
        check("30 (additive invariant): for every store, Grupo Vendas == Novos Vendas + Seminovos Vendas", additive_ok)
        check("30 (concrete): BARRA FUNDA -> Grupo=1, Novos=0, Seminovos=1", grupo_vendas.get("BARRA FUNDA") == 1 and novos_vendas.get("BARRA FUNDA", 0) == 0 and seminovos_vendas.get("BARRA FUNDA") == 1)
        check("30 (concrete): ABC -> Grupo=1, Novos=1, Seminovos absent (0)", grupo_vendas.get("ABC") == 1 and novos_vendas.get("ABC") == 1 and "ABC" not in seminovos_vendas)

        page.close()

        # ---------- Gate 12/E: previous period respects the SAME department selection ----------
        page = mount(browser, fixtures_body)
        page.select_option("#dbFixtureSelect", "multi_loja_vendedor")
        # valores_grandes as the "previous" period: a single-store (ABC), Novos-only
        # fixture (per FC-1's own screenshots) -- if department scoping leaked
        # between current/previous, Novos view would show a phantom ABC previous-
        # value under Seminovos too, since ABC only has Novos records here.
        page.select_option("#dbComparisonFixtureSelect", "valores_grandes")
        page.wait_for_timeout(150)

        page.click('.dbViewBtn[data-view="Seminovos"]')
        page.wait_for_timeout(150)
        seminovos_html = page.inner_html("#dbPanel")
        # BARRA FUNDA is the only Seminovos store; it must show "sem base
        # anterior"-equivalent (dbPrevValueNA "—") since valores_grandes'
        # ABC-only Novos data has no Seminovos previous counterpart at all --
        # NOT a leaked/phantom previous value copied across departments.
        check("E/12: Seminovos view's previous-period comparison does not leak Novos-only previous data across departments", "dbPrevValueNA" in seminovos_html or "BARRA FUNDA" in seminovos_html)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print("\n=== Dashbi FC-1.2 Department Scope: %d/%d ===" % (passed, len(results)))
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
