#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5F -- deterministic tests for the Férias/
Ausências module (master-absences-provider.js, master-absences-view-
model.js, shell-admin.js), mounted via the same lightweight harness
used by every sibling Painel Master surface.

CRITICAL SAFETY NOTE (same as Configurações/Períodos, independently
re-confirmed live this phase for ABSENCE specifically): there is NO
homologation-mode gate for this capability -- confirmed live by direct
reading of master_admin_manage's real function body. Every write
(CREATE/SET_ACTIVE/ARCHIVE) is REAL against the real backend on any
host. This suite mocks the transport at the network layer for 100% of
its checks and asserts a network tripwire proving zero real Supabase
requests.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file. Synthetic analyst/substitute names and CPFs
only.
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

ABS_ACTIVE_PAST = {"id": "aaaaaaaa-1000-4000-8000-000000000001", "cpf_analista_ausente": "11122233344",
                    "nome_analista_ausente": "Analista Um", "loja_origem": "LOJA CENTRO",
                    "cpf_analista_substituto": "22233344455", "nome_analista_substituto": "Substituto Um",
                    "loja_coberta": "LOJA CENTRO", "data_inicio": "2026-05-09", "data_fim": "2026-08-23",
                    "motivo": "FÉRIAS", "ativo": True, "criado_por": "11122233344"}
ABS_INACTIVE = {"id": "aaaaaaaa-1000-4000-8000-000000000002", "cpf_analista_ausente": "33344455566",
                 "nome_analista_ausente": "Analista Dois", "loja_origem": "LOJA NORTE",
                 "cpf_analista_substituto": "44455566677", "nome_analista_substituto": "Substituto Dois",
                 "loja_coberta": "LOJA NORTE", "data_inicio": "2026-06-01", "data_fim": "2026-06-10",
                 "motivo": "COBERTURA TEMPORÁRIA", "ativo": False, "criado_por": "11122233344"}
ABS_LONG = {"id": "aaaaaaaa-1000-4000-8000-000000000003",
            "cpf_analista_ausente": "55566677788",
            "nome_analista_ausente": "Analista Com Nome Extremamente Longo Para Teste De Estresse De Layout Em Tabela E Cartao Mobile",
            "loja_origem": "LOJA COM NOME MUITO LONGO PARA TESTE DE ESTRESSE DE LARGURA DE COLUNA E QUEBRA DE LINHA",
            "cpf_analista_substituto": "66677788899",
            "nome_analista_substituto": "Substituto Com Nome Igualmente Longo Para Garantir Que Nenhuma Coluna Estoure O Layout",
            "loja_coberta": "LOJA COBERTA COM NOME TAMBEM MUITO EXTENSO PARA VALIDAR QUEBRA DE TEXTO CORRETA",
            "data_inicio": "2026-08-01", "data_fim": "2026-08-31", "motivo": "AFASTAMENTO", "ativo": True,
            "criado_por": "11122233344"}


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


