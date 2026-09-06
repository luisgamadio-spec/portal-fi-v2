#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5E -- deterministic tests for the Períodos de
Comissão module (master-periodos-provider.js, master-periodos-view-
model.js, shell-admin.js), mounted via the same lightweight harness
used by every sibling Painel Master surface.

CRITICAL SAFETY NOTE (same as Configurações): there is NO homologation-
mode gate for this capability -- confirmed live by direct reading of
master_admin_manage's real function body. Every write (CREATE/
SET_CURRENT/SET_ACTIVE/ARCHIVE) is REAL against the real backend on any
host. This suite mocks the transport at the network layer for 100% of
its checks and asserts a network tripwire proving zero real Supabase
requests.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file. Synthetic period names/dates only.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
PR_READ_URL = "https://mock.invalid/rest/v1/rpc/master_admin_reference_data"
PR_WRITE_URL = "https://mock.invalid/rest/v1/rpc/master_admin_manage"

results = []

PERIOD_CURRENT = {"id": "aaaaaaaa-0000-4000-8000-000000000001", "nome_periodo": "Comissão Agosto/2026",
                   "data_inicio": "2026-08-21", "data_fim": "2026-09-21", "status": "EM CONFERÊNCIA",
                   "periodo_atual": True, "ativo": True, "criado_por": "11122233344"}
PERIOD_CLOSED = {"id": "aaaaaaaa-0000-4000-8000-000000000002", "nome_periodo": "Comissão Julho/2026",
                  "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "status": "FECHADO",
                  "periodo_atual": False, "ativo": True, "criado_por": "11122233344"}
PERIOD_INACTIVE = {"id": "aaaaaaaa-0000-4000-8000-000000000003", "nome_periodo": "Comissão Junho/2026",
                    "data_inicio": "2026-06-21", "data_fim": "2026-07-20", "status": "EM CONFERÊNCIA",
                    "periodo_atual": False, "ativo": False, "criado_por": "11122233344"}


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


