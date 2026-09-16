#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SALSHARE1 -- manager consolidated row Share/Conversão regression.

CONFIRMED DEFECT (Human UAT, real example): the GERENTE consolidated
row in Equipe (e.g. "ABC · NOVOS", manager "RICARDO SILVA COSTA")
always showed Conversão/Share as a hardcoded '—', even when a real
official Analyst Share exists for that exact store this period. Root
cause: trailingRowDesktopHtml() hardcoded the literal '—' for that
column, and trailingCardHtml() didn't render a Share element at all --
neither ever consulted the already-loaded, already-authoritative
Analyst Share (analystConversionPercent(), the SAME canonical formula
already used on the Analyst's own row, RH-5F.1B) that the module had
sitting in `dashboard.analystMetrics.rows` the whole time.

FIX (assets/js/salarios-comissoes.js): a manager row's displayed Share
is now the OFFICIAL Analyst's own Share (officialAnalystShareForStore,
new) for that SAME store this period -- matched by store only (Gate
20: Analyst commission is store-wide, never department-specific,
pre-existing/unchanged rule) and "official" meaning !r.transfer (the
exact same idiom ownAnalystFaixaMatch already uses elsewhere in this
file to distinguish an Analyst's own row from an absence-coverage
substitute). No new RPC, no new Share calculation -- reuses the exact
already-approved value the Analyst's own row already displays. When no
official row exists for that store, shareValue is null and
conversionCellHtml renders it as '—', unchanged from before -- never a
fabricated 0,0%.

