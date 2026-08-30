#!/usr/bin/env python3
"""
Gate 31/40 — Visual comparison harness (mechanism only).

This proves the MECHANISM (render source reference + render V2 result
+ capture both) exists and works, per the Skill's Gate 3 Visual Source
of Truth workflow. It does NOT declare visual parity — nothing is
migrated yet, so there is nothing to compare Landing's placeholder
against and call equal. Composition comparison itself remains a
human/AI judgment call for a future Wave, exactly as the Skill
requires (DOM/CSS/screenshot presence is not proof of visual parity).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/,
and a second static server (any port) serving the Approved Reference,
OR this script serves both from the SAME 8700 server since both live
under the Lab root already.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "screenshots")

SOURCE_URL = "http://localhost:8700/design-system-2.1/references/baselines/module-landing-approved/index.html"
V2_URL = "http://localhost:8700/portal-next-v2/index.html#/landing"

VIEWPORTS = [(1366, 768), (390, 844)]

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available in this environment — harness code exists,")
        print("not executed this run. Install playwright to actually capture.")
        sys.exit(0)

    os.makedirs(OUT_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in VIEWPORTS:
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(SOURCE_URL)
            page.wait_for_timeout(300)
            source_path = os.path.join(OUT_DIR, f"compare-source-landing-{w}x{h}.png")
            page.screenshot(path=source_path)
            print(f"[OK] source reference captured: {os.path.relpath(source_path, V2_ROOT)}")
            page.close()

            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(V2_URL)
            page.wait_for_timeout(300)
            v2_path = os.path.join(OUT_DIR, f"compare-v2-landing-placeholder-{w}x{h}.png")
            page.screenshot(path=v2_path)
            print(f"[OK] V2 result captured: {os.path.relpath(v2_path, V2_ROOT)}")
            page.close()
        browser.close()

    print()
    print("RESULT: harness mechanism PASS — both a source reference and a V2 result")
    print("can be rendered and captured side by side. NO COMPARISON was performed or")
    print("claimed: V2's Landing is an unmigrated placeholder, not a candidate for")
    print("parity — comparing it to the reference and calling anything 'matched' or")
    print("'different' would be meaningless. That judgment happens when Wave 1 actually")
    print("migrates Landing, using these same two capture calls plus real composition review.")

if __name__ == "__main__":
    main()
