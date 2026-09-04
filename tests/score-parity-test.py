#!/usr/bin/env python3
"""
Gates 6-7 — Score Parity Harness.

Compares PRODUCTION Score logic (an independently re-extracted copy at
PORTAL-FI-DESIGN-LAB/PORTAL-NEXT-04/.source/reference-standalone.html,
built directly from `git show origin/main:modules/score.html` — NOT
the local clone, which is proved divergent for this file, see
docs/SCORE-ENGINE-AUDIT.md) against V2's adapter
(assets/js/adapters/score.adapter.js) across all 12 golden fixtures in
tests/fixtures/score-fixtures.json.

Exact equality required (no floating tolerance) — production's own
math has no tolerance built in (Math.round at defined points), so
none is introduced here either (Gate 7's own rule).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "score-fixtures.json")
GOLDEN_PATH = os.path.join(HERE, "fixtures", "score-golden-output.json")

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    fixtures = json.load(open(FIXTURES_PATH, encoding="utf-8"))["cases"]

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Score Foundation Phase 0 forensics: the raw reference's own
        # calcScores() computes `o.retorno += f.retorno + f.receitaSPF`
        # with NO fallback (unlike the adjacent `f.spfQtd||0` one line
        # over) -- real production never actually exercises this gap
        # because its own upstream processFins() builds receitaSPF via
        # `reduce((s,r)=>s+asNumber(...), 0)`, a numeric-seeded reduce
        # that makes "receitaSPF missing" structurally impossible in
        # real data (see score.adapter.js's own PORTAL-NEXT-07.7C
        # normalizeFinInput() and its header comment, an already-made,
        # already-documented decision -- calcScores() itself stays
        # byte-identical/untouched). This test must therefore feed the
        # SAME real-guaranteed input shape to the golden reference that
        # real production would actually guarantee, not run the
        # reference directly against an artificially-impossible raw
        # fixture shape -- a no-op for every other fixture (already-
        # numeric receitaSPF passes through unchanged), and the only
        # correct way to test "does V2 reproduce production math for
        # data production can actually produce."
        def as_number(v):
            if v is None or v == "":
                return 0
            if isinstance(v, (int, float)):
                return v if v == v and v not in (float("inf"), float("-inf")) else 0
            return 0

        def normalize_fins(fins):
            out = []
            for f in fins:
                f2 = dict(f)
                f2["receitaSPF"] = as_number(f.get("receitaSPF"))
                out.append(f2)
            return out

        ref_page = browser.new_page()
        ref_page.goto("http://localhost:8700/PORTAL-NEXT-04/.source/reference-standalone.html")
        goldens = {}
        for case in fixtures:
            goldens[case["id"]] = ref_page.evaluate(
                "([sales, fins]) => REFERENCE_calcScores(sales, fins)",
                [case["sales"], normalize_fins(case["fins"])],
            )
        ref_page.close()

        # Re-save goldens each run (they are regenerated from the reference
        # copy every time, not hand-edited — if this file's content ever
        # changes without a corresponding source re-extraction, that is
        # itself a signal something is wrong).
        with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
            json.dump(goldens, f, indent=2, ensure_ascii=False)

        adapter_page = browser.new_page()
        adapter_page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_adapter-harness.html")
        results = []
        for case in fixtures:
            v2_result = adapter_page.evaluate(
                "([sales, fins]) => window.NX_SCORE_ADAPTER.compute(sales, fins)",
                [case["sales"], case["fins"]],
            )
            golden = goldens[case["id"]]
            match = json.dumps(v2_result, sort_keys=True) == json.dumps(golden, sort_keys=True)
            results.append((case["id"], match))
            print(f"[{'PASS' if match else 'FAIL'}] {case['id']}")
        adapter_page.close()
        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Score Parity: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
