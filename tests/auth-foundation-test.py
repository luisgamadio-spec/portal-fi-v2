#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTH FOUNDATION Phase 2B -- deterministic auth/authorization test.

Drives the REAL V2 shell/router/auth-core/login end to end against a
mocked Supabase client injected via Playwright's add_init_script
(BEFORE the real @supabase/supabase-js SDK and any V2 script runs),
so window.supabase.createClient() returns a fully-controlled fake
client -- no real network call, no real Supabase project touched, 0
credentials anywhere in this file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (AUTH FOUNDATION Phase 2C Gate 8/9 -- do not
introduce a new port convention; 8080 is the established one).
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
BASE = "http://127.0.0.1:8080/portal-next-v2/index.html"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


# Config that makes auth-boundary.js activate (isAuthConfigured=true)
# and points window.supabase.createClient() at our mock -- fake
# host/key, never a real project.
CONFIG_SCRIPT = """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-key',
  textEndpoint: null
};
"""

# One flexible mock, its behavior driven entirely by window.__MOCK__,
# set by CONFIG_SCRIPT + a per-scenario override appended before it.
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
          getSession: function () {
            window.__MOCK_CALLS__.getSession++;
            return ok({ session: fakeSession });
          },
          signInWithPassword: function (creds) {
            window.__MOCK_CALLS__.signIn++;
            if (window.__MOCK__.loginShouldFail) {
              return fail(window.__MOCK__.loginErrorMessage || 'Invalid login credentials');
            }
            fakeSession = { access_token: 'mock-token', user: { id: 'auth-user-1' } };
            return ok({ session: fakeSession });
          },
          onAuthStateChange: function (cb) { listeners.push(cb); return { data: { subscription: { unsubscribe: function () {} } } } ; },
          signOut: function () {
            fakeSession = null;
            listeners.forEach(function (cb) { cb('SIGNED_OUT', null); });
            return Promise.resolve({ error: null });
          }
        },
        rpc: function (name) {
          window.__MOCK_CALLS__.rpc.push(name);
          if (name === 'usuario_logado_fi') {
            if (window.__MOCK__.profileShouldFail) return fail('boom');
            if (!window.__MOCK__.profileRow) return ok([]);
            return ok([window.__MOCK__.profileRow]);
          }
          if (name === 'portal_modulos_permitidos') {
            if (window.__MOCK__.permissionsShouldFail) return fail('boom');
            return ok(window.__MOCK__.allowedModuleIds || []);
          }
          return ok(null);
        }
      };
    }
  };
})();
"""


# Painel Master Phase 2B, Gate 0/4 -- network tripwire: a deterministic,
# automatic proof that this suite never reaches a real backend, rather
# than relying solely on route.abort() to silently prevent it. Any
# request whose host matches a real Supabase project or Cloudflare
# Turnstile is recorded here and asserted empty at the very end of
# main() -- if the CDN-block below (or any future page created outside
# new_page()) ever fails to keep the mock authoritative, this makes the
# whole suite fail loudly instead of masking a real network call behind
# a passing-looking captcha/auth-state assertion (exactly how the
# Painel Master Phase 2A investigation's own throwaway repro script
# missed this: it never had this or the route-block, so a real
# signInWithPassword reached yacqlelpzchcotgngwbh.supabase.co
# undetected).
# Listens on "requestfinished" specifically, not "request" -- an
# aborted request (this file's own **/supabase-js@* block) still
# fires a "request" event even though zero bytes reach a real server;
# "requestfinished" only fires for a request that was NOT aborted, the
# actual danger signal this tripwire exists to catch.
REAL_NETWORK_TRIPWIRE_HOSTS = ("supabase.co", "challenges.cloudflare.com")
real_network_hits = []


def _install_tripwire(page):
    page.on("requestfinished", lambda req: real_network_hits.append(req.url)
            if any(h in req.url for h in REAL_NETWORK_TRIPWIRE_HOSTS) else None)


def new_page(browser, mock_state, viewport=None):
    page = browser.new_page(viewport=viewport or {"width": 1366, "height": 800})
    _install_tripwire(page)
    # The real @supabase/supabase-js UMD bundle (index.html's own CDN
    # <script>) loads AFTER add_init_script's injected scripts (normal
    # document order) and unconditionally reassigns window.supabase,
    # clobbering the mock. Block that one request so the mock stays
    # authoritative -- everything else on the page loads normally.
    page.route("**/supabase-js@*", lambda route: route.abort())
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script("window.__MOCK__ = " + mock_state + ";")
    page.add_init_script(MOCK_CLIENT_SCRIPT)
    return page


def wait_state(page, state, timeout_ms=3000):
    page.wait_for_function(
        "window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === " + repr(state).replace("'", '"'),
        timeout=timeout_ms,
    )


MASTER_ROW = "{usuario_id:'u1', auth_user_id:'auth-user-1', nome:'Master Demo', perfil:'MASTER', loja:'TODAS', status:'MASTER', ativo:true}"
VENDEDOR_ROW = "{usuario_id:'u2', auth_user_id:'auth-user-1', nome:'Vendedor Demo', perfil:'VENDEDOR', loja:'Barra Funda', status:'NOVOS', ativo:true}"
ANALISTA_ROW = "{usuario_id:'u3', auth_user_id:'auth-user-1', nome:'Analista Demo', perfil:'ANALISTA', loja:'', status:'NOVOS/SEMINOVOS', ativo:true}"


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: boot, no session -> Login ----------
        page = new_page(browser, "{initialSession: null}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        check("1: no session -> SIGNED_OUT", True)
        check("2: Login form visible", not page.is_hidden("#nxLoginRoot"))
        check("3: authenticated shell hidden", page.is_hidden("#nxRoot"))
        page.close()

        # ---------- 4: invalid credentials ----------
        page = new_page(browser, "{initialSession: null, loginShouldFail: true, loginErrorMessage: 'Invalid login credentials'}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "wrong")
        page.click("#loginSubmit")
        wait_state(page, "INVALID_CREDENTIALS")
        check("4: invalid credentials -> INVALID_CREDENTIALS", True)
        check("5: error message shown, non-technical", "inválid" in page.inner_text("#loginStatus").lower())
        page.close()

        # ---------- 6: missing profile ----------
        page = new_page(browser, "{initialSession: null, profileRow: null}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "NO_PORTAL_PROFILE")
        check("6: missing usuarios row -> NO_PORTAL_PROFILE", True)
        page.close()

        # ---------- 7: permission RPC failure -> fail-closed ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + VENDEDOR_ROW + ", permissionsShouldFail: true}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        allowed = page.evaluate("window.NX_AUTH_CORE.getContext().allowedModuleIds")
        check("7: permission RPC failure -> allowedModuleIds is empty (fail-closed, not fail-open)", allowed == [])
        page.close()

        # ---------- 8-12: successful login as VENDEDOR, matrix allow/deny, direct-hash guard ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + VENDEDOR_ROW + ", allowedModuleIds: ['gestao']}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        check("8: successful login -> AUTHORIZED", True)
        check("9: authenticated shell visible after login", not page.is_hidden("#nxRoot"))
        check("10: Login hidden after login", page.is_hidden("#nxLoginRoot"))
        check("11: default destination after login is Landing", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")

        page.evaluate("window.NX_ROUTER.navigate('gestao')")
        page.wait_for_timeout(300)
        check("12: PERMISSION_MATRIX allowed module (gestao) reachable", "gestao" in (page.evaluate("window.location.hash")))

        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(300)
        check("13: PERMISSION_MATRIX/MASTER_ONLY denied module (shell-admin, VENDEDOR) redirects to landing", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")

        page.evaluate("window.NX_ROUTER.navigate('score')")
        page.wait_for_timeout(300)
        check("14: unmapped matrix module (score, not in allowedModuleIds) redirects to landing", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")

        # ---------- 15: security -- forging isMaster client-side has no effect ----------
        page.evaluate("try { window.NX_AUTH_CORE.getContext().isMaster = true; } catch (e) {}")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(300)
        forged_still_denied = page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing"
        check("15: mutating context.isMaster client-side does not unlock MASTER_ONLY (guard re-reads context fresh each check)", forged_still_denied)

        # ---------- 16: logout ----------
        page.click("#pUserLogoutBtn")
        wait_state(page, "SIGNED_OUT")
        check("16: logout -> SIGNED_OUT", True)
        check("17: Login re-shown after logout", not page.is_hidden("#nxLoginRoot"))
        check("18: shell hidden again after logout", page.is_hidden("#nxRoot"))
        page.close()

        # ---------- 19: MASTER allowed everywhere incl. MASTER_ONLY ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + MASTER_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "master@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(300)
        check("19: MASTER_ONLY (shell-admin) allowed for MASTER even with empty matrix list", page.evaluate("window.NX_ROUTER.currentRouteId()") == "shell-admin")
        page.evaluate("window.NX_ROUTER.navigate('central-atendimento-fi')")
        page.wait_for_timeout(300)
        # .nxStatusTag renders text-transform:uppercase -- inner_text
        # reflects rendered case ("EM BREVE"), not the source HTML's
        # mixed-case "Em breve"; match case-insensitively.
        check("20: MASTER_ONLY (central-atendimento-fi) allowed for MASTER, but NOT_MIGRATED still shows deferred placeholder, never mounts", "em breve" in page.inner_text("#nxContentOutlet").lower())
        page.close()

        # ---------- 21: ANALISTA_OR_MASTER for ANALISTA ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + ANALISTA_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "analista@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        page.evaluate("window.NX_ROUTER.navigate('painel-analista-fi')")
        page.wait_for_timeout(300)
        check("21: ANALISTA_OR_MASTER (painel-analista-fi) allowed for ANALISTA", page.evaluate("window.NX_ROUTER.currentRouteId()") == "painel-analista-fi")
        page.evaluate("window.NX_ROUTER.navigate('central-atendimento-fi')")
        page.wait_for_timeout(300)
        check("22: MASTER_ONLY denied for ANALISTA (not MASTER)", page.evaluate("window.NX_ROUTER.currentRouteId()") == "landing")
        page.close()

        # ---------- 23: direct-hash attempt while signed out never mounts the module ----------
        page = new_page(browser, "{initialSession: null}")
        page.goto(BASE + "#/shell-admin")
        wait_state(page, "SIGNED_OUT")
        check("23: direct deep-link to shell-admin while signed out renders Login, not the module", not page.is_hidden("#nxLoginRoot") and page.is_hidden("#nxRoot"))
        page.close()

        # ---------- 24: session restore (existing session) skips Login ----------
        page = new_page(browser, "{initialSession: {access_token:'tok', user:{id:'auth-user-1'}}, profileRow: " + VENDEDOR_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        wait_state(page, "AUTHORIZED")
        check("24: existing session on boot resolves straight to AUTHORIZED (no Login shown)", page.is_hidden("#nxLoginRoot") and not page.is_hidden("#nxRoot"))
        page.close()

        # ---------- 25: Intelligence getAccessToken compatibility unaffected ----------
        page = new_page(browser, "{initialSession: null, profileRow: " + MASTER_ROW + ", allowedModuleIds: []}")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "master@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        token = page.evaluate("window.NX_AUTH.getAccessToken().then(function(t){return t})")
        check("25: NX_AUTH.getAccessToken() still returns a real token post-Auth-Foundation (Intelligence compatibility)", token == "mock-token")
        page.close()

        # ---------- 26: no real credentials configured -- AUTH_NOT_CONFIGURED, no regression to pre-existing behavior ----------
        # Forced explicitly, not by omission: this dev machine may
        # already have its own gitignored intelligence-runtime-
        # config.local.js (from earlier, unrelated Intelligence work)
        # auto-loaded on localhost (index.html's own document.write
        # gate), which would override isAuthConfigured back to true
        # regardless of an add_init_script override (same
        # loads-later-and-wins ordering as the CDN SDK) -- block that
        # specific file request instead, forcing the real committed
        # default (assets/js/intelligence-runtime-config.js) to be
        # what's actually in effect.
        page = browser.new_page(viewport={"width": 1366, "height": 800})
        _install_tripwire(page)
        page.route("**/supabase-js@*", lambda route: route.abort())
        page.route("**/intelligence-runtime-config.local.js", lambda route: route.abort())
        page.goto(BASE)
        page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTH_NOT_CONFIGURED'", timeout=3000)
        check("26: default committed config (no local override) -> AUTH_NOT_CONFIGURED, guard inert, shell visible unchanged", not page.is_hidden("#nxRoot") and page.is_hidden("#nxLoginRoot"))
        page.evaluate("window.NX_ROUTER.navigate('shell-admin')")
        page.wait_for_timeout(300)
        check("27: AUTH_NOT_CONFIGURED preserves pre-Auth-Foundation reachability (shell-admin still just shows its existing NOT_MIGRATED placeholder, not blocked by auth)", page.evaluate("window.NX_ROUTER.currentRouteId()") == "shell-admin")
        page.close()

        browser.close()

    check("28: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Auth Foundation Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
