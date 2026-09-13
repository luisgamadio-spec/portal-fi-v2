#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-06 -- "browser truth": a real Human UAT screenshot showed the
harness's own outer banner correctly naming CAMILE BEATRIZ SANTOS SENA
/ ANALISTA / NAÇÕES, while the real Portal INSIDE the iframe rendered
the Human's own real MASTER identity (header "LUIS GUSTAVO DE MEL...",
"Painel Master" visible in the sidebar, "Histórico" visible inside
Salários & Comissões). V2-UAT-04/05's own automated suites had all
passed. This suite exists specifically to catch that class of gap:
every check below reads the REAL, POST-NAVIGATION, POST-BOOTSTRAP DOM
(header/sidebar/module content), not an isolated call to the mock's
own JS objects -- reproducing the same navigation path a Human
actually takes (real click into Salários, not a hash assignment).

WHY THE PREVIOUS SUITES FALSE-PASSED (investigated, not assumed --
see this Wave's own report Section 3): they never actually false-
passed on THEIR OWN terms -- re-run against the fixed code they still
pass. The real gap is environmental: Playwright's chromium.launch()
starts a brand-new, cold-cache browser process on every single run,
so those suites structurally could never exercise (or catch) a
browser-HTTP-cache-staleness class of bug -- exactly the kind a
Human's real, long-lived Chrome profile (reused across many Waves of
this engagement) is exposed to. tests/_v2-uat-03-profiles-harness.html
already cache-busted the real product's own assets/ paths (RH-5B.2
precedent) but never extended that to its OWN two injected mock
script tags -- the concrete, fixed gap this suite verifies directly
(TEST 0 below, by inspecting the actual network request URLs, not by
guessing).

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "v2-uat-06")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"
HARNESS_URL = f"{BASE}/tests/_v2-uat-03-profiles-harness.html?uat=camile"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name), full_page=True)


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []
    requested_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.on("request", lambda r: requested_urls.append(r.url))

        # ============================================================
        # TEST 0 -- the concrete fix: mock scripts are now requested
        # WITH a cache-busting query string (structurally defeats any
        # browser HTTP cache for these two files, exactly like every
        # real product assets/ path already got in RH-5B.2/this
        # harness's own loadFrame()).
        # ============================================================
        page.goto(HARNESS_URL)
        page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
        page.wait_for_timeout(2000)

        mock_reqs = [u for u in requested_urls if "_v2-uat-03-profiles-mock.js" in u]
        fixtures_reqs = [u for u in requested_urls if "_salarios-uat-fixtures.js" in u]
        check("[0] _v2-uat-03-profiles-mock.js is requested with a cache-busting query string", len(mock_reqs) > 0 and all("?v2uat03=" in u for u in mock_reqs), mock_reqs)
        check("[0] _salarios-uat-fixtures.js is requested with a cache-busting query string", len(fixtures_reqs) > 0 and all("?v2uat03=" in u for u in fixtures_reqs), fixtures_reqs)

        # ============================================================
        # TEST 1 -- HEADER IS THE CANARY. Real DOM text, not a mock call.
        # ============================================================
        frame = page.frames[-1]
        frame.wait_for_selector(".pUserName", timeout=8000)
        header_name = frame.inner_text(".pUserNameText")
        header_badge = frame.inner_text(".pUserBadge")
        header_context = frame.inner_text(".pUserContext")
        check("[1 HEADER CANARY] header name is CAMILE, not any other identity", "CAMILE BEATRIZ SANTOS SENA" in header_name, header_name)
        check("[1 HEADER CANARY] header profile badge is ANALISTA, not MASTER", header_badge == "ANALISTA", header_badge)
        check("[1 HEADER CANARY] header context shows NACOES", "NACOES" in header_context, header_context)
        if "MASTER" in header_name.upper() or header_badge == "MASTER":
            print("\n*** FAIL IMEDIATO: header shows MASTER authority for a ?uat=camile scenario. Aborting further checks. ***")
            browser.close()
            check("[FATAL] header must never show MASTER for Camile", False, (header_name, header_badge))
            ok = all(r[1] for r in results)
            print(f"\n=== V2-UAT-06: Effective Runtime Authority ({sum(1 for _, p in results if p)}/{len(results)}) ===")
            print("RESULT:", "PASS" if ok else "FAIL")
            sys.exit(1)

        shot(page, "camile-landing.png")

        # ============================================================
        # TEST 2 -- runtime context, read from the real, effective
        # NX_AUTH_CORE (post-bootstrap), not the mock's own payload echo.
        # ============================================================
        ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[2] effective context perfil is ANALISTA", ctx.get("perfil") == "ANALISTA", ctx)
        check("[2] effective context isMaster is false", ctx.get("isMaster") is False, ctx)
        check("[2] effective context nome is Camile's real nome", ctx.get("nome") == "CAMILE BEATRIZ SANTOS SENA", ctx)
        check("[2] isModuleAuthorized(shell-admin) is false",
              frame.evaluate("window.NX_AUTH_CORE.isModuleAuthorized(window.NX_REGISTRY.byId('shell-admin'))") is False)
        check("[2] isModuleAuthorized(central-atendimento-fi) is false",
              frame.evaluate("window.NX_AUTH_CORE.isModuleAuthorized(window.NX_REGISTRY.byId('central-atendimento-fi'))") is False)

        # ============================================================
        # TEST 3 -- SIDEBAR: real DOM, "Painel Master" absent.
        # ============================================================
        sidebar_labels = frame.evaluate("[...document.querySelectorAll('#pGlobalNav .pNavLabel')].map(e => e.textContent)")
        check("[3 SIDEBAR] 'Painel Master' absent from the sidebar", "Painel Master" not in sidebar_labels, sidebar_labels)
        check("[3 SIDEBAR] 'Central de Atendimento F&I' absent from the sidebar", "Central de Atendimento F&I" not in sidebar_labels, sidebar_labels)
        check("[3 SIDEBAR] zero disabled/deferred sidebar items", frame.evaluate("document.querySelectorAll('#pGlobalNav .pNavItemDeferred').length") == 0)

        # ============================================================
        # TEST 4 -- REAL CLICK into Salários & Comissões (same path a
        # Human actually takes -- not a location.hash assignment).
        # ============================================================
        # "Score & Salários" is the category that holds Salários & Comissões.
        cat_labels = frame.evaluate("[...document.querySelectorAll('.fNavItem .label')].map(e => e.textContent)")
        check("[4] 'Score & Salários' category tab is present", "Score & Salários" in cat_labels, cat_labels)
        idx = cat_labels.index("Score & Salários")
        frame.evaluate(f'document.querySelectorAll(".fNavItem")[{idx}].click()')
        page.wait_for_timeout(200)
        sal_link = frame.locator("#landingModuleDetail a.fModuleBlock", has_text="Salários & Comissões")
        check("[4] 'Salários & Comissões' renders as a real, clickable link", sal_link.count() == 1)
        sal_link.first.click()
        frame.wait_for_selector("text=Salários & Comissões", timeout=8000)
        page.wait_for_timeout(1500)

        # ============================================================
        # TEST 5 -- SALÁRIOS: real DOM after real navigation, real
        # module-level auth context, MASTER controls genuinely absent.
        # ============================================================
        sal_ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[5 SALÁRIOS] module's own effective context perfil is ANALISTA", sal_ctx.get("perfil") == "ANALISTA", sal_ctx)
        check("[5 SALÁRIOS] module's own effective context isMaster is false", sal_ctx.get("isMaster") is False, sal_ctx)

        body_text = frame.evaluate("document.body.innerText")
        check("[5 SALÁRIOS] module actually rendered (real heading present)", "Salários & Comissões" in body_text)
        check("[5 SALÁRIOS] 'Histórico' tab genuinely absent from the rendered DOM", "Histórico" not in body_text, body_text[:2000])
        check("[5 SALÁRIOS] 'Comissão — Gestor F&I' section genuinely absent", "COMISSÃO — GESTOR F&I" not in body_text.upper())
        check("[5 SALÁRIOS] 'Fechar competência' action genuinely absent", "Fechar competência" not in body_text)
        check("[5 SALÁRIOS] her own real loja (NACOES) is the scope shown", "NACOES" in body_text)
        check("[5 SALÁRIOS] no leaked MASTER-fixture cross-store data (ABC/Bandeirantes Centro/Gastao)",
              not any(m in body_text for m in ["ABC", "BANDEIRANTES CENTRO", "GASTAO"]), body_text[:500])

        # Header re-checked AFTER navigating into Salários -- proves
        # the effective authority held steady across the real click,
        # not just at initial landing.
        header_name_2 = frame.inner_text(".pUserNameText")
        header_badge_2 = frame.inner_text(".pUserBadge")
        check("[5 SALÁRIOS] header still shows Camile/ANALISTA after real navigation (no drift)",
              "CAMILE BEATRIZ SANTOS SENA" in header_name_2 and header_badge_2 == "ANALISTA", (header_name_2, header_badge_2))

        shot(page, "camile-salarios.png")

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("[5 SALÁRIOS] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

        # ============================================================
        # TEST 6 -- fail-loud guard itself is present and wired (static
        # proof the mock ships the self-check, complementing the
        # positive-path proof above that it never needed to fire).
        # ============================================================
        mock_src = frame.evaluate("fetch('tests/_v2-uat-03-profiles-mock.js').then(r => r.text())")
        check("[6] the fail-loud EFFECTIVE AUTHORITY MISMATCH guard is present in the served mock", "assertEffectiveAuthorityMatches" in mock_src and "EFFECTIVE AUTHORITY MISMATCH" in mock_src)

        page.close()
        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-06: Effective Runtime Authority ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
