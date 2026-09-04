#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Integration Foundation, Phase 2 -- deterministic tests for
Gestão's real-data transport boundary (gestao-real-provider.js) and
gestao.js's own transport selection / runtime-state / sequencing
logic. Everything here runs against a mocked window.NX_AUTH and a
routed (never real) fetch -- 0 real network calls, 0 real Supabase
project touched, 0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (same convention as every other Portal V2 test).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/fixtures/_gestao-real-provider-harness.html"
RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_fandi_dashboard"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(configured, token="mock-access-token-abc", is_master=True, loja=None):
    return """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-anon-key',
  textEndpoint: null
};
window.__SESSION_EXPIRED_CALLS__ = 0;
window.NX_AUTH = {
  isAuthConfigured: %s,
  getAccessToken: function () { return Promise.resolve(%s); }
};
window.NX_AUTH_CORE = {
  getContext: function () {
    return %s;
  },
  reportSessionExpired: function () { window.__SESSION_EXPIRED_CALLS__ += 1; }
};
""" % (
        "true" if configured else "false",
        ("'" + token + "'") if token else "null",
        "null" if is_master is None else ("{isMaster:" + ("true" if is_master else "false") + ",perfil:'" +
                                           ("MASTER" if is_master else "VENDEDOR") + "',loja:" +
                                           (("'" + loja + "'") if loja else "null") + "}"),
    )


def new_page(browser, configured, token="mock-access-token-abc", is_master=True, loja=None):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token, is_master, loja))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
    return page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))") or page.wait_for_timeout(50)


def route_rpc(page, handler):
    page.route(RPC_URL + "*", handler)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=__import__("json").dumps(body))
    return handler


