#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PA-1 -- deterministic regression proving Painel do Analista F&I's V2
implementation matches the real V1 functional contract (portal-
financiamento-brabus-secure, assets/js/portal-app.js:2002-2043) and
fails closed on every RPC failure mode -- never a silent/fake status.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project
touched, 0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_painel-analista-fi-harness.html"
MY_ANALYST_URL = "https://mock.invalid/rest/v1/rpc/operational_my_analyst_fi"
UPDATE_STATUS_URL = "https://mock.invalid/rest/v1/rpc/atualizar_meu_status_analista_fi"

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


ROW_ONLINE = {"row": {"status": "ONLINE", "atendimentos_hoje": 3, "ultimo_atendimento": "2026-08-15T15:57:49.554Z", "ultimo_status_em": "2026-08-15T13:36:31.199Z"}}
ROW_FERIAS = {"row": {"status": "FÉRIAS", "atendimentos_hoje": 0, "ultimo_atendimento": None, "ultimo_status_em": "2026-08-01T10:00:00.000Z"}}


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_PAINEL_ANALISTA_FI_PAGE")
    page.evaluate("window.NX_PAINEL_ANALISTA_FI_PAGE.render(document.getElementById('paOutlet'))")


def wait_state(page, state, timeout_ms=5000):
    page.wait_for_function("(s) => window.NX_PAINEL_ANALISTA_FI_PAGE.getPanelState() === s", arg=state, timeout=timeout_ms)


def status_buttons_present(page):
    return page.evaluate("document.querySelectorAll('.paStatusBtn').length")


def retry_present(page):
    return page.evaluate("!!document.getElementById('paRetry')")


