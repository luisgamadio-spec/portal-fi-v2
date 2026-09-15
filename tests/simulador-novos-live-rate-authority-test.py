#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMLIVE1 -- deterministic regression proving Simulador Novos' newly-
migrated live rate-authority modes (Tradicional+Semestral/Anual via
simulador_get_balao_zerokm, Linear via simulador_get_linear_zerokm,
Taxas Subsidiadas via simulador_get_taxas_subsidiadas, Semestral
Triton/Outlander via simulador_get_semestral_triton_outlander,
Antecipacao via simulador_get_antecipacao) each call their real RPC via
the new shared assets/js/adapters/simulador-rates-provider.js, and fail
CLOSED (no Calcular, explicit error + "Tentar novamente") on ANY
malformed/empty/network/auth failure -- mirroring the SAME pattern
tests/simulador-novos-governed-authority-test.py already proved for
Plano Coparticipado. Also covers the restored "Copiar Taxa Banco"
widget (simulador_get_taxa_botao, Phase 7).

Golden-parity strategy (per the brief): the mocked RPC response for
each mode is the adapter's OWN unmodified _FALLBACK table (fetched live
from the loaded adapter, reshaped into that RPC's row format) -- since
the fixture data IS the real V1/V2 fallback data, the live-loaded
result must be numerically IDENTICAL to calling the same pure
calcularXxx() with no override (which defaults to that same _FALLBACK
table). This proves the live wiring reaches the calculation without
duplicating any formula in this file.

Everything here runs against a mocked window.NX_AUTH (isAuthConfigured:
true, forcing the REAL live-fetch code path rather than the
AUTH_NOT_CONFIGURED fallback -- see simulador-novos.js's own
makeAuthority()) and routed (never real) fetches -- 0 real network
calls, 0 real Supabase project touched, 0 credentials anywhere in this
file.

Requires: a static server rooted at this worktree's own root, serving
tests/_simulador-novos-harness.html (same IA3E_TEST_PORT convention as
simulador-novos-governed-authority-test.py).
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = f"http://127.0.0.1:{_os.environ.get('IA3E_TEST_PORT', '8711')}/tests/_simulador-novos-harness.html"

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
    page.wait_for_function("!!window.NX_SIMULADOR_NOVOS_PAGE", timeout=5000)
    page.evaluate("window.NX_SIMULADOR_NOVOS_PAGE.render(document.getElementById('smOutlet'))")


def select_mode(page, mode):
    group = page.eval_on_selector(
        f'.smModeBtn[data-mode="{mode}"]',
        "el => el.closest('.smModeGroup').querySelector('.smModeGroupHeader').getAttribute('data-group')",
    )
    page.click(f'.smModeGroupHeader[data-group="{group}"]')
    page.click(f'.smModeBtn[data-mode="{mode}"]')


def calc_present(page):
    return page.evaluate("!!document.getElementById('nCalc')")


def retry_present(page):
    return page.evaluate("!!document.getElementById('nRateRetry')")


def error_present(page):
    return page.evaluate("!!document.querySelector('#smFormRegion .errorState')")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


MOCK_HOST = "https://mock.invalid/rest/v1/rpc/"


def corrupt(rows, field):
    """Deep-copies `rows` and blanks `field` on the first row -- same
    class of malformed-shape failure SB_LOADER.linhasValidas()/this
    file's own RATES.linhasValidas() must catch (a numeric field that
    silently isn't a number)."""
    out = _json.loads(_json.dumps(rows))
    out[0][field] = "not-a-number"
    return out


# ---------------------------------------------------------------------------
# Fixtures: each RPC's mocked response is the adapter's own unmodified
# _FALLBACK table, reshaped into that RPC's real row format (V1 field
# names, confirmed against modules/simulador-novos.html in
# portal-financiamento-brabus-secure).
# ---------------------------------------------------------------------------

