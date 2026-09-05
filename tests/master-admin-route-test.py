#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase 2A -- deterministic tests for the /admin route
guard itself (MASTER allow, ANALISTA/VENDEDOR deny, signed-out
redirect, no unauthorized content flash), driven against the REAL V2
shell/router/auth-core -- the same infrastructure already proven in
tests/auth-foundation-test.py (its own test #19/#20/#22 already cover
shell-admin's MASTER_ONLY gate structurally; this file re-proves it
now that shell-admin actually mounts real content, plus adds the
content-flash and Usuários-specific direct-hash checks that file
doesn't cover).

Mocked window.supabase client injected via add_init_script (BEFORE the
real SDK/any V2 script runs) -- no real network call, no real Supabase
project touched, 0 credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080.
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
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-key',
  textEndpoint: null
};
"""

# Identical mock shape to tests/auth-foundation-test.py's own
# MOCK_CLIENT_SCRIPT -- same real shell/router/auth-core flow, not a
# second auth-mocking mechanism.
MOCK_CLIENT_SCRIPT = """
window.__MOCK_CALLS__ = { signIn: 0, getSession: 0, rpc: [] };
(function () {
  var listeners = [];
  var fakeSession = window.__MOCK__.initialSession || null;
  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  function fail(message) { return Promise.resolve({ data: null, error: { message: message } }); }
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          getSession: function () { window.__MOCK_CALLS__.getSession++; return ok({ session: fakeSession }); },
          signInWithPassword: function () {
            window.__MOCK_CALLS__.signIn++;
            fakeSession = { access_token: 'mock-token', user: { id: 'auth-user-1' } };
            return ok({ session: fakeSession });
          },
          onAuthStateChange: function (cb) { listeners.push(cb); return { data: { subscription: { unsubscribe: function () {} } } }; },
          signOut: function () { fakeSession = null; listeners.forEach(function (cb) { cb('SIGNED_OUT', null); }); return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          window.__MOCK_CALLS__.rpc.push(name);
          if (name === 'usuario_logado_fi') {
            if (!window.__MOCK__.profileRow) return ok([]);
            return ok([window.__MOCK__.profileRow]);
          }
          if (name === 'portal_modulos_permitidos') return ok(window.__MOCK__.allowedModuleIds || []);
          return ok(null);
        }
      };
    }
  };
})();
"""


REAL_NETWORK_TRIPWIRE_HOSTS = ("supabase.co", "challenges.cloudflare.com")
real_network_hits = []


def new_page(browser, mock_state):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    # requestfinished, not request: an aborted request (the routes
    # below) still fires "request" even though zero bytes reach a real
    # server -- requestfinished only fires for one that wasn't aborted.
    page.on("requestfinished", lambda req: real_network_hits.append(req.url)
            if any(h in req.url for h in REAL_NETWORK_TRIPWIRE_HOSTS) else None)
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script("window.__MOCK__ = " + mock_state + ";")
    page.add_init_script(MOCK_CLIENT_SCRIPT)
    # shell-admin's own real read (master_admin_security_data) would hit
    # this same mocked window.supabase.rpc() dispatcher if it used that
    # transport -- but master-users-provider.js uses raw fetch(), so we
    # additionally block the real REST endpoint here to guarantee zero
    # real network regardless of which role/route this page reaches.
    page.route("**/rest/v1/rpc/master_admin_security_data*", lambda route: route.abort())
    page.route("**/rest/v1/rpc/master_listar_convites*", lambda route: route.abort())
    # CRITICAL (discovered live, this Phase): index.html loads the real
    # @supabase/supabase-js SDK from jsdelivr with a blocking, non-async
    # <script> tag BEFORE auth-boundary.js runs. That real script
    # overwrites window.supabase (this file's own add_init_script mock
    # included) with the genuine SDK namespace -- and since
    # intelligence-runtime-config.local.js points supabaseUrl at the
    # REAL production project, auth-boundary.js's own
    # window.supabase.createClient(...) then creates a REAL client,
    # and a real signInWithPassword call reaches the real backend
    # (confirmed directly, in a throwaway standalone repro script that
    # lacked this route: a real POST to
    # https://yacqlelpzchcotgngwbh.supabase.co/auth/v1/token was
    # observed, rejected by Supabase's own bot-protection as
    # CAPTCHA_FAILED). CORRECTION (Painel Master Phase 2B): this is
    # NOT a gap in tests/auth-foundation-test.py or
    # tests/turnstile-captcha-test.py -- both already carry the
    # equivalent "**/supabase-js@*" route (present since the original
    # Auth Foundation wave, `git log` confirms) and both pass cleanly
    # with a real network tripwire attached. The real network hit
    # observed in Phase 2A came from this file's own throwaway
    # diagnostic script, written without copying that established
    # protection -- a debugging methodology gap, not a product/test
    # defect. This file's own equivalent block below (and the
    # tripwire further down) is correct defense-in-depth regardless.
    page.route("**/cdn.jsdelivr.net/npm/@supabase/supabase-js**", lambda route: route.abort())
    return page


def wait_state(page, state, timeout_ms=3000):
    page.wait_for_function(
        "window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === " + repr(state).replace("'", '"'),
        timeout=timeout_ms,
    )


MASTER_ROW = "{usuario_id:'u1', auth_user_id:'auth-user-1', nome:'Master Demo', perfil:'MASTER', loja:'TODAS', status:'MASTER', ativo:true}"
VENDEDOR_ROW = "{usuario_id:'u2', auth_user_id:'auth-user-1', nome:'Vendedor Demo', perfil:'VENDEDOR', loja:'Barra Funda', status:'NOVOS', ativo:true}"
ANALISTA_ROW = "{usuario_id:'u3', auth_user_id:'auth-user-1', nome:'Analista Demo', perfil:'ANALISTA', loja:'', status:'NOVOS/SEMINOVOS', ativo:true}"


def login(page, email):
    wait_state(page, "SIGNED_OUT")
    page.fill("#loginEmail", email)
    page.fill("#loginPassword", "pass")
    page.click("#loginSubmit")
    wait_state(page, "AUTHORIZED")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: MASTER route allow, real content actually mounts ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + MASTER_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        login(page, "master@example.com")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(400)
        check("1: MASTER route allow -- shell-admin becomes the active route", page.evaluate("window.NX_ROUTER.currentRouteId()") == "shell-admin")
        # "Em breve" legitimately appears on the disabled future-section
        # nav items (Acessos/Auditoria/Revisões) as part of the REAL
        # Painel Master page (Gate 9's own structure) -- it is the
        # generic shell.js placeholder page (a *different* full-page
        # state, "Em preparação para o Portal V2") this check must rule
        # out, not that literal substring.
        content_text = page.inner_text("#nxContentOutlet")
        check("1b: MASTER sees real Painel Master content, not the generic shell placeholder", "Painel Master" in content_text and "Em preparação para o Portal V2" not in content_text)
        page.close()

        # ---------- 2: VENDEDOR route deny ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + VENDEDOR_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        login(page, "vendedor@example.com")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(400)
        check("2: VENDEDOR route deny -- redirected to landing, never shell-admin", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")
        check("2b: no Painel Master content anywhere in the DOM for VENDEDOR", "Painel Master" not in page.inner_text("#nxContentOutlet"))
        page.close()

        # ---------- 3: ANALISTA route deny ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + ANALISTA_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        login(page, "analista@example.com")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(400)
        check("3: ANALISTA route deny (MASTER_ONLY, not ANALISTA_OR_MASTER) -- redirected to landing", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")
        page.close()

        # ---------- 4: signed-out direct hash -> Login, never mounts ----------
        page = new_page(browser, "{initialSession: null}")
        page.goto(BASE + "#/shell-admin")
        page.wait_for_timeout(400)
        check("4: signed-out direct #/shell-admin -> Login shown, module never mounted", not page.is_hidden("#nxLoginRoot") and "Painel Master" not in page.inner_text("body"))
        page.close()

        # ---------- 5: no unauthorized content flash (VENDEDOR direct hash from a fresh load) ----------
        page = new_page(browser, "{initialSession: {access_token:'tok', user:{id:'auth-user-1'}}, profileRow: " + VENDEDOR_ROW + ", allowedModuleIds: []}")
        page.goto(BASE + "#/shell-admin")
        # Check as early as possible after navigation, before any settle
        # wait -- content must never appear even transiently (authorize
        # THEN mount, never render-then-hide).
        page.wait_for_timeout(50)
        early_text = page.inner_text("#nxContentOutlet") if page.query_selector("#nxContentOutlet") else ""
        check("5: VENDEDOR direct-hash to shell-admin -- zero admin content at any point, not even transiently", "Painel Master" not in early_text)
        page.wait_for_timeout(400)
        check("5b: settles on landing, confirming the guard ran (not just slow to render)", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")
        page.close()

        # ---------- 35: future subroute architecture -- disabled sections never expose unfinished pages ----------
        # Painel Master Phase PM-4C.2: Pendências Cadastrais is now a real,
        # implemented, active section (its own module + deterministic
        # suite, master-pendencias-provider-test.py) alongside Usuários
        # (Phase 2A), Acessos aos Módulos (Phase 3B) and Auditoria
        # (Phase PM-4B) -- all four are now active. Revisões Cadastrais'
        # own disabled "Em breve" placeholder is RETIRED this Phase (per
        # its own Gate 2/15 and the PM-4C.1 human product decision that
        # it is permanently superseded, never migrated as a separate
        # surface) -- there is no longer any disabled section at all.
        # Updated here because the underlying product behavior genuinely
        # changed this Phase, not because the test was wrong before.
        page = new_page(browser, "{initialSession: null, profileRow: " + MASTER_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        login(page, "master@example.com")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(400)
        section_text = page.inner_text("#nxContentOutlet")
        check("35: Usuários, Acessos aos Módulos, Pendências Cadastrais and Auditoria are all active sections; Revisões Cadastrais no longer appears at all",
              "Acessos aos Módulos" in section_text and "Pendências Cadastrais" in section_text and "Auditoria" in section_text and "Revisões Cadastrais" not in section_text)
        # zero disabled placeholders remain -- Revisões was the only one.
        disabled_count = page.eval_on_selector_all(".maSectionItemDisabled", "els => els.length")
        check("35b: zero disabled sections remain (Revisões' placeholder fully retired, not merely relabeled)", disabled_count == 0)
        acessos_is_link = page.eval_on_selector('[data-section="acessos"]', "el => el.tagName") if page.query_selector('[data-section="acessos"]') else None
        check("35c: Acessos aos Módulos is a real, clickable nav item (a <button>, not a disabled span)", acessos_is_link == "BUTTON")
        auditoria_is_link = page.eval_on_selector('[data-section="auditoria"]', "el => el.tagName") if page.query_selector('[data-section="auditoria"]') else None
        check("35d: Auditoria is now a real, clickable nav item (a <button>, not a disabled span)", auditoria_is_link == "BUTTON")
        pendencias_is_link = page.eval_on_selector('[data-section="pendenciasCadastrais"]', "el => el.tagName") if page.query_selector('[data-section="pendenciasCadastrais"]') else None
        check("35e: Pendências Cadastrais is a real, clickable nav item (a <button>, not a disabled span)", pendencias_is_link == "BUTTON")
        page.close()

        # ---------- 37: breadcrumb reflects the real module, not the
        # stale sub-feature name (Painel Master Phase PM-5B, Gate 18) ----------
        # PM-5A found the registry's shell-admin `landingTitle` still said
        # "Auditoria / Painel Master" -- a leftover from when Auditoria was
        # the module's most recently-added sub-feature -- rendered verbatim
        # into #pBreadcrumb (landing.js renderTopBar) regardless of which of
        # the module's 4 internal sections (Usuários/Acessos/Pendências/
        # Auditoria) is actually active. Fixed at the data level (registry
        # `landingTitle` -> "Painel Master"); this asserts the REAL rendered
        # breadcrumb, not just the registry string (grep alone would not
        # catch a stale cache or a second hardcoded copy elsewhere).
        page = new_page(browser, "{initialSession: null, profileRow: " + MASTER_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        login(page, "master@example.com")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(400)
        breadcrumb_text = page.inner_text("#pBreadcrumb")
        check("37: breadcrumb no longer shows the stale 'Auditoria / Painel Master' label", "Auditoria / Painel Master" not in breadcrumb_text)
        check("37b: breadcrumb shows the corrected 'Painel Master' current-location label", page.inner_text("#pBreadcrumb .pBreadcrumbCurrent") == "Painel Master")
        check("37c: breadcrumb still shows the fixed 'Portal F&I' product tag ahead of it (format unchanged, no duplication)", page.inner_text("#pBreadcrumb .pBreadcrumbTag").upper() == "PORTAL F&I")
        # section switch does not change the breadcrumb (module-level label,
        # not section-level -- a single static string cannot correctly name
        # one of 4 internal sections, so PM-5B intentionally names the module).
        if page.query_selector('[data-section="auditoria"]'):
            page.click('[data-section="auditoria"]')
            page.wait_for_timeout(200)
        check("37d: breadcrumb unchanged after switching to the Auditoria section (module-level label, by design)", page.inner_text("#pBreadcrumb .pBreadcrumbCurrent") == "Painel Master")
        page.close()

        browser.close()

    check("36: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Admin Route Guard: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
