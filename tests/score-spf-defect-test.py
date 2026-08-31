#!/usr/bin/env python3
"""Gates 2/3/17/18/19 -- PORTAL-NEXT-07.7C receitaSPF non-finite defect.

Proves, in a real browser, against the real code paths (not a
reimplementation):

1. BEFORE: production's own byte-identical calcScores() (the untouched
   reference at PORTAL-NEXT-04/.source/reference-standalone.html, same
   copy score-parity-test.py treats as ground truth) still produces a
   non-finite Score when handed a fins record with receitaSPF absent --
   this is the pre-existing defect, reproduced live, not asserted from
   memory.

2. AFTER: V2's adapter (assets/js/adapters/score.adapter.js), which
   normalizes fins[].receitaSPF via a boundary wrapper BEFORE calling
   the still-untouched calcScores() (see the file's own Gate 14/15
   comment), produces a finite, business-safe Score for the identical
   input.

3. The full Gate 3 missing-value matrix, exercised through the real
   exported normalizeFinInput()/asNumber() (assets/js/adapters/
   score.adapter.js's window.NX_SCORE_ADAPTER._internal) -- not
   reimplemented here.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "score-fixtures.json")

BASE_FIN = {"vendedor": "x", "loja": "y", "dept": "Novos", "valorFinanciado": 100, "retorno": 10}

# (label, JS expression building the fins record, expected receitaSPF after normalizeFinInput)
MATRIX = [
    ("property absent", "{vendedor:'x',loja:'y',dept:'Novos',valorFinanciado:100,retorno:10}", 0),
    ("undefined", "Object.assign({},BASE,{receitaSPF:undefined})", 0),
    ("null", "Object.assign({},BASE,{receitaSPF:null})", 0),
    ("empty string", "Object.assign({},BASE,{receitaSPF:''})", 0),
    ("whitespace string", "Object.assign({},BASE,{receitaSPF:'   '})", 0),
    ("0", "Object.assign({},BASE,{receitaSPF:0})", 0),
    ('"0" string', "Object.assign({},BASE,{receitaSPF:'0'})", 0),
    ("valid positive number", "Object.assign({},BASE,{receitaSPF:1234.56})", 1234.56),
    ("valid numeric string (BRL)", "Object.assign({},BASE,{receitaSPF:'1.234,56'})", 1234.56),
    ("NaN", "Object.assign({},BASE,{receitaSPF:NaN})", 0),
    ("Infinity", "Object.assign({},BASE,{receitaSPF:Infinity})", 0),
    ("-Infinity", "Object.assign({},BASE,{receitaSPF:-Infinity})", 0),
    ("non-numeric text", "Object.assign({},BASE,{receitaSPF:'abc'})", 0),
]


def main():
    from playwright.sync_api import sync_playwright

    fixtures = json.load(open(FIXTURES_PATH, encoding="utf-8"))["cases"]
    case = next(c for c in fixtures if c["id"] == "missing_optional_data")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 1. BEFORE -- untouched production reference still non-finite.
        ref_page = browser.new_page()
        ref_page.goto("http://localhost:8700/PORTAL-NEXT-04/.source/reference-standalone.html")
        ref_rows = ref_page.evaluate(
            "([sales, fins]) => REFERENCE_calcScores(sales, fins)",
            [case["sales"], case["fins"]],
        )
        ref_score = ref_rows[0]["score"]
        before_ok = not (isinstance(ref_score, (int, float)) and math.isfinite(ref_score))
        results.append((f"BEFORE (raw production calcScores): score={ref_score!r} non-finite", before_ok))
        ref_page.close()

        # 2. AFTER -- V2 adapter normalizes, produces a finite score.
        page = browser.new_page()
        page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_adapter-harness.html")
        after_rows = page.evaluate(
            "([sales, fins]) => window.NX_SCORE_ADAPTER.compute(sales, fins)",
            [case["sales"], case["fins"]],
        )
        after_score = after_rows[0]["score"]
        after_ok = isinstance(after_score, (int, float)) and math.isfinite(after_score) and 0 <= after_score <= 1000
        results.append((f"AFTER (V2 adapter): score={after_score!r} finite in [0,1000]", after_ok))

        # 3. Missing-value matrix, via the real exported normalizer.
        page.evaluate("(base) => { window.BASE = base }", BASE_FIN)
        for label, expr, expected in MATRIX:
            got = page.evaluate(
                f"() => window.NX_SCORE_ADAPTER._internal.normalizeFinInput({expr}).receitaSPF"
            )
            finite_ok = isinstance(got, (int, float)) and math.isfinite(got)
            match_ok = finite_ok and abs(got - expected) < 1e-9
            results.append((f"matrix: {label} -> receitaSPF={got!r} (expected {expected!r})", match_ok))

        # 4. Gate 13 -- zero is a legitimate value, not coerced to "missing".
        zero_row = page.evaluate(
            "() => window.NX_SCORE_ADAPTER._internal.normalizeFinInput(Object.assign({},BASE,{receitaSPF:0}))"
        )
        zero_ok = zero_row["receitaSPF"] == 0
        results.append(("Gate 13: receitaSPF=0 preserved as 0 (not miscoerced)", zero_ok))

        page.close()
        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for desc, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {desc}")
    print(f"\n=== Score SPF Defect Regression: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
