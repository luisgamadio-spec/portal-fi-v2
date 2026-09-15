#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAVFIX1 -- Dashbi/Gestao SPA remount lifecycle regression.

CONFIRMED DEFECT (Human-reported, reproduced deterministically here):
dashbi -> gestao -> dashbi. location.hash correctly becomes '#/dashbi'
again, but the shared outlet (#nxContentOutlet, the real DOM shell.js's
dispatchModule() renders every module into) silently freezes on
Gestao's own stale content (or, depending on exact timing, dashbi
renders fine but the whole app is hidden behind a spurious Login
screen a moment later) -- persisting indefinitely, no further recovery.

ROOT CAUSE (confirmed by direct source read + deterministic
reproduction, not guessed): gestao.js's own render() (~line 263-441)
is the ONLY module in this codebase whose RPC failure handler
(.catch(), ~line 430-442) calls window.NX_AUTH_CORE.reportSessionExpired()
on a SESSION_EXPIRED-classified RPC error (401/403 from its own
operational_fandi_dashboard call) -- with, before this fix, NO check
that Gestao is still the active route. Gate 7's own renderSeq guard
only protects against a NEWER GESTAO-INTERNAL request (a filter
change) superseding an older one; it says nothing about the user
having navigated to a completely different module while the request
was in flight.

When that stale RPC resolves as SESSION_EXPIRED, reportSessionExpired()
unconditionally flips window.NX_AUTH_CORE's real state machine to
SESSION_EXPIRED. shell.js's boot() onStateChange listener (~line 327-
343) reacts by hiding #nxRoot and rendering Login. shell.js's own
onRouteChange() (~line 169-176) treats ANY state other than
AUTHORIZED/AUTH_NOT_CONFIGURED as "render Login, do nothing else" and
returns BEFORE ever calling dispatchModule() -- so whatever navigation
the user had already made (e.g. back to dashbi) never reaches
dashbi.js's own render() at all. The hash updates (the browser's own
native hashchange is independent of any of this), but the outlet is
simply never touched again -- frozen exactly where Gestao's own
synchronous mount-time write last left it.

FIX (assets/js/gestao.js render(), ~line 269-300 and ~430-442): a
"capture now, compare on resolution" route-ownership guard, the same
technique landing.js's own renderRoute() already uses
(NX_ROUTER.currentRouteId() !== routeId). render() now captures
window.NX_ROUTER.currentRouteId() at call time (myRoute); both its
.then() and .catch() branches return immediately, before touching the
DOM or calling reportSessionExpired(), if the CURRENT route no longer
matches -- i.e. the user has navigated away from Gestao entirely.
window.NX_ROUTER may not exist at all in gestao.js's own isolated test
harness (tests/fixtures/_gestao-real-provider-harness.html loads
gestao.js directly, never shell.js/router.js) -- myRoute stays null in
that case and the guard is a no-op, preserving every existing
harness-level test (gestao-real-provider-test.py) byte-for-byte,
INCLUDING its own test #11 ("missing token -> delegates to
NX_AUTH_CORE.reportSessionExpired exactly once"), which still fires
correctly because Gestao genuinely IS still the active/only module in
that harness.

No RPC contract, authorization rule, or business formula is touched --
this only decides whether a stale completion's existing side effects
(unchanged) are allowed to run at all.

