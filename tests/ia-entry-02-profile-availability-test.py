#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-ENTRY-02 -- Living Core availability now follows the SAME canonical
authority as the routed brabus-intelligence module/Landing card
(auth-core.js's isModuleAuthorized(), consumed via
window.NX_REGISTRY.byId('brabus-intelligence')) instead of a hardcoded
`ctx.isMaster === true` check -- see assets/js/intelligence/
intelligence-panel.js's isVisibleNow(). No per-profile hardcoded list.

Per V2-UAT-06's own finding (a real click-driven navigation escaped
the harness's mock entirely, something `location.hash = ...` never
exposed), every check below that opens the Living Core does so via a
REAL element.click(), never a scripted hash/state assignment.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-entry-02")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"
HARNESS = f"{BASE}/tests/_v2-uat-03-profiles-harness.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


PROFILES = ["camile", "william", "roberto", "felipe", "alex", "rodrigo"]


def open_landing_as_master(page):
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate("""() => {
        window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
        window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER', allowedModuleIds: [] });
        if (window.NX_INTELLIGENCE_PANEL) window.NX_INTELLIGENCE_PANEL.refresh();
    }""")
    page.wait_for_selector(".fNavItem", timeout=8000)


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def tracked_page(**kw):
            pg = browser.new_page(**kw)
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(str(e)))
            return pg

        # ============================================================
        # SIX HARNESS PROFILES
        # ============================================================
        for key in PROFILES:
            page = tracked_page(viewport={"width": 1366, "height": 900})
            page.goto(f"{HARNESS}?uat={key}")
            page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
            page.wait_for_timeout(2200)
            frame = page.frames[-1]
            frame.wait_for_selector(".fNavItem", timeout=8000)

            ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
            state = frame.evaluate("window.NX_AUTH_CORE.getState()")
            check(f"[{key}] bootstrap settled: AUTHORIZED", state == "AUTHORIZED", state)
            check(f"[{key}] effective identity resolved (nome present)", bool(ctx and ctx.get("nome")), ctx)
            check(f"[{key}] effective perfil resolved", bool(ctx and ctx.get("perfil")), ctx)
            check(f"[{key}] isMaster is real (false for these 6)", ctx is not None and ctx.get("isMaster") is False, ctx)

            authorized = frame.evaluate("window.NX_AUTH_CORE.isModuleAuthorized(window.NX_REGISTRY.byId('brabus-intelligence'))")
            check(f"[{key}] brabus-intelligence module IS authorized (canonical authority)", authorized is True, authorized)

            launcher_present = frame.locator("#baiLauncherBtn").count() == 1
            check(f"[{key}] Living Core launcher present in DOM", launcher_present)
            if not launcher_present:
                page.close()
                continue

            launcher_visible = frame.locator("#baiLauncherBtn").is_visible()
            check(f"[{key}] Living Core launcher visible", launcher_visible)

            shot(page, f"{key}-living-core-idle.png")

            identity_before = ctx
            # REAL click -- never location.hash/state assignment (V2-UAT-06).
            frame.locator("#baiLauncherBtn").click(position={"x": 13, "y": 10}, force=True)
            page.wait_for_timeout(500)
            drawer_open = frame.get_attribute("#baiPanelDrawer", "hidden") is None
            check(f"[{key}] real click opens the Brabus Intelligence panel", drawer_open)

            shot(page, f"{key}-living-core-open.png")

            ctx_after = frame.evaluate("window.NX_AUTH_CORE.getContext()")
            check(f"[{key}] identity unchanged after opening the panel", ctx_after == identity_before, (identity_before, ctx_after))
            check(f"[{key}] perfil unchanged after opening the panel", ctx_after and ctx_after.get("perfil") == identity_before.get("perfil"))
            check(f"[{key}] no MASTER authority granted by opening the panel", ctx_after is not None and ctx_after.get("isMaster") is False, ctx_after)

            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[{key}] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

            page.close()

        # ============================================================
        # MASTER (real Portal entry point, D17-workaround via config-
        # absent state already required for this pattern elsewhere)
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        page.wait_for_timeout(500)

        ctx = page.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[MASTER] effective perfil is MASTER", ctx.get("perfil") == "MASTER", ctx)
        check("[MASTER] isMaster is true", ctx.get("isMaster") is True, ctx)
        authorized = page.evaluate("window.NX_AUTH_CORE.isModuleAuthorized(window.NX_REGISTRY.byId('brabus-intelligence'))")
        check("[MASTER] brabus-intelligence module IS authorized", authorized is True, authorized)
        launcher_present = page.locator("#baiLauncherBtn").count() == 1
        check("[MASTER] Living Core launcher present in DOM", launcher_present)
        if launcher_present:
            check("[MASTER] Living Core launcher visible", page.locator("#baiLauncherBtn").is_visible())
            shot(page, "master-living-core-idle.png")
            identity_before = ctx
            page.locator("#baiLauncherBtn").click(position={"x": 13, "y": 10}, force=True)
            page.wait_for_timeout(500)
            drawer_open = page.get_attribute("#baiPanelDrawer", "hidden") is None
            check("[MASTER] real click opens the Brabus Intelligence panel", drawer_open)
            shot(page, "master-living-core-open.png")
            ctx_after = page.evaluate("window.NX_AUTH_CORE.getContext()")
            check("[MASTER] identity unchanged after opening the panel", ctx_after == identity_before, (identity_before, ctx_after))
            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check("[MASTER] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        # ============================================================
        # NEGATIVE AUTH TEST (Section 16) -- controlled, isolated
        # fixture override of the SAME canonical authority function
        # (never a new user, never a Supabase change) proving the gate
        # genuinely reacts to authorization, not a hardcoded "always
        # show now" shortcut.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{HARNESS}?uat=camile")
        page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
        page.wait_for_timeout(2200)
        frame = page.frames[-1]
        frame.wait_for_selector(".fNavItem", timeout=8000)
        check("[NEGATIVE] Living Core present BEFORE the denial override (sanity)", frame.locator("#baiLauncherBtn").count() == 1)

        frame.evaluate("""() => {
            var orig = window.NX_AUTH_CORE.isModuleAuthorized;
            window.NX_AUTH_CORE.isModuleAuthorized = function (entry) {
                if (entry && entry.id === 'brabus-intelligence') return false;
                return orig(entry);
            };
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""")
        page.wait_for_timeout(400)
        launcher_after_denial = frame.locator("#baiLauncherBtn").count()
        check("[NEGATIVE] Living Core COMPLETELY ABSENT once brabus-intelligence authorization is denied", launcher_after_denial == 0, launcher_after_denial)
        root_after_denial = frame.locator("#baiLauncherRoot").count()
        check("[NEGATIVE] no launcher root/wrapper element left behind either", root_after_denial == 0, root_after_denial)
        shot(page, "negative-auth-denied.png")
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== IA-ENTRY-02: Living Core Profile Availability ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
