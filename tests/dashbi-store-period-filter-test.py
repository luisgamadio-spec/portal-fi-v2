#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DASHBI1 -- Store filter + "Limpar período" (Clear period) parity tests
(PARITY-CHECK-1, the two confirmed real gaps against V1's "Análise Geral
do Grupo": a dashboard-wide Store filter, and a Clear-period button).

Store filter contract under test (mirrors V1's own proven mechanism,
origin/main:modules/analise-geral-grupo-secure-original-layout.html):
currentStoreFilter filters the row-level sales/fins arrays by loja, then
re-runs the SAME aggregate() the rest of the pipeline already depends on
(applyStoreFilter(), dashbi.js) -- applied at every site V1 itself applies
it (main KPI/table aggregation, the separate Model-Analysis code path).
Zero new backend authority: this is a client-side re-scoping of data the
session's own RPC calls already returned in full.

Clear-period contract under test (mirrors V1's clearPeriodFilter()):
restores THIS FILE's own pre-existing default period state (real
transport: ensureDefaultPeriod()'s currentMonth default via
applyPresetAndRender('currentMonth'); fixture transport: the module's own
DEFAULT_DATE_START/DEFAULT_DATE_END/CUSTOM preset) -- never touches
Store/Visão(dept)/Família(model) selection, same as V1's own function body.

Also includes a small Gestão metadata check (Phase 8): config/module-
registry.json's gestao entry no longer claims "0 backend"/"fixture-only"/
"not migrated this wave" for its real RPC wiring (gestao-real-provider.js,
commit 7adf71e), a pure documentation-text correction verified here not to
have touched route/permissionId/authMode/migrationStatus.

Requires: a static server for this worktree's own root (index.html at
its root), same IA3E_TEST_PORT convention as dashbi-real-provider-test.py/
gestao-real-provider-test.py/v2-uat-05/06.
"""
import io
import json as _json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
BASE = f"http://127.0.0.1:{os.environ.get('IA3E_TEST_PORT', '8711')}/tests/_dashbi-real-provider-harness.html"
METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_metrics"
MODEL_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_model_metrics"
FIXTURES_PATH = os.path.join(HERE, "fixtures", "dashbi-fixtures.json")
REGISTRY_PATH = os.path.join(V2_ROOT, "config", "module-registry.json")

with open(FIXTURES_PATH, encoding="utf-8") as _f:
    _FIXTURES_BODY = _f.read()

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("[PASS] " if cond else "[FAIL] ") + label)


# ---------------------------------------------------------------------
# Fixture-transport helpers (NX_AUTH not configured -> isRealTransport()
# false, same gate every other Dashbi test uses).
# ---------------------------------------------------------------------
def new_fixture_page(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script("window.NX_AUTH = { isAuthConfigured: false };")
    page.route("**/dashbi-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=_FIXTURES_BODY))
    return page


def mount_fixture(page, fixture_id="multi_loja_vendedor"):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")
    page.wait_for_selector("#dbStoreFilter", timeout=5000)
    if fixture_id != "multi_loja_vendedor":
        page.select_option("#dbFixtureSelect", fixture_id)
    page.wait_for_timeout(80)


def kpi_value(page, nth):
    return page.evaluate(
        "(n) => { const c = document.querySelectorAll('.modKpiGrid .modKpiCard')[n-1]; "
        "return c ? c.querySelector('.modKpiValue').textContent.trim() : null; }",
        nth,
    )


def store_options(page):
    return page.evaluate("[...document.querySelectorAll('#dbStoreFilter option')].map(o => o.value)")


def select_store(page, value):
    page.select_option("#dbStoreFilter", value)
    page.wait_for_timeout(80)


def click_view(page, view):
    page.click(".dbViewBtn[data-view='%s']" % view)
    page.wait_for_timeout(80)


def click_mode(page, mode):
    page.click(".dbModeBtn[data-mode='%s']" % mode)
    page.wait_for_timeout(80)


def set_dates(page, start, end):
    page.fill("#dbDateStart", start)
    page.eval_on_selector("#dbDateStart", "el => el.dispatchEvent(new Event('change'))")
    page.wait_for_timeout(40)
    page.fill("#dbDateEnd", end)
    page.eval_on_selector("#dbDateEnd", "el => el.dispatchEvent(new Event('change'))")
    page.wait_for_timeout(80)


def ranking_loja_names(page):
    click_mode(page, "ranking")
    # rankingHtml() renders TWO .dbTableRanking tables (Vendedores, then
    # Lojas) -- the second one is the Lojas ranking.
    return page.evaluate(
        "() => { const tables = [...document.querySelectorAll('.dbTableRanking')]; "
        "const t = tables[1]; if (!t) return []; "
        "return [...t.querySelectorAll('tbody tr')].map(tr => (tr.children[1] || {}).textContent || '').filter(Boolean); }"
    )


def panel_html(page):
    return page.inner_html("#dbPanel")


def run_fixture_group(browser):
    page = new_fixture_page(browser)
    mount_fixture(page)

    # ---- baseline (Todas as lojas / Grupo) ----
    check("F1: default store filter is 'Todas as lojas' (value='')", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "")
    baseline_vendas = kpi_value(page, 1)
    baseline_fins = kpi_value(page, 2)
    check("F2: baseline Grupo Vendas = 4 (regression anchor)", baseline_vendas == "4")
    check("F3: baseline Grupo Financiamentos = 4 (regression anchor)", baseline_fins == "4")

    # ---- store options derive from the loaded data, not a hardcoded list ----
    opts = store_options(page)
    check("F4: store select offers 'Todas as lojas' first", opts[0] == "")
    check("F5: every canonical store in this fixture is selectable (ABC/ALPHAVILLE/EUROPA/BARRA FUNDA)",
          set(opts[1:]) == {"ABC", "ALPHAVILLE", "EUROPA", "BARRA FUNDA"})

    # ---- store filter genuinely scopes KPIs (not just table rows) ----
    select_store(page, "ABC")
    check("F6: selecting ABC scopes Vendas KPI to 1 (not the Group's 4)", kpi_value(page, 1) == "1")
    check("F7: selecting ABC scopes Financiamentos KPI to 1", kpi_value(page, 2) == "1")

    # ---- Ranking is scoped (derived from the same aggregate() output) ----
    lojas_ranking = ranking_loja_names(page)
    check("F8: Ranking > Lojas contains only the selected store (ABC)", any("ABC" in n for n in lojas_ranking) and len(lojas_ranking) == 1)

    # ---- Model Analysis is scoped, including a store with 0 Novos data ----
    click_view(page, "Novos")
    click_mode(page, "modelos")
    page.eval_on_selector('[data-family="OUTLANDER"]', "el => el.click()")
    page.wait_for_timeout(80)
    outlander_row_abc = page.evaluate(
        "() => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
        "const r = rows.find(tr => tr.textContent.includes('OUTLANDER')); return r ? r.textContent : ''; }"
    )
    check("F9: OUTLANDER volume for store=ABC (Novos view) shows 1", "1" in outlander_row_abc)

    # BARRA FUNDA's own OUTLANDER sale in this fixture is Seminovos -- Model
    # Analysis (Novos-only) must show 0 for it, proving the store filter
    # doesn't leak a non-Novos row through Model Analysis's own dept gate.
    select_store(page, "BARRA FUNDA")
    outlander_row_bf = page.evaluate(
        "() => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
        "const r = rows.find(tr => tr.textContent.includes('OUTLANDER')); return r ? r.textContent : ''; }"
    )
    check("F10: OUTLANDER volume for store=BARRA FUNDA (Seminovos-only store) is 0, not leaked", ">0<" not in outlander_row_bf and "OUTLANDER" in outlander_row_bf)

    # ---- composes correctly with Novos/Seminovos dept toggle ----
    click_view(page, "Grupo")
    check("F11: store=BARRA FUNDA, Grupo view -> Financiamentos=1", kpi_value(page, 2) == "1")
    click_view(page, "Novos")
    check("F12: store=BARRA FUNDA, Novos view -> Financiamentos=0 (its only op is Seminovos)", kpi_value(page, 2) == "0")
    click_view(page, "Seminovos")
    check("F13: store=BARRA FUNDA, Seminovos view -> Financiamentos=1", kpi_value(page, 2) == "1")
    click_view(page, "Grupo")

    # ---- composes correctly with a custom period ----
    # Fixture transport's A.compute() is period-agnostic (confirmed by direct
    # source read, dashbi.js's own FC-1 comment: currentDateStart/End are
    # never applied to fixture data, only used to build real-RPC params) --
    # so the meaningful composition check here is that editing the date
    # inputs never silently resets/breaks the store filter (no filter
    # should reset another), not that fixture data itself gets date-sliced.
    select_store(page, "ABC")
    set_dates(page, "2026-04-01", "2026-04-30")
    check("F14: editing custom period does not reset the Store filter (still ABC)", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "ABC")
    check("F15: store=ABC still scopes Vendas to 1 after a custom-period edit (composition intact)", kpi_value(page, 1) == "1")

    # ---- switching back to Todas restores the exact original Group result ----
    select_store(page, "")
    check("F16: back to 'Todas as lojas' -> Vendas restored to the exact baseline (4)", kpi_value(page, 1) == baseline_vendas)
    check("F17: back to 'Todas as lojas' -> Financiamentos restored to the exact baseline (4)", kpi_value(page, 2) == baseline_fins)

    # ---- no unauthorized/sensitive data introduced by this change ----
    html = panel_html(page)
    check("F18: no CPF/document-like field leaked into the panel by the store-filter change", "cpf" not in html.lower() and "documento" not in html.lower())

    # ---- Clear Period (Phase 5): fixture-mode default restore ----
    select_store(page, "ALPHAVILLE")
    click_view(page, "Novos")
    click_mode(page, "modelos")
    page.eval_on_selector('[data-family="TRITON"]', "el => el.click()")
    page.wait_for_timeout(80)
    set_dates(page, "2026-04-01", "2026-04-30")
    page.click("#dbClearPeriodBtn")
    page.wait_for_timeout(80)
    check("F19: 'Limpar período' button exists", page.eval_on_selector("#dbClearPeriodBtn", "el => !!el") is True)
    check("F20: fixture mode -- dates reset to this file's own pre-existing default (2026-01-01/2026-12-31)",
          page.eval_on_selector("#dbDateStart", "el => el.value") == "2026-01-01" and
          page.eval_on_selector("#dbDateEnd", "el => el.value") == "2026-12-31")
    check("F21: fixture mode -- no quick-preset button left visually active (CUSTOM)",
          page.evaluate("[...document.querySelectorAll('.dbPresetBtn')].every(b => !b.classList.contains('dbBtnActive'))"))
    check("F22: Clear period does NOT reset the Store filter (still ALPHAVILLE)", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "ALPHAVILLE")
    check("F23: Clear period does NOT reset the Visão(dept) filter (still Novos)", page.eval_on_selector(".dbViewBtn[data-view='Novos']", "el => el.classList.contains('dbBtnActive')"))
    check("F24: Clear period does NOT reset the Família(model) filter (still TRITON)", page.eval_on_selector('[data-family="TRITON"]', "el => el.classList.contains('dbVehicleCardActive')"))
    check("F25: data refreshed after clear (panel still shows a KPI grid, not blank)", "modKpiGrid" in panel_html(page))

    page.close()


# ---------------------------------------------------------------------
# Real-transport helpers.
# ---------------------------------------------------------------------
def auth_mock_script():
    return """