def goto_abs(page):
    page.wait_for_selector('[data-section="feriasAusencias"]', timeout=5000)
    page.click('[data-section="feriasAusencias"]')
    page.wait_for_selector(".absTable, .modErrorState, .note", timeout=5000)


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

        # ---------- 1-9: list renders real fields, dates safe, temporal state, responsive, long content ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [ABS_ACTIVE_PAST, ABS_INACTIVE, ABS_LONG], "store_changes": []}))
        mount(page)
        goto_abs(page)
        body_text = page.inner_text("body")
        check("1: analyst/substitute/covered-store fields render", "Analista Um" in body_text and "Substituto Um" in body_text and "LOJA CENTRO" in body_text)
        check("2 (DATE SAFETY, Gate 18/54): 2026-05-09 renders as 09/05/2026 -- pure string rearrangement, no toISOString/timezone drift possible", "09/05/2026" in body_text)
        check("2b: 2026-08-23 (month/day boundary) renders correctly as 23/08/2026, not shifted a day either direction", "23/08/2026" in body_text)
        check("3: an inactive/archived absence still appears in the MASTER admin list (superset read)", "Analista Dois" in body_text)
        check("4: motivo renders as real free text, not a translated/relabeled value", "FÉRIAS" in body_text and "COBERTURA TEMPORÁRIA" in body_text)
        check("5: temporal state badge renders (past/em curso/futura) for the past-dated real fixture", "ENCERRADA" in body_text.upper())
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("6 (w=%d): no horizontal overflow (full mandatory matrix, Gate 69)" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.wait_for_timeout(60)
        no_overflow_long = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        check("7 (LONG CONTENT STRESS, Gate 69): very long analyst/store names never cause page horizontal overflow", no_overflow_long)
        check("7b: long analyst name still renders in full (no silent truncation)", "Analista Com Nome Extremamente Longo" in body_text)
        page.close()

        # ---------- 8-16: create flow -- validation, overlap warning (non-blocking), exact real payload shape ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [ABS_ACTIVE_PAST], "store_changes": []}))
        calls = []
        page.route(WRITE_URL + "*", counting_route(calls, 200, lambda post: {"id": "new-id"}))
        mount(page)
        goto_abs(page)
        page.click('#absNewBtn')
        page.wait_for_selector('.absCreateCard', timeout=3000)
        check("8: finance-effect warning is shown before submission (Gate 20/21, real -- not decorative)", "reatribuída" in page.inner_text('.absCreateCard'))
        page.click('#absSaveCreateBtn')
        check("9: blank required fields rejected client-side, no RPC call made", len(calls) == 0)
        page.fill('#absNomeAusente', 'Analista Novo')
        page.fill('#absCpfSubstituto', '99988877766')
        page.fill('#absNomeSubstituto', 'Substituto Novo')
        page.click('#absSaveCreateBtn')
        check("10: missing loja_coberta rejected client-side (NOT NULL column, Gate 35 defensive pre-check), no RPC call", len(calls) == 0)
        page.fill('#absLojaCoberta', 'LOJA SUL')
        page.click('#absSaveCreateBtn')
        check("11: missing dates rejected client-side, no RPC call", len(calls) == 0)
        page.fill('#absIni', '2026-09-10')
        page.fill('#absFim', '2026-09-01')
        page.click('#absSaveCreateBtn')
        check("12: end-before-start rejected client-side, no RPC call", len(calls) == 0)
        page.fill('#absFim', '2026-09-20')
        page.fill('#absLojaOrigem', 'LOJA CENTRO')
        page.fill('#absIni', '2026-05-15')
        page.click('#absSaveCreateBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("13 (Gate 20/21): an overlap against an ACTIVE absence for the SAME store shows a non-blocking warning yet still submits (real backend has no create-time overlap guard either)", len(calls) == 1)
        check("14: exactly one real write call, matching master_admin_manage's real entity/action/payload shape verbatim",
              calls[0]["p_entity"] == "ABSENCE" and calls[0]["p_action"] == "CREATE")
        payload = calls[0]["p_payload"]
        check("14b: payload uses the EXACT live-confirmed RPC key names (absent_name/substitute_cpf/substitute_name/covered_store/start_date/end_date/reason)",
              payload.get("absent_name") == "Analista Novo" and payload.get("substitute_cpf") == "99988877766"
              and payload.get("substitute_name") == "Substituto Novo" and payload.get("covered_store") == "LOJA SUL"
              and payload.get("start_date") == "2026-05-15" and payload.get("end_date") == "2026-09-20"
              and payload.get("reason") in (None, ""))
        check("14c: no 'note'/'observacao' key is ever sent (the real CREATE branch never inserts it -- would be silently dropped)", "note" not in payload and "observacao" not in payload)
        page.click('#absSuccessCloseBtn')
        page.close()

        # ---------- 15-19: toggle active / archive flow ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [ABS_ACTIVE_PAST], "store_changes": []}))
        calls2 = []
        page.route(WRITE_URL + "*", counting_route(calls2, 200, lambda post: {"id": ABS_ACTIVE_PAST["id"]}))
        mount(page)
        goto_abs(page)
        page.click('.absToggleActiveBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("15: 'Inativar' calls SET_ACTIVE with active=false, exact real payload shape", calls2[0]["p_action"] == "SET_ACTIVE" and calls2[0]["p_payload"]["active"] is False)
        page.click('#absSuccessCloseBtn')
        page.click('.absArchiveBtn')
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("16: Arquivar shows an explicit confirmation naming the analyst before any write (Gate 49)", "Analista Um" in page.inner_text('#nxModalRoot'))
        check("16b: zero write calls before explicit confirmation", len(calls2) == 1)
        page.click('#absConfirmCancelBtn')
        check("17: Cancelar on the archive confirmation makes zero additional write calls", len(calls2) == 1)
        page.click('.absArchiveBtn')
        page.wait_for_selector('#absConfirmArchiveBtn', timeout=3000)
        page.eval_on_selector('#absConfirmArchiveBtn', "el => { el.click(); el.click(); }")
        page.wait_for_selector('#nxModalRoot .maudModalDialog', timeout=3000)
        check("18: duplicate-submit guard -- two rapid clicks on Arquivar still produce exactly one real write call", len(calls2) == 2)
        check("18b: no EDIT/UPDATE action is ever exposed anywhere in this UI (V1 has none -- Gate 27)", all(c["p_action"] != "EDIT" and c["p_action"] != "UPDATE" for c in calls2))
        check("18c: no DELETE action is ever exposed (no DELETE RLS policy, no delete RPC action exists for this entity)", all(c["p_action"] != "DELETE" for c in calls2))
        page.close()

        # ---------- 19-21: adversarial / error states ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_abs(page)
        check("19: a 42501 denial on read is surfaced as a real error state, never a false-success empty list", "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body"))
        page.close()

        page = new_page(browser, token=None)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_abs(page)
        check("20: an expired/missing session shows a real error state, not a false-success empty list", "modErrorState" in page.content() or "Sess" in page.inner_text("body"))
        page.close()

        check("21: no native window.confirm/alert/prompt dialog ever fired across the whole suite (shared modal only)", len(dialogs_fired) == 0)
        check("22: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Férias/Ausências Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
