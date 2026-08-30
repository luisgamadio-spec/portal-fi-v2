#!/usr/bin/env python3
"""
Gates 17-21 — Landing Composition Regression (permanent test).

Compares fresh renders of the Approved Reference vs V2's Landing at
the same viewports. Tolerances are defined HERE, BEFORE running
against real numbers, and are not adjusted afterward to force a PASS
(Gate 18's own rule) — the numbers below were fixed while writing this
script, prior to seeing any V2 measurement.

Requires: measurement JSON files already captured this Wave at
tests/screenshots/landing-wave/{source,v2}-measurements.json (see
REPORT.md's PORTAL-NEXT-03 entry for the exact capture commands).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "screenshots", "landing-wave")

# Tolerances fixed BEFORE inspecting V2's numbers.
TOL_WIDTH_PCT = 3.0      # fNav/canvas width, as % of fShell width — max allowed drift
TOL_FONT_EXACT = True    # nav item label font-size must match exactly (it's a fixed clamp())

DESKTOP_VIEWPORTS = ["1366x768", "1920x1080"]
MOBILE_VIEWPORTS = ["390x844", "430x932"]

def pct(part, whole):
    return 0 if whole == 0 else 100.0 * part / whole

def main():
    source = json.load(open(os.path.join(DIR, "source-measurements.json"), encoding="utf-8"))
    v2 = json.load(open(os.path.join(DIR, "v2-measurements.json"), encoding="utf-8"))

    checks = []

    def check(label, ok, detail):
        checks.append((label, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {label} — {detail}")

    # Gate 21: source reference resolves (already proven by reference-resolution-test.py,
    # re-asserted here as part of the permanent composition test)
    ref_json = json.load(open(os.path.join(os.path.dirname(HERE), "..", "design-system-2.1", "design-system.normative.json"), encoding="utf-8"))
    landing_ref = next((r for r in ref_json["approvedReferences"] if r["id"] == "module-landing"), None)
    check("Gate 21: source reference resolves", landing_ref is not None and landing_ref["status"] == "APPROVED", f"status={landing_ref['status'] if landing_ref else 'MISSING'}")

    for vp in DESKTOP_VIEWPORTS + MOBILE_VIEWPORTS:
        s = source[vp]; v = v2[vp]

        # Gate 18: structural metrics — nav/canvas proportion within fShell
        s_nav_pct = pct(s["fNav"]["w"], s["fShell"]["w"])
        v_nav_pct = pct(v["fNav"]["w"], v["fShell"]["w"])
        drift = abs(s_nav_pct - v_nav_pct)
        check(f"[{vp}] fNav width proportion within tolerance", drift <= TOL_WIDTH_PCT,
              f"source={s_nav_pct:.1f}% v2={v_nav_pct:.1f}% drift={drift:.1f}pp (tol {TOL_WIDTH_PCT}pp)")

        # Gate 20: Human-Scale Guard — canvas must not disappear
        check(f"[{vp}] canvas region present and non-trivial", v["canvas"] is not None and v["canvas"]["w"] > 50 and v["canvas"]["h"] > 50,
              f"canvas={v['canvas']}")

        # Gate 20: nav must not become a compressed horizontal bar on desktop
        if vp in DESKTOP_VIEWPORTS:
            check(f"[{vp}] nav is NOT a compressed horizontal bar (desktop)", v["fNav"]["h"] > 400,
                  f"fNav height={v['fNav']['h']}")
            # Gate 20: title scale must not be below expected
            check(f"[{vp}] nav item label font-size matches source exactly", v["navItemFontSize"] == s["navItemFontSize"],
                  f"source={s['navItemFontSize']} v2={v['navItemFontSize']}")

        if vp in MOBILE_VIEWPORTS:
            check(f"[{vp}] mobile nav item font-size matches source exactly", v["navItemFontSize"] == s["navItemFontSize"],
                  f"source={s['navItemFontSize']} v2={v['navItemFontSize']}")

        # Gate 20 / Gate 15: no horizontal overflow (mobile MUST derive from reference, not shrink)
        check(f"[{vp}] no horizontal overflow", v["bodyScrollWidth"] <= v["bodyClientWidth"],
              f"scrollWidth={v['bodyScrollWidth']} clientWidth={v['bodyClientWidth']}")

    # Gate 20: no debug metadata — checked by anti-ai-audit.md / grep, cross-referenced here
    debug_terms = ["FICTÍCIO", "LAB ONLY", "Consultor Fictício", "Show Design Trace", "GE-01", "Disponível"]
    with open(os.path.join(os.path.dirname(HERE), "assets", "js", "landing.js"), encoding="utf-8") as f:
        landing_js = f.read()
    found_debug = [t for t in debug_terms if t in landing_js]
    check("no debug/LAB metadata terms in landing.js", not found_debug, f"found={found_debug}")

    print()
    total = len(checks)
    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"=== Landing Composition Regression: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
