#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-2.3 (GAP-003, relocated) -- XLSX export parity test for Coparticipado's
"Exportar Coparticipados" button, now living in Gestão de Coparticipados &
Subsidiados -> Visão Coparticipados (moved here from Score by Human UAT
product-placement correction; FC-2.2's already-validated 19-column
workbook is unchanged, only its module ownership moved).

V1 contract restored: modules/coparticipado.html's OWN exportarCoparticipados()
-- a REAL, wired V1 production button (<button onclick="exportarCoparticipados()">
Exportar Coparticipados em Excel</button>, confirmed by direct source read),
byte-identical in column contract to Score's same-named (but orphaned)
function. Filename convention ("Coparticipados_Score_FI_<timestamp>.xlsx")
is unchanged deliberately: V1's OWN Coparticipado module used this EXACT
same filename for its own live button, proving "_Score_FI_" is V1's
platform-wide F&I naming, not a Score-module artifact -- not a naming
defect to correct.

Static (non-browser) checks in this file also prove single ownership
(Gate 39): score.js carries no export string/id, coparticipado.js carries
exactly one.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080 (same
convention as coparticipado-real-provider-test.py).
"""
import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "coparticipado-fixtures.json")
BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_coparticipado-real-provider-harness.html"
RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_score_coparticipated_data"
# V2_COPART_GOVERNED_RATE_AUTHORITY_CORRECTION -- real transport now
# also requires this endpoint to resolve; mount_real() routes it by
# default so every pre-existing real-mode scenario in this file keeps
# its original (COPARTICIPADO-rate-dependent) behavior.
GOVERNED_RPC_URL = "https://mock.invalid/rest/v1/rpc/simulador_get_coparticipado"
DEFAULT_GOVERNED_PAYLOAD = {
    "ok": True, "batch_id": "mock-batch-id", "arquivo_nome": "mock-taxa-coparticipado.xlsx",
    "linhas": {"matriz_modelos": [
        {"modelo": "TRITON GLS", "entrada_minima": 0.6, "rebate_total": 0.06, "rebate_hpe": 0.5, "rebate_brabus": 0.5, "prazo": 48, "taxa": 0.0099}
    ], "tx_coef": []}
}

EXPECTED_HEADERS = ["Nome do cliente", "Vendedor", "Loja vinculada", "Modelo do carro",
                     "Modelo tabela taxa", "Família do carro", "Valor de venda",
                     "Valor de entrada", "Percentual de entrada", "Valor financiado",
                     "Rebate Total", "Rebate Parte Brabus", "Valor do Rebate Total",
                     "Valor da Coparticipação", "Situação", "Prazo", "Parcela",
                     "Data da venda", "Chassi"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


# ---------------------------------------------------------------------
# Gate 39 (single owner, no duplication) -- static source checks, no
# browser needed. score.js must carry NOTHING export-related; coparticipado.js
# must carry exactly the wired capability.
# ---------------------------------------------------------------------
def check_static_ownership():
    score_js = os.path.join(HERE, "..", "assets", "js", "score.js")
    cp_js = os.path.join(HERE, "..", "assets", "js", "coparticipado.js")
    with open(score_js, encoding="utf-8") as f:
        score_src = f.read()
    with open(cp_js, encoding="utf-8") as f:
        cp_src = f.read()

    check("static: score.js has ZERO 'Exportar Coparticipados' occurrences", "Exportar Coparticipados" not in score_src)
    check("static: score.js has ZERO 'exportCoparticipadosXlsx' occurrences", "exportCoparticipadosXlsx" not in score_src)
    check("static: score.js has ZERO 'scExportCopaBtn'/'scExportStatus' occurrences", "scExportCopaBtn" not in score_src and "scExportStatus" not in score_src)
    check("static: score.js has ZERO reference to NX_COPARTICIPADO_ADAPTER (no cross-module export dependency left)", "NX_COPARTICIPADO_ADAPTER" not in score_src)
    check("static: coparticipado.js has exactly ONE 'Exportar Coparticipados' button label", cp_src.count(">Exportar Coparticipados<") == 1)
    check("static: coparticipado.js has exactly ONE exportCoparticipadosXlsx() definition", cp_src.count("function exportCoparticipadosXlsx") == 1)


def auth_mock_script(configured):
    return """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture', supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-anon-key', textEndpoint: null
};
window.NX_AUTH = {
  isAuthConfigured: %s,
  getAccessToken: function () { return Promise.resolve('mock-access-token-abc'); }
};
""" % ("true" if configured else "false")


with open(FIXTURES_PATH, encoding="utf-8") as f:
    GOLDEN = json.load(f)

EMPTY_REAL_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-05",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}

# Same real-shaped payload already reviewed/used by coparticipado-real-
# provider-test.py's own SAMPLE_PAYLOAD -- reused verbatim (not redefined
# differently) for consistency: 1 COPARTICIPADO row with a matched rate
# (TRITON GLS), 1 COPARTICIPADO row with NO matched rate (fallback path),
# and SUBSIDIADO/REVERSÃO/BALÃO/LINEAR rows that must all be excluded.
# Multiple stores/departments included for the filter-parity test (Gate 34).
REAL_SAMPLE_PAYLOAD = dict(EMPTY_REAL_PAYLOAD, sales=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "operation_reference": "***AB1234"},
], finance=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "financed_value": 150000, "return_value": 9000,
     "spf_value": 3000, "spf_count": 1, "installments": 48, "installment_value": 3200,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "EM ANDAMENTO", "operation_reference": "***AB1234"},
    {"date": "2026-08-02", "seller": "Real Seller B", "store": "SANTO AMARO", "department": "SEMINOVOS",
     "model": "OUTLANDER HPE-S", "sale_value": 220000, "financed_value": 200000, "return_value": 12000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 5800,
     "balloon_value": 0, "plan": "SUBSIDIADO", "status": "PAGA", "operation_reference": "***CD5678"},
    {"date": "2026-08-03", "seller": "Real Seller C", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "ECLIPSE CROSS HPE", "sale_value": 190000, "financed_value": 170000, "return_value": 8000,
     "spf_value": 0, "spf_count": 0, "installments": 40, "installment_value": 4200,
     "balloon_value": 0, "plan": "REVERSÃO", "status": "FATURADA", "operation_reference": "***EF9012"},
    {"date": "2026-08-06", "seller": "Real Seller F", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "MODELO SEM TAXA XYZ", "sale_value": 160000, "financed_value": 150000, "return_value": 7000,
     "spf_value": 0, "spf_count": 0, "installments": 40, "installment_value": 3000,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***KL1122"},
], rates=[
    {"model": "TRITON GLS", "term": 48, "rate": 1.99, "total_rebate": 6, "brabus_percent": 50},
])


def with_golden(*extra):
    return json.dumps({"cases": GOLDEN["cases"] + list(extra)})


CAPTURE_HOOK_JS = """
    window.__CAPTURED = null;
    window.__WRITEFILE_CALLS = 0;
    XLSX.writeFile = function(wb, filename, opts) {
        window.__WRITEFILE_CALLS++;
        var dump = { filename: filename, sheetNames: wb.SheetNames.slice(), sheets: {} };
        wb.SheetNames.forEach(function(name){
            var ws = wb.Sheets[name];
            var range = XLSX.utils.decode_range(ws['!ref']);
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
"""


def mount_fixture(browser, fixtures_body):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(False))
    page.route("**/coparticipado-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=fixtures_body))
    page.goto(BASE)
    page.wait_for_function("!!window.NX_COPARTICIPADO_PAGE", timeout=5000)
    page.evaluate("window.NX_COPARTICIPADO_PAGE.render(document.getElementById('cpOutlet'))")
    page.evaluate(CAPTURE_HOOK_JS)
    return page


def mount_real(browser, route_handler, governed_status=200, governed_payload=None):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(True))
    page.route(RPC_URL + "*", route_handler)
    body = governed_payload if governed_payload is not None else DEFAULT_GOVERNED_PAYLOAD
    page.route(GOVERNED_RPC_URL + "*", lambda route: route.fulfill(status=governed_status, content_type="application/json", body=json.dumps(body)))
    page.goto(BASE)
    page.wait_for_function("!!window.NX_COPARTICIPADO_PAGE", timeout=5000)
    page.evaluate("window.NX_COPARTICIPADO_PAGE.render(document.getElementById('cpOutlet'))")
    page.evaluate(CAPTURE_HOOK_JS)
    return page


def real_json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))
    return handler


def click_export(page):
    page.click("#cpExportCopaBtn")
    page.wait_for_timeout(100)


def run(playwright):
    check_static_ownership()

    browser = playwright.chromium.launch()
    try:
        # ---- Group A: fixture mode happy path (golden fixture, Visão
        # Coparticipados is the default view) ----
        page = mount_fixture(browser, with_golden())
        page.select_option("#cpFixtureSelect", "coparticipado_valido")
        page.wait_for_timeout(100)
        check("A1: export button present in Visão Coparticipados (default view)", page.evaluate("!!document.getElementById('cpExportCopaBtn')"))

        click_export(page)
        cap = page.evaluate("window.__CAPTURED")
        check("A2: writeFile called exactly once", page.evaluate("window.__WRITEFILE_CALLS") == 1)
        check("A3: capture non-null", cap is not None)
        if cap:
            check("A4: sheet name is 'Coparticipados'", cap["sheetNames"] == ["Coparticipados"])
            check("A5: .xlsx extension", cap["filename"].endswith(".xlsx"))
            check("A6: filename matches the V1-proven pattern (Coparticipados_Score_FI_) -- kept deliberately, see module docstring", cap["filename"].startswith("Coparticipados_Score_FI_"))
            grid = cap["sheets"]["Coparticipados"]
            header = [c["v"] if c else None for c in grid[0]]
            check("A7: header row matches the validated 19-column V1 contract exactly", header == EXPECTED_HEADERS)
            data_rows = [[c["v"] if c else None for c in row] for row in grid[1:]]
            check("A8: at least one COPARTICIPADO row exported", len(data_rows) > 0)
            for row in data_rows:
                check("A9: Nome do cliente is a non-empty string, row cliente=" + str(row[0]), isinstance(row[0], str) and len(row[0]) > 0)
                check("A10: Valor de venda numeric, row=" + str(row[0]), isinstance(row[6], (int, float)))
                check("A11: Valor financiado numeric, row=" + str(row[0]), isinstance(row[9], (int, float)))
        page.close()

        # ---- Group B: Visão Subsidiados must NOT show the export button
        # (Gate 12/33 -- no Subsidiados export in this wave) ----
        page_b = mount_fixture(browser, with_golden())
        page_b.select_option("#cpFixtureSelect", "coparticipado_valido")
        page_b.wait_for_timeout(100)
        page_b.click("#cpTabSubs")
        page_b.wait_for_timeout(100)
        check("B1: no export button in Visão Subsidiados", not page_b.evaluate("!!document.getElementById('cpExportCopaBtn')"))
        check("B2: no 'Exportar Coparticipados' text in Visão Subsidiados", "Exportar Coparticipados" not in page_b.inner_html("#cpPanel"))
        page_b.click("#cpTabCopart")
        page_b.wait_for_timeout(100)
        check("B3: export button reappears after switching back to Visão Coparticipados", page_b.evaluate("!!document.getElementById('cpExportCopaBtn')"))
        page_b.close()

        # ---- Group C: filter parity (Gate 34, critical product-placement
        # test) -- apply a Loja filter, verify exported rows are a subset
        # matching that filter, never the full unfiltered set. Two SEPARATE
        # pages (not two clicks on one page) -- exportCoparticipadosXlsx()'s
        # own 800ms double-click debounce (Gate 30) would silently swallow
        # a second click this close together on the same page, capturing
        # nothing new and leaving window.__CAPTURED stale from the first.
        store_value = None
        page_c0 = mount_fixture(browser, with_golden())
        page_c0.select_option("#cpFixtureSelect", "ALL")
        page_c0.wait_for_timeout(100)
        store_value = page_c0.eval_on_selector_all(
            "#cpStoreFilter option",
            "els => els.map(e => e.value).filter(v => v)[0] || null"
        )
        check("C0: at least one store available to filter by", store_value is not None)
        click_export(page_c0)  # unfiltered export
        cap_unfiltered = page_c0.evaluate("window.__CAPTURED")
        unfiltered_rows = len(cap_unfiltered["sheets"]["Coparticipados"]) - 1 if cap_unfiltered else 0
        page_c0.close()

        if store_value:
            page_c1 = mount_fixture(browser, with_golden())
            page_c1.select_option("#cpFixtureSelect", "ALL")
            page_c1.wait_for_timeout(100)
            page_c1.select_option("#cpStoreFilter", store_value)
            page_c1.wait_for_timeout(100)
            click_export(page_c1)
            cap_filtered = page_c1.evaluate("window.__CAPTURED")
            if cap_filtered:
                grid_f = cap_filtered["sheets"]["Coparticipados"]
                rows_f = [[c["v"] if c else None for c in row] for row in grid_f[1:]]
                filtered_lojas = set(r[2] for r in rows_f)
                check("C1: filtered export contains ONLY the selected store's rows", filtered_lojas <= {store_value})
                check("C2: filtered export row count <= unfiltered row count (strictly subtractive)", len(rows_f) <= unfiltered_rows)
                check("C3: filtered export row count is strictly SMALLER (the filter actually narrowed something, not a no-op)", len(rows_f) < unfiltered_rows)
            page_c1.close()

        # ---- Group D: empty (no COPARTICIPADO rows in filter) -> controlled
        # message, no misleading file ----
        page_d = mount_real(browser, real_json_route(200, EMPTY_REAL_PAYLOAD))
        page_d.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        click_export(page_d)
        check("D1: empty dataset shows a controlled message", "coparticipado" in page_d.inner_text("#cpExportStatus").lower())
        check("D2: empty dataset does NOT call XLSX.writeFile", page_d.evaluate("window.__WRITEFILE_CALLS") == 0)
        page_d.close()

        # ---- Group E: real mode -- full contract, cliente/chassi privacy,
        # rate lookup, plan filter, familia/valorVenda now present ----
        page_e = mount_real(browser, real_json_route(200, REAL_SAMPLE_PAYLOAD))
        page_e.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        check("E1: export button present after successful real load", page_e.evaluate("!!document.getElementById('cpExportCopaBtn')"))
        click_export(page_e)
        cap_e = page_e.evaluate("window.__CAPTURED")
        check("E2: writeFile called exactly once (real mode)", page_e.evaluate("window.__WRITEFILE_CALLS") == 1)
        if cap_e:
            grid_e = cap_e["sheets"]["Coparticipados"]
            header_e = [c["v"] if c else None for c in grid_e[0]]
            check("E3: real-mode header matches the same 19-column contract", header_e == EXPECTED_HEADERS)
            data_e = [[c["v"] if c else None for c in row] for row in grid_e[1:]]
            check("E4: only the 2 COPARTICIPADO rows exported (of 4 finance rows; SUBSIDIADO/REVERSÃO excluded)", len(data_e) == 2)
            by_vendor = {r[1]: r for r in data_e}

            r_a = by_vendor.get("Real Seller A")
            check("E5: Real Seller A row present", r_a is not None)
            if r_a:
                check("E6: Nome do cliente == 'Operação protegida' (never a real name)", r_a[0] == "Operação protegida")
                check("E7: Loja vinculada", r_a[2] == "BARRA FUNDA")
                check("E8: Modelo do carro == raw RPC model", r_a[3] == "TRITON GLS")
                check("E9: Modelo tabela taxa resolved via real rates[] (rate lookup works end-to-end)", r_a[4] == "TRITON GLS")
                check("E10: Família do carro present (familia now retained on real fins, FC-2.3 addition)", r_a[5] == "Triton")
                check("E11: Valor de venda numeric and correct (valorVenda now retained, FC-2.3 addition)", abs(r_a[6] - 180000) < 0.01)
                check("E12: Rebate Total == normalized real rate (6% -> 0.06)", abs(r_a[10] - 0.06) < 0.0001)
                check("E13: Rebate Parte Brabus == normalized real rate (50% -> 0.5)", abs(r_a[11] - 0.5) < 0.0001)
                check("E14: Valor do Rebate Total == valorFinanciado * rebateTotal", abs(r_a[12] - (150000 * 0.06)) < 0.01)
                check("E15: Valor da Coparticipação == valorRebateTotal * parteBrabus", abs(r_a[13] - (150000 * 0.06 * 0.5)) < 0.01)
                check("E16: Situação == real status (no PAGA/FATURADA gate applied)", r_a[14] == "EM ANDAMENTO")
                check("E17: Chassi == EXACT masked operation_reference, never a full VIN", r_a[18] == "***AB1234")

            r_f = by_vendor.get("Real Seller F")
            check("E18: Real Seller F row present (unmatched model)", r_f is not None)
            if r_f:
                check("E19: Modelo tabela taxa falls back to 'Modelo não encontrado na tabela de taxa'", r_f[4] == "Modelo não encontrado na tabela de taxa")
                check("E20: Rebate columns fall back to the SAME text (not 0/blank)", r_f[10] == "Modelo não encontrado na tabela de taxa")

            # Type inspection.
            for row in grid_e[1:]:
                label = row[0]["v"] if row[0] else None
                check("E21: Nome do cliente cell is a string, row=" + str(label), row[0] and row[0]["t"] == "s")
                check("E22: Valor de venda cell is numeric, row=" + str(label), row[6]["t"] == "n")
                check("E23: Valor financiado cell is numeric, row=" + str(label), row[9]["t"] == "n")

            leaked = False
            for row in grid_e:
                for cell in row:
                    if cell and isinstance(cell["v"], str) and any(bad in cell["v"] for bad in ["<", ">", "▲", "▼", "Anterior:"]):
                        leaked = True
            check("E24: no HTML/comparison-arrow artifacts leaked into any cell", not leaked)
        page_e.close()

        # ---- Group F: larger dataset completes without freezing ----
        many_sales, many_fins = [], []
        for i in range(300):
            seller = "VENDEDOR %04d" % i
            many_sales.append({"date": "2026-08-01", "seller": seller, "store": "Loja %02d" % (i % 8),
                                "department": "NOVOS", "model": "TRITON GLS", "sale_value": 180000, "operation_reference": "***%04d" % i})
            many_fins.append({"date": "2026-08-01", "seller": seller, "store": "Loja %02d" % (i % 8),
                               "department": "NOVOS", "model": "TRITON GLS", "sale_value": 180000, "financed_value": 150000,
                               "return_value": 9000, "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 3200,
                               "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***%04d" % i})
        large_payload = dict(EMPTY_REAL_PAYLOAD, sales=many_sales, finance=many_fins,
                              rates=[{"model": "TRITON GLS", "total_rebate": 6, "brabus_percent": 50}])
        page_f = mount_real(browser, real_json_route(200, large_payload))
        page_f.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        t0 = time.time()
        click_export(page_f)
        elapsed = time.time() - t0
        cap_f = page_f.evaluate("window.__CAPTURED")
        check("F1: large dataset (300 coparticipados) export completes quickly (<5s), no arbitrary row cap",
              cap_f is not None and elapsed < 5.0)
        if cap_f:
            check("F2: large dataset export row count == 300, no cap", len(cap_f["sheets"]["Coparticipados"]) - 1 == 300)
        page_f.close()

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
