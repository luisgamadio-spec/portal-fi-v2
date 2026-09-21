#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5E -- deterministic tests for the Configurações
module (master-config-provider.js, master-config-view-model.js,
shell-admin.js), mounted via the same lightweight harness used by every
sibling Painel Master surface.

CRITICAL SAFETY NOTE (unlike Gestão de Bases/Simuladores): there is NO
homologation-mode gate for this capability -- confirmed live, not
assumed, by direct reading of master_update_portal_config's real
function body. Every write is REAL against the real backend on any
host. This suite therefore mocks the transport at the network layer
for 100% of its checks (never calling the real RPC) and asserts a
network tripwire proving zero real Supabase requests, exactly like
every other suite in this codebase -- there is no "prove the
simulation" test here because there is no simulation to prove; the
proof obligation is instead "this harness never reaches the real
backend at all", which the tripwire covers.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# V2-INT-01 -- pre-existing staleness fix (same class of bug already
# fixed in several sibling test files this session): BASE was still
# hardcoded to the OLD parent-dir-rooted topology (confirmed via direct
# curl: the old path 404s, this one 200s); this worktree is served
# root-at-worktree. Discovered only because this wave's own new tests
# needed to actually run to be verified -- unrelated to and pre-dating
# PM-WRITE-SAFETY-2 itself.
BASE = "http://127.0.0.1:8080/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
CFG_READ_URL = "https://mock.invalid/rest/v1/rpc/operational_portal_config"
CFG_WRITE_URL = "https://mock.invalid/rest/v1/rpc/master_update_portal_config"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


