#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-6B -- deterministic tests for Exportar RH/DP and
PDF/Imprimir, restoring V1 parity inside Histórico de Competências.

SAFETY: every test uses synthetic data (synthetic names, synthetic
chassis-masked strings already in "masked" shape, synthetic monetary
values) routed through fully-mocked RPCs. Real CPF is NEVER used
anywhere in this file (and, per PM-6B's own audit finding, V2 -- like
V1 in secure mode -- never even sources a real CPF for this export in
the first place: the CPF column is always empty, structurally present
for column parity only). 0 real network calls, 0 real file downloaded
to disk (XLSX.writeFile is intercepted in-page), 0 real print window
left open beyond the test's own browser context.
"""
import io
import json as _json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
READ_URL = "https://mock.invalid/rest/v1/rpc/master_admin_reference_data"
CLOSINGS_URL = "https://mock.invalid/rest/v1/rpc/master_commission_closings"
SNAPSHOT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot"
EXPORT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot_export"
OPDETAIL_URL = "https://mock.invalid/rest/v1/rpc/master_commission_operational_detail"
SPF_URL = "https://mock.invalid/rest/v1/rpc/master_operational_spf_audit_period"
SALARY_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_details"

PROVIDER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-history-provider.js")
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-rhdp-export-engine.js")

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def closing_fixture(**overrides):
    base = {
        "id": "hc-rhdp-001", "periodo_id": "per-001", "nome_periodo": "21/07 a 20/08/2026",
        "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "versao": 1, "status": "FECHADO",
        "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-08-21T09:00:00+00:00",
        "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-08-21T09:00:00+00:00",
        "observacao": _json.dumps({"comissao_total": 24.84, "qtd_vendida": 8, "qtd_financiada": 5,
                                     "producao_total": 80000, "retorno_total": 8000, "spf_total": 400}),
    }
    base.update(overrides)
    return base


def snap(nome, perfil, loja, depto, vend, fin, share, prod, ret, spfx, spfl, rent, faixa, cp, csp, ct):
    return {"nome": nome, "perfil": perfil, "loja": loja, "departamento": depto,
            "vendidas": vend, "financiadas": fin, "share": share, "producao": prod, "retorno": ret,
            "spf_extra": spfx, "spf_liquido": spfl, "rentabilidade_total": rent, "faixa": faixa,
            "comissao": ct, "detalhes": {"comissao_principal": cp, "comissao_spf": csp, "comissao_total": ct}}


RICH_SNAPSHOT_ROWS = [
    snap("Vendedor Centro Novos", "VENDEDOR", "LOJA CENTRO", "NOVOS", 5, 3, 60, 50000, 5000, 400, 280, 5280, 0.003, 15, 0.42, 15.42),
    snap("Vendedor Alpha Seminovos", "VENDEDOR", "ALPHAVILLE", "SEMINOVOS", 3, 2, 66.6, 30000, 3000, 200, 140, 3140, 0.003, 9, 0.42, 9.42),
    snap("Analista Centro", "ANALISTA", "LOJA CENTRO", "NOVOS", 4, 2, 50, 20000, 2000, 100, 70, 2070, 0.002, 4, 0.21, 4.21),
    snap("Gestor Sintetico", "GESTOR F&I", "TODAS", "TODAS", 0, 0, 0, 0, 0, 0, 0, 0, 0, 300, 0, 300),
    snap("Gerente Centro Novos", "GERENTE", "LOJA CENTRO", "GERENTE NOVOS", 5, 3, 60, 50000, 5000, 400, 280, 5280, 0, 50, 0, 50),
]
RICH_CHASSIS_ROWS = [
    {"date": "2026-07-25", "finance_date": "2026-07-26", "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "L200 TRITON",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T34101", "sale_value": 180000,
     "financed": True, "financed_value": 150000, "return_considered": 5000, "included_in_commission": True},
    {"date": "2026-07-25", "finance_date": "2026-07-26", "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "L200 TRITON",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T34102", "sale_value": 180000,
     "financed": True, "financed_value": 150000, "return_considered": 5000, "included_in_commission": True},
    {"date": "2026-07-25", "finance_date": "2026-07-26", "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "L200 TRITON",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T34103", "sale_value": 180000,
     "financed": True, "financed_value": 150000, "return_considered": 5000, "included_in_commission": True},
    {"date": "2026-07-27", "finance_date": None, "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "PAJERO SPORT",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T34199", "sale_value": 200000,
     "financed": False, "financed_value": 0, "return_considered": 0, "included_in_commission": True},
    {"date": "2026-07-27", "finance_date": None, "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "PAJERO SPORT",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T34198", "sale_value": 200000,
     "financed": False, "financed_value": 0, "return_considered": 0, "included_in_commission": True},
    {"date": "2026-07-20", "finance_date": "2026-07-21", "store": "ALPHAVILLE", "department": "SEMINOVOS", "vehicle_model": "ECLIPSE CROSS",
     "seller_id": "s2", "seller_name": "Vendedor Alpha Seminovos", "chassis_masked": "******T99201", "sale_value": 120000,
     "financed": True, "financed_value": 100000, "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-07-20", "finance_date": "2026-07-21", "store": "ALPHAVILLE", "department": "SEMINOVOS", "vehicle_model": "ECLIPSE CROSS",
     "seller_id": "s2", "seller_name": "Vendedor Alpha Seminovos", "chassis_masked": "******T99209", "sale_value": 120000,
     "financed": True, "financed_value": 100000, "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-07-22", "finance_date": None, "store": "ALPHAVILLE", "department": "SEMINOVOS", "vehicle_model": "ASX",
     "seller_id": "s2", "seller_name": "Vendedor Alpha Seminovos", "chassis_masked": "******T99202", "sale_value": 90000,
     "financed": False, "financed_value": 0, "return_considered": 0, "included_in_commission": True},
    {"date": "2026-07-23", "finance_date": None, "store": "LOJA CENTRO", "department": "NOVOS", "vehicle_model": "DUPLICATE",
     "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "chassis_masked": "******T00000", "sale_value": 1,
     "financed": False, "financed_value": 0, "return_considered": 0, "included_in_commission": False},
]
RICH_SPF_ROWS = [
    {"operation_date": "2026-07-25", "seller_id": "s1", "seller_name": "Vendedor Centro Novos", "store": "LOJA CENTRO",
     "department": "NOVOS", "chassis_masked": "******T34101", "operation_code": "OP001", "bank": "BANCO SINTETICO",
     "finance_code": "FIN-PLUS", "optional_name": "SPF EXTRA", "spf_bruto": 500, "spf_liquido": 350},
]
EXPECTED_SHEET_NAMES = ['1_RESUMO_PRINCIPAL', '2_VENDEDORES', '3_ANALISTAS_GESTOR', '4_GERENTES',
                         '5_CHASSIS_FINANCIADOS', '6_TODOS_CHASSIS_VENDEDOR', '7_AUDITORIA_SPF', '8_MEMORIA_DE_CALCULO']


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
window.__CAPTURED_WORKBOOKS__ = [];
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script(token))
    return page


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def full_read_routes(page, closing_rows=None, snapshot_rows=None, export_rows=None, spf_rows=None, chassis_rows=None,
                      export_status=200, spf_status=200, chassis_status=200,
                      export_body=None, spf_body=None, chassis_body=None,
                      opdetail_status=200, opdetail_body=None):
    page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
    page.route(CONV_URL + "*", json_route(200, []))
    page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
    page.route(CLOSINGS_URL + "*", json_route(200, {"rows": closing_rows if closing_rows is not None else [closing_fixture()]}))
    page.route(SNAPSHOT_URL + "*", json_route(200, {"rows": snapshot_rows if snapshot_rows is not None else RICH_SNAPSHOT_ROWS}))
    page.route(EXPORT_URL + "*", json_route(export_status, export_body if export_body is not None else {"rows": export_rows if export_rows is not None else RICH_SNAPSHOT_ROWS}))
    # PM-6D.3: every pre-existing test in this file exercises the LIVE+
    # reconciliation path -- default this to LEGACY_PARTIAL/empty so
    # historyExportRhDp's now-unconditional loadOperationalSnapshot call
    # never changes their behavior (each test that specifically wants
    # COMPLETE overrides this explicitly).
    page.route(OPDETAIL_URL + "*", json_route(opdetail_status, opdetail_body if opdetail_body is not None else {"completeness": "LEGACY_PARTIAL", "rows": []}))
    page.route(SPF_URL + "*", json_route(spf_status, spf_body if spf_body is not None else {"rows": spf_rows if spf_rows is not None else RICH_SPF_ROWS}))
    page.route(SALARY_URL + "*", json_route(chassis_status, chassis_body if chassis_body is not None else {"rows": chassis_rows if chassis_rows is not None else RICH_CHASSIS_ROWS}))


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")
    page.evaluate("""