TESTS A-E below drive the REAL shell (index.html -> shell.js ->
router.js -> landing.js -> gestao.js -> dashbi.js -> score.js), never
an isolated module harness, because the defect lives in the
cross-module interaction, not in any one module alone. TEST F is the
deterministic mechanism proof: a delayed 401 mock forces the exact
stale-completion race, rather than relying on real network flakiness.

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
    // NOTE: PERMISSION_MATRIX modules are gated by their own
    // permissionId (config/module-registry.json), not their route id --
    // Score's is 'analiseScoreVendedores', distinct from the 'score'
    // route id used with NX_ROUTER.navigate()/dispatchModule().
    resolveAllowedModules: () => Promise.resolve(['dashbi', 'gestao', 'analiseScoreVendedores']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

USER_A = {"userId": "row-navfix1", "authUserId": "AUTHUSER-NAVFIX1", "nome": "UAT MASTER NAVFIX1", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}

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


def new_authorized_page(browser):
    """Boots the real shell (index.html), installs the auth mock AFTER
    the real auth-boundary.js/auth-core.js have already finished their
    own boot (avoids auth-boundary.js's own unconditional window.NX_AUTH
    (re)assignment clobbering the mock -- same technique already
    established by sessionsec1-cross-user-isolation-test.py), then
    drives the REAL NX_AUTH_CORE.login() state machine to AUTHORIZED."""
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.route("**/rest/v1/rpc/operational_metrics*", route_json(200, EMPTY_METRICS))
    page.route("**/rest/v1/rpc/operational_model_metrics*", route_json(200, EMPTY_MODEL_METRICS))
    page.route("**/rest/v1/rpc/operational_fandi_dashboard*", route_json(200, EMPTY_GESTAO))
    page.route("**/rest/v1/rpc/operational_score_coparticipated_data*", lambda route: route.abort())
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate(INSTALL_STUB_JS)
    login_as(page, USER_A)
    page.wait_for_function("!!window.NX_ROUTER && !!window.NX_DASHBI_PAGE && !!window.NX_GESTAO_PAGE && !!window.NX_SCORE_PAGE", timeout=8000)
    return page


def nav(page, route_id):
    page.evaluate("(r) => window.NX_ROUTER.navigate(r)", route_id)


def outlet_state(page):
    return {
        "hash": page.evaluate("location.hash"),
        "dbPanel": page.locator("#dbPanel").count(),
        "gePanel": page.locator("#gePanel").count(),
        "scTable": page.locator("#scTableRegion").count(),
        "geTitle": page.evaluate("!!document.querySelector('.modTitle') && document.querySelector('.modTitle').textContent.includes('Análise F&I do Grupo')"),
        "nxRootHidden": page.evaluate("document.getElementById('nxRoot').hidden"),
        "authState": page.evaluate("window.NX_AUTH_CORE.getState()"),
    }


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================================================================
        # TEST A -- dashbi -> gestao -> dashbi. THE originally reported
        # sequence. Asserts hash AND the correct mounted DOM (not hash
        # alone -- hash was never the part that broke).
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "gestao")
        page.wait_for_selector("#gePanel", timeout=5000)
        nav(page, "dashbi")
        page.wait_for_timeout(400)
        st = outlet_state(page)
        check("A1: hash is #/dashbi after dashbi->gestao->dashbi", st["hash"] == "#/dashbi", st)
        check("A2: #dbPanel is mounted (Dash BI actually re-rendered)", st["dbPanel"] == 1, st)
        check("A3: Gestao's own title is NOT still showing", not st["geTitle"], st)
        check("A4: #nxRoot was not left hidden behind a spurious Login", st["nxRootHidden"] is not True, st)
        check("A5: auth state is still AUTHORIZED", st["authState"] == "AUTHORIZED", st)
        page.close()

        # ================================================================
        # TEST B -- the reverse sequence, gestao -> dashbi -> gestao.
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "gestao")
        page.wait_for_selector("#gePanel", timeout=5000)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "gestao")
        page.wait_for_timeout(400)
        st = outlet_state(page)
        check("B1: hash is #/gestao after gestao->dashbi->gestao", st["hash"] == "#/gestao", st)
        check("B2: #gePanel is mounted (Gestao actually re-rendered)", st["gePanel"] == 1, st)
        check("B3: #nxRoot was not left hidden behind a spurious Login", st["nxRootHidden"] is not True, st)
        page.close()

        # ================================================================
        # TEST C -- regression guard: dashbi -> score -> dashbi (a
        # combo the original report confirmed already worked; must
        # still work unchanged after this fix).
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "score")
        page.wait_for_selector("#scTableRegion", timeout=5000)
        nav(page, "dashbi")
        page.wait_for_timeout(300)
        st = outlet_state(page)
        check("C1: hash is #/dashbi after dashbi->score->dashbi", st["hash"] == "#/dashbi", st)
        check("C2: #dbPanel is mounted", st["dbPanel"] == 1, st)
        page.close()

        # ================================================================
        # TEST D -- regression guard: gestao -> score -> gestao.
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "gestao")
        page.wait_for_selector("#gePanel", timeout=5000)
        nav(page, "score")
        page.wait_for_selector("#scTableRegion", timeout=5000)
        nav(page, "gestao")
        page.wait_for_timeout(300)
        st = outlet_state(page)
        check("D1: hash is #/gestao after gestao->score->gestao", st["hash"] == "#/gestao", st)
        check("D2: #gePanel is mounted", st["gePanel"] == 1, st)
        page.close()

        # ================================================================
        # TEST E -- rapid-but-valid version of A: no long sleeps between
        # navigations, only real DOM-ready waits (the actual defect is a
        # RACE, so it must also be proven not to reappear under a fast,
        # back-to-back navigation sequence, not only a slow one).
        # ================================================================
        page = new_authorized_page(browser)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "gestao")
        page.wait_for_selector("#gePanel", timeout=5000)
        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        # settle time for any late async completion from the gestao visit
        page.wait_for_timeout(500)
        st = outlet_state(page)
        check("E1: rapid dashbi->gestao->dashbi -- hash is #/dashbi", st["hash"] == "#/dashbi", st)
        check("E2: rapid dashbi->gestao->dashbi -- #dbPanel mounted", st["dbPanel"] == 1, st)
        check("E3: rapid dashbi->gestao->dashbi -- app not hidden behind Login", st["nxRootHidden"] is not True, st)
        page.close()

        # ================================================================
        # TEST F -- THE MECHANISM, forced deterministically (not real
        # network flakiness): Gestao's own RPC is mocked to resolve as a
        # 401 (SESSION_EXPIRED) 300ms after being called, entirely via an
        # in-browser fetch() override (not a Playwright route delay from
        # a background thread, which either blocks every other Playwright
        # call this script makes or fails outright trying to fulfill from
        # the wrong thread). The user navigates gestao -> dashbi well
        # before that 300ms elapses, so gestao's own stale rejection
        # settles strictly AFTER dashbi is already the active route --
        # proving the fix's specific "navigated away, so this must be a
        # no-op" branch, not merely that the happy path still works.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.route("**/rest/v1/rpc/operational_metrics*", route_json(200, EMPTY_METRICS))
        page.route("**/rest/v1/rpc/operational_model_metrics*", route_json(200, EMPTY_MODEL_METRICS))
        page.add_init_script("""
        (() => {
          const realFetch = window.fetch.bind(window);
          window.fetch = function (input, init) {
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            if (url.indexOf('operational_fandi_dashboard') !== -1) {
              return new Promise((resolve) => {
                setTimeout(() => {
                  resolve(new Response(JSON.stringify({ message: 'invalid JWT' }), { status: 401, headers: { 'content-type': 'application/json' } }));
                }, 300);
              });
            }
            return realFetch(input, init);
          };
        })();
        """)
        page.goto(BASE + "/index.html#/landing")
        page.wait_for_selector("#landingNav", timeout=8000)
        page.evaluate(INSTALL_STUB_JS)
        page.evaluate("""() => {
            window.__navfix1SessionExpiredCalls = 0;
            const orig = window.NX_AUTH_CORE.reportSessionExpired.bind(window.NX_AUTH_CORE);
            window.NX_AUTH_CORE.reportSessionExpired = function () {
                window.__navfix1SessionExpiredCalls += 1;
                return orig.apply(this, arguments);
            };
        }""")
        login_as(page, USER_A)
        page.wait_for_function("!!window.NX_ROUTER && !!window.NX_DASHBI_PAGE && !!window.NX_GESTAO_PAGE", timeout=8000)

        nav(page, "dashbi")
        page.wait_for_selector("#dbPanel", timeout=5000)
        nav(page, "gestao")
        page.wait_for_function("document.querySelector('.modTitle') && document.querySelector('.modTitle').textContent.includes('Análise F&I do Grupo')", timeout=5000)
        state_before_return = page.evaluate("window.NX_AUTH_CORE.getState()")
        check("F0 (sanity): auth state still AUTHORIZED before the stale 401 has resolved", state_before_return == "AUTHORIZED", state_before_return)

        nav(page, "dashbi")  # return nav, WHILE gestao's delayed 401 is still in flight
        page.wait_for_timeout(120)
        mid_state = outlet_state(page)
        check("F1: dashbi already mounted 120ms after return nav (well before gestao's 300ms 401)", mid_state["dbPanel"] == 1, mid_state)

        page.wait_for_timeout(500)  # now well past the point gestao's stale 401 has resolved
        final_state = outlet_state(page)
        se_calls = page.evaluate("window.__navfix1SessionExpiredCalls")
        check("F2 (PROOF): stale gestao 401 did NOT call reportSessionExpired (route-ownership guard caught it)", se_calls == 0, se_calls)
        check("F3 (PROOF): #dbPanel still mounted after the stale 401 settled", final_state["dbPanel"] == 1, final_state)
        check("F4 (PROOF): outlet does not revert to Gestao's stale title", not final_state["geTitle"], final_state)
        check("F5 (PROOF): auth state still AUTHORIZED, app not hidden behind Login", final_state["authState"] == "AUTHORIZED" and final_state["nxRootHidden"] is not True, final_state)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== NAVFIX1 Dashbi/Gestao Navigation Lifecycle: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
