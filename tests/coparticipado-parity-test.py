#!/usr/bin/env python3
"""
Gates 13-14 -- Coparticipado Parity Harness.

Compares PRODUCTION Coparticipado logic (an independently re-extracted
copy at tests/fixtures/_coparticipado-reference.js, built directly from
`git show origin/main:modules/coparticipado.html` via a SEPARATE
extraction script/algorithm/wrapper than the one that assembled
assets/js/adapters/coparticipado.adapter.js -- see docs/
COPARTICIPADO-ENGINE-AUDIT.md and docs/COPARTICIPADO-EXTRACTION-TRACE.md)
against V2's adapter across all 22 golden fixtures in
tests/fixtures/coparticipado-fixtures.json.

Exact equality required (no floating tolerance) -- production's own
math has no tolerance built in, so none is introduced here either.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "coparticipado-fixtures.json")
GOLDEN_PATH = os.path.join(HERE, "fixtures", "coparticipado-golden-output.json")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available -- harness code exists, not executed.")
        sys.exit(0)

    fixtures = json.load(open(FIXTURES_PATH, encoding="utf-8"))["cases"]

    with sync_playwright() as p:
        browser = p.chromium.launch()

        ref_page = browser.new_page()
        ref_errors = []
        ref_page.on("pageerror", lambda e: ref_errors.append(str(e)))
        ref_page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_coparticipado-reference-harness.html")
        if ref_errors:
            print("[FATAL] reference page errors:", ref_errors)
            sys.exit(1)

        goldens = {}
        for case in fixtures:
            goldens[case["id"]] = ref_page.evaluate(
                "(fixture) => window.NX_COPARTICIPADO_REFERENCE.compute(fixture)",
                {
                    "vendorRows": case["vendorRows"],
                    "taxasCopart": case["taxasCopart"],
                    "b1Rows": case["b1Rows"],
                    "b2Rows": case["b2Rows"],
                    "b3Rows": case["b3Rows"],
                },
            )
        ref_page.close()

        with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
            json.dump(goldens, f, indent=2, ensure_ascii=False, default=str)

        adapter_page = browser.new_page()
        adapter_errors = []
        adapter_page.on("pageerror", lambda e: adapter_errors.append(str(e)))
        adapter_page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_coparticipado-adapter-harness.html")
        if adapter_errors:
            print("[FATAL] adapter page errors:", adapter_errors)
            sys.exit(1)

        results = []
        for case in fixtures:
            v2_result = adapter_page.evaluate(
                "(fixture) => window.NX_COPARTICIPADO_ADAPTER.compute(fixture)",
                {
                    "vendorRows": case["vendorRows"],
                    "taxasCopart": case["taxasCopart"],
                    "b1Rows": case["b1Rows"],
                    "b2Rows": case["b2Rows"],
                    "b3Rows": case["b3Rows"],
                },
            )
            golden = goldens[case["id"]]
            v2_dump = json.dumps(v2_result, sort_keys=True, default=str)
            golden_dump = json.dumps(golden, sort_keys=True, default=str)
            match = v2_dump == golden_dump
            results.append((case["id"], match))
            print(f"[{'PASS' if match else 'FAIL'}] {case['id']}")
            if not match:
                print("  golden :", golden_dump[:500])
                print("  result :", v2_dump[:500])
        adapter_page.close()
        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Coparticipado Parity: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
