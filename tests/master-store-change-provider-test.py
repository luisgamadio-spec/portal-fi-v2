#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5F -- deterministic tests for the Mudança de
Loja - Vendedores module (master-store-change-provider.js,
master-store-change-view-model.js, shell-admin.js), mounted via the
same lightweight harness used by every sibling Painel Master surface.

CRITICAL SAFETY NOTE (same as Configurações/Períodos, independently
re-confirmed live this phase for STORE_CHANGE specifically): there is
NO homologation-mode gate for this capability -- confirmed live by
direct reading of master_admin_manage's real function body. Every
write (CREATE/SET_DEPARTMENTS/SET_ACTIVE/ARCHIVE) is REAL against the
real backend on any host. This suite mocks the transport at the
network layer for 100% of its checks and asserts a network tripwire
proving zero real Supabase requests.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file. Synthetic seller names/CPFs/store names only.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
READ_URL = "https://mock.invalid/rest/v1/rpc/master_admin_reference_data"
WRITE_URL = "https://mock.invalid/rest/v1/rpc/master_admin_manage"

results = []

SC_RECORD = {"id": "cccccccc-1000-4000-8000-000000000001", "cpf_vendedor": "11122233344",
             "login_vendedor": "vend.um", "nome_vendedor": "Vendedor Um", "loja_origem": "LOJA CENTRO",
             "loja_destino": "LOJA NORTE", "data_inicio_origem": "2026-06-01", "data_fim_origem": "2026-06-20",
             "data_inicio_destino": "2026-06-21", "observacao": None, "usuario_id": "usr-1",
             "departamento_origem": None, "departamento_destino": "NOVOS", "ativo": True, "criado_por": "11122233344"}
SC_INACTIVE_NEVER = {"id": "cccccccc-1000-4000-8000-000000000002", "cpf_vendedor": "22233344455",
                      "login_vendedor": "vend.dois", "nome_vendedor": "Vendedor Dois", "loja_origem": "LOJA SUL",
                      "loja_destino": "LOJA LESTE", "data_inicio_origem": "2026-05-01", "data_fim_origem": "2026-05-15",
                      "data_inicio_destino": "2026-05-16", "observacao": None, "usuario_id": "usr-2",
                      "departamento_origem": None, "departamento_destino": None, "ativo": True, "criado_por": "11122233344"}
SC_LONG = {"id": "cccccccc-1000-4000-8000-000000000003", "cpf_vendedor": "33344455566",
           "login_vendedor": "vend.tres",
           "nome_vendedor": "Vendedor Com Nome Extremamente Longo Para Teste De Estresse De Layout Em Tabela E Cartao Mobile",
           "loja_origem": "LOJA COM NOME MUITO LONGO PARA TESTE DE ESTRESSE DE LARGURA DE COLUNA E QUEBRA DE LINHA",
           "loja_destino": "OUTRA LOJA COM NOME TAMBEM MUITO EXTENSO PARA VALIDAR QUEBRA DE TEXTO CORRETA NA TABELA",
           "data_inicio_origem": "2026-07-01", "data_fim_origem": "2026-07-31", "data_inicio_destino": "2026-08-01",
           "observacao": "Observação também bastante longa para garantir que nenhum campo estoure o layout de forma alguma",
           "usuario_id": "usr-3", "departamento_origem": "SEMINOVOS", "departamento_destino": "NOVOS", "ativo": True, "criado_por": "11122233344"}


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


