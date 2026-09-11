#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH-4C -- deterministic regression proving the Salários & Comissões
"Histórico" tab: MASTER-only presentation visibility (never the real
security boundary -- the server itself rejects non-MASTER, RH-4C live
proof), the closing selector, COMPLETE / LEGACY_PARTIAL / BROKEN
classification rendering (fail-closed for BROKEN, non-alarming warning
for LEGACY_PARTIAL), frozen operational-detail lazy loading, the
governed CSV export flow (including the export RPC's own fail-closed
BROKEN_CLOSING rejection), loading/empty/forbidden states, and zero
horizontal overflow at the 4 mandated widths.

Everything here runs against a mocked window.supabase/window.NX_AUTH_CORE
context and routed (never real) fetches -- 0 real network calls, 0 real
Supabase project touched, 0 credentials anywhere in this file. Fixture
shapes mirror the real, live-proven RPC contract (RH-4C Management-API
pg_get_functiondef reads against yacqlelpzchcotgngwbh) -- no real
employee names/CPF/salary/commission values.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/index.html"
CONFIG_SCRIPT = "window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-key', textEndpoint: null };"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def mock_client_script(perfil, status):
    return """
(function () {
  var listeners = [];
  var fakeSession = null;
  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          getSession: function () { return ok({ session: fakeSession }); },
          signInWithPassword: function () { fakeSession = { access_token: 'mock-token', user: { id: 'auth-user-1' } }; return ok({ session: fakeSession }); },
          onAuthStateChange: function (cb) { listeners.push(cb); return { data: { subscription: { unsubscribe: function () {} } } }; },
          signOut: function () { return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          if (name === 'usuario_logado_fi') return ok([{usuario_id:'u1', auth_user_id:'auth-user-1', nome:'Demo', perfil:'%s', loja:'TODAS', status:'%s', ativo:true}]);
          if (name === 'portal_modulos_permitidos') return ok(['comissoes']);
          return ok(null);
        }
      };
    }
  };
})();
""" % (perfil, status)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


