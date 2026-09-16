#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SALSHARE3 -- manager consolidated row Share/Conversão regression
(supersedes SALSHARE1's own assertions, which asserted a business rule
SHARE-AUDIT-1 subsequently proved WRONG).

CONFIRMED DEFECTS, in order:

1. (Pre-SALSHARE1) Conversão/Share on the GERENTE consolidated row was
   hardcoded '—', even when real data existed.

2. (SALSHARE1, commit ca06b74) "Fixed" #1 by borrowing the store's
   OFFICIAL ANALYST's own store-wide Share (officialAnalystShareForStore)
   -- but SHARE-AUDIT-1 proved, from the canonical V1 source
   (portal-app.js:3050-3051, trPessoa(...,'GERENTE NOVOS',
   sumRows(novos),'manager') / the SEMINOVOS equivalent, both rendering
   via the SAME shareBadge(m.financiadas, m.vendidas) every other row
   type uses), that a manager's canonical Share has ALWAYS been THAT
   MANAGER'S OWN DEPARTMENT TEAM'S financiadas/vendidas -- never
   another entity's. Real example (ALPHAVILLE, current competência):
   FELLIPE DE LIMA LUIZ (NOVOS, team 13 sold/8 financed, real 61,5%)
   and JOAO FONTOLAN (SEMINOVOS, team 15 sold/8 financed, real 53,3%)
   both incorrectly showed 57,1% -- ALPHAVILLE's single store-wide
   official Analyst's own ratio (Douglas Henrique Pereira da Silva,
   28 sold/16 financed), because officialAnalystShareForStore() matched
   by store only, discarding the department dimension the row's own
   Vendidas/Financiadas are scoped to.

FIX (SALSHARE3, assets/js/salarios-comissoes.js): trailingGroupRow()'s
manager branch now computes shareValue directly from `totals` -- the
SAME sumGroupTotals(group.rows) object already producing that row's
own Vendidas/Financiadas -- exactly mirroring V1's
shareBadge(m.financiadas, m.vendidas). officialAnalystShareForStore()
was dead code after this change and has been deleted; the
analystByStore parameter was dropped from trailingGroupRow() and both
call sites (analystByStore itself remains, still needed by the
unrelated Analyst section renderer).

This regression proves the CORRECT rule with the exact real-world
ALPHAVILLE two-manager scenario (Case A), the zero-activity fallback
(Case B), and full commission-field integrity (Case C, folded into
Case A's own assertions since both managers carry real faixa/totals
data).

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

USER_MASTER = {"userId": "row-salshare3", "authUserId": "AUTHUSER-SALSHARE3", "nome": "UAT MASTER SALSHARE3", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}

ONE_PERIOD = {"rows": [{
    "id": "p1-salshare3", "nome_periodo": "21/08 à 20/09", "data_inicio": "2026-08-21",
    "data_fim": "2026-09-20", "status": "EM CONFERÊNCIA", "periodo_atual": True, "ativo": True
}]}

# Case A fixture: the real ALPHAVILLE scenario from SHARE-AUDIT-1.
# NOVOS team (FELLIPE's) sums to 13 sold / 8 financed -> real 61,5%.
# SEMINOVOS team (JOAO's) sums to 15 sold / 8 financed -> real 53,3%.
# ALPHAVILLE's single store-wide official Analyst sums to 28/16 -> 57,1%
# -- must NOT appear on either manager row.
# Case B fixture: ZEROSTORE/NOVOS has one seller row with sold=0/
# financed=0 (a real, legitimate zero-activity team) and its OWN
# store-wide Analyst exists with a real, nonzero share (50,0%) -- proves
# the fallback is neither 0,0% nor a borrowed Analyst value.
METRICS = {"rows": [
    {"store": "ALPHAVILLE", "department": "NOVOS", "seller_id": "seller-1", "seller_name": "EDIBERTO TEST",
     "sold_count": 13, "financed_count": 8, "share_percent": 61.5385,
     "production_value": 130000.0, "return_value": 9500.0, "spf_net_value": 600.0, "profitability_value": 2100.0},
    {"store": "ALPHAVILLE", "department": "SEMINOVOS", "seller_id": "seller-2", "seller_name": "ALINE TEST",
     "sold_count": 15, "financed_count": 8, "share_percent": 53.3333,
     "production_value": 150000.0, "return_value": 10500.0, "spf_net_value": 650.0, "profitability_value": 2300.0},
    {"store": "ZEROSTORE", "department": "NOVOS", "seller_id": "seller-3", "seller_name": "ZERO SELLER",
     "sold_count": 0, "financed_count": 0, "share_percent": 0,
     "production_value": 0.0, "return_value": 0.0, "spf_net_value": 0.0, "profitability_value": 0.0},
], "totals": {}}

