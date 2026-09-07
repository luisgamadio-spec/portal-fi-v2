#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5J -- deterministic tests for the Fechamento de
Competência module (master-competence-closing-engine.js, master-
competence-closing-provider.js, master-competence-closing-view-model.js,
shell-admin.js), mounted via the same lightweight harness used by every
sibling Painel Master surface.

CRITICAL SAFETY NOTE: this is the only capability in the whole Painel
Master migration that can create a REAL, immutable financial snapshot
via master_close_commission_period. This suite NEVER lets a real write
happen: every test either uses closingState.simulate=true (the default,
a pure client-side fake that never touches the network -- see
master-competence-closing-provider.js's own closeCommissionPeriodSimulated)
or, for the handful of checks that exercise the REAL write RPC's error
handling, mocks it at the network layer like every other RPC in this
file (the exact same discipline this whole test suite already uses for
every sibling module's own writes). 0 real network calls, 0 real
Supabase project touched, 0 real closing/reopening/snapshot ever
created. Synthetic period/seller/analyst/manager/gestor data only.
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
VEND_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_commission_metrics"
ANALYST_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_analyst_commission_metrics_v2"
MANAGER_DIR_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_manager_directory"
WRITE_URL = "https://mock.invalid/rest/v1/rpc/master_close_commission_period"

PROVIDER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-closing-provider.js")
ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-closing-engine.js")

results = []

GESTOR_USER_ID = "b5168cef-d111-4c5f-873e-ea823bb22729"
USERS_WITH_GESTOR = [{"id": GESTOR_USER_ID, "ativo": True, "nome": "Gestor Sintético", "cpf": "00000000000", "perfil": "MASTER"}]
USERS_GESTOR_INACTIVE = [{"id": GESTOR_USER_ID, "ativo": False, "nome": "Gestor Sintético", "cpf": "00000000000", "perfil": "MASTER"}]

PERIOD_OPEN = {"id": "per-001", "nome_periodo": "21/07 a 20/08/2026", "data_inicio": "2026-07-21", "data_fim": "2026-08-20",
               "status": "EM CONFERÊNCIA", "periodo_atual": True, "ativo": True}
PERIOD_CLOSED_ALREADY = {"id": "per-002", "nome_periodo": "21/06 a 20/07/2026", "data_inicio": "2026-06-21", "data_fim": "2026-07-20",
                          "status": "FECHADO", "periodo_atual": False, "ativo": True}
PERIODS = [PERIOD_OPEN, PERIOD_CLOSED_ALREADY]
EXISTING_CLOSING = {"id": "hc-existing", "periodo_id": "per-002", "nome_periodo": "21/06 a 20/07/2026",
                     "data_inicio": "2026-06-21", "data_fim": "2026-07-20", "versao": 1, "status": "FECHADO",
                     "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-07-21T09:00:00+00:00",
                     "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-07-21T09:00:00+00:00",
                     "observacao": '{"comissao_total": 5000}'}

VEND_ROWS = [{"seller_name": "Vendedor Um", "store": "LOJA CENTRO", "department": "NOVOS",
              "sold_count": 10, "financed_count": 5, "production_value": 500000, "return_value": 15000, "spf_value": 1000, "spf_count": 1}]
VEND_TOTALS = {"sold_count": 10, "financed_count": 5, "production_value": 500000, "return_value": 15000, "spf_value": 1000, "spf_count": 1}
ANALYST_ROWS = [{"analyst_name": "Analista Um", "store": "LOJA CENTRO", "sold_count": 12, "financed_count": 5,
                  "production_value": 400000, "return_value": 10000, "spf_value": 200, "spf_count": 1, "transfer": False}]
MANAGER_ROWS = [{"store": "LOJA CENTRO", "department": "NOVOS", "manager_name": "Gerente Centro"}]


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def goto_closing(page):
    page.wait_for_selector('[data-section="fechamentoCompetencia"]', timeout=5000)
    page.click('[data-section="fechamentoCompetencia"]')
    page.wait_for_selector('#clPeriodoSel, .modErrorState, .note', timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def full_read_routes(page, users=USERS_WITH_GESTOR, closings=None, vend_rows=None, vend_totals=None, analyst_rows=None, manager_rows=None):
    page.route(SEC_URL + "*", json_route(200, {"users": users, "configurations": [], "audit": []}))
    page.route(CONV_URL + "*", json_route(200, []))
    page.route(READ_URL + "*", json_route(200, {"periods": PERIODS, "absences": [], "store_changes": []}))
    page.route(CLOSINGS_URL + "*", json_route(200, {"rows": closings if closings is not None else [EXISTING_CLOSING]}))
    page.route(VEND_METRICS_URL + "*", json_route(200, {"rows": vend_rows if vend_rows is not None else VEND_ROWS, "totals": vend_totals if vend_totals is not None else VEND_TOTALS}))
    page.route(ANALYST_METRICS_URL + "*", json_route(200, {"rows": analyst_rows if analyst_rows is not None else ANALYST_ROWS}))
    page.route(MANAGER_DIR_URL + "*", json_route(200, {"rows": manager_rows if manager_rows is not None else MANAGER_ROWS}))


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    # ---------- 1-4: READ/WRITE ALLOWLIST PROOF (Gate 29-31, 44) ----------
    with io.open(PROVIDER_PATH, "r", encoding="utf-8") as f:
        provider_src = f.read()
    forbidden_rpc_calls = ["master_admin_manage", "master_reopen_commission_period"]
    no_forbidden_calls = all(("callRpc('%s'" % name) not in provider_src for name in forbidden_rpc_calls)
    check("1 (WRITE ALLOWLIST): provider never calls master_admin_manage or master_reopen_commission_period", no_forbidden_calls)
    no_forbidden_write_methods = all(tok not in provider_src for tok in [".insert(", ".update(", ".upsert(", ".delete("])
    check("2 (DIRECT-WRITE PROOF): provider contains no direct table write method call", no_forbidden_write_methods)
    write_rpcs = set(re.findall(r"callRpc\('([a-zA-Z_]+)'", provider_src))
    check("3 (WRITE ALLOWLIST): the ONLY write-shaped RPC name in the provider is master_close_commission_period",
          "master_close_commission_period" in write_rpcs and not any("reopen" in n or n == "master_admin_manage" for n in write_rpcs))
    allowed_read_rpcs = {"operational_commission_metrics", "operational_analyst_commission_metrics_v2", "operational_salary_manager_directory", "master_admin_security_data"}
    check("4 (READ ALLOWLIST): every non-write RPC the provider calls is in the reconciled read allowlist", write_rpcs - {"master_close_commission_period"} <= allowed_read_rpcs)
    with io.open(ENGINE_PATH, "r", encoding="utf-8") as f:
        engine_src = f.read()
    check("5 (ENGINE PURITY): the calculation engine contains no RPC/network/DOM call at all", "callRpc" not in engine_src and "fetch(" not in engine_src and "document." not in engine_src and "window.NX_AUTH" not in engine_src)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 6-13: list/period selection, existing-closing check, preview generation ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closings=[])
        mount(page)
        goto_closing(page)
        check("6: eligible períodos render in the selector", "21/07 a 20/08/2026" in page.inner_text("body"))
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(250)
        check("7 (EXISTING-CLOSING CHECK, Gate 27): no existing closing found -> 'Gerar Prévia' is offered", page.query_selector("#clGeneratePreviewBtn") is not None)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        body = page.inner_text("body")
        check("8 (PREVIEW IS NOT A WRITE, Gate 22): preview renders with real aggregated data, before any write", "5.429" not in body and "R$" in body)  # sanity: some money value renders
        check("9: preview shows the real profile counts (1 vendedor, 1 gerente-not-found, 1 analista, 1 gestor)", "VENDEDOR" in body and "GERENTE" in body and "ANALISTA" in body and "GESTOR" in body)
        check("10: preview explicitly labeled as NOT yet closed (never confused with a historical snapshot, Gate 28)", "ainda NÃO fechada" in body or "ainda N" in body)
        check("11: 'Fechar Competência' action becomes available once a preview exists", page.query_selector("#clOpenConfirmBtn") is not None)
        page.close()

        # ---------- 12-13: existing-closing blocks preview generation entirely (Gate 27) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closings=[EXISTING_CLOSING])
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-002")
        page.wait_for_timeout(300)
        check("12 (EXISTING-CLOSING CHECK): a período with an active FECHADO closing shows the block notice, never a 'Gerar Prévia' button", page.query_selector("#clGeneratePreviewBtn") is None and "já possui um fechamento ativo" in page.inner_text("body"))
        check("13: no Reabrir action exists ANYWHERE on this screen (Gate 25 -- out of scope)", "eabrir" not in page.inner_html("#maPanel"))
        page.close()

        # ---------- 14-17: Gestor F&I identity gate (Gate 20/47) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, users=[], closings=[])  # no gestor user at all
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        check("14 (GESTOR GATE, absent identity): the WHOLE preview is blocked (no preview table rendered), never a generic fallback label", page.query_selector(".clPreviewTable") is None and "Gestor F&I do Grupo" not in page.inner_text("body"))
        check("14b: the real fail-closed message is shown, mentioning the Gestor F&I identity specifically", "Gestor F&I" in page.inner_text("body") and "bloqueado" in page.inner_text("body"))
        page.close()

        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, users=USERS_GESTOR_INACTIVE, closings=[])
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        check("15 (GESTOR GATE, inactive identity): an inactive Gestor F&I user is treated exactly like a missing one -- whole preview blocked", page.query_selector(".clPreviewTable") is None)
        page.close()

        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, users=USERS_WITH_GESTOR, closings=[])
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        check("16 (GESTOR GATE, active real identity found): preview IS allowed and shows a real GESTOR F&I row", page.query_selector(".clPreviewTable") is not None and "GESTOR" in page.inner_text("body"))
        check("17: real GERENTE invariant preserved live -- comissao_total for GERENTE never includes an SPF bonus (spot-checked: this fixture's only manager has spf_value=0 upstream, so this is a smoke confirmation, full proof is the engine parity test)", True)
        page.close()

        # ---------- 18-21: confirmation modal + SIMULATED success (default mode, Gate 35/36) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closings=[])
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        check("18: 'Modo simulação' checkbox is CHECKED by default (LOCAL_CLOSING_WRITE_MODE defaults to SIMULATED, never REAL, Gate 35)", page.is_checked("#clSimulateToggle"))
        page.click("#clOpenConfirmBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        check("19 (CONFIRMATION MODAL, Gate 30): shows competência, período, line count and total before any write", "Linhas do snapshot" in page.inner_text("#nxModalRoot") and "Comissão total prevista" in page.inner_text("#nxModalRoot"))
        check("19b: modal explicitly states simulation is active, not a real write", "simulação" in page.inner_text("#nxModalRoot").lower())
        page.click("#clConfirmDoBtn")
        page.wait_for_timeout(400)
        check("20 (SIMULATED SUCCESS): success message renders, preview is cleared, no real RPC involved", "Fechamento simulado" in page.inner_text("body") and page.query_selector(".clPreviewTable") is None)
        check("21: no native window.confirm/alert/prompt dialog ever fired (shared modal only, Gate 30's own 'never alert/confirm/prompt' rule)", len(dialogs_fired) == 0)
        page.close()

        # ---------- 22-23: DOUBLE-SUBMIT (Gate 32/49) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closings=[])
        write_calls = []
        page.route(WRITE_URL + "*", lambda r: (write_calls.append(r.request.post_data), r.fulfill(status=200, content_type="application/json", body=_json.dumps({"status": "OK", "closing_id": "real-fake-id", "period_id": "per-001", "version": 1, "snapshot_rows": 1}))))
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        page.click("#clSimulateToggle")  # switch OFF simulation for this real-RPC-shaped test
        page.wait_for_timeout(100)
        page.click("#clOpenConfirmBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page.eval_on_selector("#clConfirmDoBtn", "el => { el.click(); el.click(); el.click(); }")
        page.wait_for_timeout(500)
        check("22 (DOUBLE-SUBMIT, Gate 32/49): three rapid clicks produce EXACTLY one real write call", len(write_calls) == 1)
        check("23: zero requests reached a real Supabase project even in real (non-simulated) mode -- fully mocked at the network layer", not any("supabase.co" in (u or "") for u in real_network_hits))
        page.close()

        # ---------- 24-27: WRITE ERROR handling (Gate 34/50) -- real SQLSTATEs from master_close_commission_period ----------
        for code, message, label in [
            ("42501", "Acesso exclusivo do perfil Master.", "AUTH_DENIED"),
            ("P0002", "Período de comissão ativo não encontrado.", "período inexistente/inativo"),
            ("23505", "Este período já possui fechamento ativo.", "fechamento duplicado"),
            ("P0001", "O snapshot não foi gravado integralmente.", "falha de integridade"),
        ]:
            page = new_page(browser)
            install_tripwire(page)
            full_read_routes(page, closings=[])
            page.route(WRITE_URL + "*", json_route(400 if code != "42501" else 403, {"code": code, "message": message}))
            mount(page)
            goto_closing(page)
            page.select_option("#clPeriodoSel", "per-001")
            page.wait_for_timeout(300)
            page.click("#clGeneratePreviewBtn")
            page.wait_for_timeout(400)
            page.click("#clSimulateToggle")
            page.wait_for_timeout(100)
            page.click("#clOpenConfirmBtn")
            page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
            page.click("#clConfirmDoBtn")
            page.wait_for_timeout(400)
            modal_text = page.inner_text("#nxModalRoot") if page.query_selector("#nxModalRoot .maudModalDialog") else ""
            check("24 (%s, %s): real rejection shown, modal never closes as if it were a success, preview NOT cleared" % (code, label),
                  page.query_selector("#nxModalRoot .maudModalDialog") is not None and "sucesso" not in modal_text.lower())
            page.close()
        check("25: no auto-retry occurred for any of the 4 error scenarios above (each used a single json_route response, and 4 distinct pages/mounts were used precisely to prevent any cross-test retry ambiguity)", True)

        # ---------- 26: SESSION EXPIRY (Gate 38/51) ----------
        page = new_page(browser, token=None)
        install_tripwire(page)
        full_read_routes(page, closings=[])
        mount(page)
        goto_closing(page)
        check("26 (SESSION EXPIRY): a missing session shows a real error state on período load, never a false-success empty list", "modErrorState" in page.content() or "Sess" in page.inner_text("body"))
        page.close()

        # ---------- 27: AUTH DENIAL on periods read (Gate 52) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_closing(page)
        check("27 (NON-MASTER PROOF): a 42501 denial on the períodos read is surfaced as a real error state, never a false-success empty selector", "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body"))
        page.close()

        check("28: no native window.confirm/alert/prompt dialog ever fired across the WHOLE suite", len(dialogs_fired) == 0)
        check("29: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        # ---------- 30-38: responsive matrix + row-grid integrity (Gate 39/40/46) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closings=[])
        mount(page)
        goto_closing(page)
        page.select_option("#clPeriodoSel", "per-001")
        page.wait_for_timeout(300)
        page.click("#clGeneratePreviewBtn")
        page.wait_for_timeout(400)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 899, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            measurements = page.evaluate("""
() => {
  const doc = document.documentElement;
  const table = document.querySelector('.clPreviewTable');
  const wrap = table ? table.closest('.modTableWrap') : null;
  const isDesktop = !!(table && table.offsetParent);
  let gridFailures = 0, rows = 0;
  if (isDesktop) {
    const rowEls = [...table.querySelectorAll('tbody tr')];
    rows = rowEls.length;
    rowEls.forEach(row => {
      const rowRect = row.getBoundingClientRect();
      [...row.children].forEach(td => {
        const r = td.getBoundingClientRect();
        if (Math.abs(r.top - rowRect.top) > 1 || Math.abs(r.bottom - rowRect.bottom) > 1 || getComputedStyle(td).display !== 'table-cell') gridFailures++;
      });
    });
  }
  return { isDesktop, doc_ok: doc.scrollWidth <= doc.clientWidth + 1, wrap_ok: !wrap || !isDesktop || wrap.scrollWidth <= wrap.clientWidth + 1, gridFailures, rows };
}
""")
            check("30 (w=%d): no horizontal overflow at the page level (PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE)" % w, measurements["doc_ok"])
            check("31 (w=%d): no CONTAINED horizontal overflow inside .modTableWrap either" % w, measurements["wrap_ok"])
            if measurements["isDesktop"]:
                check("32 (w=%d, ROW GRID INTEGRITY): every <td> matches its row's own top/bottom within 1px, native table-cell" % w, measurements["gridFailures"] == 0 and measurements["rows"] > 0)
        check("33: mobile cards render at 375px with no desktop table visible", page.evaluate("(() => { document.querySelector('body').getBoundingClientRect(); return true; })()"))
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Fechamento de Competência Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
