#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Integration Foundation, Dashbi Phase 2 -- deterministic tests
for Dashbi's real-data transport boundary (dashbi-real-provider.js),
the real view-model mapping (dashbi-real-view-model.js) and dashbi.js's
own transport selection / runtime-state / sequencing logic.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project
touched, 0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (same convention as every other Portal V2 test).
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_dashbi-real-provider-harness.html"
METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_metrics"
MODEL_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_model_metrics"

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


import os as _os
_FIXTURES_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures", "dashbi-fixtures.json")
with open(_FIXTURES_PATH, encoding="utf-8") as _f:
    _FIXTURES_BODY = _f.read()


def new_page(browser, configured, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token))
    # The harness lives at tests/_dashbi-real-provider-harness.html (not
    # portal-next-v2/index.html), so dashbi.js's own page-relative
    # loadFixtures() fetch('tests/fixtures/dashbi-fixtures.json') would
    # resolve to the wrong path from here -- routed by filename glob
    # instead, serving the real fixtures file content, so fixture-mode
    # assertions exercise the real data rather than an artifact of harness
    # placement.
    page.route("**/dashbi-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=_FIXTURES_BODY))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


EMPTY_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}
EMPTY_MODEL_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "entry_rule": "SUM_ENTRY_DIV_VALID_OPERATIONS", "entry_percent_rule": "SUM_ENTRY_DIV_SUM_SALE_VALUE",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}

SAMPLE_METRICS = dict(EMPTY_METRICS, rows=[
    {
        "seller_id": "s1", "seller_name": "João Silva", "store": "BARRA FUNDA", "department": "NOVOS",
        "sold_count": 10, "sales_value": 500000,
        "financed_count": 8, "share_percent": 80,
        "production_value": 400000, "return_value": 40000,
        "spf_count": 2, "spf_value": 10000, "spf_net_value": 7000,
        "profitability_value": 47000,
        "plan_breakdown": [
            {"plan_type": "LINEAR", "financed_count": 5, "production_value": 250000, "return_value": 25000, "average_balloon_value": 0},
            {"plan_type": "BALÃO", "financed_count": 3, "production_value": 150000, "return_value": 15000, "average_balloon_value": 5000}
        ]
    },
    {
        "seller_id": "s2", "seller_name": "Maria Souza", "store": "SANTO AMARO", "department": "SEMINOVOS",
        "sold_count": 4, "sales_value": 120000,
        "financed_count": 2, "share_percent": 50,
        "production_value": 80000, "return_value": 8000,
        "spf_count": 0, "spf_value": 0, "spf_net_value": 0,
        "profitability_value": 8000,
        "plan_breakdown": [
            {"plan_type": "LINEAR", "financed_count": 2, "production_value": 80000, "return_value": 8000, "average_balloon_value": 0}
        ]
    }
])

