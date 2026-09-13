#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEC-1C.2 -- Human UAT with a REAL, live-authenticated ANALISTA session
(luuis.guga@gmail.com, configured server-side to resolve as
ANALISTA/NACOES/NOVOS+SEMINOVOS) found the Living Core launcher
completely absent on the PUBLISHED homologation, despite IA-ENTRY-02's
own 84/84 test suite passing against the local profile UAT harness.

Root cause (this wave's own investigation, see the wave's final
report): the published homologation's `main` branch was frozen 56
commits / 5 days behind this integrated worktree -- its `index.html`
never even contained the <script> tags for assets/js/intelligence/
intelligence-panel.js (or intelligence-context.js/intelligence-state.js/
intelligence-voice.js/intelligence-voice-focus.js). Not a runtime
authority bug: the Living Core's own code was simply never loaded on
the stale published build. IA-ENTRY-02's harness-based suite could
never have caught this, because it only ever loads the CURRENT,
correct index.html.

This file closes that specific gap: it proves the real code's own
runtime behavior for ANALISTA using the SAME direct-index.html-load
technique IA-ENTRY-01/IA-ENTRY-02 already use for their own MASTER
regression (open_landing_as_master() in those files) -- i.e. it
exercises the REAL, live NX_AUTH_CORE/NX_REGISTRY/NX_INTELLIGENCE_PANEL
runtime machinery directly, with only the two accessor functions
(getState/getContext) substituted for what a real authenticated
bootstrap would have produced -- never a hash-navigation shortcut
(V2-UAT-06's own lesson), never a hand-copied duplicate of the real
gate logic.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "sec1c2")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


# The exact real allowedModuleIds already verified for the real
# ANALISTA test account (luuis.guga@gmail.com, configured this wave to
# mirror Camile's own real permissoes_modulos grant) -- never invented.
ANALISTA_ALLOWED_MODULE_IDS = [
    "analiseScoreVendedores", "comissoes", "coparticipadoPortal",
    "dashbi", "gestao", "simuladorCompleto", "simuladorSeminovos"
]


def open_landing_as(page, perfil, is_master, allowed_module_ids):
    """Mirrors ia-entry-01/ia-entry-02's own open_landing_as_master()
    exactly, generalized to any profile -- loads the REAL index.html
    directly (not a harness iframe), then substitutes only the two
    NX_AUTH_CORE accessor functions with what a real authenticated
    bootstrap would have produced for that profile. Never touches
    NX_INTELLIGENCE_PANEL/NX_REGISTRY/isModuleAuthorized -- those stay
    100% real."""
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate(
        """([perfil, isMaster, allowedModuleIds]) => {
            window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
            window.NX_AUTH_CORE.getContext = () => Object.freeze({
                isMaster, perfil, allowedModuleIds,
                nome: perfil === 'MASTER' ? 'UAT MASTER' : 'UAT ' + perfil,
                loja: perfil === 'ANALISTA' ? 'NACOES' : null,
                status: perfil === 'ANALISTA' ? 'NOVOS/SEMINOVOS' : null
            });
            if (window.NX_INTELLIGENCE_PANEL) window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [perfil, is_master, allowed_module_ids]
    )
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
        # REAL-AUTH-SHAPE ANALISTA -- direct index.html load, real
        # runtime machinery, only the bootstrap accessors substituted.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as(page, "ANALISTA", False, ANALISTA_ALLOWED_MODULE_IDS)

        ctx = page.evaluate("window.NX_AUTH_CORE.getContext()")
        state = page.evaluate("window.NX_AUTH_CORE.getState()")
        check("[ANALISTA] bootstrap state is AUTHORIZED", state == "AUTHORIZED", state)
        check("[ANALISTA] effective perfil is ANALISTA", ctx.get("perfil") == "ANALISTA", ctx)
        check("[ANALISTA] isMaster is false", ctx.get("isMaster") is False, ctx)

        authorized = page.evaluate(
            "window.NX_AUTH_CORE.isModuleAuthorized(window.NX_REGISTRY.byId('brabus-intelligence'))"
        )
        check("[ANALISTA] brabus-intelligence module IS authorized (real canonical authority call, no shortcut)", authorized is True, authorized)

        launcher_present = page.locator("#baiLauncherBtn").count() == 1
        check("[ANALISTA] Living Core launcher PRESENT in the real DOM (this is the exact defect the Human found absent on the stale published build)", launcher_present)
        if launcher_present:
            check("[ANALISTA] Living Core launcher visible", page.locator("#baiLauncherBtn").is_visible())
            shot(page, "analista-real-auth-idle.png")

            identity_before = ctx
            # Real click, never location.hash (V2-UAT-06's own lesson).
            page.locator("#baiLauncherBtn").click(position={"x": 13, "y": 10}, force=True)
            page.wait_for_timeout(500)
            drawer_open = page.get_attribute("#baiPanelDrawer", "hidden") is None
            check("[ANALISTA] real click opens the Brabus Intelligence panel", drawer_open)
            shot(page, "analista-real-auth-open.png")

            ctx_after = page.evaluate("window.NX_AUTH_CORE.getContext()")
            check("[ANALISTA] identity stable after opening the panel (perfil/isMaster unchanged)",
                  ctx_after.get("perfil") == "ANALISTA" and ctx_after.get("isMaster") is False, ctx_after)

            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check("[ANALISTA] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        # ============================================================
        # NEGATIVE -- brabus-intelligence explicitly denied for this
        # same ANALISTA-shaped context -> launcher must be completely
        # absent (V2-UAT-05 product rule, preserved).
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as(page, "ANALISTA", False, ANALISTA_ALLOWED_MODULE_IDS)
        check("[NEGATIVE] Living Core present BEFORE the denial override (sanity)", page.locator("#baiLauncherBtn").count() == 1)
        page.evaluate("""() => {
            var orig = window.NX_AUTH_CORE.isModuleAuthorized;
            window.NX_AUTH_CORE.isModuleAuthorized = function (entry) {
                if (entry && entry.id === 'brabus-intelligence') return false;
                return orig(entry);
            };
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""")
        page.wait_for_timeout(400)
        check("[NEGATIVE] Living Core COMPLETELY ABSENT once brabus-intelligence is denied", page.locator("#baiLauncherBtn").count() == 0, page.locator("#baiLauncherBtn").count())
        check("[NEGATIVE] no orphaned launcher root/wrapper left behind either", page.locator("#baiLauncherRoot").count() == 0)
        shot(page, "analista-real-auth-denied.png")
        page.close()

        # ============================================================
        # MASTER regression, same real-auth-shape technique.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as(page, "MASTER", True, [])
        ctx = page.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[MASTER] isMaster true, perfil MASTER (unchanged)", ctx.get("isMaster") is True and ctx.get("perfil") == "MASTER", ctx)
        launcher_present = page.locator("#baiLauncherBtn").count() == 1
        check("[MASTER] Living Core launcher present (unchanged)", launcher_present)
        if launcher_present:
            page.locator("#baiLauncherBtn").click(position={"x": 13, "y": 10}, force=True)
            page.wait_for_timeout(500)
            check("[MASTER] real click opens the panel (unchanged)", page.get_attribute("#baiPanelDrawer", "hidden") is None)
            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check("[MASTER] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== SEC-1C.2: Real-Auth-Shape ANALISTA Living Core ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
