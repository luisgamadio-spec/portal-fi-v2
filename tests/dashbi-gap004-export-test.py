#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-2 (GAP-004) -- XLSX export parity test for Dash BI's "Exportar Excel"
button (restores V1's exportarResumoCSV(), analise-geral-grupo-secure-
original-layout.html -- confirmed orphaned/unreachable in V1 production,
but its own field/scope contract is what's being restored here).

Contract under test (V1 exportarResumoCSV(), read at
portal-financiamento-brabus-secure@4d8ce1d):
  const rows = rowsFromAgg(A.shareLojaDept,"Grupo").map(r=>({
    Grupo, Vendas, Financiamentos, Penetracao, Receita, ReceitaSPF,
    ReceitaTotal, Producao, Retorno, MediaParcelas, MediaPMT, Balao,
    Linear, ValorMedioBalao
  }));
Source: lastResults.aggs.shareLojaDept -- the FULL cross-department
"Loja | Dept" aggregate, captured BEFORE any department-view filter (V2's
own currentDeptView equivalent). Sheet name "Resumo".

This test never invokes a real browser download: XLSX.writeFile is
monkey-patched in-page to capture the workbook object (SheetNames + a
type-preserving dump of every cell), which is read back via
page.evaluate -- "programmatically reopen/inspect", this Wave's Gate 34,
rather than a superficial "button exists" check.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "dashbi-fixtures.json")
BASE = "http://localhost:8700/portal-next-v2/tests/_dashbi-real-provider-harness.html"
CSS_FILES = ["../design-system-2/tokens.css", "assets/css/module-system.css", "assets/css/dashbi.css"]

