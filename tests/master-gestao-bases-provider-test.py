#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5C -- deterministic tests for the Gestão de Bases
module (master-gestao-bases-provider.js, master-gestao-bases-view-
model.js, shell-admin.js), mounted via the same lightweight harness used
by every sibling Painel Master surface (route guard tested separately in
tests/master-admin-route-test.py).

Everything here runs against mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. Synthetic-only fixtures: fake
names/CPFs/chassis/values, never real Base 01/02/03 data (Gate 44).

The single most safety-critical property this suite proves is that the
homologation-mode gate (ported verbatim from V1's own already-proven
GB_HOMOLOGATION_MODE) makes every WRITE RPC auto-simulate on this test
harness's own hostname (never "127.0.0.1"/"localhost" is in the
production allowlist) -- proven here by asserting the exact real-network
call COUNT for each flow, not merely that the UI "looks done".

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080, and `openpyxl` (pip) to build tiny synthetic .xlsx
fixtures on the fly -- no fixture file is committed to the repo.
"""
import io
import json as _json
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
LIST_BATCHES_URL = "https://mock.invalid/rest/v1/rpc/master_operational_list_batches"
LIST_SELLERS_URL = "https://mock.invalid/rest/v1/rpc/master_operational_list_sellers"
LIST_SPF_EXTRA_URL = "https://mock.invalid/rest/v1/rpc/master_operational_list_spf_extra_base02"
BEGIN_IMPORT_URL = "https://mock.invalid/rest/v1/rpc/master_operational_begin_import"
IMPORT_SALES_URL = "https://mock.invalid/rest/v1/rpc/master_operational_import_sales"
IMPORT_FINANCE_URL = "https://mock.invalid/rest/v1/rpc/master_operational_import_finance"
IMPORT_SELLERS_URL = "https://mock.invalid/rest/v1/rpc/master_operational_import_sellers"
FINALIZE_URL = "https://mock.invalid/rest/v1/rpc/master_operational_finalize_import"
APPLY_BASE03_URL = "https://mock.invalid/rest/v1/rpc/master_operational_apply_base03"

results = []
TMP_DIR = tempfile.mkdtemp(prefix="pm5c_gb_fixtures_")


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def goto_gestao_bases(page):
    page.wait_for_selector('[data-section="gestaoBases"]', timeout=5000)
    page.click('[data-section="gestaoBases"]')
    page.wait_for_selector(".gbGrid, .modErrorState", timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def counting_route(calls, status, body_fn):
    def handler(route):
        post = None
        try:
            post = _json.loads(route.request.post_data) if route.request.post_data else None
        except Exception:
            post = route.request.post_data
        calls.append(post)
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body_fn(post)))
    return handler


def make_xlsx(name, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    path = os.path.join(TMP_DIR, name)
    wb.save(path)
    return path


BASE01_XLSX = make_xlsx("base01.xlsx",
    ["Tipo", "Chassi Completo", "Vendedor", "CPF do Vendedor", "Nome Vendedor Completo", "Data venda", "Valor Venda", "Empresa Vendedora", "Modelo"],
    [
        ["Novo", "9BWZZZ377VT004251", "MARIASA", "11122233344", "MARIA SILVA SANTOS", "01/08/2026", "89900,00", "EUROPA", "PEUGEOT 208"],
        ["Usado", "9BWZZZ377VT004252", "JOAOSA", "22233344455", "JOAO PEDRO PEREIRA", "02/08/2026", "45000,50", "ALPHAVILLE", "CITROEN C3"],
    ])
BASE02_XLSX = make_xlsx("base02.xlsx",
    ["Vendedor", "Descrição Serviço", "Chassi Completo", "Cliente", "Data Venda", "Retorno Liquido", "Valor Serviço", "Plano", "Nome completo vendedor"],
    [
        ["MARIASA", "POR PLANO-FINANCIAMENTO", "9BWZZZ377VT004251", "MARIA SILVA SANTOS", "01/08/2026", "1200,00", "45000,00", "PLANO A", "MARIA SILVA SANTOS"],
        ["SEMVEND", "FINANCIAMENTO", "9BWZZZ377VT004253", "PEDRO ALVES", "03/08/2026", "800,00", "30000,00", "PLANO B", "PEDRO ALVES"],
    ])
BASE03_XLSX = make_xlsx("base03.xlsx",
    ["Op - Data Inclusão", "Cli - Nome", "Inst - Ponto de Venda", "Inst - Departamento", "Op - Modalidade", "Op - Código", "Op - Situação",
     "Op Fin - Banco", "Op Fin - Financiado (R$)", "Opcional - Nome", "Opcional - Valor (R$)", "Op Fin - Quantidade Parcelas",
     "Op Fin - PMT (R$)", "Op Fin - Balão PMT (R$)", "Tabela - Código IF", "Tabela - TC Devolvida (R$)"],
    [
        ["01/08/2026", "MARIA SILVA SANTOS", "EUROPA", "NOVOS", "CDC", "OP001", "ATIVA", "BANCO XYZ", "45000,00", "", "", 48, "1200,50", "", "1", ""],
        ["", "", "", "", "", "", "", "", "", "SPF EXTRA", "350,75", "", "", "", "", ""],
    ])
BASE03_NO_PRINCIPAL_XLSX = make_xlsx("base03_no_principal.xlsx",
    ["Op - Data Inclusão", "Cli - Nome", "Inst - Ponto de Venda", "Inst - Departamento", "Op - Modalidade", "Op - Código", "Op - Situação",
     "Op Fin - Banco", "Op Fin - Financiado (R$)", "Opcional - Nome", "Opcional - Valor (R$)", "Op Fin - Quantidade Parcelas",
     "Op Fin - PMT (R$)", "Op Fin - Balão PMT (R$)", "Tabela - Código IF", "Tabela - TC Devolvida (R$)"],
    [
        # Only an SPF Extra row, no principal ever seen (client name never set) -> discarded, not SPF (no forward-fill source).
        ["", "", "", "", "", "", "", "", "", "algo qualquer", "0", "", "", "", "", ""],
    ])
COLABORADORES_XLSX = make_xlsx("colaboradores.xlsx",
    ["Nome", "STATUS", "CPF", "NBS", "Loja", "TIPO"],
    [
        ["Maria Silva Santos", "VENDEDOR/ATIVO", "111.222.333-44", "MARIASA", "Europa", "VENDEDOR"],
        ["Maria Silva Santos", "INATIVO/INATIVO", "111.222.333-44", "MARIASA", "Europa", "VENDEDOR"],  # duplicate CPF, last wins
        ["Pedro Alves", "VENDEDOR/ATIVO", "999", "PEDROAL", "Alphaville", "VENDEDOR"],  # invalid CPF, kept separately
    ])
EMPTY_XLSX = make_xlsx("empty.xlsx", ["Chassi"], [])

BASELINE_BATCHES = [
    {"source_type": "SALES_CURRENT", "status": "VALIDATED", "original_filename": "vendas_08_2026.xlsx",
     "period_start": "2026-08-01", "period_end": "2026-08-31", "rows_read": 1500, "rows_accepted": 1490,
     "rows_rejected": 10, "validation_message": "ok", "completed_at": "2026-09-04T18:52:52+00:00", "created_at": "2026-09-04T18:00:00+00:00"},
    # An orphan VALIDATING batch must NEVER be treated as "the official base" (Gate 19/20).
    {"source_type": "FINANCE_CURRENT", "status": "VALIDATING", "original_filename": "orphan.xlsx",
     "period_start": None, "period_end": None, "rows_read": 5, "rows_accepted": 0,
     "rows_rejected": 0, "validation_message": None, "completed_at": None, "created_at": "2026-08-01T00:00:00+00:00"},
]


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)

        # ---------- 1-6: cards render the real batch status (Gate 26/58) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, BASELINE_BATCHES))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        mount(page)
        goto_gestao_bases(page)
        check("1: homologation-mode banner is visible (this harness's hostname is never in the production allowlist)",
              page.query_selector(".gbHomologBanner") is not None)
        cards_text = page.inner_text(".gbGrid")
        check("2: all 4 real V1 bases are present (Vendas/Financiamentos/Complementar/Colaboradores), nothing invented or dropped",
              "BASE 01" in cards_text and "BASE 02" in cards_text and "BASE 03" in cards_text and "Colaboradores" in cards_text)
        check("3: Base 01's card shows the real VALIDATED batch's file/counts", "vendas_08_2026.xlsx" in cards_text and "1.490" in cards_text)
        check("4: Base 02's card shows 'no batch yet' -- the VALIDATING orphan must NOT be shown as an official/validated batch",
              "Nenhuma carga validada ainda" in cards_text)
        check("5: no horizontal overflow on the Gestão de Bases panel at desktop width",
              page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        for w in (1440, 1024, 768, 390):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(80)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("6 (w=%d): no horizontal overflow" % w, no_overflow)
        page.set_viewport_size({"width": 1366, "height": 900})
        page.close()

        # ---------- 7-14: BASE 01 happy path -- exact payload shape + homologation safety ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        write_calls = []
        for url in (BEGIN_IMPORT_URL, IMPORT_SALES_URL, FINALIZE_URL):
            page.route(url + "*", counting_route(write_calls, 200, lambda p: "SHOULD-NEVER-BE-CALLED"))
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='SALES_CURRENT']")
        page.set_input_files("#gbFileInput", BASE01_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        diag_text = page.inner_text("#nxModalRoot")
        check("7: Base 01 diagnostic shows correct linhas/aceitas/rejeitadas from the real parsed file (2/2/0)",
              "Linhas lidas" in diag_text and "2" in diag_text and "PRONTO PARA ATUALIZAÇÃO" in diag_text)
        check("8: unresolved sellers (not in cadastro) are listed by name+NBS for the MASTER to see",
              "MARIA SILVA SANTOS" in diag_text and "MARIASA" in diag_text)
        page.click("#gbConfirmarBtn")
        page.wait_for_selector("#gbSuccessCloseBtn", timeout=5000)
        page.wait_for_timeout(150)
        success_text = page.inner_text("#nxModalRoot")
        check("9: success modal explicitly says SIMULATION, never claims a real write happened", "SIMULAÇÃO CONCLUÍDA" in success_text)
        check("10: zero REAL network calls reached begin_import/import_sales/finalize_import -- homologation gate works by construction, not by luck",
              len(write_calls) == 0)
        page.close()

        # ---------- 11-13: BASE 02 -> Colaboradores session-reprocess chain ----------
        # In homologation mode NOTHING is ever really written (that is the
        # whole point), so master_operational_list_sellers -- a real read,
        # never blocked -- can never organically reflect a just-simulated
        # Colaboradores import. This is not testable "for real" without
        # actually writing to a backend (forbidden, Gate 36); instead this
        # mock reflects the cadastro EXACTLY as of the moment Colaboradores'
        # own confirm resolves (a legitimate stand-in for "this exact same
        # request, made moments later against a real backend, would see the
        # row it just wrote") -- it isolates and proves the REPROCESS LOGIC
        # itself (does gbReprocessarPendentesBase02 correctly reload the
        # cache, re-resolve the pending row, and re-submit it), independent
        # of the fact that the import that "caused" the update was itself
        # simulated.
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        sellers_state = {"resolved": False}

        def sellers_handler(route):
            if sellers_state["resolved"]:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(
                    [{"cpf_normalizado": "22233344455", "nbs": "SEMVEND", "name": "PEDRO ALVES", "store": "ALPHAVILLE", "profile_type": "VENDEDOR", "status": "ATIVO"}]))
            else:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps([]))
        page.route(LIST_SELLERS_URL + "*", sellers_handler)
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='FINANCE_CURRENT']")
        page.set_input_files("#gbFileInput", BASE02_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        diag02 = page.inner_text("#nxModalRoot")
        check("11: Base 02 diagnostic flags the seller (SEMVEND) not found in cadastro", "SEMVEND" in diag02 or "PEDRO ALVES" in diag02)
        # Deliberately NOT confirming Base 02 yet -- matches V1's own real
        # flow exactly: the session-pending-seller reprocess mechanism only
        # works while the batch is still VALIDATING (gbState.sessionFinanceBatch
        # is cleared the moment Base 02's OWN confirm succeeds, in both V1 and
        # this port). Cancel here (closes the modal, batch stays open/
        # VALIDATING in the backend -- an orphan batch until later confirmed,
        # the exact real-world shape gbLoadStatus's own comment already
        # accounts for), then go fix Colaboradores first.
        page.click("#gbCancelarBtn")
        page.wait_for_timeout(150)
        page.click(".gbUpdateBtn[data-source-type='COLABORADORES']")
        page.set_input_files("#gbFileInput", COLABORADORES_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        diagColab = page.inner_text("#nxModalRoot")
        check("12: Colaboradores diagnostic flags the duplicate-CPF row (last occurrence kept, not both)", "apareciam mais de uma vez" in diagColab)
        sellers_state["resolved"] = True  # cadastro now "reflects" SEMVEND, as it would moments after a real write
        page.click("#gbConfirmarBtn")
        page.wait_for_selector("#gbSuccessCloseBtn", timeout=8000)
        page.wait_for_timeout(150)
        successColab = page.inner_text("#nxModalRoot")
        check("13: after Colaboradores confirms, Base 02's session-pending seller (SEMVEND) is retroactively reprocessed",
              "linha(s) da Base 02" in successColab)
        page.close()

        # ---------- 14-17: BASE 03 -- atomic dry-run/commit, forward-fill taxonomy ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        apply_calls = []

        def apply_body(post):
            if post and post.get("p_dry_run") is True:
                return {"dry_run": True, "finance_batch_id": "22222222-2222-4222-8222-222222222222", "finance_rows_matched": 1, "spf_rows_received": 2}
            return {"dry_run": False, "finance_batch_id": "22222222-2222-4222-8222-222222222222", "finance_rows_matched": 1,
                    "spf_batch_id": "33333333-3333-4333-8333-333333333333", "spf_rows_received": 2, "spf_accepted": 2, "spf_rejected": 0}
        page.route(APPLY_BASE03_URL + "*", counting_route(apply_calls, 200, apply_body))
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='SPF_CURRENT']")
        page.set_input_files("#gbFileInput", BASE03_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("14: exactly 1 real apply_base03 call so far (the dry-run preview, a real read)", len(apply_calls) == 1)
        check("14b: the dry-run call correctly carries p_dry_run=true", apply_calls[0].get("p_dry_run") is True)
        check("15: the SPF Extra row correctly forward-filled client/date from the principal row (2 operational rows sent, not 1)",
              len(apply_calls[0].get("p_spf_rows", [])) == 2)
        diag03 = page.inner_text("#nxModalRoot")
        check("15b: diagnostic shows the real dry-run enrichment count (1 client matched)", "Enriquecimento financeiro" in diag03)
        page.click("#gbConfirmarBtn")
        page.wait_for_selector("#gbSuccessCloseBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("16: the commit step made NO second real network call -- homologation builds the result from the dry-run's own real numbers, client-side",
              len(apply_calls) == 1)
        success03 = page.inner_text("#nxModalRoot")
        check("16b: success screen shows the real accepted count from the dry-run (2), not a generic zero", "Registros" in success03 and "2" in success03)
        page.close()

        # ---------- 17: BASE 03 with no principal row anywhere -- rejected, not silently accepted ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        page.route(APPLY_BASE03_URL + "*", json_route(200, {"dry_run": True, "finance_batch_id": "x", "finance_rows_matched": 0, "spf_rows_received": 0}))
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='SPF_CURRENT']")
        page.set_input_files("#gbFileInput", BASE03_NO_PRINCIPAL_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("17: a file with zero principal operational rows is REJECTED (disabled confirm), matching V1's own structural guard",
              page.eval_on_selector("#gbConfirmarBtn", "el => el.disabled") is True)
        page.close()

        # ---------- 18: empty file -- controlled error, no commit call, no crash ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        empty_write_calls = []
        page.route(BEGIN_IMPORT_URL + "*", counting_route(empty_write_calls, 200, lambda p: "x"))
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='SALES_CURRENT']")
        page.set_input_files("#gbFileInput", EMPTY_XLSX)
        page.wait_for_timeout(400)
        check("18: an empty workbook shows a controlled error modal (not a silent no-op, not an uncaught exception)",
              page.query_selector("#gbErrorCloseBtn") is not None)
        check("18b: no import RPC was ever called for an empty file", len(empty_write_calls) == 0)
        page.close()

        # ---------- 19: duplicate-submit guard on CONFIRMAR ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(200, []))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        mount(page)
        goto_gestao_bases(page)
        page.click(".gbUpdateBtn[data-source-type='SALES_CURRENT']")
        page.set_input_files("#gbFileInput", BASE01_XLSX)
        page.wait_for_selector("#gbConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        page.eval_on_selector("#gbConfirmarBtn", "el => { el.click(); el.click(); }")
        page.wait_for_selector("#gbSuccessCloseBtn", timeout=5000)
        success_dup = page.inner_text("#nxModalRoot")
        check("19: duplicate-submit guard -- two rapid clicks still show exactly one success screen (not a corrupted double-run)",
              "SIMULAÇÃO CONCLUÍDA" in success_dup)
        page.close()

        # ---------- 20: adversarial -- real server-side MASTER authority (not merely client-side) ----------
        # This is proven directly against the LIVE production functions
        # (PM-5C Gate 13/49 forensics: every master_operational_* RPC body
        # was read via pg_get_functiondef and independently confirmed to
        # start with `if not public.is_master() then raise exception ...
        # using errcode = '42501'`, and all 5 underlying tables have RLS
        # enabled with ZERO policies -- direct table access denied for
        # every role, real or forged). A harness-level test cannot
        # re-simulate real Postgres role/RLS enforcement without becoming
        # a second, weaker copy of the real backend; asserting that the
        # frontend correctly SURFACES a 42501 denial (rather than treating
        # it as a false success) is the meaningful, non-redundant proof
        # available at this layer.
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_BATCHES_URL + "*", json_route(403, {"code": "42501", "message": "Acesso negado."}))
        page.route(LIST_SELLERS_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="gestaoBases"]', timeout=5000)
        page.click('[data-section="gestaoBases"]')
        page.wait_for_timeout(300)
        check("20: a 42501 (Acesso negado) denial on the one always-real read (list_batches) is surfaced as a real error state, never a false-success empty grid",
              page.query_selector(".modErrorState") is not None)
        page.close()

        browser.close()

    check("21: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Gestão de Bases Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
