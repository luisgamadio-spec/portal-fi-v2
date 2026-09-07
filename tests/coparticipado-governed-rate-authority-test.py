#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2_COPART_GOVERNED_RATE_AUTHORITY_CORRECTION -- deterministic
regression proving Gestão de Coparticipados' financial rebate
calculation uses the governed rate authority (simulador_get_
coparticipado, the same ACTIVE managed batch Simulador de Novos'
reference implementation consumes -- see
docs/CHANGE-PROPOSAL-V2-COPART-GOVERNED-RATE-AUTHORITY.md) and NEVER
the legacy/stale operational_score_coparticipated_data "rates" field
(backed by a table proven frozen since 2026-06-30 in the read-only
Secure reference investigation).

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. The governed-rate fixture used
(tests/fixtures/coparticipado-governed-rates-contract.json) is a frozen
CONTRACT REGRESSION snapshot, not a runtime authority -- the real V2
module always calls the live RPC.

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
GOVERNED_RPC_URL = "https://mock.invalid/rest/v1/rpc/simulador_get_coparticipado"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(configured=True, token="mock-access-token-abc"):
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


_FIXTURES_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures")
with open(_os.path.join(_FIXTURES_DIR, "coparticipado-fixtures.json"), encoding="utf-8") as _f:
    _FIXTURES_BODY = _f.read()
with open(_os.path.join(_FIXTURES_DIR, "coparticipado-governed-rates-contract.json"), encoding="utf-8") as _f:
    GOVERNED_CONTRACT = _json.load(_f)

# Real ACTIVE governed contract's own commercial values (Secure reference,
# read-only). Copied here (not re-read from the fixture) so this file's
# assertions are self-contained and legible without cross-referencing
# the JSON.
OUTLANDER_SIGNATURE_REBATE_TOTAL = 0.17123756815255212
OUTLANDER_SIGNATURE_REBATE_BRABUS = 0.48

ALL_15_MODELS = sorted(set(m["modelo"] for m in GOVERNED_CONTRACT["linhas"]["matriz_modelos"]))


def new_page(browser, configured=True, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(configured, token))
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


def route_governed(page, payload=None, status=200):
    body = payload if payload is not None else GOVERNED_CONTRACT
    page.route(GOVERNED_RPC_URL + "*", json_route(status, body))


EMPTY_OPERATIONAL = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}


def operational_with_outlander(financed_value, stale_rate=True):
    # Deliberately includes the STALE legacy rate (20.5%/40%, matching
    # the real coparticipado_modelos_fi values proven in the Secure
    # investigation) in the operational payload's own "rates" field --
    # RED before the fix: this is what the module used to consume.
    # GREEN after the fix: this field is present but never read for
    # calculation (Gate 9/10/34 of the change proposal).
    rates = [{"model": "OUTLANDER SIGNATURE", "term": 48, "rate": 0.0069, "total_rebate": 20.5, "brabus_percent": 40}] if stale_rate else []
    return dict(EMPTY_OPERATIONAL, finance=[{
        "date": "2026-08-26", "seller": "Vendedor Sintetico", "store": "ALPHAVILLE", "department": "NOVOS",
        "model": "OUTLANDER SIGNATURE", "sale_value": 364990, "financed_value": financed_value, "return_value": 0,
        "spf_value": 0, "spf_count": 0, "installments": 48, "installment_value": 0,
        "balloon_value": 0, "plan": "COPARTICIPADO", "status": "PAGA", "operation_reference": "***A02055"
    }], rates=rates)


