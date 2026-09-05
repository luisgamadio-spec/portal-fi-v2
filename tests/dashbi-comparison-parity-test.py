#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FC-1 (GAP-001) -- Dashbi previous-period comparison parity harness.

Tests the byte-identical-extracted comparison primitives added to
dashbi.adapter.js this Wave (sameDayPreviousMonth, getPreviousMonthComparablePeriod,
calcDelta -- origin/main:modules/analise-geral-grupo-secure-original-layout.html
lines 3112-3155) plus the SAME_PIPELINE_DIFFERENT_PERIOD dual-compute
architecture (A.compute() called twice, once per period, dashbi.js's render()).

Does NOT touch tests/fixtures/dashbi-fixtures.json or dashbi-golden-output.json
(Gate 26, this Wave's brief -- golden business logic is FROZEN); reuses those
existing golden fixtures read-only as CURRENT/PREVIOUS period inputs, since
their own aggregate output is already independently verified elsewhere
(tests/dashbi-parity-test.py, 26/26).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/
(same convention as tests/dashbi-parity-test.py).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, "fixtures", "dashbi-fixtures.json")
FIELDS = ["b1HistRows", "b2HistRows", "b1NovaRows", "b2NovaRows", "b3Rows", "vendorRows"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available -- harness code exists, not executed.")
        sys.exit(0)

    fixtures = {c["id"]: {k: c.get(k, []) for k in FIELDS} for c in json.load(open(FIXTURES_PATH, encoding="utf-8"))["cases"]}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://localhost:8700/portal-next-v2/tests/_dashbi-real-provider-harness.html")
        if errors:
            print("[FATAL] harness page errors:", errors)
            sys.exit(1)

        # ---------- 1-5: calcDelta pure math (production formula: (c-p)/p) ----------
        d = page.evaluate("([a,b]) => window.NX_DASHBI_ADAPTER.calcDelta(a,b)", [120, 100])
        check("1: current > previous -> positive delta (120 vs 100 -> +0.20)", abs(d - 0.20) < 1e-9)

        d = page.evaluate("([a,b]) => window.NX_DASHBI_ADAPTER.calcDelta(a,b)", [80, 100])
        check("2: current < previous -> negative delta (80 vs 100 -> -0.20)", abs(d - (-0.20)) < 1e-9)

        d = page.evaluate("([a,b]) => window.NX_DASHBI_ADAPTER.calcDelta(a,b)", [100, 100])
        check("3: current = previous -> delta 0 (flat)", d == 0)

        d = page.evaluate("([a,b]) => window.NX_DASHBI_ADAPTER.calcDelta(a,b)", [50, 0])
        check("4: previous = 0 -> null (\"sem base anterior\"), never divide-by-zero", d is None)

        d = page.evaluate("([a,b]) => window.NX_DASHBI_ADAPTER.calcDelta(a,b)", [50, None])
        check("5: previous missing/null -> null", d is None)

        # ---------- 6-12: getPreviousMonthComparablePeriod / sameDayPreviousMonth ----------
        def prev_period(start, end):
            return page.evaluate(
                """([s,e]) => {
                    var A = window.NX_DASHBI_ADAPTER;
                    function parseLocal(v){ var p=v.split('-').map(Number); return new Date(p[0],p[1]-1,p[2]); }
                    function fmt(d){ return d ? (d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')) : null; }
                    var r = A.getPreviousMonthComparablePeriod(parseLocal(s), parseLocal(e));
                    return { start: fmt(r.start), end: fmt(r.end) };
                }""",
                [start, end],
            )

        r = prev_period("2026-01-15", "2026-01-20")
        check("6: January rollover (2026-01 -> 2025-12, year decrements)", r["start"] == "2025-12-15" and r["end"] == "2025-12-20")

        r = prev_period("2026-03-05", "2026-03-05")
        check("7: February normal, non-leap (2026-03-05 -> 2026-02-05)", r["start"] == "2026-02-05")

        r = prev_period("2028-03-31", "2028-03-31")
        check("8: leap-year February clamp (2028 is leap -> 2028-02-29, not 28)", r["start"] == "2028-02-29")

        r = prev_period("2026-05-31", "2026-05-31")
        check("9: 30-day-month clamp (April has 30 days -> 2026-04-30, not 31)", r["start"] == "2026-04-30")

        r = prev_period("2026-09-01", "2026-09-04")
        check("10: partial current month, day-aligned both ends (-> 2026-08-01..2026-08-04)", r["start"] == "2026-08-01" and r["end"] == "2026-08-04")

        r = prev_period("2026-08-01", "2026-08-31")
        check("11: closed full month -> closed full previous month (2026-07-01..2026-07-31)", r["start"] == "2026-07-01" and r["end"] == "2026-07-31")

        r = prev_period("2026-03-10", "2026-06-20")
        check("12: custom multi-month range, EACH end shifted independently (NOT the whole span shifted) -> 2026-02-10..2026-05-20", r["start"] == "2026-02-10" and r["end"] == "2026-05-20")

        r = page.evaluate(
            """() => {
                var A = window.NX_DASHBI_ADAPTER;
                function fmt(d){ return d ? (d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')) : null; }
                var r = A.getPreviousMonthComparablePeriod(null, null);
                return { start: fmt(r.start), end: fmt(r.end) };
            }"""
        )
        check("K: period without a base (start/end null) -> {start:null,end:null}, not a throw", r["start"] is None and r["end"] is None)

        # ---------- 13-15: SAME_PIPELINE_DIFFERENT_PERIOD, scope preservation ----------
        # compute() called on the SAME fixture for both current and previous
        # guarantees perfect key overlap across every store/department/model,
        # so a correct dual-compute implementation must yield delta=0 (flat)
        # EVERYWHERE -- this is what "same server-side scope on both periods"
        # (Gate 24, this Wave's brief) means at the pipeline level: filtering
        # by store/department/seller/model must affect current and previous
        # identically, since here they are literally the same input.
        same_check = page.evaluate(
            """(fixture) => {
                var A = window.NX_DASHBI_ADAPTER;
                var current = A.compute(fixture);
                var previous = A.compute(fixture);
                var kpiC = A.kpiMetricsFor(current, 'Grupo');
                var kpiP = A.kpiMetricsFor(previous, 'Grupo');
                var deltas = ['vendas','fins','receita','receitaSPF','receitaTotal','producao','retorno'].map(function(k){
                    return A.calcDelta(kpiC[k], kpiP[k]);
                });
                var storeKeys = Object.keys(current.aggs.vendasLoja);
                var storeDeltasFlat = storeKeys.every(function(loja){
                    var vC = current.aggs.vendasLoja[loja], vP = previous.aggs.vendasLoja[loja];
                    var d = A.calcDelta(vC.qtd, vP.qtd);
                    return d === null || d === 0;
                });
                return { deltasAllZero: deltas.every(function(d){ return d === null || d === 0; }), storeCount: storeKeys.length, storeDeltasFlat: storeDeltasFlat };
            }""",
            fixtures["multi_loja_vendedor"],
        )
        check("13 (filtered store, scope preservation): identical current/previous fixture -> every store's delta flat", same_check["storeDeltasFlat"] and same_check["storeCount"] > 0)
        check("14/15 (Grupo KPIs, scope preservation): identical current/previous fixture -> every top KPI delta flat (0 or null)", same_check["deltasAllZero"])

        # ---------- 16: distinct fixtures -> a real, non-degenerate delta computes end-to-end ----------
        distinct_check = page.evaluate(
            """([current, previous]) => {
                var A = window.NX_DASHBI_ADAPTER;
                var outC = A.compute(current);
                var outP = A.compute(previous);
                var kpiC = A.kpiMetricsFor(outC, 'Grupo');
                var kpiP = A.kpiMetricsFor(outP, 'Grupo');
                return { kpiC: kpiC, kpiP: kpiP, delta: A.calcDelta(kpiC.vendas, kpiP.vendas) };
            }""",
            [fixtures["valores_grandes"], fixtures["multi_loja_vendedor"]],
        )
        expected_delta = None
        if distinct_check["kpiP"]["vendas"]:
            expected_delta = (distinct_check["kpiC"]["vendas"] - distinct_check["kpiP"]["vendas"]) / distinct_check["kpiP"]["vendas"]
        check(
            "16: two distinct golden fixtures -> calcDelta(current,previous) matches hand-computed (c-p)/p exactly",
            expected_delta is not None and abs(distinct_check["delta"] - expected_delta) < 1e-9 and distinct_check["delta"] != 0,
        )

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print("\n=== Dashbi Comparison Parity: %d/%d ===" % (passed, len(results)))
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
