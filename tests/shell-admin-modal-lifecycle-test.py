#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASTERFIX1 -- Painel Master stale-modal cross-module leak regression.

CONFIRMED DEFECT (found during [PAINEL MASTER][FINAL-UAT-1], reproduced
deterministically here): unlike gestao.js (fixed at 8a985e7, NAVFIX1)
and salarios-comissoes.js (fixed at b1c5751, SALFIX1), shell-admin.js
had zero window.NX_ROUTER references anywhere in the file. Every one of
its ~12 modal call sites (Usuários' "Gerar link de acesso", Gestão de
Bases, Gestão dos Simuladores, Configurações, Períodos, Férias/
Ausências, Histórico de Competências' Reabrir/Fechamento, etc.) funnels
through the single shared renderNxModal()/clearNxModal() chokepoint,
which writes into #nxModalRoot -- a page-level <div> in index.html, a
SIBLING of the router-controlled #nxContentOutlet, never cleared on
route change by shell.js itself. A Painel Master mutation whose promise
settles AFTER the user has navigated to a different module would still
write its result dialog (backdrop + focus-trapped dialog + a global
document.body scroll-lock class, 'maudModalOpen') on top of whatever
module the user is now using -- the exact "stale async write into
shared DOM after navigation" defect class NAVFIX1/SALFIX1 already
fixed once each, manifesting here through the modal root instead of
the main outlet (the outlet itself, #maPanel, was already safe -- its
own renderPanel() null-checks document.getElementById('maPanel'),
which correctly returns null once another module owns the outlet).

FIX (assets/js/shell-admin.js): the same "capture now, compare on
resolution" route-ownership guard technique gestao.js's/salarios-
comissoes.js's own fixes already established. A module-level
`mountRoute` is captured once by NX_SHELL_ADMIN_PAGE.render() (the real
mount entry point) via window.NX_ROUTER.currentRouteId(); both
renderNxModal() and clearNxModal() -- the single chokepoint every
modal call site already funnels through -- now return immediately,
before touching #nxModalRoot or the body scroll-lock class, if the
current route no longer matches. window.NX_ROUTER may not exist in
this module's own isolated test harnesses -- mountRoute stays null
there and the guard is a no-op, preserving every existing
harness-level test unchanged.

No RPC contract, authorization rule, closing/reopen semantics, or
business calculation is touched -- this only decides whether a stale
completion's existing DOM write is allowed to run at all.

TEST A drives the REAL shell (index.html -> shell.js -> router.js ->
shell-admin.js -> dashbi.js), never an isolated module harness, because
the defect lives in the cross-module interaction: a delayed "Gerar
link de acesso" mutation forces the exact stale-completion race, rather
than relying on real network flakiness. TEST B is a lightweight
repeated-navigation sanity check (Home<->Painel Master, 10x) confirming
the fix introduced no regression to the module's own remount.

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
    resolveAllowedModules: () => Promise.resolve(['painelMaster', 'dashbi']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

MASTER_A = {"userId": "row-masterfix1", "authUserId": "AUTHUSER-MASTERFIX1", "nome": "UAT MASTER MASTERFIX1", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}

USER_ROW = {
    "id": "u-link1", "nome": "LINK TARGET USER", "email_auth": "u-link1@uat.invalid", "cpf": "12345678901",
    "perfil": "VENDEDOR", "loja": "EUROPA", "status": "NOVOS",
    "ativo": True, "tem_auth": True, "auth_confirmado": True, "primeiro_acesso": False,
    "email_divergente": False
}

EMPTY_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}


def route_json(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def route_generic_catchall(route):
    route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": []}))


def route_common_rpcs(page):
    # generic catch-all FIRST -- Playwright gives later registrations
    # priority, so the specific handlers below safely override it.
    page.route("**/rest/v1/rpc/**", route_generic_catchall)
    page.route("**/functions/v1/**", route_generic_catchall)
    page.route("**/rest/v1/rpc/master_admin_security_data*", route_json(200, {"users": [USER_ROW]}))
    page.route("**/rest/v1/rpc/master_listar_convites*", route_json(200, []))
    page.route("**/rest/v1/rpc/operational_metrics*", route_json(200, EMPTY_METRICS))


def login_as(page, profile):
    page.evaluate(
        "(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('uat@test.invalid', 'x', 'uat-captcha'); }",
        profile
    )
    page.wait_for_function(
        "(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id",
        arg=profile["authUserId"], timeout=5000
    )


def boot_signed_out(page):
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=8000)
    page.evaluate(INSTALL_STUB_JS)


def nav(page, route_id):
    page.evaluate("(r) => window.NX_ROUTER.navigate(r)", route_id)


def outlet_state(page):
    return {
        "hash": page.evaluate("location.hash"),
        "maPage": page.locator(".maPage").count(),
        "dbPanel": page.locator("#dbPanel").count(),
        "nxModalRootHtml": page.evaluate("(function(){var m=document.getElementById('nxModalRoot'); return m?m.innerHTML:null;})()"),
        "nxModalRootAriaHidden": page.evaluate("(function(){var m=document.getElementById('nxModalRoot'); return m?m.getAttribute('aria-hidden'):null;})()"),
        "bodyModalOpen": page.evaluate("document.body.classList.contains('maudModalOpen')"),
        "nxRootHidden": page.evaluate("document.getElementById('nxRoot').hidden"),
    }


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================================================================
        # TEST A -- THE MECHANISM, forced deterministically: Painel
        # Master's own "Gerar link de acesso" mutation (Usuários tab) is
        # mocked to resolve 400ms after being confirmed, via an in-browser
        # fetch() override targeting the admin-generate-user-access-link
        # Edge Function. The user navigates shell-admin -> dashbi well
        # before that 400ms elapses, so the stale completion settles
        # strictly AFTER dashbi is already the active route.
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_common_rpcs(page)
        page.add_init_script("""
        (() => {
          const realFetch = window.fetch.bind(window);
          window.fetch = function (input, init) {
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            if (url.indexOf('admin-generate-user-access-link') !== -1) {
              return new Promise((resolve) => {
                setTimeout(() => {
                  resolve(new Response(JSON.stringify({ link: 'https://uat-test-only.invalid/STALE-LINK-MASTERFIX1' }), { status: 200, headers: { 'content-type': 'application/json' } }));
                }, 400);
              });
            }
            return realFetch(input, init);
          };
        })();
        """)
        boot_signed_out(page)
        login_as(page, MASTER_A)
        page.wait_for_function("!!window.NX_ROUTER && !!window.NX_SHELL_ADMIN_PAGE && !!window.NX_DASHBI_PAGE", timeout=8000)

        nav(page, "shell-admin")
        page.wait_for_selector(".maPage", timeout=5000)
        page.wait_for_selector(".maTable tbody tr[data-key='u-link1']", timeout=5000)
        page.locator(".maTable tbody tr[data-key='u-link1']").click()
        page.wait_for_selector("#maGenerateLinkBtn", timeout=5000)
        page.locator("#maGenerateLinkBtn").click()
        page.wait_for_selector("#maConfirmYes", timeout=5000)
        page.locator("#maConfirmYes").click()  # fires the 400ms-delayed mutation

        page.wait_for_timeout(80)  # request now in flight
        nav(page, "dashbi")  # return nav, WELL before the 400ms elapses
        page.wait_for_selector("#dbPanel", timeout=5000)
        mid = outlet_state(page)
        check("A1: dashbi mounted 80ms after nav (well before the 400ms delayed mutation)", mid["dbPanel"] == 1, mid)

        page.wait_for_timeout(600)  # now well past the point the stale mutation resolved
        final = outlet_state(page)
        check("A2 (PROOF): #nxModalRoot stays empty on Dash BI after Painel Master's stale mutation settles", (final["nxModalRootHtml"] or "") == "", final)
        check("A3 (PROOF): aria-hidden stays 'true' -- no stale modal surfaced over Dash BI", final["nxModalRootAriaHidden"] == "true", final)
        check("A4 (PROOF): body scroll-lock class not leaked onto Dash BI", not final["bodyModalOpen"], final)
        check("A5: still on #/dashbi, app not hidden behind Login", final["hash"] == "#/dashbi" and final["nxRootHidden"] is not True, final)
        page.close()

        # ================================================================
        # TEST B -- lightweight regression guard: 10x Home<->Painel
        # Master round trips remain clean after the fix (module's own
        # remount, unrelated to the modal chokepoint, must not regress).
        # ================================================================
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        route_common_rpcs(page)
        boot_signed_out(page)
        login_as(page, MASTER_A)
        page.wait_for_function("!!window.NX_ROUTER && !!window.NX_SHELL_ADMIN_PAGE", timeout=8000)
        clobbers = 0
        for i in range(10):
            nav(page, "shell-admin")
            page.wait_for_selector(".maPage", timeout=5000)
            nav(page, "landing")
            page.wait_for_timeout(150)
            st = outlet_state(page)
            if st["hash"] == "#/landing" and st["maPage"] != 0:
                clobbers += 1
        check("B1: 10/10 Home<->Painel Master round trips clean (0 clobbers)", clobbers == 0, clobbers)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"=== MASTERFIX1 Painel Master Modal Lifecycle: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
