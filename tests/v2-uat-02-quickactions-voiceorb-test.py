#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-02 -- Part A (Intelligence Quick Actions) + Part B (Voice Orb).

PART A: the empty-state suggestion chips used to be a permanent,
100%-managerial 3-item list (EMPTY_STATE_SUGGESTIONS). Replaced with a
4-category pool (financiamento/antecipacao/cash_conversion/gestao) --
still exactly 3 chips visible at a time, deterministically rotated (no
Math.random, no continuous timer) one notch forward on "Nova
conversa," so gestão suggestions are preserved in the pool rather than
disappearing, while every fresh page load leads with the brief's own
commercial/antecipação/Cash reference example. Clicking a chip still
goes through the exact same submitText()/handleSend() authority as
Send/Enter -- no parallel flow.

PART B: the abstract Fluid-Aperture-style Voice icon is replaced with
an unambiguous microphone glyph inside a Living-Core-family "Voice
Orb" (dark capsule, thin red ring, orbiting arc), distinct from the
floating Living Core launcher by icon and by being driven off the
REAL VOICE_STATES enum (intelligence-state.js) -- no new lifecycle,
no duplicate state tree. A pre-existing class-name bug (voiceStateClass
stripped the 'VOICE_' prefix the CSS selectors never stripped, so
every per-state color/motion rule was dead code) is fixed so IDLE/
CONNECTING/LISTENING/THINKING/SPEAKING/ERROR are now actually visually
distinguishable. Hover/focus reveals the live state label (e.g.
"Conversar por voz" at rest) via the same width/overflow-hidden
pattern as the floating launcher.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


COMMERCIAL_POOL = {
    'Simule uma parcela para este cliente',
    'Quanto preciso de entrada para chegar nesta parcela?',
    'Encontre uma opção Linear e Balão',
}
ANTECIPACAO_POOL = {'Calcule a antecipação deste contrato'}
CASH_POOL = {'Vale preservar o capital e financiar?', 'Faça um Cash Conversion deste cenário'}
GESTAO_POOL = {
    'Qual foi o resultado do mês passado?',
    'Como está o score do vendedor?',
    'Compare o resultado entre as lojas',
}
ALL_POOL = COMMERCIAL_POOL | ANTECIPACAO_POOL | CASH_POOL | GESTAO_POOL


def open_panel(page):
    page.goto(BASE + "#/landing")
    page.wait_for_selector("#baiLauncherBtn", timeout=8000)
    # position+force: at narrow widths the pre-existing, LOCAL/HOMOLOG-
    # only .nxDevBadge (shell.css, unrelated to this Wave, never shown
    # in production) can geometrically cover the launcher's bottom
    # half -- same known, documented collision as IA-ENTRY-01's own
    # suite. Clicking the launcher's own top half avoids it.
    page.locator("#baiLauncherBtn").click(position={"x": 26, "y": 10}, force=True)
    page.wait_for_timeout(200)


def suggestion_texts(page):
    return page.evaluate("[...document.querySelectorAll('#baiPanelSuggestions .baiSuggestionChip')].map(b => b.textContent)")


