#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTH FOUNDATION Phase 3B -- deterministic Turnstile/CAPTCHA contract
test.

Drives the REAL V2 Login/auth-core/auth-boundary end to end against a
mocked Supabase client (same pattern as auth-foundation-test.py) AND a
mocked window.turnstile global -- 0 real Cloudflare network calls, 0
real Supabase project touched, 0 credentials anywhere in this file.

**/intelligence-runtime-config.local.js is blocked on every page here
(same technique auth-foundation-test.py already uses for its own
AUTH_NOT_CONFIGURED scenario): that file is loaded unconditionally by
index.html on localhost and would otherwise silently override
turnstileSiteKey regardless of this test's own add_init_script config
-- exactly the interference that broke auth-foundation-test.py earlier
in this Wave until the real site key was reverted out of that ambient
file.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080 (same convention as auth-foundation-test.py).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/index.html"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


CONFIG_SCRIPT_REAL = """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-key',
  turnstileSiteKey: '1x00000000000000000000AA',
  textEndpoint: null
};
"""

CONFIG_SCRIPT_MOCK_MODE = """
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'fixture',
  supabaseUrl: 'https://mock.invalid',
  supabasePublishableKey: 'mock-key',
  textEndpoint: null
};
"""

# Same fake Supabase client factory as auth-foundation-test.py:
# signIn resolves/rejects per window.__MOCK__, captures the exact
# credentials object it was called with so the test can assert
# captchaToken really reached the SDK call (Gate 15/21).
MOCK_CLIENT_SCRIPT = """
window.__MOCK_CALLS__ = { signInCreds: null };
(function () {
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          signInWithPassword: function (creds) {
            window.__MOCK_CALLS__.signInCreds = creds;
            var m = window.__MOCK__;
            if (m.loginShouldFail) {
              return Promise.resolve({ data: null, error: { message: m.loginErrorMessage || 'error' } });
            }
            return Promise.resolve({ data: { session: { access_token: 'tok', user: {} } }, error: null });
          },
          getSession: function () {
            return Promise.resolve({ data: { session: null } });
          },
          onAuthStateChange: function () { return { data: { subscription: { unsubscribe: function () {} } } }; },
          signOut: function () { return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          if (name === 'usuario_logado_fi') {
            return Promise.resolve({ data: [{ usuario_id: 'u1', auth_user_id: 'a1', nome: 'Demo', perfil: 'VENDEDOR', loja: 'X', status: 'NOVOS', ativo: true }], error: null });
          }
          return Promise.resolve({ data: [], error: null });
        }
      };
    }
  };
})();
"""

# window.turnstile mock: render()/execute() drive the exact same
# callback/error-callback/expired-callback contract login.js's real
# renderAndExecuteTurnstile() wires up to (Gate 7's verified shape) --
# no real Cloudflare script ever loads, deterministic and instant.
def turnstile_mock_script(mode, token="mock-turnstile-token-xyz"):
    return """
window.__TURNSTILE_RENDER_CALLS__ = 0;
window.__TURNSTILE_EXECUTE_CALLS__ = 0;
window.turnstile = {
  render: function (host, opts) {
    window.__TURNSTILE_RENDER_CALLS__ += 1;
    window.__turnstileOpts = opts;
    return 'widget-' + window.__TURNSTILE_RENDER_CALLS__;
  },
  execute: function () {
    window.__TURNSTILE_EXECUTE_CALLS__ += 1;
    var opts = window.__turnstileOpts;
    setTimeout(function () {
      if ('%s' === 'success') opts.callback('%s');
      else if ('%s' === 'error') opts['error-callback']();
      else if ('%s' === 'expired') opts['expired-callback']();
      // 'hang': never calls back -- exercises the 60s timeout path;
      // not used in this deterministic suite (would make it slow).
    }, 5);
  },
  remove: function () {}
};
""" % (mode, token, mode, mode)


def new_page(browser, config_script, mock_state, turnstile_script=None):
    page = browser.new_page(viewport={"width": 1366, "height": 800})
    page.route("**/supabase-js@*", lambda route: route.abort())
    # Both the committed default (assets/js/intelligence-runtime-
    # config.js) and the ambient .local.js are real <script> tags that
    # load AFTER add_init_script's injected assignment and unconditionally
    # overwrite window.NX_INTELLIGENCE_CONFIG again (document order) --
    # exactly the ordering that made auth-foundation-test.py's own
    # CONFIG_SCRIPT a no-op there too, silently relying on whatever
    # .local.js happens to contain on this machine. Block both so this
    # test's own config is the only writer and is fully portable.
    page.route("**/intelligence-runtime-config.js", lambda route: route.abort())
    page.route("**/intelligence-runtime-config.local.js", lambda route: route.abort())
    page.add_init_script(config_script)
    page.add_init_script("window.__MOCK__ = " + mock_state + ";")
    page.add_init_script(MOCK_CLIENT_SCRIPT)
    if turnstile_script:
        page.add_init_script(turnstile_script)
    else:
        # No window.turnstile mock and no real Cloudflare reachable
        # (route below) -- exercises the widget/script load-failure
        # path deterministically.
        page.route("**/challenges.cloudflare.com/**", lambda route: route.abort())
    return page