ANALYST_METRICS = {"rows": [
    {"store": "ALPHAVILLE", "analyst_name": "DOUGLAS HENRIQUE PEREIRA DA SILVA", "sold_count": 28, "financed_count": 16,
     "production_value": 400000.0, "return_value": 30000.0, "spf_value": 2000.0, "transfer": False, "coverage_id": None},
    {"store": "ZEROSTORE", "analyst_name": "ANALISTA ZEROSTORE", "sold_count": 10, "financed_count": 5,
     "production_value": 50000.0, "return_value": 4000.0, "spf_value": 300.0, "transfer": False, "coverage_id": None}
]}

MANAGER_DIRECTORY = {"rows": [
    {"store": "ALPHAVILLE", "department": "NOVOS", "manager_name": "FELLIPE DE LIMA LUIZ"},
    {"store": "ALPHAVILLE", "department": "SEMINOVOS", "manager_name": "JOAO FONTOLAN"},
    {"store": "ZEROSTORE", "department": "NOVOS", "manager_name": "MANAGER ZERO"}
]}

FAIXA_ROWS = {"rows": [
    {"perfil": "GERENTE", "store": "ALPHAVILLE", "department": "NOVOS", "faixa_level": "INTERMEDIARIA", "faixa": 0.10, "comissao_total": 1300.00},
    {"perfil": "GERENTE", "store": "ALPHAVILLE", "department": "SEMINOVOS", "faixa_level": "MINIMA", "faixa": 0.05, "comissao_total": 750.00},
    {"perfil": "GERENTE", "store": "ZEROSTORE", "department": "NOVOS", "faixa_level": "MINIMA", "faixa": 0.03, "comissao_total": 0.00}
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
    """Desktop .salManagerRow cell texts, in column order: Nome|Vendidas|
    Financiadas|Conversão|Produção|Retorno|SPF Líq.|Rentabilidade|
    % Comissão|Comissão Total|Ações."""
    row = page.locator(".salManagerRow", has_text=manager_name).first
    cells = row.locator("td")
    return [cells.nth(i).inner_text().strip() for i in range(cells.count())]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================================================================
        # CASE A -- ALPHAVILLE two-manager split. Each manager must show
        # THEIR OWN department team's ratio, never the store-wide
        # Analyst's 57,1%, and never each other's value either.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_salary_rpcs(page)
        open_salary(page)

        fellipe = manager_row_cells(page, "FELLIPE DE LIMA LUIZ")
        check("A1: manager row found for FELLIPE DE LIMA LUIZ", len(fellipe) > 0, fellipe)
        if fellipe:
            check("A2: Fellipe (NOVOS) Vendidas = 13", fellipe[1] == "13", fellipe)
            check("A3: Fellipe (NOVOS) Financiadas = 8", fellipe[2] == "8", fellipe)
            check("A4: Fellipe Share = 61,5% (own team ratio)", fellipe[3] == "61,5%", fellipe)
            check("A5: Fellipe Share != 57,1% (the Analyst's store-wide value)", fellipe[3] != "57,1%", fellipe)
            check("A6: Fellipe Produção unchanged (R$ 130.000,00)", fellipe[4] == "R$ 130.000,00", fellipe)
            check("A7: Fellipe Retorno unchanged (R$ 9.500,00)", fellipe[5] == "R$ 9.500,00", fellipe)
            check("A8: Fellipe SPF Líq. unchanged (R$ 600,00)", fellipe[6] == "R$ 600,00", fellipe)
            check("A9: Fellipe Rentabilidade unchanged (R$ 2.100,00)", fellipe[7] == "R$ 2.100,00", fellipe)
            check("A10: Fellipe % Comissão unchanged (10%)", fellipe[8] == "10%", fellipe)
            check("A11: Fellipe Comissão Total unchanged (R$ 1.300,00)", fellipe[9] == "R$ 1.300,00", fellipe)

        joao = manager_row_cells(page, "JOAO FONTOLAN")
        check("A12: manager row found for JOAO FONTOLAN", len(joao) > 0, joao)
        if joao:
            check("A13: Joao (SEMINOVOS) Vendidas = 15", joao[1] == "15", joao)
            check("A14: Joao (SEMINOVOS) Financiadas = 8", joao[2] == "8", joao)
            check("A15: Joao Share = 53,3% (own team ratio)", joao[3] == "53,3%", joao)
            check("A16: Joao Share != 57,1% (the Analyst's store-wide value)", joao[3] != "57,1%", joao)
            check("A17: Joao Share != Fellipe's Share (different teams, different ratios)", joao[3] != (fellipe[3] if fellipe else None), joao)
            check("A18: Joao Produção unchanged (R$ 150.000,00)", joao[4] == "R$ 150.000,00", joao)
            check("A19: Joao Retorno unchanged (R$ 10.500,00)", joao[5] == "R$ 10.500,00", joao)
            check("A20: Joao SPF Líq. unchanged (R$ 650,00)", joao[6] == "R$ 650,00", joao)
            check("A21: Joao Rentabilidade unchanged (R$ 2.300,00)", joao[7] == "R$ 2.300,00", joao)
            check("A22: Joao % Comissão unchanged (5%)", joao[8] == "5%", joao)
            check("A23: Joao Comissão Total unchanged (R$ 750,00)", joao[9] == "R$ 750,00", joao)

        # Mobile card variant -- same values must appear, same absence of 57,1%.
        page_m = browser.new_page(viewport={"width": 480, "height": 900})
        route_salary_rpcs(page_m)
        open_salary(page_m)
        fellipe_card = page_m.locator(".salCard.salManagerRow", has_text="FELLIPE DE LIMA LUIZ").first.inner_text()
        joao_card = page_m.locator(".salCard.salManagerRow", has_text="JOAO FONTOLAN").first.inner_text()
        check("A24 (mobile): Fellipe card shows 61,5%", "61,5%" in fellipe_card, fellipe_card)
        check("A25 (mobile): Fellipe card does not show 57,1%", "57,1%" not in fellipe_card, fellipe_card)
        check("A26 (mobile): Joao card shows 53,3%", "53,3%" in joao_card, joao_card)
        check("A27 (mobile): Joao card does not show 57,1%", "57,1%" not in joao_card, joao_card)
        page.close()
        page_m.close()

        # ================================================================
        # CASE B -- ZEROSTORE/NOVOS: manager's own team has 0 sold/0
        # financed this period. Share must be '—' -- not 0,0%, and not
        # ZEROSTORE's own real, nonzero Analyst share (50,0%).
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_salary_rpcs(page)
        open_salary(page)
        zero_cells = manager_row_cells(page, "MANAGER ZERO")
        check("B1: manager row found for MANAGER ZERO", len(zero_cells) > 0, zero_cells)
        if zero_cells:
            check("B2: Vendidas = 0", zero_cells[1] == "0", zero_cells)
            check("B3: Financiadas = 0", zero_cells[2] == "0", zero_cells)
            check("B4: Share = '—' (not fabricated 0,0%)", zero_cells[3] == "—", zero_cells)
            check("B5: Share != '0,0%'", zero_cells[3] != "0,0%", zero_cells)
            check("B6: Share != ZEROSTORE's own real Analyst share (50,0%)", zero_cells[3] != "50,0%", zero_cells)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== SALSHARE3 Manager Share Regression (canonical rule): {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