# PM-WRITE-SAFETY-2 -- env_name defaults to AUTHORIZED_PRODUCTION so
# every PRE-EXISTING call site (new_page(browser), no args) keeps
# exercising exactly the real-write behavior it was already written and
# validated against -- this harness never loads environment-guard.js at
# all (confirmed: zero reference to it in _master-users-harness.html),
# so window.NX_ENVIRONMENT would otherwise stay undefined and the new
# write-safety gate would default to non-production (simulated) for
# every existing test, silently invalidating them. New tests below pass
# a different env_name explicitly to exercise the other 3 states.
def auth_mock_script(token="mock-access-token-abc", env_name="AUTHORIZED_PRODUCTION"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
window.NX_ENVIRONMENT = { name: %s, hostname: 'pm-write-safety-test', allowed: true };
""" % (("'" + token + "'") if token else "null", _json.dumps(env_name))


def new_page(browser, token="mock-access-token-abc", env_name="AUTHORIZED_PRODUCTION"):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script(token, env_name))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def goto_config(page):
    page.wait_for_selector('[data-section="configuracoes"]', timeout=5000)
    page.click('[data-section="configuracoes"]')
    page.wait_for_selector(".gbGrid, .modErrorState", timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def counting_route(calls, status, body_fn):
    def handler(route):
        post = None
        try:
            post = _json.loads(route.request.post_data) if route.request.post_data else None
        except Exception:
            post = route.request.post_data
        calls.append(post)
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body_fn(post)))
    return handler


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)

        # ---------- 1-6: all 13 real settings render, real-value merge, no invented key ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(CFG_READ_URL + "*", json_route(200, {"rows": [
            {"chave": "share_minimo", "valor": "40"},
            {"chave": "permissoes_modulos_dinamicas", "valor": "true"},  # unrelated key, must be ignored
        ]}))
        mount(page)
        goto_config(page)
        check("1: exactly the 13 real V1 settings render, nothing invented, nothing dropped",
              len(page.query_selector_all(".cfgCard")) == 13)
        body_text = page.inner_text("body")
        check("2: an unrelated key returned by the RPC (permissoes_modulos_dinamicas) is silently ignored, exactly like V1's own hasOwnProperty filter",
              "permissoes_modulos_dinamicas" not in body_text and "dinamicas" not in body_text.lower())
        check("3: a key WITH a real row shows that value (40), not its hardcoded default", "40" in page.inner_text(".cfgCard >> nth=0"))
        # bonus_spf_analista has no row in this fixture -> must show its real documented default (150) and the "never customized" note
        bonus_card_text = None
        for i in range(13):
            t = page.inner_text(f".cfgCard >> nth={i}")
            if "Bônus SPF Analista" in t:
                bonus_card_text = t
                break
        check("4: a key with NO row shows its real hardcoded default (150), matching the live-confirmed current production state", bonus_card_text and "150" in bonus_card_text)
        check("4b: a never-customized setting is labeled as such, not presented as if it were an explicit saved value", bonus_card_text and "Nunca personalizado" in bonus_card_text)
        for w in (1440, 1024, 768, 390):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(80)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("5 (w=%d): no horizontal overflow on the settings grid" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.close()

        # ---------- 6-12: edit -> confirm (before/after) -> real save -> canonical refresh ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(CFG_READ_URL + "*", json_route(200, {"rows": [{"chave": "share_minimo", "valor": "40"}]}))
        write_calls = []
        page.route(CFG_WRITE_URL + "*", counting_route(write_calls, 200, lambda p: {"status": "OK", "chave": p["p_key"], "valor": p["p_value"]}))
        mount(page)
        goto_config(page)
        page.click(".cfgEditBtn >> nth=0")
        page.wait_for_selector("#cfgEditInput", timeout=5000)
        check("6: editing does not immediately write anything (Gate 46: read -> explicit Editar -> changed -> confirm -> save)", len(write_calls) == 0)
        page.fill("#cfgEditInput", "45")
        page.click(".cfgSaveBtn")
        page.wait_for_selector("#cfgConfirmSaveBtn", timeout=5000)
        confirm_text = page.inner_text("#nxModalRoot")
        check("7: confirmation shows an explicit BEFORE value (40)", "40" in confirm_text)
        check("7b: confirmation shows an explicit AFTER value (45)", "45" in confirm_text)
        # PM-WRITE-SAFETY-2 -- the prior unconditional "não há simulação"
        # claim is now only true in production; this test runs under the
        # default AUTHORIZED_PRODUCTION environment (new_page's own
        # default), so the accurate production-mode warning ("gravada
        # imediatamente... afeta todos os usuários") is what must appear
        # here -- corrected to match the intentionally-updated copy
        # (Section 17), not weakened.
        check("7c: confirmation explicitly warns the write is real and immediate in production (Gate 39 -- must not be hidden from the Human)",
              "gravada imediatamente" in confirm_text.lower())
        check("8: still zero write calls before explicit confirmation", len(write_calls) == 0)
        page.click("#cfgConfirmSaveBtn")
        page.wait_for_selector("#cfgSuccessCloseBtn", timeout=5000)
        check("9: exactly one write call, matching the live RPC's real argument names verbatim", len(write_calls) == 1
              and set(write_calls[0].keys()) == {"p_key", "p_value", "p_description"})
        check("9b: the write payload carries the exact key and new numeric value, never a stringified/percent-shifted value", write_calls[0]["p_key"] == "share_minimo" and write_calls[0]["p_value"] == 45)
        page.click("#cfgSuccessCloseBtn")
        page.wait_for_selector(".gbGrid", timeout=5000)
        check("10: after success, the screen returns to canonical read state (not stuck showing stale optimistic local state)", page.query_selector(".cfgEditRow") is None)
        page.close()

        # ---------- 11-13: percent-cap validation (client-side hint, never the authority) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(CFG_READ_URL + "*", json_route(200, {"rows": []}))
        blocked_calls = []
        page.route(CFG_WRITE_URL + "*", counting_route(blocked_calls, 200, lambda p: {"status": "OK"}))
        mount(page)
        goto_config(page)
        page.click(".cfgEditBtn >> nth=0")  # share_minimo, percentCapped: true
        page.wait_for_selector("#cfgEditInput", timeout=5000)
        page.fill("#cfgEditInput", "150")
        page.click(".cfgSaveBtn")
        page.wait_for_timeout(200)
        check("11: a percent-capped field rejects a value over 100 client-side (matching the live RPC's own real 0-100 percent-sanity check)",
              "0 a 100" in page.inner_text("#cfgEditError"))
        check("11b: no write call was made for the rejected value", len(blocked_calls) == 0)
        page.fill("#cfgEditInput", "abc")
        page.click(".cfgSaveBtn")
        page.wait_for_timeout(200)
        check("12: a non-numeric value is rejected client-side with a clear message, never sent to the RPC", "numérico" in page.inner_text("#cfgEditError") and len(blocked_calls) == 0)
        page.fill("#cfgEditInput", "0,0112")
        page.click(".cfgSaveBtn")
        page.wait_for_selector("#cfgConfirmSaveBtn", timeout=5000)
        check("13: BR comma-decimal input (0,0112) is accepted and parsed correctly", "0,0112" in page.inner_text("#nxModalRoot") or "0.0112" in page.inner_text("#nxModalRoot"))
        page.close()

        # ---------- 14: double-submit guard ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(CFG_READ_URL + "*", json_route(200, {"rows": []}))
        dup_calls = []
        page.route(CFG_WRITE_URL + "*", counting_route(dup_calls, 200, lambda p: {"status": "OK"}))
        mount(page)
        goto_config(page)
        page.click(".cfgEditBtn >> nth=0")
        page.wait_for_selector("#cfgEditInput", timeout=5000)
        page.fill("#cfgEditInput", "50")
        page.click(".cfgSaveBtn")
        page.wait_for_selector("#cfgConfirmSaveBtn", timeout=5000)
        page.eval_on_selector("#cfgConfirmSaveBtn", "el => { el.click(); el.click(); }")
        page.wait_for_selector("#cfgSuccessCloseBtn", timeout=5000)
        check("14: duplicate-submit guard -- two rapid clicks on Confirmar still produce exactly one real write call", len(dup_calls) == 1)
        page.close()

        # ---------- 15: adversarial -- real server-side MASTER authority ----------
        # Proven directly against the LIVE production function (PM-5E
        # Gate 26 forensics: master_update_portal_config's real body
        # starts with a `usuarios`/`perfil='MASTER'` check and raises
        # 42501 otherwise; RLS on public.configuracoes additionally
        # restricts INSERT/UPDATE to is_master() -- confirmed live, not
        # assumed). A harness-level test cannot re-simulate real
        # Postgres RLS/role enforcement; asserting the frontend
        # correctly surfaces a 42501 denial (never a false success) is
        # the meaningful, non-redundant proof available at this layer.
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(CFG_READ_URL + "*", json_route(200, {"rows": []}))
        page.route(CFG_WRITE_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_config(page)
        page.click(".cfgEditBtn >> nth=0")
        page.wait_for_selector("#cfgEditInput", timeout=5000)
        page.fill("#cfgEditInput", "50")
        page.click(".cfgSaveBtn")
        page.wait_for_selector("#cfgConfirmSaveBtn", timeout=5000)
        page.click("#cfgConfirmSaveBtn")
        page.wait_for_timeout(300)
        check("15: a 42501 denial is surfaced inline in the confirmation modal, never a false success", "42501" in page.inner_text("#cfgConfirmMsg") or "Master" in page.inner_text("#cfgConfirmMsg"))
        check("15b: the modal stays open on failure (never silently closes on a real denial)", page.query_selector("#cfgConfirmSaveBtn") is not None)
        page.close()

        # ---------- 16: session expiry on read ----------
        page = new_page(browser, token=None)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        page.wait_for_selector('[data-section="configuracoes"]', timeout=5000)
        page.click('[data-section="configuracoes"]')
        page.wait_for_timeout(300)
        check("16: an expired/missing session on read shows a real error state, not a false-success empty grid", page.query_selector(".modErrorState") is not None)
        page.close()

        # ---------- 18-21: PM-WRITE-SAFETY-2 -- environment-authority write safety ----------
        # Network/provider-boundary proof, not a bare isHomologationMode()
        # check: spies the mocked HTTP route for the real write RPC via
        # counting_route (the same mechanism the production-path checks
        # 9/9b above already trust) and asserts the exact invocation
        # count per environment -- len(calls)==0 is itself the
        # anti-false-green proof that the gate runs before any fetch,
        # not merely that a call happens to not occur for some other
        # incidental reason. The route's own fulfilled body for the
        # non-production cases is a recognizable poison value
        # ("SHOULD-NEVER-BE-CALLED") -- an extra, independent signal:
        # if the gate ever regressed, the resolved promise would carry
        # this exact string, which the assertions below also check for.
        env_cases = [
            ("LOCAL_DEV", False),
            ("AUTHORIZED_HOMOLOGATION", False),
            ("UNKNOWN_HOST", False),
            ("AUTHORIZED_PRODUCTION", True),
        ]
        for idx, (env_name, expect_real_network) in enumerate(env_cases):
            page = new_page(browser, env_name=env_name)
            install_tripwire(page)
            page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
            page.route(CONV_URL + "*", json_route(200, []))
            page.route(CFG_READ_URL + "*", json_route(200, {"rows": [{"chave": "share_minimo", "valor": "40"}]}))
            env_calls = []
            poison = {"status": "SHOULD-NEVER-BE-CALLED"}
            page.route(CFG_WRITE_URL + "*", counting_route(env_calls, 200,
                (lambda p: {"status": "OK", "chave": p["p_key"], "valor": p["p_value"]}) if expect_real_network else (lambda p: poison)))
            mount(page)
            goto_config(page)
            outcome = page.evaluate("""
              () => window.NX_MASTER_CONFIG_PROVIDER
                .updateConfig('share_minimo', 45, 'test')
                .then(r => ({ ok: true, result: r }))
                .catch(e => ({ ok: false, error: String(e && e.message || e) }))
            """)
            n = 18 + idx
            if expect_real_network:
                check(f"{n}: {env_name} -> real write RPC reaches the network (NOT frontend-simulated)", len(env_calls) == 1)
                check(f"{n}b: {env_name} -> outgoing payload is byte-parity with the pre-existing production contract (only p_key/p_value/p_description, exact values)",
                      len(env_calls) == 1 and env_calls[0] == {"p_key": "share_minimo", "p_value": 45, "p_description": "test"})
                check(f"{n}c: {env_name} -> response is the real (non-simulated) server response shape", isinstance(outcome, dict) and outcome.get("ok") and outcome["result"].get("simulated") is not True)
            else:
                check(f"{n}: {env_name} -> real write RPC never reaches the network (frontend-simulated), zero calls to the poisoned route", len(env_calls) == 0)
                check(f"{n}b: {env_name} -> updateConfig() resolves with simulated:true, never the poison value the route would have returned if touched",
                      isinstance(outcome, dict) and outcome.get("ok") and outcome["result"].get("simulated") is True and outcome["result"].get("status") != "SHOULD-NEVER-BE-CALLED")
            check(f"{n}d: {env_name} -> isHomologationMode() reports {not expect_real_network} (single source of truth, same expression callRpc reads)",
                  page.evaluate("window.NX_MASTER_CONFIG_PROVIDER.isHomologationMode()") == (not expect_real_network))
            page.close()

        # ---------- 22-25: read preservation across all 4 environments ----------
        # The write gate must never swallow the read RPC -- proven for
        # every environment, including UNKNOWN_HOST.
        for idx, env_name in enumerate(["LOCAL_DEV", "AUTHORIZED_HOMOLOGATION", "AUTHORIZED_PRODUCTION", "UNKNOWN_HOST"]):
            page = new_page(browser, env_name=env_name)
            install_tripwire(page)
            page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
            page.route(CONV_URL + "*", json_route(200, []))
            read_calls = []
            page.route(CFG_READ_URL + "*", counting_route(read_calls, 200, lambda p: {"rows": [{"chave": "share_minimo", "valor": "40"}]}))
            mount(page)
            goto_config(page)
            check(f"{26 + idx}: {env_name} -> the real read RPC (operational_portal_config) still reaches the network normally", len(read_calls) == 1)
            page.close()

        browser.close()

    check("30: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Config Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