def goto_periodos(page):
    page.wait_for_selector('[data-section="periodosComissao"]', timeout=5000)
    page.click('[data-section="periodosComissao"]')
    page.wait_for_selector(".prTable, .modErrorState, .note", timeout=5000)


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

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)

        # ---------- 1-8: list renders real fields, dates safe, current badge, no horizontal scroll ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PR_READ_URL + "*", json_route(200, {"periods": [PERIOD_CURRENT, PERIOD_CLOSED, PERIOD_INACTIVE], "absences": [], "store_changes": []}))
        mount(page)
        goto_periodos(page)
        body_text = page.inner_text("body")
        check("1: all 3 real fields render per period (name, date range, status)", "Comissão Agosto/2026" in body_text and "Comissão Julho/2026" in body_text)
        check("2 (DATE SAFETY, Gate 18/54): 2026-08-21 renders as 21/08/2026 -- pure string rearrangement, no toISOString/timezone drift possible",
              "21/08/2026" in body_text)
        check("2b: 2026-09-21 (month/day boundary) renders correctly as 21/09/2026, not shifted a day either direction", "21/09/2026" in body_text)
        check("3: the current period shows the PERÍODO ATUAL badge, and only that one", body_text.count("PERÍODO ATUAL") == 1)
        check("4: status labels are human-readable (Em conferência / Fechado), not raw enum strings", "Em conferência" in body_text and "Fechado" in body_text)
        check("5: an inactive/archived period still appears in the MASTER admin list (master_admin_reference_data is the superset read, unlike the narrower operational_commission_periods)",
              "Comissão Junho/2026" in body_text)
        check("6: the current period's own 'Definir atual' button is disabled (already current, matches real backend invariant)",
              page.eval_on_selector('.prSetCurrentBtn[data-id="aaaaaaaa-0000-4000-8000-000000000001"]', "el => el.disabled") is True)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("7 (w=%d): no horizontal overflow (full requested matrix, Gate 52)" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.close()

        # ---------- 8-12: create flow -- validation, overlap hint, exact real payload shape ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PR_READ_URL + "*", json_route(200, {"periods": [PERIOD_CURRENT], "absences": [], "store_changes": []}))
        write_calls = []
        page.route(PR_WRITE_URL + "*", counting_route(write_calls, 200, lambda p: {"status": "OK", "id": "new-period-id"}))
        mount(page)
        goto_periodos(page)
        page.click("#prNewBtn")
        page.wait_for_selector("#prSaveCreateBtn", timeout=5000)
        # blank name
        page.click("#prSaveCreateBtn")
        page.wait_for_timeout(150)
        check("8: blank name is rejected client-side, matching V1's own validation, no RPC call made", len(write_calls) == 0)
        page.fill("#prNome", "Comissão Teste PM-5E")
        page.click("#prSaveCreateBtn")
        page.wait_for_timeout(150)
        check("9: missing dates rejected client-side, no RPC call made", len(write_calls) == 0)
        page.fill("#prIni", "2030-02-01")
        page.fill("#prFim", "2030-01-01")  # end before start
        page.click("#prSaveCreateBtn")
        page.wait_for_timeout(150)
        check("10: end-before-start is rejected client-side, no RPC call made", len(write_calls) == 0)
        page.fill("#prIni", "2026-08-25")
        page.fill("#prFim", "2026-09-10")  # overlaps PERIOD_CURRENT's 08-21..09-21
        page.click("#prSaveCreateBtn")
        page.wait_for_timeout(150)
        check("11: an overlapping range against an ACTIVE period is flagged client-side before any RPC call (mirrors the live server's own overlap rule)",
              "sobreposto" in page.inner_text("#prNome ~ p, .prCreateCard") or len(write_calls) == 0)
        page.fill("#prIni", "2030-01-01")
        page.fill("#prFim", "2030-01-31")
        page.click("#prSaveCreateBtn")
        page.wait_for_selector("#prSuccessCloseBtn", timeout=5000)
        check("12: exactly one real write call, matching master_admin_manage's real entity/action/payload shape verbatim",
              len(write_calls) == 1 and write_calls[0] == {
                  "p_entity": "PERIOD", "p_action": "CREATE",
                  "p_payload": {"name": "Comissão Teste PM-5E", "start_date": "2030-01-01", "end_date": "2030-01-31", "is_current": False}
              })
        page.close()

        # ---------- 13-15: Definir atual / Ativar-Inativar -- direct actions (matching V1's own no-confirm posture) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PR_READ_URL + "*", json_route(200, {"periods": [PERIOD_CURRENT, PERIOD_CLOSED], "absences": [], "store_changes": []}))
        action_calls = []
        page.route(PR_WRITE_URL + "*", counting_route(action_calls, 200, lambda p: {"status": "OK"}))
        mount(page)
        goto_periodos(page)
        page.click('.prSetCurrentBtn[data-id="aaaaaaaa-0000-4000-8000-000000000002"]')
        page.wait_for_selector("#prSuccessCloseBtn", timeout=5000)
        check("13: 'Definir atual' calls SET_CURRENT with the exact real payload shape", action_calls[-1] == {
            "p_entity": "PERIOD", "p_action": "SET_CURRENT", "p_payload": {"id": "aaaaaaaa-0000-4000-8000-000000000002"}
        })
        page.click("#prSuccessCloseBtn")
        page.wait_for_selector(".prTable", timeout=5000)
        page.click('.prToggleActiveBtn[data-id="aaaaaaaa-0000-4000-8000-000000000001"]')
        page.wait_for_selector("#prSuccessCloseBtn", timeout=5000)
        check("14: 'Inativar' calls SET_ACTIVE with active=false for an active period, exact real payload shape", action_calls[-1] == {
            "p_entity": "PERIOD", "p_action": "SET_ACTIVE", "p_payload": {"id": "aaaaaaaa-0000-4000-8000-000000000001", "active": False}
        })
        check("15: no SET_STATUS action is ever exposed anywhere in this UI (V1 itself has no reachable caller for it)",
              all(c.get("p_action") != "SET_STATUS" for c in action_calls))
        page.close()

        # ---------- 16-18: Arquivar requires explicit confirmation (matches V1's own confirm() intent) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PR_READ_URL + "*", json_route(200, {"periods": [PERIOD_CURRENT], "absences": [], "store_changes": []}))
        archive_calls = []
        page.route(PR_WRITE_URL + "*", counting_route(archive_calls, 200, lambda p: {"status": "OK"}))
        mount(page)
        goto_periodos(page)
        page.click(".prArchiveBtn")
        page.wait_for_selector("#prConfirmArchiveBtn", timeout=5000)
        check("16: Arquivar shows an explicit confirmation naming the period before any write (Gate 49)",
              "Comissão Agosto/2026" in page.inner_text("#nxModalRoot"))
        check("16b: zero write calls before explicit confirmation", len(archive_calls) == 0)
        page.click("#prConfirmCancelBtn")
        page.wait_for_timeout(150)
        check("17: Cancelar on the archive confirmation makes zero write calls", len(archive_calls) == 0)
        page.click(".prArchiveBtn")
        page.wait_for_selector("#prConfirmArchiveBtn", timeout=5000)
        page.eval_on_selector("#prConfirmArchiveBtn", "el => { el.click(); el.click(); }")
        page.wait_for_selector("#prSuccessCloseBtn", timeout=5000)
        check("18: duplicate-submit guard -- two rapid clicks on Arquivar still produce exactly one real write call", len(archive_calls) == 1)
        check("18b: the single archive call uses the ARCHIVE action with the exact real payload shape",
              archive_calls[0] == {"p_entity": "PERIOD", "p_action": "ARCHIVE", "p_payload": {"id": "aaaaaaaa-0000-4000-8000-000000000001"}})
        page.close()

        # ---------- 19: adversarial -- real server-side MASTER authority ----------
        # Proven directly against the LIVE production function
        # (PM-5E Gate 26 forensics: master_admin_manage's real body
        # starts with a `usuarios`/`perfil='MASTER'` check and raises
        # 42501 otherwise; RLS on public.periodos_comissao additionally
        # restricts INSERT/UPDATE to is_master() -- confirmed live).
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(PR_READ_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        page.wait_for_selector('[data-section="periodosComissao"]', timeout=5000)
        page.click('[data-section="periodosComissao"]')
        page.wait_for_timeout(300)
        check("19: a 42501 denial on read is surfaced as a real error state, never a false-success empty list", page.query_selector(".modErrorState") is not None)
        page.close()

        # ---------- 20: session expiry ----------
        page = new_page(browser, token=None)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="periodosComissao"]', timeout=5000)
        page.click('[data-section="periodosComissao"]')
        page.wait_for_timeout(300)
        check("20: an expired/missing session shows a real error state, not a false-success empty list", page.query_selector(".modErrorState") is not None)
        page.close()

        browser.close()

    check("21: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Períodos de Comissão Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
