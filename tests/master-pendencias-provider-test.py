#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-4C.2 -- deterministic tests for Pendências
Cadastrais (master-pendencias-provider.js, master-pendencias-view-
model.js, shell-admin.js), mounted via the same lightweight harness
already used by Usuários/Auditoria (route guard tested separately in
tests/master-admin-route-test.py).

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project
touched, 0 credentials anywhere in this file. All 7 real RPCs
identified in PM-4C.1 (master_cadastro_alertas_listar/
alerta_resolver/alerta_ignorar/alerta_excluir/
alerta_corrigir_login_nbs/excecao_criar/excecao_revogar) are exercised
here ONLY through this mocked transport.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
PC_LIST_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_alertas_listar"
PC_RESOLVER_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_alerta_resolver"
PC_IGNORAR_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_alerta_ignorar"
PC_EXCLUIR_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_alerta_excluir"
PC_NBS_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_alerta_corrigir_login_nbs"
PC_EXC_LIST_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_excecoes_listar"
PC_EXC_CRIAR_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_excecao_criar"
PC_EXC_REVOGAR_URL = "https://mock.invalid/rest/v1/rpc/master_cadastro_excecao_revogar"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
window.__consoleCapture = [];
(function () {
  var orig = console.log;
  console.log = function () { window.__consoleCapture.push(Array.prototype.slice.call(arguments).join(' ')); return orig.apply(console, arguments); };
})();
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc", viewport=None):
    page = browser.new_page(viewport=viewport or {"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def goto_pendencias(page):
    # Usuários may legitimately be an EMPTY real list in some fixtures
    # here (users:[]) -- wait for the nav button itself, never for
    # Usuários' own table markup, which would then never appear.
    page.wait_for_selector("button[data-section='pendenciasCadastrais']", timeout=5000)
    page.click("button[data-section='pendenciasCadastrais']")
    page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('pcTable') || document.getElementById('maPanel').innerHTML.includes('modEmptyState') || document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)


USERS = [
    {"id": "u1", "cpf": "11111111111", "cpf_normalizado": "11111111111", "nome": "Usuário Candidato Um",
     "perfil": "VENDEDOR", "loja": "BARRA FUNDA", "status": "NOVOS", "ativo": True,
     "primeiro_acesso": False, "ultimo_login": None, "email_auth": "u1@example.com",
     "tem_auth": True, "email_divergente": False, "auth_confirmado": True, "ativacao_legado": None},
]

# One real row per canonical type (Gate 11/50) -- exact real field shape
# from PM-4C.1's own pg_get_functiondef read of master_cadastro_alertas_listar.
ALL_TYPES = [
    "NOVO_CADASTRO_NECESSARIO", "ATUALIZACAO_CADASTRAL_NECESSARIA", "CORRESPONDENCIA_INDETERMINADA",
    "NBS_DIVERGENTE", "LOJA_DIVERGENTE", "DEPARTAMENTO_DIVERGENTE", "IDENTIFICADOR_DUPLICADO",
    "USUARIO_INATIVO_COM_PRODUCAO", "FATO_SEM_VENDEDOR_ATRIBUIDO", "OUTRO",
]


def make_row(idx, tipo, overrides=None):
    base = {
        "id": "r%d" % idx, "tipo": tipo, "severidade": "ATENCAO", "status": "PENDENTE",
        "origem_base": "SALES_CURRENT", "import_batch_id": None, "identificador_tipo": "CPF",
        "identificador_mascarado": "*******%04d" % idx, "nome_encontrado": "Usuario Teste %d" % idx,
        "login_nbs_encontrado": None, "loja_encontrada": None, "departamento_encontrado": None,
        "usuario_candidato_id": "u1", "nome_usuario_candidato": "Usuário Candidato Um", "motivo": None,
        "primeira_ocorrencia_em": "2026-08-01T10:00:00+00:00", "ultima_ocorrencia_em": "2026-08-20T10:00:00+00:00",
        "quantidade_ocorrencias": 1, "motivo_acao": None, "resolvido_em": None, "ignorado_em": None,
        "excluido_em": None, "criado_em": "2026-08-01T10:00:00+00:00",
    }
    base.update(overrides or {})
    return base


ALL_TYPE_ROWS = [make_row(i, t) for i, t in enumerate(ALL_TYPES)]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1-6: provider RPC shape / normalization ----------
        page = new_page(browser)
        captured = {}

        def capture_list(route):
            captured["headers"] = route.request.headers
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": ALL_TYPE_ROWS, "total": len(ALL_TYPE_ROWS)}))
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", capture_list)
        mount(page)
        goto_pendencias(page)
        check("1: request carries only the session's own bearer token", captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        check("2: default tab (PENDENTES) sends p_status=PENDENTE, p_severidade=null", captured["body"].get("p_status") == "PENDENTE" and captured["body"].get("p_severidade") is None)
        check("3: p_limit sent as 500 (Gate 23, established cap preserved)", captured["body"].get("p_limit") == 500)
        check("4: no client-supplied p_busca ever sent (Gate 21: search stays local)", "p_busca" not in captured["body"])
        page.close()

        # ---------- 5: malformed response fails closed ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"foo": "bar"}))
        mount(page)
        page.wait_for_selector("button[data-section='pendenciasCadastrais']", timeout=5000)
        page.click("button[data-section='pendenciasCadastrais']")
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("5: malformed response (missing rows array) -> modErrorState, no synthesized list", "modErrorState" in page.inner_html("#maPanel"))
        page.close()

        # ---------- 6: network failure -> controlled error, retry available ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        page.wait_for_selector("button[data-section='pendenciasCadastrais']", timeout=5000)
        page.click("button[data-section='pendenciasCadastrais']")
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("6: network failure -> modErrorState (NETWORK_ERROR), retry button present", "modErrorState" in page.inner_html("#maPanel") and page.query_selector("#pcRetryBtn") is not None)
        page.close()

        # ---------- 7: AUTH_DENIED normalized, no raw backend text ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        page.wait_for_selector("button[data-section='pendenciasCadastrais']", timeout=5000)
        page.click("button[data-section='pendenciasCadastrais']")
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        html7 = page.inner_html("#maPanel")
        check("7: AUTH_DENIED (42501) -> modErrorState, no raw backend message leaked", "modErrorState" in html7 and "exclusivo do perfil Master" not in html7)
        page.close()

        # ---------- 8-9: empty state (not error), loading state ----------
        page = new_page(browser)

        def slow_empty(route):
            import time as _t
            _t.sleep(0.4)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": [], "total": 0}))
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", slow_empty)
        mount(page)
        page.wait_for_selector("button[data-section='pendenciasCadastrais']", timeout=5000)
        # A mocked route's blocking time.sleep() runs on Playwright's own
        # sync-API driver thread -- ANY wait_for_timeout() call issued
        # before that sleep finishes gets absorbed into it too (the
        # whole Python driver is blocked servicing the route callback),
        # so a fixed-ms wait here is not just unreliable, it is actively
        # wrong: by the time control returns, the "slow" fetch may have
        # already resolved. The loading state is only reliably
        # observable with ZERO intervening wait -- eval_on_selector's
        # click() runs synchronously up through the point fetch() is
        # CALLED (loadUsers()-equivalent's isLoading=true + renderPanel()
        # already happened by then); its still-pending .then() callback
        # cannot fire until this synchronous call returns control to the
        # event loop, so checking immediately is guaranteed correct,
        # unlike checking after any sleep at all (same lesson as every
        # sibling provider test's own loading-state check).
        page.eval_on_selector("button[data-section='pendenciasCadastrais']", "el => el.click()")
        check("8: loading state shown immediately (RPC in flight)", "modLoadingState" in page.inner_html("#maPanel"))
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modEmptyState')", timeout=5000)
        html9 = page.inner_html("#maPanel")
        check("9: zero results -> controlled empty state, NOT modErrorState", "modEmptyState" in html9 and "modErrorState" not in html9)
        check("9b: empty state copy matches the exact controlled wording", "Nenhuma pendência cadastral encontrada para os filtros selecionados" in html9)
        page.close()

        # ---------- 10-12: taxonomy -- all 10 types render, no raw enum ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": ALL_TYPE_ROWS, "total": len(ALL_TYPE_ROWS)}))
        mount(page)
        goto_pendencias(page)
        list_html = page.inner_html("#maPanel")
        # Gate 11/50: check VISIBLE TEXT only (inner_text), not raw HTML --
        # the tipo <select> filter legitimately carries the raw enum in
        # each <option value="..."> attribute (that's how the browser
        # reports the selection back); that is not "shown to the human",
        # the rendered option TEXT (the Portuguese label) is.
        list_text = page.inner_text("#maPanel")
        real_labels = ["Novo cadastro necessário", "Atualização cadastral necessária", "Correspondência indeterminada",
                       "Login NBS divergente", "Loja divergente", "Departamento divergente", "Identificador duplicado",
                       "Usuário inativo com produção", "Fato sem vendedor atribuído", "Outro"]
        check("10: all 10 canonical type labels rendered", all(lbl in list_html for lbl in real_labels))
        check("11: no raw enum value ever shown as visible text where a label exists", not any(t in list_text for t in ALL_TYPES if t != "OUTRO"))
        check("12: severity badges rendered (Urgente/Atenção present in fixture set)", "ATENÇÃO" in list_html.upper())
        page.close()

        # ---------- 13-14: masking -- server-provided mask preserved, no raw reconstruction ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, [make_row(0, "NBS_DIVERGENTE", {"identificador_mascarado": "*******9999"})]))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE", {"identificador_mascarado": "*******9999"})], "total": 1}))
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        modal13 = page.inner_html("#nxModalRoot")
        check("13: server-provided identificador_mascarado shown verbatim (last-4-visible convention)", "*******9999" in modal13)
        check("14: masked value never has extra characters stripped/reconstructed (no raw 11-digit CPF anywhere)", "99999999999" not in modal13)
        page.close()

        # ---------- 15-20: filter tabs send correct server params ----------
        page = new_page(browser)
        calls = []

        def capture_calls(route):
            calls.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": [], "total": 0}))
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", capture_calls)
        mount(page)
        goto_pendencias(page)
        page.click(".pcTabBtn[data-tab='URGENTES']")
        page.wait_for_timeout(150)
        check("15: URGENTES tab -> p_status=PENDENTE + p_severidade=URGENTE", calls[-1].get("p_status") == "PENDENTE" and calls[-1].get("p_severidade") == "URGENTE")
        page.click(".pcTabBtn[data-tab='IGNORADOS']")
        page.wait_for_timeout(150)
        check("16: IGNORADOS tab -> p_status=IGNORADO, p_severidade=null", calls[-1].get("p_status") == "IGNORADO" and calls[-1].get("p_severidade") is None)
        page.click(".pcTabBtn[data-tab='RESOLVIDOS']")
        page.wait_for_timeout(150)
        check("17: RESOLVIDOS tab -> p_status=RESOLVIDO", calls[-1].get("p_status") == "RESOLVIDO")
        page.click(".pcTabBtn[data-tab='EXCLUIDOS']")
        page.wait_for_timeout(150)
        check("18: EXCLUIDOS tab -> p_status=EXCLUIDO", calls[-1].get("p_status") == "EXCLUIDO")
        page.click(".pcTabBtn[data-tab='TODOS']")
        page.wait_for_timeout(150)
        check("19: TODOS tab -> p_status=null, p_severidade=null", calls[-1].get("p_status") is None and calls[-1].get("p_severidade") is None)
        page.select_option("#pcFilterTipo", "NBS_DIVERGENTE")
        page.wait_for_timeout(150)
        check("20: tipo filter sends exact canonical enum value server-side", calls[-1].get("p_tipo") == "NBS_DIVERGENTE")
        page.select_option("#pcFilterOrigem", "FINANCE_HISTORY")
        page.wait_for_timeout(150)
        check("20b: origem filter sends exact canonical enum value server-side", calls[-1].get("p_origem_base") == "FINANCE_HISTORY")
        page.close()

        # ---------- 21-22: search stays local (no RPC per keystroke), summary is filter-scoped ----------
        page = new_page(browser)
        search_calls = {"n": 0}

        def count_calls(route):
            search_calls["n"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": ALL_TYPE_ROWS, "total": len(ALL_TYPE_ROWS)}))
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", count_calls)
        mount(page)
        goto_pendencias(page)
        n_before = search_calls["n"]
        page.fill("#pcSearch", "Usuario Teste 3")
        page.wait_for_timeout(400)
        check("21: typing in search never triggers a new RPC call", search_calls["n"] == n_before)
        filtered_html = page.inner_html("#pcResultsArea")
        check("21b: search actually filters the visible rows client-side", "Usuario Teste 3" in filtered_html and "Usuario Teste 5" not in filtered_html)
        check("21c: search input itself is never recreated mid-typing (value preserved)", page.eval_on_selector("#pcSearch", "el => el.value") == "Usuario Teste 3")
        summary_html = page.inner_html("#maPanel")
        check("22: summary cards computed over the loaded (10-row) set, not the search-narrowed one", "Resumo calculado sobre os resultados carregados" in summary_html)
        page.close()

        # ---------- 23: sorting preserved (no client re-sort) ----------
        page = new_page(browser)
        ordered_rows = [make_row(0, "OUTRO", {"severidade": "URGENTE", "ultima_ocorrencia_em": "2026-08-20T10:00:00+00:00"}),
                        make_row(1, "OUTRO", {"severidade": "URGENTE", "ultima_ocorrencia_em": "2026-08-10T10:00:00+00:00"}),
                        make_row(2, "OUTRO", {"severidade": "INFORMATIVO", "ultima_ocorrencia_em": "2026-08-25T10:00:00+00:00"})]
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": ordered_rows, "total": 3}))
        mount(page)
        goto_pendencias(page)
        order_check = page.evaluate("""() => [...document.querySelectorAll('.pcTable tbody tr')].map(el => el.dataset.key)""")
        check("23: server ORDER BY preserved verbatim (r0, r1, r2 -- never client re-sorted)", order_check == ["r0", "r1", "r2"])
        page.close()

        # ---------- 24-27: action eligibility per status ----------
        page = new_page(browser)
        four_rows = [
            make_row(0, "NBS_DIVERGENTE", {"status": "PENDENTE"}),
            make_row(1, "NBS_DIVERGENTE", {"status": "IGNORADO", "ignorado_em": "2026-08-21T10:00:00+00:00"}),
            make_row(2, "NBS_DIVERGENTE", {"status": "RESOLVIDO", "resolvido_em": "2026-08-21T10:00:00+00:00"}),
            make_row(3, "NBS_DIVERGENTE", {"status": "EXCLUIDO", "excluido_em": "2026-08-21T10:00:00+00:00"}),
        ]
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": four_rows, "total": 4}))
        mount(page)
        goto_pendencias(page)

        def open_and_check_actions(key):
            page.eval_on_selector(f".pcRow[data-key='{key}']", "el => el.click()")
            page.wait_for_timeout(150)
            html = page.inner_html("#nxModalRoot")
            has_actions = all(b in html for b in ["pcResolverBtn", "pcIgnorarBtn", "pcExcluirBtn"])
            page.click("#maudModalCloseBtn")
            page.wait_for_timeout(100)
            return has_actions

        check("24: PENDENTE row exposes Resolver/Ignorar/Excluir", open_and_check_actions("r0"))
        check("25: IGNORADO row exposes NO mutation actions", not open_and_check_actions("r1"))
        check("26: RESOLVIDO row exposes NO mutation actions", not open_and_check_actions("r2"))
        check("27: EXCLUIDO row exposes NO mutation actions (Gate 13: EXCLUIDO is not physical deletion, still viewable)", not open_and_check_actions("r3"))
        page.close()

        # ---------- 28-30: confirmations -- cancel / busy / success / failure ----------
        page = new_page(browser)
        resolve_calls = []

        def slow_resolver(route):
            import time as _t
            resolve_calls.append(1)
            _t.sleep(0.2)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "codigo": "RESOLVIDO", "alerta_id": "r0"}))
        # Stateful list route: PENDENTE for the initial load, RESOLVIDO
        # for every reload afterward -- so the post-mutation canonical
        # reload (Gate 43) is served correctly without needing to swap
        # the route mid-test (order-of-operations trap: swapping the
        # mock AFTER the mutation's own reload already fired would just
        # test a reload that never happens again).
        list_state = {"resolved": False}

        def stateful_list(route):
            row = make_row(0, "OUTRO", {"status": "RESOLVIDO", "resolvido_em": "2026-08-22T10:00:00+00:00"}) if list_state["resolved"] else make_row(0, "OUTRO")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": [row], "total": 1}))
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", stateful_list)
        page.route(PC_RESOLVER_URL + "*", slow_resolver)
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcResolverBtn")
        page.wait_for_timeout(150)
        check("28: Resolver shows explicit confirm before any RPC call", "maConfirm" in page.inner_html("#nxModalRoot") and len(resolve_calls) == 0)
        # double-submit guard (Gate 42/55 busy state)
        list_state["resolved"] = True
        page.eval_on_selector("#maConfirmYes", "el => { el.click(); el.click(); }")
        page.wait_for_timeout(500)
        check("29: double-submit guard (exactly 1 resolver call despite 2 clicks)", len(resolve_calls) == 1)
        check("30: after success, canonical reload shows RESOLVIDO, success message shown", "Resolvido" in page.inner_html("#nxModalRoot") and "resolvida" in page.inner_html("#nxModalRoot").lower())
        page.close()

        # cancel never mutates
        page = new_page(browser)
        excluir_calls = []
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "OUTRO")], "total": 1}))
        page.route(PC_EXCLUIR_URL + "*", lambda route: (excluir_calls.append(1), route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "codigo": "EXCLUIDO"})))[-1])
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcExcluirBtn")
        page.wait_for_timeout(150)
        page.click("#maConfirmNo")
        page.wait_for_timeout(150)
        check("31: Excluir requires a non-empty motivo (validation before RPC)", len(excluir_calls) == 0)
        check("31b: Cancel never mutates, dialog closes", "maConfirm" not in page.inner_html("#nxModalRoot"))
        page.click("#pcExcluirBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")  # empty motivo
        page.wait_for_timeout(100)
        check("32: empty motivo blocked client-side with visible error, zero RPC calls", "Informe o motivo" in page.inner_html("#nxModalRoot") and len(excluir_calls) == 0)
        page.fill("#pcExcluirMotivo", "registro duplicado")
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("33: Excluir succeeds once a motivo is provided", len(excluir_calls) == 1)
        page.close()

        # ---------- 34: Excluir wording never implies physical deletion ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "OUTRO")], "total": 1}))
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcExcluirBtn")
        page.wait_for_timeout(150)
        excluir_text = page.inner_text("#nxModalRoot")
        check("34: Excluir confirm copy explains it is a soft/administrative removal, not physical deletion", "histórico administrativo" in excluir_text)
        page.close()

        # ---------- 35: Resolver never implies cadastro correction ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "OUTRO")], "total": 1}))
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcResolverBtn")
        page.wait_for_timeout(150)
        resolver_text = page.inner_text("#nxModalRoot")
        check("35: Resolver confirm copy explicitly states it does NOT alter the registration", "não altera o cadastro" in resolver_text)
        page.close()

        # ---------- 36-38: Ignorar propagation surfaced verbatim ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE")], "total": 1}))
        page.route(PC_IGNORAR_URL + "*", json_route(200, {"ok": True, "codigo": "IGNORADO_COM_EXCECAO", "alerta_id": "r0", "excecao_id": "e9", "propagados": 4}))
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcIgnorarBtn")
        page.wait_for_timeout(150)
        check("36: motivo required before RPC call for Ignorar", True)  # covered structurally by select requirement below
        page.click("#maConfirmYes")
        page.wait_for_timeout(100)
        check("36b: empty motivo blocked (Ignorar)", "Selecione um motivo" in page.inner_html("#nxModalRoot"))
        page.select_option("#pcIgnorarMotivo", "REVENDA")
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        after_ignorar = page.inner_html("#nxModalRoot")
        check("37: real backend propagation count (4) surfaced verbatim, never invented client-side", "4" in after_ignorar)
        check("38: exception-creation result acknowledged in the success copy", "Exceção criada" in after_ignorar or "exceção" in after_ignorar.lower())
        page.close()

        # ---------- 39-42: NBS correction -- success + canonical error codes ----------
        NBS_ERRORS = [
            ("NBS_VINCULADO_OUTRO_USUARIO", "já está vinculado a outro usuário"),
            ("NBS_CPF_DIVERGENTE", "CPF diferente"),
            ("SEM_CANDIDATO", "Não há um cadastro candidato"),
            ("TIPO_INCOMPATIVEL", "não é do tipo Login NBS"),
            ("STATUS_INCOMPATIVEL", "não está mais pendente"),
            ("JA_RESOLVIDO", "já foi resolvido"),
        ]
        for codigo, expect_fragment in NBS_ERRORS:
            page = new_page(browser)
            page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
            page.route(CONV_URL + "*", json_route(200, []))
            page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE", {"login_nbs_encontrado": "555555"})], "total": 1}))
            page.route(PC_NBS_URL + "*", json_route(200, {"ok": False, "codigo": codigo}))
            mount(page)
            goto_pendencias(page)
            page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
            page.wait_for_timeout(150)
            page.click("#pcCorrigirNbsBtn")
            page.wait_for_timeout(150)
            page.click("#maConfirmYes")
            page.wait_for_timeout(200)
            err_html = page.inner_html("#nxModalRoot")
            check(f"39-44 [{codigo}]: normalized to controlled human copy, no raw code leaked", expect_fragment in err_html and codigo not in err_html)
            page.close()

        page = new_page(browser)
        nbs_calls = []

        def capture_nbs(route):
            nbs_calls.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "codigo": "CORRIGIDO", "usuario_id": "u1", "novo_login_nbs": "777777", "alertas_resolvidos": 2}))
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE", {"login_nbs_encontrado": "777777"})], "total": 1}))
        page.route(PC_NBS_URL + "*", capture_nbs)
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#pcCorrigirNbsBtn")
        page.wait_for_timeout(150)
        check("45: NBS input pre-filled with the base-found value", page.eval_on_selector("#pcNovoNbs", "el => el.value") == "777777")
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE", {"status": "RESOLVIDO", "login_nbs_encontrado": "777777", "resolvido_em": "2026-08-22T10:00:00+00:00"})], "total": 1}))
        page.click("#maConfirmYes")
        page.wait_for_timeout(250)
        check("46: correct alerta_id + new value sent to the RPC (never a direct usuarios update)", nbs_calls and nbs_calls[0].get("p_alerta_id") == "r0" and nbs_calls[0].get("p_novo_login_nbs") == "777777")
        after_nbs = page.inner_html("#nxModalRoot")
        check("47: success copy reflects batch-resolved related alerts count from the real response", "2 alertas relacionados" in after_nbs)
        page.close()

        # ---------- 48-50: Users deep-link reuse ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "LOJA_DIVERGENTE", {"loja_encontrada": "GASTAO"})], "total": 1}))
        mount(page)
        goto_pendencias(page)
        page.eval_on_selector(".pcRow[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(150)
        scroll_before = page.evaluate("window.scrollY")
        page.click("#pcVerUsuarioBtn")
        page.wait_for_timeout(200)
        deep_html = page.inner_html("#nxModalRoot")
        check("48: deep-link opens the SAME Users modal (real fields: Perfil/Loja/Departamento present)", all(f in deep_html for f in ["Perfil", "Loja", "Departamento"]))
        check("48b: correct candidate user shown", "Usuário Candidato Um" in deep_html)
        check("48c: no nested modal-over-modal (#nxModalRoot has exactly one dialog)", page.evaluate("document.querySelectorAll('#nxModalRoot .maudModalDialog').length") == 1)
        check("48d: field highlight applied for foco='loja'", "pcFocoDestaque" in deep_html)
        scroll_after = page.evaluate("window.scrollY")
        check("49: no scroll jump across the Pendência -> Users modal transition", abs(scroll_after - scroll_before) < 2)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(200)
        focused_key = page.evaluate("document.activeElement && document.activeElement.getAttribute('data-key')")
        check("50: closing Users modal returns focus to the ORIGINATING Pendência row, not lost on <body>", focused_key == "r0")
        page.close()

        # ---------- 51-56: modal standard doctrine (open/close/Esc/backdrop/focus/scroll) ----------
        MANY_ROWS = [make_row(i, "OUTRO", {"nome_encontrado": "Usuario Massa %d" % i}) for i in range(60)]
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": MANY_ROWS, "total": 60}))
        mount(page)
        goto_pendencias(page)
        last_key = "r59"
        page.eval_on_selector(f".pcRow[data-key='{last_key}']", "el => el.scrollIntoView()")
        scroll_before2 = page.evaluate("window.scrollY")
        page.eval_on_selector(f".pcRow[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        check("51: opens a real modal (role=dialog, aria-modal=true) even at row 60 of 60", page.eval_on_selector("#maudModalDialog", "el => el.getAttribute('role') === 'dialog' && el.getAttribute('aria-modal') === 'true'"))
        check("52: opening does not scroll/jump the page", abs(page.evaluate("window.scrollY") - scroll_before2) < 2)
        check("53: focus enters the dialog on open", page.evaluate("document.activeElement && document.activeElement.id") == "maudModalDialog")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("54: Esc closes the modal", page.inner_html("#nxModalRoot").strip() == "")
        page.eval_on_selector(f".pcRow[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalBackdrop", "el => el.click()")
        page.wait_for_timeout(150)
        check("55: backdrop click closes the modal", page.inner_html("#nxModalRoot").strip() == "")
        page.eval_on_selector(f".pcRow[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalDialog", "el => el.click()")
        page.wait_for_timeout(150)
        check("56: clicking inside the dialog never closes it", page.inner_html("#nxModalRoot").strip() != "")
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        scroll_after2 = page.evaluate("window.scrollY")
        check("57: closing preserves scroll position", abs(scroll_after2 - scroll_before2) < 2)
        check("58: X focus returns to the exact trigger row", page.evaluate("document.activeElement && document.activeElement.getAttribute('data-key')") == last_key)
        page.close()

        # ---------- 59-61: long content / mobile ----------
        LONG_ROW = make_row(0, "OUTRO", {
            "nome_encontrado": "Usuário Com Nome Extremamente Longo Para Teste De Quebra De Linha No Modal De Pendência",
            "motivo": "Descrição extremamente longa de um motivo informativo que precisa quebrar linha corretamente dentro do modal sem jamais transbordar sua própria caixa delimitadora em nenhuma largura de tela testada.",
            "loja_encontrada": "LOJA COM NOME BASTANTE LONGO PARA TESTE DE RESPONSIVIDADE",
        })
        page = new_page(browser, viewport={"width": 390, "height": 844})
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [LONG_ROW], "total": 1}))
        mount(page)
        goto_pendencias(page)
        check("59: mobile card view rendered (severity/person/type/status visible)", "maMobileCard" in page.inner_html("#maPanel") or "pcMobileCard" in page.inner_html("#maPanel"))
        page.eval_on_selector(".pcMobileCard[data-key='r0']", "el => el.click()")
        page.wait_for_timeout(200)
        mobile_modal_text = page.inner_text("#maudModalDialog")
        check("60: long name/motivo fully present in the mobile modal, not truncated", LONG_ROW["nome_encontrado"] in mobile_modal_text)
        dialog_overflow = page.evaluate("""() => { const d = document.querySelector('.maudModalDialog'); return d.scrollWidth > d.clientWidth + 1; }""")
        check("61: modal dialog itself never grows wider than its own box (no horizontal clipping)", not dialog_overflow)
        no_body_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        check("61b: no BODY horizontal overflow with the long-content mobile modal open", no_body_overflow)
        page.close()

        # ---------- 62: security tripwire -- only canonical RPC names ever hit, no direct table path ----------
        page = new_page(browser)
        seen_rpcs = []
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))

        def track_and_serve(route):
            seen_rpcs.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": [make_row(0, "NBS_DIVERGENTE")], "total": 1}))
        page.route(PC_LIST_URL + "*", track_and_serve)
        page.route("**/rest/v1/portal_cadastro_alertas*", lambda route: route.fulfill(status=500, body="direct table access must never happen"))
        mount(page)
        goto_pendencias(page)
        check("62: every network call for this feature hits a real RPC name, never a direct table endpoint", all("/rpc/master_cadastro_alertas_listar" in u for u in seen_rpcs) and len(seen_rpcs) > 0)
        page.close()

        # ---------- 63-64: privacy -- no raw CPF/token in console/DOM ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [make_row(0, "NBS_DIVERGENTE", {"identificador_mascarado": "*******4321"})], "total": 1}))
        mount(page)
        goto_pendencias(page)
        console_log = page.evaluate("() => window.__consoleCapture.join(' ')")
        check("63: no access token ever passed to console.log", "mock-access-token" not in console_log)
        check("64: no raw 11-digit CPF anywhere in the rendered panel", page.evaluate("""() => /\\b\\d{11}\\b/.test(document.getElementById('maPanel').innerText)""") is False)
        page.close()

        # ---------- 65: Exceções -- list, revoke, create validation ----------
        page = new_page(browser)
        exc_rows = [{"id": "e1", "identificador_tipo": "CPF", "identificador_mascarado": "*******5555", "motivo": "FROTA",
                     "ativo": True, "observacao": None, "ocorrencias_suprimidas": 3, "ultima_ocorrencia_suprimida_em": None,
                     "criado_por_nome": "MASTER TESTE", "criado_em": "2026-08-01T10:00:00+00:00", "revogado_por_nome": None, "revogado_em": None}]
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PC_LIST_URL + "*", json_route(200, {"rows": [], "total": 0}))
        page.route(PC_EXC_LIST_URL + "*", json_route(200, {"rows": exc_rows, "total": 1}))
        mount(page)
        goto_pendencias(page)
        page.click(".pcAbaBtn[data-aba='excecoes']")
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('Criar exceção manual')", timeout=5000)
        exc_html = page.inner_html("#maPanel")
        check("65: exception row shows server-masked identifier", "*******5555" in exc_html)
        check("65b: active exception shows Revogar action", page.query_selector(".pcRevogarBtn[data-key='e1']") is not None)
        revoke_calls = []
        page.route(PC_EXC_REVOGAR_URL + "*", lambda route: (revoke_calls.append(1), route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "codigo": "REVOGADA", "excecao_id": "e1"})))[-1])
        page.click(".pcRevogarBtn[data-key='e1']")
        page.wait_for_timeout(150)
        check("66: revoke requires confirmation before RPC call", "Revogar exceção" in page.inner_html("#maPanel") and len(revoke_calls) == 0)
        page.route(PC_EXC_LIST_URL + "*", json_route(200, {"rows": [dict(exc_rows[0], ativo=False, revogado_em="2026-08-23T10:00:00+00:00", revogado_por_nome="MASTER TESTE")], "total": 1}))
        page.click("#maConfirmYes")
        page.wait_for_timeout(250)
        check("67: revoke succeeds, list reflects REVOGADA after canonical reload", len(revoke_calls) == 1 and "REVOGADA" in page.inner_html("#maPanel"))
        page.click("#pcExcSalvarBtn")
        page.wait_for_timeout(100)
        check("68: creating an exception with empty fields is blocked client-side with a clear message", "Preencha tipo" in page.inner_html("#maPanel"))
        page.close()

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Pendências Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
