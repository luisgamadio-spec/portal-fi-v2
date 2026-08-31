#!/usr/bin/env python3
"""Gate 23-24 -- Score Band classifier tests (PORTAL-NEXT-07.7B).

Exercises window.NX_SCORE_PAGE.classifyScoreBand() directly in a real
browser -- the ONE authoritative classifier (assets/js/score.js), not a
reimplementation of its logic here. Boundary values are the exact
HUMAN-APPROVED thresholds from docs/SCORE-BAND-NORMATIVE-07-7B.md
(PORTAL-NEXT-07.7A Option 1). Requires:
`python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import math
import sys

# (score, expected_label_or_None)
BOUNDARY_CASES = [
    (0, "CRÍTICO"), (299, "CRÍTICO"),
    (300, "DESENVOLVIMENTO"), (549, "DESENVOLVIMENTO"),
    (550, "PERFORMANCE"), (749, "PERFORMANCE"),
    (750, "ALTA PERFORMANCE"), (899, "ALTA PERFORMANCE"),
    (900, "ELITE"), (1000, "ELITE"),
]

INVALID_CASES = [
    ("NaN", None), ("Infinity", None), ("-Infinity", None),
    ("null", None), ("undefined", None), (-1, None),
]

# Representative real fixture scores (Gate 24) -- exact values computed
# by the real adapter across the 12 golden fixtures (see
# docs/SCORE-BAND-DISCOVERY-07-7A.md's Gate 4/5).
REPRESENTATIVE_CASES = [
    (71, "CRÍTICO"),           # AAA BAIXO PERF (very_low)
    (380, "DESENVOLVIMENTO"),  # RRR REF ALTO / DDD REF PERF / TTT REF PERF
    (533, "DESENVOLVIMENTO"),  # HHH TRES VENDAS (confidence_boundary)
    (803, "ALTA PERFORMANCE"),  # CCC MEDIO PERF (middle) -- the "~795" case
                                # from the brief, exact fixture value used
                                # per Gate 24's own instruction
    (955, "ELITE"),   # GGG QUATRO VENDAS (confidence_boundary) -- the
                      # "~967" case from the brief, exact value used
    (968, "ELITE"),   # P1 RANK PRIMEIRO (sorting_case)
    (1000, "ELITE"),  # BBB TOPO PERF / EEE MELHOR PERF
]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://localhost:8700/portal-next-v2/index.html#/score")
        page.wait_for_timeout(600)
        if errors:
            print("[FATAL] page errors on load:", errors)
            sys.exit(1)

        results = []

        for score, expected in BOUNDARY_CASES:
            band = page.evaluate("(s) => window.NX_SCORE_PAGE.classifyScoreBand(s)", score)
            label = band["label"] if band else None
            ok = label == expected
            results.append((f"boundary {score} -> {expected}", ok, label))

        for expr, expected in INVALID_CASES:
            band = page.evaluate(f"() => window.NX_SCORE_PAGE.classifyScoreBand({expr})")
            label = band["label"] if band else None
            ok = label == expected
            results.append((f"invalid {expr} -> {expected}", ok, label))

        for score, expected in REPRESENTATIVE_CASES:
            band = page.evaluate("(s) => window.NX_SCORE_PAGE.classifyScoreBand(s)", score)
            label = band["label"] if band else None
            ok = label == expected
            results.append((f"representative {score} -> {expected}", ok, label))

        # PORTAL-NEXT-07.7C: the fixture that used to produce a NaN Score
        # (receitaSPF absent) is now normalized to 0 at the adapter
        # boundary (see assets/js/adapters/score.adapter.js) -- it must
        # produce a real, finite, business-safe Score and band end to
        # end, computed live (not hardcoded) via the real adapter +
        # classifier. See docs/SCORE-RECEITA-SPF-NONFINITE-07-7C.md.
        fixtures = page.evaluate("() => fetch('tests/fixtures/score-fixtures.json').then(r => r.json())")
        case = [c for c in fixtures["cases"] if c["id"] == "missing_optional_data"][0]
        rows = page.evaluate("(c) => window.NX_SCORE_ADAPTER.compute(c.sales, c.fins)", case)
        row = rows[0]
        score = row["score"]
        band = page.evaluate("(s) => window.NX_SCORE_PAGE.classifyScoreBand(s)", score)
        label = band["label"] if band else None
        ok = isinstance(score, (int, float)) and math.isfinite(score) and score == 431 and label == "DESENVOLVIMENTO"
        results.append((f"formerly-NaN fixture now finite (score={score!r}) -> DESENVOLVIMENTO", ok, label))

        passed = sum(1 for _, ok, _ in results if ok)
        for desc, ok, actual in results:
            print(f"[{'PASS' if ok else 'FAIL'}] {desc} (got: {actual!r})")

        print(f"\n=== Score Band Tests: {passed}/{len(results)} ===")
        print("RESULT:", "PASS" if passed == len(results) else "FAIL")
        browser.close()
        sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