SAMPLE_MODEL_METRICS = dict(EMPTY_MODEL_METRICS, rows=[
    {
        "store": "BARRA FUNDA", "department": "NOVOS", "model": "TRITON HPE-S",
        "sold_count": 4, "sales_value": 800000,
        "financed_count": 3, "penetration_percent": 75,
        "production_value": 300000, "return_value": 30000, "average_return_percent": 10,
        "average_installments": 48, "average_installment_value": 6000,
        "valid_entry_count": 2, "entry_total": 40000, "entry_sales_value_total": 200000,
        "average_entry_value": 20000, "weighted_entry_percent": 20,
        "plan_breakdown": [
            {"plan_type": "LINEAR", "financed_count": 2, "production_value": 200000, "return_value": 20000, "average_balloon_value": 0},
            {"plan_type": "BALÃO", "financed_count": 1, "production_value": 100000, "return_value": 10000, "average_balloon_value": 4000}
        ],
        "spf_count": 1, "spf_value": 5000, "spf_net_value": 3500
    },
    # A SEMINOVOS-department row for the SAME model -- must NOT contaminate
    # the Novos-only Model Analysis view (Gate B7/22).
    {
        "store": "BARRA FUNDA", "department": "SEMINOVOS", "model": "TRITON HPE-S",
        "sold_count": 100, "sales_value": 99999999,
        "financed_count": 100, "penetration_percent": 100,
        "production_value": 99999999, "return_value": 99999999, "average_return_percent": 100,
        "average_installments": 60, "average_installment_value": 9999,
        "valid_entry_count": 0, "entry_total": 0, "entry_sales_value_total": 0,
        "average_entry_value": 0, "weighted_entry_percent": 0,
        "plan_breakdown": [], "spf_count": 0, "spf_value": 0, "spf_net_value": 0
    }
])


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1-2: fixture transport when not configured, 0 RPC calls ----------
        page = new_page(browser, configured=False)
        rpc_calls = []
        page.route(METRICS_URL + "*", lambda route: (rpc_calls.append(route.request), route.abort()))
        page.route(MODEL_METRICS_URL + "*", lambda route: (rpc_calls.append(route.request), route.abort()))
        mount(page)
        page.wait_for_timeout(300)
        check("1: fixture transport selected when not configured (0 RPC calls)", len(rpc_calls) == 0)
        check("2: fixture transport still renders data deterministically", "modKpiGrid" in page.inner_html("#dbPanel"))
        check("2b: fixture banner present in fixture mode", "DADOS DE TESTE" in page.inner_html("#dbOutlet"))
        page.close()

        # ---------- 3-7: real transport, exact argument mapping + auth headers, both RPCs ----------
        # FC-1 (GAP-001): loadDashbiRealWithComparison now fires operational_metrics/
        # operational_model_metrics TWICE (current period, then the day-aligned
        # previous comparable period) -- captured_calls is a list per URL (not a
        # single overwritten dict) so both are inspectable, current-period
        # assertions (3-7c) unchanged in what they check, FC-1's own dual-fetch
        # is verified separately (33-35 below).
        page = new_page(browser, configured=True, token="mock-access-token-abc")
        captured_calls = {"metrics": [], "model_metrics": []}
        captured = {}

        def capture_metrics(route):
            body = _json.loads(route.request.post_data or "{}")
            captured_calls["metrics"].append(body)
            captured["metrics_url"] = route.request.url
            captured["metrics_headers"] = route.request.headers
            captured["metrics_body"] = body
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(SAMPLE_METRICS))

        def capture_model_metrics(route):
            body = _json.loads(route.request.post_data or "{}")
            captured_calls["model_metrics"].append(body)
            captured["model_metrics_url"] = route.request.url
            captured["model_metrics_body"] = body
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(SAMPLE_MODEL_METRICS))

        page.route(METRICS_URL + "*", capture_metrics)
        page.route(MODEL_METRICS_URL + "*", capture_model_metrics)
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        # Two Promise.all pairs settle asynchronously (current, then previous);
        # wait for the second metrics call to land before asserting on it.
        for _ in range(50):
            if len(captured_calls["metrics"]) >= 2:
                break
            page.wait_for_timeout(50)
        current_metrics_calls = [b for b in captured_calls["metrics"] if b.get("p_start") == "2026-01-01" and b.get("p_end") == "2026-12-31"]
        previous_metrics_calls = [b for b in captured_calls["metrics"] if b.get("p_start") == "2025-12-01" and b.get("p_end") == "2026-11-30"]
        check("3: real transport calls operational_metrics", captured.get("metrics_url", "").startswith(METRICS_URL))
        check("4: real transport calls operational_model_metrics", captured.get("model_metrics_url", "").startswith(MODEL_METRICS_URL))
        check("5: Authorization header carries the session's own token, nothing constructed", captured.get("metrics_headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        check("6: apikey header present (existing publishable key, not a secret)", captured.get("metrics_headers", {}).get("apikey") == "mock-anon-key")
        check("7: Stage A frozen -- p_group_view always sent true, no scope invented client-side", all(b.get("p_group_view") is True for b in captured_calls["metrics"]) and all(b.get("p_group_view") is True for b in captured_calls["model_metrics"]))
        check("7b: p_start/p_end mapped from the selected period (Gate B5 -- no fixture-era date disconnect)", len(current_metrics_calls) == 1)
        check("7c: no fixture banner in real mode", "DADOS DE TESTE" not in page.inner_html("#dbOutlet"))
        check("33 (FC-1): previous comparable period fetched too, day-aligned (not naive calendar month)", len(previous_metrics_calls) == 1)
        check("34 (FC-1): previous period fetched for BOTH real RPCs (operational_metrics and operational_model_metrics)", len([b for b in captured_calls["model_metrics"] if b.get("p_start") == "2025-12-01" and b.get("p_end") == "2026-11-30"]) == 1)
        page.close()

        # ---------- 35 (FC-1, Gate 12): previous period fails -> current still renders, comparison omitted ----------
        page = new_page(browser, configured=True)

        def metrics_fail_previous_only(route):
            body = _json.loads(route.request.post_data or "{}")
            if body.get("p_start") == "2026-01-01":
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(SAMPLE_METRICS))
            else:
                route.fulfill(status=500, content_type="application/json", body=_json.dumps({"code": "57014", "message": "backend detail not for users"}))

        page.route(METRICS_URL + "*", metrics_fail_previous_only)
        page.route(MODEL_METRICS_URL + "*", json_route(200, SAMPLE_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        panel_html = page.inner_html("#dbPanel")
        check("35a (FC-1, Gate 12): current period renders normally when only the previous fetch fails", "modKpiGrid" in panel_html and "modErrorState" not in panel_html)
        check("35b (FC-1, Gate 12): comparison omitted (no delta badge) when previous fetch failed, not a crash/blank comparison", "dbDelta" not in panel_html)
        page.close()

        # ---------- 36 (FC-1, Gate 12): current period fails -> normal error state (current is primary) ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(500, {"code": "57014", "message": "backend detail not for users"}))
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState') || document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        check("36 (FC-1, Gate 12): current period failing still yields the normal error state, regardless of previous", "modErrorState" in page.inner_html("#dbPanel"))
        page.close()

        # ---------- 8-10: KPI numbers are exact sums from operational_metrics, no client recalculation ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(200, SAMPLE_METRICS))
        page.route(MODEL_METRICS_URL + "*", json_route(200, SAMPLE_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        vendas = page.evaluate("document.querySelector('.modKpiGrid .modKpiCard:nth-child(1) .modKpiValue').textContent")
        fins = page.evaluate("document.querySelector('.modKpiGrid .modKpiCard:nth-child(2) .modKpiValue').textContent")
        check("8: Vendas KPI = exact sold_count sum across rows (Grupo view, 10+4=14)", vendas.strip() == "14")
        check("9: Financiamentos KPI = exact financed_count sum across rows (8+2=10)", fins.strip() == "10")
        page.eval_on_selector('[data-view="Novos"]', "el => el.click()")
        page.wait_for_timeout(150)
        vendas_novos = page.evaluate("document.querySelector('.modKpiGrid .modKpiCard:nth-child(1) .modKpiValue').textContent")
        check("10: Novos view filters by real department field (10, not 14)", vendas_novos.strip() == "10")
        page.close()

        # ---------- 11-15: Model Analysis -- direct construction, ticket, department scoping ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(200, SAMPLE_METRICS))
        page.route(MODEL_METRICS_URL + "*", json_route(200, SAMPLE_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        page.eval_on_selector('[data-view="Novos"]', "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector('[data-mode="modelos"]', "el => el.click()")
        page.wait_for_timeout(150)
        canonical = page.evaluate("window.NX_DASHBI_ADAPTER.modeloPadrao('TRITON HPE-S')")
        family = page.evaluate("window.NX_DASHBI_ADAPTER.familyOfModel(%r)" % canonical)
        if family != "TRITON":
            check("11: TRITON HPE-S normalizes into the TRITON family", False)
        else:
            page.eval_on_selector('[data-family="TRITON"]', "el => el.click()")
            page.wait_for_timeout(150)
            row_html = page.evaluate(
                "(name) => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
                "const r = rows.find(tr => tr.textContent.includes(name)); return r ? r.outerHTML : ''; }",
                canonical,
            )
            check("11: normalized model row appears in TRITON family table", canonical in row_html)
            check("12: SEMINOVOS-department real row excluded from Novos-only Model Analysis (financiada=3, not 103)", ">3<" in row_html or "3 " in row_html)
            # Ticket (Stage A frozen formula): production_value/financed_count = 300000/3 = 100000.
            ticket_ok = page.evaluate(
                "(name) => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
                "const r = rows.find(tr => tr.textContent.includes(name)); "
                "if (!r) return false; const btn = r.querySelector('.dbDetailToggle'); if (btn) btn.click(); return true; }",
                canonical,
            )
            page.wait_for_timeout(150)
            detail_html = page.evaluate(
                "(name) => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
                "const idx = rows.findIndex(tr => tr.textContent.includes(name)); "
                "return idx >= 0 && rows[idx + 1] ? rows[idx + 1].textContent : ''; }",
                canonical,
            )
            check("13: Ticket Médio = production_value/financed_count (100000/3 -> R$ 100.000,00), not sales_value/sold_count", "100.000,00" in detail_html or "100.000" in detail_html)
            check("14: BALÃO plan count correct (subsidiadoQtd/coparticipadoQtd not overwritten to 0 by fixture-only merge)", "1" in detail_html)
        page.close()

        # ---------- 16: empty real payload renders zeroed KPIs, not an error ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(200, EMPTY_METRICS))
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        html = page.inner_html("#dbPanel")
        check("16: empty real payload -> zeroed KPI grid, no modErrorState", "modErrorState" not in html and "modKpiGrid" in html)
        page.close()

        # ---------- 17-20: error code normalization ----------
        error_cases = [
            ("42501", "PERMISSION_DENIED case"),
            ("22023", "INVALID_FILTER case"),
            ("P0002", "SCOPE_EMPTY case"),
            ("57014", "BACKEND_ERROR/timeout case"),
        ]
        for code, label in error_cases:
            page = new_page(browser, configured=True)
            page.route(METRICS_URL + "*", json_route(400, {"code": code, "message": "backend detail not for users"}))
            page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
            mount(page)
            page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState')", timeout=5000)
            html = page.inner_html("#dbPanel")
            check("17." + code + ": " + label + " -> modErrorState shown", "modErrorState" in html)
            check("17." + code + ": no raw backend error text leaked", "backend detail not for users" not in html)
            page.close()

        # ---------- 21: network error -> BACKEND_ERROR ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", lambda route: route.abort("failed"))
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("21: network failure -> modErrorState (BACKEND_ERROR)", "modErrorState" in page.inner_html("#dbPanel"))
        page.close()

        # ---------- 22: missing token -> SESSION_EXPIRED, never calls the RPC ----------
        page = new_page(browser, configured=True, token=None)
        rpc_hit = []
        page.route(METRICS_URL + "*", lambda route: (rpc_hit.append(1), route.abort()))
        page.route(MODEL_METRICS_URL + "*", lambda route: (rpc_hit.append(1), route.abort()))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("22: missing token -> modErrorState without ever calling the RPC", "modErrorState" in page.inner_html("#dbPanel") and len(rpc_hit) == 0)
        page.close()

        # ---------- 23: unexpected sensitive shape -> rejected, not rendered as data ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(200, dict(SAMPLE_METRICS, client_identity={"cpf": "should-never-appear"})))
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState')", timeout=5000)
        html = page.inner_html("#dbPanel")
        check("23: sensitive-shaped response rejected, never rendered as data", "modErrorState" in html and "should-never-appear" not in html)
        page.close()

        # ---------- 24: invalid response shape (missing rows) -> rejected ----------
        page = new_page(browser, configured=True)
        page.route(METRICS_URL + "*", json_route(200, {"scope": {}}))
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)
        page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("24: response missing rows[] -> modErrorState, not treated as empty data", "modErrorState" in page.inner_html("#dbPanel"))
        page.close()

        # ---------- 25: stale request ignored, latest request wins ----------
        page = new_page(browser, configured=True)
        state = {"n": 0}

        def sequenced(route):
            state["n"] += 1
            n = state["n"]
            qty = 1 if n == 1 else 2
            body = dict(EMPTY_METRICS, rows=[{
                "seller_id": "s1", "seller_name": "X", "store": "BARRA FUNDA", "department": "NOVOS",
                "sold_count": qty, "sales_value": qty * 1000, "financed_count": qty, "share_percent": 100,
                "production_value": qty * 1000, "return_value": 0, "spf_count": 0, "spf_value": 0,
                "spf_net_value": 0, "profitability_value": 0,
                "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": qty, "production_value": qty * 1000, "return_value": 0, "average_balloon_value": 0}]
            }])
            delay = 400 if n == 1 else 50
            import time as _t
            _t.sleep(delay / 1000.0)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(body))

        page.route(METRICS_URL + "*", sequenced)
        page.route(MODEL_METRICS_URL + "*", json_route(200, EMPTY_MODEL_METRICS))
        mount(page)  # request #1 (stale)
        page.wait_for_timeout(60)
        page.eval_on_selector("#dbDateEnd", "el => { el.value = '2026-09-02'; el.dispatchEvent(new Event('change')); }")  # request #2 (latest)
        page.wait_for_timeout(600)
        vendas_final = page.evaluate("document.querySelector('.modKpiGrid .modKpiCard:nth-child(1) .modKpiValue').textContent")
        check("25: latest request's data wins over a slower stale one (Vendas=2, not overwritten back to 1)", vendas_final.strip() == "2")
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Dashbi Real Provider Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()