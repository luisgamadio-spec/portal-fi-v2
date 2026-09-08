#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PA-1B -- Human UAT proved a real ANALISTA session did not see the
"Atendimento F&I" / "Painel do Analista F&I" tile on Landing despite
PA-1's technical suite passing.

Root cause, proven by reproducing the REAL auth flow (mocked Supabase
client via add_init_script, same technique as tests/auth-foundation-
test.py -- not window.NX_AUTH direct-override, which auth-boundary.js's
own real client construction clobbers): with a genuinely authenticated
ANALISTA session, landing.js/module-registry.js/auth-core.js already
render "Atendimento F&I" -> "Painel do Analista F&I" correctly as an
authorized, clickable link. The defect is NOT in authorization logic.
It is that config/landing-groups.json and config/module-registry.json
were fetched with a plain fetch() (no cache directive) -- across a
long-lived Human browser session spanning multiple Waves, a
heuristically-cached stale response (Last-Modified present, no
Cache-Control) can silently serve pre-PA-1 content forever without a
hard refresh. Fix: cache:'no-store' on both fetches.

This test proves the CURRENT (already-correct) authorization behavior
for the full profile matrix (ANALISTA/MASTER/VENDEDOR) at both the
Landing-visibility layer and the direct-route layer, so a future
regression in either dimension is caught even though this specific
incident's true cause was a caching gap, not a logic defect.

0 real network calls, 0 real Supabase project touched, 0 credentials.
Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/index.html"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


CONFIG_SCRIPT = """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-key', textEndpoint: null
};
"""
MOCK_CLIENT_SCRIPT = """
(function () {
  var fakeSession = window.__MOCK__.initialSession || null;
  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          getSession: function () { return ok({ session: fakeSession }); },
          onAuthStateChange: function () { return { data: { subscription: { unsubscribe: function () {} } } } ; },
          signOut: function () { return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          if (name === 'usuario_logado_fi') return ok([window.__MOCK__.profileRow]);
          if (name === 'portal_modulos_permitidos') return ok(window.__MOCK__.allowedModuleIds || []);
          return ok(null);
        }
      };
    }
  };
})();
"""

ANALISTA_ROW = "{usuario_id:'u1', auth_user_id:'auth-user-1', nome:'Analista Teste', perfil:'ANALISTA', loja:'BARRA FUNDA', status:'NOVOS', ativo:true}"
MASTER_ROW = "{usuario_id:'u2', auth_user_id:'auth-user-1', nome:'Master Teste', perfil:'MASTER', loja:'TODAS', status:'MASTER', ativo:true}"
VENDEDOR_ROW = "{usuario_id:'u3', auth_user_id:'auth-user-1', nome:'Vendedor Teste', perfil:'VENDEDOR', loja:'Barra Funda', status:'NOVOS', ativo:true}"


def new_page(browser, profile_row, allowed_module_ids):
    mock_state = ("{initialSession: {access_token:'tok', user:{id:'auth-user-1'}}, profileRow: " +
                  profile_row + ", allowedModuleIds: " + str(allowed_module_ids).replace("'", "'") + "}")
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.route("**/supabase-js@*", lambda route: route.abort())
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script("window.__MOCK__ = " + mock_state + ";")
    page.add_init_script(MOCK_CLIENT_SCRIPT)
    return page


def goto_landing(page):
    page.goto(BASE + "#/landing")
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTHORIZED'", timeout=5000)
    page.wait_for_timeout(300)


def landing_tabs(page):
    return page.evaluate("[...document.querySelectorAll('#landingNav .fNavItem .label')].map(e => e.textContent)")


def atendimento_module_is_link(page, tabs):
    if "Atendimento F&I" not in tabs:
        return None
    idx = tabs.index("Atendimento F&I")
    page.click(f"#fNavTab{idx}")
    page.wait_for_timeout(200)
    return page.evaluate("!!document.querySelector('#landingModuleDetail a.fModuleBlock')")


def route_reaches_module(page):
    page.evaluate("window.location.hash = '#/painel-analista-fi'")
    page.wait_for_timeout(400)
    return page.evaluate("!!window.NX_PAINEL_ANALISTA_FI_PAGE && document.getElementById('paOutlet') !== null || !!document.querySelector('.paPage')")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- ANALISTA: Landing visibility + direct route ----------
        page = new_page(browser, ANALISTA_ROW, ['dashbi', 'gestao', 'painelAnalistaFi'])
        goto_landing(page)
        tabs = landing_tabs(page)
        check("ANALISTA: 'Atendimento F&I' tab visible on Landing", "Atendimento F&I" in tabs)
        check("ANALISTA: Painel do Analista F&I rendered as authorized link (not deferred)", atendimento_module_is_link(page, tabs) is True)
        check("ANALISTA: direct route #/painel-analista-fi reaches the module", route_reaches_module(page))
        page.close()

        # ---------- MASTER: Landing visibility + direct route ----------
        page = new_page(browser, MASTER_ROW, ['dashbi', 'gestao', 'painelAnalistaFi', 'painelMaster'])
        goto_landing(page)
        tabs = landing_tabs(page)
        check("MASTER: 'Atendimento F&I' tab visible on Landing", "Atendimento F&I" in tabs)
        check("MASTER: Painel do Analista F&I rendered as authorized link (not deferred)", atendimento_module_is_link(page, tabs) is True)
        check("MASTER: direct route #/painel-analista-fi reaches the module", route_reaches_module(page))
        page.close()

        # ---------- VENDEDOR: denied at both layers ----------
        page = new_page(browser, VENDEDOR_ROW, ['simuladorCompleto', 'comissoes'])
        goto_landing(page)
        tabs = landing_tabs(page)
        # VENDEDOR has no module in "Atendimento F&I" -- the group tab
        # still renders (landingHtml renders all group tabs
        # unconditionally, per its own architecture -- Gate 24 asks that
        # an unauthorized profile not see a meaningfully-populated
        # empty group; verify the ONE module inside it is correctly
        # deferred/non-navigable, not that the tab itself vanishes).
        is_link = atendimento_module_is_link(page, tabs)
        check("VENDEDOR: Painel do Analista F&I is NOT rendered as an authorized link", is_link is not True)
        check("VENDEDOR: direct route #/painel-analista-fi is DENIED (redirected away)", route_reaches_module(page) is False)
        page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Painel do Analista F&I Landing Visibility (PA-1B): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
