#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-1-VISUAL-FIX-01 -- evidence for the approved human visual UAT
change: removal of the initial empty-state panel ("Nenhuma pergunta
ainda" / the guidance sentence). Focused, dedicated evidence set --
the full contract/presentation/responsive/accessibility assertions
already live in intelligence-browser-test.py and
intelligence-visual-qa-test.py (both updated alongside this file to
assert the panel's ABSENCE instead of its presence) and are re-run
separately, not duplicated here.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-v2-1-visual-fix-01")
os.makedirs(SHOT_DIR, exist_ok=True)

BASE = "http://localhost:8700/portal-next-v2/index.html"
ROUTE = "#/brabus-intelligence"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond), detail))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


def overflow_of(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def assert_no_panel(page, label_prefix):
    check(f"{label_prefix}: no .modEmptyState panel", page.locator(".modEmptyState").count() == 0)
    check(f"{label_prefix}: no 'Nenhuma pergunta ainda' text anywhere on the page", "Nenhuma pergunta ainda" not in page.content())
    check(f"{label_prefix}: no instructional guidance sentence anywhere on the page", "Faça uma pergunta sobre financiamento" not in page.content())
    check(f"{label_prefix}: composer visible", page.locator("#baiInput").is_visible())
    check(f"{label_prefix}: fixture disclosure still present", page.locator(".modFixtureBanner").count() > 0)
    check(f"{label_prefix}: 0 horizontal overflow", overflow_of(page) <= 0)


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Desktop 1366 ----------
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "desktop 1366 initial")
        shot(page, "01-desktop-initial-1366.png")

        # first message
        page.fill("#baiInput", "Qual foi o resultado do mês passado?")
        page.click("#baiSendBtn")
        page.wait_for_timeout(400)
        check("desktop: first message renders a user bubble", page.locator(".baiMessageUser").count() == 1)
        check("desktop: first message renders an assistant bubble", page.locator(".baiMessageAssistant").count() == 1)
        check("desktop: structured block renders unchanged (metrics)", page.locator(".baiBlockPanel").count() == 1)
        shot(page, "06-desktop-after-first-message.png")

        # Nova conversa
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(200)
        assert_no_panel(page, "desktop after Nova conversa")
        check("desktop: Nova conversa leaves 0 messages", page.locator(".baiMessage").count() == 0)
        check("desktop: Nova conversa leaves 0 structured blocks", page.locator(".baiBlockPanel").count() == 0)
        shot(page, "08-after-nova-conversa.png")
        page.close()

        # ---------- Desktop 1920 ----------
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "desktop 1920 initial")
        shot(page, "02-desktop-initial-1920.png")
        page.close()

        # ---------- Tablet 768 ----------
        page = browser.new_page(viewport={"width": 768, "height": 1024})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "tablet 768 initial")
        shot(page, "03-tablet-initial-768.png")
        page.close()

        # ---------- Mobile 430 ----------
        page = browser.new_page(viewport={"width": 430, "height": 932})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "mobile 430 initial")
        shot(page, "04-mobile-initial-430.png")
        page.close()

        # ---------- Mobile 390 ----------
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "mobile 390 initial")
        shot(page, "05-mobile-initial-390.png")

        page.fill("#baiInput", "Qual foi o resultado do mês passado?")
        page.click("#baiSendBtn")
        page.wait_for_timeout(400)
        check("mobile 390: first message renders correctly", page.locator(".baiMessageUser").count() == 1 and page.locator(".baiBlockPanel").count() == 1)
        check("mobile 390: 0 horizontal overflow after first message", overflow_of(page) <= 0)
        shot(page, "07-mobile-after-first-message.png")
        page.close()

        # ---------- Also confirm 1024 (Gate 9 revalidation) ----------
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        assert_no_panel(page, "tablet 1024 initial")
        page.close()

        browser.close()

    ok = all(r[1] for r in results)
    for label, passed, detail in results:
        line = f"[{'PASS' if passed else 'FAIL'}] {label}"
        if not passed and detail:
            line += f" -- {detail}"
        print(line)
    print(f"\n=== IA-V2-1-VISUAL-FIX-01: {sum(1 for _, p, _ in results if p)}/{len(results)} ===")
    print(f"Screenshots: {SHOT_DIR}")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
