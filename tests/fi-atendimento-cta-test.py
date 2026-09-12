#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIM-REG-01 -- "Falar com um Analista" restoration + expansion
regression guard.

Prevents a repeat of the exact regression this Wave restored: the
"Falar com um Analista" attendance CTA silently disappeared during the
PORTAL-NEXT-08 simulator-engine extraction (the original
assets/js/fi-atendimento.js -- still live today in
portal-financiamento-brabus-secure -- was deliberately marked "not
extracted" for that Wave's narrower calculation-engine-only scope, and
was never restored afterward).

Asserts, deterministically:
  - the CTA is present at all 3 approved entry points (Portal Home,
    Simulador Novos, Simulador Seminovos);
  - all 3 use the SAME attendance authority (window.NX_FI_ATENDIMENTO,
    calling the same chamar_analista_fi RPC) -- no duplicated
    telephone/URL/routing;
  - each CTA carries its own distinguishable data-analyst-origin,
    ready for future measurement, with 0 new analytics backend;
  - clicking calls chamar_analista_fi exactly once and opens exactly
    one https://wa.me/<digits-only-phone>?text=<fixed greeting> link
    -- the SAME destination format and message the real, currently-
    live production implementation uses (verified byte-identical
    against PORTAL-NEXT-08/.source/fi-atendimento-origin-main.js this
    Wave; not re-diffed here since that source lives outside this
    repository);
  - F.2 (Hybrid Luxury Collapsible) navigation is unaffected by the
    CTA's presence in the simulator page header;
  - zero horizontal scroll at 1366/480 on all 3 pages.

Requires: a static server rooted at this worktree's own root (NOT the
PORTAL-FI-DESIGN-LAB parent -- unlike the main portal-next-v2
worktree's convention, this file assumes URL == BASE + path, no
/portal-next-v2/ prefix) on port 8721, OR override via SIM_REG01_BASE
env var.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.environ.get("SIM_REG01_BASE", "http://127.0.0.1:8721")
MOCK_PHONE_DIGITS = "11912345678"
MOCK_ANALYST_JSON = '[{"nome":"Ana Teste","whatsapp":"(11) 91234-5678"}]'

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- presence + integration at each entry point ----------
        pages = [
            ("portal_home", BASE + "/index.html", "#landingAnalystCtaBtn"),
            ("simulador_novos", BASE + "/index.html#/simulador-novos", "#smAnalystCtaBtn"),
            ("simulador_seminovos", BASE + "/index.html#/simulador-seminovos", "#smAnalystCtaBtn"),
        ]
        for origin, url, sel in pages:
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.wait_for_timeout(600)

            btn = page.locator(sel)
            check(f"{origin}: CTA present exactly once", btn.count() == 1)
            check(f"{origin}: CTA is a real <button>", btn.count() and btn.evaluate("el => el.tagName") == "BUTTON")
            check(f"{origin}: CTA text is 'Falar com um Analista'", btn.count() and "Falar com um Analista" in btn.text_content())
            check(f"{origin}: data-analyst-origin correct", btn.get_attribute("data-analyst-origin") == origin)
            check(f"{origin}: shared authority loaded (window.NX_FI_ATENDIMENTO)", page.evaluate("!!window.NX_FI_ATENDIMENTO && typeof window.NX_FI_ATENDIMENTO.falarComAnalista === 'function'"))
            check(f"{origin}: shared provider loaded (window.NX_FI_ATENDIMENTO_PROVIDER)", page.evaluate("!!window.NX_FI_ATENDIMENTO_PROVIDER && typeof window.NX_FI_ATENDIMENTO_PROVIDER.chamarAnalista === 'function'"))
            check(f"{origin}: touch target >= 44px tall", btn.count() and btn.evaluate("el => el.getBoundingClientRect().height") >= 44)

            overflow_1366 = page.evaluate("document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth")
            check(f"{origin} @ 1366px: zero horizontal overflow", overflow_1366 <= 0)
            page.set_viewport_size({"width": 480, "height": 900})
            page.wait_for_timeout(150)
            overflow_480 = page.evaluate("document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth")
            check(f"{origin} @ 480px: zero horizontal overflow", overflow_480 <= 0)

            check(f"{origin}: no console/page errors on load", len(errors) == 0)
            page.close()

        # ---------- F.2 unaffected by the CTA (Novos) ----------
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
        page.goto(BASE + "/index.html#/simulador-novos")
        page.wait_for_timeout(600)
        check("F.2: all categories collapsed on load (unaffected by CTA)", page.eval_on_selector_all(".smModeGroup.open", "els => els.length") == 0)
        page.click('.smModeGroupHeader[data-group="Campanhas"]')
        page.wait_for_timeout(200)
        page.click('.smModeBtn[data-mode="triton"]')
        page.wait_for_timeout(300)
        check("F.2: auto-collapse still works with CTA present", page.eval_on_selector_all(".smModeGroup.open", "els => els.length") == 0)
        check("F.2: red/bold hint still present with CTA in the same header", page.locator(".smModeHint").count() == 1)
        check("CTA: still present after an F.2 mode switch (static header, not re-rendered)", page.locator("#smAnalystCtaBtn").count() == 1)
        page.close()

        # ---------- shared authority: click -> exactly 1 RPC call, 1 wa.me open, same destination for all 3 origins ----------
        opened = {}
        for origin, url, sel in pages:
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            rpc_calls = []
            page.on("request", lambda req: rpc_calls.append(req.url) if "chamar_analista_fi" in req.url else None)
            captured = []
            page.expose_binding("__capturedOpen", lambda source, u: captured.append(u))
            page.add_init_script("window.open = function (u) { window.__capturedOpen(u); return null; };")
            page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
            page.route("**/rest/v1/rpc/chamar_analista_fi*", lambda route: route.fulfill(status=200, content_type="application/json", body=MOCK_ANALYST_JSON))
            page.goto(url)
            page.wait_for_timeout(600)
            page.evaluate("""
                () => {
                    if (!window.NX_INTELLIGENCE_CONFIG) window.NX_INTELLIGENCE_CONFIG = {};
                    window.NX_INTELLIGENCE_CONFIG.supabaseUrl = 'https://mock.invalid';
                    window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = 'mock-anon-key';
                    window.NX_AUTH = window.NX_AUTH || {};
                    window.NX_AUTH.getAccessToken = function () { return Promise.resolve('mock-token-xyz'); };
                }
            """)
            page.click(sel)
            page.wait_for_timeout(1200)
            check(f"{origin}: chamar_analista_fi RPC called exactly once on click", len(rpc_calls) == 1)
            check(f"{origin}: exactly one wa.me window opened on click", len(captured) == 1)
            if captured:
                u = captured[0]
                check(f"{origin}: destination uses wa.me + correct digits-only phone", u.startswith("https://wa.me/" + MOCK_PHONE_DIGITS + "?text="))
                opened[origin] = u
            page.close()

        urls = list(opened.values())
        check("all 3 origins resolve to the IDENTICAL wa.me destination (single authority, zero duplication)", len(urls) == 3 and len(set(urls)) == 1)

        browser.close()

    passed = sum(1 for _, c in results if c)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print()
    print(f"=== SIM-REG-01 Falar com um Analista Regression Guard: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
