#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SALFIX1 -- Salários & Comissões stale-async-overwrite regression.

CONFIRMED DEFECT (found during [SALÁRIOS][FINAL-UAT-1], reproduced
deterministically here): unlike gestao.js (fixed at 8a985e7, NAVFIX1)
and landing.js, salarios-comissoes.js never captured which route owned
the outlet before firing its RPCs. Every one of its 12 independent
load* functions (loadPeriods, loadCommissionConfig, loadDashboard,
loadGestorFiCommission, loadFaixaRows, loadOwnCommission,
loadScopeCommission, openDetails, openAnalystDetails,
loadHistoryClosings, selectClosing, loadHistoryOperationalDetail, plus
triggerExport) called render(outletRef) unconditionally from its
.then()/.catch() callbacks. A late-resolving Salary RPC -- arriving
after the user had already navigated to a different module -- would
silently repaint that OTHER module's outlet with Salary's own markup.
Observed both under a forced deterministic delay (TEST F below) and
organically under normal (near-instant) mocked latency during a plain
Home<->Salários stress loop (2/10 clobbers).

FIX (assets/js/salarios-comissoes.js): the exact "capture now, compare
on resolution" route-ownership guard technique gestao.js's own NAVFIX1
fix established. A module-level `mountRoute` is captured once by
NX_SALARIOS_COMISSOES_PAGE.render() (the real mount entry point) via
window.NX_ROUTER.currentRouteId(); every load* function's .then()/
.catch() callback now returns immediately, before touching
render(outletRef) or any module state, if the current route no longer
matches. window.NX_ROUTER may not exist in this module's own isolated
harnesses (tests/_salarios-comissoes-real-provider-harness.html,
tests/_salarios-uat-harness.html load the module without shell.js/
router.js) -- mountRoute stays null there and every guard is a no-op,
preserving every existing harness-level test unchanged (confirmed by
this Wave's own full re-run: salarios-comissoes-real-provider-test.py
35/35, v2-uat-04-other-profiles-salarios-test.py 60/60).

No RPC contract, authorization rule, or commission formula is touched
-- this only decides whether a stale completion's existing DOM write is
allowed to run at all.

TESTS A-C drive the REAL shell (index.html -> shell.js -> router.js ->
salarios-comissoes.js -> dashbi.js / gestao.js), never an isolated
module harness, because the defect lives in the cross-module
interaction. TEST D is the deterministic mechanism proof: one Salary
RPC is mocked to resolve late, forcing the exact stale-completion race
rather than relying on real network flakiness.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port; start/stop it externally,
matching this repo's established test convention.
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
    mode: 'fixture',
    supabaseUrl: 'https://mock.invalid',
    supabasePublishableKey: 'mock-anon-key',
    textEndpoint: null
  });
  window.NX_AUTH = {
    isAuthConfigured: true,
    getSession: () => Promise.resolve(window.__uatFakeSession),
    signIn: () => {
      window.__uatFakeSession = { user: { id: (window.__uatPendingProfile || {}).authUserId } };
      return Promise.resolve();
    },
    signOut: () => { window.__uatFakeSession = null; return Promise.resolve(); },
    resolveAuthorizedProfile: () => Promise.resolve(window.__uatPendingProfile),
    // PERMISSION_MATRIX modules are gated by their own permissionId
    // (config/module-registry.json) -- Salários' is 'comissoes'.
    resolveAllowedModules: () => Promise.resolve(['dashbi', 'gestao', 'comissoes']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

USER_A = {"userId": "row-salfix1", "authUserId": "AUTHUSER-SALFIX1", "nome": "UAT MASTER SALFIX1", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}

EMPTY_ROWS = {"rows": []}
ONE_PERIOD = {"rows": [{
    "id": "p1-salfix1", "nome_periodo": "21/08 à 20/09", "data_inicio": "2026-08-21",
    "data_fim": "2026-09-20", "status": "EM CONFERÊNCIA", "periodo_atual": True, "ativo": True
}]}
GESTOR_FI_EMPTY = {"pronto": False}
EMPTY_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}
EMPTY_MODEL_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "entry_rule": "SUM_ENTRY_DIV_VALID_OPERATIONS", "entry_percent_rule": "SUM_ENTRY_DIV_SUM_SALE_VALUE",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}
EMPTY_GESTAO = {
    "scope": {}, "period": {}, "filters": {}, "source": {},
    "summary": {"operational_quantity": 0, "total_financed": 0},
    "stores": [], "banks": [], "status_by_store": [], "status_by_bank": [],
    "plans": [], "plans_by_store_department": [], "spf_extra": [], "proposal_outcomes": []
}


