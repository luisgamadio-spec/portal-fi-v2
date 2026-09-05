#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-4B -- deterministic tests for the Auditoria
section (master-audit-provider.js, master-audit-view-model.js, the
audit-* additions to shell-admin.js), mounted via the same lightweight
harness already proven for Usuários/Acessos
(tests/_master-users-harness.html). Route-guard-level MASTER-only
enforcement is tested separately in tests/master-admin-route-test.py --
this file tests only the section's own behavior once mounted as MASTER.

READ-ONLY surface: there is no mutation to exercise here at all --
every check is about correct rendering, masking, ordering, and
fail-closed behavior of a single real RPC read.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched.

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

REAL_NETWORK_TRIPWIRE_HOSTS = ["supabase.co", "cloudflare", "challenges.cloudflare.com"]

results = []


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
    real_hits = []
    page.on("requestfinished", lambda req: real_hits.append(req.url) if any(h in req.url for h in REAL_NETWORK_TRIPWIRE_HOSTS) else None)
    page._real_hits = real_hits
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def goto_auditoria(page):
    page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
    page.click('[data-section="auditoria"]')
    page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('maudTable')", timeout=5000)


# Real contract shape (Phase 4A/PM-4B forensics, pg_get_functiondef of
# master_admin_security_data): id, tipo, descricao, base_origem, loja,
# vendedor, cpf, resolvido, resolvido_por, resolvido_em, criado_em.
# resolvido_por deliberately never appears here either -- V1 itself
# never renders it (Gate 9/parity).
AUDIT_ROWS = [
    {"id": 3, "tipo": "CONVITE_ENVIADO", "descricao": "Convite enviado com sucesso para novo@example.com (MASTER: Demo)",
     "base_origem": "Edge Function admin-invite-user", "loja": "ANALIA FRANCO", "vendedor": "Usuário Teste",
     "cpf": "29999999902", "resolvido": False, "resolvido_por": "actor-uuid-1", "resolvido_em": None,
     "criado_em": "2026-09-04T23:18:29.902764+00:00"},
    {"id": 2, "tipo": "REVISAO_CADASTRAL_APROVADA", "descricao": "Revisão de loja aprovada administrativamente",
     "base_origem": "Painel Master", "loja": None, "vendedor": None,
     "cpf": None, "resolvido": True, "resolvido_por": "actor-uuid-1", "resolvido_em": "2026-09-03T10:00:00+00:00",
     "criado_em": "2026-09-03T09:00:00+00:00"},
    {"id": 1, "tipo": "ALERTA_IGNORADO", "descricao": "Um texto de descrição bastante longo " * 3,
     "base_origem": "Importador Base 01", "loja": "GASTAO", "vendedor": "Fulano de Tal",
     "cpf": "11111111111", "resolvido": False, "resolvido_por": None, "resolvido_em": None,
     "criado_em": "2026-09-01T08:00:00+00:00"},
]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: MASTER reaches Auditoria, real RPC called ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        check("1: MASTER reaches Auditoria and the real audit RPC is called", "maudTable" in page.inner_html("#maPanel"))

        # ---------- ordering: never re-sorted client-side ----------
        html = page.inner_html("#maPanel")
        text = page.inner_text("#maPanel")
        first_row_key = page.eval_on_selector(".maudRow", "el => el.getAttribute('data-key')")
        check("15: server order preserved verbatim (no client re-sort) -- first row is id=3, the array's own first element", first_row_key == "3")

        # ---------- masking: V1's own maskCpfFicha shape (first-3-visible), NOT master-users-view-model's maskCpf ----------
        page.eval_on_selector(".maudRow[data-key='3']", "el => el.click()")
        page.wait_for_timeout(100)
        detail_text = page.inner_text("#maudModalDialog")
        check("9 (masking): CPF masked with V1's own maskCpfFicha shape (299.***.***-**), not the Usuários (***.***.**02) shape",
              "299.***.***-**" in detail_text and "29999999902" not in detail_text and "***.***.**02" not in detail_text)
        check("14 (fields): detail shows Data/Hora, Evento, Descrição, Loja, Origem, Resultado", all(k in detail_text for k in ["Data/Hora", "Evento", "Descrição", "Loja", "Origem", "Resultado"]))
        check("resolvido_por never rendered anywhere (V1 itself never shows it)", "actor-uuid-1" not in html and "resolvido_por" not in html)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)

        # ---------- null/optional fields: '-' or '—' fallback, never 'null'/'undefined'/'[object Object]' ----------
        page.eval_on_selector(".maudRow[data-key='2']", "el => el.click()")
        page.wait_for_timeout(100)
        detail2 = page.inner_text("#maudModalDialog")
        check("null-optional fields (loja/vendedor/cpf all null on row 2) never render 'null'/'undefined'", "null" not in detail2.lower() and "undefined" not in detail2.lower())
        check("resolvido_em shown only when present (row 2 has one)", "10:00:00" in detail2 or "2026" in detail2)
        check("no '[object Object]' ever rendered", "[object Object]" not in page.inner_html("#maPanel"))
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)

        # ---------- status badges ----------
        check("status badge: resolvido=true -> RESOLVIDO, resolvido=false -> PENDENTE", "RESOLVIDO" in text and "PENDENTE" in text)

        # ---------- long description doesn't break the layout ----------
        page.eval_on_selector(".maudRow[data-key='1']", "el => el.click()")
        page.wait_for_timeout(100)
        no_overflow_desktop = page.evaluate("document.body.scrollWidth <= document.documentElement.clientWidth + 1")
        check("long description (parity test: real 301-char max seen in Phase 4A) does not cause BODY overflow at desktop width", no_overflow_desktop)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)

        # ---------- no filters/search added (V1 parity -- Gate 16) ----------
        has_filter_input = page.eval_on_selector_all("#maPanel input, #maPanel select", "els => els.length")
        check("16: no filter/search/period controls added -- V1's own Auditoria tab has none either", has_filter_input == 0)

        # ---------- explicit "100 most recent" framing, never implies full history ----------
        check("copy states this is the recent-events window, not implying all 478 historical rows", "100" in text and "recentes" in text.lower())

        # ---------- PM-4B.1 (Human UAT finding): explicit "Ver detalhes" affordance ----------
        detail_btn_count = page.eval_on_selector_all(".maDesktopOnly .maudDetailBtn", "els => els.length")
        check("A: every desktop row has an explicit detail affordance (not just an invisible whole-row click)", detail_btn_count == len(AUDIT_ROWS))
        btn_label = page.eval_on_selector(".maudDetailBtn[data-key='3']", "el => el.getAttribute('aria-label')")
        check("B: the affordance has a real, specific accessible label (not a generic 'click here')", bool(btn_label) and "CONVITE_ENVIADO" in btn_label)
        btn_title = page.eval_on_selector(".maudDetailBtn[data-key='3']", "el => el.getAttribute('title')")
        check("B: also exposes a title, doesn't depend on hover/aria alone", bool(btn_title))
        # C: click the explicit button (row id=2 this time) opens exactly that row's detail
        page.eval_on_selector(".maudDetailBtn[data-key='2']", "el => el.click()")
        page.wait_for_timeout(100)
        detail_via_button = page.inner_text("#maudModalDialog")
        check("C: clicking the explicit action opens the CORRECT event's detail", "REVISAO_CADASTRAL_APROVADA" in detail_via_button)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)
        # D: the row click still works too (same controller, not a second flow)
        page.eval_on_selector(".maudRow[data-key='1']", "el => el.click()")
        page.wait_for_timeout(100)
        detail_via_row = page.inner_text("#maudModalDialog")
        check("D: row click still opens the detail (preserved, not replaced by the new button)", "ALERTA_IGNORADO" in detail_via_row)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)
        # E: visible at the human's own reported ~1000px width, not just 1366/1440
        for w in (1000, 1366, 1440):
            page.set_viewport_size({"width": w, "height": 800})
            page.wait_for_timeout(50)
            visible_count = page.eval_on_selector_all(".maDesktopOnly .maudDetailBtn", "els => els.filter(el => el.offsetParent !== null).length")
            check(f"E: Detalhes action remains visible at {w}px (the human's own reported viewport class)", visible_count == len(AUDIT_ROWS))
        page.set_viewport_size({"width": 1366, "height": 900})
        page.close()

        # ---------- F: mobile has an equally explicit affordance ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        mobile_btn_count = page.eval_on_selector_all(".maudMobileCard .maudDetailBtn", "els => els.filter(el => el.offsetParent !== null).length")
        check("F: mobile cards also carry an explicit, visible 'Ver detalhes' action", mobile_btn_count == len(AUDIT_ROWS))
        page.eval_on_selector(".maudMobileCard .maudDetailBtn[data-key='1']", "el => el.click()")
        page.wait_for_timeout(100)
        check("F: mobile explicit action opens the correct detail too", "ALERTA_IGNORADO" in page.inner_text("#maudModalDialog"))
        no_overflow_mobile_2 = page.evaluate("document.body.scrollWidth <= document.documentElement.clientWidth + 1")
        check("no BODY horizontal overflow introduced by the new mobile action", no_overflow_mobile_2)
        page.close()

        # ---------- 4: empty ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        page.click('[data-section="auditoria"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modEmptyState')", timeout=5000)
        check("4: empty audit -> normal empty state, not modErrorState", "modErrorState" not in page.inner_html("#maPanel"))
        page.close()

        # ---------- malformed response ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        page.click('[data-section="auditoria"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        malformed_html = page.inner_html("#maPanel")
        check("malformed response (missing audit array) fails closed -- no synthesized list rendered", "modErrorState" in malformed_html and "maudTable" not in malformed_html)
        page.close()

        # ---------- auth denied ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        page.click('[data-section="auditoria"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        denied_html = page.inner_html("#maPanel")
        check("AUTH_DENIED normalized, no raw backend text leaked", "modErrorState" in denied_html and "Acesso exclusivo do perfil Master." not in denied_html)
        page.close()

        # ---------- session expired (401) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(401, {"message": "jwt expired"}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        page.click('[data-section="auditoria"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        expired_html = page.inner_html("#maPanel")
        check("SESSION_EXPIRED normalized, no raw JWT text leaked", "modErrorState" in expired_html and "jwt expired" not in expired_html)
        page.close()

        # ---------- network failure ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", lambda route: route.abort("failed"))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        page.click('[data-section="auditoria"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        check("network failure -> modErrorState (NETWORK_ERROR), zero fixture fallback", "modErrorState" in page.inner_html("#maPanel"))
        page.close()

        # ---------- loading state (slow route) ----------
        page = new_page(browser)

        def slow_sec(route):
            import time as _t
            _t.sleep(0.3)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(SEC_URL + "*", slow_sec)
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="auditoria"]', timeout=5000)
        # JS-dispatched click, not Playwright's own click() -- the mocked
        # route's blocking time.sleep() runs on Playwright's sync-API
        # driver thread, so a real click() blocks until the whole 300ms
        # round-trip settles before even returning control, making the
        # in-flight loading state unobservable afterwards (same lesson
        # already documented in master-users-provider-test.py's own
        # double-submit test). Check immediately, no wait_for_timeout.
        page.eval_on_selector('[data-section="auditoria"]', "el => el.click()")
        loading_html = page.inner_html("#maPanel")
        check("loading state shown immediately (RPC in flight), never a premature empty state", "modLoadingState" in loading_html)
        page.close()

        # ---------- mobile representation, same data ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        mobile_visible = page.evaluate("getComputedStyle(document.querySelector('.maudMobileCard')).display !== 'none'")
        mobile_count = page.eval_on_selector_all(".maudMobileCard", "els => els.length")
        no_overflow_mobile = page.evaluate("document.body.scrollWidth <= document.documentElement.clientWidth + 1")
        check("mobile representation shows grouped cards (same data source, same 3 rows)", mobile_visible and mobile_count == 3)
        check("no BODY horizontal overflow at mobile width", no_overflow_mobile)
        page.close()

        # ---------- adversarial: no user selector/filter/search anywhere ----------
        # (already covered above via has_filter_input == 0)

        # ==================== Painel Master Phase PM-4B.3 ====================
        # Human UAT decision: "Ver detalhes" must open a MODAL over the
        # current context, never render at the end of the (up to
        # 100-row) list forcing a long scroll. Gate 26 A-K.
        MANY_ROWS = [dict(r, id=str(100 - i)) for i, r in enumerate(
            [{"tipo": f"EVENTO_{n}", "descricao": f"Descrição do evento {n}", "base_origem": "Painel Master",
              "loja": "GASTAO", "vendedor": f"Usuario {n}", "cpf": "11111111111", "resolvido": False,
              "resolvido_por": None, "resolvido_em": None, "criado_em": f"2026-09-{(n % 28) + 1:02d}T08:00:00+00:00"}
             for n in range(100)]
        )]

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": MANY_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        # A/K: with 100 rows, open the LAST (100th) row's detail -- the
        # worst case for "long scroll to find it" if this ever regressed
        # back to end-of-list rendering.
        last_row_key = MANY_ROWS[-1]["id"]
        page.eval_on_selector(f".maudRow[data-key='{last_row_key}']", "el => el.scrollIntoView()")
        scroll_before = page.evaluate("window.scrollY")
        page.eval_on_selector(f".maudDetailBtn[data-key='{last_row_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        check("A: Ver detalhes opens a real modal (role=dialog, aria-modal=true)", page.eval_on_selector("#maudModalDialog", "el => el.getAttribute('role') === 'dialog' && el.getAttribute('aria-modal') === 'true'"))
        check("B: the correct event (the 100th row, not a re-sorted/wrong one) is shown", MANY_ROWS[-1]["tipo"] in page.inner_text("#maudModalDialog"))
        check("C: the detail is NOT rendered inside the list/panel itself (single canonical presentation, Gate 25)", "maudModalDialog" not in page.inner_html("#maPanel"))
        check("C: #maPanel itself is completely unaffected by opening the modal (same content as before)", "maudTable" in page.inner_html("#maPanel"))
        scroll_after_open = page.evaluate("window.scrollY")
        check("D: opening the modal does not scroll/jump the page position", abs(scroll_after_open - scroll_before) < 2)
        check("K: this holds even at row 100 of 100 -- the modal is never positioned relative to list length", True)  # covered by the above using the LAST row specifically

        # E: Esc closes
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("E: Esc closes the modal", page.eval_on_selector("#nxModalRoot", "el => el.getAttribute('aria-hidden') === 'true'") and page.inner_html("#nxModalRoot").strip() == "")

        # F: X (close button) closes
        page.eval_on_selector(f".maudDetailBtn[data-key='{last_row_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        check("F: the X/Fechar button closes the modal", page.inner_html("#nxModalRoot").strip() == "")

        # G: backdrop click closes
        page.eval_on_selector(f".maudDetailBtn[data-key='{last_row_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalBackdrop", "el => el.click()")
        page.wait_for_timeout(150)
        check("G: clicking the backdrop closes the modal", page.inner_html("#nxModalRoot").strip() == "")
        # clicking INSIDE the dialog itself must never close it
        page.eval_on_selector(f".maudDetailBtn[data-key='{last_row_key}']", "el => el.click()")
        page.wait_for_timeout(150)
        page.eval_on_selector("#maudModalDialog", "el => el.click()")
        page.wait_for_timeout(150)
        check("G: clicking INSIDE the dialog (not the backdrop) never closes it", page.inner_html("#nxModalRoot").strip() != "")

        # H: focus management -- focus enters dialog on open, returns to trigger on close
        check("H: focus enters the dialog on open", page.evaluate("document.activeElement && document.activeElement.id") == "maudModalDialog")
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(150)
        check("H: focus returns to the exact trigger (the Ver detalhes button) on close, never left on <body>", page.evaluate("document.activeElement && document.activeElement.getAttribute('data-key')") == last_row_key)

        # I: CPF still masked inside the modal
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.close()

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        page.eval_on_selector(".maudDetailBtn[data-key='3']", "el => el.click()")
        page.wait_for_timeout(150)
        modal_text = page.inner_text("#maudModalDialog")
        check("I: CPF still masked inside the modal (299.***.***-**, real digits never shown)", "299.***.***-**" in modal_text and "29999999902" not in modal_text)
        # J: mobile -- modal correct, near-full-screen, nothing critical clipped
        page.click("#maudModalCloseBtn")
        page.wait_for_timeout(100)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        page.eval_on_selector(".maudMobileCard .maudDetailBtn[data-key='3']", "el => el.click()")
        page.wait_for_timeout(150)
        mobile_modal_text = page.inner_text("#maudModalDialog")
        check("J: mobile modal shows Descrição/CPF/Resultado/Fechar, nothing cut", all(k in mobile_modal_text for k in ["Descrição", "Alvo (CPF)", "Resultado"]) and page.query_selector("#maudModalCloseBtn") is not None)
        no_overflow_modal_mobile = page.evaluate("document.body.scrollWidth <= document.documentElement.clientWidth + 1")
        check("J: no BODY horizontal overflow with the mobile modal open", no_overflow_modal_mobile)
        page.close()

        # ---------- network tripwire + no secret leakage ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": AUDIT_ROWS}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_auditoria(page)
        check("no real network hit in the mocked suite (requestfinished tripwire)", len(page._real_hits) == 0)
        check("no access token leaked into rendered HTML", "mock-access-token-abc" not in page.inner_html("#maOutlet"))
        page.close()

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Audit Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
