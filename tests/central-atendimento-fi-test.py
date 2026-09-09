#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CA-1 -- deterministic regression proving Central de Atendimento F&I's V2
implementation matches the real V1 functional contract (portal-
financiamento-brabus-secure, index.html:1620-1753) AND the real, live
backend contract (yacqlelpzchcotgngwbh, proven this Wave via read-only
pg_get_functiondef/information_schema queries, wrapped in BEGIN...
ROLLBACK -- see docs/CHANGE-PROPOSAL-CENTRAL-ATENDIMENTO-FI.md) --
fails closed on every RPC failure mode, never a silent/fake status.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project
touched, 0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_central-atendimento-fi-harness.html"
LISTAR_ANALISTAS_URL = "https://mock.invalid/rest/v1/rpc/gestor_listar_analistas_fi"
LISTAR_HISTORICO_URL = "https://mock.invalid/rest/v1/rpc/gestor_listar_historico_atendimentos_fi"
SALVAR_ANALISTA_URL = "https://mock.invalid/rest/v1/rpc/gestor_salvar_analista_fi"
ALTERAR_STATUS_URL = "https://mock.invalid/rest/v1/rpc/gestor_alterar_status_analista_fi"
ENCERRAR_EXPEDIENTE_URL = "https://mock.invalid/rest/v1/rpc/gestor_encerrar_expediente_fi"

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


# Real column shape confirmed live this Wave (information_schema.columns
# against analistas_fi/historico_atendimentos_fi) -- not invented.
ANALISTAS = [
    {"id": "a1", "nome": "Ana Silva", "cpf_normalizado": "11111111111", "whatsapp": "5511999990001", "teams_link": None,
     "status": "ONLINE", "online": True, "ocupado": False, "ativo": True, "atendimentos_hoje": 3, "ordem_fila": 1,
     "ultimo_atendimento": "2026-09-07T12:00:00.000Z", "ultimo_status_em": "2026-09-07T09:00:00.000Z"},
    {"id": "a2", "nome": "Bruno Costa", "cpf_normalizado": "22222222222", "whatsapp": "5511999990002", "teams_link": "https://teams/b",
     "status": "OCUPADO", "online": True, "ocupado": True, "ativo": True, "atendimentos_hoje": 5, "ordem_fila": 2,
     "ultimo_atendimento": "2026-09-07T11:00:00.000Z", "ultimo_status_em": "2026-09-07T10:00:00.000Z"},
    {"id": "a3", "nome": "Carla Dias", "cpf_normalizado": "33333333333", "whatsapp": "5511999990003", "teams_link": None,
     "status": "OFFLINE", "online": False, "ocupado": False, "ativo": False, "atendimentos_hoje": 0, "ordem_fila": 3,
     "ultimo_atendimento": None, "ultimo_status_em": None},
]
HISTORICO = [
    {"id": "h1", "criado_em": "2026-09-07T12:00:00.000Z", "origem": "SIMULADOR_FI", "canal": "WHATSAPP", "cpf_vendedor": "44444444444",
     "nome_vendedor": "Vendedor Um", "loja_vendedor": "ABC", "analista_id": "a1", "cpf_analista": "11111111111", "nome_analista": "Ana Silva",
     "status_atendimento": "ABERTO", "iniciado_em": "2026-09-07T12:00:00.000Z", "finalizado_em": None, "observacao": None},
    {"id": "h2", "criado_em": "2026-09-06T09:00:00.000Z", "origem": "SIMULADOR_FI", "canal": "WHATSAPP", "cpf_vendedor": "55555555555",
     "nome_vendedor": "Vendedor Dois", "loja_vendedor": "ALPHAVILLE", "analista_id": "a2", "cpf_analista": "22222222222", "nome_analista": "Bruno Costa",
     "status_atendimento": "ABERTO", "iniciado_em": "2026-09-06T09:00:00.000Z", "finalizado_em": None, "observacao": None},
]


