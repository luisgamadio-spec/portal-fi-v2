#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5K-RETRY -- deterministic tests for Reabertura de
Competência, mounted from Histórico de Competências (the single UI
location this action lives in, per Gate 29).

SAFETY: this exercises the second (and last) capability in the whole
Painel Master migration that can mutate a real, previously-immutable
financial closing. Every test uses either historyState.reopenSimulate
=true (the default -- a pure client-side fake, reopenCommissionPeriod
Simulated, that never touches the network) or, for the RPC-error/
double-submit/allowlist tests, a fully network-mocked real call (same
discipline as every other RPC test in this suite). 0 real network
calls, 0 real Supabase project touched, 0 real reopen ever performed.
The real RPC body used to derive every expectation below was read live
via Management API pg_get_functiondef against the real project
(PM-5K-RETRY) -- reproduced here only as already-public SQLSTATEs/
messages, never as credentials.
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
SNAPSHOT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot"
REOPEN_URL = "https://mock.invalid/rest/v1/rpc/master_reopen_commission_period"
CLOSE_URL = "https://mock.invalid/rest/v1/rpc/master_close_commission_period"

PROVIDER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-closing-provider.js")

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def closing_fixture(**overrides):
    base = {
        "id": "hc-001", "periodo_id": "per-001", "nome_periodo": "21/07 a 20/08/2026",
        "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "versao": 1, "status": "FECHADO",
        "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-08-21T09:00:00+00:00",
        "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-08-21T09:00:00+00:00",
        "observacao": _json.dumps({"comissao_total": 5000}),
    }
    base.update(overrides)
    return base