def get_outlander_calc(page, financed_value):
    return page.evaluate(
        "(v) => window.NX_COPARTICIPADO_ADAPTER.calcCoparticipacaoDetalhe({modelo:'OUTLANDER SIGNATURE', valorFinanciado:v})",
        financed_value,
    )


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: golden R$114.990 -- governed wins over stale legacy rate ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page)
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        c = get_outlander_calc(page, 114990)
        check("1: OUTLANDER SIGNATURE resolved", c["ok"] is True)
        check("1: rebateTotal == governed raw (0.17123756815255212), not stale (0.205)", c["rebateTotal"] == OUTLANDER_SIGNATURE_REBATE_TOTAL)
        check("1: parteBrabus == governed raw (0.48), not stale (0.40)", c["parteBrabus"] == OUTLANDER_SIGNATURE_REBATE_BRABUS)
        check("1: valorRebateTotal ~= R$19.690,61", abs(c["valorRebateTotal"] - 19690.607961861968) < 0.01)
        check("1: coparticipacao ~= R$9.451,49 (golden)", abs(c["coparticipacao"] - 9451.49182169374) < 0.01)
        page.close()

        # ---------- 2: golden R$146.000 ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(146000)))
        route_governed(page)
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        c = get_outlander_calc(page, 146000)
        check("2: coparticipacao ~= R$12.000,33 for R$146.000 (golden)", abs(c["coparticipacao"] - 12000.328776130851) < 0.01)
        page.close()

        # ---------- 3: negative golden -- must NEVER be the stale 20.5/40 result ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page)
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        c = get_outlander_calc(page, 114990)
        check("3: rebateTotal != stale 0.205", c["rebateTotal"] != 0.205)
        check("3: parteBrabus != stale 0.40", c["parteBrabus"] != 0.40)
        check("3: coparticipacao != stale R$9.429,18", abs(c["coparticipacao"] - 9429.18) > 1)
        panel_html = page.inner_html("#cpPanel")
        check("3: rendered table shows the golden value, not the stale one", "9.451" in panel_html or "9451" in panel_html)
        check("3b: rendered table does NOT show the stale value", "9.429" not in panel_html and "23.573" not in panel_html)
        page.close()

        # ---------- 4: 15/15 model parity against the governed contract ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, EMPTY_OPERATIONAL))
        route_governed(page)
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modTabGroup')", timeout=5000)
        model_match = 0
        financial_match = 0
        # One representative row per model (rebate_total/rebate_brabus
        # already proven term-invariant for all 15 in the Secure
        # reference investigation; this fixture carries all 6 terms per
        # model for completeness, this loop just needs one each).
        by_model = {}
        for row in GOVERNED_CONTRACT["linhas"]["matriz_modelos"]:
            by_model.setdefault(row["modelo"], row)
        for modelo, row in by_model.items():
            got = page.evaluate(
                "(args) => window.NX_COPARTICIPADO_ADAPTER.calcCoparticipacaoDetalhe({modelo: args.modelo, valorFinanciado: 100000})",
                {"modelo": modelo},
            )
            expected_cop = 100000 * row["rebate_total"] * row["rebate_brabus"]
            if got["ok"] and got["rebateTotal"] == row["rebate_total"] and got["parteBrabus"] == row["rebate_brabus"]:
                model_match += 1
            if got["ok"] and abs(got["coparticipacao"] - expected_cop) < 0.01:
                financial_match += 1
        check(f"4: 15-model source parity = {model_match}/15", model_match == 15)
        check(f"4: 15-model financial parity = {financial_match}/15", financial_match == 15)
        page.close()

        # ---------- 5: term invariance -- all 6 terms per model share rebate_total/rebate_brabus ----------
        by_model_all = {}
        for row in GOVERNED_CONTRACT["linhas"]["matriz_modelos"]:
            by_model_all.setdefault(row["modelo"], set()).add((row["rebate_total"], row["rebate_brabus"]))
        invariant_models = sum(1 for v in by_model_all.values() if len(v) == 1)
        check(f"5: term invariance across all 6 terms for all 15 models (contract fixture) = {invariant_models}/15", invariant_models == 15)
        check("5b: exactly 15 distinct models in the governed contract fixture", len(ALL_15_MODELS) == 15)

        # ---------- 6: STALE FALLBACK NEGATIVE TEST -- governed fails, stale legacy rate IS available -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990, stale_rate=True)))
        route_governed(page, status=500, payload={"code": "57014", "message": "backend detail"})
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        html = page.inner_html("#cpPanel")
        check("6: governed authority failure -> modErrorState (BLOCK, not stale fallback)", "modErrorState" in html)
        check("6: stale value never rendered even though it was available in the operational payload", "20,5" not in html and "9.429" not in html)
        page.close()

        # ---------- 7: empty governed matriz_modelos -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page, payload={"ok": True, "batch_id": "x", "arquivo_nome": "y", "linhas": {"matriz_modelos": [], "tx_coef": []}})
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("7: empty governed matriz_modelos -> modErrorState (BLOCK)", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 8: malformed governed response (missing linhas) -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page, payload={"ok": True, "batch_id": "x", "arquivo_nome": "y"})
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("8: malformed governed response (missing linhas) -> modErrorState (BLOCK)", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 9: governed-specific 42501 (operational succeeds) -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page, status=400, payload={"code": "42501", "message": "backend detail not for users"})
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        html = page.inner_html("#cpPanel")
        check("9: governed 42501 -> modErrorState (BLOCK)", "modErrorState" in html)
        check("9: no raw backend error text leaked", "backend detail not for users" not in html)
        page.close()

        # ---------- 10: governed-specific network failure (operational succeeds) -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        page.route(GOVERNED_RPC_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("10: governed network failure -> modErrorState (BLOCK)", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        # ---------- 11: governed-specific session-expired (401) (operational succeeds) -> BLOCK ----------
        page = new_page(browser)
        page.route(RPC_URL + "*", json_route(200, operational_with_outlander(114990)))
        route_governed(page, status=401, payload={"message": "unauthorized"})
        mount(page)
        page.wait_for_function("document.getElementById('cpPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("11: governed 401 -> modErrorState (BLOCK)", "modErrorState" in page.inner_html("#cpPanel"))
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Coparticipado Governed Rate Authority Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