def new_page(browser, token="mock-access-token-abc", width=1366, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.add_init_script(auth_mock_script(token))
    return page


def route_defaults(page, analistas=None, historico=None):
    page.route(LISTAR_ANALISTAS_URL + "*", json_route(200, ANALISTAS if analistas is None else analistas))
    page.route(LISTAR_HISTORICO_URL + "*", json_route(200, HISTORICO if historico is None else historico))


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_CENTRAL_ATENDIMENTO_FI_PAGE")
    page.evaluate("window.NX_CENTRAL_ATENDIMENTO_FI_PAGE.render(document.getElementById('caOutlet'))")


def wait_states(page, analistas_state="READY", historico_state="READY", timeout_ms=5000):
    page.wait_for_function(
        "(a) => window.NX_CENTRAL_ATENDIMENTO_FI_PAGE.getAnalistasState() === a[0] && window.NX_CENTRAL_ATENDIMENTO_FI_PAGE.getHistoricoState() === a[1]",
        arg=[analistas_state, historico_state], timeout=timeout_ms)


def click_tab(page, tab_id):
    page.click(f'[data-tab="{tab_id}"]')


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: Dashboard READY -- real KPI formulas ----------
        page = new_page(browser)
        route_defaults(page)
        mount(page)
        wait_states(page)
        check("1a: analistasState=READY, historicoState=READY on valid data", True)
        kpis = page.evaluate("[...document.querySelectorAll('.caKpiValue')].map(e => e.textContent.trim())")
        # order: Disponiveis, Online, Ocupados, Almoco, Offline/Ferias, Atendimentos hoje, Analistas ativos
        check("1b: Disponíveis KPI = 1 (V1 formula: ativo && status=ONLINE && online && !ocupado -> only a1)", kpis[0] == "1")
        check("1c: Online KPI = 1 (status=ONLINE count among ativos)", kpis[1] == "1")
        check("1d: Ocupados KPI = 1 (status=OCUPADO count among ativos)", kpis[2] == "1")
        check("1e: Almoço KPI = 0", kpis[3] == "0")
        check("1f: Offline/Férias KPI = 0 among ATIVOS (a3 is inactive, excluded from ativos-based counts)", kpis[4] == "0")
        check("1g: Atendimentos hoje KPI = 8 (3+5, inactive a3's 0 also excluded)", kpis[5] == "8")
        check("1h: Analistas ativos KPI = 2", kpis[6] == "2")
        ultimo = page.evaluate("document.querySelector('.caKpiValueSm').textContent")
        check("1i: Último atendimento shows a real formatted date (not em-dash)", "—" not in ultimo and len(ultimo.strip()) > 0)
        fila_names = page.evaluate("[...document.querySelectorAll('.caDesktopOnly table tbody tr td:first-child')].map(e => e.textContent)")
        check("1j: Fila atual panel lists real analyst names", "Ana Silva" in fila_names and "Bruno Costa" in fila_names)
        hist_names = page.evaluate("() => { const t = document.querySelectorAll('.caDesktopOnly table'); return t.length > 1 ? [...t[1].querySelectorAll('tbody tr td:nth-child(2)')].map(e => e.textContent) : []; }")
        check("1k: Últimos atendimentos panel lists real vendor names", "Vendedor Um" in hist_names)
        page.close()

        # ---------- 2: Dashboard error states ----------
        page = new_page(browser)
        page.route(LISTAR_ANALISTAS_URL + "*", lambda route: route.abort("failed"))
        page.route(LISTAR_HISTORICO_URL + "*", json_route(200, HISTORICO))
        mount(page)
        wait_states(page, analistas_state="ERROR")
        check("2a: analistas fetch failure -> ERROR state surfaced on dashboard", page.evaluate("!!document.getElementById('caDashRetry')"))
        page.close()

        # ---------- 3: fail-closed -- no access token ----------
        page = new_page(browser, token=None)
        route_defaults(page)
        mount(page)
        wait_states(page, analistas_state="ERROR", historico_state="ERROR")
        check("3: no access token (session expired) -> ERROR on both, no fallback data shown", True)
        page.close()

        # ---------- 4: fail-closed -- permission denied 42501 ----------
        page = new_page(browser)
        page.route(LISTAR_ANALISTAS_URL + "*", json_route(403, {"code": "42501", "message": "insufficient_privilege"}))
        page.route(LISTAR_HISTORICO_URL + "*", json_route(200, HISTORICO))
        mount(page)
        wait_states(page, analistas_state="ERROR")
        check("4: permission denied (42501) -> ERROR, no fallback data", True)
        page.close()

        # ---------- 5: Encerrar Expediente -- in-page confirm, never native confirm() ----------
        page = new_page(browser)
        call_log = {"analistas_calls": 0, "encerrar_calls": 0}

        def analistas_counting(route):
            call_log["analistas_calls"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(ANALISTAS))

        def encerrar_counting(route):
            call_log["encerrar_calls"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "Expediente encerrado com sucesso.", "total_alterado": 2}))

        page.route(LISTAR_ANALISTAS_URL + "*", analistas_counting)
        page.route(LISTAR_HISTORICO_URL + "*", json_route(200, HISTORICO))
        page.route(ENCERRAR_EXPEDIENTE_URL + "*", encerrar_counting)
        mount(page)
        wait_states(page)
        check("5a: no in-page confirm panel present before clicking Encerrar Expediente", page.evaluate("!document.querySelector('.caConfirm')"))
        page.click("#caDashEncerrar")
        check("5b: clicking Encerrar Expediente shows an in-page confirm panel (never native confirm())", page.evaluate("!!document.querySelector('.caConfirm')"))
        check("5c: RPC not yet called before confirming", call_log["encerrar_calls"] == 0)
        page.click("#caConfirmNo")
        check("5d: Cancelar dismisses the confirm panel without calling the RPC", page.evaluate("!document.querySelector('.caConfirm')") and call_log["encerrar_calls"] == 0)
        page.click("#caDashEncerrar")
        page.click("#caConfirmYes")
        page.wait_for_timeout(200)
        check("5e: Confirmar calls gestor_encerrar_expediente_fi exactly once", call_log["encerrar_calls"] == 1)
        check("5f: success re-fetches analistas (non-optimistic, 2 reads: mount + post-write)", call_log["analistas_calls"] == 2)
        msg = page.evaluate("document.querySelector('.caInlineMsg').textContent")
        check("5g: server success message surfaced verbatim", "sucesso" in msg.lower())
        page.close()

        # ---------- 6: Analistas tab -- roster table + exact V1 status set ----------
        page = new_page(browser)
        route_defaults(page)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        check("6a: form present in create mode (no editingId)", page.evaluate("document.querySelector('.modSectionTitle').textContent.includes('Novo analista')"))
        rows = page.evaluate("document.querySelectorAll('.caDesktopOnly table tbody tr').length")
        check("6b: roster table shows all 3 analistas (active + inactive)", rows == 3)
        statuses = page.evaluate("[...document.querySelectorAll('.caDesktopOnly table .modStatusCell')].map(e => e.textContent.trim())")
        check("6c: exact V1 status labels rendered (Online/Ocupado/Offline)", any("Online" in s for s in statuses) and any("Ocupado" in s for s in statuses) and any("Offline" in s for s in statuses))
        badges = page.evaluate("[...document.querySelectorAll('.caDesktopOnly table .modBadge')].map(e => e.textContent.trim())")
        check("6d: Ativo/Inativo badges rendered (not color-only)", "Ativo" in badges and "Inativo" in badges)
        page.close()

        # ---------- 7: create analyst -- client validation + real RPC call ----------
        page = new_page(browser)
        call_log2 = {"salvar_calls": 0, "salvar_payload": None}

        def salvar_capturing(route):
            call_log2["salvar_calls"] += 1
            call_log2["salvar_payload"] = _json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "Analista cadastrado com sucesso.", "analista_id": "a9"}))

        route_defaults(page)
        page.route(SALVAR_ANALISTA_URL + "*", salvar_capturing)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        page.click("#caFormSave")
        page.wait_for_timeout(150)
        check("7a: empty nome blocked client-side, 0 RPC calls made", call_log2["salvar_calls"] == 0)
        check("7b: client-side error message shown for empty nome", "obrigat" in page.inner_text(".caForm").lower())
        page.fill("#caFNome", "Novo Analista")
        page.fill("#caFCpf", "99999999999")
        page.fill("#caFWhatsapp", "5511999990009")
        page.click("#caFormSave")
        page.wait_for_timeout(150)
        check("7c: valid create submits exactly one RPC call", call_log2["salvar_calls"] == 1)
        check("7d: create sends p_id=null (create, not update)", call_log2["salvar_payload"]["p_id"] is None)
        check("7e: create sends normalized (digits-only) CPF/WhatsApp", call_log2["salvar_payload"]["p_cpf_normalizado"] == "99999999999" and call_log2["salvar_payload"]["p_whatsapp"] == "5511999990009")
        check("7f: success message shown, form reset to create mode", "sucesso" in page.inner_text(".caForm").lower())
        page.close()

        # ---------- 8: edit flow -- form populates, submits with real p_id ----------
        page = new_page(browser)
        call_log3 = {"payload": None}

        def salvar_capturing2(route):
            call_log3["payload"] = _json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "Analista atualizado com sucesso.", "analista_id": "a1"}))

        route_defaults(page)
        page.route(SALVAR_ANALISTA_URL + "*", salvar_capturing2)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        page.click('[data-action="edit"][data-id="a1"]')
        check("8a: Editar populates the form with the real row's own values", page.input_value("#caFNome") == "Ana Silva")
        check("8b: edit mode heading changes", "Editar" in page.evaluate("document.querySelector('.modSectionTitle').textContent"))
        page.click("#caFormSave")
        page.wait_for_timeout(150)
        check("8c: update sends the real p_id (a1), not a new record", call_log3["payload"]["p_id"] == "a1")
        page.close()

        # ---------- 9: toggle ativo -- preserves other fields, flips only ativo ----------
        page = new_page(browser)
        call_log4 = {"payload": None}

        def salvar_capturing3(route):
            call_log4["payload"] = _json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "ok"}))

        route_defaults(page)
        page.route(SALVAR_ANALISTA_URL + "*", salvar_capturing3)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        page.click('[data-action="toggle"][data-id="a1"]')
        page.wait_for_timeout(150)
        check("9a: toggle Inativar flips ativo to false", call_log4["payload"]["p_ativo"] is False)
        check("9b: toggle preserves the row's own nome/cpf unchanged (no data corruption)", call_log4["payload"]["p_nome"] == "Ana Silva" and call_log4["payload"]["p_cpf_normalizado"] == "11111111111")
        page.close()

        # ---------- 10: status modal -- change another analyst's status ----------
        page = new_page(browser)
        call_log5 = {"payload": None, "analistas_calls": 0}

        def analistas_counting2(route):
            call_log5["analistas_calls"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(ANALISTAS))

        def alterar_capturing(route):
            call_log5["payload"] = _json.loads(route.request.post_data)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "Status alterado com sucesso.", "status_atual": "OFFLINE"}))

        page.route(LISTAR_ANALISTAS_URL + "*", analistas_counting2)
        page.route(LISTAR_HISTORICO_URL + "*", json_route(200, HISTORICO))
        page.route(ALTERAR_STATUS_URL + "*", alterar_capturing)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        page.click('[data-action="status"][data-id="a1"]')
        check("10a: modal opens with all 5 V1 status options", page.evaluate("document.querySelectorAll('.caModal .paStatusBtn').length") == 5)
        check("10b: current status (Online) marked active/pressed in modal", page.evaluate("document.querySelector('.caModal .paStatusBtn[data-status=\"ONLINE\"]').getAttribute(\"aria-pressed\")") == "true")
        page.click('.caModal .paStatusBtn[data-status="OFFLINE"]')
        page.wait_for_timeout(150)
        check("10c: chooses OFFLINE -> calls gestor_alterar_status_analista_fi with correct analista_id + status", call_log5["payload"]["p_analista_id"] == "a1" and call_log5["payload"]["p_status"] == "OFFLINE")
        check("10d: modal closes and non-optimistic re-fetch happens (2 reads)", not page.evaluate("!!document.querySelector('.caModalBackdrop')") and call_log5["analistas_calls"] == 2)
        page.close()

        # ---------- 11: queue reorder -- boundary buttons disabled at edges ----------
        page = new_page(browser)
        route_defaults(page)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        first_up_disabled = page.evaluate("document.querySelectorAll('.caDesktopOnly [data-action=\"up\"]')[0].disabled")
        last_down_disabled = page.evaluate("() => { const els = document.querySelectorAll('.caDesktopOnly [data-action=\"down\"]'); return els[els.length - 1].disabled; }")
        check("11a: Mover para cima disabled on the first row", first_up_disabled)
        check("11b: Mover para baixo disabled on the last row", last_down_disabled)
        page.close()

        # ---------- 12: queue reorder -- swap sends 2 writes with swapped ordem_fila ----------
        page = new_page(browser)
        payloads = []

        def salvar_capturing4(route):
            payloads.append(_json.loads(route.request.post_data))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"sucesso": True, "mensagem": "ok"}))

        route_defaults(page)
        page.route(SALVAR_ANALISTA_URL + "*", salvar_capturing4)
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        page.click('.caDesktopOnly [data-action="down"][data-id="a1"]')
        page.wait_for_timeout(200)
        check("12a: moving a1 down issues exactly 2 salvar calls (atomic-looking swap, 2 sequential writes)", len(payloads) == 2)
        ids_moved = sorted([p["p_id"] for p in payloads])
        check("12b: the 2 writes target the swapped adjacent pair (a1, a2)", ids_moved == ["a1", "a2"])
        ordens = {p["p_id"]: p["p_ordem_fila"] for p in payloads}
        check("12c: ordem_fila values were swapped between the two rows", ordens.get("a1") == 2 and ordens.get("a2") == 1)
        page.close()

        # ---------- 13: Histórico tab -- filters (debounced, focus-preserving) + export ----------
        page = new_page(browser)
        route_defaults(page)
        mount(page)
        wait_states(page)
        click_tab(page, "historico")
        rows_before = page.evaluate("document.querySelectorAll('.caDesktopOnly table tbody tr').length")
        check("13a: histórico table shows both real rows initially", rows_before == 2)
        check("13b: Exportar Excel button present", page.evaluate("!!document.getElementById('caHistExport')"))
        page.click("#caHistLoja")
        page.type("#caHistLoja", "ALPHA", delay=30)
        check("13c: input keeps focus through debounced re-render window (no DOM replace mid-typing)", page.evaluate("document.activeElement && document.activeElement.id") == "caHistLoja")
        page.wait_for_timeout(300)
        rows_after = page.evaluate("document.querySelectorAll('.caDesktopOnly table tbody tr').length")
        check("13d: after debounce settles, Loja filter narrows to the matching row only", rows_after == 1)
        remaining_name = page.evaluate("document.querySelector('.caDesktopOnly table tbody tr td:nth-child(2)').textContent")
        check("13e: the remaining row is the correct match (Vendedor Dois / ALPHAVILLE)", remaining_name == "Vendedor Dois")
        page.close()

        # ---------- 14: empty roster / empty history states ----------
        page = new_page(browser)
        route_defaults(page, analistas=[], historico=[])
        mount(page)
        wait_states(page)
        click_tab(page, "analistas")
        check("14a: empty roster shows 'Nenhum analista encontrado.'", "Nenhum analista encontrado" in page.content())
        click_tab(page, "historico")
        check("14b: empty history shows the correct empty-state message", "Nenhum atendimento encontrado" in page.content())
        page.close()

        # ---------- 15: zero horizontal scroll + desktop/mobile table split ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            mount(page)
            wait_states(page)
            click_tab(page, "analistas")
            page.wait_for_timeout(50)
            page_ok = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"15: zero horizontal overflow @{width}px (Analistas tab)", page_ok)
            click_tab(page, "historico")
            page.wait_for_timeout(50)
            page_ok2 = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"15: zero horizontal overflow @{width}px (Histórico tab)", page_ok2)
            desktop_visible = page.evaluate("() => { const el = document.querySelector('.caDesktopOnly'); return el && getComputedStyle(el).display !== 'none'; }")
            mobile_visible = page.evaluate("() => { const el = document.querySelector('.caMobileOnly'); return el && getComputedStyle(el).display !== 'none'; }")
            if width <= 760:
                check(f"15: @{width}px mobile card renderer is the one actually shown (not a CSS-squeezed table)", mobile_visible and not desktop_visible)
            else:
                check(f"15: @{width}px desktop table is the one actually shown", desktop_visible and not mobile_visible)
            page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Central de Atendimento F&I (CA-1): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
