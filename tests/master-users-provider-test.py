#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase 2A -- deterministic tests for the Usuários module
itself (master-users-provider.js, master-users-view-model.js,
shell-admin.js), mounted directly via a lightweight harness (route
guard is tested separately in tests/master-admin-route-test.py, against
the real shell/router/auth-core).

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. Mutations (invite/edit/block/
resend) are exercised here ONLY through this mocked transport --
Painel Master Phase 2A's own MUTATION FREEZE means no real mutation RPC
is ever called against the real backend in this session; this file is
exactly how the mutation code paths get proven correct without that.

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
INVITE_URL = "https://mock.invalid/rest/v1/rpc/master_convidar_usuario"
UPDATE_URL = "https://mock.invalid/rest/v1/rpc/master_atualizar_autorizacao_usuario"
RESEND_URL = "https://mock.invalid/rest/v1/rpc/master_reenviar_convite"
ADMIN_INVITE_EDGE_URL = "https://mock.invalid/functions/v1/admin-invite-user"
ACCESS_LINK_EDGE_URL = "https://mock.invalid/functions/v1/admin-generate-user-access-link"
CONTINUATION_RPC_URL = "https://mock.invalid/rest/v1/rpc/master_gerar_continuacao_primeiro_acesso"

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


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
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


# Real contract shape (docs/MASTER-USERS-RPC-CONTRACT-CAPTURE.md),
# covering each lifecycle state + a profile/store spread. Names are
# synthetic, not real staff records.
USERS = [
    {"id": "u1", "cpf": "11111111111", "cpf_normalizado": "11111111111", "nome": "Usuário Convidado",
     "perfil": "VENDEDOR", "loja": "BARRA FUNDA", "status": "NOVOS", "ativo": False,
     "primeiro_acesso": True, "ultimo_login": None, "email_auth": "convidado@example.com",
     "tem_auth": False, "email_divergente": False, "auth_confirmado": False, "ativacao_legado": None},
    {"id": "u2", "cpf": "22222222222", "cpf_normalizado": "22222222222", "nome": "Usuário Não Confirmado",
     "perfil": "GERENTE", "loja": "ALPHAVILLE", "status": "SEMINOVOS", "ativo": False,
     "primeiro_acesso": True, "ultimo_login": None, "email_auth": "naoconfirmado@example.com",
     "tem_auth": True, "email_divergente": False, "auth_confirmado": False, "ativacao_legado": None},
    {"id": "u3", "cpf": "33333333333", "cpf_normalizado": "33333333333", "nome": "Usuário Primeiro Acesso",
     "perfil": "ANALISTA", "loja": None, "status": "NOVOS/SEMINOVOS", "ativo": False,
     "primeiro_acesso": True, "ultimo_login": None, "email_auth": "primeiroacesso@example.com",
     "tem_auth": True, "email_divergente": False, "auth_confirmado": True, "ativacao_legado": None},
    {"id": "u4", "cpf": "44444444444", "cpf_normalizado": "44444444444", "nome": "Usuário Ativo",
     "perfil": "MASTER", "loja": None, "status": "MASTER", "ativo": True,
     "primeiro_acesso": False, "ultimo_login": "2026-09-01T10:00:00Z", "email_auth": "ativo@example.com",
     "tem_auth": True, "email_divergente": False, "auth_confirmado": True, "ativacao_legado": None},
    {"id": "u5", "cpf": "55555555555", "cpf_normalizado": "55555555555", "nome": "Usuário Bloqueado",
     "perfil": "RH", "loja": None, "status": None, "ativo": False,
     "primeiro_acesso": False, "ultimo_login": "2026-08-01T10:00:00Z", "email_auth": "bloqueado@example.com",
     "tem_auth": True, "email_divergente": True, "auth_confirmado": True, "ativacao_legado": None},
]
CONVITES = [
    {"id": "c1", "usuario_id": "u1", "cpf": "11111111111", "nome": "Usuário Convidado", "perfil": "VENDEDOR",
     "loja": "BARRA FUNDA", "email": "convidado@example.com", "nbs": None, "status": "PENDENTE",
     "convidado_por": "master-id", "convidado_em": "2026-09-01T10:00:00Z", "atualizado_em": "2026-09-01T10:00:00Z",
     "tentativas_envio": 1, "aceito_em": None, "erro_mensagem": None,
     "usuario_auth_user_id": None, "usuario_ativo": False, "usuario_primeiro_acesso": True},
]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 7: loading ----------
        page = new_page(browser)

        def slow_sec(route):
            import time as _t
            _t.sleep(0.3)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"users": USERS, "configurations": [], "audit": []}))
        page.route(SEC_URL + "*", slow_sec)
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.goto(BASE)
        page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
        page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")
        loading_html = page.inner_html("#maPanel")
        check("7: loading state visible immediately after mount (RPC in flight)", "modLoadingState" in loading_html)
        page.close()

        # ---------- 8: empty ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.length > 0", timeout=5000)
        html = page.inner_html("#maPanel")
        check("8: empty user list -> normal empty state, not modErrorState", "modErrorState" not in html and "Nenhum usuário encontrado" in html)
        page.close()

        # ---------- 9: malformed response ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"foo": "bar"}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("9: malformed response (missing users array) -> modErrorState", "modErrorState" in page.inner_html("#maPanel"))
        page.close()

        # ---------- 10-12: error normalization ----------
        error_cases = [(42501, "42501", "AUTH_DENIED"), (500, "57014", "RPC_ERROR")]
        for status, code, label in error_cases:
            page = new_page(browser)
            page.route(SEC_URL + "*", json_route(status, {"code": code, "message": "backend detail not for users"}))
            page.route(CONV_URL + "*", json_route(200, []))
            mount(page)
            page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
            html = page.inner_html("#maPanel")
            check("10." + code + ": " + label + " -> modErrorState shown", "modErrorState" in html)
            check("10." + code + ": no raw backend error text leaked", "backend detail not for users" not in html)
            page.close()

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(401, {"message": "jwt expired"}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("11: 401 -> SESSION_EXPIRED normalization, no raw JWT text", "modErrorState" in page.inner_html("#maPanel") and "jwt expired" not in page.inner_html("#maPanel"))
        page.close()

        page = new_page(browser)
        page.route(SEC_URL + "*", lambda route: route.abort("failed"))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("12: network failure -> modErrorState (NETWORK_ERROR)", "modErrorState" in page.inner_html("#maPanel"))
        page.close()

        # ---------- 15-20: PII minimization + mapping (full dataset) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        list_html = page.inner_html("#maPanel")
        # CPF is a detail-panel-only field (never shown in the list at
        # all) -- open a detail to exercise the actual masking path.
        page.eval_on_selector(".maTable tbody tr[data-key='u1']", "el => el.click()")
        page.wait_for_timeout(100)
        detail_html = page.inner_html("#nxModalRoot")
        check("15: CPF never rendered in full, only masked form, in the detail modal", "11111111111" not in detail_html and "***.***.**" in detail_html)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)
        check("16: auth_user_id never rendered anywhere (not even in raw payload)", "auth_user_id" not in list_html and "auth-user" not in list_html.lower())
        check("17: no invite/continuation token ever rendered", "token" not in list_html.lower() and "continuacao" not in list_html.lower())
        check("18: profile values rendered from real contract (VENDEDOR/GERENTE/ANALISTA/MASTER/RH all present)",
              all(p in list_html for p in ["VENDEDOR", "GERENTE", "ANALISTA", "MASTER", "RH"]))
        check("19: store values rendered (BARRA FUNDA/ALPHAVILLE present)", "BARRA FUNDA" in list_html and "ALPHAVILLE" in list_html)
        check("20: lifecycle labels present for each real state (Convidado/confirmado/Ativo/Inativo)",
              "Convidado" in list_html and "primeiro acesso pendente" in list_html and "Ativo" in list_html and "Inativo" in list_html)

        # ---------- 21-22: search / filters ----------
        page.fill("#maSearch", "Ativo")
        page.wait_for_timeout(100)
        filtered_html = page.inner_html("#maPanel")
        check("21: search filters to matching rows only", "Usuário Ativo" in filtered_html and "Usuário Convidado" not in filtered_html)
        page.fill("#maSearch", "")
        page.select_option("#maFilterPerfil", "RH")
        page.wait_for_timeout(100)
        perfil_filtered = page.inner_html("#maPanel")
        check("22: perfil filter shows only matching profile", "Usuário Bloqueado" in perfil_filtered and "Usuário Ativo" not in perfil_filtered)
        page.select_option("#maFilterPerfil", "")
        page.wait_for_timeout(100)

        # ---------- 28-29: responsive equivalence + keyboard/focus ----------
        check("28: desktop table and mobile cards render the SAME rows (same data-key set)",
              page.evaluate("""() => {
                  const desktopKeys = [...document.querySelectorAll('.maTable tbody tr')].map(el => el.dataset.key).sort();
                  const mobileKeys = [...document.querySelectorAll('.maMobileCard')].map(el => el.dataset.key).sort();
                  return JSON.stringify(desktopKeys) === JSON.stringify(mobileKeys) && desktopKeys.length > 0;
              }"""))
        first_row = page.query_selector(".maTable tbody tr")
        first_row.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        check("29: Enter key on a focused row opens the detail modal (keyboard-operable, not click-only)",
              "maudModalDialog" in page.inner_html("#nxModalRoot") and page.get_attribute("#nxModalRoot", "aria-hidden") == "false")
        page.close()

        # ---------- 24-27: double-submit, confirmations (mocked mutation, never real) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        invite_calls = []

        def slow_invite(route):
            import time as _t
            invite_calls.append(1)
            _t.sleep(0.2)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"convite_id": "c-new", "usuario_id": "u-new", "email": "novo@example.com", "status": "PENDENTE"}))
        page.route(INVITE_URL + "*", slow_invite)
        page.route(ADMIN_INVITE_EDGE_URL + "*", json_route(200, {"ok": True, "message": "Convite enviado."}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.click("#maNewUserBtn")
        page.wait_for_timeout(100)
        page.fill("#maCpf", "12345678901")
        page.fill("#maNome", "Novo Colaborador")
        page.select_option("#maPerfil", "GERENTE")
        page.wait_for_timeout(50)
        page.select_option("#maStatus", "NOVOS")
        page.fill("#maEmail", "novo@example.com")
        page.click("#maCreateSubmit")
        page.wait_for_timeout(100)
        check("26: invite requires explicit confirmation step before RPC call", "maConfirm" in page.inner_html("#maPanel") and len(invite_calls) == 0)
        # Two clicks dispatched via JS in the same task, not two separate
        # Playwright click() actionability-checked calls -- a mocked
        # route's blocking time.sleep() runs on Playwright's own sync-API
        # driver thread, so a second real click() can time out waiting
        # for the (already-submitting) button's actionability state
        # rather than exercising the guard itself (same class of issue
        # diagnosed in Score Phase 2B's own loading-state test).
        page.eval_on_selector("#maConfirmYes", "el => { el.click(); el.click(); }")
        page.wait_for_timeout(500)
        check("24: double-submit prevented (exactly 1 invite RPC call despite 2 clicks)", len(invite_calls) == 1)
        page.close()

        # ---------- 37: two-step invite chain -- exact Edge Function shape (Gate 15) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(INVITE_URL + "*", json_route(200, {"convite_id": "c-new", "usuario_id": "u-new", "email": "novo@example.com", "status": "PENDENTE"}))
        edge_captured = {}

        def capture_edge(route):
            edge_captured["headers"] = route.request.headers
            edge_captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "message": "Convite enviado."}))
        page.route(ADMIN_INVITE_EDGE_URL + "*", capture_edge)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.click("#maNewUserBtn")
        page.wait_for_timeout(100)
        page.fill("#maCpf", "12345678901")
        page.fill("#maNome", "Novo Colaborador")
        page.select_option("#maPerfil", "GERENTE")
        page.wait_for_timeout(50)
        page.select_option("#maStatus", "NOVOS")
        page.fill("#maEmail", "novo@example.com")
        page.click("#maCreateSubmit")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        check("37: Edge Function called with exactly the RPC-returned convite_id, nothing else", edge_captured.get("body", {}) == {"convite_id": "c-new"})
        check("37b: Edge Function call carries only the session's own bearer token, never a service-role key", edge_captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc")
        page.close()

        # ---------- 25: destructive confirmation (block) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        update_calls = []
        page.route(UPDATE_URL + "*", lambda route: (update_calls.append(1), route.fulfill(status=200, content_type="application/json", body="true"))[-1])
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")  # Usuário Ativo
        page.wait_for_timeout(100)
        page.click("#maToggleActiveBtn")
        page.wait_for_timeout(100)
        confirm_html = page.inner_html("#nxModalRoot")
        check("25: block action shows a destructive confirmation before any RPC call", "maConfirm" in confirm_html and "modBtnDanger" in confirm_html and len(update_calls) == 0)
        page.close()

        # ---------- 27: edit confirmation ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(UPDATE_URL + "*", json_route(200, True))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maEditBtn")
        page.wait_for_timeout(100)
        page.select_option("#maEditPerfil", "GERENTE")
        page.eval_on_selector("#maEditForm", "el => el.requestSubmit()")
        page.wait_for_timeout(100)
        check("27: edit requires explicit confirmation before RPC call", "maConfirm" in page.inner_html("#nxModalRoot"))
        page.close()

        # ---------- 13-14: duplicate/conflict normalization on mutation ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(INVITE_URL + "*", json_route(409, {"code": "23505", "message": "duplicate"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.click("#maNewUserBtn")
        page.wait_for_timeout(100)
        page.fill("#maCpf", "99999999999")
        page.fill("#maNome", "Duplicado")
        page.select_option("#maPerfil", "VENDEDOR")
        page.wait_for_timeout(50)
        page.select_option("#maStatus", "NOVOS")
        page.fill("#maEmail", "dup@example.com")
        page.click("#maCreateSubmit")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("13: duplicate-user (23505) normalized to a user-facing message, no raw code", "Já existe um cadastro" in page.inner_html("#maPanel") and "23505" not in page.inner_html("#maPanel"))
        page.close()

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(RESEND_URL + "*", json_route(409, {"code": "55000", "message": "ja entregue"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u1']", "el => el.click()")  # Usuário Convidado (has conviteId)
        page.wait_for_timeout(100)
        resend_btn = page.query_selector("#maResendBtn")
        check("14a: resend button present for INVITED lifecycle user with a real conviteId", resend_btn is not None)
        page.click("#maResendBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        full_html_14 = page.inner_html("#maOutlet") + page.inner_html("#nxModalRoot")
        check("14: conflict (55000) normalized, no raw backend text", "modErrorState" not in full_html_14 or "55000" not in full_html_14)
        page.close()

        # ---------- 38: resend success -- two-step chain (RPC then same admin-invite-user Edge Function) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(RESEND_URL + "*", json_route(200, {"ok": True, "convite_id": "c1"}))
        resend_edge_captured = {}

        def capture_resend_edge(route):
            resend_edge_captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "message": "Reenviado."}))
        page.route(ADMIN_INVITE_EDGE_URL + "*", capture_resend_edge)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u1']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maResendBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        check("38: resend chains into the same admin-invite-user Edge Function with the correct convite_id", resend_edge_captured.get("body", {}) == {"convite_id": "c1"})
        page.close()

        # ---------- 23: read cancellation (rapid re-mount aborts prior list request) ----------
        page = new_page(browser)
        state = {"n": 0}

        def sequenced(route):
            import time as _t
            state["n"] += 1
            n = state["n"]
            marker = "***STALE" if n == 1 else "***FRESH"
            delay = 0.4 if n == 1 else 0.05
            _t.sleep(delay)
            body = {"users": [dict(USERS[0], nome=marker)], "configurations": [], "audit": []}
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(body))
        page.route(SEC_URL + "*", sequenced)
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_timeout(30)
        page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")  # re-mount triggers a fresh loadUsers()
        page.wait_for_timeout(600)
        final_html = page.inner_html("#maOutlet")
        check("23: stale list response never overwrites the fresher one", "***STALE" not in final_html)
        page.close()

        # ---------- 31: no token/link ever logged to console ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        console_log = page.evaluate("() => window.__consoleCapture.join(' ')")
        check("31: no token/access_token/link ever passed to console.log", "mock-access-token" not in console_log and "token" not in console_log.lower())
        page.close()

        # ---------- 32: real-mode provider request shape (no client scope authority) ----------
        page = new_page(browser)
        captured = {}

        def capture(route):
            captured["headers"] = route.request.headers
            captured["body"] = _json.loads(route.request.post_data or "{}")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"users": USERS, "configurations": [], "audit": []}))
        page.route(SEC_URL + "*", capture)
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        check("32: request carries only the session's own bearer token, no client-supplied scope/role param", captured.get("headers", {}).get("authorization") == "Bearer mock-access-token-abc" and captured.get("body", {}) == {})
        page.close()

        # ---------- 39-44: Phase 2C human UAT fix -- block state visibility + success feedback ----------
        # Exact reported bug shape: tem_auth=False (pre-first-access
        # invited) AND ativo=True (administratively active) -- the
        # precise combination that made the old single-dimension badge
        # mask a real, successful block.
        PRE_ACCESS_ACTIVE_USER = {
            "id": "u9", "cpf": "29999999902", "cpf_normalizado": "29999999902",
            "nome": "PAINEL MASTER HOMOLOG V2", "perfil": "VENDEDOR", "loja": "EUROPA",
            "status": "NOVOS", "ativo": True, "primeiro_acesso": True, "ultimo_login": None,
            "email_auth": "luisg.amadio@gmail.com", "tem_auth": False,
            "email_divergente": False, "auth_confirmado": False, "ativacao_legado": None,
        }

        def stateful_pages(browser, initial_ativo=True):
            state = {"ativo": initial_ativo}

            def sec_handler(route):
                u = dict(PRE_ACCESS_ACTIVE_USER, ativo=state["ativo"])
                route.fulfill(status=200, content_type="application/json", body=_json.dumps({"users": [u], "configurations": [], "audit": []}))

            def update_handler(route):
                state["ativo"] = not state["ativo"]
                route.fulfill(status=200, content_type="application/json", body="true")

            page = new_page(browser)
            page.route(SEC_URL + "*", sec_handler)
            page.route(CONV_URL + "*", json_route(200, []))
            page.route(UPDATE_URL + "*", update_handler)
            return page

        page = stateful_pages(browser, initial_ativo=True)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        pre_html = page.inner_html("#maPanel")
        check("39: BEFORE block -- invite state and admin state both visible independently (Convidado + Ativo)", "aguardando aceite" in pre_html and "Ativo" in pre_html)
        page.eval_on_selector(".maTable tbody tr[data-key='u9']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maToggleActiveBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        # Gate 13 (PM-4B.4): the success message + the refreshed detail
        # now render inside the modal (#nxModalRoot), not below the list
        # -- both regions must be combined to see the full picture.
        post_html = page.inner_html("#maOutlet") + page.inner_html("#nxModalRoot")
        check("40: AFTER block -- success message shown (inside the modal)", "bloqueado com sucesso" in post_html.lower())
        check("41: AFTER block -- admin state badge shows Bloqueado (list AND modal detail), invite state unchanged (Convidado still present, not masked/replaced)",
              post_html.count("Bloqueado") >= 2 and "aguardando aceite" in post_html)
        check("41b: button toggled to Reativar", "Reativar" in post_html and "id=\"maToggleActiveBtn\"" in post_html)
        page.close()

        # ---------- 42: block failure does not fake success ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [PRE_ACCESS_ACTIVE_USER], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(UPDATE_URL + "*", json_route(500, {"code": "57014", "message": "boom"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u9']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maToggleActiveBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        fail_html = page.inner_html("#maOutlet") + page.inner_html("#nxModalRoot")
        check("42: block RPC failure -> no success message, badge still shows Ativo (no fake transition)", "com sucesso" not in fail_html.lower() and "Bloqueado" not in fail_html)
        page.close()

        # ---------- 43: resend success displays confirmation ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(RESEND_URL + "*", json_route(200, {"ok": True, "convite_id": "c1"}))
        page.route(ADMIN_INVITE_EDGE_URL + "*", json_route(200, {"ok": True}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u1']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maResendBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        check("43: resend success -> visible confirmation message shown (inside the modal)",
              "reenviado com sucesso" in (page.inner_html("#maOutlet") + page.inner_html("#nxModalRoot")).lower())
        page.close()

        # ---------- 44: Edge Function failure AFTER RPC success -> no success message ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(RESEND_URL + "*", json_route(200, {"ok": True, "convite_id": "c1"}))
        page.route(ADMIN_INVITE_EDGE_URL + "*", json_route(500, {"error": "smtp down"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u1']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maResendBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        check("44: RPC success + Edge Function failure -> no success message ever shown (Gate 9)",
              "reenviado com sucesso" not in (page.inner_html("#maOutlet") + page.inner_html("#nxModalRoot")).lower())
        page.close()

        # ==================== Painel Master Phase PM-4B.3 ====================
        # Human UAT finding: real V1 parity gap -- link-generation actions
        # (activation/recovery/continuation) never existed in V2 at all.
        # State-specific visibility proven against the SAME fixture users
        # already used above (u2=activation-eligible, u3=continuation-
        # eligible, u4=recovery-eligible, u1/u5=no action, matching V1's
        # own real gap for those combinations -- not invented).

        # ---------- 45: correct action per state, invalid states show none ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)

        def open_and_get_action_btn(uid):
            page.eval_on_selector(f".maTable tbody tr[data-key='{uid}']", "el => el.click()")
            page.wait_for_timeout(100)
            btn = page.query_selector("#maGenerateLinkBtn")
            text = btn.text_content() if btn else None
            page.click("#maudModalCloseBtn")
            page.wait_for_timeout(100)
            return text

        check("45a: u2 (AUTH_CREATED_UNCONFIRMED+BLOCKED) shows 'Gerar link de ativação'", open_and_get_action_btn("u2") == "Gerar link de ativação")
        check("45b: u3 (FIRST_ACCESS_PENDING+BLOCKED) shows 'Gerar link para concluir acesso'", open_and_get_action_btn("u3") == "Gerar link para concluir acesso")
        check("45c: u4 (ACCEPTED+ACTIVE) shows 'Gerar link para redefinir senha'", open_and_get_action_btn("u4") == "Gerar link para redefinir senha")
        check("45d: u1 (INVITED, no auth yet) shows NO link action (Reenviar Convite covers it instead)", open_and_get_action_btn("u1") is None)
        check("45e: u5 (ACCEPTED+BLOCKED) shows NO link action (matches V1's own real gap, not invented)", open_and_get_action_btn("u5") is None)
        page.close()

        # ---------- 46: activation link -- confirm step, correct provider call, copy-only-after-link ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        link_calls = []

        def capture_link_call(route):
            link_calls.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "link": "https://TEST-ONLY-MOCK.example/token-placeholder-not-real"}))
        page.route(ACCESS_LINK_EDGE_URL + "*", capture_link_call)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u2']", "el => el.click()")
        page.wait_for_timeout(100)
        check("46: no link panel shown before any action taken", "maGeneratedLinkInput" not in page.inner_html("#nxModalRoot"))
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        check("46: explicit confirmation step shown before calling the backend (zero calls yet)", "maConfirm" in page.inner_html("#nxModalRoot") and len(link_calls) == 0)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("46: exactly one call to admin-generate-user-access-link", len(link_calls) == 1)
        if link_calls:
            check("46: correct usuario_id and tipo='activation' sent", link_calls[0].get("usuario_id") == "u2" and link_calls[0].get("tipo") == "activation")
            check("MASTER_USERS_ACTION security: no cpf/email/actor field ever sent in the payload", not any(k in link_calls[0] for k in ("cpf", "email", "actor", "master_id", "auth_uid")))
        check("46: link only shown AFTER generation succeeds (present now)", "maGeneratedLinkInput" in page.inner_html("#nxModalRoot"))
        check("46: the mock link string never appears anywhere except inside the readonly input value (no console/log leak surface in this render)", page.inner_html("#nxModalRoot").count("TEST-ONLY-MOCK") == 1)
        page.close()

        # ---------- 47: copy button only meaningful once a link exists; never auto-copies ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(ACCESS_LINK_EDGE_URL + "*", json_route(200, {"ok": True, "link": "https://TEST-ONLY-MOCK.example/token-b"}))
        page.add_init_script("""
        window.__clipboardWrites = [];
        Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__clipboardWrites.push(t); return Promise.resolve(); } }, configurable: true });
        """)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        clipboard_before = page.evaluate("window.__clipboardWrites.length")
        check("47: nothing copied to clipboard automatically after generation", clipboard_before == 0)
        page.click("#maCopyLinkBtn")
        page.wait_for_timeout(100)
        check("47: explicit 'Copiar link' click copies the exact generated link", page.evaluate("window.__clipboardWrites") == ["https://TEST-ONLY-MOCK.example/token-b"])
        check("47: visible feedback shown after copying", "copiado" in page.inner_text("#nxModalRoot").lower())
        page.click("#maCloseLinkPanel")
        page.wait_for_timeout(100)
        check("47: link panel fully cleared after Fechar (nothing lingers)", "maGeneratedLinkInput" not in page.inner_html("#nxModalRoot"))
        page.close()

        # ---------- 48: continuation link -- different backend shape (RPC, not Edge Function), same UX ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        continuation_calls = []

        def capture_continuation(route):
            continuation_calls.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "codigo": "GERADO"}))
        page.route(CONTINUATION_RPC_URL + "*", capture_continuation)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u3']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("48: exactly one call to master_gerar_continuacao_primeiro_acesso", len(continuation_calls) == 1)
        if continuation_calls:
            check("48: correct usuario_id sent, real token HASH sent (never the raw token)", continuation_calls[0].get("p_usuario_id") == "u3" and len(continuation_calls[0].get("p_token_hash", "")) == 64)
            check("48: expiration is ~30 minutes out, never absent", "p_expira_em" in continuation_calls[0])
        link_val = page.eval_on_selector("#maGeneratedLinkInput", "el => el.value")
        check("48: final link built client-side from the RAW token (server never returns it) -- points at the real production continuation host", link_val is not None and link_val.startswith("https://brabus.blistiq.com.br/concluir-acesso.html#token="))
        raw_token_in_link = link_val.split("token=")[1] if link_val else ""
        sent_hash = continuation_calls[0].get("p_token_hash") if continuation_calls else ""
        check("48: the hash sent to the server does not equal the raw token in the link (real hashing occurred, not a passthrough)", raw_token_in_link != sent_hash)
        page.close()

        # ---------- 49: real V1 continuation error codes normalized, dialog stays open (not silently closed) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(CONTINUATION_RPC_URL + "*", json_route(200, {"ok": False, "codigo": "RATE_LIMIT", "aguardar_segundos": 180}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u3']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        confirm_text = page.inner_text("#nxModalRoot")
        check("49: RATE_LIMIT normalized to real V1 copy (minutes, not raw codigo)", "minuto" in confirm_text.lower() and "RATE_LIMIT" not in confirm_text)
        check("49: confirm dialog stays open on failure (never silently closed, never a false success)", "maConfirm" in page.inner_html("#nxModalRoot") and "maGeneratedLinkInput" not in page.inner_html("#nxModalRoot"))
        page.close()

        # ---------- 50: MASTER-only server-side (403) normalized, no raw backend text ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(ACCESS_LINK_EDGE_URL + "*", json_route(403, {"error": "Apenas usuário MASTER ativo pode gerar links de acesso"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("50: 403 normalized, no raw backend text leaked", "Apenas usuário MASTER ativo" not in page.inner_html("#nxModalRoot"))
        page.close()

        # ---------- 51: duplicate-submit guard on link generation ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        dup_link_calls = []

        def slow_link(route):
            import time as _t
            dup_link_calls.append(1)
            _t.sleep(0.2)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"ok": True, "link": "https://TEST-ONLY-MOCK.example/token-c"}))
        page.route(ACCESS_LINK_EDGE_URL + "*", slow_link)
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.eval_on_selector("#maConfirmYes", "el => { el.click(); el.click(); }")
        page.wait_for_timeout(500)
        check("51: duplicate-submit guard (exactly 1 call despite 2 clicks)", len(dup_link_calls) == 1)
        page.close()

        # ==================== Painel Master Phase PM-4B.4 ====================
        # Human UAT decision: user detail must open as a MODAL over the
        # current list context -- the SAME UX class of fix already
        # Human-approved for Auditoria at PM-4B.3 -- never render below a
        # long user list forcing a scroll. Gate 24 A-R. Administrative-
        # action availability/eligibility (K/L) and link generation/copy
        # (M/N) are already proven above (tests 45-51), now exercised
        # entirely through this same modal -- not duplicated here.
        MANY_USERS = [dict(USERS[3], id="mu%d" % i, nome="Usuario Massa %d" % i, email_auth="massa%d@example.com" % i)
                      for i in range(60)]
        LONG_NAME_USER = dict(USERS[3], id="ulong",
                               nome="Usuário Com Nome Extremamente Longo Para Teste De Quebra De Linha No Modal De Detalhe",
                               email_auth="usuario.com.email.consideravelmente.longo.para.teste.de.responsividade@example.com")

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": MANY_USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        last_key = MANY_USERS[-1]["id"]
        page.eval_on_selector(f".maTable tbody tr[data-key='{last_key}']", "el => el.scrollIntoView()")
        scroll_before = page.evaluate("window.scrollY")
        page.eval_on_selector(f".maTable tbody tr[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        check("A: clicking a user opens a real modal (role=dialog, aria-modal=true)",
              page.eval_on_selector("#maudModalDialog", "el => el.getAttribute('role') === 'dialog' && el.getAttribute('aria-modal') === 'true'"))
        check("B: the correct user (last of 60, not a re-sorted/wrong one) is shown", MANY_USERS[-1]["nome"] in page.inner_text("#maudModalDialog"))
        check("C: the detail is NOT rendered below the list itself (single canonical presentation, below-list surface retired)",
              "maDetailField" not in page.inner_html("#maPanel"))
        check("C: #maPanel itself is completely unaffected by opening the modal (list still intact)", "maTable" in page.inner_html("#maPanel"))
        scroll_after_open = page.evaluate("window.scrollY")
        check("D: opening the modal does not scroll/jump the page position", abs(scroll_after_open - scroll_before) < 2)

        # E/F: closing via the X preserves scroll and fully clears the modal
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        scroll_after_close = page.evaluate("window.scrollY")
        check("E: closing the modal preserves the exact same list scroll position", abs(scroll_after_close - scroll_before) < 2)
        check("F: the X/Fechar button closes the modal", page.inner_html("#nxModalRoot").strip() == "")

        # G: Esc closes
        page.eval_on_selector(f".maTable tbody tr[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("G: Esc closes the modal", page.inner_html("#nxModalRoot").strip() == "")

        # H: backdrop click closes; clicking inside the dialog never does
        page.eval_on_selector(f".maTable tbody tr[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalBackdrop", "el => el.click()")
        page.wait_for_timeout(150)
        check("H: clicking the backdrop closes the modal", page.inner_html("#nxModalRoot").strip() == "")
        page.eval_on_selector(f".maTable tbody tr[data-key='{last_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalDialog", "el => el.click()")
        page.wait_for_timeout(150)
        check("H: clicking INSIDE the dialog (not the backdrop) never closes it", page.inner_html("#nxModalRoot").strip() != "")

        # I/J: focus management (dialog from the H check above is still open)
        check("I: focus enters the dialog on open", page.evaluate("document.activeElement && document.activeElement.id") == "maudModalDialog")
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        check("J: focus returns to the exact trigger row on close, never left on <body>",
              page.evaluate("document.activeElement && document.activeElement.getAttribute('data-key')") == last_key)
        page.close()

        # O/P: a generated link disappears once the WHOLE modal closes
        # (not just the link panel's own Fechar), and reopening the SAME
        # user never resurrects a stale link merely from lingering
        # frontend state.
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, CONVITES))
        page.route(ACCESS_LINK_EDGE_URL + "*", json_route(200, {"ok": True, "link": "https://TEST-ONLY-MOCK.example/token-op"}))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(100)
        page.click("#maGenerateLinkBtn")
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(200)
        check("O: link generated and visible before closing", "maGeneratedLinkInput" in page.inner_html("#nxModalRoot"))
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        check("O: generated link fully gone once the modal itself closes", page.inner_html("#nxModalRoot").strip() == "")
        page.eval_on_selector(".maTable tbody tr[data-key='u4']", "el => el.click()")
        page.wait_for_timeout(150)
        check("P: reopening the SAME user never resurrects the stale link merely from lingering frontend state",
              "maGeneratedLinkInput" not in page.inner_html("#nxModalRoot") and "TEST-ONLY-MOCK" not in page.inner_html("#nxModalRoot"))
        page.close()

        # Q/R: mobile modal + long name/e-mail never clip
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [LONG_NAME_USER], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maTable')", timeout=5000)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        page.eval_on_selector(".maMobileCard[data-key='ulong']", "el => el.click()")
        page.wait_for_timeout(150)
        check("Q: mobile modal opens correctly (role=dialog) for a card click",
              page.eval_on_selector("#maudModalDialog", "el => el.getAttribute('role') === 'dialog'"))
        modal_text_mobile = page.inner_text("#maudModalDialog")
        check("R: long name fully present in the mobile modal, not truncated", LONG_NAME_USER["nome"] in modal_text_mobile)
        check("R: long e-mail fully present in the mobile modal, not truncated", LONG_NAME_USER["email_auth"] in modal_text_mobile)
        no_overflow_mobile_modal = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        check("R: no BODY horizontal overflow with the long-content mobile modal open", no_overflow_mobile_modal)
        # R: the dialog's own box must not be forced wider than itself by
        # an unbroken long value (a real bug found during this Phase's own
        # screenshot check -- flexbox's default min-width:auto let a long
        # e-mail overflow .maDetailValue and widen the whole dialog,
        # clipping it at the right edge; same defect class as PM-4B.2,
        # different mechanism -- fixed via min-width:0 + overflow-wrap).
        dialog_self_overflow = page.evaluate("""() => {
            const d = document.querySelector('.maudModalDialog');
            return d.scrollWidth > d.clientWidth + 1;
        }""")
        check("R: the modal dialog itself never grows wider than its own box from a long e-mail (real clipping check, not just presence-in-DOM)", not dialog_self_overflow)
        page.close()

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Users Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
