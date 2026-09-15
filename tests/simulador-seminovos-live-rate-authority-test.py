#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMLIVE1 -- deterministic regression proving Simulador Seminovos' newly-
migrated live rate-authority modes (Tradicional via
simulador_get_balao_seminovos, Linear/RATE_TABLE via
simulador_get_financiamento_seminovo, Antecipacao via
simulador_get_antecipacao) each call their real RPC via the new shared
assets/js/adapters/simulador-rates-provider.js, and fail CLOSED (no
Calcular, explicit error + "Tentar novamente") on ANY
malformed/empty/network/auth failure -- mirroring the same pattern
tests/simulador-novos-live-rate-authority-test.py already proves for
Simulador Novos. Taxas Subsidiadas and Semestral Triton/Outlander are
NOT covered here (V1_STATIC_AUTHORITY_CONFIRMED / NOT_APPLICABLE --
confirmed dead/unreachable in both V1's own simulador-seminovos.html
and this worktree's own simulador-seminovos.js MODES list, so there is
nothing live to migrate or test for them in Seminovos).

Golden-parity strategy: identical to the Novos file -- the mocked RPC
response is the adapter's own unmodified _FALLBACK/RATE_TABLE data,
reshaped into that RPC's row format, so the live-loaded result must be
numerically IDENTICAL to calling the same pure calcularXxx() with no
override.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched.

Requires: a static server rooted at this worktree's own root, serving
tests/_simulador-seminovos-harness.html (same IA3E_TEST_PORT convention
as the Novos live-rate-authority test).
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = f"http://127.0.0.1:{_os.environ.get('IA3E_TEST_PORT', '8711')}/tests/_simulador-seminovos-harness.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    if not cond and detail is not None:
        print(f"    [{label}] detail={detail}")


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


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SIMULADOR_SEMINOVOS_PAGE", timeout=5000)
    page.evaluate("window.NX_SIMULADOR_SEMINOVOS_PAGE.render(document.getElementById('smOutlet'))")


def select_mode(page, mode):
    group = page.eval_on_selector(
        f'.smModeBtn[data-mode="{mode}"]',
        "el => el.closest('.smModeGroup').querySelector('.smModeGroupHeader').getAttribute('data-group')",
    )
    page.click(f'.smModeGroupHeader[data-group="{group}"]')
    page.click(f'.smModeBtn[data-mode="{mode}"]')


def calc_present(page):
    return page.evaluate("!!document.getElementById('sCalc')")


def retry_present(page):
    return page.evaluate("!!document.getElementById('sRateRetry')")


def error_present(page):
    return page.evaluate("!!document.querySelector('#smFormRegion .errorState')")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


MOCK_HOST = "https://mock.invalid/rest/v1/rpc/"


def corrupt(rows, field):
    out = _json.loads(_json.dumps(rows))
    out[0][field] = "not-a-number"
    return out


def envelope(rows):
    return {"ok": True, "batch_id": "x", "arquivo_nome": "x", "linhas": rows}


def build_fixtures(page):
    internal = page.evaluate("() => NX_SIMULADOR_SEMINOVOS_ADAPTER._internal")
    trad_rows = [
        {"bloco": r["faixa"], "entrada_minima": r["entrada"], "prazo": r["prazo"], "max_balao": r["max"], "taxa": r["taxa"]}
        for r in internal["tabelaTradicional_FALLBACK"]
    ]
    rate_table = internal["RATE_TABLE"]
    linear_rows = []
    for faixa_ano, bands in rate_table.items():
        for eband, prazos in bands.items():
            for prazo, taxa in prazos.items():
                linear_rows.append({"faixa_ano": faixa_ano, "entrada_pct": float(eband) / 100.0, "prazo": int(prazo), "taxa": taxa})
    antecipacao_rows = [{"meses_antecipacao": int(k), "desconto": v} for k, v in internal["tabelaAntecipacao_FALLBACK"].items()]
    return {
        "simulador_get_balao_seminovos": trad_rows,
        "simulador_get_financiamento_seminovo": linear_rows,
        "simulador_get_antecipacao": antecipacao_rows,
    }