EXPECTED_HEADERS = ["Grupo", "Vendas", "Financiamentos", "Penetracao", "Receita", "ReceitaSPF",
                     "ReceitaTotal", "Producao", "Retorno", "MediaParcelas", "MediaPMT",
                     "Balao", "Linear", "ValorMedioBalao"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


def make_b1(vendedor, modelo, valor, cliente, chassi, data="2026-03-01", transacao="V21"):
    # deptFromBase01 (dashbi.adapter.js) reads "Transação": "U21" -> Seminovos,
    # "V21"/"VD" -> Novos -- dept comes from THIS field, not from which
    # fixture array (b1Hist.../b1Nova...) the row happens to be placed in.
    return {"Transação": transacao, "Chassi": chassi, "Data Venda": data, "Nome Vendedor": vendedor, "Modelo": modelo, "Valor Venda": valor, "Nome Cliente": cliente}


def make_b2(vendedor, modelo, financiado, receita, receita_spf, cliente, cod_tipo="N", data="2026-03-01"):
    return {"FINANCIADO": 1, "DESCRICAO": "FINANCIAMENTO", "VALOR_FINANCIADO": financiado, "RECEITA": receita, "RECEITA_SPF": receita_spf, "NOME_VENDEDOR": vendedor, "DES_MODELO": modelo, "CLIENTE": cliente, "CPF": "", "COD_TIPO_VENDA": cod_tipo, "Chassi": "", "Data Venda": data}


# ---- Fixture A: 1 store, BOTH Novos and Seminovos transactions (dept comes
# from the "Transação"/COD_TIPO_VENDA field itself, per deptFromBase01/
# deptFromBase02 -- confirmed by direct source read, NOT from which fixture
# array a row is placed in), plus special characters in the seller/store
# name -- proves the export is dept-scope-independent (shareLojaDept, not
# deptOut) and that accented text flows through cleanly (Gate 33) even
# though V2's existing, pre-FC-2 store-name canonicalization intentionally
# upper-cases and strips accents for the aggregation key (resolveLoja) --
# not a defect, the same normalization every other Dash BI table already
# applies, verified separately via the canonical-pipeline-parity check above.
SELLER_ACCENTED = "JOÃO D'ÁVILA-PÉREZ"
FIXTURE_A = {
    "id": "fc2_gap004_export",
    "description": "FC-2 GAP-004 export parity fixture.",
    # Both dept variants go through the "Hist" arrays -- confirmed by direct
    # in-browser inspection that A.compute()'s "Nova" ingestion path requires
    # a separate chassis-matched lookup (b3Rows join) unrelated to GAP-004's
    # own scope, and dept is decided by the Transação/COD_TIPO_VENDA field
    # value regardless of which array a row is placed in (deptFromBase01/
    # deptFromBase02, dashbi.adapter.js).
    "b1HistRows": [
        make_b1(SELLER_ACCENTED, "OUTLANDER", 150000, "CLI1", "CHS1", transacao="U21"),
        make_b1("MARIA SOUZA", "TRITON", 120000, "CLI2", "CHS2", transacao="U21"),
        make_b1(SELLER_ACCENTED, "OUTLANDER", 180000, "CLI3", "CHS3", transacao="V21"),
    ],
    "b2HistRows": [
        make_b2(SELLER_ACCENTED, "OUTLANDER", 150000, 8000, 500, "CLI1", cod_tipo="U"),
        make_b2("MARIA SOUZA", "TRITON", 120000, 6000, 0, "CLI2", cod_tipo="U"),
        make_b2(SELLER_ACCENTED, "OUTLANDER", 180000, 9000, 0, "CLI3", cod_tipo="N"),
    ],
    "b1NovaRows": [], "b2NovaRows": [],
    "b3Rows": [],
    "vendorRows": [
        {"NBS": "V1", "Nome": SELLER_ACCENTED, "Loja": "Loja Nações"},
        {"NBS": "V2", "Nome": "MARIA SOUZA", "Loja": "Loja Nações"},
    ],
}

# ---- Fixture B: no sales/financing rows at all -- exercises the empty
# controlled-message path (Gate 30: no silently misleading empty workbook).
FIXTURE_B_EMPTY = {
    "id": "fc2_gap004_export_empty",
    "description": "FC-2 GAP-004 empty-dataset fixture.",
    "b1HistRows": [], "b2HistRows": [], "b1NovaRows": [], "b2NovaRows": [], "b3Rows": [],
    "vendorRows": [],
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
    # Install the capture hook BEFORE any export click.
    page.evaluate("""
        window.__CAPTURED = null;
        window.__WRITEFILE_CALLS = 0;
        var _orig = XLSX.writeFile;
        XLSX.writeFile = function(wb, filename, opts) {
            window.__WRITEFILE_CALLS++;
            var dump = { filename: filename, sheetNames: wb.SheetNames.slice(), sheets: {} };
            wb.SheetNames.forEach(function(name){
                var ws = wb.Sheets[name];
                var ref = ws['!ref'];
                var range = XLSX.utils.decode_range(ref);
                var grid = [];
                for (var r = range.s.r; r <= range.e.r; r++) {
                    var row = [];
                    for (var c = range.s.c; c <= range.e.c; c++) {
                        var addr = XLSX.utils.encode_cell({r:r, c:c});
                        var cell = ws[addr];
                        row.push(cell ? { v: (cell.v instanceof Date ? cell.v.toISOString() : cell.v), t: cell.t } : null);
                    }
                    grid.push(row);
                }
                dump.sheets[name] = grid;
            });
            window.__CAPTURED = dump;
        };
        void 0;
    """)
    return page


def select_fixture(page, fixture_id):
    page.select_option("#dbFixtureSelect", fixture_id)
    page.wait_for_timeout(50)


def click_export(page):
    page.click("#dbExportResumoBtn")
    page.wait_for_timeout(50)


def get_captured(page):
    return page.evaluate("window.__CAPTURED")


def get_writefile_calls(page):
    return page.evaluate("window.__WRITEFILE_CALLS")


def independent_expected_rows(page, fixture):
    """Recompute the expected export rows independently, via the SAME
    public adapter API (A.compute + A.rowsFromAgg) the export itself uses,
    over the full un-filtered fixture input -- proves the export reads the
    canonical pipeline's output, not a second/duplicated computation."""
    input_json = json.dumps({
        "b1HistRows": fixture["b1HistRows"], "b2HistRows": fixture["b2HistRows"],
        "b1NovaRows": fixture["b1NovaRows"], "b2NovaRows": fixture["b2NovaRows"],
        "b3Rows": fixture["b3Rows"], "vendorRows": fixture["vendorRows"],
    })
    return page.evaluate("""(inputJson) => {
        var A = window.NX_DASHBI_ADAPTER;
        A.setVendors(JSON.parse(inputJson).vendorRows);
        var out = A.compute(JSON.parse(inputJson));
        var rows = A.rowsFromAgg(out.aggs.shareLojaDept, 'Grupo');
        return rows.map(function(r){
            return [r.Grupo, r.vendas||0, r.fin||0, r.penetracao||0, r.receita||0,
                r.receitaSPF||0, r.receitaTotal||((r.receita||0)+(r.receitaSPF||0)),
                r.producao||0, r.retorno||0, r.parcelasMed||0, r.pmtMed||0,
                r.balaoQtd||0, r.linearQtd||0, r.balaoMed||0];
        });
    }""", input_json)


def run(playwright):
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        golden_cases = json.load(f)["cases"]

    def with_golden(*extra):
        # The harness's initial NX_DASHBI_PAGE.render() call renders
        # currentFixtureId ('multi_loja_vendedor') BEFORE this test gets a
        # chance to select a different one -- the golden set must stay
        # present in every route-mock response, same technique as FC-1.3's
        # own dashbi-fc13-readability-test.py.
        return json.dumps({"cases": golden_cases + list(extra)})

    browser = playwright.chromium.launch()
    try:
        # ---- Test group 1: happy path, Grupo view (default) ----
        page = mount(browser, with_golden(FIXTURE_A))
        select_fixture(page, "fc2_gap004_export")
        click_export(page)
        cap = get_captured(page)

        check("writeFile called exactly once", get_writefile_calls(page) == 1)
        check("capture non-null", cap is not None)
        if cap:
            check("sheet name is 'Resumo'", cap["sheetNames"] == ["Resumo"])
            check(".xlsx extension", cap["filename"].endswith(".xlsx"))
            check("filename has no illegal filesystem chars", not any(ch in cap["filename"] for ch in '<>:"/\\|?*'))
            check("filename identifies module (DashBI/Resumo)", "Resumo" in cap["filename"] and "DashBI" in cap["filename"])

            grid = cap["sheets"]["Resumo"]
            header_row = [c["v"] if c else None for c in grid[0]]
            check("header row matches V1 contract exactly (order+labels)", header_row == EXPECTED_HEADERS)

            data_rows = [[c["v"] if c else None for c in row] for row in grid[1:]]
            expected_rows = independent_expected_rows(page, FIXTURE_A)
            # Sort both by Grupo key for order-independent comparison (dict
            # key iteration order is not part of the contract being tested).
            data_sorted = sorted(data_rows, key=lambda r: r[0])
            expected_sorted = sorted(expected_rows, key=lambda r: r[0])
            check("row count matches independently-recomputed canonical rows", len(data_sorted) == len(expected_sorted))
            if len(data_sorted) == len(expected_sorted):
                all_match = True
                for got, exp in zip(data_sorted, expected_sorted):
                    if got[0] != exp[0]:
                        all_match = False
                        break
                    for gv, ev in zip(got[1:], exp[1:]):
                        if abs((gv or 0) - (ev or 0)) > 0.005:
                            all_match = False
                            break
                check("every row's values match canonical pipeline output within rounding tolerance", all_match)

            # Dept-scope independence: shareLojaDept must contain BOTH the
            # Novos and Seminovos rows for this Loja -- proving the export is
            # NOT limited to whatever currentDeptView the visible table
            # happens to be showing. resolveLoja() (pre-existing, frozen V2
            # business logic, confirmed by direct source read) upper-cases
            # and strips accents for the aggregation key -- "Loja Nações"
            # canonicalizes to "LOJA NACOES", the SAME transformation every
            # other Dash BI table already applies; this is not a GAP-004
            # defect, so the assertion targets the canonical form.
            groups = [r[0] for r in data_rows]
            check("export contains the Novos row for the store (dept-independent scope)", any("NACOES | Novos" in (g or "") for g in groups))
            check("export contains the Seminovos row for the store (dept-independent scope)", any("NACOES | Seminovos" in (g or "") for g in groups))

            # Special characters (Gate 33): the accented/apostrophe/hyphen
            # seller name is not itself a GAP-004 export field (Grupo is
            # "Loja | Dept" only, per V1's own contract) -- what matters here
            # is that the Loja's accented input reaches the cell as a CLEAN
            # canonicalized string (no mojibake/corruption), which the
            # canonical-pipeline-parity check above already proves byte-for-
            # byte (export vs. independently-recomputed rows). This assertion
            # additionally confirms the normalized text itself is legible.
            check("Loja text in Grupo cell is clean, non-corrupted text (no mojibake)", any("LOJA NACOES" in (g or "") for g in groups))

            # Type inspection (Gate 32): Vendas/Financiamentos/Balao/Linear
            # are numeric cells (t == 'n'), Grupo is a string cell (t == 's').
            for row in grid[1:]:
                check("Grupo cell is a string ('s') cell, row=" + str(row[0]["v"] if row[0] else None), row[0] and row[0]["t"] == "s")
                for idx, name in [(1, "Vendas"), (2, "Financiamentos"), (11, "Balao"), (12, "Linear")]:
                    cell = row[idx]
                    check(name + " cell is numeric ('n'), row=" + str(row[0]["v"] if row[0] else None), cell is not None and cell["t"] == "n")

            # No FC-1 comparison-UI or HTML/markup leakage into any cell.
            leaked = False
            for row in grid:
                for cell in row:
                    if cell and isinstance(cell["v"], str) and any(bad in cell["v"] for bad in ["<", ">", "▲", "▼", "Anterior:"]):
                        leaked = True
            check("no HTML/comparison-arrow artifacts leaked into any cell", not leaked)

        # ---- Test group 2: department-view independence when a NON-Grupo
        # view is active on screen (clicks 'Novos' button, THEN exports) ----
        page2 = mount(browser, with_golden(FIXTURE_A))
        select_fixture(page2, "fc2_gap004_export")
        page2.click(".dbViewBtn[data-view='Novos']")
        page2.wait_for_timeout(50)
        click_export(page2)
        cap2 = get_captured(page2)
        if cap2:
            grid2 = cap2["sheets"]["Resumo"]
            groups2 = [ (row[0]["v"] if row[0] else None) for row in grid2[1:] ]
            check("export while 'Novos' view active still includes Seminovos rows (scope != on-screen dept filter)",
                  any("Seminovos" in (g or "") for g in groups2))

        # ---- Test group 3: empty dataset -> controlled message, no file ----
        page3 = mount(browser, with_golden(FIXTURE_B_EMPTY))
        select_fixture(page3, "fc2_gap004_export_empty")
        click_export(page3)
        status_text = page3.inner_text("#dbExportResumoStatus")
        check("empty dataset shows a controlled message (not a crash/misleading empty file)",
              "dado" in status_text.lower() or "disponível" in status_text.lower())
        check("empty dataset does NOT call XLSX.writeFile", get_writefile_calls(page3) == 0)

        # ---- Test group 4: larger dataset completes without freezing ----
        many_sellers = []
        b1h, b2h = [], []
        for i in range(400):
            nome = "VENDEDOR %04d" % i
            loja = "Loja %02d" % (i % 12)
            many_sellers.append({"NBS": "V%d" % i, "Nome": nome, "Loja": loja})
            b1h.append(make_b1(nome, "OUTLANDER", 100000 + i, "CLI%d" % i, "CHS%d" % i))
            b2h.append(make_b2(nome, "OUTLANDER", 100000 + i, 5000, 0, "CLI%d" % i))
        fixture_large = {
            "id": "fc2_gap004_export_large", "description": "perf",
            "b1HistRows": b1h, "b2HistRows": b2h, "b1NovaRows": [], "b2NovaRows": [], "b3Rows": [],
            "vendorRows": many_sellers,
        }
        page4 = mount(browser, with_golden(fixture_large))
        select_fixture(page4, "fc2_gap004_export_large")
        t0 = time.time()
        click_export(page4)
        elapsed = time.time() - t0
        cap4 = get_captured(page4)
        check("large dataset (400 sellers/12 lojas) export completes quickly (<5s), no arbitrary row cap",
              cap4 is not None and elapsed < 5.0)
        if cap4:
            check("large dataset export row count == 12 (one per Loja|Dept combo, no cap)",
                  len(cap4["sheets"]["Resumo"]) - 1 == 12)

    finally:
        browser.close()


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
