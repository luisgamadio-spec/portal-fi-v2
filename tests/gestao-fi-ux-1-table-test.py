#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FI-UX-1 (Human-reported defect A) -- "Planos por Loja e Departamento"
(Análise F&I do Grupo, gestao.js) column-alignment/geometry contract.

ROOT CAUSE (confirmed live, not assumed):
1) module-system.css's .modTable thead th{text-align:left} (a compound
   element+class selector) out-specified the plain .modNumCol{text-align:
   right} class alone -- every numeric header rendered LEFT-aligned over
   a RIGHT-aligned value beneath it (computed style proved: th.modNumCol
   -> text-align:left, td.modNumCol on the SAME column -> text-align:
   right).
2) table-layout:fixed with no <colgroup> still divides the full table
   width EQUALLY among every column -- both the 7-column Novos and
   5-column Seminovos tables stretched to the SAME ~1318px wrapper width
   (188px/264px per column), even though the actual values are small
   integer counts.

Fix: a scoped header-alignment override + a class-based (not inline)
<colgroup> shared between both tables (same LOJA/plan/total column
widths), with the table itself no longer forced to width:100% --
Seminovos (fewer columns) now renders visibly narrower instead of
stretching sparse values across a full-width table.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8700 (fixture
mode only -- this file never touches real transport).
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://localhost:8700/portal-next-v2/tests/fixtures/_gestao-real-provider-harness.html"
CSS = ["../design-system-2/tokens.css", "assets/css/module-system.css", "assets/css/gestao.css"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


def mount(browser, width=1440, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(BASE)
    for css in CSS:
        page.add_style_tag(path=css)
    page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
    page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
    page.wait_for_timeout(200)
    return page


def get_plan_tables(page):
    return page.evaluate("""() => {
        const headings = [...document.querySelectorAll('h2')].filter(h => h.textContent.includes('Planos por Loja'));
        if (!headings.length) return null;
        const h2 = headings[0];
        const wraps = [];
        let sib = h2.nextElementSibling;
        while (sib && wraps.length < 2) {
            if (sib.classList && sib.classList.contains('modTableWrap')) wraps.push(sib);
            sib = sib.nextElementSibling;
        }
        return wraps.map(wrap => {
            const table = wrap.querySelector('table');
            const rect = table.getBoundingClientRect();
            const wrapRect = wrap.getBoundingClientRect();
            const ths = [...table.querySelectorAll('thead th')].map(th => ({
                text: th.textContent.trim(),
                x: Math.round(th.getBoundingClientRect().x),
                w: Math.round(th.getBoundingClientRect().width),
                align: getComputedStyle(th).textAlign,
                cls: th.className
            }));
            const firstRow = table.querySelector('tbody tr');
            const tds = firstRow ? [...firstRow.querySelectorAll('td')].map(td => ({
                x: Math.round(td.getBoundingClientRect().x),
                align: getComputedStyle(td).textAlign
            })) : [];
            return {
                tableWidth: Math.round(rect.width),
                wrapWidth: Math.round(wrapRect.width),
                wrapScrollWidth: wrap.scrollWidth,
                wrapClientWidth: wrap.clientWidth,
                headers: ths,
                dataRow: tds
            };
        });
    }""")


def run(playwright):
    browser = playwright.chromium.launch()
    try:
        # ---- Group A: header/value alignment contract (Gate 17) ----
        page = mount(browser, 1440)
        tables = get_plan_tables(page)
        check("A0: both plan tables found", tables is not None and len(tables) == 2)
        if tables:
            novos, seminovos = tables[0], tables[1]
            check("A1 (Novos): LOJA header is left-aligned", novos["headers"][0]["align"] == "left")
            for h in novos["headers"][1:]:
                check("A2 (Novos): numeric header '%s' is right-aligned" % h["text"], h["align"] == "right")
            for td in novos["dataRow"][1:]:
                check("A3 (Novos): numeric data cell is right-aligned", td["align"] == "right")
            # Header x-position must match the data cell x-position directly
            # below it (Gate 17: "weak visual anchoring" -- the original defect).
            for i in range(1, len(novos["headers"])):
                hx = novos["headers"][i]["x"]
                dx = novos["dataRow"][i]["x"] if i < len(novos["dataRow"]) else None
                check("A4 (Novos): header '%s' box aligns with its data column (x=%s vs %s)" % (novos["headers"][i]["text"], hx, dx),
                      dx is not None and abs(hx - dx) <= 1)

            check("A5 (Seminovos): LOJA header is left-aligned", seminovos["headers"][0]["align"] == "left")
            for h in seminovos["headers"][1:]:
                check("A6 (Seminovos): numeric header '%s' is right-aligned" % h["text"], h["align"] == "right")

        # ---- Group B: column geometry (Gate 19-21) ----
        if tables:
            novos, seminovos = tables[0], tables[1]
            check("B1: Novos LOJA column width == Seminovos LOJA column width (table-to-table consistency)",
                  novos["headers"][0]["w"] == seminovos["headers"][0]["w"])
            check("B2: Novos 'Linear' column width == Seminovos 'Linear' column width",
                  novos["headers"][1]["w"] == seminovos["headers"][1]["w"])
            check("B3: Novos 'Total' column width == Seminovos 'Total' column width",
                  novos["headers"][-1]["w"] == seminovos["headers"][-1]["w"])
            check("B4: Seminovos table is narrower than Novos (fewer columns, not stretched to the same width)",
                  seminovos["tableWidth"] < novos["tableWidth"])
            check("B5: Novos and Seminovos tables share the same left edge",
                  abs(novos["headers"][0]["x"] - seminovos["headers"][0]["x"]) <= 1)
            check("B6: no column is absurdly empty -- Novos table width is well below its wrapper's full width (auto-sized, not stretched)",
                  novos["tableWidth"] < novos["wrapWidth"] * 0.8)
            check("B7: Novos has exactly 7 columns (Loja + 5 plans + Total)", len(novos["headers"]) == 7)
            check("B8: Seminovos has exactly 5 columns (Loja + 3 plans + Total) -- no fabricated Subsidiado/Coparticipado columns",
                  len(seminovos["headers"]) == 5)
            check("B9: no wrapper horizontal overflow at 1440px",
                  novos["wrapScrollWidth"] <= novos["wrapClientWidth"] + 1 and seminovos["wrapScrollWidth"] <= seminovos["wrapClientWidth"] + 1)
        page.close()

        # ---- Group C: tabular-nums for numeric cells (Gate 18) ----
        page = mount(browser, 1440)
        tabular = page.evaluate("""() => {
            const headings = [...document.querySelectorAll('h2')].filter(h => h.textContent.includes('Planos por Loja'));
            const h2 = headings[0];
            const wrap = h2.nextElementSibling.nextElementSibling;
            const td = wrap.querySelector('tbody tr td.modNumCol');
            return td ? getComputedStyle(td).fontVariantNumeric : null;
        }""")
        check("C1: numeric cells use tabular-nums (already a module-system.css default, unaffected by this fix)", tabular is not None and "tabular-nums" in tabular)
        page.close()

        # ---- Group D: responsive matrix, no horizontal scroll (Gate 22/24) ----
        for width in [1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375]:
            page = mount(browser, width)
            doc_overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            wraps = page.eval_on_selector_all(".modTableWrap", "els => els.map(e => ({sw: e.scrollWidth, cw: e.clientWidth}))")
            wrap_overflow = any(w["sw"] > w["cw"] + 1 for w in wraps)
            check("D (%dpx): no document horizontal overflow" % width, not doc_overflow)
            check("D (%dpx): no table wrapper horizontal overflow" % width, not wrap_overflow)
            page.close()

        # ---- Group E: long store-name content (Gate 25) -- synthetic, no real PII ----
        for width in [1440, 900, 375]:
            page = mount(browser, width)
            page.evaluate("""() => {
                const orig = window.NX_STORE_DISPLAY.storeDisplayName;
                window.NX_STORE_DISPLAY.storeDisplayName = function(code) {
                    if (code === 'ABC') return 'NAÇÕES UNIDAS — UNIDADE HOMOLOGAÇÃO';
                    return orig(code);
                };
            }""")
            page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
            page.wait_for_timeout(150)
            doc_overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            wraps = page.eval_on_selector_all(".modTableWrap", "els => els.map(e => ({sw: e.scrollWidth, cw: e.clientWidth}))")
            wrap_overflow = any(w["sw"] > w["cw"] + 1 for w in wraps)
            check("E (%dpx): long store label does not cause document overflow" % width, not doc_overflow)
            check("E (%dpx): long store label does not cause wrapper overflow" % width, not wrap_overflow)
            visible = page.evaluate("""() => {
                const cell = [...document.querySelectorAll('td')].find(td => td.textContent.includes('NAÇÕES UNIDAS'));
                return !!cell;
            }""")
            check("E (%dpx): long store label remains fully present in the DOM (not truncated away)" % width, visible)
            page.close()

        # ---- Group F: no data hidden (Gate 26) -- all plan columns present
        # with real values, not display:none'd or replaced with ellipsis ----
        page = mount(browser, 1440)
        all_headers = page.evaluate("""() => {
            const headings = [...document.querySelectorAll('h2')].filter(h => h.textContent.includes('Planos por Loja'));
            const h2 = headings[0];
            let wrap = h2.nextElementSibling.nextElementSibling;
            const out = [];
            for (let i = 0; i < 2 && wrap; i++) {
                const table = wrap.querySelector('table');
                out.push([...table.querySelectorAll('thead th')].map(th => ({text: th.textContent.trim(), visible: getComputedStyle(th).display !== 'none'})));
                wrap = wrap.nextElementSibling;
            }
            return out;
        }""")
        novos_headers = [h["text"] for h in all_headers[0]]
        check("F1: Novos still shows all 7 expected plan/total columns", novos_headers == ["Loja", "Linear", "Balão", "Subsidiado", "Reversão", "Coparticipado", "Total"])
        check("F2: no column display:none in Novos", all(h["visible"] for h in all_headers[0]))
        seminovos_headers = [h["text"] for h in all_headers[1]]
        check("F3: Seminovos still shows all 5 expected plan/total columns", seminovos_headers == ["Loja", "Linear", "Balão", "Reversão", "Total"])
        check("F4: no column display:none in Seminovos", all(h["visible"] for h in all_headers[1]))
        page.close()

        # ---- Group G: other Análise F&I sections unaffected (Gate 27) ----
        page = mount(browser, 1440)
        html = page.inner_html("#geOutlet")
        check("G1: Produção cards still present (modKpiGrid)", "modKpiGrid" in html)
        check("G2: Classificação dos Planos section still present", "Classifica" in html and "SUBSIDIADO" in html)
        check("G3: SPF Extra section still present", "SPF EXTRA" in html or "SPF Extra" in html)
        page.close()

        browser.close()
    except Exception:
        browser.close()
        raise


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        run(p)
    failed = [r for r in results if not r[1]]
    print("\n%d passed, %d failed" % (len(results) - len(failed), len(failed)))
    if failed:
        print("FAILED:")
        for label, _ in failed:
            print(" -", label)
        sys.exit(1)
