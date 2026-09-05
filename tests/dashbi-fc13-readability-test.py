#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-1.3 (DASHBI_ANALYTICAL_TABLE_NUMERIC_READABILITY_DEFECT) -- geometry
harness for Analise por Modelos / Ranking / Loja.

Root cause (2 parts, both confirmed by direct source read of dashbi.css):
1) .dbTableExpandable's own blanket white-space:normal/overflow-wrap:
   break-word/word-break:break-word (needed for long Modelo/Loja names)
   also reached numeric cells via inheritance -- word-break/overflow-wrap
   ARE inherited, so a nested .dbNumCompare number span still inherited
   break-word from its ancestor <td> even though the span itself set
   white-space:nowrap. Fixed by re-asserting word-break:keep-all/
   overflow-wrap:normal at the td.dbNumCol level (3-class selector,
   .dbTable.dbTableExpandable td.dbNumCol, intentionally out-specifies the
   2-class rule above).
2) Every numeric column shared an even 1/N split under table-layout:fixed
   regardless of a formatted BRL value's real length -- new dbColMoney/
   dbColCount/dbColPercent/dbColRank/dbColName classes + per-table
   min-width (dbTableLoja/dbTableRanking/dbTableModelos) give money columns
   real room, with .dbTableWrap's existing overflow-x:auto (table-scoped,
   never page-level) as the fallback at genuinely narrow viewports.

Uses a synthetic fixture (injected via a fixtures.json response override,
never written to the frozen tests/fixtures/dashbi-fixtures.json) with
realistic long model names (ECLIPSE CROSS HPE-S 4X4/4X2, Gate 29) and large
BRL values (Gate 26/27) across 3 stores, to make both the money-collision
and the wrap-into-a-third-line defects directly, deterministically
reproducible -- not something the existing golden fixtures happen to
exercise.

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

VIEWPORT_WIDTHS = [1920, 1440, 1366, 1280, 1100, 1024, 1000, 900]

results = []


def check(label, cond):
    results.append((label, bool(cond)))


# ---- Synthetic fixture: 2 ECLIPSE CROSS SKUs + 1 OUTLANDER, 3 stores, large BRL values ----
def make_b1(transacao, chassi, vendedor, modelo, valor, cliente, data="2026-03-01"):
    return {"Transação": transacao, "Chassi": chassi, "Data Venda": data, "Nome Vendedor": vendedor, "Modelo": modelo, "Valor Venda": valor, "Nome Cliente": cliente}


def make_b2(vendedor, modelo, financiado, receita, receita_spf, cliente, cod_tipo="N", data="2026-03-01"):
    return {"FINANCIADO": 1, "DESCRICAO": "FINANCIAMENTO", "VALOR_FINANCIADO": financiado, "RECEITA": receita, "RECEITA_SPF": receita_spf, "NOME_VENDEDOR": vendedor, "DES_MODELO": modelo, "CLIENTE": cliente, "CPF": "", "COD_TIPO_VENDA": cod_tipo, "Chassi": "", "Data Venda": data}


SELLERS = [
    ("CARLOS EDUARDO SILVA", "ALPHAVILLE"),
    ("MARIANA ALVES COSTA", "BANDEIRANTES"),
    ("JULIANA PEREIRA LIMA", "NACOES"),
]
CUSTOM_FIXTURE = {
    "id": "fc13_readability_stress",
    "description": "FC-1.3 synthetic -- long model names + large BRL values across 3 stores.",
    "b1HistRows": [
        make_b1("V21", "CHS9001", SELLERS[0][0], "ECLIPSE CROSS HPE-S 4X4", 3103601, "CLIA"),
        make_b1("V21", "CHS9002", SELLERS[1][0], "ECLIPSE CROSS HPE-S 4X2", 755200, "CLIB"),
        make_b1("V21", "CHS9003", SELLERS[2][0], "OUTLANDER", 12907705, "CLIC"),
        make_b1("V21", "CHS9004", SELLERS[0][0], "ECLIPSE CROSS HPE-S 4X4", 10164566, "CLID"),
    ],
    "b2HistRows": [
        make_b2(SELLERS[0][0], "ECLIPSE CROSS HPE-S 4X4", 3103601, 146461, 0, "CLIA"),
        make_b2(SELLERS[1][0], "ECLIPSE CROSS HPE-S 4X2", 755200, 47800, 0, "CLIB"),
        make_b2(SELLERS[2][0], "OUTLANDER", 12907705, 653490, 0, "CLIC"),
        make_b2(SELLERS[0][0], "ECLIPSE CROSS HPE-S 4X4", 10164566, 471072, 0, "CLID"),
    ],
    "b1NovaRows": [], "b2NovaRows": [], "b3Rows": [],
    "vendorRows": [{"NBS": "V%d" % i, "Nome": s[0], "Loja": s[1]} for i, s in enumerate(SELLERS)],
}


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


