#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-2 (GAP-003) -- XLSX export parity test for Score's "Exportar
Coparticipados" button (restores V1's exportarCoparticipados(), modules/
score.html -- confirmed orphaned/unreachable in V1 production, but its
own field/scope contract is what's being restored here).

Contract under test (V1 exportarCoparticipados(), read at
portal-financiamento-brabus-secure@4d8ce1d):
  headers = ['Nome do cliente','Vendedor','Loja vinculada','Modelo do carro',
    'Modelo tabela taxa','Família do carro','Valor de venda',
    'Valor de entrada','Percentual de entrada','Valor financiado',
    'Rebate Total','Rebate Parte Brabus','Valor do Rebate Total',
    'Valor da Coparticipação','Situação','Prazo','Parcela',
    'Data da venda','Chassi']
  Source: currentFiltered().fins.filter(r=>r.plano==='COPARTICIPADO').
  Rebate/coparticipação columns via calcCoparticipacaoDetalhe(r) (frozen,
  reused from the Coparticipado module, not a second classifier). "Prazo"
  reads r.parcelas (installment COUNT); "Parcela" reads r.pmt (installment
  VALUE) -- an odd V1 naming preserved deliberately, not "fixed".

THIS WAVE'S CENTRAL FINDING (documented, not fixed here): V2's real-mode
Score data (score-real-view-model.js's buildFins()) deliberately omits
modelo/cliente/chassi/data/parcelas/pmt/situacaoB3/valorVenda -- a
pre-existing Gate-13 privacy-minimization decision. Every field this
export needs beyond vendedor/loja/valorFinanciado/plano is therefore
UNAVAILABLE in real mode. Real-mode export is gated off (disabled button +
explicit reason) rather than shipped in a silently-broken form -- this
test proves that gating, not a working real-mode export.

Fixture-mode testing uses a NEW synthetic, non-golden fixture (injected
via route-mock, exactly like dashbi-fc13-readability-test.py's own
technique) that carries the full field set PLUS its own `taxasCopart`
table (mirroring the Coparticipado module's own compute(fixture) ->
"DATA.taxasCopart = fixture.taxasCopart || {}" convention) -- the frozen
tests/fixtures/score-fixtures.json is never modified.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080 (same
convention as score-real-contract-test.py).
"""
import io
import json
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "score-fixtures.json")
BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_score-real-provider-harness.html"

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
    GOLDEN_CASES = json.load(f)["cases"]

# ---- Synthetic fixture: full field set (modelo/cliente/chassi/data/
# parcelas/pmt/situacaoB3/valorVenda) the golden set deliberately lacks,
# plus its OWN taxasCopart table (score.js reads caseData.taxasCopart,
# mirroring coparticipado.adapter.js's own established convention) --
# needed to independently prove the full 19-column contract mechanically,
# not something a human would encounter by picking a golden fixture.
SELLER_ACCENTED = "JOÃO D'ÁVILA-PÉREZ"
SYNTHETIC_CASE = {
    "id": "fc2_gap003_export",
    "description": "FC-2 GAP-003 export parity fixture.",
    "sales": [
        {"vendedor": SELLER_ACCENTED, "loja": "Loja Nações", "dept": "Novos", "familia": "Outlander"},
        {"vendedor": "MARIA SOUZA", "loja": "Loja Nações", "dept": "Novos", "familia": "Triton"},
    ],
    "fins": [
        {
            "vendedor": SELLER_ACCENTED, "loja": "Loja Nações", "dept": "Novos",
            "cliente": "CLIENTE UM", "modelo": "OUTLANDER", "familia": "Outlander",
            "valorVenda": 200000, "valorFinanciado": 180000, "retorno": 9000,
            "receitaSPF": 0, "spfQtd": 0, "plano": "COPARTICIPADO",
            "situacaoB3": "PAGA", "parcelas": 48, "pmt": 3750,
            "data": "2026-04-10", "chassi": "CHS-A1",
        },
        {
            # No matching taxa entry for TRITON -- exercises V1's own
            # "Modelo não encontrado na tabela de taxa" fallback (Gate: not
            # a defect, the SAME behavior V1 already has).
            "vendedor": "MARIA SOUZA", "loja": "Loja Nações", "dept": "Novos",
            "cliente": "CLIENTE DOIS", "modelo": "TRITON", "familia": "Triton",
            "valorVenda": 150000, "valorFinanciado": 140000, "retorno": 7000,
            "receitaSPF": 0, "spfQtd": 0, "plano": "COPARTICIPADO",
            "situacaoB3": "PAGA", "parcelas": 36, "pmt": 4200,
            "data": "2026-05-02", "chassi": "CHS-B2",
        },
        {
            # A non-COPARTICIPADO row -- must be excluded from the export.
            "vendedor": SELLER_ACCENTED, "loja": "Loja Nações", "dept": "Novos",
            "cliente": "CLIENTE TRES", "modelo": "OUTLANDER", "familia": "Outlander",
            "valorVenda": 190000, "valorFinanciado": 170000, "retorno": 8000,
            "receitaSPF": 0, "spfQtd": 0, "plano": "LINEAR",
            "situacaoB3": "PAGA", "parcelas": 48, "pmt": 3500,
            "data": "2026-04-15", "chassi": "CHS-C3",
        },
    ],
    "focusSeller": None,
    "taxasCopart": {
        # Keyed by NX_COPARTICIPADO_ADAPTER.taxaKey('OUTLANDER') -- plain
        # "OUTLANDER" normalizes to itself (no accents/known noise words).
        "OUTLANDER": {"modeloTabela": "OUTLANDER TAB", "rebateTotal": 0.03, "parteBrabus": 0.5},
    },
}

EMPTY_CASE = {
    "id": "fc2_gap003_export_empty", "description": "empty",
    "sales": [], "fins": [], "focusSeller": None, "taxasCopart": {},
}


def with_golden(*extra):
    return json.dumps({"cases": GOLDEN_CASES + list(extra)})


RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_score_coparticipated_data"

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


def mount(browser, configured, fixtures_body):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured))
    page.route("**/score-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=fixtures_body))
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SCORE_PAGE", timeout=5000)
    page.evaluate("window.NX_SCORE_PAGE.render(document.getElementById('scOutlet'))")
    # Install the capture hook (same technique as dashbi-gap004-export-test.py).
    page.evaluate(CAPTURE_HOOK_JS)
    return page


def mount_real(browser, route_handler):
    # FC-2.2: real-mode mount, mirroring score-real-contract-test.py's own
    # new_page()/mount() pair -- NX_AUTH.isAuthConfigured=true, RPC routed
    # to `route_handler` instead of the fixtures.json route.
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(True))
    page.route(RPC_URL + "*", route_handler)
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SCORE_PAGE", timeout=5000)
    page.evaluate("window.NX_SCORE_PAGE.render(document.getElementById('scOutlet'))")
    page.evaluate(CAPTURE_HOOK_JS)
    return page


def real_json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))
    return handler


EMPTY_REAL_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-06-01", "period_end": "2026-09-05",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}

# Real-shaped payload (same field names score-real-contract-test.py's own
# SAMPLE_PAYLOAD uses) -- 1 COPARTICIPADO row with a matching rate, 1
# LINEAR row that must be excluded from the export.
REAL_SAMPLE_PAYLOAD = dict(EMPTY_REAL_PAYLOAD, sales=[
    {"date": "2026-08-01", "seller": "REAL SELLER A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "OUTLANDER", "sale_value": 200000, "operation_reference": "***AB1234"},
], finance=[
    {"date": "2026-08-01", "seller": "REAL SELLER A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "OUTLANDER", "sale_value": 200000, "financed_value": 180000, "return_value": 9000,
     "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 3750,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***AB1234"},
    {"date": "2026-08-02", "seller": "REAL SELLER B", "store": "SANTO AMARO", "department": "NOVOS",
     "model": "TRITON", "sale_value": 150000, "financed_value": 140000, "return_value": 7000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 4200,
     "balloon_value": 0, "plan": "LINEAR", "status": "PAGA", "operation_reference": "***CD5678"},
], rates=[
    {"model": "OUTLANDER", "total_rebate": 3, "brabus_percent": 50},  # percent-form -> normalized to 0.03/0.5
])


def select_fixture(page, fixture_id):
    # score.js's #scFixtureSelect <option> list is built from a HARDCODED
    # FIXTURE_IDS constant (unlike dashbi.js's own selector, which is
    # populated dynamically from the loaded fixturesData) -- confirmed by
    # direct source read. A synthetic test-only fixture id therefore has no
    # matching <option> to select by default; this injects one (DOM-only,
    # score.js itself is untouched) so Playwright's select_option can pick
    # it, exactly as if score.js's own list included it.
    page.eval_on_selector(
        "#scFixtureSelect",
        "(el, id) => { if (!el.querySelector('option[value=\"' + id + '\"]')) { var o = document.createElement('option'); o.value = id; o.textContent = id; el.appendChild(o); } }",
        fixture_id,
    )
    page.select_option("#scFixtureSelect", fixture_id)
    page.wait_for_timeout(50)


def run(playwright):
    browser = playwright.chromium.launch()
    try:
        # ---- Test group 1: fixture mode happy path ----
        page = mount(browser, False, with_golden(SYNTHETIC_CASE))
        select_fixture(page, "fc2_gap003_export")

        btn_disabled = page.eval_on_selector("#scExportCopaBtn", "el => el.disabled")
        check("export button is ENABLED in fixture mode", btn_disabled is False)

        page.click("#scExportCopaBtn")
        page.wait_for_timeout(50)
        cap = page.evaluate("window.__CAPTURED")

        check("writeFile called exactly once", page.evaluate("window.__WRITEFILE_CALLS") == 1)
        check("capture non-null", cap is not None)
        if cap:
            check("sheet name is 'Coparticipados'", cap["sheetNames"] == ["Coparticipados"])
            check(".xlsx extension", cap["filename"].endswith(".xlsx"))
            check("filename has no illegal filesystem chars", not any(ch in cap["filename"] for ch in '<>:"/\\|?*'))
            check("filename matches V1's own prefix (Coparticipados_Score_FI_)", cap["filename"].startswith("Coparticipados_Score_FI_"))

            grid = cap["sheets"]["Coparticipados"]
            header_row = [c["v"] if c else None for c in grid[0]]
            check("header row matches V1 contract exactly (order+labels)", header_row == EXPECTED_HEADERS)

            data_rows = [[c["v"] if c else None for c in row] for row in grid[1:]]
            check("only COPARTICIPADO rows exported (2 of 3 fins rows; the LINEAR row excluded)", len(data_rows) == 2)

            by_cliente = {r[0]: r for r in data_rows}

            # Row 1 (OUTLANDER, taxa found)
            r1 = by_cliente.get("CLIENTE UM")
            check("row 1 present (CLIENTE UM)", r1 is not None)
            if r1:
                check("Nome do cliente", r1[0] == "CLIENTE UM")
                check("Vendedor (accented/apostrophe/hyphen survives, Gate 33)", r1[1] == SELLER_ACCENTED)
                check("Loja vinculada", r1[2] == "Loja Nações")
                check("Modelo do carro", r1[3] == "OUTLANDER")
                check("Modelo tabela taxa (found)", r1[4] == "OUTLANDER TAB")
                check("Família do carro", r1[5] == "Outlander")
                check("Valor de venda", abs(r1[6] - 200000) < 0.01)
                check("Valor de entrada = valorVenda - valorFinanciado", abs(r1[7] - 20000) < 0.01)
                check("Percentual de entrada = entrada/valorVenda", abs(r1[8] - (20000 / 200000)) < 0.0001)
                check("Valor financiado", abs(r1[9] - 180000) < 0.01)
                check("Rebate Total (numeric, from taxa table)", abs(r1[10] - 0.03) < 0.0001)
                check("Rebate Parte Brabus (numeric, from taxa table)", abs(r1[11] - 0.5) < 0.0001)
                check("Valor do Rebate Total = valorFinanciado * rebateTotal", abs(r1[12] - (180000 * 0.03)) < 0.01)
                check("Valor da Coparticipação = valorRebateTotal * parteBrabus", abs(r1[13] - (180000 * 0.03 * 0.5)) < 0.01)
                check("Situação", r1[14] == "PAGA")
                check("Prazo reads r.parcelas (installment COUNT, V1's own field mapping)", r1[15] == 48)
                check("Parcela reads r.pmt (installment VALUE, V1's own field mapping)", abs(r1[16] - 3750) < 0.01)
                check("Data da venda present (non-empty)", bool(r1[17]))
                check("Chassi", r1[18] == "CHS-A1")

            # Row 2 (TRITON, taxa NOT found -- V1's own existing fallback)
            r2 = by_cliente.get("CLIENTE DOIS")
            check("row 2 present (CLIENTE DOIS, unmatched model)", r2 is not None)
            if r2:
                check("Modelo tabela taxa falls back to V1's own 'not found' text", r2[4] == "Modelo não encontrado na tabela de taxa")
                check("Rebate Total falls back to the SAME text (not 0, not blank) -- V1's own mixed-type behavior preserved", r2[10] == "Modelo não encontrado na tabela de taxa")
                check("Valor da Coparticipação falls back to the SAME text", r2[13] == "Modelo não encontrado na tabela de taxa")

            # Type inspection (Gate 32).
            for row in grid[1:]:
                label = row[0]["v"] if row[0] else None
                check("Nome do cliente cell is a string, row=" + str(label), row[0] and row[0]["t"] == "s")
                # Valor de venda / Valor financiado are always numeric floats
                # regardless of the taxa-lookup outcome (only the rebate/
                # coparticipação columns can carry the fallback string).
                check("Valor de venda cell is numeric, row=" + str(label), row[6]["t"] == "n")
                check("Valor financiado cell is numeric, row=" + str(label), row[9]["t"] == "n")

            # No HTML/comparison-arrow leakage anywhere.
            leaked = False
            for row in grid:
                for cell in row:
                    if cell and isinstance(cell["v"], str) and any(bad in cell["v"] for bad in ["<", ">", "▲", "▼", "Anterior:"]):
                        leaked = True
            check("no HTML/comparison-arrow artifacts leaked into any cell", not leaked)

        # ---- Test group 2: empty (no COPARTICIPADO rows) -> controlled message ----
        page2 = mount(browser, False, with_golden(EMPTY_CASE))
        select_fixture(page2, "fc2_gap003_export_empty")
        page2.click("#scExportCopaBtn")
        page2.wait_for_timeout(50)
        status_text = page2.inner_text("#scExportStatus")
        check("empty dataset shows a controlled message", "coparticipado" in status_text.lower())
        check("empty dataset does NOT call XLSX.writeFile", page2.evaluate("window.__WRITEFILE_CALLS") == 0)

        # ---- Test group 3A: real mode, request in flight -> button
        # disabled (Gate 24: no export while loading). Route intentionally
        # never resolves (no fulfill/abort) -- Playwright's sync API runs
        # route handlers and page.wait_for_timeout() on the same dispatcher,
        # so a Python-side time.sleep() inside the handler itself blocks
        # that SAME wait, making a "resolve after N ms" delay unreliable to
        # observe mid-flight from this single-threaded test driver. Leaving
        # the request permanently pending is simpler and just as valid for
        # proving the loading window alone -- test group 3B separately
        # proves the button re-enables after a real success.
        page3a = mount_real(browser, lambda route: None)
        page3a.wait_for_timeout(150)  # render() already kicked off loadReal() synchronously by now
        btn3a_disabled = page3a.eval_on_selector("#scExportCopaBtn", "el => el.disabled")
        check("32: export button is DISABLED while a real request is in flight", btn3a_disabled is True)
        status3a = page3a.inner_text("#scExportStatus")
        check("32b: loading state shows an explanatory status, not silence", len(status3a.strip()) > 0)
        page3a.close()

        # ---- Test group 3B: real mode, successful load with a
        # COPARTICIPADO row -> button enabled, full 19-column real export ----
        page3b = mount_real(browser, real_json_route(200, REAL_SAMPLE_PAYLOAD))
        page3b.wait_for_function("!document.getElementById('scExportCopaBtn').disabled", timeout=5000)
        btn3b_disabled = page3b.eval_on_selector("#scExportCopaBtn", "el => el.disabled")
        check("33: export button is ENABLED after a successful real load", btn3b_disabled is False)

        page3b.click("#scExportCopaBtn")
        page3b.wait_for_timeout(100)
        cap3b = page3b.evaluate("window.__CAPTURED")
        check("34: writeFile called exactly once (real mode)", page3b.evaluate("window.__WRITEFILE_CALLS") == 1)
        check("35: capture non-null (real mode)", cap3b is not None)
        if cap3b:
            grid3b = cap3b["sheets"]["Coparticipados"]
            header3b = [c["v"] if c else None for c in grid3b[0]]
            check("36: real-mode header row matches the same 19-column V1 contract", header3b == EXPECTED_HEADERS)
            data3b = [[c["v"] if c else None for c in row] for row in grid3b[1:]]
            check("37: only the COPARTICIPADO row exported (1 of 2 finance rows; LINEAR excluded)", len(data3b) == 1)
            if data3b:
                row = data3b[0]
                check("38: Nome do cliente == 'Operação protegida' (never a real name, real mode)", row[0] == "Operação protegida")
                check("39: Vendedor == real seller identity (staff, not customer PII)", row[1] == "REAL SELLER A")
                check("40: Loja vinculada", row[2] == "BARRA FUNDA")
                check("41: Modelo do carro == raw RPC model, no re-normalization", row[3] == "OUTLANDER")
                check("42: Modelo tabela taxa resolved via real payload.rates[] (rate lookup works end-to-end)", row[4] == "OUTLANDER")
                check("43: Família do carro present (familia now retained on real fins)", row[5] == "Outlander")
                check("44: Valor de venda numeric and correct", abs(row[6] - 200000) < 0.01)
                check("45: Valor financiado numeric and correct", abs(row[9] - 180000) < 0.01)
                check("46: Rebate Total == normalized real rate (3% -> 0.03)", abs(row[10] - 0.03) < 0.0001)
                check("47: Rebate Parte Brabus == normalized real rate (50% -> 0.5)", abs(row[11] - 0.5) < 0.0001)
                check("48: Valor do Rebate Total == valorFinanciado * rebateTotal", abs(row[12] - (180000 * 0.03)) < 0.01)
                check("49: Valor da Coparticipação == valorRebateTotal * parteBrabus", abs(row[13] - (180000 * 0.03 * 0.5)) < 0.01)
                check("50: Situação == real status", row[14] == "PAGA")
                check("51: Prazo == real installments count", row[15] == 48)
                check("52: Parcela == real installment value", abs(row[16] - 3750) < 0.01)
                check("53: Data da venda present (real date parsed)", bool(row[17]))
                check("54: Chassi == EXACT masked operation_reference, never a full VIN", row[18] == "***AB1234")
        page3b.close()

        # ---- Test group 3C: real mode, successful load but ZERO
        # COPARTICIPADO rows -> button stays ENABLED (Gate 25/38), click
        # shows the same controlled empty message as fixture mode. ----
        real_no_copart = dict(EMPTY_REAL_PAYLOAD, sales=REAL_SAMPLE_PAYLOAD["sales"], finance=[REAL_SAMPLE_PAYLOAD["finance"][1]])  # only the LINEAR row
        page3c = mount_real(browser, real_json_route(200, real_no_copart))
        page3c.wait_for_function("!document.getElementById('scExportCopaBtn').disabled", timeout=5000)
        check("55: button ENABLED even with zero COPARTICIPADO rows (eligibility != row count)",
              page3c.eval_on_selector("#scExportCopaBtn", "el => el.disabled") is False)
        page3c.click("#scExportCopaBtn")
        page3c.wait_for_timeout(100)
        check("56: zero-COPARTICIPADO real click shows the controlled empty message",
              "coparticipado" in page3c.inner_text("#scExportStatus").lower())
        check("57: zero-COPARTICIPADO real click does NOT call XLSX.writeFile", page3c.evaluate("window.__WRITEFILE_CALLS") == 0)
        page3c.close()

        # ---- Test group 3D: real mode, transport failure -> button
        # disabled, no stale/misleading export available (Gate 24/37). ----
        page3d = mount_real(browser, real_json_route(500, {"code": "57014", "message": "backend detail not for users"}))
        page3d.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("58: export button DISABLED after a transport failure", page3d.eval_on_selector("#scExportCopaBtn", "el => el.disabled") is True)
        check("58b: failure status does not leak raw backend error text", "backend detail not for users" not in page3d.inner_text("#scExportStatus"))
        page3d.close()

        # ---- Test group 3E: real mode, contract failure (unexpected
        # department -> MALFORMED_RESPONSE thrown by the view-model) ----
        bad_contract = dict(EMPTY_REAL_PAYLOAD, sales=[
            {"date": "2026-08-01", "seller": "X", "store": "Y", "department": "OFICINA", "model": "OUTLANDER", "operation_reference": "***ZZ0000"}
        ])
        page3e = mount_real(browser, real_json_route(200, bad_contract))
        page3e.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("59: export button DISABLED after a contract failure (MALFORMED_RESPONSE)", page3e.eval_on_selector("#scExportCopaBtn", "el => el.disabled") is True)
        page3e.close()

        # ---- Test group 4: larger dataset completes without freezing ----
        many_fins = []
        many_sales = []
        for i in range(300):
            nome = "VENDEDOR %04d" % i
            many_sales.append({"vendedor": nome, "loja": "Loja %02d" % (i % 8), "dept": "Novos", "familia": "Outlander"})
            many_fins.append({
                "vendedor": nome, "loja": "Loja %02d" % (i % 8), "dept": "Novos",
                "cliente": "CLIENTE %04d" % i, "modelo": "OUTLANDER", "familia": "Outlander",
                "valorVenda": 200000 + i, "valorFinanciado": 180000 + i, "retorno": 9000,
                "receitaSPF": 0, "spfQtd": 0, "plano": "COPARTICIPADO",
                "situacaoB3": "PAGA", "parcelas": 48, "pmt": 3750,
                "data": "2026-04-10", "chassi": "CHS-%04d" % i,
            })
        large_case = {
            "id": "fc2_gap003_export_large", "description": "perf",
            "sales": many_sales, "fins": many_fins, "focusSeller": None,
            "taxasCopart": {"OUTLANDER": {"modeloTabela": "OUTLANDER TAB", "rebateTotal": 0.03, "parteBrabus": 0.5}},
        }
        page4 = mount(browser, False, with_golden(large_case))
        select_fixture(page4, "fc2_gap003_export_large")
        t0 = time.time()
        page4.click("#scExportCopaBtn")
        page4.wait_for_timeout(50)
        elapsed = time.time() - t0
        cap4 = page4.evaluate("window.__CAPTURED")
        check("large dataset (300 coparticipados) export completes quickly (<5s), no arbitrary row cap",
              cap4 is not None and elapsed < 5.0)
        if cap4:
            check("large dataset export row count == 300, no cap", len(cap4["sheets"]["Coparticipados"]) - 1 == 300)

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
