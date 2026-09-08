#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CA-1 -- proves the /central-atendimento-fi route guard AND real shell
integration (router -> auth-core -> registry -> shell dispatch ->
module mount), driven against the REAL V2 shell -- same infrastructure
and mocking pattern as tests/master-admin-route-test.py. This is
deliberately separate from tests/central-atendimento-fi-test.py (which
proves the module's OWN internal contract in isolation via the test
harness) -- this file instead proves the module is actually reachable,
correctly gated, and free of console errors inside the real app shell.

Mocked window.supabase client injected via add_init_script -- no real
network call, no real Supabase project touched, 0 credentials anywhere
in this file.

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
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-key',
  textEndpoint: null
};
"""

# Identical mock shape to tests/master-admin-route-test.py's own
# MOCK_CLIENT_SCRIPT -- same real shell/router/auth-core flow.
MOCK_CLIENT_SCRIPT = """
window.__MOCK_CALLS__ = { signIn: 0, getSession: 0, rpc: [] };
(function () {
  var listeners = [];
  var fakeSession = window.__MOCK__.initialSession || null;
  function ok(data) { return Promise.resolve({ data: data, error: null }); }
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
          // gestor_listar_analistas_fi / gestor_listar_historico_atendimentos_fi
          // (called via raw fetch by the real provider, not this RPC
          // dispatcher -- routed/aborted separately below so this
          // integration test never depends on their real response shape).
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
    page.on("requestfinished", lambda req: real_network_hits.append(req.url)
            if any(h in req.url for h in REAL_NETWORK_TRIPWIRE_HOSTS) else None)
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script("window.__MOCK__ = " + mock_state + ";")
    page.add_init_script(MOCK_CLIENT_SCRIPT)
    # central-atendimento-fi-real-provider.js uses raw fetch(), not the
    # mocked window.supabase.rpc() dispatcher -- abort its real REST
    # endpoints so this route/auth integration test never depends on a
    # real (or even fixture) response shape from them.
    page.route("**/rest/v1/rpc/gestor_listar_analistas_fi*", lambda route: route.abort())
    page.route("**/rest/v1/rpc/gestor_listar_historico_atendimentos_fi*", lambda route: route.abort())
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

        # ---------- 1: MASTER can reach the real route, module mounts ----------
        page = new_page(browser, "{initialSession:null, profileRow:" + MASTER_ROW + ", allowedModuleIds:['centralAtendimentoFi','painelMaster']}")
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(BASE)
        login(page, "master@demo.local")
        page.evaluate("location.hash = '#/central-atendimento-fi'")
        page.wait_for_selector(".caPage", timeout=5000)
        check("1a: MASTER reaches the real route, module mounts (.caPage present)", True)
        check("1b: real page title rendered", "Central de Atendimento F&I" in page.inner_text(".modTitle"))
        check("1c: tab navigation rendered (3 tabs)", page.evaluate("document.querySelectorAll('.modTabGroup .modTab').length") == 3)
        page.wait_for_timeout(300)
        check("1d: zero uncaught page errors after mount", len(errors) == 0)
        page.close()

        # ---------- 2: VENDEDOR denied (MASTER_ONLY, not PERMISSION_MATRIX/other) ----------
        page = new_page(browser, "{initialSession:null, profileRow:" + VENDEDOR_ROW + ", allowedModuleIds:[]}")
        page.goto(BASE)
        login(page, "vendedor@demo.local")
        page.evaluate("location.hash = '#/central-atendimento-fi'")
        page.wait_for_timeout(600)
        check("2a: VENDEDOR direct-hash to central-atendimento-fi -- module never mounts", page.evaluate("!document.querySelector('.caPage')"))
        check("2b: redirected to landing", "landing" in page.evaluate("location.hash"))
        page.close()

        # ---------- 3: ANALISTA denied too (MASTER_ONLY differs from painel-analista-fi's ANALISTA_OR_MASTER) ----------
        page = new_page(browser, "{initialSession:null, profileRow:" + ANALISTA_ROW + ", allowedModuleIds:['painelAnalistaFi']}")
        page.goto(BASE)
        login(page, "analista@demo.local")
        page.evaluate("location.hash = '#/central-atendimento-fi'")
        page.wait_for_timeout(600)
        check("3a: ANALISTA direct-hash to central-atendimento-fi -- module never mounts (MASTER_ONLY, unlike painel-analista-fi)", page.evaluate("!document.querySelector('.caPage')"))
        check("3b: redirected to landing", "landing" in page.evaluate("location.hash"))
        page.close()

        # ---------- 4: signed-out direct hash -- Login shown, module never mounted ----------
        page = new_page(browser, "{initialSession:null, profileRow:null, allowedModuleIds:[]}")
        page.goto(BASE + "#/central-atendimento-fi")
        page.wait_for_timeout(600)
        check("4: signed-out direct #/central-atendimento-fi -- Login shown, module never mounted", page.evaluate("!document.querySelector('.caPage')") and page.evaluate("!!document.getElementById('loginEmail')"))
        page.close()

        # ---------- 5: real network tripwire across the whole suite ----------
        check("5: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile", len(real_network_hits) == 0)

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Central de Atendimento F&I Route Guard (CA-1): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