TEST A proves the fill-in works for a store with a real official
Analyst row, AND that every other manager-row field (% Comissão,
Comissão Total, Vendidas, Financiadas, Produção, Retorno, SPF
Líquido, Rentabilidade) matches the exact value the fixture's own
faixa/totals inputs dictate -- i.e. this change has ZERO effect on
manager commission, only fills in the previously-empty Share cell.
TEST B proves the '—' fallback is preserved when no official row
exists for that store. (The pre-fix-vs-post-fix "before == after"
proof itself was performed once, manually, outside this permanent
suite -- see the SALSHARE1 wave report -- since mutating the actual
source file inside a committed regression test would be unsafe.)

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port; start/stop it externally.
"""
import io
import json as _json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(("[PASS] " if cond else "[FAIL] ") + label + (f" -- {detail}" if detail is not None and not cond else ""))


INSTALL_STUB_JS = """
(() => {
  window.__uatFakeSession = null;
  window.__uatPendingProfile = null;
  window.NX_INTELLIGENCE_CONFIG = Object.assign({}, window.NX_INTELLIGENCE_CONFIG, {
    mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null
  });
  window.NX_AUTH = {
    isAuthConfigured: true,
    getSession: () => Promise.resolve(window.__uatFakeSession),
    signIn: () => { window.__uatFakeSession = { user: { id: (window.__uatPendingProfile || {}).authUserId } }; return Promise.resolve(); },
    signOut: () => { window.__uatFakeSession = null; return Promise.resolve(); },
    resolveAuthorizedProfile: () => Promise.resolve(window.__uatPendingProfile),
    resolveAllowedModules: () => Promise.resolve(['comissoes']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

USER_MASTER = {"userId": "row-salshare1", "authUserId": "AUTHUSER-SALSHARE1", "nome": "UAT MASTER SALSHARE1", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}

ONE_PERIOD = {"rows": [{
    "id": "p1-salshare1", "nome_periodo": "21/08 à 20/09", "data_inicio": "2026-08-21",
    "data_fim": "2026-09-20", "status": "EM CONFERÊNCIA", "periodo_atual": True, "ativo": True
}]}

# Store ABC/NOVOS has a real official (non-transfer) Analyst row:
# sold=10, financed=6 -> 60.0% (>=40% threshold -> success badge).
# Store XYZ/NOVOS has a seller+manager but ZERO analyst rows at all
# (the store simply never appears in analystByStore) -- proves the
# fallback stays '-' rather than fabricating a value.
METRICS = {"rows": [
    {"store": "ABC", "department": "NOVOS", "seller_id": "seller-1", "seller_name": "VENDEDOR ABC",
     "sold_count": 5, "financed_count": 3, "share_percent": 60.0,
     "production_value": 100000.0, "return_value": 8000.0, "spf_net_value": 500.0, "profitability_value": 1500.0},
    {"store": "XYZ", "department": "NOVOS", "seller_id": "seller-2", "seller_name": "VENDEDOR XYZ",
     "sold_count": 4, "financed_count": 2, "share_percent": 50.0,
     "production_value": 60000.0, "return_value": 4000.0, "spf_net_value": 300.0, "profitability_value": 900.0},
], "totals": {}}

ANALYST_METRICS = {"rows": [
    {"store": "ABC", "analyst_name": "ANALISTA OFICIAL ABC", "sold_count": 10, "financed_count": 6,
     "production_value": 200000.0, "return_value": 15000.0, "spf_value": 1000.0, "transfer": False, "coverage_id": None}
    # XYZ intentionally has NO analyst row at all.
]}

MANAGER_DIRECTORY = {"rows": [
    {"store": "ABC", "department": "NOVOS", "manager_name": "RICARDO SILVA COSTA"},
    {"store": "XYZ", "department": "NOVOS", "manager_name": "MANAGER XYZ"}
]}

FAIXA_ROWS = {"rows": [
    {"perfil": "GERENTE", "store": "ABC", "department": "NOVOS", "faixa_level": "INTERMEDIARIA", "faixa": 0.10, "comissao_total": 1234.56},
    {"perfil": "GERENTE", "store": "XYZ", "department": "NOVOS", "faixa_level": "MINIMA", "faixa": 0.05, "comissao_total": 321.00}
]}

EMPTY_ROWS = {"rows": []}
GESTOR_FI_EMPTY = {"pronto": False}


def route_json(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def route_salary_rpcs(page):
    page.route("**/rest/v1/rpc/operational_commission_periods*", route_json(200, ONE_PERIOD))
    page.route("**/rest/v1/rpc/operational_commission_metrics*", route_json(200, METRICS))
    page.route("**/rest/v1/rpc/operational_analyst_commission_metrics_v2*", route_json(200, ANALYST_METRICS))
    page.route("**/rest/v1/rpc/operational_salary_manager_directory*", route_json(200, MANAGER_DIRECTORY))
    page.route("**/rest/v1/rpc/operational_portal_config*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_gestor_fi_commission*", route_json(200, GESTOR_FI_EMPTY))
    page.route("**/rest/v1/rpc/operational_commission_faixa_rows*", route_json(200, FAIXA_ROWS))


def login_as(page, profile):
    page.evaluate(
        "(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('uat@test.invalid', 'x', 'uat-captcha'); }",
        profile
    )
    page.wait_for_function(
        "(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id",
        arg=profile["authUserId"], timeout=5000
    )


def open_salary(page):
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=8000)
    page.evaluate(INSTALL_STUB_JS)
    login_as(page, USER_MASTER)
    page.wait_for_function("!!window.NX_ROUTER && !!window.NX_SALARIOS_COMISSOES_PAGE", timeout=8000)
    page.evaluate("() => window.NX_ROUTER.navigate('salarios-comissoes')")
    page.wait_for_selector(".salPage", timeout=5000)
    page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getDashboardState() === 'READY'", timeout=8000)
    page.wait_for_timeout(300)


def manager_row_cells(page, manager_name):
    """Desktop .salManagerRow cell texts, in column order, for the row
    matching manager_name (Vendedor|Vendidas|Financiadas|Conversão|
    Produção|Retorno|SPF Líq.|Rentabilidade|% Comissão|Comissão Total)."""
    row = page.locator(".salManagerRow", has_text=manager_name).first
    cells = row.locator("td")
    return [cells.nth(i).inner_text().strip() for i in range(cells.count())]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================================================================
        # TEST A -- ABC/NOVOS: real official Analyst Share (60.0%) must
        # now appear on RICARDO SILVA COSTA's manager row, using the
        # same badge/format rules as every other Conversão cell.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_salary_rpcs(page)
        open_salary(page)
        abc_cells = manager_row_cells(page, "RICARDO SILVA COSTA")
        check("A1: manager row found for RICARDO SILVA COSTA", len(abc_cells) > 0, abc_cells)
        if abc_cells:
            check("A2: Conversão cell shows the official Analyst Share (60,0%)", abc_cells[3] == "60,0%", abc_cells)
            check("A3: not the old hardcoded '—'", abc_cells[3] != "—", abc_cells)
            badge_cls = page.locator(".salManagerRow", has_text="RICARDO SILVA COSTA").first.locator("td").nth(3).locator(".modBadge").get_attribute("class")
            check("A4: >=40% uses the success badge class (same rule as seller/Analyst rows)", "modBadgeSuccess" in (badge_cls or ""), badge_cls)
            # Commission-integrity proof (Step 5): every OTHER field on
            # this exact row must match precisely what the fixture's own
            # totals/faixa inputs dictate -- this change touches ONLY the
            # Conversão cell (index 3), nothing else in the row.
            check("A5: Vendidas unchanged (sumGroupTotals of the ABC seller row)", abc_cells[1] == "5", abc_cells)
            check("A6: Financiadas unchanged", abc_cells[2] == "3", abc_cells)
            check("A7: Produção unchanged (R$ 100.000,00)", abc_cells[4] == "R$ 100.000,00", abc_cells)
            check("A8: Retorno unchanged (R$ 8.000,00)", abc_cells[5] == "R$ 8.000,00", abc_cells)
            check("A9: SPF Líq. unchanged (R$ 500,00)", abc_cells[6] == "R$ 500,00", abc_cells)
            check("A10: Rentabilidade unchanged (R$ 1.500,00)", abc_cells[7] == "R$ 1.500,00", abc_cells)
            check("A11: % Comissão unchanged (from faixaRows, 10%)", abc_cells[8] == "10%", abc_cells)
            check("A12: Comissão Total unchanged (from faixaRows, R$ 1.234,56)", abc_cells[9] == "R$ 1.234,56", abc_cells)

        # Mobile card variant -- same value must appear next to the name.
        page_m = browser.new_page(viewport={"width": 480, "height": 900})
        route_salary_rpcs(page_m)
        open_salary(page_m)
        card_text = page_m.locator(".salCard.salManagerRow", has_text="RICARDO SILVA COSTA").first.inner_text()
        check("A13 (mobile): card shows 60,0% next to the manager name", "60,0%" in card_text, card_text)
        page.close()
        page_m.close()

        # ================================================================
        # TEST B -- XYZ/NOVOS: no official Analyst row exists for this
        # store at all -- manager Share must stay '—', never a
        # fabricated 0,0%.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_salary_rpcs(page)
        open_salary(page)
        xyz_cells = manager_row_cells(page, "MANAGER XYZ")
        check("B1: manager row found for MANAGER XYZ", len(xyz_cells) > 0, xyz_cells)
        if xyz_cells:
            check("B2: Conversão cell stays '—' (no official Analyst row for XYZ)", xyz_cells[3] == "—", xyz_cells)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== SALSHARE1 Manager Share Regression: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