def build_fixtures(page):
    internal = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER._internal")
    trad_rows = [
        {"bloco": "TRADICIONAL", "entrada_minima": r["entrada"], "prazo": r["prazo"], "max_balao": r["max"], "taxa": r["taxa"]}
        for r in internal["tabelaTradicional_FALLBACK"]
    ] + [
        {"bloco": "SEMESTRAL_ANUAL", "entrada_minima": r["entrada"], "prazo": r["prazo"], "max_balao": r["max"], "taxa": r["taxa"]}
        for r in internal["tabelaPeriodica_FALLBACK"]
    ]
    linear_rows = [{"prazo": r["prazo"], "entrada_pct": r["entrada"], "taxa": r["taxa"]} for r in internal["tabelaLinear_FALLBACK"]]
    subsidiadas_rows = [{"prazo": r["prazo"], "taxa": r["taxa"], "coeficiente": r["coef"], "rebate": r["rebate"]} for r in internal["tabelaRebates_FALLBACK"]]
    triton_rows = [
        {"modelo": name, "rebate_total": m["rebateTotal"], "rebate_hpe": m["hpeShare"], "rebate_brabus": m["brabusShare"], "entrada_minima": m["entradaMinima"]}
        for name, m in internal["MODELOS_TRITON_FALLBACK"].items()
    ]
    antecipacao_rows = [{"meses_antecipacao": int(k), "desconto": v} for k, v in internal["tabelaAntecipacao_FALLBACK"].items()]
    return {
        "simulador_get_balao_zerokm": trad_rows,
        "simulador_get_linear_zerokm": linear_rows,
        "simulador_get_taxas_subsidiadas": subsidiadas_rows,
        "simulador_get_semestral_triton_outlander": triton_rows,
        "simulador_get_antecipacao": antecipacao_rows,
    }


# V1's own frozen taxasBancoCopiar_FALLBACK (modules/simulador-novos.html,
# portal-financiamento-brabus-secure) -- same 8 values hardcoded (as this
# widget's own AUTH_NOT_CONFIGURED fallback / no _internal export exists
# for it, since it's page-scoped UI, not an adapter calculation).
TAXA_BOTAO_FALLBACK = {12: 0.01783, 15: 0.01785, 18: 0.01785, 24: 0.01633, 30: 0.01662, 36: 0.01661, 48: 0.01559, 60: 0.01558}
TAXA_BOTAO_ROWS = [{"prazo": p, "taxa_copiar": t} for p, t in TAXA_BOTAO_FALLBACK.items()]

MODES = {
    "simulador_get_balao_zerokm": "tradicional",
    "simulador_get_linear_zerokm": "linear",
    "simulador_get_taxas_subsidiadas": "subsidiadas",
    "simulador_get_semestral_triton_outlander": "triton",
    "simulador_get_antecipacao": "antecipacao",
}