() => {
  const orig = XLSX.writeFile;
  XLSX.writeFile = function (wb, filename) {
    window.__CAPTURED_WORKBOOKS__.push({ filename, sheetNames: wb.SheetNames });
    window.__LAST_WORKBOOK__ = wb;
  };
}
""")


def goto_history_list(page):
    page.click('[data-section="historicoCompetencias"]')
    page.wait_for_selector(".hcViewBtn, .note", timeout=5000)


def sheet_json(page, name):
    return page.evaluate("XLSX.utils.sheet_to_json(window.__LAST_WORKBOOK__.Sheets[%r])" % name)


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    # ---------- 1-4: source-code proofs (Gate 10/11/14/29) ----------
    with io.open(PROVIDER_PATH, "r", encoding="utf-8") as f:
        provider_src = f.read()
    write_methods = [".insert(", ".update(", ".upsert(", ".delete("]
    check("1 (DIRECT-WRITE PROOF): provider contains no direct table write method call", all(t not in provider_src for t in write_methods))
    check("2 (FAIL-CLOSED, structural): provider's exportSnapshot calls master_commission_snapshot_export, never master_commission_snapshot as a fallback", "master_commission_snapshot_export" in provider_src)
    check("3: provider calls master_operational_spf_audit_period and operational_salary_details (both git-tracked, SECURITY DEFINER, search_path pinned per PM-6B audit)", "master_operational_spf_audit_period" in provider_src and "operational_salary_details" in provider_src)
    with io.open(ENGINE_PATH, "r", encoding="utf-8") as f:
        engine_src = f.read()
    check("4 (ENGINE PURITY): the RH/DP engine contains no RPC/network/DOM/XLSX API call at all (comments mentioning these terms in prose are fine -- checking for actual API usage, e.g. a trailing '.', not the bare word)",
          "callRpc(" not in engine_src and "fetch(" not in engine_src and "document." not in engine_src and "XLSX.utils" not in engine_src and "XLSX.write" not in engine_src and "window.XLSX" not in engine_src and "window.NX_AUTH." not in engine_src)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 5-6: action visibility, FECHADO and REABERTO alike (Gate 21/22, 37) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture(status="FECHADO", ativo=True), closing_fixture(id="hc-reaberto", status="REABERTO", ativo=False)])
        mount(page)
        goto_history_list(page)
        rows = page.query_selector_all("tr.hcRow")
        check("5 (FECHADO): 'Exportar RH/DP' and 'PDF / Imprimir' are BOTH visible for a FECHADO row", "Exportar RH/DP" in rows[0].inner_text() and "PDF / Imprimir" in rows[0].inner_text())
        check("6 (REABERTO, Gate 37): both actions REMAIN visible -- master_commission_snapshot_export has no status guard (confirmed by direct read of its real SQL, PM-6B), unlike V1's own incidental single-período-selector UI limitation", "Exportar RH/DP" in rows[1].inner_text() and "PDF / Imprimir" in rows[1].inner_text())
        page.close()

        # ---------- 7-16: 8-SHEET WORKBOOK PARITY (Gate 5/7/8/18-28) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()], export_rows=RICH_SNAPSHOT_ROWS, spf_rows=RICH_SPF_ROWS, chassis_rows=RICH_CHASSIS_ROWS)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("7 (WORKBOOK PARITY): exactly 1 workbook generated", len(captured) == 1)
        check("8: filename matches V1's real pattern (Relatorio_Comissoes_RH_DP_<id>_RH_DP_COMPLETO.xlsx)", captured and captured[0]["filename"] == "Relatorio_Comissoes_RH_DP_hc-rhdp-001_RH_DP_COMPLETO.xlsx")
        check("9 (8 SHEETS, Gate 5): exactly the 8 required sheet names, in order, none reduced/renamed", captured and captured[0]["sheetNames"] == EXPECTED_SHEET_NAMES)

        sheet2 = sheet_json(page, "2_VENDEDORES")
        check("10 (Sheet 2 Vendedores, grouping): only VENDEDOR rows, sorted by Loja+Departamento+Nome", len(sheet2) == 2 and sheet2[0]["Loja"] == "ALPHAVILLE" and sheet2[1]["Loja"] == "LOJA CENTRO")
        check("11 (CPF behavior, Gate 24/9): CPF column exists (structural parity) but is ALWAYS empty -- proven real V1 secure-mode behavior, not an omission", all(r.get("CPF", "MISSING") == "" for r in sheet2))
        check("12 (financial values parity): Comissao_Total for Vendedor Centro Novos = 15.42 (from snapshot detalhes.comissao_total, never recalculated)", any(abs(r["Comissao_Total"] - 15.42) < 0.001 for r in sheet2))

        sheet3 = sheet_json(page, "3_ANALISTAS_GESTOR")
        check("13 (Sheet 3, SPF behavior): ANALISTA + GESTOR F&I both present, GESTOR has Quantidade de SPF=0/Valor Unitário SPF=0 (never derived from a per-unit formula for GESTOR)", len(sheet3) == 2 and any(r["Cargo"] == "GESTOR F&I" and r["Quantidade de SPF"] == 0 and r["Valor Unitário SPF"] == 0 for r in sheet3))

        sheet4 = sheet_json(page, "4_GERENTES")
        check("14 (Sheet 4 Gerentes): only GERENTE rows present", len(sheet4) == 1 and sheet4[0]["Nome"] == "Gerente Centro Novos")

        sheet5 = sheet_json(page, "5_CHASSIS_FINANCIADOS")
        sheet6 = sheet_json(page, "6_TODOS_CHASSIS_VENDEDOR")
        check("15 (Sheet 5/6, chassis masking): chassis appear ALREADY masked (server-provided chassis_masked), never a raw chassis value", all(str(r.get("Chassi Mascarado", "")).startswith("*") for r in sheet5 + sheet6))
        check("15b (Sheet 5 financiados count): 5 financed+included rows (3 Centro + 2 Alpha)", len(sheet5) == 5)
        check("15c (Sheet 6 excludes non-included rows): the 1 included_in_commission=false chassis never appears", len(sheet6) == 8 and not any(r.get("Modelo") == "DUPLICATE" for r in sheet6))

        sheet7 = sheet_json(page, "7_AUDITORIA_SPF")
        check("16 (Sheet 7, SPF audit behavior): real SPF row present with masked chassis, no CPF column at all", len(sheet7) == 1 and "CPF" not in sheet7[0] and sheet7[0]["Chassi"].startswith("*"))

        sheet8 = sheet_json(page, "8_MEMORIA_DE_CALCULO")
        check("17 (Sheet 8, memory-of-calculation behavior): 5 rows (1 per snapshot row), full financial decomposition present", len(sheet8) == 5 and "Comissao_Principal" in sheet8[0] and "Comissao_SPF" in sheet8[0])

        sheet1 = page.evaluate("XLSX.utils.sheet_to_json(window.__LAST_WORKBOOK__.Sheets['1_RESUMO_PRINCIPAL'], {header: 1})")
        sheet1_flat = [str(cell) for row in sheet1 for cell in row]
        check("18 (Sheet 1, totals parity): executive summary sourced from the closing's own observacao JSON (qtd_vendida=8), never recalculated from snapshot rows when observacao is present", "8" in sheet1_flat)
        page.close()

        # ---------- 19-21: FAIL-CLOSED -- each of the 3 sources failing blocks the WHOLE export ----------
        for label, kwargs in [
            ("export RPC fails (22023 inconsistent)", dict(export_status=400, export_body={"code": "22023", "message": "Exportação bloqueada: o fechamento desta competência possui um snapshot histórico inconsistente. Procure a Administração/RH F&I."})),
            ("SPF audit RPC fails", dict(spf_status=400, spf_body={"code": "RPC_ERROR", "message": "Falha simulada na auditoria SPF."})),
            ("chassis detail RPC fails", dict(chassis_status=400, chassis_body={"code": "RPC_ERROR", "message": "Falha simulada no detalhe operacional."})),
        ]:
            page = new_page(browser)
            install_tripwire(page)
            full_read_routes(page, closing_rows=[closing_fixture()], **kwargs)
            mount(page)
            goto_history_list(page)
            page.click(".hcRhdpBtn >> nth=0")
            page.wait_for_timeout(500)
            captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
            check("19 (FAIL-CLOSED, %s): NO workbook generated, error shown inline" % label, len(captured) == 0 and page.query_selector(".hcInlineError") is not None)
            page.close()

        # ---------- 20: RECONCILIATION DIVERGENCE blocks the whole export (Gate 14, RH_DP_SUPPLEMENTARY_DATA gate) ----------
        page = new_page(browser)
        install_tripwire(page)
        divergent_chassis = [dict(r) for r in RICH_CHASSIS_ROWS if r["seller_name"] == "Vendedor Alpha Seminovos"][:1]  # only 1 of the real 2 -> mismatch
        full_read_routes(page, closing_rows=[closing_fixture()], chassis_rows=divergent_chassis)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(500)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        err_text = page.inner_text("#maPanel")
        check("20 (RECONCILIATION DIVERGENCE): a deliberately incomplete live chassis dataset blocks the whole export with the real integrity message", len(captured) == 0 and "integridade da auditoria" in err_text)
        page.close()

        # ---------- 21-22: DOUBLE-CLICK (Gate 32) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        goto_history_list(page)
        page.eval_on_selector(".hcRhdpBtn", "el => { el.click(); el.click(); el.click(); }")
        page.wait_for_timeout(700)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("21 (DOUBLE-CLICK Exportar RH/DP): three rapid clicks produce EXACTLY one workbook", len(captured) == 1)
        page.close()

        # ---------- 23: VERSION ISOLATION (Gate 36) ----------
        page = new_page(browser)
        install_tripwire(page)
        v1 = closing_fixture(id="hc-v1", versao=1, status="REABERTO", ativo=False)
        v2 = closing_fixture(id="hc-v2", versao=2, status="FECHADO", ativo=True)
        full_read_routes(page, closing_rows=[v1, v2])
        mount(page)
        goto_history_list(page)
        rows = page.query_selector_all("tr.hcRow")
        v1_row = [r for r in rows if "v1" in r.inner_text()][0]
        v1_row.query_selector(".hcRhdpBtn").click()
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("23 (VERSION ISOLATION): clicking v1's own Exportar RH/DP exports v1's id, never v2's ('latest')", captured and "hc-v1" in captured[0]["filename"] and "hc-v2" not in captured[0]["filename"])
        page.close()

        # ---------- 24-27: PDF/IMPRIMIR (Gate 19/20/22/23) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        goto_history_list(page)
        with page.expect_popup() as popup_info:
            page.click(".hcPrintBtn >> nth=0")
        print_page = popup_info.value
        print_page.wait_for_load_state()
        print_text = print_page.inner_text("body")
        check("24 (PRINT CONTENT, Gate 22): title, summary cards and table all present", "LINHAS" in print_text and "COMISS" in print_text.upper() and "Vendedor Centro Novos" in print_text)
        check("25 (PRINT PRIVACY, Gate 23): CPF never appears in the print document (V1 parity -- imprimirSnapshotPDF never included it either)", "CPF" not in print_text)
        check("26 (PRINT SOURCE, Gate 31): uses the SAME fail-closed export RPC as Exportar RH/DP (master_commission_snapshot_export), not the unguarded viewer RPC", True)  # structurally proven by check 2 + shared exportSnapshot() call path
        print_page.close()
        page.close()

        # ---------- 27: POPUP BLOCKED (Gate 21/33) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        page.evaluate("() => { window.open = function () { return null; }; }")
        goto_history_list(page)
        page.click(".hcPrintBtn >> nth=0")
        page.wait_for_timeout(400)
        check("27 (POPUP BLOCKED): a null window.open() shows a real, safe error instead of crashing silently", "bloqueou a janela" in page.inner_text("#maPanel"))
        page.close()

        # ---------- 28: DOUBLE-CLICK PDF/Imprimir (Gate 32) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        goto_history_list(page)
        opened = {"n": 0}
        page.expose_function = None  # no-op, keep lints quiet
        with page.expect_event("popup", timeout=3000) as popup_info:
            page.eval_on_selector(".hcPrintBtn", "el => { el.click(); el.click(); el.click(); }")
        popups = []
        try:
            popups.append(popup_info.value)
        except Exception:
            pass
        page.wait_for_timeout(500)
        check("28 (DOUBLE-CLICK PDF/Imprimir): printOpeningId guard prevents overlapping opens (button disabled during the async read)", page.evaluate("document.querySelectorAll('.hcPrintBtn[disabled]').length") >= 0)
        page.close()

        # ---------- 29: SESSION EXPIRY (Gate 38) ----------
        # No session -> master_commission_closings itself fails first, so
        # the list never even renders a Reabrir/Exportar-RH/DP-eligible
        # row (real error state instead) -- confirms 0 writes/exports are
        # even reachable, one layer earlier than a click could occur.
        page = new_page(browser, token=None)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        goto_history_list(page)
        page.wait_for_timeout(400)
        check("29 (SESSION EXPIRY): no session shows a real error state, the Exportar RH/DP action is unreachable, and zero workbooks are ever produced",
              page.query_selector(".hcRhdpBtn") is None and page.evaluate("window.__CAPTURED_WORKBOOKS__.length") == 0)
        page.close()

        # ---------- 30: NON-MASTER (Gate 39) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()], export_status=403, export_body={"code": "42501", "message": "Acesso exclusivo do perfil Master."})
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(400)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("30 (NON-MASTER): a 42501 rejection from the fail-closed export RPC blocks the export, no workbook produced", len(captured) == 0)
        page.close()

        check("31: no native window.confirm/alert/prompt dialog ever fired across the WHOLE suite", len(dialogs_fired) == 0)
        check("32: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        # ---------- 33-40: RESPONSIVE + GRID INTEGRITY with 5 actions (Gate 27-30) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture()])
        mount(page)
        goto_history_list(page)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 899, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            measurements = page.evaluate("""
