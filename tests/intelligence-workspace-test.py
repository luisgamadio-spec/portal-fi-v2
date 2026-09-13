#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3I -- Brabus Intelligence INTELLIGENCE WORKSPACE test.

Covers the new presentation architecture introduced this Wave (assets/
css/intelligence.css's ".baiWorkspaceShell" system + assets/js/
intelligence/{intelligence-panel,intelligence-voice-focus}.js): the
large centered Workspace replacing the lateral drawer, the intentional
empty state, the redesigned command surface (icon-only Voice trigger +
Send control), and the Text<->Voice single-shell coordination (Voice
Focus as a STATE of the same Workspace, never a second stacked modal).

Does NOT re-test what unchanged suites already prove: structured-
block rendering (intelligence-panel-test.py), the Voice state machine/
WebRTC/analyser lifecycle (intelligence-voice-foundation-test.py,
intelligence-voice-focus-test.py), D14 (shared-core-gating-test.mjs),
or the retired A/B/C/D orb lab's own isolation (voice-orb-selection-
lab-test.py) -- all re-run unmodified as this Wave's regression proof.

Voice state transitions are driven directly via
NX_INTELLIGENCE_STATE.setVoiceState(), the SAME low-risk convention
intelligence-voice-focus-test.py already established -- Focus Mode
(and now the Workspace coordination built on top of it) only reacts to
STATE, never the underlying WebRTC transport, so no real/faked
RTCPeerConnection is needed to prove the presentation-layer contract
this file is actually about.

Requires: `python -m http.server <port>` running from this worktree's
own root, with assets/js/intelligence-runtime-config.local.js ABSENT
for this run (same pre-existing D17 requirement as every other Voice
suite in this repo).
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-3i")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


def set_profile(page, state, is_master=None, perfil=None):
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(200)


TRUE_OVERFLOW_JS = """
() => {
    var vw = window.innerWidth;
    var worst = 0, worstSel = null;
    document.querySelectorAll('#baiLauncherRoot *, #baiVoiceFocusRoot *').forEach(el => {
        var r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        var over = Math.max(0, r.right - vw) + Math.max(0, -r.left);
        if (over > worst) { worst = over; worstSel = el.className || el.tagName; }
    });
    return { worst: worst, worstSel: String(worstSel) };
}
"""

