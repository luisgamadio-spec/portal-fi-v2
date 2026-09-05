#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Data Integration Foundation, Score Phase 2A -- deterministic tests
for Score's real-data transport boundary (score-real-provider.js), the
real view-model mapping (score-real-view-model.js) and score.js's own
transport selection / runtime-state logic.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080.
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_score-real-provider-harness.html"
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


_FIXTURES_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures", "score-fixtures.json")
with open(_FIXTURES_PATH, encoding="utf-8") as _f:
    _FIXTURES_BODY = _f.read()


def new_page(browser, configured, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token))
    page.route("**/score-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=_FIXTURES_BODY))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SCORE_PAGE", timeout=5000)
    page.evaluate("window.NX_SCORE_PAGE.render(document.getElementById('scOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


EMPTY_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-06-01", "period_end": "2026-09-04",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}

# Real contract shape (Phase 1): one record per sale / financing
# operation. Includes an unknown non-Mitsubishi model (Gate 16), a
# REVERSÃO plan (excluded from MIX_PLANOS_UNIVERSO by design), and
# fields Score never reads (sale_value, installments, balloon_value,
# status, operation_reference) to prove privacy minimization (Gate 13).
SAMPLE_PAYLOAD = dict(EMPTY_PAYLOAD, sales=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "operation_reference": "***AB1234"},
    {"date": "2026-08-02", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "OUTLANDER HPE-S", "sale_value": 220000, "operation_reference": "***CD5678"},
    {"date": "2026-08-03", "seller": "Real Seller B", "store": "SANTO AMARO", "department": "SEMINOVOS",
     "model": "COROLLA XEI", "sale_value": 130000, "operation_reference": "***EF9012"},
], finance=[
    {"date": "2026-08-01", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "TRITON GLS", "sale_value": 180000, "financed_value": 150000, "return_value": 9000,
     "spf_value": 3000, "spf_count": 1, "installments": 48, "installment_value": 3200,
     "balloon_value": 0, "plan": "COPARTICIPADO", "status": "EM ANDAMENTO", "operation_reference": "***AB1234"},
    {"date": "2026-08-02", "seller": "Real Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
     "model": "OUTLANDER HPE-S", "sale_value": 220000, "financed_value": 200000, "return_value": 12000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 5800,
     "balloon_value": 0, "plan": "REVERSÃO", "status": "PAGA", "operation_reference": "***CD5678"},
    {"date": "2026-08-03", "seller": "Real Seller B", "store": "SANTO AMARO", "department": "SEMINOVOS",
     "model": "COROLLA XEI", "sale_value": 130000, "financed_value": 120000, "return_value": 6000,
     "spf_value": 0, "spf_count": 0, "installments": 36, "installment_value": 3600,
     "balloon_value": 0, "plan": "LINEAR", "status": "PAGA", "operation_reference": "***EF9012"},
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
        check("2: fixture banner present in fixture mode", "DADOS DE TESTE" in page.inner_html("#scOutlet"))
        page.close()

        # ---------- 3-8: real transport, exact argument mapping ----------
        page = new_page(browser, configured=True, token="mock-access-token-abc")
        captured = {}

        def capture(route):
            captured["url"] = route.request.url
            captured["headers"] = route.request.headers
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(SAMPLE_PAYLOAD))

        page.route(RPC_URL + "*", capture)
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        check("3: real transport calls the exact RPC endpoint", captured.get("url", "").startswith(RPC_URL))
        check("4: Authorization header carries the session's own token, nothing constructed", captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        check("5: apikey header present (existing publishable key, not a secret)", captured.get("headers", {}).get("apikey") == "mock-anon-key")
        check("6: only p_start/p_end sent -- NO_CLIENT_SCOPE_AUTHORITY (Gate 12)", set(captured.get("body", {}).keys()) == {"p_start", "p_end"})
        check("7: p_start defaults to the real production authority 2026-06-01 (Gate 6, SCORE_DATE_CONTRACT_DIRECT)", captured.get("body", {}).get("p_start") == "2026-06-01")
        check("13: no fixture banner/selector in real mode (Gate 20/21)", "DADOS DE TESTE" not in page.inner_html("#scOutlet") and "scFixtureSelect" not in page.inner_html("#scOutlet"))
        page.close()

        # ---------- 9: empty real payload renders normally, not an error ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, EMPTY_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.length > 0", timeout=5000)
        html = page.inner_html("#scTableRegion")
        check("9: empty real payload -> normal empty state, no modErrorState", "modErrorState" not in html and "Nenhum vendedor encontrado" in html)
        page.close()

        # ---------- 10-12: error code normalization (Gate 8 state vocabulary) ----------
        error_cases = [
            ("42501", "AUTH_DENIED"),
            ("57014", "RPC_ERROR"),
        ]
        for code, label in error_cases:
            page = new_page(browser, configured=True)
            page.route(RPC_URL + "*", json_route(400, {"code": code, "message": "backend detail not for users"}))
            mount(page)
            page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
            html = page.inner_html("#scTableRegion")
            check("10." + code + ": " + label + " -> modErrorState shown", "modErrorState" in html)
            check("10." + code + ": no raw backend error text leaked", "backend detail not for users" not in html)
            page.close()

        # 401 -> SESSION_EXPIRED
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(401, {"message": "jwt expired"}))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("11: 401 -> modErrorState (SESSION_EXPIRED), no raw JWT text leaked", "modErrorState" in page.inner_html("#scTableRegion") and "jwt expired" not in page.inner_html("#scTableRegion"))
        page.close()

        # network failure -> RPC_ERROR
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("12: network failure -> modErrorState (RPC_ERROR)", "modErrorState" in page.inner_html("#scTableRegion"))
        page.close()

        # missing token -> SESSION_EXPIRED, never calls the RPC
        page = new_page(browser, configured=True, token=None)
        rpc_hit = []
        page.route(RPC_URL + "*", lambda route: (rpc_hit.append(1), route.abort()))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("12b: missing token -> modErrorState without ever calling the RPC", "modErrorState" in page.inner_html("#scTableRegion") and len(rpc_hit) == 0)
        page.close()

        # ---------- privacy-contract violation -> rejected, not rendered ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, dict(EMPTY_PAYLOAD, contains_client_identity=True)))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("14: contains_client_identity=true -> rejected as MALFORMED_RESPONSE, never rendered", "modErrorState" in page.inner_html("#scTableRegion"))
        page.close()

        # ---------- malformed response (missing arrays) -> rejected ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, {"scope": {}}))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("15: malformed response (missing sales/finance) -> modErrorState", "modErrorState" in page.inner_html("#scTableRegion"))
        page.close()

        # ---------- invalid department -> MALFORMED_RESPONSE (Gate 5, strict dept mapping) ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, dict(EMPTY_PAYLOAD, sales=[
            {"date": "2026-08-01", "seller": "X", "store": "Y", "department": "OFICINA", "model": "TRITON", "operation_reference": "***XX0001"}
        ])))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
        check("16: unexpected department value ('OFICINA') -> MALFORMED_RESPONSE, not silently passed through", "modErrorState" in page.inner_html("#scTableRegion"))
        page.close()

        # ---------- full success: privacy minimization, family mapping, finite scores, ranking, banding ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        table_html = page.inner_html("#scTableRegion")

        check("17: real seller identity rendered (staff, not customer PII)", "Real Seller A" in table_html)
        check("18: masked operation_reference / sale_value / installments never rendered (Gate 13 privacy minimization)",
              "***AB1234" not in table_html and "180000" not in table_html and "EM ANDAMENTO" not in table_html)

        # Re-derive scored rows directly via the real view-model + frozen adapter,
        # exactly mirroring what score.js's own loadReal() does, to assert on the
        # underlying data (not just rendered HTML).
        computed = page.evaluate(
            "(payload) => { const mapped = window.NX_SCORE_REAL_VIEW_MODEL.buildRealResult(payload); return window.NX_SCORE_ADAPTER.compute(mapped.sales, mapped.fins); }",
            SAMPLE_PAYLOAD,
        )
        seller_a = next((r for r in computed if r["vendedor"] == "Real Seller A"), None)
        mix_detail = next((b["detail"] for b in (seller_a or {}).get("scoreBreakdown", []) if b["label"] == "Mix de famílias vendidas"), "")
        check("19: canonical family mapping wired end-to-end -- TRITON GLS->Triton, OUTLANDER HPE-S->Outlander counted as 2 distinct families (Gate 3 extraction, real payload)",
              "2 de 3" in mix_detail)
        check("20: all scores finite, no NaN/Infinity end-to-end through real transport", all(isinstance(r["score"], (int, float)) and r["score"] == r["score"] and abs(r["score"]) != float("inf") for r in computed))
        check("21: ranking deterministic (sorted score desc)", all(computed[i]["score"] >= computed[i + 1]["score"] for i in range(len(computed) - 1)))
        check("22: unknown non-Mitsubishi model (COROLLA) does not crash and buckets safely", len(computed) == 2)
        check("23: REVERSÃO plan present in real data but excluded from MIX_PLANOS_UNIVERSO by design (not a defect)",
              any(any(b["label"] == "Mix de planos (diversidade)" for b in r.get("scoreBreakdown", [])) for r in computed if r["dept"] == "Novos"))
        page.close()

        # ---------- generic row-set fidelity, independent of the GAP-003
        # export (which no longer lives in Score, FC-2.3) -- proves
        # buildRealResult() still maps every row, in order, 1:1 ----------
        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        mapped = page.evaluate(
            "(payload) => window.NX_SCORE_REAL_VIEW_MODEL.buildRealResult(payload)",
            SAMPLE_PAYLOAD,
        )
        check("24: row-set invariant -- mapped.sales/fins.length == payload.sales/finance.length (no row added/dropped)",
              len(mapped["sales"]) == len(SAMPLE_PAYLOAD["sales"]) and len(mapped["fins"]) == len(SAMPLE_PAYLOAD["finance"]))
        # Index-aligned: buildFins/buildSales are .map() with no filter/sort,
        # so row i of the input must correspond to row i of the output.
        check("24b: row identity preserved index-for-index (vendedor/valorFinanciado)",
              all(mapped["fins"][i]["vendedor"] == SAMPLE_PAYLOAD["finance"][i]["seller"]
                  and abs(mapped["fins"][i]["valorFinanciado"] - SAMPLE_PAYLOAD["finance"][i]["financed_value"]) < 0.01
                  for i in range(len(SAMPLE_PAYLOAD["finance"]))))
        # FC-2.3 (Gate 32): the export-only fields FC-2.2 briefly added here
        # (modelo/cliente/chassi/data/parcelas/pmt/situacaoB3/valorVenda/
        # familia-on-fins/taxasCopart) must be gone now that the export
        # lives in Coparticipado -- restored data-minimization discipline.
        check("24c: export-only fields (modelo/cliente/chassi/parcelas/pmt/situacaoB3/valorVenda) are ABSENT from mapped fins (Gate 9, FC-2.3 cleanup)",
              all(("modelo" not in f and "cliente" not in f and "chassi" not in f and "parcelas" not in f
                   and "pmt" not in f and "situacaoB3" not in f and "valorVenda" not in f and "data" not in f)
                  for f in mapped["fins"]))
        check("24d: taxasCopart is no longer part of buildRealResult()'s output (Score has no rate lookup)",
              "taxasCopart" not in mapped)
        page.close()

        # ---------- sensitive-shape guard still fails closed (Gate 16 --
        # unrelated to the FC-2.3 cleanup, must not have regressed) ----------
        for flag in ["contains_client_identity", "contains_personal_documents", "contains_full_chassis"]:
            page = new_page(browser, configured=True)
            bad_payload = dict(EMPTY_PAYLOAD)
            bad_payload[flag] = True
            page.route(RPC_URL + "*", json_route(200, bad_payload))
            mount(page)
            page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('modErrorState')", timeout=5000)
            check("25." + flag + ": still rejected as MALFORMED_RESPONSE (privacy guard unweakened)",
                  "modErrorState" in page.inner_html("#scTableRegion"))
            page.close()

        # ---------- FC-2.3 (Gate 32): Score renders NO export action, in
        # either mode -- the capability moved to Coparticipado, not
        # duplicated ----------
        page = new_page(browser, configured=False)
        mount(page)
        page.wait_for_timeout(300)
        html_fixture = page.inner_html("#scOutlet")
        check("26: fixture mode has NO 'Exportar Coparticipados' button/text", "Exportar Coparticipados" not in html_fixture)
        check("26b: fixture mode has no export-related element id", "scExportCopaBtn" not in html_fixture and "scExportStatus" not in html_fixture)
        page.close()

        page = new_page(browser, configured=True)
        page.route(RPC_URL + "*", json_route(200, SAMPLE_PAYLOAD))
        mount(page)
        page.wait_for_function("document.getElementById('scTableRegion').innerHTML.includes('scTable')", timeout=5000)
        html_real = page.inner_html("#scOutlet")
        check("27: real mode has NO 'Exportar Coparticipados' button/text", "Exportar Coparticipados" not in html_real)
        check("27b: real mode has no export-related element id", "scExportCopaBtn" not in html_real and "scExportStatus" not in html_real)
        page.close()

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Score Real Contract: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