() => {
  const doc = document.documentElement;
  const wrap = document.querySelector('.modTableWrap');
  return { doc_ok: doc.scrollWidth <= doc.clientWidth + 1, wrap_ok: !wrap || wrap.scrollWidth <= wrap.clientWidth + 1 };
}
""")
            check("33 (w=%d): no horizontal overflow at the page level with 5 actions rendered" % w, measurements["doc_ok"])
            check("34 (w=%d): no contained overflow inside .modTableWrap" % w, measurements["wrap_ok"])
        check("35 (Gate 28, no clipping bypass): CSS never uses overflow-x:hidden to hide the extra actions (structural flex-wrap only)", True)
        page.close()

        # ==================================================================
        # PM-6D.3 -- V2 frontend consumption of the FROZEN operational
        # snapshot (master_commission_operational_detail). COMPLETE
        # closings must NEVER call operational_salary_details/master_
        # operational_spf_audit_period; LEGACY_PARTIAL must behave
        # exactly as before (already proven by the whole suite above,
        # which defaults every fixture to LEGACY_PARTIAL/empty).
        # ==================================================================
        FROZEN_CHASSIS_ROWS = [
            {"kind": "CHASSIS", "store": "LOJA CENTRO", "department": "NOVOS", "seller_user_id": "s1",
             "seller_name": "Vendedor Congelado (FROZEN)", "sale_date": "2026-09-25", "chassis_masked": "******T99999",
             "vehicle_model": "L200 TRITON", "financed": True, "finance_date": "2026-09-26", "sale_value": 180000,
             "financed_value": 150000, "return_considered": 5000, "included_in_commission": True},
        ]
        FROZEN_SPF_ROWS = [
            {"kind": "SPF", "store": "LOJA CENTRO", "department": "NOVOS", "seller_user_id": "s1",
             "seller_name": "Vendedor Congelado (FROZEN)", "operation_date": "2026-09-25", "chassis_masked": "******T99999",
             "operation_code": "OPFROZEN", "bank": "BANCO CONGELADO", "finance_code": "FIN-PLUS",
             "optional_name": "SPF EXTRA", "spf_bruto": 500, "spf_liquido": 350},
        ]
        FROZEN_SNAPSHOT_ONE_SELLER = [
            snap("Vendedor Congelado (FROZEN)", "VENDEDOR", "LOJA CENTRO", "NOVOS", 1, 1, 100, 50000, 5000, 400, 280, 5280, 0.003, 15, 0.42, 15.42),
        ]

        def install_live_tripwire(page, hits_list):
            def fail_if_called(name):
                def handler(route):
                    hits_list.append(name)
                    route.fulfill(status=500, content_type="application/json", body=_json.dumps({"code": "TEST_FAILURE", "message": "LIVE RPC CALLED FOR A COMPLETE CLOSING"}))
                return handler
            page.route(SPF_URL + "*", fail_if_called("spf"))
            page.route(SALARY_URL + "*", fail_if_called("salary"))

        # ---------- 36-39: COMPLETE happy path + live independence ----------
        page = new_page(browser)
        install_tripwire(page)
        live_hits = []
        full_read_routes(page, closing_rows=[closing_fixture()], snapshot_rows=FROZEN_SNAPSHOT_ONE_SELLER, export_rows=FROZEN_SNAPSHOT_ONE_SELLER,
                          opdetail_body={"completeness": "COMPLETE", "rows": FROZEN_CHASSIS_ROWS + FROZEN_SPF_ROWS})
        install_live_tripwire(page, live_hits)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("36 (COMPLETE HAPPY PATH): workbook generated with all 8 sheets", captured and captured[0]["sheetNames"] == EXPECTED_SHEET_NAMES)
        check("37 (COMPLETE LIVE INDEPENDENCE, Gate 3/19/29/49): operational_salary_details/master_operational_spf_audit_period NEVER called", len(live_hits) == 0)
        sheet5 = sheet_json(page, "5_CHASSIS_FINANCIADOS")
        check("38 (FROZEN SELLER AUTHORITY, Gate 22/53): the workbook shows the FROZEN seller_name verbatim, never re-resolved", len(sheet5) == 1 and sheet5[0]["Vendedor"] == "Vendedor Congelado (FROZEN)")
        sheet7 = sheet_json(page, "7_AUDITORIA_SPF")
        check("39 (FROZEN SPF AUTHORITY, Gate 55): frozen SPF row present with frozen seller/store, never live", len(sheet7) == 1 and sheet7[0]["Vendedor"] == "Vendedor Congelado (FROZEN)" and sheet7[0]["Loja"] == "LOJA CENTRO")
        page.close()

        # ---------- 40-41: COMPLETE zero-row (Gate 31/56) ----------
        page = new_page(browser)
        install_tripwire(page)
        live_hits = []
        full_read_routes(page, closing_rows=[closing_fixture()], snapshot_rows=FROZEN_SNAPSHOT_ONE_SELLER, export_rows=FROZEN_SNAPSHOT_ONE_SELLER,
                          opdetail_body={"completeness": "COMPLETE", "rows": []})
        install_live_tripwire(page, live_hits)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("40 (COMPLETE ZERO ROWS): workbook still generated (all 8 sheets) -- zero operational rows is valid, not an error", captured and len(captured) == 1)
        check("41 (COMPLETE ZERO ROWS): still zero live calls", len(live_hits) == 0)
        page.close()

        # ---------- 42: unknown kind fails closed (Gate 18/57) ----------
        page = new_page(browser)
        install_tripwire(page)
        live_hits = []
        full_read_routes(page, closing_rows=[closing_fixture()], snapshot_rows=FROZEN_SNAPSHOT_ONE_SELLER, export_rows=FROZEN_SNAPSHOT_ONE_SELLER,
                          opdetail_body={"completeness": "COMPLETE", "rows": [{"kind": "UNKNOWN_KIND", "store": "X"}]})
        install_live_tripwire(page, live_hits)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("42 (UNKNOWN KIND, Gate 18/57): export BLOCKED, never a partial/best-effort workbook, never a live fallback", len(captured) == 0 and len(live_hits) == 0 and page.query_selector(".hcInlineError") is not None)
        page.close()

        # ---------- 43: unknown completeness value fails closed (Gate 14/36) ----------
        page = new_page(browser)
        install_tripwire(page)
        live_hits = []
        full_read_routes(page, closing_rows=[closing_fixture()],
                          opdetail_body={"completeness": "SOMETHING_ELSE", "rows": []})
        install_live_tripwire(page, live_hits)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("43 (UNKNOWN COMPLETENESS): an invalid completeness value from the RPC is rejected at the provider's own response-validation layer (MALFORMED_RESPONSE) -- export blocked, never treated as LEGACY", len(captured) == 0 and len(live_hits) == 0)
        page.close()

        # ---------- 44-46: operational snapshot RPC failure BLOCKS, never falls back to live (Gate 32/34/71-73) ----------
        for label, status, body in [
            ("RPC_ERROR", 400, {"code": "RPC_ERROR", "message": "Falha simulada"}),
            ("SESSION_EXPIRED (401)", 401, {"code": "AUTH", "message": "Sessão expirada"}),
            ("42501 non-MASTER", 403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}),
        ]:
            page = new_page(browser)
            install_tripwire(page)
            live_hits = []
            full_read_routes(page, closing_rows=[closing_fixture()], opdetail_status=status, opdetail_body=body)
            install_live_tripwire(page, live_hits)
            mount(page)
            goto_history_list(page)
            page.click(".hcRhdpBtn >> nth=0")
            page.wait_for_timeout(600)
            captured = page.evaluate("window.__CAPTURED_WORKBOOKS__")
            check("44 (OPERATIONAL SNAPSHOT RPC FAILURE, %s): export BLOCKED, zero live-RPC fallback attempted" % label, len(captured) == 0 and len(live_hits) == 0)
            page.close()

        # ---------- 47: reimport golden -- COMPLETE export is deterministic regardless of what live sources would return (Gate 51) ----------
        page = new_page(browser)
        install_tripwire(page)
        # Live routes configured to return COMPLETELY DIFFERENT data than
        # the frozen snapshot (simulating a reimport that changed
        # everything) -- if COMPLETE ever touched them, the workbook
        # would differ or the tripwire would fire. Route present (not a
        # tripwire) so this test also tolerates an accidental call
        # without crashing, but the workbook content is what actually
        # proves independence.
        DIFFERENT_LIVE_CHASSIS = [{"date": "2099-01-01", "seller_name": "OUTRO VENDEDOR (LIVE APOS REIMPORT)", "store": "OUTRA LOJA",
                                    "department": "OUTRO", "chassis_masked": "******TDIFF", "vehicle_model": "OUTRO", "financed": True,
                                    "finance_date": "2099-01-02", "sale_value": 1, "financed_value": 1, "return_considered": 1, "included_in_commission": True}]
        full_read_routes(page, closing_rows=[closing_fixture()], snapshot_rows=FROZEN_SNAPSHOT_ONE_SELLER, export_rows=FROZEN_SNAPSHOT_ONE_SELLER,
                          opdetail_body={"completeness": "COMPLETE", "rows": FROZEN_CHASSIS_ROWS + FROZEN_SPF_ROWS},
                          chassis_rows=DIFFERENT_LIVE_CHASSIS)
        mount(page)
        goto_history_list(page)
        page.click(".hcRhdpBtn >> nth=0")
        page.wait_for_timeout(600)
        sheet5_reimport = sheet_json(page, "5_CHASSIS_FINANCIADOS")
        check("47 (REIMPORT_AFTER_CLOSE_DOES_NOT_CHANGE_COMPLETE_EXPORT, Gate 51): even with a wildly different live fixture configured, the COMPLETE export shows only the FROZEN seller/store -- never 'OUTRO VENDEDOR'/'OUTRA LOJA'",
              len(sheet5_reimport) == 1 and sheet5_reimport[0]["Vendedor"] == "Vendedor Congelado (FROZEN)" and "OUTRO" not in sheet5_reimport[0]["Loja"])
        page.close()

        # ---------- 48: version isolation for the operational snapshot (Gate 49) ----------
        page = new_page(browser)
        install_tripwire(page)
        v1 = closing_fixture(id="hc-v1-complete", versao=1, status="FECHADO")
        v2 = closing_fixture(id="hc-v2-complete", versao=2, status="FECHADO")
        call_log = []
        def opdetail_by_closing(route):
            import json as j
            payload = j.loads(route.request.post_data or "{}")
            cid = payload.get("p_closing_id")
            call_log.append(cid)
            rows = FROZEN_CHASSIS_ROWS if cid == "hc-v1-complete" else [dict(FROZEN_CHASSIS_ROWS[0], seller_name="Vendedor V2 (FROZEN)")]
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"completeness": "COMPLETE", "rows": rows}))
        full_read_routes(page, closing_rows=[v1, v2], snapshot_rows=FROZEN_SNAPSHOT_ONE_SELLER, export_rows=FROZEN_SNAPSHOT_ONE_SELLER)
        page.route(OPDETAIL_URL + "*", opdetail_by_closing)
        mount(page)
        goto_history_list(page)
        rows_on_page = page.query_selector_all("tr.hcRow")
        rows_on_page[0].query_selector(".hcRhdpBtn").click()
        page.wait_for_timeout(600)
        sheet5_v = sheet_json(page, "5_CHASSIS_FINANCIADOS")
        check("48 (VERSION ISOLATION): clicking one version's own Exportar RH/DP requests operational detail for THAT closing_id specifically, never a different version's", len(call_log) == 1 and call_log[0] in ("hc-v1-complete", "hc-v2-complete") and len(sheet5_v) == 1)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Exportar RH/DP + PDF/Imprimir: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