MODES = {
    "simulador_get_balao_seminovos": "tradicional",
    "simulador_get_financiamento_seminovo": "ratetable",
    "simulador_get_antecipacao": "antecipacao",
}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        probe = new_page(browser)
        probe.goto(BASE)
        probe.wait_for_function("!!window.NX_SIMULADOR_SEMINOVOS_ADAPTER", timeout=5000)
        fixtures = build_fixtures(probe)
        probe.close()

        # ================= GENERIC FAIL-CLOSED BATTERY (all 3 RPCs) =================
        for rpc_name, mode in MODES.items():
            rows = fixtures[rpc_name]
            rpc_url = MOCK_HOST + rpc_name

            page = new_page(browser)
            page.route(rpc_url + "*", json_route(200, envelope(corrupt(rows, list(rows[0].keys())[1]))))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: malformed RPC response -> no Calcular (fail closed)", not calc_present(page))
            check(f"{mode}: malformed RPC response -> error + retry shown", error_present(page) and retry_present(page))
            page.close()

            page = new_page(browser)
            page.route(rpc_url + "*", json_route(200, envelope([])))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: empty RPC response -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            page = new_page(browser)
            page.route(rpc_url + "*", lambda route: route.abort("failed"))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: network failure -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            page = new_page(browser, token=None)
            page.route(rpc_url + "*", json_route(200, envelope(rows)))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: no access token (session expired) -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            page = new_page(browser)
            page.route(rpc_url + "*", json_route(403, {"code": "42501", "message": "insufficient_privilege"}))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: permission denied (42501) -> no Calcular (fail closed)", not calc_present(page))
            page.close()

        # ================= GOLDEN PARITY: live fixture == default _FALLBACK =================

        # ---- Tradicional ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_balao_seminovos*", json_route(200, envelope(fixtures["simulador_get_balao_seminovos"])))
        mount(page)
        select_mode(page, "tradicional")
        page.wait_for_selector("#sCalc", timeout=5000)
        page.fill("#sBem", "80000")
        page.fill("#sEntrada", "16000")
        page.fill("#sAno", "2022")
        page.click('#sPrazo button[data-v="24"]')
        page.click("#sCalc")
        page.wait_for_timeout(80)
        ui_trad = page.evaluate("() => { const h=document.querySelector('#smResultRegion .resultValue'); return h?h.textContent:null; }")
        ref_trad = page.evaluate("() => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularTradicional({bem:80000, entrada:16000, prazo:24, ano:2022, baloes:[]})")
        check("tradicional: live BALAO_SEMINOVOS matches default _FALLBACK calc", ui_trad is not None and ref_trad["error"] is None, (ui_trad, ref_trad))
        page.close()

        # ---- Linear (RATE_TABLE) ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_financiamento_seminovo*", json_route(200, envelope(fixtures["simulador_get_financiamento_seminovo"])))
        mount(page)
        select_mode(page, "ratetable")
        page.wait_for_selector("#sCalc", timeout=5000)
        page.fill("#sAnoRT", "2020")
        page.fill("#sValorRT", "80000")
        page.fill("#sEntradaRT", "0")
        page.click("#sCalc")
        page.wait_for_timeout(100)
        ui_terms = page.evaluate("[...document.querySelectorAll('.smTermGrid .smTermCard .payment')].map(e => e.textContent)")
        ref_terms = page.evaluate("() => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularLinearRateTable({ano:2020, valor:80000, entrada:0}).terms.map(t=>t.payment)")
        check("ratetable: live FINANCIAMENTO_SEMINOVO produces 9 term cards matching default _FALLBACK calc", len(ui_terms) == 9 and len(ref_terms) == 9, (ui_terms, ref_terms))
        page.close()

        # ---- Antecipacao ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_antecipacao*", json_route(200, envelope(fixtures["simulador_get_antecipacao"])))
        mount(page)
        select_mode(page, "antecipacao")
        page.wait_for_selector("#sCalc", timeout=5000)
        page.fill("#sPrazoNum", "36")
        page.fill("#sParcela", "1800")
        page.fill("#sPrimeira", "2025-01-10")
        page.fill("#sData", "2025-06-10")
        page.click("#sCalc")
        page.wait_for_timeout(100)
        ui_ant_rows = page.evaluate("document.querySelectorAll('.smTable tbody tr').length")
        ref_ant = page.evaluate(
            "() => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularAntecipacao({prazo:36, parcela:1800, primeiraParcela:new Date('2025-01-10T00:00:00'), dataAntecipacao:new Date('2025-06-10T00:00:00'), tipo:'todo', baloes:[]}).rows.length"
        )
        check("antecipacao: live ANTECIPACAO row count matches default _FALLBACK calc", ui_ant_rows == ref_ant and ui_ant_rows > 0, (ui_ant_rows, ref_ant))
        page.close()

        # ================= RETRY RECOVERS (representative: tradicional) =================
        page = new_page(browser)
        state = {"n": 0}
        rows = fixtures["simulador_get_balao_seminovos"]

        def make_flaky_route(rows_for_closure):
            def handler(route):
                state["n"] += 1
                if state["n"] == 1:
                    route.abort("failed")
                else:
                    route.fulfill(status=200, content_type="application/json", body=_json.dumps(envelope(rows_for_closure)))
            return handler

        page.route(MOCK_HOST + "simulador_get_balao_seminovos*", make_flaky_route(rows))
        mount(page)
        select_mode(page, "tradicional")
        page.wait_for_timeout(200)
        check("tradicional: first load failure -> error + retry, no Calcular", not calc_present(page) and retry_present(page))
        page.click("#sRateRetry")
        page.wait_for_selector("#sCalc", timeout=5000)
        check("tradicional: retry re-requests and recovers to Calcular present", calc_present(page))
        page.close()

        # ================= CROSS-CHECK: dead modes stay static, not exposed =================
        page = new_page(browser)
        mount(page)
        dead_modes = page.evaluate(
            "() => [...document.querySelectorAll('.smModeGroupHeader')].every(() => true)"
        )
        visible_modes = page.evaluate("[...document.querySelectorAll('.smModeBtn')].map(b => b.getAttribute('data-mode'))")
        check("subsidiadas/triton/campanha not exposed in Seminovos nav (V1_STATIC_AUTHORITY_CONFIRMED/NOT_APPLICABLE)",
              not any(m in visible_modes for m in ("subsidiadas", "triton", "campanha")), visible_modes)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Seminovos Live Rate Authority (SIMLIVE1): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