def wait_state(page, state, timeout_ms=3000):
    page.wait_for_function(
        "window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === " + repr(state).replace("'", '"'),
        timeout=timeout_ms,
    )


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: mock mode (no turnstileSiteKey) -> 0 Cloudflare dependency ----------
        page = new_page(browser, CONFIG_SCRIPT_MOCK_MODE, "{}", turnstile_script="window.turnstile = undefined;")
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        check("1: mock mode -> no #loginTurnstile host rendered", page.eval_on_selector("body", "() => !document.getElementById('loginTurnstile')"))
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        check("2: mock mode login succeeds with 0 Cloudflare dependency", True)
        check("3: mock mode -> captchaToken not sent (options undefined)", page.evaluate("window.__MOCK_CALLS__.signInCreds.options") is None)
        page.close()

        # ---------- 4: real mode + widget success -> captchaToken reaches SDK ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL, "{}", turnstile_script=turnstile_mock_script("success"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        check("4: real mode -> #loginTurnstile host present", page.eval_on_selector("body", "() => !!document.getElementById('loginTurnstile')"))
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "AUTHORIZED")
        check("5: real mode + successful widget -> login reaches AUTHORIZED", True)
        check("6: captchaToken forwarded to SDK inside creds.options (Gate 7 verified shape)",
              page.evaluate("window.__MOCK_CALLS__.signInCreds.options && window.__MOCK_CALLS__.signInCreds.options.captchaToken") == "mock-turnstile-token-xyz")
        check("7: exactly one widget rendered, one execute call (no duplicates, Gate 10)",
              page.evaluate("window.__TURNSTILE_RENDER_CALLS__") == 1 and page.evaluate("window.__TURNSTILE_EXECUTE_CALLS__") == 1)
        check("8: token never written to localStorage/sessionStorage",
              "mock-turnstile-token-xyz" not in page.evaluate("JSON.stringify(window.localStorage) + JSON.stringify(window.sessionStorage)"))
        page.close()

        # ---------- 9: real mode + widget error-callback -> CAPTCHA never reaches Supabase ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL, "{}", turnstile_script=turnstile_mock_script("error"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        page.wait_for_timeout(500)
        check("9: widget error-callback -> signInWithPassword NEVER called (Gate 14)", page.evaluate("window.__MOCK_CALLS__.signInCreds") is None)
        check("10: state stays SIGNED_OUT (auth-core.login() never invoked)", page.evaluate("window.NX_AUTH_CORE.getState()") == "SIGNED_OUT")
        check("11: Login shows a security-check error, not a blank/stuck form", "segurança" in page.inner_text("#loginStatus").lower())
        check("12: submit re-enabled after captcha failure (not stuck)", not page.is_disabled("#loginSubmit"))
        page.close()

        # ---------- 13: real mode + widget expired-callback ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL, "{}", turnstile_script=turnstile_mock_script("expired"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        page.wait_for_timeout(500)
        check("13: expired-callback -> signInWithPassword NEVER called", page.evaluate("window.__MOCK_CALLS__.signInCreds") is None)
        page.close()

        # ---------- 14: real mode + script load failure (no window.turnstile, Cloudflare blocked) ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL, "{}")  # no turnstile_script -> real CF host blocked
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        page.wait_for_timeout(21000)  # loadTurnstileScript()'s own 20s internal timeout
        check("14: script load failure -> signInWithPassword NEVER called", page.evaluate("window.__MOCK_CALLS__.signInCreds") is None)
        check("15: state stays SIGNED_OUT after script load failure", page.evaluate("window.NX_AUTH_CORE.getState()") == "SIGNED_OUT")
        page.close()

        # ---------- 17: Supabase itself rejects with captcha_failed -> CAPTCHA_FAILED state, distinct message ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL,
                         "{loginShouldFail: true, loginErrorMessage: 'captcha protection: request disallowed (no captcha_token found)'}",
                         turnstile_script=turnstile_mock_script("success"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "pass")
        page.click("#loginSubmit")
        wait_state(page, "CAPTCHA_FAILED")
        check("16: Supabase captcha_failed -> auth-core reaches CAPTCHA_FAILED (Gate 16)", True)
        check("17: CAPTCHA_FAILED message distinct from generic RPC_ERROR wording, no raw provider text leaked",
              "segurança" in page.inner_text("#loginStatus").lower() and "captcha_token" not in page.inner_text("#loginStatus").lower())
        page.close()

        # ---------- 19: invalid credentials still classified correctly in real mode (not swallowed by captcha path) ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL,
                         "{loginShouldFail: true, loginErrorMessage: 'Invalid login credentials'}",
                         turnstile_script=turnstile_mock_script("success"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "wrong")
        page.click("#loginSubmit")
        wait_state(page, "INVALID_CREDENTIALS")
        check("18: real mode + valid captcha + wrong password -> INVALID_CREDENTIALS (not CAPTCHA_FAILED)", True)
        page.close()

        # ---------- 20: retry after failure requests a fresh token (Gate 17) ----------
        page = new_page(browser, CONFIG_SCRIPT_REAL,
                         "{loginShouldFail: true, loginErrorMessage: 'Invalid login credentials'}",
                         turnstile_script=turnstile_mock_script("success"))
        page.goto(BASE)
        wait_state(page, "SIGNED_OUT")
        page.fill("#loginEmail", "user@example.com")
        page.fill("#loginPassword", "wrong")
        page.click("#loginSubmit")
        wait_state(page, "INVALID_CREDENTIALS")
        page.fill("#loginPassword", "wrong-again")
        page.click("#loginSubmit")
        page.wait_for_timeout(300)
        check("19: second submit renders a second, fresh widget (no stale token reuse)", page.evaluate("window.__TURNSTILE_RENDER_CALLS__") == 2)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Turnstile/CAPTCHA Contract Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