PERIODS = {"rows": [{"id": "p1", "nome_periodo": "21/07 a 20/08", "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "status": "ABERTO", "periodo_atual": True, "ativo": True, "criado_por": "seed"}]}
METRICS = {"scope": {"profile": "MASTER", "departments": ["NOVOS", "SEMINOVOS"], "is_master": True, "is_director": False, "is_seller": False, "store": None},
    "period_start": "2026-07-21", "period_end": "2026-08-20", "spf_net_percent": 70, "eligibility_rule": "ACTIVE_VENDEDOR_ONLY",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR", "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "totals": {"sold_count": 128, "financed_count": 96, "share_percent": 75.0, "production_value": 4520000.55, "return_value": 231000.10, "spf_count": 40, "spf_value": 61000.0, "spf_net_value": 42700.0, "profitability_value": 273700.10},
    "rows": []}
ANALYST = {"absence_aware": True, "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False, "rows": []}
DIRECTORY = {"period_start": "2026-07-21", "period_end": "2026-08-20", "assignment_source": "ACTIVE_PORTAL_PROFILE",
    "rows": [], "ambiguous_assignments": 0, "contains_client_identity": False, "contains_personal_documents": False, "contains_operational_identifiers": False}


def route_dashboard_defaults(page):
    page.route("**/assets/js/intelligence-runtime-config.js*", lambda r: r.fulfill(status=200, content_type="application/javascript", body="/* mocked */"))
    page.route("**/rest/v1/rpc/operational_commission_periods*", json_route(200, PERIODS))
    page.route("**/rest/v1/rpc/operational_commission_metrics*", json_route(200, METRICS))
    page.route("**/rest/v1/rpc/operational_analyst_commission_metrics_v2*", json_route(200, ANALYST))
    page.route("**/rest/v1/rpc/operational_salary_manager_directory*", json_route(200, DIRECTORY))
    page.route("**/cdn.jsdelivr.net/npm/@supabase/supabase-js**", lambda r: r.abort())


def closing_row(id_, historical_detail_status):
    return {"id": id_, "periodo_id": "per-1", "nome_periodo": "21/07 a 20/08", "data_inicio": "2026-07-21",
            "data_fim": "2026-08-20", "versao": 1, "status": "FECHADO", "fechado_por": "seed-user",
            "fechado_em": "2026-08-21T00:00:00Z", "reaberto_por": None, "reaberto_em": None, "observacao": None,
            "ativo": True, "criado_por": "seed-user", "criado_em": "2026-08-21T00:00:00Z", "atualizado_em": "2026-08-21T00:00:00Z",
            "sales_batch_id": "b1", "finance_batch_id": "b2", "spf_batch_id": "b3", "snapshot_payload_hash": "hash",
            "commission_engine_version": "commission-secure-v1", "historical_detail_status": historical_detail_status}


def snapshot_row(fechamento_id, comissao, detalhes):
    return {"id": "snap-" + fechamento_id, "fechamento_id": fechamento_id, "periodo_id": "per-1",
            "nome_periodo": "21/07 a 20/08", "data_inicio": "2026-07-21", "data_fim": "2026-08-20",
            "nome": "Vendedor Demo", "perfil": "VENDEDOR", "loja": "ABC", "departamento": "NOVOS",
            "vendidas": 5, "financiadas": 3, "share": 60.0, "producao": 100000.0, "retorno": 5000.0,
            "spf_extra": 1000.0, "spf_liquido": 700.0, "rentabilidade_total": 5700.0, "faixa": "A",
            "comissao": comissao, "detalhes": detalhes, "criado_em": "2026-08-21T00:00:00Z"}


CLOSING_COMPLETE = closing_row("c-complete", "COMPLETE")
CLOSING_LEGACY = closing_row("c-legacy", None)
CLOSING_BROKEN = closing_row("c-broken", None)
CLOSINGS_ALL = {"rows": [CLOSING_COMPLETE, CLOSING_LEGACY, CLOSING_BROKEN]}

ROWS_COMPLETE = {"rows": [snapshot_row("c-complete", 500.0, {"faixa": "A"})]}
ROWS_LEGACY = {"rows": [snapshot_row("c-legacy", 300.0, {"faixa": "B"})]}
ROWS_BROKEN = {"rows": [snapshot_row("c-broken", 0, None), snapshot_row("c-broken", 0, None)]}


# RH-5C -- a real, already-frozen snapshot row can carry
# perfil='GESTOR F&I' (V1's group-wide oversight commission, one
# synthetic row per closing, loja literally 'GRUPO'). Fixture placed
# FIRST in the RPC's own return array (mirroring the real RPC's `order
# by loja, perfil, nome` -- 'GRUPO' can sort before a real store name
# alphabetically) specifically to prove the page re-sorts it to the end
# rather than trusting raw RPC order.
def gestor_fi_row(fechamento_id):
    r = snapshot_row(fechamento_id, 1200.0, {"faixa": "C"})
    r["nome"] = "Gestor Demo"
    r["perfil"] = "GESTOR F&I"
    r["loja"] = "GRUPO"
    r["departamento"] = "GESTOR F&I"
    return r


ROWS_COMPLETE_WITH_GESTOR = {"rows": [gestor_fi_row("c-complete"), snapshot_row("c-complete", 500.0, {"faixa": "A"})]}

OP_DETAIL_COMPLETE = {"completeness": "COMPLETE", "rows": [
    {"kind": "CHASSIS", "store": "ABC", "department": "NOVOS", "seller_user_id": "u1", "seller_name": "Vendedor Demo",
     "sale_date": "2026-08-01", "chassis_masked": "******T12345", "vehicle_model": "ECLIPSE CROSS", "financed": True,
     "finance_date": "2026-08-02", "sale_value": 100000.0, "financed_value": 90000.0, "return_considered": 5000.0,
     "included_in_commission": True, "operation_date": None, "operation_code": None, "bank": None, "finance_code": None,
     "optional_name": None, "spf_bruto": None, "spf_liquido": None}]}


def new_page(browser, perfil="MASTER", status="MASTER", width=1366, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script(mock_client_script(perfil, status))
    return page


def login(page, email):
    page.goto(BASE)
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'")
    page.fill("#loginEmail", email)
    page.fill("#loginPassword", "pass")
    page.click("#loginSubmit")
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTHORIZED'")


def mount(page):
    page.evaluate("location.hash = '#/salarios-comissoes'")
    page.wait_for_selector(".salPage", timeout=8000)
    page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getDashboardState() !== 'LOADING'", timeout=8000)


def open_historico(page):
    page.click('[data-view-mode="historico"]')
    page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'READY'", timeout=8000)


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: profile visibility -- MASTER sees Histórico, RH/VENDEDOR do not ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        tabs = page.evaluate("[...document.querySelectorAll('.salViewModeToggle .modTab')].map(b => b.getAttribute('data-view-mode'))")
        check("1a: MASTER sees the Atual/Histórico toggle", "historico" in tabs)
        page.close()

        for perfil, status in [("RH", "RH"), ("VENDEDOR", "NOVOS")]:
            page = new_page(browser, perfil=perfil, status=status)
            route_dashboard_defaults(page)
            login(page, perfil.lower() + "@demo.local")
            mount(page)
            tabs2 = page.evaluate("[...document.querySelectorAll('.salViewModeToggle .modTab')].map(b => b.getAttribute('data-view-mode'))")
            check(f"1b: {perfil} does not see the Histórico toggle option at all (server itself also rejects, RH-4C live proof)", "historico" not in tabs2)
            page.close()

        # ---------- 2: loading state, then closing selector populated ----------
        # RH-5B: two earlier attempts at this check were both racy under
        # system load -- a fixed 250ms network delay (RH-4D) and a
        # thread-blocking route handler (still 1/6 flaky, likely thread-
        # pool contention with the OTHER concurrent dashboard routes
        # mount() also needs). Neither relies on real determinism.
        # Replaced with JS-level Promise control: the canonical
        # provider's own listClosings() is monkey-patched (after real
        # script load, before the click) to return a Promise this test
        # holds open until AFTER the loading-state assertion runs --
        # zero network/thread timing anywhere, so there is no race left
        # to lose. The underlying claim (loadHistoryClosings() sets
        # state to LOADING and renders synchronously, BEFORE calling the
        # provider) is also directly readable in salarios-comissoes.js's
        # own source -- this assertion is runtime confirmation of that,
        # not the sole proof of it.
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        login(page, "master@demo.local")
        mount(page)
        page.evaluate("""() => {
          const real = window.NX_MASTER_COMPETENCE_HISTORY_PROVIDER;
          const orig = real.listClosings.bind(real);
          window.__rh5bRelease = null;
          real.listClosings = function () {
            return new Promise((resolve, reject) => {
              window.__rh5bRelease = () => orig().then(resolve, reject);
            });
          };
        }""")
        page.click('[data-view-mode="historico"]')
        loading_visible = page.evaluate("!!document.querySelector('.salBody .modLoadingState')")
        check("2a: a loading state is shown immediately after opening Histórico", loading_visible)
        page.evaluate("window.__rh5bRelease()")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'READY'", timeout=8000)
        options = page.evaluate("[...document.querySelectorAll('#salHistClosingSelect option')].map(o => o.value)")
        check("2b: closing selector lists all 3 real closings", set(options) >= {"c-complete", "c-legacy", "c-broken"})
        page.close()

        # ---------- 3: COMPLETE closing renders success badge + snapshot rows ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_COMPLETE))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-complete")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        badge = page.evaluate("document.querySelector('.salHistoryMeta .modBadge').textContent")
        check("3a: COMPLETE closing shows the Completo badge", badge == "Completo")
        rowName = page.evaluate("document.querySelector('.salBody .modTable tbody tr td')?.textContent")
        check("3b: snapshot row (real seller name) is rendered", rowName == "Vendedor Demo")
        exportBtn = page.evaluate("!!document.getElementById('salHistExportBtn')")
        check("3c: export button is offered for a COMPLETE closing", exportBtn)
        page.close()

        # ---------- 4: LEGACY_PARTIAL closing shows a non-alarming warning, not 'broken' wording ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_LEGACY))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-legacy")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        badge4 = page.evaluate("document.querySelector('.salHistoryMeta .modBadge').textContent")
        check("4a: LEGACY_PARTIAL closing shows the 'Histórico parcial' badge", badge4 == "Histórico parcial")
        warnText = page.evaluate("document.querySelector('.salBody .modInfoState .modStateTitle')?.textContent || ''")
        check("4b: warning text does not use alarming/corruption wording", "corromp" not in warnText.lower() and "invál" not in warnText.lower())
        rowsShown = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr').length")
        check("4c: LEGACY_PARTIAL still shows its valid snapshot rows (not hidden)", rowsShown >= 1)
        page.close()

        # ---------- 5: BROKEN closing fails closed -- no rows, no export offered ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_BROKEN))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-broken")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        badge5 = page.evaluate("document.querySelector('.salHistoryMeta .modBadge').textContent")
        check("5a: structurally broken closing shows the 'Sem integridade' badge", badge5 == "Sem integridade")
        rowsShown5 = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr').length")
        check("5b: BROKEN closing shows zero financial rows (fail closed, no misleading totals)", rowsShown5 == 0)
        exportBtn5 = page.evaluate("!!document.getElementById('salHistExportBtn')")
        check("5c: no export action is offered for a BROKEN closing", not exportBtn5)
        page.close()

        # ---------- 6: operational detail lazy load (COMPLETE) ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_COMPLETE))
        detail_calls = {"n": 0}
        def detail_handler(route):
            detail_calls["n"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(OP_DETAIL_COMPLETE))
        page.route("**/rest/v1/rpc/master_commission_operational_detail*", detail_handler)
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-complete")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        check("6a: operational detail is NOT fetched until requested", detail_calls["n"] == 0)
        page.click("#salHistOpDetailBtn")
        page.wait_for_timeout(300)
        check("6b: operational detail fetched exactly once after the button is clicked", detail_calls["n"] == 1)
        chassisShown = page.evaluate("document.body.textContent.includes('******T12345')")
        check("6c: frozen operational detail shows the real masked chassis", chassisShown)
        page.close()

        # ---------- 7: export flow -- real CSV download, no CPF column populated ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_COMPLETE))
        page.route("**/rest/v1/rpc/master_commission_snapshot_export*", json_route(200, ROWS_COMPLETE))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-complete")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        with page.expect_download() as dl_info:
            page.click("#salHistExportBtn")
        download = dl_info.value
        dl_path = download.path()
        csv_text = open(dl_path, encoding="utf-8").read()
        check("7a: export downloads a real CSV file", download.suggested_filename.endswith(".csv"))
        check("7b: exported CSV contains the real seller name", "Vendedor Demo" in csv_text)
        check("7c: exported CSV has a CPF-free header row (no CPF column ever emitted)", "CPF" not in csv_text.split("\r\n")[0])
        page.close()

        # ---------- 8: export on a structurally-inconsistent closing -> server 22023 -> BROKEN_CLOSING message, no file ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, {"rows": [CLOSING_LEGACY]}))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_LEGACY))
        page.route("**/rest/v1/rpc/master_commission_snapshot_export*", json_route(400, {"code": "22023", "message": "Exportação bloqueada: o fechamento desta competência possui um snapshot histórico inconsistente."}))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-legacy")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        page.click("#salHistExportBtn")
        page.wait_for_timeout(300)
        exportErrText = page.evaluate("document.body.textContent")
        check("8: a server-side fail-closed export rejection surfaces a clear 'blocked' message, not a silent failure", "Exportação bloqueada" in exportErrText)
        page.close()

        # ---------- 9: empty history (zero closings) ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, {"rows": []}))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        emptyText = page.evaluate("document.querySelector('.salBody .modEmptyState .modStateTitle')?.textContent || ''")
        check("9: zero closings shows a real empty state, not an error", "fechamento" in emptyText.lower())
        page.close()

        # ---------- 10: forbidden (server 42501) shows an explicit unauthorized message ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        login(page, "master@demo.local")
        mount(page)
        page.click('[data-view-mode="historico"]')
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'ERROR'", timeout=8000)
        forbiddenText = page.evaluate("document.body.textContent")
        check("10: PERMISSION_DENIED shows an explicit unauthorized message (not a generic empty/error)", "exclusivo do perfil Master" in forbiddenText)
        page.close()

        # ---------- 11: backend failure -> retry button works ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        call_state = {"fail": True}
        def flaky_closings(route):
            if call_state["fail"]:
                call_state["fail"] = False
                route.abort("failed")
            else:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_closings*", flaky_closings)
        login(page, "master@demo.local")
        mount(page)
        page.click('[data-view-mode="historico"]')
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'ERROR'", timeout=8000)
        page.click("#salHistRetry")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'READY'", timeout=8000)
        check("11: retry after a backend failure successfully loads real closings", True)
        page.close()

        # ---------- 12: zero horizontal overflow at the 4 mandated widths (page AND the table wrapper itself, RH-5C.1 Gate 37/39) ----------
        # Wider, more realistic values than ROWS_COMPLETE (RH-5C.1 root-
        # cause: the 10-column snapshot table's overflow only showed up
        # with longer real-world numbers -- e.g. a 9-digit production
        # value -- not the smaller synthetic ROWS_COMPLETE fixture,
        # which never exercised the actual failure width).
        ROWS_WIDE = {"rows": [dict(snapshot_row("c-complete", 5440.0, {"faixa": "A"}),
                                    nome="Vendedor Demo A", producao=4520000.55, retorno=231000.10,
                                    spf_liquido=42700.0, rentabilidade_total=273700.10),
                               gestor_fi_row("c-complete")]}
        for width in (1366, 1024, 900, 480):
            page = new_page(browser, width=width)
            route_dashboard_defaults(page)
            page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
            page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_WIDE))
            login(page, "master@demo.local")
            mount(page)
            open_historico(page)
            page.select_option("#salHistClosingSelect", "c-complete")
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
            page.wait_for_timeout(150)
            no_overflow = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"12: zero horizontal page overflow @{width}px (Histórico)", no_overflow)
            if width > 760:
                wrap_overflow = page.evaluate("() => { const w = document.querySelector('.salBody .modTableWrap'); return w ? w.scrollWidth <= w.clientWidth + 1 : true; }")
                check(f"12w: zero horizontal WRAPPER overflow @{width}px (Histórico snapshot table, RH-5C.1 Gate 37)", wrap_overflow)
            page.close()

        # ---------- 13: RH-5C -- a real GESTOR F&I snapshot row (V1's group-wide oversight commission) is sorted last, labeled, and never mistaken for a normal store row ----------
        page = new_page(browser)
        route_dashboard_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, CLOSINGS_ALL))
        page.route("**/rest/v1/rpc/master_commission_snapshot*", json_route(200, ROWS_COMPLETE_WITH_GESTOR))
        login(page, "master@demo.local")
        mount(page)
        open_historico(page)
        page.select_option("#salHistClosingSelect", "c-complete")
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryDetailState() === 'READY'", timeout=8000)
        names = page.evaluate("[...document.querySelectorAll('.salBody .modTable tbody tr')].map(tr => tr.children[0].textContent.trim())")
        check("13a: even though the RPC returned the Gestor F&I row FIRST, the page sorts it AFTER the seller row (matches Painel Master's own canonical PROFILE_ORDER)", len(names) == 2 and "Vendedor Demo" in names[0] and "Gestor Demo" in names[1])
        gestorRowHtml = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr')[1].outerHTML")
        check("13b: the Gestor F&I row carries a distinct 'Gestor F&I' badge next to the name", "Gestor F&amp;I</span>" in gestorRowHtml or "Gestor F&I</span>" in gestorRowHtml)
        check("13c: the Gestor F&I row has its own distinguishing CSS class (never blends into a normal row)", "salGestorFiRow" in gestorRowHtml)
        gestorLojaCell = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr')[1].children[1].textContent")
        check("13d: the raw 'GRUPO' store code is never shown bare -- it's relabeled 'Grupo', with the full group-wide explanation as a hover tooltip (kept short so it never re-widens the table)", "GRUPO" not in gestorLojaCell and gestorLojaCell.strip() == "Grupo")
        gestorLojaTitle = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr')[1].children[1].querySelector('[title]')?.getAttribute('title') || ''")
        check("13f: the group-wide scope explanation is present as a real tooltip (V1's own copy, not fabricated)", "Grupo" in gestorLojaTitle and "loja" in gestorLojaTitle.lower())
        sellerRowHtml = page.evaluate("document.querySelectorAll('.salBody .modTable tbody tr')[0].outerHTML")
        check("13e: the ordinary seller row is completely unaffected (no Gestor F&I badge/class leaks onto it)", "Gestor F&I" not in sellerRowHtml and "salGestorFiRow" not in sellerRowHtml)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Salários & Comissões Histórico Tab (RH-4C): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
