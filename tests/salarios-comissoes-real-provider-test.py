#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH-4A -- deterministic regression proving the Salários & Comissões real
provider matches the live-proven RPC contract (RH-1/RH-2/RH-3/RH-3A),
fails closed on every RPC failure mode, never falls back to a raw
table, never recomputes a financial formula, and never leaks a
sensitive field -- with one narrow, RPC-shape-aware exception
(contains_masked_chassis:true is the EXPECTED, safe shape for
operational_salary_details, proven live this engagement).

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. A separate, non-mutating live-
definition layer (RH-1 through RH-3A's own Management-API-based RPC
body/schema reads) already proves the real contract these fixtures
mirror -- REAL_PROFILE_RUNTIME_TEST_UNAVAILABLE for a genuine browser-
level authenticated RPC call: this test file has no real per-user
Supabase Auth JWT available (only a Management API PAT, a fundamentally
different credential never used for REST calls), so no such call is
attempted or fabricated.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_salarios-comissoes-real-provider-harness.html"
PERIODS_URL = "https://mock.invalid/rest/v1/rpc/operational_commission_periods"
METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_commission_metrics"
ANALYST_URL = "https://mock.invalid/rest/v1/rpc/operational_analyst_commission_metrics_v2"
DIRECTORY_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_manager_directory"
DETAILS_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_details"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null
};
window.NX_AUTH = {
  isAuthConfigured: true,
  getAccessToken: function () { return Promise.resolve(%s); }
};
""" % (("'" + token + "'") if token else "null")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


# Fixture shapes mirror the REAL live contract confirmed by RH-1/RH-3/
# RH-3A (pg_get_functiondef reads against yacqlelpzchcotgngwbh) -- not
# invented. No real employee names/CPF/salary/commission values.
PERIODS_ROWS = {"rows": [
    {"id": "p1", "nome_periodo": "21/07 à 20/08", "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "status": "ABERTO", "periodo_atual": True, "ativo": True, "criado_por": "seed"}
]}
METRICS_ROWS = {"scope": {"profile": "RH", "departments": ["NOVOS", "SEMINOVOS"], "is_master": False, "is_director": False, "is_seller": False, "store": None},
                "period_start": "2026-07-21", "period_end": "2026-08-20", "spf_net_percent": 70,
                "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
                "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False, "rows": []}
ANALYST_ROWS = {"absence_aware": True, "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False, "rows": []}
DIRECTORY_ROWS = {"period_start": "2026-07-21", "period_end": "2026-08-20", "assignment_source": "ACTIVE_PORTAL_PROFILE",
                   "rows": [], "ambiguous_assignments": 0, "contains_client_identity": False,
                   "contains_personal_documents": False, "contains_operational_identifiers": False}
DETAILS_ROWS = {"scope": METRICS_ROWS["scope"], "period_start": "2026-07-21", "period_end": "2026-08-20",
                 "seller_filter": None, "seller_count": 0, "row_count": 0, "row_limit": 2000, "truncated": False,
                 "rows": [], "contains_client_identity": False, "contains_personal_documents": False,
                 "contains_full_chassis": False, "contains_masked_chassis": True, "contains_chassis": False, "contains_nbs": False}


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SALARIOS_COMISSOES_REAL_PROVIDER")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: static source-text audit (Gate 34) ----------
        # Checked against CODE ONLY (block/line comments stripped) -- the
        # file's own header comments legitimately NAME every excluded
        # RPC/table (documenting what must never be called/read) and the
        # anti-leak guard's own rejection list legitimately contains the
        # literal string 'cpf' (data to detect and reject, not a
        # parameter sent to the server). A raw substring search over the
        # whole file self-flags this documentation; same mistake class
        # already hit and fixed in this codebase's own PM-6D.1 test
        # suite (stripSqlLineComments) -- comments must be stripped
        # before any "is X absent from the CODE" claim is made.
        import os
        import re

        def strip_js_comments(text):
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            text = re.sub(r"(?m)//.*$", "", text)
            return text

        src_path = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "salarios-comissoes-real-provider.js")
        raw_src = open(src_path, encoding="utf-8").read()
        src = strip_js_comments(raw_src)
        forbidden_rpcs = ["master_close_commission_period", "master_reopen_commission_period", "master_admin_manage",
                           "master_commission_closings", "master_commission_snapshot", "master_commission_snapshot_export"]
        forbidden_tables = ["from(", ".select(", "snapshot_comissoes", "snapshot_operational_detail",
                             "portal_sales", "portal_finance_operations", "portal_spf_operations",
                             "from usuarios", "from analistas_fi"]
        forbidden_terms = ["service_role", "SERVICE_ROLE", "sk-proj", "api.openai.com", "shareMin", "faixa =", "comissaoTotal", "comissaoPrincipal"]
        check("1a: no MASTER write/closing RPC referenced in executable code", not any(t in src for t in forbidden_rpcs))
        check("1b: no raw-table read pattern in executable code", not any(t in src for t in forbidden_tables))
        check("1c: no secret/service-role/OpenAI/financial-formula literal in executable code", not any(t in src for t in forbidden_terms))
        # RH-5B.3: +1 RPC (operational_portal_config -- a real, already-
        # live, already authenticated-granted config-reference RPC,
        # feeds only the static "Faixas de comissão" card).
        # RH-5C.1: +2 RPCs (operational_gestor_fi_commission,
        # operational_commission_faixa_rows -- new governed authority,
        # both server-computed, zero client-side formula per test 1c
        # above -- this provider only transports their responses).
        check("1d: exactly 8 real RPC names referenced (governed surface only)", sum(rpc in src for rpc in [
            "operational_commission_periods", "operational_commission_metrics",
            "operational_analyst_commission_metrics_v2", "operational_salary_manager_directory",
            "operational_salary_details", "operational_portal_config",
            "operational_gestor_fi_commission", "operational_commission_faixa_rows"]) == 8)
        # 'cpf' as a REJECTION-LIST value (data the guard checks FOR and
        # blocks) is expected and correct; 'p_cpf' as an outgoing RPC
        # parameter would not be -- these are the two real cases to tell
        # apart, not "the substring 'cpf' appears anywhere".
        check("1e: CPF is never sent as an outgoing RPC parameter (p_cpf absent)", "p_cpf" not in src)

        # ---------- 2: loadCommissionPeriods ----------
        page = new_page(browser)
        page.route(PERIODS_URL + "*", json_route(200, PERIODS_ROWS))
        mount(page)
        rows = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionPeriods()")
        check("2a: loadCommissionPeriods returns the real rows array", rows == PERIODS_ROWS["rows"])
        page.close()

        # ---------- 3: loadCommissionMetrics -- success + params ----------
        page = new_page(browser)
        captured = {}

        def metrics_capture(route):
            captured["body"] = _json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(METRICS_ROWS))

        page.route(METRICS_URL + "*", metrics_capture)
        mount(page)
        result = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionMetrics('2026-07-21','2026-08-20')")
        check("3a: loadCommissionMetrics sends exact p_start/p_end", captured["body"] == {"p_start": "2026-07-21", "p_end": "2026-08-20"})
        check("3b: loadCommissionMetrics returns the real payload unmodified", result == METRICS_ROWS)
        page.close()

        # ---------- 4: loadCommissionMetrics -- missing period fails closed, no network call ----------
        page = new_page(browser)
        call_count = {"n": 0}
        page.route(METRICS_URL + "*", lambda route: (call_count.__setitem__("n", call_count["n"] + 1), route.fulfill(status=200, content_type="application/json", body=_json.dumps(METRICS_ROWS))))
        mount(page)
        err = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionMetrics(null, null).then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("4a: missing period -> INVALID_FILTER, not a crash", err == {"ok": False, "state": "INVALID_FILTER"})
        check("4b: zero network calls made for an invalid period (fail closed BEFORE fetch)", call_count["n"] == 0)
        page.close()

        # ---------- 5: server-side INVALID_FILTER passthrough (real 22023) ----------
        page = new_page(browser)
        page.route(METRICS_URL + "*", json_route(400, {"code": "22023", "message": "Período máximo permitido: 732 dias."}))
        mount(page)
        err2 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionMetrics('2020-01-01','2026-01-01').then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("5: real 732-day-cap 22023 rejection classified INVALID_FILTER", err2 == {"ok": False, "state": "INVALID_FILTER"})
        page.close()

        # ---------- 6: PERMISSION_DENIED (real 42501) ----------
        page = new_page(browser)
        page.route(ANALYST_URL + "*", json_route(403, {"code": "42501", "message": "Perfil sem acesso aos dados operacionais."}))
        mount(page)
        err3 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadAnalystCommissionMetrics('2026-07-21','2026-08-20').then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("6: real 42501 rejection classified PERMISSION_DENIED", err3 == {"ok": False, "state": "PERMISSION_DENIED"})
        page.close()

        # ---------- 7: SESSION_EXPIRED -- no access token ----------
        page = new_page(browser, token=None)
        page.route(DIRECTORY_URL + "*", json_route(200, DIRECTORY_ROWS))
        mount(page)
        err4 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadManagerDirectory('2026-07-21','2026-08-20').then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("7: no access token -> SESSION_EXPIRED, no fallback data", err4 == {"ok": False, "state": "SESSION_EXPIRED"})
        page.close()

        # ---------- 8: network failure -> BACKEND_ERROR ----------
        page = new_page(browser)
        page.route(DETAILS_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        err5 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadSalaryDetails('2026-07-21','2026-08-20', null).then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("8: network failure -> BACKEND_ERROR, not silent", err5 == {"ok": False, "state": "BACKEND_ERROR"})
        page.close()

        # ---------- 9: loadSalaryDetails -- p_seller_id null vs provided ----------
        page = new_page(browser)
        captured2 = {}
        page.route(DETAILS_URL + "*", lambda route: (captured2.__setitem__("body", _json.loads(route.request.post_data)), route.fulfill(status=200, content_type="application/json", body=_json.dumps(DETAILS_ROWS))))
        mount(page)
        r9 = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadSalaryDetails('2026-07-21','2026-08-20', 'seller-uuid-1')")
        check("9a: loadSalaryDetails sends the provided p_seller_id", captured2["body"]["p_seller_id"] == "seller-uuid-1")
        check("9b: expected masked-chassis shape is NOT rejected by the anti-leak guard", r9 == DETAILS_ROWS)
        page.close()

        # ---------- 10: anti-leak guard rejects genuinely sensitive shapes ----------
        for bad_flag in ["contains_full_chassis", "contains_chassis", "contains_client_identity", "contains_personal_documents", "contains_nbs"]:
            page = new_page(browser)
            bad_body = dict(DETAILS_ROWS)
            bad_body[bad_flag] = True
            page.route(DETAILS_URL + "*", json_route(200, bad_body))
            mount(page)
            errX = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadSalaryDetails('2026-07-21','2026-08-20', null).then(
              () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
            check(f"10: {bad_flag}=true rejected as BACKEND_ERROR (anti-leak guard fires)", errX == {"ok": False, "state": "BACKEND_ERROR"})
            page.close()

        # ---------- 11: anti-leak guard rejects a raw cpf key on any RPC ----------
        page = new_page(browser)
        bad_metrics = dict(METRICS_ROWS)
        bad_metrics["cpf"] = "00000000000"
        page.route(METRICS_URL + "*", json_route(200, bad_metrics))
        mount(page)
        err6 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionMetrics('2026-07-21','2026-08-20').then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("11: a raw cpf key anywhere in the payload is rejected", err6 == {"ok": False, "state": "BACKEND_ERROR"})
        page.close()

        # ---------- 12: loadCommissionDashboardData -- partial failure resilience ----------
        page = new_page(browser)
        page.route(METRICS_URL + "*", json_route(200, METRICS_ROWS))
        page.route(ANALYST_URL + "*", lambda route: route.abort("failed"))
        page.route(DIRECTORY_URL + "*", json_route(200, DIRECTORY_ROWS))
        mount(page)
        dash = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionDashboardData('2026-07-21','2026-08-20')")
        check("12a: metrics leg succeeds independently", dash["metrics"] == METRICS_ROWS and dash["metricsError"] is None)
        check("12b: analyst leg fails independently, carries a classified error (never a fabricated zero)", dash["analystMetrics"] is None and dash["analystMetricsError"]["state"] == "BACKEND_ERROR")
        check("12c: directory leg succeeds independently despite the analyst leg failing", dash["managerDirectory"] == DIRECTORY_ROWS and dash["managerDirectoryError"] is None)
        page.close()

        # ---------- 13: loadCommissionDashboardData -- missing period fails closed before any leg fires ----------
        page = new_page(browser)
        any_call = {"n": 0}
        for url in (METRICS_URL, ANALYST_URL, DIRECTORY_URL):
            page.route(url + "*", lambda route: (any_call.__setitem__("n", any_call["n"] + 1), route.fulfill(status=200, content_type="application/json", body="{}")))
        mount(page)
        err7 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionDashboardData(null, null).then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("13a: dashboard aggregate also fails closed on missing period", err7 == {"ok": False, "state": "INVALID_FILTER"})
        check("13b: zero network calls across all 3 legs for an invalid period", any_call["n"] == 0)
        page.close()

        # ---------- 14: loadPortalConfig -- reshapes {rows:[{chave,valor}]} into a plain object, numeric coercion ----------
        page = new_page(browser)
        CONFIG_URL = "https://mock.invalid/rest/v1/rpc/operational_portal_config"
        page.route(CONFIG_URL + "*", json_route(200, {"rows": [
            {"chave": "share_minimo", "valor": "40"},
            {"chave": "vendedor_faixa_baixo_share_baixo", "valor": "10"},
            {"chave": "ia_texto_habilitada", "valor": "true"}
        ]}))
        mount(page)
        cfg = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadPortalConfig()")
        check("14a: loadPortalConfig reshapes rows into a plain {chave: valor} object", cfg["share_minimo"] == 40 and cfg["vendedor_faixa_baixo_share_baixo"] == 10)
        check("14b: a non-numeric value (e.g. a boolean-as-text config key) is preserved as-is, not coerced to NaN", cfg["ia_texto_habilitada"] == "true")
        page.close()

        # ---------- 15: loadGestorFiCommission (RH-5C.1) -- {pronto,...} shape accepted (no rows array), passthrough only, missing period fails closed ----------
        page = new_page(browser)
        GESTOR_URL = "https://mock.invalid/rest/v1/rpc/operational_gestor_fi_commission"
        GESTOR_READY = {"pronto": True, "period_start": "2026-07-21", "period_end": "2026-08-20", "beneficiary_name": "Demo",
                         "vendidas": 100, "financiadas": 40, "share": 40.0, "producao": 1, "retorno": 200000, "spf": 20000,
                         "spf_qty": 10, "spf_liquido": 14000, "base": 214000, "faixa": 0.003, "comissao_principal": 642,
                         "bonus_spf": 300, "comissao_final": 942, "contains_client_identity": False, "contains_personal_documents": False}
        page.route(GESTOR_URL + "*", json_route(200, GESTOR_READY))
        mount(page)
        g = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadGestorFiCommission('2026-07-21','2026-08-20')")
        check("15a: a {pronto:true,...} shape (no rows array) is accepted, not rejected as malformed", g["pronto"] is True and g["comissao_final"] == 942)
        check("15b: the provider performs zero arithmetic -- comissao_final passes through byte-identical to what the server sent", g["comissao_final"] == GESTOR_READY["comissao_final"] and g["faixa"] == GESTOR_READY["faixa"])
        page.close()

        page = new_page(browser)
        GESTOR_NOT_READY = {"pronto": False, "motivo": "NENHUM_BENEFICIARIO_CONFIGURADO"}
        page.route(GESTOR_URL + "*", json_route(200, GESTOR_NOT_READY))
        mount(page)
        g2 = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadGestorFiCommission('2026-07-21','2026-08-20')")
        check("15c: a real pronto:false response passes through as-is -- never papered over with a fabricated zero/value", g2["pronto"] is False and g2["motivo"] == "NENHUM_BENEFICIARIO_CONFIGURADO")
        page.close()

        page = new_page(browser)
        gestor_call = {"n": 0}
        page.route(GESTOR_URL + "*", lambda route: (gestor_call.__setitem__("n", gestor_call["n"] + 1), route.fulfill(status=200, content_type="application/json", body="{}")))
        mount(page)
        err8 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadGestorFiCommission(null, null).then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("15d: loadGestorFiCommission fails closed on a missing period, zero network calls made", err8 == {"ok": False, "state": "INVALID_FILTER"} and gestor_call["n"] == 0)
        page.close()

        page = new_page(browser)
        page.route(GESTOR_URL + "*", lambda route: route.fulfill(status=403, content_type="application/json", body=_json.dumps({"code": "42501", "message": "Acesso exclusivo do perfil Master."})))
        mount(page)
        err9 = page.evaluate("""() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadGestorFiCommission('2026-07-21','2026-08-20').then(
          () => ({ok:true}), (e) => ({ok:false, state:e.state}))""")
        check("15e: a real 42501 (non-MASTER) rejection classifies as PERMISSION_DENIED", err9 == {"ok": False, "state": "PERMISSION_DENIED"})
        page.close()

        # ---------- 16: loadCommissionFaixaRows (RH-5C.1) -- passthrough only, no client-side classification ----------
        page = new_page(browser)
        FAIXA_URL = "https://mock.invalid/rest/v1/rpc/operational_commission_faixa_rows"
        FAIXA_ROWS = {"rows": [
            {"perfil": "VENDEDOR", "seller_id": "s1", "store": "ABC", "department": "NOVOS", "faixa": 0.2, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": "ALTO"},
            {"perfil": "GERENTE", "store": "ABC", "department": "NOVOS", "faixa": 0.04, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": None}
        ], "contains_client_identity": False, "contains_personal_documents": False}
        page.route(FAIXA_URL + "*", json_route(200, FAIXA_ROWS))
        mount(page)
        f = page.evaluate("() => window.NX_SALARIOS_COMISSOES_REAL_PROVIDER.loadCommissionFaixaRows('2026-07-21','2026-08-20')")
        check("16a: rows pass through unmodified, including server-computed faixa_level/share_tier/retorno_tier", f["rows"][0]["faixa_level"] == "MAXIMA" and f["rows"][1]["retorno_tier"] is None)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Salários & Comissões Real Provider (RH-4A): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
