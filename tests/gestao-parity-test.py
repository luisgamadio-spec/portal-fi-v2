#!/usr/bin/env python3
"""
Gates 27-28 -- Gestão (Análise F&I do Grupo) Parity Harness.

HISTORICAL RECORD ONLY since Wave 2 (RPC-shaped local contract
reconciliation): the client-side upload/classification engine this
test validates was retired from the active render path -- see
assets/js/adapters/_gestao-legacy-upload-engine.js's header. The
active adapter (assets/js/adapters/gestao.adapter.js) is now a thin
response-shaping layer with no classification logic to hold parity
against; store/business-rule authority moved to the production RPC
(operational_fandi_dashboard, proven in Wave 1's backend contract
proof). This test still runs, against the retired engine's own
harness, to keep the hard-won parity proof intact as a historical
record -- it says nothing about the current active Gestão surface.

Compares PRODUCTION Gestão logic (an independently re-extracted copy at
tests/fixtures/_gestao-reference.js, built directly from
`git show origin/main:modules/analise-fi-grupo.html` via a SEPARATE
extraction script/algorithm/wrapper than the one that assembled the
retired engine -- see docs/GESTAO-ENGINE-AUDIT.md and docs/
GESTAO-FUNCTION-MAP.md) against that retired engine across all 26
golden fixtures in tests/fixtures/gestao-fixtures.json.

Exact equality required (no floating tolerance) -- production's own
math has no tolerance built in, so none is introduced here either.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "gestao-fixtures.json")
GOLDEN_PATH = os.path.join(HERE, "fixtures", "gestao-golden-output.json")


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
        ref_page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_gestao-reference-harness.html")
        if ref_errors:
            print("[FATAL] reference page errors:", ref_errors)
            sys.exit(1)

        goldens = {}
        for case in fixtures:
            goldens[case["id"]] = ref_page.evaluate(
                "(fixture) => window.NX_GESTAO_REFERENCE.compute(fixture)",
                {"rows": case["rows"], "start": case["start"], "end": case["end"],
                 "store": case["store"], "vehicle": case["vehicle"]},
            )
        ref_page.close()

        with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
            json.dump(goldens, f, indent=2, ensure_ascii=False, default=str)

        adapter_page = browser.new_page()
        adapter_errors = []
        adapter_page.on("pageerror", lambda e: adapter_errors.append(str(e)))
        adapter_page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_gestao-legacy-upload-engine-harness.html")
        if adapter_errors:
            print("[FATAL] adapter page errors:", adapter_errors)
            sys.exit(1)

        results = []
        for case in fixtures:
            v2_result = adapter_page.evaluate(
                "(fixture) => window.NX_GESTAO_LEGACY_UPLOAD_ENGINE.compute(fixture)",
                {"rows": case["rows"], "start": case["start"], "end": case["end"],
                 "store": case["store"], "vehicle": case["vehicle"]},
            )
            golden = goldens[case["id"]]
            v2_dump = json.dumps(v2_result, sort_keys=True, default=str)
            golden_dump = json.dumps(golden, sort_keys=True, default=str)
            match = v2_dump == golden_dump
            results.append((case["id"], match))
            print(f"[{'PASS' if match else 'FAIL'}] {case['id']}")
            if not match:
                print("  golden :", golden_dump[:600])
                print("  result :", v2_dump[:600])
        adapter_page.close()
        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Gestão Parity: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
