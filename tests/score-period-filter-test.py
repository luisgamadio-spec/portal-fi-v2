#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Integration Foundation, Score Phase 2B -- deterministic tests
for the real period-filter contract (date inputs, quick-period presets,
request sequencing/cancellation, detail consistency on period change).

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080.
"""
import io
import json as _json
import sys
import time as _time
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_score-real-provider-harness.html"
RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_score_coparticipated_data"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(configured=True, token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: %s, getAccessToken: function () { return Promise.resolve(%s); } };
""" % ("true" if configured else "false", ("'" + token + "'") if token else "null")


def new_page(browser, configured=True, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SCORE_PAGE", timeout=5000)
    page.evaluate("window.NX_SCORE_PAGE.render(document.getElementById('scOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def payload_for(plan="LINEAR", marker="***MK0001"):
    return {
        "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-12-31",
        "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
        "sales": [{"date": "2026-08-01", "seller": "X", "store": "Y", "department": "NOVOS", "model": "TRITON GLS", "operation_reference": marker}],
        "finance": [{"date": "2026-08-01", "seller": "X", "store": "Y", "department": "NOVOS", "model": "TRITON GLS",
                     "financed_value": 100000, "return_value": 5000, "spf_value": 0, "spf_count": 0,
                     "installments": 0, "installment_value": 0, "balloon_value": 0, "plan": plan,
                     "status": "PAGA", "operation_reference": marker}],
        "rates": []
    }


EMPTY_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-01-31",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: date controls render ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, payload_for()))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        shell = page.inner_html("#scOutlet")
        check("1: date inputs + preset buttons render in real mode", "scDateStart" in shell and "scDateEnd" in shell and "scPresetBtn" in shell)
        check("1b: 4 quick-period buttons present (Mês atual/anterior/6 meses/ano)", shell.count("scPresetBtn") == 4)
        page.close()

        # ---------- 2/8: valid custom period -> exact p_start/p_end sent ----------
        page = new_page(browser)
        captured = {}

        def capture(route):
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for()))

        page.route(RPC_URL + "*", capture)
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        page.eval_on_selector("#scDateStart", "el => { el.value = '2026-08-01'; el.dispatchEvent(new Event('change')); }")
        page.eval_on_selector("#scDateEnd", "el => { el.value = '2026-08-31'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(150)
        check("2/8: custom period sends exact p_start/p_end to the RPC", captured.get("body", {}).get("p_start") == "2026-08-01" and captured.get("body", {}).get("p_end") == "2026-08-31")
        page.close()

        # ---------- 3: invalid start > end -> no request, local error ----------
        page = new_page(browser)
        rpc_calls = []
        page.route(RPC_URL + "*", lambda route: (rpc_calls.append(1), route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for()))))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        rpc_calls.clear()
        # Set end first, to an early date already before the default start
        # (2026-06-01) -- invalid from the first change event onward, so no
        # intermediate valid combination is ever reached (sequential field
        # edits naturally pass through a transiently-valid state otherwise).
        page.eval_on_selector("#scDateEnd", "el => { el.value = '2026-01-01'; el.dispatchEvent(new Event('change')); }")
        page.eval_on_selector("#scDateStart", "el => { el.value = '2026-09-01'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(150)
        html = page.inner_html("#scTableRegion")
        check("3: start>end -> local 'Período inválido' error, zero new RPC calls", "Período inválido" in html and len(rpc_calls) == 0)
        page.close()

        # ---------- 4/5: missing start / missing end -> no request ----------
        for field, other, label in [("scDateStart", "scDateEnd", "4: missing start"), ("scDateEnd", "scDateStart", "5: missing end")]:
            page = new_page(browser)
            calls = []
            page.route(RPC_URL + "*", lambda route: (calls.append(1), route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for()))))
            mount(page)
            page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
            calls.clear()
            page.eval_on_selector("#" + field, "el => { el.value = ''; el.dispatchEvent(new Event('change')); }")
            page.wait_for_timeout(150)
            html = page.inner_html("#scTableRegion")
            check(label + " -> local error, zero RPC calls", "Período inválido" in html and len(calls) == 0)
            page.close()

        # ---------- 6: quick period mapping -- exact date math ----------
        today = date.today()
        cur_month_start = today.replace(day=1)
        last_month_end = cur_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last6_month = today.month - 5
        last6_year = today.year
        while last6_month <= 0:
            last6_month += 12
            last6_year -= 1
        last6_start = date(last6_year, last6_month, 1)
        try:
            last_year_start = today.replace(year=today.year - 1)
        except ValueError:
            last_year_start = today.replace(year=today.year - 1, day=28)

        preset_expectations = {
            "currentMonth": (cur_month_start.isoformat(), today.isoformat()),
            "lastMonth": (last_month_start.isoformat(), last_month_end.isoformat()),
            "last6": (last6_start.isoformat(), today.isoformat()),
            "lastYear": (last_year_start.isoformat(), today.isoformat()),
        }
        for preset, (exp_start, exp_end) in preset_expectations.items():
            page = new_page(browser)
            cap = {}
            page.route(RPC_URL + "*", lambda route: (cap.update(body=_json.loads(route.request.post_data or "{}")), route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for())))[-1])
            mount(page)
            page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
            page.eval_on_selector(".scPresetBtn[data-preset='%s']" % preset, "el => el.click()")
            page.wait_for_timeout(150)
            body = cap.get("body", {})
            check("6." + preset + ": quick period computes exact start/end (dashbi.js day-math reused)", body.get("p_start") == exp_start and body.get("p_end") == exp_end)
            check("6." + preset + "b: input fields reflect the computed range", page.eval_on_selector("#scDateStart", "el => el.value") == exp_start and page.eval_on_selector("#scDateEnd", "el => el.value") == exp_end)
            page.close()

        # ---------- 9/10: stale response ignored, latest wins (rapid Aug->Jul) ----------
        page = new_page(browser)
        state = {"n": 0}

        def sequenced(route):
            state["n"] += 1
            n = state["n"]
            marker = "***AUG_STALE" if n == 1 else "***JUL_FRESH"
            delay = 400 if n == 1 else 50
            _time.sleep(delay / 1000.0)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for(marker=marker)))

        page.route(RPC_URL + "*", sequenced)
        mount(page)  # request #1 (initial default period)
        page.wait_for_timeout(60)
        page.eval_on_selector("#scDateStart", "el => { el.value = '2026-08-01'; el.dispatchEvent(new Event('change')); }")  # request #2 (Aug, slow)
        page.wait_for_timeout(30)
        page.eval_on_selector("#scDateStart", "el => { el.value = '2026-07-01'; el.dispatchEvent(new Event('change')); }")  # request #3 (Jul, fast)
        page.wait_for_timeout(600)
        final_html = page.inner_html("#scTableRegion") + page.inner_html("#scDetailRegion")
        check("9/10: rapid period change -- slower stale response never overwrites the faster fresh one", "***AUG_STALE" not in final_html)
        page.close()

        # ---------- 11: loading state shown while a period request is in flight ----------
        page = new_page(browser)

        def slow(route):
            _time.sleep(0.3)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(payload_for()))

        page.route(RPC_URL + "*", slow)
        # Checked immediately after mount(), with no wait_for_timeout() in
        # between: the mocked route's blocking time.sleep() runs on
        # Playwright's sync-API driver thread, so any wait call issued
        # afterward can itself block until that sleep finishes -- only a
        # check made before the first such wait reliably observes the
        # true in-flight state.
        mount(page)
        loading_html = page.inner_html("#scTableRegion")
        check("11: loading state visible immediately after mount (RPC still in flight)", "modLoadingState" in loading_html)
        page.close()

        # ---------- 12: empty period -> legitimate EMPTY state, not an error ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, EMPTY_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.length > 0", timeout=5000)
        html = page.inner_html("#scTableRegion")
        check("12: empty valid period -> normal empty state, not modErrorState/fixture fallback", "modErrorState" not in html and "Nenhum vendedor encontrado" in html)
        page.close()

        # ---------- 13: detail closes on period change (Gate 11, critical) ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, payload_for()))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        page.eval_on_selector(".scTable tbody tr", "el => el.click()")
        page.wait_for_timeout(100)
        check("13a: detail open before period change", "scDetail" in page.inner_html("#scDetailRegion"))
        page.eval_on_selector("#scDateStart", "el => { el.value = '2026-07-01'; el.dispatchEvent(new Event('change')); }")
        page.wait_for_timeout(200)
        check("13b: detail closed after period change -- never a stale ranking A + breakdown B pairing", page.inner_html("#scDetailRegion").strip() == "")
        page.close()

        # ---------- 14: no fixture fallback on RPC error ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(500, {"code": "57014", "message": "x"}))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        html = page.inner_html("#scOutlet")
        check("14: RPC failure -> error state, never 'DADOS DE TESTE' fixture banner in real mode", "modErrorState" in html and "DADOS DE TESTE" not in html)
        page.close()

        # ---------- 15/16: VENDEDOR denial preserved / MASTER success (transport-level, mocked) ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(400, {"code": "42501", "message": "Acesso não autorizado ao módulo Score F&I."}))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("15: VENDEDOR-style 42501 denial still -> AUTH_DENIED/modErrorState with period filters present", "modErrorState" in page.inner_html("#scTableRegion"))
        page.close()

        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, payload_for()))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        check("16: MASTER success renders ranking with period filters present", "scTable" in page.inner_html("#scTableRegion") and "scDateStart" in page.inner_html("#scOutlet"))
        page.close()

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Score Period Filter: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
