#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Integration Foundation, Coparticipado Phase 2 -- deterministic
tests for Coparticipado's real-data transport boundary
(coparticipado-real-provider.js), the real view-model mapping
(coparticipado-real-view-model.js) and coparticipado.js's own transport
selection / runtime-state / sequencing / abort logic.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (same convention as every other Portal V2 test).
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_coparticipado-real-provider-harness.html"
RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_score_coparticipated_data"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(configured, token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-anon-key',
  textEndpoint: null
};
window.NX_AUTH = {
  isAuthConfigured: %s,
  getAccessToken: function () { return Promise.resolve(%s); }
};
""" % (
        "true" if configured else "false",
        ("'" + token + "'") if token else "null",
    )


_FIXTURES_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures", "coparticipado-fixtures.json")
with open(_FIXTURES_PATH, encoding="utf-8") as _f:
    _FIXTURES_BODY = _f.read()


def new_page(browser, configured, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token))
    # Harness lives at tests/_coparticipado-real-provider-harness.html
    # (not portal-next-v2/index.html) -- routed by filename glob so
    # fixture-mode assertions exercise the real fixtures content
    # regardless of harness placement (same technique as Dashbi's own
    # provider test).
    page.route("**/coparticipado-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=_FIXTURES_BODY))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_COPARTICIPADO_PAGE", timeout=5000)
    page.evaluate("window.NX_COPARTICIPADO_PAGE.render(document.getElementById('cpOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


EMPTY_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}

# Real contract shape (Phase 1/1B): one record per financing operation,
# already classified server-side via plan_codigo_if/tc_devolvida/
# balloon_value. The COPARTICIPADO record below deliberately carries a
# status the OLD, superseded fixture-era rule (isSituacaoCoparticipadoValida:
# status in PAGA/FATURADA) would have REJECTED -- proving real transport
# never applies that gate (Gate 15's critical regression case).
SAMPLE_PAYLOAD = dict(EMPTY_PAYLOAD, sales=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "operation_reference": "***AB1234"}
], finance=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "financed_value": 150000, "return_value": 9000,
     "spf_value": 3000, "spf_count": 1, "installments": 48, "installment_value": 3200,
     "balloon_value": 0, "plan": "COPARTICIPADO",
     "status": "EM ANDAMENTO",  # NOT PAGA/FATURADA -- old rule would reject this as COPARTICIPADO
     "operation_reference": "***AB1234"},
    # FC-2.4 (Human product decision): this module is now NOVOS-only
    # (coparticipado.js's own applyFilters() excludes Seminovos
    # unconditionally) -- department changed from the original SEMINOVOS
    # to NOVOS so check 14 (Subsidiados privacy/masking) still has a
    # visible record. This record's own purpose (client placeholder +
    # masked reference) was never about department scope; FC-2.4's own
    # coparticipado-fc24-test.py separately, exhaustively proves Seminovos
    # exclusion for both Coparticipados and Subsidiados.
    {"date": "2026-08-02", "seller": "Real Seller B", "store": "SANTO AMARO", "department": "NOVOS",
     "model": "OUTLANDER HPE-S", "sale_value": 220000, "financed_value": 200000, "return_value": 12000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 5800,
     "balloon_value": 0, "plan": "SUBSIDIADO", "status": "PAGA", "operation_reference": "***CD5678"},
    {"date": "2026-08-03", "seller": "Real Seller C", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "ECLIPSE CROSS HPE", "sale_value": 190000, "financed_value": 170000, "return_value": 8000,
     "spf_value": 0, "spf_count": 0, "installments": 40, "installment_value": 4200,
     "balloon_value": 0, "plan": "REVERSÃO", "status": "FATURADA", "operation_reference": "***EF9012"},
    {"date": "2026-08-04", "seller": "Real Seller D", "store": "ALPHAVILLE", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 175000, "financed_value": 160000, "return_value": 7500,
     "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 3100,
     "balloon_value": 45000, "plan": "BALÃO", "status": "PAGA", "operation_reference": "***GH3456"},
    {"date": "2026-08-05", "seller": "Real Seller E", "store": "ANALIA FRANCO", "department": "SEMINOVOS",
     "model": "COROLLA XEI", "sale_value": 130000, "financed_value": 120000, "return_value": 6000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 3600,
     "balloon_value": 0, "plan": "LINEAR", "status": "PAGA", "operation_reference": "***IJ7890"},
    {"date": "2026-08-06", "seller": "Real Seller F", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "MODELO SEM TAXA XYZ", "sale_value": 160000, "financed_value": 150000, "return_value": 7000,
     "spf_value": 0, "spf_count": 0, "installments": 40, "installment_value": 3000,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***KL1122"}
], rates=[
    {"model": "TRITON GLS", "term": 48, "rate": 1.99, "total_rebate": 6, "brabus_percent": 50}
])


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1-2: fixture transport when not configured, 0 RPC calls ----------
        page = new_page(browser, configured=False)
        rpc_calls = []
        page.route(RPC_URL + "*", lambda route: (rpc_calls.append(route.request), route.abort()))
        mount(page)
        page.wait_for_timeout(300)
        check("1: fixture transport selected when not configured (0 RPC calls)", len(rpc_calls) == 0)
        check("2: fixture transport still renders data deterministically", "modTabGroup" in page.inner_html("#cpPanel"))
        check("2b: fixture banner present in fixture mode", "DADOS DE TESTE" in page.inner_html("#cpOutlet"))
        page.close()

        # ---------- 3-8: real transport, exact argument mapping + auth headers ----------
        page = new_page(browser, configured=True, token="mock-access-token-abc")
        captured = {}

        def capture(route):
            captured["url"] = route.request.url
            captured["headers"] = route.request.headers
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(SAMPLE_PAYLOAD))

        page.route(RPC_URL + "*", capture)
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        check("3: real transport calls the exact RPC endpoint", captured.get("url", "").startswith(RPC_URL))
        check("4: Authorization header carries the session's own token, nothing constructed", captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        check("5: apikey header present (existing publishable key, not a secret)", captured.get("headers", {}).get("apikey") == "mock-anon-key")
        check("6: only p_start/p_end sent -- no store/dept/group-view override (Gate 7)", set(captured.get("body", {}).keys()) == {"p_start", "p_end"})
        check("7: p_start defaults to 2026-01-01 in real mode (RPC requires non-null p_start)", captured.get("body", {}).get("p_start") == "2026-01-01")
        check("7b: no fixture banner in real mode", "DADOS DE TESTE" not in page.inner_html("#cpOutlet"))
        check("8: real mode renders both tab buttons", "cpTabCopart" in page.inner_html("#cpPanel") and "cpTabSubs" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 9-14: privacy contract, plan authority, masked reference ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        panel_html = page.inner_html("#cpPanel")
        check("9: real Coparticipados view shows client placeholder, never a real name", "Operação protegida" in panel_html and "Real Seller A" in panel_html and "Real Seller B" not in panel_html)
        check("10: masked operation_reference shown verbatim, never a full chassis", "***AB1234" in panel_html)
        check("11: COPARTICIPADO record with non-PAGA/FATURADA status still classified COPARTICIPADO (old-rule divergence regression, Gate 15)",
              page.evaluate("() => { const rows = [...document.querySelectorAll('.cpTableCopart tbody tr')]; return rows.some(r => r.textContent.includes('***AB1234')); }"))
        check("12: modelo_sem_taxa COPARTICIPADO record shows 'Modelo não encontrado', not a fabricated rate", "Modelo não encontrado" in panel_html or "Não encontrado" in panel_html)
        # Ticket Gate 16 -- rebate formula: valorRebateTotal = 150000*0.06=9000; coparticipacao = 9000*0.50=4500.
        check("13: rebate formula exact (financed_value * total_rebate * brabus_percent)",
              page.evaluate("() => { const r = window.NX_COPARTICIPADO_ADAPTER.calcCoparticipacaoDetalhe({modelo:'TRITON GLS', valorFinanciado:150000}); return r.ok && Math.abs(r.valorRebateTotal - 9000) < 0.01 && Math.abs(r.coparticipacao - 4500) < 0.01; }"))
        page.eval_on_selector("#cpTabSubs", "el => el.click()")
        page.wait_for_timeout(150)
        subs_html = page.inner_html("#cpPanel")
        check("14: Subsidiados view shows the real SUBSIDIADO record with client placeholder", "Operação protegida" in subs_html and "***CD5678" in subs_html)
        page.close()

        # ---------- 15: empty real payload renders normally, not an error ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, EMPTY_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        html = page.inner_html("#cpPanel")
        check("15: empty real payload -> normal empty-state row, no modErrorState", "modErrorState" not in html and "Nenhum coparticipado encontrado" in html)
        page.close()

        # ---------- 16-18: error code normalization ----------
        error_cases = [
            ("42501", "PERMISSION_DENIED case"),
            ("22023", "INVALID_FILTER case"),
            ("57014", "BACKEND_ERROR/timeout case"),
        ]
        for code, label in error_cases:
            page = new_page(browser, configured=True)
            page.route(RPC_URL + "*", json_route(400, {"code": code, "message": "backend detail not for users"}))
            mount(page)
            page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
            html = page.inner_html("#cpPanel")
            check("16." + code + ": " + label + " -> modErrorState shown", "modErrorState" in html)
            check("16." + code + ": no raw backend error text leaked", "backend detail not for users" not in html)
            page.close()

        # ---------- 19: network error -> BACKEND_ERROR ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("19: network failure -> modErrorState (BACKEND_ERROR)", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 20: missing token -> SESSION_EXPIRED, never calls the RPC ----------
        page = new_page(browser, configured=True, token=None)
        rpc_hit = []
        page.route(RPC_URL + "*", lambda route: (rpc_hit.append(1), route.abort()))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("20: missing token -> modErrorState without ever calling the RPC", "modErrorState" in page.inner_html("#cpPanel") and len(rpc_hit) == 0)
        page.close()

        # ---------- 21: privacy-contract violation -> rejected, not rendered ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, dict(EMPTY_PAYLOAD, contains_client_identity=True)))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("21: contains_client_identity=true -> rejected as BACKEND_ERROR, never rendered", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 22: malformed response (missing arrays) -> rejected ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, {"scope": {}}))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("22: malformed response (missing sales/finance/rates) -> modErrorState", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 23: stale response ignored, latest wins ----------
        page = new_page(browser, configured=True)
        state = {"n": 0}

        def sequenced(route):
            state["n"] += 1
            n = state["n"]
            marker = "***STALE01" if n == 1 else "***FRESH02"
            # plan must be COPARTICIPADO -- the default active view
            # (Visão Coparticipados) only renders that plan type; a
            # LINEAR record would never appear regardless of staleness,
            # which would make this test vacuously pass/fail for the
            # wrong reason.
            body = dict(EMPTY_PAYLOAD, finance=[{
                "date": "2026-08-01", "seller": "X", "store": "BARRA FUNDA", "department": "NOVOS",
                "model": "TRITON GLS", "sale_value": 1000, "financed_value": 1000, "return_value": 0,
                "spf_value": 0, "spf_count": 0, "installments": 0, "installment_value": 0,
                "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": marker
            }])
            delay = 400 if n == 1 else 50
            import time as _t
            _t.sleep(delay / 1000.0)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(body))

        page.route(RPC_URL + "*", sequenced)
        mount(page)  # request #1 (stale)
        page.wait_for_timeout(60)
        page.eval_on_selector("#cpDateEnd", "el => { el.value = '2026-09-02'; el.dispatchEvent(new Event('change')); }")  # request #2 (fresh)
        page.wait_for_timeout(600)
        final_html = page.inner_html("#cpPanel")
        check("23: latest request wins over a slower stale one (FRESH marker present, STALE absent)", "***FRESH02" in final_html and "***STALE01" not in final_html)
        page.close()

        # ---------- 24: abort behavior -- rapid date changes abort the in-flight request cleanly ----------
        page = new_page(browser, configured=True)
        abort_seen = {"count": 0}

        def slow_then_track(route):
            import time as _t
            _t.sleep(0.3)
            try:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(EMPTY_PAYLOAD))
            except Exception:
                abort_seen["count"] += 1

        page.route(RPC_URL + "*", slow_then_track)
        mount(page)
        page.wait_for_timeout(50)
        page.eval_on_selector("#cpDateEnd", "el => { el.value = '2026-09-01'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(50)
        page.eval_on_selector("#cpDateEnd", "el => { el.value = '2026-09-02'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(700)
        check("24: rapid successive date changes settle without a stuck loading state", "modLoadingState" not in page.inner_html("#cpPanel"))
        check("24b: no user-facing error from an aborted superseded request", "modErrorState" not in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 25: filter subtractiveness -- store filter narrows, never expands ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        page.eval_on_selector("#cpTabSubs", "el => el.click()")
        page.wait_for_timeout(100)
        all_stores = page.eval_on_selector_all("#cpStoreFilter option", "els => els.map(e => e.value)")
        page.eval_on_selector("#cpStoreFilter", "el => { el.value = 'BARRA FUNDA'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(100)
        filtered_html = page.inner_html("#cpPanel")
        check("25: store dropdown only offers stores present in the authorized real dataset", set(all_stores) - {""} <= {"BARRA FUNDA", "SANTO AMARO", "ALPHAVILLE", "ANALIA FRANCO"})
        check("25b: store filter is strictly subtractive (SANTO AMARO record excluded after filtering to BARRA FUNDA)", "***CD5678" not in filtered_html)
        page.close()

        # ---------- 26: no raw scope/diagnostic dump ever appears in the panel ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        check("26: no raw scope JSON ever rendered in the panel (Coparticipado never introduces a diagnostic block)", "is_master" not in page.inner_html("#cpPanel") and "REAL_BACKEND" not in page.inner_html("#cpPanel"))
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Coparticipado Real Provider Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