def login_as(page, profile):
    page.evaluate(
        "(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('uat@test.invalid', 'x', 'uat-captcha'); }",
        profile
    )
    page.wait_for_function(
        "(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id",
        arg=profile["authUserId"], timeout=5000
    )


def route_json(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def route_salary_rpcs(page):
    page.route("**/rest/v1/rpc/operational_commission_periods*", route_json(200, ONE_PERIOD))
    page.route("**/rest/v1/rpc/operational_commission_metrics*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_analyst_commission_metrics_v2*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_salary_manager_directory*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_portal_config*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_gestor_fi_commission*", route_json(200, GESTOR_FI_EMPTY))
    page.route("**/rest/v1/rpc/operational_commission_faixa_rows*", route_json(200, EMPTY_ROWS))
    page.route("**/rest/v1/rpc/operational_metrics*", route_json(200, EMPTY_METRICS))
    page.route("**/rest/v1/rpc/operational_model_metrics*", route_json(200, EMPTY_MODEL_METRICS))
    page.route("**/rest/v1/rpc/operational_fandi_dashboard*", route_json(200, EMPTY_GESTAO))
    page.route("**/rest/v1/rpc/operational_score_coparticipated_data*", lambda route: route.abort())


def new_authorized_page(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    route_salary_rpcs(page)
    page.goto(BASE + "/index.html#/landing")
    # Wait for auth-boundary.js/auth-core.js's own real boot to finish
    # (SIGNED_OUT is its settled pre-login state) BEFORE installing the
    # mock -- installing any earlier risks auth-boundary.js's own
    # unconditional window.NX_AUTH (re)assignment clobbering it.
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=8000)
    page.evaluate(INSTALL_STUB_JS)
    login_as(page, USER_A)
    page.wait_for_function("!!window.NX_ROUTER && !!window.NX_SALARIOS_COMISSOES_PAGE && !!window.NX_DASHBI_PAGE && !!window.NX_GESTAO_PAGE", timeout=8000)
    return page


def nav(page, route_id):
    page.evaluate("(r) => window.NX_ROUTER.navigate(r)", route_id)


def outlet_state(page):
    return {
        "hash": page.evaluate("location.hash"),
        "salPage": page.locator(".salPage").count(),
        "dbPanel": page.locator("#dbPanel").count(),
        "gePanel": page.locator("#gePanel").count(),
        "salTitle": page.evaluate("!!document.querySelector('.modTitle') && document.querySelector('.modTitle').textContent.includes('Salários')"),
        "nxRootHidden": page.evaluate("document.getElementById('nxRoot').hidden"),
        "authState": page.evaluate("window.NX_AUTH_CORE.getState()"),
    }


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================================================================
        # TEST A -- Home -> Salários -> Home -> Salários, 10 repeated
        # round trips (the exact sequence the live UAT found 2/10
        # organic clobbers under).
        # ================================================================
        page = new_authorized_page(browser)
        clobbers = 0
        for i in range(10):
            nav(page, "salarios-comissoes")
            page.wait_for_selector(".salPage", timeout=5000)
            nav(page, "landing")
            page.wait_for_timeout(150)
            st = outlet_state(page)
            if st["hash"] == "#/landing" and (st["salPage"] != 0 or st["salTitle"]):
                clobbers += 1
        check("A1: 10/10 Home<->Salários round trips clean (0 clobbers)", clobbers == 0, clobbers)
        page.close()

        # ================================================================
        # TEST B -- Salários -> Dash BI -> Salários.
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "salarios-comissoes")
        page.wait_for_selector(".salPage", timeout=5000)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "salarios-comissoes")
        page.wait_for_timeout(400)
        st = outlet_state(page)
        check("B1: hash is #/salarios-comissoes after salários->dashbi->salários", st["hash"] == "#/salarios-comissoes", st)
        check("B2: .salPage is mounted (Salários actually re-rendered)", st["salPage"] == 1, st)
        check("B3: #nxRoot was not left hidden behind a spurious Login", st["nxRootHidden"] is not True, st)
        page.close()

        # ================================================================
        # TEST C -- Salários -> Gestão -> Salários.
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "salarios-comissoes")
        page.wait_for_selector(".salPage", timeout=5000)
        nav(page, "gestao")
        page.wait_for_selector("#gePanel", timeout=5000)
        nav(page, "salarios-comissoes")
        page.wait_for_timeout(400)
        st = outlet_state(page)
        check("C1: hash is #/salarios-comissoes after salários->gestão->salários", st["hash"] == "#/salarios-comissoes", st)
        check("C2: .salPage is mounted", st["salPage"] == 1, st)
        page.close()

        # ================================================================
        # TEST D -- THE MECHANISM, forced deterministically: Salário's
        # own operational_commission_metrics (the RPC loadDashboard's
        # .then() ultimately depends on, via loadCommissionDashboardData)
        # is mocked to resolve 400ms after being called. The user
        # navigates salários -> dashbi well before that elapses, so
        # Salário's stale render(outletRef) call would land strictly
        # AFTER dashbi is already the active route if the fix were
        # absent.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_salary_rpcs(page)  # operational_commission_metrics route is superseded below by the fetch()-level delay, which never reaches the network layer
        page.add_init_script("""
        (() => {
          const realFetch = window.fetch.bind(window);
          window.fetch = function (input, init) {
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            if (url.indexOf('operational_commission_metrics') !== -1) {
              return new Promise((resolve) => {
                setTimeout(() => {
                  resolve(new Response(JSON.stringify({ rows: [] }), { status: 200, headers: { 'content-type': 'application/json' } }));
                }, 400);
              });
            }
            return realFetch(input, init);
          };
        })();
        """)
        page.goto(BASE + "/index.html#/landing")
        page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=8000)
        page.evaluate(INSTALL_STUB_JS)
        login_as(page, USER_A)
        page.wait_for_function("!!window.NX_ROUTER && !!window.NX_SALARIOS_COMISSOES_PAGE && !!window.NX_DASHBI_PAGE", timeout=8000)

        nav(page, "salarios-comissoes")
        page.wait_for_selector(".salPage", timeout=5000)
        nav(page, "dashbi")  # return nav, WHILE the delayed RPC is still in flight
        page.wait_for_timeout(120)
        mid_state = outlet_state(page)
        check("D1: dashbi already mounted 120ms after nav (well before the 400ms delayed RPC)", mid_state["dbPanel"] == 1, mid_state)

        page.wait_for_timeout(500)  # now well past the point the stale RPC has resolved
        final_state = outlet_state(page)
        check("D2 (PROOF): #dbPanel still mounted after the stale Salário RPC settled", final_state["dbPanel"] == 1, final_state)
        check("D3 (PROOF): outlet does not revert to Salário's stale title/DOM", not final_state["salTitle"] and final_state["salPage"] == 0, final_state)
        check("D4 (PROOF): hash still #/dashbi, app not hidden behind Login", final_state["hash"] == "#/dashbi" and final_state["nxRootHidden"] is not True, final_state)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== SALFIX1 Salários Navigation Lifecycle: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