# Mocked analyser -- if the Voice trigger ever DID instantiate the real
# runtime just by being rendered/hovered/focused, this would catch it.
AUDIO_GUARD_SCRIPT = """
(function () {
  window.__getUserMediaCalls = 0;
  window.__analysersCreated = 0;
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = function () {
      window.__getUserMediaCalls++;
      return Promise.reject(new Error('must never be called merely by rendering the trigger'));
    };
  }
  if (window.AudioContext) {
    var OrigAC = window.AudioContext;
    window.AudioContext = function () {
      var ctx = new OrigAC();
      var orig = ctx.createAnalyser.bind(ctx);
      ctx.createAnalyser = function () { window.__analysersCreated++; return orig(); };
      return ctx;
    };
  }
})();
"""


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script(AUDIO_GUARD_SCRIPT)
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(500)

        # ---------- Portal, before the Workspace ever opens ----------
        shot(page, "13-portal-before-open.png")
        check("Portal renders normally before Workspace ever opens (module content present)",
              page.locator("#nxContentOutlet").count() == 1)
        check("no Intelligence backdrop visible before first open",
              page.evaluate("(function(){var el=document.getElementById('baiPanelBackdrop'); return !el || el.hidden;})()"))

        set_profile(page, "AUTHORIZED", True, "MASTER")
        open_panel(page)

        # ---------- Workspace opens centered, large, over a darkened Portal ----------
        geo = page.evaluate(
            """() => {
                var d = document.getElementById('baiPanelDrawer');
                var r = d.getBoundingClientRect();
                return { left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                         vw: window.innerWidth, vh: window.innerHeight, w: r.width, h: r.height };
            }"""
        )
        left_margin = geo["left"]
        right_margin = geo["vw"] - geo["right"]
        top_margin = geo["top"]
        bottom_margin = geo["vh"] - geo["bottom"]
        check("Workspace is roughly horizontally centered (left/right margins within 2px)", abs(left_margin - right_margin) <= 2, (left_margin, right_margin))
        check("Workspace is roughly vertically centered (top/bottom margins within 2px)", abs(top_margin - bottom_margin) <= 2, (top_margin, bottom_margin))
        check("Workspace occupies a large majority of the viewport width (>=75%)", geo["w"] / geo["vw"] >= 0.75, geo)
        check("Workspace occupies a large majority of the viewport height (>=75%)", geo["h"] / geo["vh"] >= 0.75, geo)
        check("old lateral drawer presentation is gone -- not docked to the right edge", right_margin > 20, right_margin)

        check("Portal darkened behind the Workspace (backdrop visible)",
              page.evaluate("!document.getElementById('baiPanelBackdrop').hidden"))
        backdrop_bg = page.evaluate("getComputedStyle(document.getElementById('baiPanelBackdrop')).backgroundColor")
        check("backdrop genuinely paints a dark scrim (not transparent)", backdrop_bg not in ("rgba(0, 0, 0, 0)", "transparent"), backdrop_bg)
        shot(page, "01-workspace-empty-1366.png")

        # ---------- Empty state (intentional composition) ----------
        check("empty state visible when conversation is empty", page.evaluate("!document.getElementById('baiPanelEmptyState').hidden"))
        check("empty state shows the real heading", "Como posso ajudar" in page.locator("#baiPanelEmptyState").inner_text())
        check("a small number of truthful suggestions present (3-4)", 3 <= page.locator(".baiSuggestionChip").count() <= 4)
        shot(page, "02-command-surface-empty-1366.png")

        # ---------- Command surface ----------
        check("command surface (.baiPanelComposer) present", page.locator(".baiPanelComposer").count() == 1)
        check("Voice trigger present inside the command surface", page.locator(".baiPanelComposer #baiPanelVoiceBtn").count() == 1)
        check("Send control present inside the command surface", page.locator(".baiPanelComposer #baiPanelSendBtn").count() == 1)
        # V2-UAT-02 (Section B3): the label is no longer permanently
        # screen-reader-only (position:absolute/clip) -- it's still
        # invisible AT REST (this check), but now genuinely reveals on
        # hover/focus as a discoverable "Conversar por voz" affordance
        # (covered by tests/v2-uat-02-quickactions-voiceorb-test.py),
        # which a permanently-clipped sr-only technique could never do.
        check("no persistent visible 'Voz' text at rest (collapsed via max-width/opacity, reveals on hover/focus)",
              page.evaluate("getComputedStyle(document.getElementById('baiPanelVoiceBtnLabel')).opacity") == "0")
        check("no generic 'Enviar' text visible on the Send control",
              "Enviar" not in page.locator("#baiPanelSendBtn").inner_text())
        check("Send control has an accessible name", page.locator("#baiPanelSendBtn").get_attribute("aria-label") == "Enviar mensagem")

        # ---------- Send: disabled empty, active with text ----------
        check("Send starts disabled with an empty composer", page.locator("#baiPanelSendBtn").is_disabled())
        page.fill("#baiPanelInput", "Qual foi o resultado do mês passado?")
        check("Send becomes enabled once real text is present", not page.locator("#baiPanelSendBtn").is_disabled())
        check("Send visually gains authority (active class) once text is present",
              "baiSendBtnActive" in page.locator("#baiPanelSendBtn").get_attribute("class"))
        page.fill("#baiPanelInput", "")
        check("Send returns to disabled once text is cleared", page.locator("#baiPanelSendBtn").is_disabled())
        shot(page, "03-command-surface-text-active-1366.png")

        # ---------- Textarea grows, Enter submits (existing semantics preserved) ----------
        page.fill("#baiPanelInput", "linha um\nlinha dois\nlinha três\nlinha quatro")
        h_multi = page.evaluate("document.getElementById('baiPanelInput').getBoundingClientRect().height")
        page.fill("#baiPanelInput", "x")
        h_single = page.evaluate("document.getElementById('baiPanelInput').getBoundingClientRect().height")
        check("textarea grows with multi-line content", h_multi > h_single, (h_multi, h_single))
        page.fill("#baiPanelInput", "Qual foi o resultado do mês passado?")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        check("Enter submits (existing semantics preserved)", page.locator("#baiPanelConversation .baiMessageUser").count() >= 1)
        page.wait_for_timeout(300)
        shot(page, "04-workspace-conversation-1366.png")
        check("structured response still renders (renderer preserved)", page.locator("#baiPanelConversation .baiCompactMetrics").count() >= 1)
        shot(page, "05-structured-response-1366.png")
        check("empty state hides once a real conversation exists", page.evaluate("document.getElementById('baiPanelEmptyState').hidden") is True)

        # ---------- Voice trigger: accessible, no runtime until clicked ----------
        vbtn = page.locator("#baiPanelVoiceBtn")
        check("Voice trigger is a real <button>", vbtn.evaluate("e => e.tagName") == "BUTTON")
        check("Voice trigger accessible name mentions 'voz'", "voz" in (vbtn.get_attribute("aria-label") or "").lower())
        vbtn.hover()
        page.wait_for_timeout(150)
        check("hovering the Voice trigger never calls getUserMedia", page.evaluate("window.__getUserMediaCalls") == 0)
        check("hovering the Voice trigger never creates an AnalyserNode", page.evaluate("window.__analysersCreated") == 0)

        # ---------- Text -> Voice: the SAME shell transforms, no nested modal ----------
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_LISTENING')")
        page.wait_for_timeout(200)
        check("Voice Focus becomes visible on a Voice state transition", page.evaluate("!document.getElementById('baiVoiceFocusRoot').hidden"))
        check("Text drawer visually recedes (Section 24: transforms, not a second modal)",
              page.evaluate("document.getElementById('baiPanelDrawer').classList.contains('baiPanelDrawerReceded')"))
        check("Text drawer's own `hidden` attribute is untouched by the Voice transition (state/conversation preserved, not closed)",
              page.evaluate("document.getElementById('baiPanelDrawer').hidden") is False)
        vf_geo = page.evaluate(
            """() => {
                var p = document.querySelector('.baiVoiceFocusPanel');
                var r = p.getBoundingClientRect();
                return { w: r.width, h: r.height, vw: window.innerWidth, vh: window.innerHeight };
            }"""
        )
        check("Voice Focus shares the SAME large Workspace footprint (not a smaller nested dialog)",
              vf_geo["w"] / vf_geo["vw"] >= 0.75 and vf_geo["h"] / vf_geo["vh"] >= 0.75, vf_geo)
        # No nested modal: at most ONE of {Text drawer, Voice Focus} is
        # actually on-screen at a time.
        visible_count = page.evaluate(
            """() => {
                var t = document.getElementById('baiPanelDrawer');
                var v = document.getElementById('baiVoiceFocusRoot');
                var tVisible = !t.hidden && getComputedStyle(t).display !== 'none';
                var vVisible = !v.hidden;
                return (tVisible ? 1 : 0) + (vVisible ? 1 : 0);
            }"""
        )
        check("no nested-modal stacking -- exactly one of Text/Voice panels is visible", visible_count == 1, visible_count)
        shot(page, "06-text-to-voice-transition.png")
        shot(page, "07-voice-focus-1366.png")

        # ---------- Voice -> Text: returns to the SAME Workspace, conversation intact ----------
        conv_len_before = page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation().length")
        page.click("#baiVoiceFocusTextBtn")
        page.wait_for_timeout(200)
        check("'Voltar ao texto' hides Voice Focus", page.evaluate("document.getElementById('baiVoiceFocusRoot').hidden") is True)
        check("Text drawer is revealed again (same Workspace, not a fresh one)",
              page.evaluate("!document.getElementById('baiPanelDrawer').classList.contains('baiPanelDrawerReceded')"))
        check("conversation context preserved across the Voice interlude", page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation().length") == conv_len_before)
        check("still exactly one of Text/Voice panels visible after returning", page.evaluate(
            """() => {
                var t = document.getElementById('baiPanelDrawer');
                var v = document.getElementById('baiVoiceFocusRoot');
                var tVisible = !t.hidden && getComputedStyle(t).display !== 'none';
                var vVisible = !v.hidden;
                return (tVisible ? 1 : 0) + (vVisible ? 1 : 0);
            }"""
        ) == 1)
        shot(page, "08-voice-to-text-return.png")
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_DISCONNECTED')")
        page.wait_for_timeout(100)

        # ---------- Workspace closes correctly ----------
        page.click("#baiPanelCloseBtn")
        page.wait_for_timeout(150)
        check("Workspace closes: drawer hidden", page.evaluate("document.getElementById('baiPanelDrawer').hidden") is True)
        check("Workspace closes: backdrop hidden (Portal returns to normal)", page.evaluate("document.getElementById('baiPanelBackdrop').hidden") is True)
        check("Workspace closes: body no longer marked open", not page.evaluate("document.body.classList.contains('bai-panel-open')"))
        shot(page, "14-portal-after-close.png")
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        # ---------- Close while Voice is active also cleanly ends the session ----------
        open_panel(page)
        page.evaluate("window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_LISTENING')")
        page.wait_for_timeout(150)
        page.evaluate("window.__endCalled = 0; window.__realEnd = window.NX_INTELLIGENCE_VOICE.end; window.NX_INTELLIGENCE_VOICE.end = function(){ window.__endCalled++; window.__realEnd(); };")
        page.click("#baiPanelCloseBtn")
        page.wait_for_timeout(150)
        check("closing the Workspace while Voice is active ends the Voice session (no orphaned background call)", page.evaluate("window.__endCalled") >= 1)
        check("closing the Workspace while Voice is active also hides Voice Focus", page.evaluate("document.getElementById('baiVoiceFocusRoot').hidden") is True)
        page.evaluate("window.NX_INTELLIGENCE_VOICE.end = window.__realEnd;")

        # ---------- Reduced motion: Workspace still opens/works, no functionality lost ----------
        rp = browser.new_page(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        rp.add_init_script(AUDIO_GUARD_SCRIPT)
        rp.goto(BASE + "#/landing")
        rp.wait_for_timeout(500)
        set_profile(rp, "AUTHORIZED", True, "MASTER")
        open_panel(rp)
        check("reduced motion: Workspace still opens and is usable", rp.locator("#baiPanelDrawer").is_visible())
        check("reduced motion: command surface still present", rp.locator(".baiPanelComposer").count() == 1)
        rp.close()

        # ---------- Zero horizontal scroll (Section 34) ----------
        # Workspace was closed by the previous section -- reopen it so
        # the responsive evidence (09-12) actually shows the OPEN
        # Workspace at each breakpoint, not the Portal underneath.
        open_panel(page)
        for w in (1366, 1024, 900, 480):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
            page_overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{w}px: no page horizontal overflow", page_overflow <= 0, page_overflow)
            comp = page.evaluate(
                """() => {
                    function w(sel) { var el = document.querySelector(sel); return el ? {sw: el.scrollWidth, cw: el.clientWidth} : null; }
                    return { header: w('.baiPanelHeader'), body: w('.baiPanelBody'), composer: w('.baiPanelComposer'), input: w('#baiPanelInput') };
                }"""
            )
            for key in ("header", "body", "composer", "input"):
                v = comp[key]
                check(f"{w}px: .{key} no overflow", v and v["sw"] <= v["cw"] + 1, v)
            tov = page.evaluate(TRUE_OVERFLOW_JS)
            check(f"{w}px: no element truly escapes the viewport", tov["worst"] <= 0.5, tov)
        page.set_viewport_size({"width": 1024, "height": 900})
        page.wait_for_timeout(150)
        shot(page, "09-workspace-1024.png")
        page.set_viewport_size({"width": 900, "height": 900})
        page.wait_for_timeout(150)
        shot(page, "10-workspace-900.png")
        page.set_viewport_size({"width": 480, "height": 900})
        page.wait_for_timeout(150)
        shot(page, "11-workspace-480.png")
        shot(page, "12-command-surface-480.png")
        page.set_viewport_size({"width": 1366, "height": 900})

        page.close()

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        browser.close()

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence Workspace Test (IA-3I): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
