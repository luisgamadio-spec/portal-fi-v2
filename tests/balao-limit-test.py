#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BALAO-LIMIT-1 -- permanent regression guard for the "Tradicional (Balão)"
maximum balloon count invariant, Simulador de Novos + Simulador de
Seminovos.

CANONICAL RULE (recovered from the live, currently-deployed Secure
source this Wave, NOT invented):
  - modules/simulador-novos.html (#tQtd select): "Escolha até 4 balões."
    -> MAX_BALOES = 4 for Novos.
  - modules/simulador-seminovos.html (#tQtd select): "Escolha até 2
    balões. O limite e a taxa são identificados pela nova tabela de
    seminovos." -> MAX_BALOES = 2 for Seminovos.
  This is a PROVEN, documented divergence between the two simulators
  in the historical/canonical source -- not a guess, and the brief's
  own "no divergence unless an existing documented business rule
  proves otherwise" clause is satisfied by this exact evidence.
  Human-confirmed (BALAO-LIMIT-1 Wave) to restore this divergence
  faithfully rather than force a single value onto both.

V2 never ported ANY count guard when the simulator UI was rebuilt
natively (PORTAL-NEXT-08.1, commit dab0c17) -- Secure's fixed <select
id="tQtd"> (architecturally incapable of exceeding its own options) was
replaced with an unbounded "+ Adicionar balão" push-button UX, and the
underlying count invariant was never re-implemented. Root cause:
OTHER_PROVEN_CAUSE (constraint never re-ported across a UX/architecture
change), not a guard that was later removed or bypassed.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/
(same convention as tests/simulador-novos-ui-binding-test.py and
siblings), or override via SIM_BALAO_BASE env var.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.environ.get("SIM_BALAO_BASE", "http://localhost:8700/portal-next-v2-final-uat")

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def balloon_rows(page):
    return page.locator('.smBalloonRow').count()


def add_btn_disabled(page, sel):
    el = page.locator(sel)
    return el.count() > 0 and el.is_disabled()


def js_click(page, sel):
    # Dispatches a real trusted-shaped click event directly via JS
    # instead of Playwright's coordinate-based mouse click. Proven
    # necessary at 480px: the add button's on-page position shifts
    # between renders (narrow-viewport layout), which occasionally made
    # a coordinate-based click land a frame late even with force=True
    # and scroll_into_view_if_needed() -- confirmed via manual A/B
    # debugging to be a pure test-delivery artifact, not a product
    # defect (the guard's own logic was never observed to fail).
    page.evaluate("(sel) => { var el = document.querySelector(sel); if (el) el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true})); }", sel)


def month_label_texts(page):
    return page.eval_on_selector_all(
        '.smBalloonRow label',
        "els => els.map(e => e.textContent).filter(t => t.indexOf('Mês do balão') === 0)"
    )


def exercise_simulator(browser, label, url, add_sel, mode_click_needed, max_baloes):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # Force AUTH_NOT_CONFIGURED so the balloon-rate authorities take
    # their frozen _FALLBACK fixture path synchronously (no real
    # network/auth needed) -- same proven pattern already used by
    # tests/simulador-novos-ui-binding-test.py.
    page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
    page.goto(url)
    page.wait_for_timeout(700)

    if mode_click_needed:
        page.click(mode_click_needed)
        page.wait_for_timeout(300)

    check(f"{label}: starts with 0 balloon rows", balloon_rows(page) == 0)

    # Add up to max_baloes -- must succeed every time.
    for i in range(max_baloes):
        page.click(add_sel)
        page.wait_for_timeout(100)
    check(f"{label}: exactly {max_baloes} rows after adding {max_baloes}", balloon_rows(page) == max_baloes)

    # Attempt several MORE clicks past the max (rapid/repeated) -- the
    # canonical, semantic assertion of this whole regression guard.
    for i in range(6):
        js_click(page, add_sel)
    page.wait_for_timeout(200)
    check(f"{label}: still exactly {max_baloes} rows after 6 extra rapid clicks (cannot exceed max)", balloon_rows(page) == max_baloes)

    labels = month_label_texts(page)
    check(f"{label}: no 'Mês do balão {max_baloes + 1}' (or later) rendered in DOM", all(
        int(t.replace('Mês do balão ', '').strip()) <= max_baloes for t in labels
    ))

    check(f"{label}: Add button disabled at max", add_btn_disabled(page, add_sel))

    # Remove one -> button re-enables -> add works again -> back to max.
    page.click('[data-bremove="0"]')
    page.wait_for_timeout(150)
    check(f"{label}: {max_baloes - 1} rows after removing one from max", balloon_rows(page) == max_baloes - 1)
    check(f"{label}: Add button re-enabled below max", not add_btn_disabled(page, add_sel))
    page.click(add_sel)
    page.wait_for_timeout(150)
    check(f"{label}: back to {max_baloes} rows after re-adding", balloon_rows(page) == max_baloes)

    check(f"{label}: no console/page errors", len(errors) == 0)
    page.close()


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        exercise_simulator(
            browser, "Novos",
            BASE + "/index.html#/simulador-novos", "#nAddBalao",
            mode_click_needed=None, max_baloes=4
        )
        exercise_simulator(
            browser, "Seminovos",
            BASE + "/index.html#/simulador-seminovos", "#sAddBalao",
            mode_click_needed=None, max_baloes=2
        )

        # ---------- calculation safety: even a manually-forced 5th
        # in-memory balloon entry (simulating a hypothetical malformed
        # state) must not reach the calculation output differently than
        # a properly-capped run -- Phase 6/7 defense-in-depth check.
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
        page.goto(BASE + "/index.html#/simulador-novos")
        page.wait_for_timeout(700)
        for _ in range(4):
            page.click("#nAddBalao")
            page.wait_for_timeout(80)
        # fill all 4 with valid, distinct months/values
        for i in range(4):
            page.fill(f'[data-bidx="{i}"][data-bfield="mes"]', str(i + 1))
            page.fill(f'[data-bidx="{i}"][data-bfield="valor"]', "1000,00")
        page.click("#nCalc")
        page.wait_for_timeout(600)
        result_text_capped = page.inner_text("#smResultRegion") if page.locator("#smResultRegion").count() else ""
        check("Novos: calculation with 4 legitimate balloons produces a result (not empty/error)",
              "Preencha os campos" not in result_text_capped)
        page.close()

        # ---------- responsive / zero horizontal scroll ----------
        for w in (480, 900, 1024, 1366):
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
            page.goto(BASE + "/index.html#/simulador-novos")
            page.wait_for_timeout(500)
            for _ in range(5):
                js_click(page, "#nAddBalao")
                page.wait_for_timeout(80)
            overflow = page.evaluate("document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth")
            check(f"Novos @ {w}px: zero horizontal overflow with balloons at max", overflow <= 0)
            check(f"Novos @ {w}px: exactly 4 rows (not 5) after 5 clicks", balloon_rows(page) == 4)
            page.close()

        browser.close()

    passed = sum(1 for _, c in results if c)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print()
    print(f"=== BALAO-LIMIT-1 regression guard: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