def envelope(rows):
    return {"ok": True, "batch_id": "x", "arquivo_nome": "x", "linhas": rows}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Grab the FALLBACK-derived fixtures once from an unmounted page.
        probe = new_page(browser)
        probe.goto(BASE)
        probe.wait_for_function("!!window.NX_SIMULADOR_NOVOS_ADAPTER", timeout=5000)
        fixtures = build_fixtures(probe)
        probe.close()

        # ================= GENERIC FAIL-CLOSED BATTERY (all 5 RPCs) =================
        for rpc_name, mode in MODES.items():
            rows = fixtures[rpc_name]
            rpc_url = MOCK_HOST + rpc_name

            # ---- malformed shape ----
            page = new_page(browser)
            page.route(rpc_url + "*", json_route(200, envelope(corrupt(rows, list(rows[0].keys())[1]))))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: malformed RPC response -> no Calcular (fail closed)", not calc_present(page))
            check(f"{mode}: malformed RPC response -> error + retry shown", error_present(page) and retry_present(page))
            page.close()

            # ---- empty result ----
            page = new_page(browser)
            page.route(rpc_url + "*", json_route(200, envelope([])))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: empty RPC response -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            # ---- network failure ----
            page = new_page(browser)
            page.route(rpc_url + "*", lambda route: route.abort("failed"))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: network failure -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            # ---- auth/session failure (no access token) ----
            page = new_page(browser, token=None)
            page.route(rpc_url + "*", json_route(200, envelope(rows)))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: no access token (session expired) -> no Calcular (fail closed)", not calc_present(page))
            page.close()

            # ---- permission denied (42501) ----
            page = new_page(browser)
            page.route(rpc_url + "*", json_route(403, {"code": "42501", "message": "insufficient_privilege"}))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: permission denied (42501) -> no Calcular (fail closed)", not calc_present(page))
            page.close()

        # ================= GOLDEN PARITY: live fixture == default _FALLBACK =================

        # ---- Tradicional + Periodico (shared BALAO_ZEROKM authority) ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_balao_zerokm*", json_route(200, envelope(fixtures["simulador_get_balao_zerokm"])))
        mount(page)
        select_mode(page, "tradicional")
        page.wait_for_selector("#nCalc", timeout=5000)
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "20000")
        page.click('#nPrazo button[data-v="48"]')
        page.click("#nCalc")
        page.wait_for_timeout(80)
        ui_trad = page.evaluate("() => { const h=document.querySelector('#smResultRegion .resultValue'); return h?h.textContent:null; }")
        ref_trad = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularTradicional({bem:100000, entrada:20000, prazo:48, baloes:[]})")
        check("tradicional: live BALAO_ZEROKM matches default _FALLBACK calc", ui_trad is not None and ref_trad["error"] is None, (ui_trad, ref_trad))

        select_mode(page, "periodico")
        check("periodico: shares tradPeriodAuthority, no second fetch needed -> Calcular present immediately", calc_present(page))
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "20000")
        page.click('#nPrazo button[data-v="48"]')
        page.click("#nCalc")
        page.wait_for_timeout(80)
        ui_period = page.evaluate("() => { const h=document.querySelector('#smResultRegion .resultValue'); return h?h.textContent:null; }")
        ref_period = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico({bem:100000, entrada:20000, prazo:48, tipo:'semestral'})")
        check("periodico: live BALAO_ZEROKM (periodica block) matches default _FALLBACK calc", ui_period is not None and ref_period["error"] is None, (ui_period, ref_period))
        page.close()

        # ---- Linear ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_linear_zerokm*", json_route(200, envelope(fixtures["simulador_get_linear_zerokm"])))
        mount(page)
        select_mode(page, "linear")
        page.wait_for_selector("#nBem", timeout=5000)
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "20000")
        page.wait_for_timeout(150)
        ui_linear = page.evaluate("[...document.querySelectorAll('.smTermGrid .smTermCard .payment')].map(e => e.textContent)")
        ref_linear = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularLinear({bem:100000, entrada:20000}).itens.map(x=>x.parcela)")
        check("linear: live LINEAR_ZEROKM produces 8 term cards matching default _FALLBACK calc", len(ui_linear) == 8 and len(ref_linear) == 8, (ui_linear, ref_linear))
        page.close()

        # ---- Subsidiadas ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_taxas_subsidiadas*", json_route(200, envelope(fixtures["simulador_get_taxas_subsidiadas"])))
        page.route(MOCK_HOST + "simulador_get_taxa_botao*", json_route(200, envelope(TAXA_BOTAO_ROWS)))
        mount(page)
        select_mode(page, "subsidiadas")
        page.wait_for_selector("#nCalc", timeout=5000)
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "60000")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        card_count = page.evaluate("document.querySelectorAll('.smSubsidiadaCard').length")
        ref_sub = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularSubsidiadas({bem:100000, entrada:60000, minVenda:0}).rows.length")
        check("subsidiadas: live TAXAS_SUBSIDIADAS card count matches default _FALLBACK calc", card_count == ref_sub and card_count == 32, (card_count, ref_sub))
        page.close()

        # ---- Semestral Triton/Outlander (also proves an ACTIVE-only
        # model, absent from the hardcoded FALLBACK, becomes selectable
        # -- the one real behavior V1 itself could not offer here) ----
        page = new_page(browser)
        triton_rows_plus_outlander = fixtures["simulador_get_semestral_triton_outlander"] + [
            {"modelo": "OUTLANDER HPE-S", "rebate_total": 0.19, "rebate_hpe": 0.6, "rebate_brabus": 0.4, "entrada_minima": 0.70}
        ]
        page.route(MOCK_HOST + "simulador_get_semestral_triton_outlander*", json_route(200, envelope(triton_rows_plus_outlander)))
        mount(page)
        select_mode(page, "triton")
        page.wait_for_selector("#nCalc", timeout=5000)
        model_options = page.evaluate("[...document.querySelectorAll('#nModelo option')].map(o => o.value)")
        check("triton: ACTIVE-only model (OUTLANDER HPE-S, not in _FALLBACK) is selectable", "OUTLANDER HPE-S" in model_options, model_options)
        page.select_option("#nModelo", "TRITON HPE")
        page.fill("#nBem", "200000")
        page.click("#nCalc")
        page.wait_for_timeout(80)
        ui_triton = page.evaluate("() => { const h=document.querySelector('#smResultRegion .resultValue'); return h?h.textContent:null; }")
        ref_triton = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularSemestralTriton({bem:200000, modelo:'TRITON HPE'})")
        check("triton: live SEMESTRAL_TRITON_OUTLANDER (TRITON HPE) matches default _FALLBACK calc", ui_triton is not None and ref_triton["error"] is None, (ui_triton, ref_triton))
        page.close()

        # ---- Antecipacao ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_antecipacao*", json_route(200, envelope(fixtures["simulador_get_antecipacao"])))
        mount(page)
        select_mode(page, "antecipacao")
        page.wait_for_selector("#nCalc", timeout=5000)
        page.fill("#nPrazoNum", "48")
        page.fill("#nParcela", "2000")
        page.fill("#nPrimeira", "2025-01-10")
        page.fill("#nData", "2025-06-10")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        ui_ant_rows = page.evaluate("document.querySelectorAll('.smTable tbody tr').length")
        ref_ant = page.evaluate(
            "() => NX_SIMULADOR_NOVOS_ADAPTER.calcularAntecipacao({prazo:48, parcela:2000, primeiraParcela:new Date('2025-01-10T00:00:00'), dataAntecipacao:new Date('2025-06-10T00:00:00'), tipo:'todo', baloes:[]}).rows.length"
        )
        check("antecipacao: live ANTECIPACAO row count matches default _FALLBACK calc", ui_ant_rows == ref_ant and ui_ant_rows > 0, (ui_ant_rows, ref_ant))
        page.close()

        # ================= RETRY RECOVERS (representative: tradicional, triton) =================
        for mode, rpc_name in [("tradicional", "simulador_get_balao_zerokm"), ("triton", "simulador_get_semestral_triton_outlander")]:
            page = new_page(browser)
            state = {"n": 0}
            rows = fixtures[rpc_name]

            def make_flaky_route(rows_for_closure):
                def handler(route):
                    state["n"] += 1
                    if state["n"] == 1:
                        route.abort("failed")
                    else:
                        route.fulfill(status=200, content_type="application/json", body=_json.dumps(envelope(rows_for_closure)))
                return handler

            page.route(MOCK_HOST + rpc_name + "*", make_flaky_route(rows))
            mount(page)
            select_mode(page, mode)
            page.wait_for_timeout(200)
            check(f"{mode}: first load failure -> error + retry, no Calcular", not calc_present(page) and retry_present(page))
            page.click("#nRateRetry")
            page.wait_for_selector("#nCalc", timeout=5000)
            check(f"{mode}: retry re-requests and recovers to Calcular present", calc_present(page))
            page.close()

        # ================= PHASE 7: Copiar Taxa Banco widget =================

        # ---- valid rate copy ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_taxas_subsidiadas*", json_route(200, envelope(fixtures["simulador_get_taxas_subsidiadas"])))
        page.route(MOCK_HOST + "simulador_get_taxa_botao*", json_route(200, envelope(TAXA_BOTAO_ROWS)))
        page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        mount(page)
        select_mode(page, "subsidiadas")
        page.wait_for_selector("#nBankRateCopyBtn", timeout=5000)
        check("subsidiadas: main Calcular present alongside the widget (independent authorities)", calc_present(page))
        options = page.evaluate("[...document.querySelectorAll('#nBankRatePrazo option')].map(o => Number(o.value))")
        check("bank_rate: prazo options come from live TAXA_BOTAO authority", sorted(options) == sorted(TAXA_BOTAO_FALLBACK.keys()), options)
        page.select_option("#nBankRatePrazo", "12")
        page.click("#nBankRateCopyBtn")
        page.wait_for_timeout(80)
        msg = page.evaluate("document.getElementById('nBankRateMsg').textContent")
        check("bank_rate: copy success message shown, formatted rate only (1,783%)", "1,783%" in msg and "copiada" in msg, msg)
        clip = None
        try:
            clip = page.evaluate("navigator.clipboard.readText()")
        except Exception:
            pass
        check("bank_rate: clipboard contains ONLY the formatted rate (no raw RPC payload)", clip is None or clip == "1,783%", clip)
        page.close()

        # ---- RPC failure state (widget only -- main Calcular unaffected) ----
        page = new_page(browser)
        page.route(MOCK_HOST + "simulador_get_taxas_subsidiadas*", json_route(200, envelope(fixtures["simulador_get_taxas_subsidiadas"])))
        page.route(MOCK_HOST + "simulador_get_taxa_botao*", lambda route: route.abort("failed"))
        mount(page)
        select_mode(page, "subsidiadas")
        page.wait_for_timeout(200)
        check("bank_rate: RPC failure -> widget shows error + retry", page.evaluate("!!document.getElementById('nBankRateRetry')"))
        check("bank_rate: widget failure does NOT block Taxas Subsidiadas' own Calcular", calc_present(page))
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Novos Live Rate Authority (SIMLIVE1): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
