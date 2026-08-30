#!/usr/bin/env python3
"""
Gates 30/41 — Foundation Test Harness.

Runs every STATIC (non-browser) check this Foundation has. Routing,
responsive layout, keyboard/focus, and reduced-motion behavior are
real-browser concerns and are NOT re-implemented here as a fake DOM
simulation — they are verified separately with Playwright (Gates 42-44,
already run manually this phase; see docs/DEVELOPMENT.md for the
exact commands to re-run them). This harness does not pretend a static
scan proves what only a real browser can prove — see the "NOT COVERED
HERE" section at the end of the output.
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

CHECKS = [
    ("Token authority sync (Gate 8/9)", ["python", os.path.join(V2_ROOT, "config", "validate-token-authority.py")]),
    ("Module registry structure (Gate 13/39)", ["python", os.path.join(HERE, "registry-test.py")]),
    ("Landing reference resolution (Gate 21)", ["python", os.path.join(HERE, "reference-resolution-test.py")]),
    ("No business logic (Gate 16)", ["python", os.path.join(HERE, "business-logic-scanner.py")]),
    ("Prototype + V1 contamination (Gates 33-34)", ["python", os.path.join(HERE, "contamination-scanner.py")]),
    ("Landing Composition Regression (Gates 17-21)", ["python", os.path.join(HERE, "landing-composition-regression.py")]),
    ("Score Parity (Gates 6-7)", ["python", os.path.join(HERE, "score-parity-test.py")]),
]

def main():
    results = []
    for label, cmd in CHECKS:
        print(f"\n=== {label} ===")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            print(proc.stderr)
        results.append((label, proc.returncode == 0))

    print("\n" + "=" * 60)
    print("FOUNDATION REGRESSION SUMMARY")
    print("=" * 60)
    for label, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    all_ok = all(ok for _, ok in results)

    print("\nNOT COVERED HERE (real-browser only — see docs/DEVELOPMENT.md):")
    print("  - environment guard (must load in a real browser to check window.NX_ENVIRONMENT)")
    print("  - network guard (must load in a real browser + navigate to check 0 flagged requests)")
    print("  - responsive shell across 6 breakpoints")
    print("  - keyboard/focus order, skip-link behavior")
    print("  - reduced-motion CSS actually applying")
    print("  These were run manually via Playwright each Wave — see REPORT.md's")
    print("  PORTAL-NEXT-02/03/04 entries for the exact results, and re-run them")
    print("  the same way before trusting this Foundation again after any future")
    print("  change.")

    print(f"\nRESULT: {'PASS' if all_ok else 'FAIL'} ({sum(1 for _,ok in results if ok)}/{len(results)} static checks)")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
