#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2_SIMULADOR_NOVOS_GOVERNED_AUTHORITY_MIGRATION -- deterministic
regression proving Simulador Novos' "Plano Coparticipado" campaign mode
uses the governed rate/coefficient authority (simulador_get_coparticipado,
the SAME ACTIVE managed batch V2 Coparticipado's own Human-approved
module already consumes) and NEVER the stale hardcoded MODELS/TX_COEF
embedded in financiamento-campanha.adapter.js.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. The governed-rate fixture used
(tests/fixtures/simulador-novos-governed-campanha-contract.json) is a
frozen CONTRACT REGRESSION snapshot (read-only, captured 2026-09-07),
not a runtime authority -- the real V2 module always calls the live RPC.

RED-before-fix: stash assets/js/simulador-novos.js and assets/js/adapters/
financiamento-campanha.adapter.js (scoped git stash, leaving unrelated
dirty work untouched), then re-run this file -- it must fail because the
pre-fix code never calls the governed RPC and never gates the Calcular
button on campState.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (same convention as every other Portal V2 test).
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_simulador-novos-harness.html"
GOVERNED_RPC_URL = "https://mock.invalid/rest/v1/rpc/simulador_get_coparticipado"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-anon-key',
  textEndpoint: null
};
window.NX_AUTH = {
  isAuthConfigured: true,
  getAccessToken: function () { return Promise.resolve(%s); }
};
""" % (("'" + token + "'") if token else "null")


_FIXTURES_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures")
with open(_os.path.join(_FIXTURES_DIR, "simulador-novos-governed-campanha-contract.json"), encoding="utf-8") as _f:
    GOVERNED_CONTRACT = _json.load(_f)

MODEL_ROWS = GOVERNED_CONTRACT["linhas"]["matriz_modelos"]
COEF_ROWS = GOVERNED_CONTRACT["linhas"]["tx_coef"]
ALL_15_MODELS = sorted(set(m["modelo"] for m in MODEL_ROWS))
PRAZOS = [12, 18, 24, 36, 48, 60]


def coef_for(prazo, taxa):
    for r in COEF_ROWS:
        if r["prazo"] == prazo and abs(r["taxa"] - taxa) < 1e-7:
            return r["coeficiente"]
    return None


def rows_for(modelo):
    return [r for r in MODEL_ROWS if r["modelo"] == modelo]


def compute_expected(modelo, sale, entry):
    """Mirrors calcularCampanha()'s formula exactly, computed from the
    governed fixture -- never a hand-typed literal (Gate 17/18/19)."""
    rows = rows_for(modelo)
    entry_min = rows[0]["entrada_minima"]
    rebate_pct = rows[0]["rebate_total"]
    hpe = rows[0]["rebate_hpe"]
    brabus = rows[0]["rebate_brabus"]
    min_value = sale * entry_min
    valid = sale > 0 and entry >= min_value
    financed = max(sale - entry, 0) if valid else 0
    terms = {}
    for r in rows:
        p, taxa = r["prazo"], r["taxa"]
        coef = coef_for(p, taxa)
        acrescimo = 0.0411 if p <= 24 else 0.0622
        terms[p] = (financed * (1 + acrescimo)) * coef if (valid and coef) else None
    rebate_total = financed * rebate_pct if valid else None
    rebate_brabus = rebate_total * brabus if valid else None
    rebate_hpe = rebate_total * hpe if valid else None
    final_sale = max(sale - rebate_brabus, 0) if valid else None
    return {"financed": financed, "terms": terms, "rebateTotal": rebate_total,
            "rebateBrabus": rebate_brabus, "rebateHpe": rebate_hpe, "finalSale": final_sale}


def close(a, b, eps=0.02):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < eps


def brl_to_float(s):
    import re
    if s is None:
        return None
    m = re.search(r"-?[\d.]+,\d+", s.replace("\xa0", " "))
    return float(m.group(0).replace(".", "").replace(",", ".")) if m else None


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SIMULADOR_NOVOS_PAGE", timeout=5000)
    page.evaluate("window.NX_SIMULADOR_NOVOS_PAGE.render(document.getElementById('smOutlet'))")


def enter_campanha(page):
    page.click('.smModeBtn[data-mode="campanha"]')


def wait_camp_state(page, state, timeout_ms=5000):
    page.wait_for_function(
        "(s) => window.NX_SIMULADOR_NOVOS_PAGE.getCampState() === s", arg=state, timeout=timeout_ms
    )


def calc_button_present(page):
    return page.evaluate("!!document.getElementById('nCalc')")


def retry_button_present(page):
    return page.evaluate("!!document.getElementById('nCampRetry')")


def has_error_state(page):
    return page.evaluate("!!document.querySelector('#smResultRegion .errorState, #smFormRegion .errorState')")


def read_result(page):
    def kpi(label):
        return page.evaluate(
            """(label) => {
                const kpis = [...document.querySelectorAll('#smResultRegion .kpiLabel')];
                const k = kpis.find(e => e.textContent.trim() === label);
                if (!k) return null;
                const val = k.nextElementSibling;
                return val ? val.textContent : null;
            }""",
            label,
        )
    financed = brl_to_float(kpi("Financiado"))
    rebate_total = brl_to_float(kpi("Rebate total — custo comercial da taxa"))
    rebate_hpe = brl_to_float(kpi("Rebate HPE"))
    rebate_brabus = brl_to_float(page.evaluate(
        "() => { const c=[...document.querySelectorAll('.smEmphasisCard .smEmphasisValue')][0]; return c?c.textContent:null; }"
    ))
    final_sale = brl_to_float(page.evaluate(
        "() => { const e=document.querySelector('.smEmphasisValuePrimary'); return e?e.textContent:null; }"
    ))
    payments_raw = page.evaluate(
        "[...document.querySelectorAll('.smTermGrid .smTermCard')].map(c => { "
        "const p = c.querySelector('.payment'); return p ? p.textContent : null; })"
    )
    payments = [brl_to_float(x) for x in payments_raw]
    return {
        "financed": financed, "rebateTotal": rebate_total, "rebateHpe": rebate_hpe,
        "rebateBrabus": rebate_brabus, "finalSale": final_sale, "payments": payments,
    }


def run_case(page, modelo, sale, entry, label):
    page.select_option("#nModelo", modelo)
    page.fill("#nSale", str(sale))
    page.fill("#nEntry", str(entry))
    page.click("#nCalc")
    page.wait_for_timeout(80)
    got = read_result(page)
    exp = compute_expected(modelo, sale, entry)
    ok = (
        close(got["financed"], exp["financed"])
        and close(got["rebateTotal"], exp["rebateTotal"])
        and close(got["rebateHpe"], exp["rebateHpe"])
        and close(got["rebateBrabus"], exp["rebateBrabus"])
        and close(got["finalSale"], exp["finalSale"])
        and len(got["payments"]) == len(PRAZOS)
        and all(close(got["payments"][i], exp["terms"][PRAZOS[i]]) for i in range(len(PRAZOS)))
    )
    check(label, ok)
    if not ok:
        print(f"    [{label}] got={got} exp={exp}")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: AUTHORITY SUCCESS -- governed READY, 15/15/90/90/39/39 ----------
        page = new_page(browser)
        page.route(GOVERNED_RPC_URL + "*", json_route(200, GOVERNED_CONTRACT))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "READY")
        check("1a: campState=READY on valid governed payload", True)
        check("1b: Calcular button present once READY", calc_button_present(page))
        auth = page.evaluate("window.NX_SIMULADOR_NOVOS_PAGE.getCampAuthorityForTest()")
        check("1c: 15 unique governed models loaded", len(auth["modelNames"]) == 15)
        check("1d: modelNames match governed set exactly", sorted(auth["modelNames"]) == ALL_15_MODELS)
        model_select_options = page.evaluate(
            "[...document.querySelectorAll('#nModelo option')].map(o => o.value)"
        )
        check("1e: <select> options sourced from governed authority, not hardcoded MODELS", sorted(model_select_options) == ALL_15_MODELS)

        # 90/90 model x term coverage: every governed row's own (prazo,taxa)
        # must resolve through campAuthority.coefLookup (proves 39/39 keys
        # required by the 90 rows are all consumable).
        coverage = page.evaluate(
            """() => {
                const a = window.NX_SIMULADOR_NOVOS_PAGE.getCampAuthorityForTest();
                return %s.map(r => a.coefLookup(r.prazo, r.taxa) != null);
            }""" % _json.dumps(MODEL_ROWS)
        )
        check("1f: 90/90 governed model×term rows resolve a coefficient", len(coverage) == 90 and all(coverage))

        # ---------- 2: RUSH golden -- rebate + taxa divergence resolved via governed authority ----------
        run_case(page, "ECLIPSE CROSS RUSH", 200000, 120000, "2: ECLIPSE CROSS RUSH golden (governed rebate+taxa+coef)")

        # ---------- 3: TRITON TARMAC golden -- previously-missing local coefficient key ----------
        run_case(page, "TRITON TARMAC", 200000, 120000, "3: TRITON TARMAC golden (governed prazo18/taxa0.0029 coefficient)")

        # ---------- 4: OUTLANDER SIGNATURE golden -- control model ----------
        run_case(page, "OUTLANDER SIGNATURE", 200000, 120000, "4: OUTLANDER SIGNATURE golden (control)")
        page.close()

        # ---------- 5: AUTHORITY EMPTY -- fail closed, no fallback ----------
        page = new_page(browser)
        empty_body = {"ok": True, "batch_id": "x", "arquivo_nome": "x", "linhas": {"matriz_modelos": [], "tx_coef": []}}
        page.route(GOVERNED_RPC_URL + "*", json_route(200, empty_body))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("5a: empty governed payload -> campState=ERROR", True)
        check("5b: Calcular button absent (no fallback path)", not calc_button_present(page))
        check("5c: Retry button present", retry_button_present(page))
        check("5d: error message rendered (no stale value shown)", has_error_state(page))
        page.close()

        # ---------- 6: MISSING tx_coef only -- still fail closed ----------
        page = new_page(browser)
        missing_coef = {"ok": True, "batch_id": "x", "arquivo_nome": "x", "linhas": {"matriz_modelos": MODEL_ROWS, "tx_coef": []}}
        page.route(GOVERNED_RPC_URL + "*", json_route(200, missing_coef))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("6: matriz_modelos present but tx_coef empty -> ERROR (no coefficient fallback)", not calc_button_present(page))
        page.close()

        # ---------- 7: PERMISSION DENIED (42501) -- fail closed ----------
        page = new_page(browser)
        page.route(GOVERNED_RPC_URL + "*", json_route(403, {"code": "42501", "message": "insufficient_privilege"}))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("7: permission denied (42501) -> ERROR, no fallback", not calc_button_present(page))
        page.close()

        # ---------- 8: NETWORK FAILURE -- fail closed ----------
        page = new_page(browser)
        page.route(GOVERNED_RPC_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("8: network failure -> ERROR, no fallback", not calc_button_present(page))
        page.close()

        # ---------- 9: SESSION EXPIRED (no access token) -- fail closed ----------
        page = new_page(browser, token=None)
        page.route(GOVERNED_RPC_URL + "*", json_route(200, GOVERNED_CONTRACT))
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("9: no access token (session expired) -> ERROR, no fallback", not calc_button_present(page))
        page.close()

        # ---------- 10: RETRY recovers after transient failure ----------
        page = new_page(browser)
        state = {"n": 0}

        def flaky_route(route):
            state["n"] += 1
            if state["n"] == 1:
                route.abort("failed")
            else:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(GOVERNED_CONTRACT))

        page.route(GOVERNED_RPC_URL + "*", flaky_route)
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "ERROR")
        check("10a: first load failure -> ERROR", not calc_button_present(page))
        page.click("#nCampRetry")
        wait_camp_state(page, "READY")
        check("10b: retry re-requests governed authority and recovers to READY", calc_button_present(page))
        page.close()

        # ---------- 11: caching -- leaving and re-entering 'campanha' does not re-fetch ----------
        page = new_page(browser)
        call_count = {"n": 0}

        def counting_route(route):
            call_count["n"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(GOVERNED_CONTRACT))

        page.route(GOVERNED_RPC_URL + "*", counting_route)
        mount(page)
        enter_campanha(page)
        wait_camp_state(page, "READY")
        page.click('.smModeBtn[data-mode="tradicional"]')
        enter_campanha(page)
        page.wait_for_timeout(150)
        check("11: governed authority loaded once per session (cached across mode re-entry)", call_count["n"] == 1)
        page.close()

        # ---------- 12: non-campaign engine regression (Linear, untouched formula) ----------
        page = new_page(browser)
        page.route(GOVERNED_RPC_URL + "*", json_route(200, GOVERNED_CONTRACT))
        mount(page)
        page.click('.smModeBtn[data-mode="linear"]')
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "20000")
        page.wait_for_timeout(120)
        linear_ok = page.evaluate("!!document.querySelector('.smTermGrid, #smResultRegion .kpiLabel')")
        check("12: non-campaign engine (Linear) renders unaffected by governed migration", linear_ok)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Novos Governed Authority Migration: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
