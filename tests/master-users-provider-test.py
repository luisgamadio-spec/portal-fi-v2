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
        detail_html = page.inner_html("#maPanel")
        check("15: CPF never rendered in full, only masked form, in the detail panel", "11111111111" not in detail_html and "***.***.**" in detail_html)
        page.click("#maCloseDetail")
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
        check("29: Enter key on a focused row opens detail (keyboard-operable, not click-only)", "maDetail" in page.inner_html("#maPanel"))
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
        confirm_html = page.inner_html("#maPanel")
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
        check("27: edit requires explicit confirmation before RPC call", "maConfirm" in page.inner_html("#maPanel"))
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
        check("14: conflict (55000) normalized, no raw backend text", "modErrorState" not in page.inner_html("#maOutlet") or "55000" not in page.inner_html("#maOutlet"))
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