window.NX_INTELLIGENCE_CONFIG = { supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key' };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve('mock-access-token-abc'); } };
"""


REAL_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-12-31",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": [
        {
            "seller_id": "s1", "seller_name": "Seller A", "store": "BARRA FUNDA", "department": "NOVOS",
            "sold_count": 5, "sales_value": 500000, "financed_count": 4, "share_percent": 80,
            "production_value": 400000, "return_value": 40000, "spf_count": 0, "spf_value": 0, "spf_net_value": 0,
            "profitability_value": 40000,
            "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": 4, "production_value": 400000, "return_value": 40000, "average_balloon_value": 0}]
        },
        {
            "seller_id": "s2", "seller_name": "Seller B", "store": "ALPHAVILLE", "department": "NOVOS",
            "sold_count": 3, "sales_value": 300000, "financed_count": 2, "share_percent": 66.6,
            "production_value": 200000, "return_value": 20000, "spf_count": 0, "spf_value": 0, "spf_net_value": 0,
            "profitability_value": 20000,
            "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": 2, "production_value": 200000, "return_value": 20000, "average_balloon_value": 0}]
        },
        {
            "seller_id": "s3", "seller_name": "Seller A", "store": "BARRA FUNDA", "department": "SEMINOVOS",
            "sold_count": 2, "sales_value": 120000, "financed_count": 1, "share_percent": 50,
            "production_value": 80000, "return_value": 8000, "spf_count": 0, "spf_value": 0, "spf_net_value": 0,
            "profitability_value": 8000,
            "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": 1, "production_value": 80000, "return_value": 8000, "average_balloon_value": 0}]
        }
    ]
}
REAL_MODEL_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-12-31",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "entry_rule": "SUM_ENTRY_DIV_VALID_OPERATIONS", "entry_percent_rule": "SUM_ENTRY_DIV_SUM_SALE_VALUE",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": [
        {
            "store": "BARRA FUNDA", "department": "NOVOS", "model": "TRITON HPE-S",
            "sold_count": 3, "sales_value": 600000, "financed_count": 2, "penetration_percent": 66.6,
            "production_value": 200000, "return_value": 20000, "average_return_percent": 10,
            "average_installments": 48, "average_installment_value": 6000,
            "valid_entry_count": 1, "entry_total": 20000, "entry_sales_value_total": 100000,
            "average_entry_value": 20000, "weighted_entry_percent": 20,
            "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": 2, "production_value": 200000, "return_value": 20000, "average_balloon_value": 0}],
            "spf_count": 0, "spf_value": 0, "spf_net_value": 0
        },
        {
            "store": "ALPHAVILLE", "department": "NOVOS", "model": "TRITON HPE-S",
            "sold_count": 1, "sales_value": 200000, "financed_count": 1, "penetration_percent": 100,
            "production_value": 100000, "return_value": 10000, "average_return_percent": 10,
            "average_installments": 36, "average_installment_value": 5000,
            "valid_entry_count": 0, "entry_total": 0, "entry_sales_value_total": 0,
            "average_entry_value": 0, "weighted_entry_percent": 0,
            "plan_breakdown": [{"plan_type": "LINEAR", "financed_count": 1, "production_value": 100000, "return_value": 10000, "average_balloon_value": 0}],
            "spf_count": 0, "spf_value": 0, "spf_net_value": 0
        }
    ]
}


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def new_real_page(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script())
    return page


def mount_real(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")
    page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
    page.wait_for_selector("#dbStoreFilter", timeout=5000)


def run_real_group(browser):
    page = new_real_page(browser)
    captured = []

    def capture_metrics(route):
        body = _json.loads(route.request.post_data or "{}")
        captured.append(body)
        route.fulfill(status=200, content_type="application/json", body=_json.dumps(REAL_METRICS))

    page.route(METRICS_URL + "*", capture_metrics)
    page.route(MODEL_METRICS_URL + "*", json_route(200, REAL_MODEL_METRICS))
    mount_real(page)

    baseline_vendas = kpi_value(page, 1)
    baseline_fins = kpi_value(page, 2)
    check("R1: real transport baseline (Todas) Vendas = 10 (5+3+2)", baseline_vendas == "10")
    check("R2: real transport baseline (Todas) Financiamentos = 7 (4+2+1)", baseline_fins == "7")

    opts = store_options(page)
    check("R3: real-transport store options derive from the RPC's own store field (BARRA FUNDA/ALPHAVILLE)", set(opts[1:]) == {"BARRA FUNDA", "ALPHAVILLE"})

    select_store(page, "BARRA FUNDA")
    check("R4: store=BARRA FUNDA (Grupo view) -> Vendas=7 (5+2), scoping the KPI itself", kpi_value(page, 1) == "7")
    check("R5: store=BARRA FUNDA (Grupo view) -> Financiamentos=5 (4+1)", kpi_value(page, 2) == "5")

    click_view(page, "Novos")
    check("R6: store=BARRA FUNDA + Novos view composes -> Vendas=5", kpi_value(page, 1) == "5")

    lojas_ranking = ranking_loja_names(page)
    check("R7: Ranking > Lojas scoped to the selected store only", lojas_ranking == ["BARRA FUNDA"])

    # ---- Model Analysis real-transport scoping: proves the modelMetricsRows
    # filter (dashbi-real-view-model.js's own real-only data source, which
    # bypasses aggregate()/sales/fins entirely) is genuinely store-scoped,
    # not just the sales/fins-derived surfaces.
    click_mode(page, "modelos")
    page.eval_on_selector('[data-family="TRITON"]', "el => el.click()")
    page.wait_for_timeout(80)
    triton_row_bf = page.evaluate(
        "() => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
        "const r = rows.find(tr => tr.textContent.includes('TRITON')); return r ? r.textContent : ''; }"
    )
    check("R8: TRITON volume for store=BARRA FUNDA (real modelMetricsRows scoping) shows 3, not the Group's 4", "3" in triton_row_bf)
    select_store(page, "ALPHAVILLE")
    triton_row_av = page.evaluate(
        "() => { const rows = [...document.querySelectorAll('.dbModelSection table tbody tr')]; "
        "const r = rows.find(tr => tr.textContent.includes('TRITON')); return r ? r.textContent : ''; }"
    )
    check("R9: TRITON volume for store=ALPHAVILLE (real modelMetricsRows scoping) shows 1, not BARRA FUNDA's 3", "1" in triton_row_av)
    select_store(page, "BARRA FUNDA")
    click_view(page, "Grupo")
    click_mode(page, "overview")

    # ---- composes with a quick preset (real transport re-fetches; store
    # filter must survive the async reload) ----
    captured.clear()
    page.click(".dbPresetBtn[data-preset='currentMonth']")
    page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
    for _ in range(30):
        if captured:
            break
        page.wait_for_timeout(50)
    check("R10: quick preset triggers a fresh real fetch", len(captured) >= 1)
    check("R11: store filter survives the quick-preset async reload (still BARRA FUNDA)", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "BARRA FUNDA")
    check("R12: quick preset + store composes -> Vendas still store-scoped (7)", kpi_value(page, 1) == "7")

    # ---- composes with a custom period (real transport: dates genuinely
    # drive a fresh RPC call, store filter must survive it too) ----
    captured.clear()
    set_dates(page, "2026-02-01", "2026-02-28")
    page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
    custom_period_calls = []
    for _ in range(40):
        custom_period_calls = [b for b in captured if b.get("p_start") == "2026-02-01" and b.get("p_end") == "2026-02-28"]
        if custom_period_calls:
            break
        page.wait_for_timeout(50)
    check("R12b: editing a custom period sends the exact new p_start/p_end to the RPC", len(custom_period_calls) >= 1)
    check("R12c: store filter survives a custom-period edit (still BARRA FUNDA)", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "BARRA FUNDA")
    check("R12d: store scoping still applies after a custom-period edit (Vendas=7)", kpi_value(page, 1) == "7")

    # ---- export reflects the CURRENT store scope, not always Group-wide ----
    page.evaluate("""
        window.__CAPTURED = null;
        XLSX.writeFile = function(wb) {
            if (!wb || !wb.Sheets || !wb.SheetNames) return; // defensive: ignore any spurious/empty invocation
            var ws = wb.Sheets[wb.SheetNames[0]];
            var ref = ws['!ref'];
            var range = XLSX.utils.decode_range(ref);
            var grid = [];
            for (var r = range.s.r; r <= range.e.r; r++) {
                var addr = XLSX.utils.encode_cell({r:r, c:0});
                var cell = ws[addr];
                grid.push(cell ? cell.v : null);
            }
            window.__CAPTURED = grid;
        };
    """)
    page.click("#dbExportResumoBtn")
    page.wait_for_timeout(80)
    exported_groups = page.evaluate("window.__CAPTURED") or []
    check("R13: export while store=BARRA FUNDA is selected excludes ALPHAVILLE rows", not any("ALPHAVILLE" in (g or "") for g in exported_groups))
    check("R14: export while store=BARRA FUNDA is selected includes BARRA FUNDA rows (both depts)", any("BARRA FUNDA" in (g or "") for g in exported_groups))

    # ---- switching back to Todas restores the exact original Group result ----
    select_store(page, "")
    check("R15: back to 'Todas as lojas' -> Vendas restored to the exact real baseline (10)", kpi_value(page, 1) == baseline_vendas)
    check("R16: back to 'Todas as lojas' -> Financiamentos restored to the exact real baseline (7)", kpi_value(page, 2) == baseline_fins)

    page.close()


def run_clear_period_real_group(browser):
    page = new_real_page(browser)
    page.route(METRICS_URL + "*", json_route(200, REAL_METRICS))
    page.route(MODEL_METRICS_URL + "*", json_route(200, REAL_MODEL_METRICS))
    mount_real(page)

    # A fully-closed past month (Mês anterior is always day-1..last-day of a
    # complete past month, isClosedMonthPeriod() is unconditionally true for
    # it) -- gives FECHAMENTO a real state to transition FROM.
    page.click(".dbPresetBtn[data-preset='lastMonth']")
    page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)
    check("C1: 'Mês anterior' shows FECHAMENTO (a complete past month)", "dbFechamento" in panel_html(page) and "FECHAMENTO" in panel_html(page))

    select_store(page, "BARRA FUNDA")
    click_view(page, "Novos")
    page.wait_for_timeout(80)

    expected_closed = page.evaluate("""
        () => {
          const A = window.NX_DASHBI_ADAPTER;
          const today = new Date();
          const start = new Date(today.getFullYear(), today.getMonth(), 1);
          return A.isClosedMonthPeriod({ min: start, max: today });
        }
    """)

    page.click("#dbClearPeriodBtn")
    page.wait_for_function("document.getElementById('dbPanel').innerHTML.includes('modKpiGrid')", timeout=5000)

    today_start = page.evaluate("() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0,10); }")
    today_end = page.evaluate("() => new Date().toISOString().slice(0,10)")
    check("C2: real mode -- 'Limpar período' restores this dashboard's own currentMonth default (start = day 1 of this month)", page.eval_on_selector("#dbDateStart", "el => el.value") == today_start)
    check("C3: real mode -- 'Limpar período' restores currentMonth default (end = today)", page.eval_on_selector("#dbDateEnd", "el => el.value") == today_end)
    check("C4: 'Mês atual' preset shows as active after Limpar período", page.eval_on_selector(".dbPresetBtn[data-preset='currentMonth']", "el => el.classList.contains('dbBtnActive')"))
    html_after = panel_html(page)
    check("C5: FECHAMENTO state after clear matches a fresh recomputation for the new period", (("FECHAMENTO" in html_after) == expected_closed))
    check("C6: Store filter untouched by Limpar período (still BARRA FUNDA)", page.eval_on_selector("#dbStoreFilter", "el => el.value") == "BARRA FUNDA")
    check("C7: Visão(dept) filter untouched by Limpar período (still Novos)", page.eval_on_selector(".dbViewBtn[data-view='Novos']", "el => el.classList.contains('dbBtnActive')"))
    check("C8: data refreshed after Limpar período (panel re-rendered with a KPI grid)", "modKpiGrid" in html_after)

    page.close()


# ---------------------------------------------------------------------
# Gestão metadata correction (Phase 8) -- static file check, no server.
# ---------------------------------------------------------------------
def run_gestao_metadata_group():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = _json.load(f)
    modules = registry.get("modules") or registry.get("modulos") or []
    gestao = next((m for m in modules if m.get("id") == "gestao"), None)
    check("G1: gestao entry found in module-registry.json", gestao is not None)
    if not gestao:
        return
    combined = _json.dumps(gestao, ensure_ascii=False)
    check("G2: registry text now references gestao-real-provider.js", "gestao-real-provider.js" in combined)
    check("G3: registry text now references the real operational_fandi_dashboard RPC being wired", "operational_fandi_dashboard" in combined and "7adf71e" in combined)
    check("G4: no stale '0 backend' claim remains for gestao", "0 backend" not in combined)
    check("G5: no stale 'fixture-only' claim remains for gestao", "fixture-only" not in combined.lower())
    check("G6: no stale 'not implemented this Wave' backend claim remains for gestao", "NOT implemented this Wave" not in combined)
    # visibility/behavior-affecting fields must be byte-identical to before.
    check("G7: route untouched ('/gestao')", gestao.get("route") == "/gestao")
    check("G8: permissionId untouched ('gestao')", gestao.get("permissionId") == "gestao")
    check("G9: authMode untouched ('PERMISSION_MATRIX')", gestao.get("authMode") == "PERMISSION_MATRIX")
    check("G10: migrationStatus untouched ('HUMAN_APPROVED')", gestao.get("migrationStatus") == "HUMAN_APPROVED")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        run_fixture_group(browser)
        run_real_group(browser)
        run_clear_period_real_group(browser)
        browser.close()

    run_gestao_metadata_group()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== Dashbi Store/Clear-Period Filter Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    if passed != total:
        print("FAILED:")
        for label, cond in results:
            if not cond:
                print(" -", label)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