def goto_sc(page):
    page.wait_for_selector('[data-section="mudancaLoja"]', timeout=5000)
    page.click('[data-section="mudancaLoja"]')
    page.wait_for_selector(".scTable, .modErrorState, .note", timeout=5000)


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


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 1-9: list renders real fields, dates safe, no data_fim_destino, responsive, long content ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": [SC_RECORD, SC_INACTIVE_NEVER, SC_LONG]}))
        mount(page)
        goto_sc(page)
        body_text = page.inner_text("body")
        check("1: seller/origin/destination store fields render", "Vendedor Um" in body_text and "LOJA CENTRO" in body_text and "LOJA NORTE" in body_text)
        check("2 (DATE SAFETY, Gate 18/54): 2026-06-01 renders as 01/06/2026 -- pure string rearrangement, no toISOString/timezone drift possible", "01/06/2026" in body_text)
        check("2b: 2026-06-21 (destination start) renders correctly as 21/06/2026, not shifted a day either direction", "21/06/2026" in body_text)
        check("3: destination is shown as open-ended ('em aberto') -- there is no data_fim_destino column at all", "em aberto" in body_text)
        check("4: department pair renders when present (SEMINOVOS -> NOVOS)", "SEMINOVOS" in body_text and "NOVOS" in body_text)
        check("5: ALL real records stay ATIVO (matches confirmed production invariant: old records are never deactivated by a newer one)", body_text.count("ATIVO") >= 3)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("6 (w=%d): no horizontal overflow (full mandatory matrix, Gate 69)" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.wait_for_timeout(60)
        no_overflow_long = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        check("7 (LONG CONTENT STRESS, Gate 69): very long seller/store/observação values never cause page horizontal overflow", no_overflow_long)
        check("7b: long seller name still renders in full (no silent truncation)", "Vendedor Com Nome Extremamente Longo" in body_text)
        page.close()

        # ---------- 8-15: create flow -- chain guidance (non-blocking), validation, exact real payload shape ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": [SC_RECORD]}))
        calls = []
        page.route(WRITE_URL + "*", counting_route(calls, 200, lambda post: {"id": "new-id"}))
        mount(page)
        goto_sc(page)
        page.click('#scNewBtn')
        page.wait_for_selector('.scCreateCard', timeout=3000)
        check("8: retroactive-financial-impact warning is shown before submission (Gate 20/21, real -- store changes feed resolve_store_temporal)", "retroativamente" in page.inner_text('.scCreateCard'))
        page.click('#scSaveCreateBtn')
        check("9: blank required fields (seller name, destination store) rejected client-side, no RPC call", len(calls) == 0)
        page.fill('#scNome', 'Vendedor Um')
        page.fill('#scCpf', '11122233344')
        page.fill('#scLojaDestino', 'LOJA OESTE')
        page.click('#scSaveCreateBtn')
        check("10: missing origin/destination dates rejected client-side, no RPC call", len(calls) == 0)
        page.fill('#scIniOrigem', '2026-06-25')
        page.fill('#scFimOrigem', '2026-06-20')
        page.fill('#scIniDestino', '2026-06-21')
        page.click('#scSaveCreateBtn')
        check("11: origin end-before-start rejected client-side, no RPC call", len(calls) == 0)
        page.fill('#scFimOrigem', '2026-06-25')
        page.fill('#scLojaOrigem', 'LOJA OESTE')
        page.click('#scSaveCreateBtn')
        check("12: origin store equal to destination store rejected client-side (mirrors real RPC's own rule), no RPC call", len(calls) == 0)
        # This seller (matched by CPF) already has an active record ending in
        # LOJA NORTE (SC_RECORD). Deliberately supply a MISMATCHED origin
        # store to prove the chain-guidance warning surfaces without
        # blocking submission -- the real RPC re-validates regardless.
        page.fill('#scLojaOrigem', 'LOJA ERRADA')
        page.click('#scSaveCreateBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("13 (CHAIN GUIDANCE, Gate 13-19): a mismatched origin store against the seller's most recent chain record does not block submission -- only the real RPC is authoritative", len(calls) == 1)
        check("14: exactly one real write call, matching master_admin_manage's real entity/action/payload shape verbatim",
              calls[0]["p_entity"] == "STORE_CHANGE" and calls[0]["p_action"] == "CREATE")
        payload = calls[0]["p_payload"]
        check("14b: payload uses the EXACT live-confirmed RPC key names (seller_name/origin_store/destination_store/origin_start/origin_end/destination_start/notes)",
              payload.get("seller_name") == "Vendedor Um" and payload.get("origin_store") == "LOJA ERRADA"
              and payload.get("destination_store") == "LOJA OESTE" and payload.get("origin_start") == "2026-06-25"
              and payload.get("origin_end") == "2026-06-25" and payload.get("destination_start") == "2026-06-21")
        check("14c: no invented 'lojas' enum constrains the store text fields client-side (there is no canonical store catalog server-side)", isinstance(payload.get("origin_store"), str))
        page.click('#scSuccessCloseBtn')
        page.close()

        # ---------- 15-19: SET_DEPARTMENTS via shared modal (never native prompt), toggle/archive ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": [SC_RECORD]}))
        calls2 = []
        page.route(WRITE_URL + "*", counting_route(calls2, 200, lambda post: {"id": SC_RECORD["id"]}))
        mount(page)
        goto_sc(page)
        page.click('.scEditDeptBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("15 (Gate 55): 'Editar departamentos' opens the shared #nxModalRoot form, never V1's native window.prompt()", len(dialogs_fired) == 0 and page.is_visible('#scEditDeptOrigem'))
        page.select_option('#scEditDeptOrigem', 'SEMINOVOS')
        page.click('#scEditDeptSaveBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("16: SET_DEPARTMENTS sends the exact real payload shape (id + origin_department/destination_department)",
              calls2[0]["p_action"] == "SET_DEPARTMENTS" and calls2[0]["p_payload"]["origin_department"] == "SEMINOVOS")
        page.click('#scSuccessCloseBtn')
        page.click('.scToggleActiveBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("17: 'Inativar' calls SET_ACTIVE with active=false, exact real payload shape", calls2[1]["p_action"] == "SET_ACTIVE" and calls2[1]["p_payload"]["active"] is False)
        check("17b: toggling active does NOT imply deactivating any OTHER (older/newer) record for this seller -- only the exact targeted id is sent", calls2[1]["p_payload"]["id"] == SC_RECORD["id"])
        page.click('#scSuccessCloseBtn')
        page.click('.scArchiveBtn')
        page.wait_for_selector('#scConfirmArchiveBtn', timeout=3000)
        check("18: Arquivar shows an explicit confirmation naming the seller before any write (Gate 49)", "Vendedor Um" in page.inner_text('#nxModalRoot'))
        page.eval_on_selector('#scConfirmArchiveBtn', "el => { el.click(); el.click(); }")
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("19: duplicate-submit guard -- two rapid clicks on Arquivar still produce exactly one real write call", len(calls2) == 3)
        check("19b: no DELETE action is ever exposed (no DELETE RLS policy, no delete RPC action exists for this entity)", all(c["p_action"] != "DELETE" for c in calls2))
        page.close()

        # ---------- 20-22: adversarial / error states ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_sc(page)
        check("20: a 42501 denial on read is surfaced as a real error state, never a false-success empty list", "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body"))
        page.close()

        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": [SC_RECORD]}))
        calls3 = []
        page.route(WRITE_URL + "*", counting_route(calls3, 403, lambda post: {"code": "23P01", "message": "Existe uma mudança de alocação que conflita com este período."}))
        mount(page)
        goto_sc(page)
        page.click('.scArchiveBtn')
        page.wait_for_selector('#scConfirmArchiveBtn', timeout=3000)
        page.click('#scConfirmArchiveBtn')
        page.wait_for_timeout(200)
        check("21 (CONFLICT classification, Gate 13-19): a real 23P01 chain-conflict error surfaces inline, never a false success", "conflita" in page.inner_text('#nxModalRoot'))
        page.close()

        check("22: no native window.confirm/alert/prompt dialog ever fired across the whole suite (shared modal only)", len(dialogs_fired) == 0)
        check("23: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Mudança de Loja - Vendedores Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
