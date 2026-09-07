#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-2.4 (Gestão de Coparticipados & Subsidiados -- Human-requested product
completion): period-preset shortcuts (Mês atual/Mês anterior/Últimos 6
meses), removal of the Departamento selector in favor of a fixed
NOVOS-only business filter, and the "Exportar Subsidiados" workbook
(V1_SUBSIDIADOS_EXPORT_EXISTS_AND_WIRED -- modules/coparticipado.html's
own exportarSubsidiados(), a real production button alongside
exportarCoparticipados()'s own).

Presets are tested deterministically by overriding the page's global
`Date` via an init script (a fixed "now"), NOT the machine's real wall
clock -- covers January year-rollover, a leap-year February, a 31-day
month-end, and a timezone far ahead of UTC (proving coparticipado.js's
own localIso() avoids the .toISOString() calendar-date-shift defect
already known and NOT fixed in dashbi.js/score.js, per this Wave's own
explicit "do not fix Score's defect" boundary).

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080 (fixture
mode) and 8700 is NOT used here -- port 8080 only, matching every other
Portal V2 real-mode-capable test.
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

SUBS_HEADERS = ["Nome do cliente", "Vendedor", "Loja vinculada", "Departamento", "Modelo do carro",
                 "Família do carro", "Valor de venda", "Valor financiado", "Retorno", "SPF Extra",
                 "Situação", "Prazo", "Parcela", "Data da venda", "Chassi"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


def fixed_date_script(y, m, d, hh=10, mm=0):
    # month is 1-indexed here (human-friendly); JS Date month is 0-indexed.
    return """
        (function() {
            var FIXED = new Date(%d, %d, %d, %d, %d, 0);
            var OrigDate = Date;
            function FakeDate() {
                if (arguments.length === 0) return new OrigDate(FIXED.getTime());
                return new (Function.prototype.bind.apply(OrigDate, [null].concat(Array.prototype.slice.call(arguments))))();
            }
            FakeDate.prototype = OrigDate.prototype;
            FakeDate.now = function() { return FIXED.getTime(); };
            window.Date = FakeDate;
        })();
    """ % (y, m - 1, d, hh, mm)


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


def with_golden(*extra):
    return json.dumps({"cases": GOLDEN["cases"] + list(extra)})


EMPTY_REAL_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-05",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}

# Synthetic real-shaped payload with BOTH Novos and Seminovos rows, both
# COPARTICIPADO and SUBSIDIADO plans -- proves Novos-only exclusion for
# both exports/tables (Gate 38, mandatory).
NOVOS_SEMINOVOS_PAYLOAD = dict(EMPTY_REAL_PAYLOAD, sales=[], finance=[
    {"date": "2026-08-01", "seller": "Seller Novos Copart", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "financed_value": 150000, "return_value": 9000,
     "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 3200,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***N-COP1"},
    {"date": "2026-08-01", "seller": "Seller Semi Copart", "store": "SANTO AMARO", "department": "SEMINOVOS",
     "model": "TRITON GLS", "sale_value": 170000, "financed_value": 140000, "return_value": 8000,
     "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 3000,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***S-COP1"},
    {"date": "2026-08-02", "seller": "Seller Novos Subs", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "OUTLANDER", "sale_value": 200000, "financed_value": 180000, "return_value": 10000,
     "spf_value": 1000, "spf_count": 1, "installments": 36, "installment_value": 5500,
     "balloon_value": 0, "plan": "SUBSIDIADO", "status": "PAGA", "operation_reference": "***N-SUB1"},
    {"date": "2026-08-02", "seller": "Seller Semi Subs", "store": "SANTO AMARO", "department": "SEMINOVOS",
     "model": "OUTLANDER", "sale_value": 190000, "financed_value": 170000, "return_value": 9500,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 5200,
     "balloon_value": 0, "plan": "SUBSIDIADO", "status": "PAGA", "operation_reference": "***S-SUB1"},
], rates=[
    {"model": "TRITON GLS", "total_rebate": 6, "brabus_percent": 50},
])

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


def mount_fixture(browser, fixtures_body, date_script=None, timezone_id=None):
    ctx_kwargs = {"viewport": {"width": 1366, "height": 900}}
    if timezone_id:
        ctx_kwargs["timezone_id"] = timezone_id
    page = browser.new_page(**ctx_kwargs)
    page.add_init_script(auth_mock_script(False))
    if date_script:
        page.add_init_script(date_script)
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


def run(playwright):
    browser = playwright.chromium.launch()
    try:
        # ---- Group P: deterministic preset semantics (Gate 35) ----
        cases = [
            # (label, fixed today, expected currentMonth, expected lastMonth, expected last6-start)
            ("January year-rollover", (2026, 1, 15),
             ("2026-01-01", "2026-01-15"), ("2025-12-01", "2025-12-31"), "2025-08-01"),
            ("leap-year February (2028)", (2028, 3, 15),
             ("2028-03-01", "2028-03-15"), ("2028-02-01", "2028-02-29"), "2027-10-01"),
            ("31-day month-end (May)", (2026, 5, 31),
             ("2026-05-01", "2026-05-31"), ("2026-04-01", "2026-04-30"), "2025-12-01"),
            ("December (year-end)", (2026, 12, 10),
             ("2026-12-01", "2026-12-10"), ("2026-11-01", "2026-11-30"), "2026-07-01"),
        ]
        for label, (y, m, d), exp_current, exp_last, exp_last6_start in cases:
            page = mount_fixture(browser, with_golden(), date_script=fixed_date_script(y, m, d))
            got_current = page.evaluate("window.NX_COPARTICIPADO_PAGE.computePreset('currentMonth')")
            got_last = page.evaluate("window.NX_COPARTICIPADO_PAGE.computePreset('lastMonth')")
            got_last6 = page.evaluate("window.NX_COPARTICIPADO_PAGE.computePreset('last6')")
            check("P (%s): Mês atual == %s" % (label, exp_current), (got_current["start"], got_current["end"]) == exp_current)
            check("P (%s): Mês anterior == %s" % (label, exp_last), (got_last["start"], got_last["end"]) == exp_last)
            check("P (%s): Últimos 6 meses start == %s, end == today" % (label, exp_last6_start),
                  got_last6["start"] == exp_last6_start and got_last6["end"] == exp_current[1])
            page.close()

        # ---- Group Q: timezone-boundary safety (Gate 22, 35) -- a host
        # timezone far AHEAD of UTC would make .toISOString() shift the
        # calendar date backward by one day; localIso() must not. ----
        page = mount_fixture(browser, with_golden(), date_script=fixed_date_script(2026, 6, 1, hh=0, mm=30), timezone_id="Pacific/Kiritimati")
        got = page.evaluate("window.NX_COPARTICIPADO_PAGE.computePreset('currentMonth')")
        check("Q: currentMonth start stays 2026-06-01 even at UTC+14, 00:30 local (no .toISOString() day-shift)", got["start"] == "2026-06-01")
        page.close()

        # ---- Group R: preset click updates inputs + active state; manual
        # edit clears it (Gates 23-25) ----
        page = mount_fixture(browser, with_golden(), date_script=fixed_date_script(2026, 6, 15))
        page.click(".cpPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(100)
        check("R1: clicking a preset updates #cpDateStart", page.eval_on_selector("#cpDateStart", "e => e.value") == "2026-06-01")
        check("R2: clicking a preset updates #cpDateEnd", page.eval_on_selector("#cpDateEnd", "e => e.value") == "2026-06-15")
        check("R3: clicked preset shows active state", page.eval_on_selector(".cpPresetBtn[data-preset='currentMonth']", "e => e.classList.contains('modSegItemActive')"))
        page.fill("#cpDateStart", "2026-01-01")
        page.eval_on_selector("#cpDateStart", "e => e.dispatchEvent(new Event('change'))")
        page.wait_for_timeout(100)
        check("R4: manual date edit clears the active preset state", not page.eval_on_selector(".cpPresetBtn[data-preset='currentMonth']", "e => e.classList.contains('modSegItemActive')"))
        page.close()

        # ---- Group S: Departamento absent (fixture + real) ----
        page = mount_fixture(browser, with_golden())
        check("S1: no Departamento selector in fixture mode", not page.evaluate("!!document.getElementById('cpDeptFilter')"))
        check("S1b: no 'Departamento' filter label text in fixture mode", "for=\"cpDeptFilter\"" not in page.inner_html("#cpOutlet"))
        page.close()

        page = mount_real(browser, real_json_route(200, EMPTY_REAL_PAYLOAD))
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        check("S2: no Departamento selector in real mode", not page.evaluate("!!document.getElementById('cpDeptFilter')"))
        page.close()

        # ---- Group T: Novos-only enforcement (Gate 38, mandatory) ----
        page = mount_real(browser, real_json_route(200, NOVOS_SEMINOVOS_PAYLOAD))
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        copart_html = page.inner_html("#cpPanel")
        check("T1: Coparticipados table includes the Novos seller", "Seller Novos Copart" in copart_html)
        check("T2: Coparticipados table EXCLUDES the Seminovos seller", "Seller Semi Copart" not in copart_html)
        page.click("#cpExportCopaBtn")
        page.wait_for_timeout(100)
        cap_t = page.evaluate("window.__CAPTURED")
        if cap_t:
            rows_t = [[c["v"] if c else None for c in row] for row in cap_t["sheets"]["Coparticipados"][1:]]
            check("T3: Coparticipados EXPORT contains only the Novos row (1 row, not 2)", len(rows_t) == 1)

        page.click("#cpTabSubs")
        page.wait_for_timeout(100)
        subs_html = page.inner_html("#cpPanel")
        check("T4: Subsidiados table includes the Novos seller", "Seller Novos Subs" in subs_html)
        check("T5: Subsidiados table EXCLUDES the Seminovos seller", "Seller Semi Subs" not in subs_html)
        # exportCoparticipadosXlsx()/exportSubsidiadosXlsx() share ONE
        # 800ms double-click debounce (lastCpExportAt) -- wait it out so
        # this second, DIFFERENT export isn't silently swallowed.
        page.wait_for_timeout(850)
        page.click("#cpExportSubsBtn")
        page.wait_for_timeout(100)
        cap_t2 = page.evaluate("window.__CAPTURED")
        if cap_t2:
            rows_t2 = [[c["v"] if c else None for c in row] for row in cap_t2["sheets"]["Subsidiados"][1:]]
            check("T6: Subsidiados EXPORT contains only the Novos row (1 row, not 2)", len(rows_t2) == 1)
            check("T7: exported row's Departamento column reads 'Novos'", rows_t2[0][3] == "Novos")
        page.close()

        # ---- Group U: Subsidiados export presence/absence (Gate 39) ----
        page = mount_fixture(browser, with_golden())
        page.select_option("#cpFixtureSelect", "ALL")
        page.wait_for_timeout(100)
        check("U1: Subsidiados export ABSENT while Visão Coparticipados active", not page.evaluate("!!document.getElementById('cpExportSubsBtn')"))
        page.click("#cpTabSubs")
        page.wait_for_timeout(100)
        check("U2: Subsidiados export PRESENT in Visão Subsidiados", page.evaluate("!!document.getElementById('cpExportSubsBtn')"))
        check("U3: Coparticipados export ABSENT while Visão Subsidiados active", not page.evaluate("!!document.getElementById('cpExportCopaBtn')"))
        page.close()

        # ---- Group V: Subsidiados workbook contract (Gate 40) ----
        page = mount_real(browser, real_json_route(200, NOVOS_SEMINOVOS_PAYLOAD))
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        page.click("#cpTabSubs")
        page.wait_for_timeout(100)
        page.click("#cpExportSubsBtn")
        page.wait_for_timeout(100)
        cap_v = page.evaluate("window.__CAPTURED")
        check("V1: writeFile called exactly once", page.evaluate("window.__WRITEFILE_CALLS") == 1)
        check("V2: capture non-null", cap_v is not None)
        if cap_v:
            check("V3: sheet name is 'Subsidiados'", cap_v["sheetNames"] == ["Subsidiados"])
            check("V4: filename matches Subsidiados_Score_FI_ pattern (V1 precedent)", cap_v["filename"].startswith("Subsidiados_Score_FI_") and cap_v["filename"].endswith(".xlsx"))
            grid_v = cap_v["sheets"]["Subsidiados"]
            header_v = [c["v"] if c else None for c in grid_v[0]]
            check("V5: header row matches the 15-column V1 contract exactly", header_v == SUBS_HEADERS)
            data_v = [[c["v"] if c else None for c in row] for row in grid_v[1:]]
            check("V6: exactly 1 row (Novos-only)", len(data_v) == 1)
            if data_v:
                row = data_v[0]
                check("V7: Nome do cliente == 'Operação protegida' (privacy preserved)", row[0] == "Operação protegida")
                check("V8: Vendedor == real seller identity", row[1] == "Seller Novos Subs")
                check("V9: Loja vinculada", row[2] == "BARRA FUNDA")
                check("V10: Departamento == 'Novos'", row[3] == "Novos")
                check("V11: Modelo do carro", row[4] == "OUTLANDER")
                check("V12: Família do carro present", row[5] == "Outlander")
                check("V13: Valor de venda numeric and correct", abs(row[6] - 200000) < 0.01)
                check("V14: Valor financiado numeric and correct", abs(row[7] - 180000) < 0.01)
                check("V15: Retorno numeric and correct", abs(row[8] - 10000) < 0.01)
                check("V16: SPF Extra numeric and correct", abs(row[9] - 1000) < 0.01)
                check("V17: Situação", row[10] == "PAGA")
                check("V18: Prazo == installments count", row[11] == 36)
                check("V19: Parcela == installment value", abs(row[12] - 5500) < 0.01)
                check("V20: Data da venda present", bool(row[13]))
                check("V21: Chassi == exact masked operation_reference", row[14] == "***N-SUB1")
            # type inspection
            for row in grid_v[1:]:
                check("V22: Nome do cliente cell is a string", row[0]["t"] == "s")
                check("V23: Valor de venda cell is numeric", row[6]["t"] == "n")
                check("V24: Prazo cell is numeric", row[11]["t"] == "n")
            leaked = any(
                cell and isinstance(cell["v"], str) and any(bad in cell["v"] for bad in ["<", ">", "▲", "▼", "Anterior:"])
                for row in grid_v for cell in row
            )
            check("V25: no HTML/comparison-arrow artifacts leaked", not leaked)
        page.close()

        # ---- Group W: empty Subsidiados -> controlled message ----
        page = mount_real(browser, real_json_route(200, EMPTY_REAL_PAYLOAD))
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('cpTableCopart')", timeout=5000)
        page.click("#cpTabSubs")
        page.wait_for_timeout(100)
        page.click("#cpExportSubsBtn")
        page.wait_for_timeout(100)
        check("W1: empty dataset shows a controlled message", "subsidiado" in page.inner_text("#cpExportStatus").lower())
        check("W2: empty dataset does NOT call XLSX.writeFile", page.evaluate("window.__WRITEFILE_CALLS") == 0)
        page.close()

        # ---- Group X: real transport failure -> no export available for
        # either view, no fixture fallback ----
        page = mount_real(browser, real_json_route(500, {"code": "57014", "message": "x"}))
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("X1: no Coparticipados export button after a real failure", not page.evaluate("!!document.getElementById('cpExportCopaBtn')"))
        page.click("#cpTabSubs") if page.evaluate("!!document.getElementById('cpTabSubs')") else None
        check("X2: no Subsidiados export button after a real failure", not page.evaluate("!!document.getElementById('cpExportSubsBtn')"))
        check("X3: no fixture banner leaked into a real-mode failure", "DADOS DE TESTE" not in page.inner_html("#cpOutlet"))
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