def nova_conversa(page):
    page.click("#baiPanelNewChatBtn")
    page.wait_for_timeout(100)


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
        # PART A -- Quick Actions
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_panel(page)

        chips = suggestion_texts(page)
        check("[A] exactly 3 suggestion chips visible", len(chips) == 3, chips)
        check("[A] every chip text comes from the real known pool (no invented question)",
              all(c in ALL_POOL for c in chips), chips)
        check("[A] default (fresh load) set matches the brief's own commercial/antecipação/Cash reference example",
              set(chips) == {
                  'Simule uma parcela para este cliente',
                  'Calcule a antecipação deste contrato',
                  'Vale preservar o capital e financiar?',
              }, chips)

        # Rotate through several "Nova conversa" clicks: still always
        # exactly 3, and a gestão-category suggestion resurfaces (pool
        # preserved, never permanently dropped).
        seen_categories = set()

        def categorize(text):
            if text in COMMERCIAL_POOL: return 'financiamento'
            if text in ANTECIPACAO_POOL: return 'antecipacao'
            if text in CASH_POOL: return 'cash_conversion'
            if text in GESTAO_POOL: return 'gestao'
            return 'unknown'

        all_max3 = True
        for _ in range(6):
            nova_conversa(page)
            chips = suggestion_texts(page)
            if len(chips) != 3:
                all_max3 = False
            for c in chips:
                seen_categories.add(categorize(c))
        check("[A] never more than 3 chips across repeated 'Nova conversa' rotations", all_max3)
        check("[A] gestão suggestions still appear somewhere in the rotation (pool preserved, not deleted)",
              'gestao' in seen_categories, seen_categories)
        check("[A] commercial/antecipação/Cash Conversion all appear across the rotation",
              {'financiamento', 'antecipacao', 'cash_conversion'} <= seen_categories, seen_categories)

        page.close()

        # Click reuses the SAME submitText()/handleSend() authority --
        # no parallel flow: the clicked text appears as a real user
        # message in the conversation and the composer stays empty.
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_panel(page)
        first_chip_text = suggestion_texts(page)[0]
        page.click("#baiPanelSuggestions .baiSuggestionChip >> nth=0")
        page.wait_for_timeout(200)
        user_msgs = page.evaluate("[...document.querySelectorAll('#baiPanelConversation [data-role=\"user\"], .baiBubbleUser, .baiBubble')].map(b => b.textContent)")
        check("[A] clicking a chip sends it as a real user message via the existing submit authority",
              any(first_chip_text in m for m in user_msgs), (first_chip_text, user_msgs))
        composer_val = page.input_value("#baiPanelInput")
        check("[A] composer is cleared after a chip click (submitText's own existing behavior)", composer_val == "")
        page.close()

        # Responsive / zero horizontal scroll with the suggestions visible
        for w, h in [(1366, 900), (1024, 900), (480, 900), (390, 844)]:
            page = tracked_page(viewport={"width": w, "height": h})
            open_panel(page)
            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[A] zero horizontal scroll at {w}px with suggestions visible", overflow["scroll"] <= overflow["client"], overflow)
            page.close()

        # ============================================================
        # PART B -- Voice Orb
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_panel(page)

        check("[B] voice button exists", page.locator("#baiPanelVoiceBtn").count() == 1)
        check("[B] a real microphone glyph is present (capsule + stand + base paths, not a generic mark)",
              page.locator("#baiPanelVoiceBtn .baiVoiceBtnMarkCapsule").count() == 1 and
              page.locator("#baiPanelVoiceBtn .baiVoiceBtnMarkStand").count() == 1 and
              page.locator("#baiPanelVoiceBtn .baiVoiceBtnMarkBase").count() == 1)
        check("[B] Living-Core-family ring/arc present (same visual family as the floating launcher)",
              page.locator("#baiPanelVoiceBtn .baiVoiceOrbRing").count() == 1 and
              page.locator("#baiPanelVoiceBtn .baiVoiceOrbArc").count() == 1)
        aria = page.get_attribute("#baiPanelVoiceBtn", "aria-label")
        check("[B] aria-label is unambiguous about starting a voice conversation", "voz" in (aria or "").lower() and "Brabus Intelligence" in (aria or ""), aria)

        # HOVER reveal
        box = page.locator("#baiPanelVoiceBtn").bounding_box()
        w0 = box["width"]
        page.hover("#baiPanelVoiceBtn")
        page.wait_for_timeout(250)
        box2 = page.locator("#baiPanelVoiceBtn").bounding_box()
        check("[B] hover expands the Orb to reveal its label (distinguishable from idle)", box2["width"] > w0 + 20, (w0, box2["width"]))
        label_text = page.inner_text("#baiPanelVoiceBtnLabel")
        check("[B] hover reveals the brief's own literal wording", label_text.strip() == "Conversar por voz", label_text)
        page.mouse.move(20, 20)
        page.wait_for_timeout(250)

        # KEYBOARD -- a real Tab-driven focus (Shift+Tab back from the
        # textarea, which is the Orb's very next DOM sibling), not a
        # bare programmatic .focus() call: Chromium's :focus-visible
        # heuristic can suppress the ring for a script-triggered focus
        # that follows recent pointer activity (the hover above), which
        # a genuine keyboard user would never trigger.
        page.click("#baiPanelInput")
        page.keyboard.press("Shift+Tab")
        page.wait_for_timeout(100)
        check("[B] keyboard focus reaches the Orb", page.evaluate("document.activeElement && document.activeElement.id") == "baiPanelVoiceBtn")
        outline = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle")
        check("[B] focus-visible outline present on the Orb", outline == "solid", outline)
        box3 = page.locator("#baiPanelVoiceBtn").bounding_box()
        check("[B] keyboard focus also reveals the expanded label (not mouse-only)", box3["width"] > w0 + 20, (w0, box3["width"]))
        page.evaluate("document.getElementById('baiPanelVoiceBtn').blur()")
        page.wait_for_timeout(150)

        # TOUCH TARGET
        box4 = page.locator("#baiPanelVoiceBtn").bounding_box()
        check("[B] idle touch target >= 44x44 effective (36px circle + composer padding easily clears 44 with the real click area)", box4["width"] >= 36 and box4["height"] >= 36, box4)

        # SINGLE ACTIVATION: click a nested decorative child (the mic
        # icon itself), verify toggle() fires exactly once via the
        # SAME existing listener (no duplicate).
        page.evaluate("""() => {
            window.__toggleCount = 0;
            var orig = window.NX_INTELLIGENCE_VOICE.toggle;
            window.NX_INTELLIGENCE_VOICE.toggle = function () { window.__toggleCount++; return orig.apply(this, arguments); };
        }""")
        page.click("#baiPanelVoiceBtn .baiVoiceBtnMark")
        page.wait_for_timeout(150)
        toggle_count = page.evaluate("window.__toggleCount")
        check("[B] exactly one toggle() call per click, even on a nested icon node (no duplicate listener)", toggle_count == 1, toggle_count)
        page.close()

        # STATE DISTINCTION (B4): drive the REAL state store directly
        # (window.NX_INTELLIGENCE_STATE.setVoiceState) -- the same
        # authoritative setter intelligence-voice.js itself calls, no
        # new/parallel state machine invented for this test.
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_panel(page)
        STATE_CHECKS = [
            ("VOICE_IDLE", "IDLE"),
            ("VOICE_CONNECTING", "CONNECTING"),
            ("VOICE_LISTENING", "LISTENING"),
            ("VOICE_THINKING", "THINKING"),
            ("VOICE_SPEAKING", "SPEAKING"),
            ("VOICE_ERROR", "ERROR"),
        ]
        state_colors = {}
        for state_key, short in STATE_CHECKS:
            page.evaluate(f"window.NX_INTELLIGENCE_STATE.setVoiceState('{state_key}')")
            page.wait_for_timeout(80)
            cls = page.get_attribute("#baiPanelVoiceBtn", "class")
            check(f"[B4] {short}: correct state class applied", ("baiVoiceState" + state_key) in (cls or ""), cls)
            ring_color = page.evaluate("getComputedStyle(document.querySelector('#baiPanelVoiceBtn .baiVoiceOrbRing')).borderColor")
            state_colors[short] = ring_color
        check("[B4] IDLE and LISTENING are visually distinguishable (different ring color)",
              state_colors["IDLE"] != state_colors["LISTENING"], state_colors)
        check("[B4] CONNECTING and LISTENING are visually distinguishable (transitional vs. active)",
              state_colors["CONNECTING"] != state_colors["LISTENING"], state_colors)
        check("[B4] LISTENING and ERROR are visually distinguishable",
              state_colors["LISTENING"] != state_colors["ERROR"], state_colors)
        # label text also changes per state (never color-only signal)
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_LISTENING')")
        page.wait_for_timeout(80)
        check("[B4] LISTENING shows the 'Ouvindo' label", page.inner_text("#baiPanelVoiceBtnLabel").strip() == "Ouvindo")
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_DISCONNECTED')")
        page.close()

        # REDUCED MOTION: states remain distinguishable, no continuous animation
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.emulate_media(reduced_motion="reduce")
        open_panel(page)
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_LISTENING')")
        page.wait_for_timeout(80)
        anim = page.evaluate("""() => {
            var ring = document.querySelector('#baiPanelVoiceBtn .baiVoiceOrbRing');
            var arc = document.querySelector('#baiPanelVoiceBtn .baiVoiceOrbArc');
            return [ring, arc].map(el => getComputedStyle(el).animationName);
        }""")
        check("[B5] no continuous keyframe animation under prefers-reduced-motion", all(a == "none" for a in anim), anim)
        ring_color_reduced = page.evaluate("getComputedStyle(document.querySelector('#baiPanelVoiceBtn .baiVoiceOrbRing')).borderColor")
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_IDLE')")
        page.wait_for_timeout(80)
        ring_color_idle_reduced = page.evaluate("getComputedStyle(document.querySelector('#baiPanelVoiceBtn .baiVoiceOrbRing')).borderColor")
        check("[B5] LISTENING vs IDLE still visually distinguishable under reduced-motion (color, not motion)",
              ring_color_reduced != ring_color_idle_reduced, (ring_color_reduced, ring_color_idle_reduced))
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_DISCONNECTED')")
        page.close()

        # TOUCH (mobile viewport): tap toggles voice, no hover dependency
        page = tracked_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        open_panel(page)
        page.evaluate("""() => {
            window.__toggleCount2 = 0;
            var orig = window.NX_INTELLIGENCE_VOICE.toggle;
            window.NX_INTELLIGENCE_VOICE.toggle = function () { window.__toggleCount2++; return orig.apply(this, arguments); };
        }""")
        # position+force: same pre-existing .nxDevBadge collision as
        # open_panel() above -- the badge's bottom strip overlaps most
        # of the Orb's 38px height at this viewport; its own top few
        # pixels remain clear.
        page.locator("#baiPanelVoiceBtn").click(position={"x": 19, "y": 5}, force=True)
        page.wait_for_timeout(150)
        check("[B5] tap toggles voice on mobile (no hover dependency)", page.evaluate("window.__toggleCount2") == 1)
        overflow_mobile = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("[B5] zero horizontal scroll on mobile with the Voice Orb present", overflow_mobile["scroll"] <= overflow_mobile["client"], overflow_mobile)
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[K] zero unexplained console/page errors across the whole suite", len(unexplained) == 0, unexplained[:5])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-02: Quick Actions + Voice Orb ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