def main():
    from playwright.sync_api import sync_playwright
    import json as _json

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1-2: fixture transport when not configured, 0 RPC calls ----------
        page = new_page(browser, configured=False)
        rpc_calls = []
        page.route(RPC_URL + "*", lambda route: (rpc_calls.append(route.request), route.abort()))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_timeout(300)
        check("1: fixture transport selected when not configured (0 RPC calls)", len(rpc_calls) == 0)
        check("2: fixture transport still renders data deterministically", "modKpiGrid" in page.inner_html("#gePanel"))
        page.close()

        # ---------- 3-6: real transport, exact argument mapping + auth headers ----------
        page = new_page(browser, configured=True, token="mock-access-token-abc")
        captured = {}
        def capture_and_succeed(route):
            captured["url"] = route.request.url
            captured["method"] = route.request.method
            captured["headers"] = route.request.headers
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({
                "scope": {"profile": "MASTER"}, "period": {"start": "2026-08-01", "end": "2026-09-03"},
                "filters": {"store": None, "department": None}, "source": {"latest_validated_batch": "b1"},
                "summary": {"operational_quantity": 5, "total_financed": 100000},
                "stores": [{"store": "BARRA FUNDA", "quantity": 5, "new_quantity": 5, "used_quantity": 0,
                             "new_average_financed": 20000, "used_average_financed": 0,
                             "new_average_installment": 1000, "used_average_installment": 0,
                             "balloon_quantity": 0, "average_balloon": 0, "total_financed": 100000}],
                "banks": [], "status_by_store": [], "status_by_bank": [], "plans": [],
                "plans_by_store_department": [], "spf_extra": [], "proposal_outcomes": []
            }))
        route_rpc(page, capture_and_succeed)
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_function("document.getElementById('gePanel').innerHTML.includes('modKpiGrid')", timeout=5000)
        check("3: real transport calls the exact RPC endpoint", captured.get("url", "").startswith(RPC_URL))
        check("4: Authorization header carries the session's own token, nothing constructed", captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        check("5: apikey header present (existing publishable key, not a secret)", captured.get("headers", {}).get("apikey") == "mock-anon-key")
        check("6: argument mapping exact (p_start/p_end/p_store/p_department, no scope invented client-side)",
              captured.get("body") == {"p_start": "2026-01-01", "p_end": "2026-06-30", "p_store": None, "p_department": None})
        check("7: real transport renders READY_WITH_DATA", "modKpiGrid" in page.inner_html("#gePanel"))
        page.close()

        # ---------- 8: empty response -> READY_EMPTY, not an error ----------
        page = new_page(browser, configured=True)
        route_rpc(page, json_route(200, {
            "scope": {}, "period": {}, "filters": {}, "source": {},
            "summary": {"operational_quantity": 0, "total_financed": 0},
            "stores": [], "banks": [], "status_by_store": [], "status_by_bank": [],
            "plans": [], "plans_by_store_department": [], "spf_extra": [], "proposal_outcomes": []
        }))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_function("document.getElementById('gePanel').innerHTML.includes('modEmptyState')", timeout=5000)
        check("8: empty RPC response -> modEmptyState (not modErrorState)", "modErrorState" not in page.inner_html("#gePanel"))
        page.close()

        # ---------- 9-12: error code normalization ----------
        error_cases = [
            ("42501", "PERMISSION_DENIED case"),
            ("22023", "INVALID_FILTER case"),
            ("P0002", "SCOPE_EMPTY case"),
            ("57014", "BACKEND_ERROR/timeout case"),
        ]
        for code, label in error_cases:
            page = new_page(browser, configured=True)
            route_rpc(page, json_route(400, {"code": code, "message": "backend detail not for users"}))
            page.goto(BASE)
            page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
            page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
            page.wait_for_function("document.getElementById('gePanel').innerHTML.includes('modErrorState')", timeout=5000)
            html = page.inner_html("#gePanel")
            check("9." + code + ": " + label + " -> modErrorState shown", "modErrorState" in html)
            check("9." + code + ": no raw backend error text leaked", "backend detail not for users" not in html)
            page.close()

        # ---------- 10: network error -> BACKEND_ERROR ----------
        page = new_page(browser, configured=True)
        route_rpc(page, lambda route: route.abort("failed"))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_function("document.getElementById('gePanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("10: network failure -> modErrorState (BACKEND_ERROR)", "modErrorState" in page.inner_html("#gePanel"))
        page.close()

        # ---------- 11: session expired (no token) delegates to Auth Foundation ----------
        page = new_page(browser, configured=True, token=None)
        route_rpc(page, lambda route: route.abort())
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_function("window.__SESSION_EXPIRED_CALLS__ === 1", timeout=5000)
        check("11: missing token -> delegates to NX_AUTH_CORE.reportSessionExpired exactly once", page.evaluate("window.__SESSION_EXPIRED_CALLS__") == 1)
        page.close()

        # ---------- 12: unexpected sensitive shape -> rejected, not rendered as data ----------
        page = new_page(browser, configured=True)
        route_rpc(page, json_route(200, {
            "scope": {}, "period": {}, "filters": {}, "source": {},
            "summary": {"operational_quantity": 1, "total_financed": 1}, "stores": [], "banks": [],
            "status_by_store": [], "status_by_bank": [], "plans": [], "plans_by_store_department": [],
            "spf_extra": [], "proposal_outcomes": [], "client_identity": {"cpf": "should-never-appear"}
        }))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_function("document.getElementById('gePanel').innerHTML.includes('modErrorState')", timeout=5000)
        html = page.inner_html("#gePanel")
        check("12: sensitive-shaped response rejected, never rendered as data", "modErrorState" in html and "should-never-appear" not in html)
        page.close()

        # ---------- 13: stale request ignored, latest request wins ----------
        page = new_page(browser, configured=True)
        state = {"n": 0}
        def sequenced(route):
            state["n"] += 1
            n = state["n"]
            qty = 1 if n == 1 else 2
            body = {
                "scope": {}, "period": {}, "filters": {}, "source": {},
                "summary": {"operational_quantity": qty, "total_financed": qty * 1000},
                "stores": [{"store": "BARRA FUNDA", "quantity": qty, "new_quantity": qty, "used_quantity": 0,
                             "new_average_financed": 1, "used_average_financed": 0, "new_average_installment": 1,
                             "used_average_installment": 0, "balloon_quantity": 0, "average_balloon": 0, "total_financed": qty * 1000}],
                "banks": [], "status_by_store": [], "status_by_bank": [], "plans": [],
                "plans_by_store_department": [], "spf_extra": [], "proposal_outcomes": []
            }
            # First (stale) request resolves SLOWER than the second -- must not win.
            delay = 400 if n == 1 else 50
            import time as _t
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(body)) if _t.sleep(delay / 1000.0) is None else None
        route_rpc(page, sequenced)
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")  # request #1 (stale)
        page.wait_for_timeout(60)
        page.eval_on_selector("#geDateEnd", "el => { el.value = '2026-09-02'; el.dispatchEvent(new Event('change')); }")  # request #2 (latest)
        page.wait_for_timeout(600)
        panel_html = page.inner_html("#gePanel")
        total_section = panel_html.split("Produção Total")[1][:200] if "Produção Total" in panel_html else ""
        check("13: latest request's data wins over a slower stale one (Produção Total=2, not overwritten back to 1)",
              '<div class="modKpiValue">2</div>' in total_section)
        page.close()

        # ---------- 14: Gate 14 -- VENDEDOR store selector constrained ----------
        page = new_page(browser, configured=True, is_master=False, loja="BARRA FUNDA")
        route_rpc(page, json_route(200, {
            "scope": {}, "period": {}, "filters": {}, "source": {},
            "summary": {"operational_quantity": 0, "total_financed": 0}, "stores": [], "banks": [],
            "status_by_store": [], "status_by_bank": [], "plans": [], "plans_by_store_department": [],
            "spf_extra": [], "proposal_outcomes": []
        }))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_timeout(300)
        select_disabled = page.eval_on_selector("#geStoreFilter", "el => el.disabled")
        select_options = page.eval_on_selector_all("#geStoreFilter option", "els => els.length")
        select_value = page.eval_on_selector("#geStoreFilter", "el => el.value")
        check("14: VENDEDOR (non-MASTER, real loja) -> store selector disabled and locked to own store", select_disabled and select_options == 1 and select_value == "BARRA FUNDA")
        page.close()

        # ---------- 15: MASTER store selector remains fully open ----------
        page = new_page(browser, configured=True, is_master=True)
        route_rpc(page, json_route(200, {
            "scope": {}, "period": {}, "filters": {}, "source": {},
            "summary": {"operational_quantity": 0, "total_financed": 0}, "stores": [], "banks": [],
            "status_by_store": [], "status_by_bank": [], "plans": [], "plans_by_store_department": [],
            "spf_extra": [], "proposal_outcomes": []
        }))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
        page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
        page.wait_for_timeout(300)
        master_disabled = page.eval_on_selector("#geStoreFilter", "el => el.disabled")
        master_options = page.eval_on_selector_all("#geStoreFilter option", "els => els.length")
        check("15: MASTER store selector NOT constrained (all stores + ALL still offered)", not master_disabled and master_options > 1)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Gestão Real Provider Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