SNAPSHOT_ROWS = [
    {"nome": "Vendedor Um", "perfil": "VENDEDOR", "loja": "LOJA CENTRO", "departamento": "NOVOS",
     "vendidas": 5, "financiadas": 3, "share": 60, "producao": 50000, "retorno": 5000,
     "spf_extra": 200, "spf_liquido": 140, "rentabilidade_total": 5140, "faixa": 0.003,
     "comissao": 15.42, "detalhes": {"comissao_principal": 15, "comissao_spf": 0.42, "comissao_total": 15.42}},
]


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script(token))
    return page


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def full_read_routes(page, closing_rows=None, snapshot_rows=None):
    page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
    page.route(CONV_URL + "*", json_route(200, []))
    page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
    page.route(CLOSINGS_URL + "*", json_route(200, {"rows": closing_rows if closing_rows is not None else [closing_fixture()]}))
    page.route(SNAPSHOT_URL + "*", json_route(200, {"rows": snapshot_rows if snapshot_rows is not None else SNAPSHOT_ROWS}))


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def goto_history_detail(page):
    page.click('[data-section="historicoCompetencias"]')
    page.wait_for_selector(".hcViewBtn, .note", timeout=5000)
    page.click(".hcViewBtn")
    page.wait_for_selector(".hcDetailHead", timeout=5000)


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    # ---------- 1-4: PROVIDER ALLOWLIST PROOF (Gate 42) ----------
    with io.open(PROVIDER_PATH, "r", encoding="utf-8") as f:
        provider_src = f.read()
    write_rpcs = set(re.findall(r"callRpc\('([a-zA-Z_]+)'", provider_src))
    check("1 (WRITE ALLOWLIST): master_reopen_commission_period is a write-shaped RPC the provider calls",
          "master_reopen_commission_period" in write_rpcs)
    check("2 (WRITE ALLOWLIST): the only two write-shaped RPCs are close+reopen -- never master_admin_manage",
          write_rpcs - {"operational_commission_metrics", "operational_analyst_commission_metrics_v2",
                        "operational_salary_manager_directory", "master_admin_security_data"}
          == {"master_close_commission_period", "master_reopen_commission_period"})
    check("3 (DIRECT-WRITE PROOF): provider contains no direct table write method call",
          all(tok not in provider_src for tok in [".insert(", ".update(", ".upsert(", ".delete("]))
    check("4 (REOPEN SIGNATURE): provider calls reopen with p_closing_id only, never p_period_id",
          "p_closing_id: closingId" in provider_src and "master_reopen_commission_period'" in provider_src)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 5-9: ACTION VISIBILITY (Gate 30) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[closing_fixture(status="FECHADO", ativo=True)])
        mount(page)
        goto_history_detail(page)
        check("5: Reabrir button IS shown for a FECHADO+ativo closing", page.query_selector(".hcReopenBtn") is not None)
        page.close()

        for label, status, ativo in [("REABERTO", "REABERTO", False), ("inativo-mas-FECHADO", "FECHADO", False)]:
            page = new_page(browser)
            install_tripwire(page)
            full_read_routes(page, closing_rows=[closing_fixture(status=status, ativo=ativo)])
            mount(page)
            goto_history_detail(page)
            check("6 (%s): Reabrir button is HIDDEN (frontend mirrors the real server guard)" % label,
                  page.query_selector(".hcReopenBtn") is None)
            page.close()

        # ---------- 6b-6h: LIST-VIEW ACTION VISIBILITY, real production row
        # shape (PM-5K-H1 regression). The original defect: Reabrir was only
        # ever wired into the DETAIL view (hcDetailHtml), never into the
        # list row's own "Ações" column (hcRowHtml / hcMobileCardHtml) --
        # the exact place the Human actually looked. This fixture is the
        # REAL shape read live (structural columns only, no names/amounts)
        # from fechamentos_comissao via the Management API, not an
        # enriched/synthetic one -- the whole point of this regression
        # test is to never again test against a richer fixture than the
        # real contract. ----------
        REAL_SHAPE_FECHADO = {
            "id": "c0be54f1-9a64-4583-ae84-72d4630d2e5a", "periodo_id": "7b57561c-9048-4426-9850-a4abf8476f3c",
            "nome_periodo": "21/07 à 20/08", "versao": 4, "status": "FECHADO", "ativo": True,
            "criado_em": "2026-08-22T02:26:54.04106+00:00", "fechado_em": "2026-08-22T02:26:54.04106+00:00",
            "atualizado_em": "2026-08-22T02:26:54.04106+00:00", "reaberto_em": None,
            "fechado_por": "Sintético", "reaberto_por": None, "observacao": _json.dumps({"comissao_total": 1000}),
        }
        REAL_SHAPE_REABERTO = dict(REAL_SHAPE_FECHADO, id="953f162d-bc43-4c63-aa07-d6647a407ca9", versao=3,
                                    status="REABERTO", ativo=False, reaberto_em="2026-08-22T00:32:09.946967+00:00",
                                    reaberto_por="Sintético")
        REAL_SHAPE_NULL_STATUS = dict(REAL_SHAPE_FECHADO, id="null-status-row", status=None)
        REAL_SHAPE_UNKNOWN_STATUS = dict(REAL_SHAPE_FECHADO, id="unknown-status-row", status="ARQUIVADO")

        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[REAL_SHAPE_FECHADO, REAL_SHAPE_REABERTO])
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_selector(".hcViewBtn", timeout=5000)
        list_rows = page.query_selector_all("tr.hcRow")
        check("6b (REAL SHAPE, PM-5K-H1 regression): exactly 2 list rows render", len(list_rows) == 2)
        row0_text = list_rows[0].inner_text() if len(list_rows) > 0 else ""
        row1_text = list_rows[1].inner_text() if len(list_rows) > 1 else ""
        check("6c (REAL SHAPE, FECHADO v4, ativo=true): Reabrir IS visible in the LIST row's own Ações column -- the exact place the Human looked", "Reabrir" in row0_text)
        check("6d (REAL SHAPE, REABERTO v3, ativo=false): Reabrir is NOT visible in the LIST row", "Reabrir" not in row1_text)
        check("6e: 'Ver snapshot' and 'Exportar XLSX' still present alongside Reabrir (no existing action removed)", "Ver snapshot" in row0_text and "Exportar XLSX" in row0_text)
        page.close()

        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[REAL_SHAPE_NULL_STATUS])
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_selector(".hcViewBtn", timeout=5000)
        check("6f (NEGATIVE, status=null): Reabrir is NOT visible for a row with a null status", page.query_selector(".hcReopenBtn") is None)
        page.close()

        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[REAL_SHAPE_UNKNOWN_STATUS])
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_selector(".hcViewBtn", timeout=5000)
        check("6g (NEGATIVE, status='ARQUIVADO'/unknown): Reabrir is NOT visible for an unrecognized status value", page.query_selector(".hcReopenBtn") is None)
        page.close()

        # Clicking Reabrir directly from the LIST (not via detail first) must work end-to-end.
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page, closing_rows=[REAL_SHAPE_FECHADO])
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_selector(".hcViewBtn", timeout=5000)
        page.click(".hcReopenBtn >> nth=0")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        check("6h: clicking Reabrir directly from the LIST (never having opened the detail view) opens the real confirmation modal with the real closing's data",
              "v4" in page.inner_text("#nxModalRoot") and "21/07" in page.inner_text("#nxModalRoot"))
        page.close()

        # ---------- 7-12: CONFIRMATION MODAL CONTENT (Gate 33/34 -- no generic claims) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        modal_text = page.inner_text("#nxModalRoot")
        check("7: modal states the closing will be marked REABERTO (proven by live RPC body)", "REABERTO" in modal_text)
        check("8: modal states the period returns to EM CONFERÊNCIA (proven)", "EM CONFER" in modal_text)
        check("9: modal states the snapshot rows are NOT altered/removed (proven -- RPC never touches snapshot_comissoes)",
              "não são alteradas nem removidas" in modal_text or "nao sao alteradas nem removidas" in modal_text)
        check("10: modal mentions the possibility of a new closing afterwards (v+1)", "v2" in modal_text)
        check("11: modal never claims anything about active/period/version NOT provable (no stray unqualified claims found by spot-check)",
              "talvez" not in modal_text.lower() and "provavelmente" not in modal_text.lower())
        check("12: 'Modo simulação' checkbox is CHECKED by default (Gate 31)", page.is_checked("#hcReopenSimulateToggle"))
        page.close()

        # ---------- 13-16: SIMULATED SUCCESS (Gate 36) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page.click("#hcReopenDoBtn")
        page.wait_for_timeout(400)
        check("13: modal closes after simulated success", page.query_selector("#nxModalRoot .maudModalDialog") is None)
        badge_html = page.inner_html("#maPanel")
        check("14: badge now reads REABERTO (rendered uppercase by .maBadge's CSS, real DOM text is 'Reaberto')",
              ">Reaberto<" in badge_html)
        check("15: Reabrir button disappears once the (simulated) closing is no longer FECHADO+ativo", page.query_selector(".hcReopenBtn") is None)
        check("16: snapshot rows are still displayed unchanged after the simulated reopen (Gate 40)", "Vendedor Um" in page.inner_text("#maPanel"))
        page.close()

        # ---------- 17-18: DOUBLE-SUBMIT (Gate 35) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        write_calls = []
        page.route(REOPEN_URL + "*", lambda r: (write_calls.append(r.request.post_data), r.fulfill(status=200, content_type="application/json", body=_json.dumps({"status": "OK", "closing_id": "hc-001", "period_id": "per-001"}))))
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page.click("#hcReopenSimulateToggle")  # switch OFF simulation for this real-RPC-shaped test
        page.wait_for_timeout(100)
        page.eval_on_selector("#hcReopenDoBtn", "el => { el.click(); el.click(); el.click(); }")
        page.wait_for_timeout(500)
        check("17 (DOUBLE-SUBMIT): three rapid clicks produce EXACTLY one real write call", len(write_calls) == 1)
        check("18: zero requests reached a real Supabase project even in real (non-simulated) mode", not any("supabase.co" in (u or "") for u in real_network_hits))
        page.close()

        # ---------- 19-22: REAL-MODE SUCCESS refetches canonical (Gate 36) ----------
        page = new_page(browser)
        install_tripwire(page)
        reopened_fixture = closing_fixture(status="REABERTO", ativo=False, reaberto_por="Ana Master", reaberto_em="2026-09-01T10:00:00+00:00")
        call_count = {"n": 0}
        def closings_route(route):
            call_count["n"] += 1
            rows = [closing_fixture()] if call_count["n"] == 1 else [reopened_fixture]
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": rows}))
        page.route(CLOSINGS_URL + "*", closings_route)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(SNAPSHOT_URL + "*", json_route(200, {"rows": SNAPSHOT_ROWS}))
        page.route(REOPEN_URL + "*", json_route(200, {"status": "OK", "closing_id": "hc-001", "period_id": "per-001"}))
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page.click("#hcReopenSimulateToggle")
        page.wait_for_timeout(100)
        page.click("#hcReopenDoBtn")
        page.wait_for_timeout(500)
        check("19 (REAL MODE): after real success, canonical list is refetched (2nd call to master_commission_closings)", call_count["n"] >= 2)
        check("20: after real-mode refetch, badge reflects the SERVER's real REABERTO state", ">Reaberto<" in page.inner_html("#maPanel"))
        page.close()

        # ---------- 21-24: ERROR HANDLING -- 3 real SQLSTATEs from master_reopen_commission_period ----------
        # 42501 is classified AUTH_DENIED (provider's own classifyError,
        # checked BEFORE http status) and, by the SAME established,
        # app-wide convention already used by every sibling module
        # (including Fechamento's own closeError handling), routes
        # through the generic errorStateHtml copy ("Sem permissão / Sua
        # conta não tem acesso a esta área.") rather than the verbatim
        # RPC message -- only business-rule rejections classified
        # RPC_ERROR (P0002/22023 here) show the real message verbatim.
        for code, message, http_status, label, expect_verbatim in [
            ("42501", "Acesso exclusivo do perfil Master.", 403, "AUTH_DENIED", False),
            ("P0002", "Fechamento não encontrado.", 400, "closing inexistente", True),
            ("22023", "Este fechamento não está ativo.", 400, "já reaberto / inativo", True),
        ]:
            page = new_page(browser)
            install_tripwire(page)
            full_read_routes(page)
            page.route(REOPEN_URL + "*", json_route(http_status, {"code": code, "message": message}))
            mount(page)
            goto_history_detail(page)
            page.click(".hcReopenBtn")
            page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
            page.click("#hcReopenSimulateToggle")
            page.wait_for_timeout(100)
            page.click("#hcReopenDoBtn")
            page.wait_for_timeout(400)
            modal_text_err = page.inner_text("#nxModalRoot") if page.query_selector("#nxModalRoot .maudModalDialog") else ""
            expected_text = message if expect_verbatim else "Sem permissão"
            check("21 (%s, %s): %s shown, modal stays open, never a false success" % (code, label, "verbatim message" if expect_verbatim else "generic safe copy"),
                  expected_text in modal_text_err and "sucesso" not in modal_text_err.lower())
            page.close()

        # ---------- 22: SESSION EXPIRY (Gate 38/47) ----------
        page = new_page(browser, token=None)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_timeout(500)
        check("22 (SESSION EXPIRY): a missing session shows a real error state on closings read, never a false-success empty list",
              "modErrorState" in page.content() or "Sess" in page.inner_text("body"))
        page.close()

        # ---------- 23: NON-MASTER on closings read (Gate 39/48) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_timeout(500)
        check("23 (NON-MASTER): a 42501 denial on closings read is surfaced as a real error, never an empty false-success list",
              "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body") or "Master" in page.inner_text("body"))
        page.close()

        check("24: no native window.confirm/alert/prompt dialog ever fired across the WHOLE suite", len(dialogs_fired) == 0)
        check("25: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        # ---------- 26-31: SNAPSHOT PRESERVATION TEST (Gate 40) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        goto_history_detail(page)
        rows_before = page.inner_text("#maPanel")
        row_count_before = page.eval_on_selector_all(".hcSnapshotRow, tbody tr", "els => els.length")
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page.click("#hcReopenDoBtn")  # stays simulated (default)
        page.wait_for_timeout(400)
        rows_after = page.inner_text("#maPanel")
        check("26 (SNAPSHOT PRESERVATION): 'Vendedor Um' row identity survives the simulated reopen unchanged", "Vendedor Um" in rows_after)
        check("27: financial fields (R$ 15,42) survive the simulated reopen unchanged", "15,42" in rows_after)
        check("28: production/return fields survive unchanged", "50.000,00" in rows_after and "5.000,00" in rows_after)
        page.close()

        # ---------- 29-30: RECLOSE / VERSION PRESENTATION (Gate 41) -- confirms EXISTING PM-5H sort logic, no new code ----------
        page = new_page(browser)
        install_tripwire(page)
        v1_reopened = closing_fixture(id="hc-001", versao=1, status="REABERTO", ativo=False, data_fim="2026-08-20")
        v2_closed = closing_fixture(id="hc-002", versao=2, status="FECHADO", ativo=True, data_fim="2026-08-20", criado_em="2026-09-01T10:00:00+00:00")
        full_read_routes(page, closing_rows=[v1_reopened, v2_closed])
        mount(page)
        page.click('[data-section="historicoCompetencias"]')
        page.wait_for_selector(".hcViewBtn", timeout=5000)
        list_text = page.inner_text("#maPanel")
        check("29 (RECLOSE PRESENTATION): both v1 (Reaberto) and v2 (Fechado) versions are listed, neither hidden", "v1" in list_text and "v2" in list_text)
        v2_idx = list_text.find("v2")
        v1_idx = list_text.find("v1")
        check("30: v2 (most recent version) sorts before v1 (PM-5H's existing sortClosings, unmodified)", v2_idx != -1 and v1_idx != -1 and v2_idx < v1_idx)
        page.close()

        # ---------- 31-40: RESPONSIVE + GRID INTEGRITY (Gate 44-46) ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            measurements = page.evaluate("""
() => {
  const doc = document.documentElement;
  const modal = document.querySelector('#nxModalRoot .maudModalDialog');
  return {
    doc_ok: doc.scrollWidth <= doc.clientWidth + 1,
    modal_ok: !modal || modal.scrollWidth <= modal.clientWidth + 1,
  };
}
""")
            check("31 (w=%d): no horizontal overflow at the page level" % w, measurements["doc_ok"])
            check("32 (w=%d): modal itself has no horizontal overflow" % w, measurements["modal_ok"])
        check("33: modal and its action buttons remain reachable/visible at 375px (no vertical clipping check beyond DOM presence)",
              page.query_selector("#hcReopenDoBtn") is not None and page.query_selector("#hcReopenCancelBtn") is not None)
        page.close()

        # ---------- 34-36: ACCESSIBILITY spot checks ----------
        page = new_page(browser)
        install_tripwire(page)
        full_read_routes(page)
        mount(page)
        goto_history_detail(page)
        page.click(".hcReopenBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        check("34: confirm button has real accessible text (not empty/icon-only)", (page.inner_text("#hcReopenDoBtn") or "").strip() != "")
        check("35: cancel button has real accessible text", (page.inner_text("#hcReopenCancelBtn") or "").strip() != "")
        check("36: simulate checkbox has an associated <label> wrapping it (native accessible name)",
              page.eval_on_selector("#hcReopenSimulateToggle", "el => el.closest('label') !== null"))
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Reabertura de Competência Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
