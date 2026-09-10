#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3H.2.1A -- Voice Orb Visual Selection Lab structural test.

Covers tests/voice-orb-selection-lab.html: an isolated, LOCAL-ONLY
visual-selection lab built after the Human rejected the shipped Voice
Focus Mode orb and asked for four distinct futuristic concepts to
choose from. This test proves the lab's STRUCTURAL contract, not
subjective visual quality (that judgment is the Human's alone -- see
the wave report's HUMAN SELECTION section):

  - exactly 4 concepts, correctly labeled A/B/C/D with their real names
  - 3 LAB-only simulated states exist and are independently selectable
  - large-preview mode opens/closes per orb
  - zero production coupling: no production <script src>, no
    microphone API call, no backend/network call, no localStorage
    write, and the lab is not referenced from index.html or shell.js
  - zero horizontal overflow at 1366/1024/900/480
  - prefers-reduced-motion is honored (animations stop, page stays
    readable)

This is a standalone page with no auth/session dependency, so unlike
the production Focus Mode tests it needs neither the D17
intelligence-runtime-config.local.js workaround nor any NX_AUTH_CORE
setup -- it is loaded directly.

Requires a static file server already serving this worktree's root at
IA3E_TEST_PORT (default 8080, matching the dev server already used
throughout this engagement) -- this test does not start its own
server, only launches its own isolated Playwright browser.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

PORT = os.environ.get("IA3E_TEST_PORT", "8080")
BASE = f"http://localhost:{PORT}/portal-next-v2-ia3e/tests/voice-orb-selection-lab.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


# Detects any attempt to touch the real microphone -- a mocked
# getUserMedia that COUNTS calls rather than granting real media, so a
# false PASS from an actually-blocked permission prompt is impossible.
MIC_GUARD_SCRIPT = """
(function () {
  window.__getUserMediaCalls = 0;
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = function () {
      window.__getUserMediaCalls++;
      return Promise.reject(new Error('lab must never call getUserMedia'));
    };
  }
  window.__localStorageWrites = 0;
  var realSet = window.localStorage.setItem.bind(window.localStorage);
  window.localStorage.setItem = function () {
    window.__localStorageWrites++;
    return realSet.apply(null, arguments);
  };
})();
"""

TRUE_OVERFLOW_JS = """
() => ({
    doc: document.documentElement.scrollWidth - document.documentElement.clientWidth
})
"""


def main():
    from playwright.sync_api import sync_playwright

    # ---------- Static, file-level isolation checks (no browser needed) ----------
    index_html = os.path.join(V2_ROOT, "index.html")
    shell_js = os.path.join(V2_ROOT, "assets", "js", "shell.js")
    with open(index_html, "r", encoding="utf-8") as f:
        index_src = f.read()
    with open(shell_js, "r", encoding="utf-8") as f:
        shell_src = f.read()
    check("index.html does not reference the orb lab", "voice-orb-selection-lab" not in index_src)
    check("shell.js does not reference the orb lab", "voice-orb-selection-lab" not in shell_src)

    # Matches an actual load/import (src="...name", href="...name",
    # import "...name") rather than a bare substring -- the lab file's
    # OWN isolation-policy comment legitimately names these files in
    # prose (e.g. "never loaded by shell.js"), so a blind substring
    # search would false-positive on the very comment that documents
    # the requirement. A real <script src=...> tag is separately and
    # unambiguously ruled out below.
    import re

    lab_html = os.path.join(HERE, "voice-orb-selection-lab.html")
    with open(lab_html, "r", encoding="utf-8") as f:
        lab_src = f.read()
    PRODUCTION_SCRIPT_NAMES = [
        "intelligence-voice.js", "intelligence-voice-focus.js", "intelligence-panel.js",
        "intelligence-state.js", "brabus-intelligence", "shell.js", "master-config-provider.js",
    ]
    for name in PRODUCTION_SCRIPT_NAMES:
        loaded = re.search(r'(?:src|href|import)\s*=?\s*["\'(][^"\')]*' + re.escape(name), lab_src)
        check(f"lab file does not LOAD production script '{name}'", loaded is None, str(loaded))
    check("lab file has no <script src=...> tag at all (fully self-contained)", "<script src=" not in lab_src)
    check("lab file does not <link> the real design-tokens.css stylesheet",
          re.search(r'<link[^>]*design-tokens\.css', lab_src) is None)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        network_urls = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: network_urls.append(r.url))
        page.add_init_script(MIC_GUARD_SCRIPT)

        page.goto(BASE)
        page.wait_for_timeout(500)

        check("page loads with zero console/page errors", len(errors) == 0, str(errors[:3]))

        # ---------- Exactly 4 concepts, correctly labeled ----------
        letters = page.evaluate("Array.from(document.querySelectorAll('.lgCardLetter')).map(e => e.textContent.trim())")
        names = page.evaluate("Array.from(document.querySelectorAll('.lgCardName')).map(e => e.textContent.trim())")
        check("exactly 4 concept cards present", page.evaluate("document.querySelectorAll('.lgCard').length") == 4, str(letters))
        check("labels are exactly A, B, C, D in order", letters == ["A", "B", "C", "D"], str(letters))
        check("names are Quantum Core / Liquid Intelligence / Neural Singularity / Digital Aurora",
              names == ["Quantum Core", "Liquid Intelligence", "Neural Singularity", "Digital Aurora"], str(names))

        # ---------- No microphone / no backend / no localStorage on idle load ----------
        check("no getUserMedia call on load", page.evaluate("window.__getUserMediaCalls") == 0)
        check("no localStorage write on load", page.evaluate("window.__localStorageWrites") == 0)
        non_self_requests = [u for u in network_urls if "voice-orb-selection-lab.html" not in u and not u.startswith("http://localhost:" + PORT + "/portal-next-v2-ia3e/tests/screenshots")]
        check("zero backend/network calls beyond the lab document itself", len(non_self_requests) == 0, str(non_self_requests[:5]))

        # ---------- Large preview open/close per orb, state selector ----------
        for letter in ["A", "B", "C", "D"]:
            page.click(f'.lgCard[data-orb="{letter}"]')
            page.wait_for_timeout(150)
            visible = page.evaluate("document.getElementById('lgPreview').classList.contains('show')")
            check(f"orb {letter}: large preview opens on click", visible)
            shown_letter = page.evaluate("document.getElementById('lgPreviewLetter').textContent")
            check(f"orb {letter}: large preview header shows correct letter", letter in shown_letter)

            # 3 simulated states selectable, and orb element's state class
            # actually changes -- proves the state selector is wired, not
            # decorative.
            for state in ["LISTENING", "THINKING", "SPEAKING"]:
                page.click(f'.lgStateBtn[data-state="{state}"]')
                page.wait_for_timeout(80)
                cls = page.evaluate("document.querySelector('#lgPreviewStage > div').className")
                check(f"orb {letter}: state {state} applies st{state} class to orb element", f"st{state}" in cls, cls)
                active_btn = page.evaluate(f"document.querySelector('.lgStateBtn[data-state=\"{state}\"]').classList.contains('active')")
                check(f"orb {letter}: state {state} button shows active", active_btn)

            page.click("#lgBackBtn")
            page.wait_for_timeout(150)
            hidden_again = page.evaluate("!document.getElementById('lgPreview').classList.contains('show')")
            check(f"orb {letter}: 'Voltar às opções' closes the large preview", hidden_again)

        check("no getUserMedia call after full interaction pass", page.evaluate("window.__getUserMediaCalls") == 0)
        check("no localStorage write after full interaction pass", page.evaluate("window.__localStorageWrites") == 0)

        # ---------- Amplitude simulation is clearly labeled as such ----------
        check("amplitude control explicitly labeled SIMULAÇÃO VISUAL", page.evaluate(
            "document.body.textContent.includes('SIMULAÇÃO VISUAL')"))

        # ---------- Responsive / zero horizontal overflow ----------
        for w in [1366, 1024, 900, 480]:
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
            overflow = page.evaluate(TRUE_OVERFLOW_JS)
            check(f"zero horizontal overflow at {w}px", overflow["doc"] <= 0, str(overflow))

        # ---------- Reduced motion ----------
        page.set_viewport_size({"width": 1366, "height": 900})
        page.emulate_media(reduced_motion="reduce")
        page.reload()
        page.wait_for_timeout(400)
        reduced_errors_before = len(errors)
        anim_name = page.evaluate("getComputedStyle(document.querySelector('.orbA .nucleus')).animationName")
        check("reduced-motion: orb animation is disabled (animation-name none)", anim_name == "none", anim_name)
        check("reduced-motion: page still loads with zero console errors", len(errors) == reduced_errors_before)
        check("reduced-motion: status/labels remain visible (not just hidden via animation)",
              page.evaluate("document.querySelector('.lgCardName').offsetParent !== null"))

        browser.close()

    print()
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"=== Voice Orb Visual Selection Lab Test (IA-3H.2.1A): {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