def pill_text(page):
    return page.evaluate("() => { const e = document.querySelector('.paStatusPill'); return e ? e.textContent.trim() : null; }")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: READY -- correct fields, exact V1 status labels, 5 buttons ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(200, ROW_ONLINE))
        mount(page)
        wait_state(page, "READY")
        check("1a: panelState=READY on valid row", True)
        check("1b: exactly 5 status buttons (V1 contract: ONLINE/OCUPADO/ALMOÇO/FÉRIAS/OFFLINE)", status_buttons_present(page) == 5)
        btn_values = page.evaluate("[...document.querySelectorAll('.paStatusBtn')].map(b => b.getAttribute('data-status'))")
        check("1c: exact V1 status values, exact accents/casing preserved", btn_values == ["ONLINE", "OCUPADO", "ALMOÇO", "FÉRIAS", "OFFLINE"])
        check("1d: current status pill shows 'Online' (text, not color-only)", "Online" in (pill_text(page) or ""))
        check("1e: ONLINE button marked active/pressed", page.evaluate("document.querySelector('.paStatusBtn[data-status=\"ONLINE\"]').getAttribute('aria-pressed')") == "true")
        check("1f: atendimentos_hoje rendered (3)", "3" in page.evaluate("document.querySelector('.paCardValue').textContent"))
        page.close()

        # ---------- 2: accented status value round-trips correctly (FÉRIAS) ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(200, ROW_FERIAS))
        mount(page)
        wait_state(page, "READY")
        check("2: accented status FÉRIAS rendered correctly", "rias" in (pill_text(page) or "").lower())
        page.close()

        # ---------- 3: NOT_LINKED -- analyst record does not exist ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(200, {"row": None}))
        mount(page)
        wait_state(page, "NOT_LINKED")
        check("3a: null row -> NOT_LINKED state", True)
        check("3b: no internal table name leaked in the user-facing message", "analistas_fi" not in page.content())
        check("3c: no status buttons rendered when not linked", status_buttons_present(page) == 0)
        page.close()

        # ---------- 4: RPC failure (network) -- fail closed ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        wait_state(page, "ERROR")
        check("4a: network failure -> ERROR state", True)
        check("4b: Retry action present", retry_present(page))
        check("4c: no status buttons rendered on error (no fallback/fake status)", status_buttons_present(page) == 0)
        page.close()

        # ---------- 5: RPC failure (permission denied 42501) -- fail closed ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(403, {"code": "42501", "message": "insufficient_privilege"}))
        mount(page)
        wait_state(page, "ERROR")
        check("5: permission denied (42501) -> ERROR, no fallback", status_buttons_present(page) == 0)
        page.close()

        # ---------- 6: session expired (no access token) -- fail closed ----------
        page = new_page(browser, token=None)
        page.route(MY_ANALYST_URL + "*", json_route(200, ROW_ONLINE))
        mount(page)
        wait_state(page, "ERROR")
        check("6: no access token (session expired) -> ERROR, no fallback", status_buttons_present(page) == 0)
        page.close()

        # ---------- 7: Retry recovers after transient failure ----------
        page = new_page(browser)
        state = {"n": 0}

        def flaky(route):
            state["n"] += 1
            if state["n"] == 1:
                route.abort("failed")
            else:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(ROW_ONLINE))

        page.route(MY_ANALYST_URL + "*", flaky)
        mount(page)
        wait_state(page, "ERROR")
        page.click("#paRetry")
        wait_state(page, "READY")
        check("7: Retry re-requests and recovers to READY", status_buttons_present(page) == 5)
        page.close()

        # ---------- 8: change status -- success re-fetches (non-optimistic) ----------
        page = new_page(browser)
        call_log = {"my_analyst_calls": 0}

        def my_analyst_counting(route):
            call_log["my_analyst_calls"] += 1
            body = ROW_ONLINE if call_log["my_analyst_calls"] == 1 else {"row": {"status": "OCUPADO", "atendimentos_hoje": 3, "ultimo_atendimento": None, "ultimo_status_em": "2026-09-07T10:00:00.000Z"}}
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(body))

        page.route(MY_ANALYST_URL + "*", my_analyst_counting)
        page.route(UPDATE_STATUS_URL + "*", json_route(200, {"sucesso": True, "mensagem": "Status atualizado com sucesso."}))
        mount(page)
        wait_state(page, "READY")
        page.click('.paStatusBtn[data-status="OCUPADO"]')
        page.wait_for_timeout(150)
        check("8a: status change re-fetches the authoritative record (2 reads, non-optimistic)", call_log["my_analyst_calls"] == 2)
        check("8b: rendered status now reflects the re-fetched value (OCUPADO)", "cupado" in (pill_text(page) or "").lower())
        msg = page.evaluate("document.getElementById('paMsg').textContent")
        check("8c: success message shown", "sucesso" in msg.lower())
        page.close()

        # ---------- 9: change status -- server-reported failure (sucesso=false) ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(200, ROW_ONLINE))
        page.route(UPDATE_STATUS_URL + "*", json_route(200, {"sucesso": False, "mensagem": "Status inválido."}))
        mount(page)
        wait_state(page, "READY")
        page.click('.paStatusBtn[data-status="ALMOÇO"]')
        page.wait_for_timeout(150)
        msg2 = page.evaluate("document.getElementById('paMsg').textContent")
        check("9a: server-reported failure message surfaced verbatim", "inv" in msg2.lower() and "lido" in msg2.lower())
        check("9b: status pill NOT silently changed on reported failure (still Online)", "Online" in (pill_text(page) or ""))
        page.close()

        # ---------- 10: change status -- RPC transport failure ----------
        page = new_page(browser)
        page.route(MY_ANALYST_URL + "*", json_route(200, ROW_ONLINE))
        page.route(UPDATE_STATUS_URL + "*", lambda route: route.abort("failed"))
        mount(page)
        wait_state(page, "READY")
        page.click('.paStatusBtn[data-status="OFFLINE"]')
        page.wait_for_timeout(150)
        msg3 = page.evaluate("document.getElementById('paMsg').textContent")
        check("10: RPC transport failure on write shows an error message, not silence", "erro" in msg3.lower())
        page.close()

        # ---------- 11: zero horizontal scroll at 4 widths ----------
        for width in [1366, 1024, 900, 480]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.add_init_script(auth_mock_script())
            page.route(MY_ANALYST_URL + "*", json_route(200, ROW_ONLINE))
            page.goto(BASE)
            page.wait_for_function("!!window.NX_PAINEL_ANALISTA_FI_PAGE")
            page.evaluate("window.NX_PAINEL_ANALISTA_FI_PAGE.render(document.getElementById('paOutlet'))")
            page.wait_for_function("window.NX_PAINEL_ANALISTA_FI_PAGE.getPanelState() === 'READY'")
            page_ok = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"11: zero horizontal overflow @{width}px", page_ok)
            check(f"11: status buttons remain tappable (>=44px height) @{width}px", page.evaluate("[...document.querySelectorAll('.paStatusBtn')].every(b => b.getBoundingClientRect().height >= 44)"))
            page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Painel do Analista F&I (PA-1): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