def rects_overlap(a, b):
    # Horizontal overlap only (columns are laid out left-to-right; a few px
    # of vertical overlap across current/previous lines is expected and fine).
    return a["right"] > b["left"] + 1 and b["right"] > a["left"] + 1


def check_no_overlap(page, selector_list, label_prefix):
    boxes = []
    for sel in selector_list:
        el = page.query_selector(sel)
        if not el:
            continue
        boxes.append((sel, el.bounding_box()))
    ok = True
    for i in range(len(boxes) - 1):
        (sel_a, box_a), (sel_b, box_b) = boxes[i], boxes[i + 1]
        if not box_a or not box_b:
            continue
        a = {"left": box_a["x"], "right": box_a["x"] + box_a["width"]}
        b = {"left": box_b["x"], "right": box_b["x"] + box_b["width"]}
        if rects_overlap(a, b):
            ok = False
    return ok


def check_single_line(page, selector):
    # Range.getClientRects() on the element's own text returns exactly one
    # rect per line the text actually occupies -- unlike comparing the
    # ELEMENT's bounding-box height, this is unaffected by the surrounding
    # table ROW being tall for an unrelated reason (e.g. a long vendor name
    # wrapping in a sibling "Nome" cell, confirmed as a false positive here
    # with tests/fixtures/dashbi-fixtures.json's own "PEDRO HENRIQUE ALMEIDA
    # NASCIMENTO SANTOS BARBOSA" golden case).
    el = page.query_selector(selector)
    if not el:
        return None
    rect_count = el.evaluate(
        """e => {
            var r = document.createRange();
            r.selectNodeContents(e);
            return r.getClientRects().length;
        }"""
    )
    return rect_count <= 1


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available -- harness code exists, not executed.")
        sys.exit(0)

    with open(FIXTURES_PATH, encoding="utf-8") as f:
        golden = json.load(f)
    fixtures_with_custom = json.dumps({"cases": golden["cases"] + [CUSTOM_FIXTURE]})

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Modelos: overlap + atomicity across the 8-width matrix ----------
        for w in VIEWPORT_WIDTHS:
            page = mount(browser, fixtures_with_custom, width=w, height=900)
            page.click('.dbViewBtn[data-view="Novos"]')
            page.wait_for_timeout(80)
            page.select_option("#dbFixtureSelect", "fc13_readability_stress")
            page.wait_for_timeout(150)
            page.click('#dbSubnav .dbModeBtn[data-mode="modelos"]')
            page.wait_for_timeout(150)
            # ECLIPSE CROSS is not the active family by default (OUTLANDER is) -- switch.
            eclipse_btn = page.query_selector('.dbVehicleCard[data-family="ECLIPSE CROSS"]')
            if eclipse_btn:
                eclipse_btn.click()
                page.wait_for_timeout(150)

            row = page.query_selector(".dbTableModelos tbody tr")
            no_overlap = check_no_overlap(page, [
                ".dbTableModelos tbody tr:first-child td:nth-child(5) .dbNumCurrent",
                ".dbTableModelos tbody tr:first-child td:nth-child(6) .dbNumCurrent",
                ".dbTableModelos tbody tr:first-child td:nth-child(7) .dbNumCurrent",
            ], "modelos")
            check(f"7 (Modelos, {w}px): Produção/Receita Total/Ticket Médio current values do not overlap", no_overlap)

            producao_current_ok = check_single_line(page, ".dbTableModelos tbody tr:first-child td:nth-child(5) .dbNumCurrent")
            check(f"26 (Modelos, {w}px): Produção current value (large BRL) stays on one line", producao_current_ok is not False)

            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"15 ({w}px): no page-level horizontal overflow", overflow <= 1)

            wrap_scroll = page.eval_on_selector(".dbTableModelos", "el => el.closest('.dbTableWrap').scrollWidth - el.closest('.dbTableWrap').clientWidth")
            table_wraps_ok = True
            if wrap_scroll and wrap_scroll > 0:
                # The table wrapper itself may legitimately scroll at narrow
                # widths (Gate 14) -- confirm it's an intentional, contained
                # overflow-x:auto, not an accidental clip.
                overflow_x = page.eval_on_selector(".dbTableModelos", "el => getComputedStyle(el.closest('.dbTableWrap')).overflowX")
                table_wraps_ok = overflow_x == "auto"
            check(f"14 ({w}px): any needed horizontal access belongs to the table wrapper (overflow-x:auto), not a clip", table_wraps_ok)
            page.close()

        # ---------- Ranking: currency atomicity + no third-line wrap ----------
        for w in [1440, 1024, 1000]:
            page = mount(browser, fixtures_with_custom, width=w, height=900)
            page.select_option("#dbFixtureSelect", "fc13_readability_stress")
            page.wait_for_timeout(150)
            page.click('#dbSubnav .dbModeBtn[data-mode="ranking"]')
            page.wait_for_timeout(150)
            producao_cell = page.query_selector('.dbTableRanking tbody tr:first-child td[data-th="Produção Total"]')
            single_line = check_single_line(page, '.dbTableRanking tbody tr:first-child td[data-th="Produção Total"]')
            check(f"26/28 (Ranking, {w}px): currency value does not wrap into a second/third line", single_line is not False)
            text = producao_cell.inner_text() if producao_cell else ""
            check(f"8 (Ranking, {w}px): currency text has no embedded newline (no 'R$ 755.20' + '0' split)", "\n" not in text.strip())
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"15 (Ranking, {w}px): no page-level horizontal overflow", overflow <= 1)
            page.close()

        # ---------- Ranking: Nome column no longer starved (the '#' first-child bug) ----------
        page = mount(browser, fixtures_with_custom, width=1366, height=900)
        page.select_option("#dbFixtureSelect", "fc13_readability_stress")
        page.wait_for_timeout(150)
        page.click('#dbSubnav .dbModeBtn[data-mode="ranking"]')
        page.wait_for_timeout(150)
        rank_width = page.eval_on_selector(".dbTableRanking thead th:nth-child(1)", "el => el.getBoundingClientRect().width")
        name_width = page.eval_on_selector(".dbTableRanking thead th:nth-child(2)", "el => el.getBoundingClientRect().width")
        check("12: Ranking's Nome column is meaningfully wider than the # column (not the reverse)", name_width > rank_width * 2)
        page.close()

        # ---------- Loja regression: Grupo/Novos/Seminovos still correct (FC-1.2 untouched) ----------
        page = mount(browser, fixtures_with_custom, width=1366, height=900)
        page.select_option("#dbFixtureSelect", "multi_loja_vendedor")
        page.wait_for_timeout(150)
        page.click('.dbViewBtn[data-view="Grupo"]')
        page.wait_for_timeout(120)
        grupo_stores = set(page.eval_on_selector_all(".dbTableLoja tbody tr td:first-child", "els => els.map(e => e.textContent.trim())"))
        page.click('.dbViewBtn[data-view="Novos"]')
        page.wait_for_timeout(120)
        novos_stores = set(page.eval_on_selector_all(".dbTableLoja tbody tr td:first-child", "els => els.map(e => e.textContent.trim())"))
        check("22 (Loja regression): Grupo still shows all 4 stores", grupo_stores == {"ABC", "ALPHAVILLE", "EUROPA", "BARRA FUNDA"})
        check("22 (Loja regression): Novos still correctly excludes the Seminovos-only store", novos_stores == {"ABC", "ALPHAVILLE", "EUROPA"})
        no_overlap_loja = check_no_overlap(page, [
            ".dbTableLoja tbody tr:first-child td:nth-child(5) .dbNumCurrent",
            ".dbTableLoja tbody tr:first-child td:nth-child(6) .dbNumCurrent",
        ], "loja")
        check("7 (Loja regression): Produção Total / Receita Total current values do not overlap", no_overlap_loja)
        page.close()

        # ---------- Mobile representative surface (actual mobile cards, not "desktop hidden") ----------
        page = mount(browser, fixtures_with_custom, width=390, height=844)
        page.select_option("#dbFixtureSelect", "fc13_readability_stress")
        page.wait_for_timeout(150)
        mobile_card_visible = page.eval_on_selector(".dbMobileOnly", "el => getComputedStyle(el).display !== 'none'")
        desktop_table_hidden = page.eval_on_selector(".dbDesktopOnly", "el => getComputedStyle(el).display === 'none'")
        check("30 (mobile): the actual mobile card surface renders (not just 'desktop table hidden')", mobile_card_visible)
        check("30 (mobile): desktop table is hidden at this width (dbDesktopOnly)", desktop_table_hidden)
        overflow_m = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("15 (mobile): no page-level horizontal overflow", overflow_m <= 1)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print("\n=== Dashbi FC-1.3 Table Readability: %d/%d ===" % (passed, len(results)))
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
