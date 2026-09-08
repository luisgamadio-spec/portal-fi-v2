#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2_SIMULATOR_INSTALLMENT_GRID_VISUAL_FIX -- deterministic geometry
regression for the "Plano Coparticipado" (6 cells), Novos "Financiamento
Linear" (8 cells) and Seminovos "Linear" (9 cells) installment result
grids (.smTermGrid).

Root cause (proven by rendered geometry, not screenshots): .smTermGrid
paints its dividers as the container's own background showing through
1px CSS Grid gaps. `grid-template-columns: repeat(auto-fill,
minmax(110px,1fr))` computes a column count from container width alone,
with no awareness of the actual item count -- whenever the item count
wasn't an exact multiple of that column count, the wrapped last row
still allocated every computed track (auto-fill never collapses unused
trailing tracks), leaving a visible untinted void from the last real
cell to the grid's right edge -- a broken/dangling divider exactly at
the row-wrap boundary (reported by the Human at 24x/36x in Coparticipado
and 24x/30x in Linear -- the exact pair depends on the viewer's own
window width, which determines where the grid happened to wrap).

Fix: .smTermGrid now reads --term-grid-cols, set by the new
UI.wireTermResultGrid() (simuladores-shared.js) via a NEW
balancedColumnsExact() that only accepts a column count that EXACTLY
divides the item count (remainder must be 0) -- guaranteeing every row
is always completely filled edge to edge, at any container width.

This test asserts DOM/geometry invariants, not pixels/screenshots:
- every row's last cell reaches the grid's own right edge (no
  incomplete/empty trailing row -- the actual defect mechanism);
- adjacent cells within a row are separated by exactly the CSS gap
  (no doubled or missing internal divider);
- the outer grid rectangle is intact at every tested width;
- zero horizontal overflow at both page and grid-wrapper level
  (PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE), never via
  overflow-x:auto/hidden.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import os as _os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

NOVOS_BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_simulador-novos-harness.html"
SEMINOVOS_BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_simulador-seminovos-harness.html"
GOVERNED_RPC_URL = "https://mock.invalid/rest/v1/rpc/simulador_get_coparticipado"
WIDTHS = [1366, 1024, 900, 480]
GAP_PX = 1

_FIXTURES_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures")
with open(_os.path.join(_FIXTURES_DIR, "simulador-novos-governed-campanha-contract.json"), encoding="utf-8") as _f:
    GOVERNED_CONTRACT = _json.load(_f)

AUTH_SCRIPT = """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve('tok'); } };
"""

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def analyze_grid(page):
    return page.evaluate(
        """
        () => {
            const grid = document.querySelector('.smTermGrid');
            if (!grid) return null;
            const gridRect = grid.getBoundingClientRect();
            const gcs = getComputedStyle(grid);
            const bL = parseFloat(gcs.borderLeftWidth) || 0;
            const bR = parseFloat(gcs.borderRightWidth) || 0;
            const cards = [...grid.querySelectorAll('.smTermCard')];
            const rows = {};
            cards.forEach(c => {
                const r = c.getBoundingClientRect();
                const y = Math.round(r.y);
                (rows[y] = rows[y] || []).push({x: r.x, w: r.width, term: c.querySelector('.term')?.textContent});
            });
            const rowYs = Object.keys(rows).map(Number).sort((a, b) => a - b);
            const rowsOut = rowYs.map(y => rows[y].sort((a, b) => a.x - b.x));
            return {
                // gridLeft/gridRight are the INNER content edges (border
                // excluded), matching where the cards themselves actually sit.
                gridLeft: gridRect.x + bL, gridRight: gridRect.x + gridRect.width - bR,
                cardCount: cards.length, rows: rowsOut
            };
        }
        """
    )


def page_overflow_ok(page):
    return page.evaluate(
        "document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1"
    )


def grid_wrapper_overflow_ok(page):
    return page.evaluate(
        """() => {
            const grid = document.querySelector('.smTermGrid');
            return grid ? grid.scrollWidth <= grid.clientWidth + 1 : true;
        }"""
    )


def no_overflow_hidden_masking(page):
    # Forbidden as a "fix" per Gate 11 -- confirm the grid itself doesn't
    # rely on overflow:hidden/auto to hide an oversized row (its own
    # 1px border-radius clip, applied to the WHOLE grid, is pre-existing
    # and untouched -- this checks the grid never becomes wider than its
    # own container, which is the actual invariant that matters).
    return page.evaluate(
        """() => {
            const grid = document.querySelector('.smTermGrid');
            const parent = grid && grid.parentElement;
            return !grid || !parent || grid.scrollWidth <= parent.clientWidth + 1;
        }"""
    )


def assert_geometry(label, info, eps=1.0):
    if info is None:
        check(f"{label}: grid found", False)
        return
    ok_rows_fill = all(abs(row[-1]["x"] + row[-1]["w"] - info["gridRight"]) <= eps for row in info["rows"])
    check(f"{label}: every row's last cell reaches the grid's right edge (no incomplete trailing row)", ok_rows_fill)

    ok_gap = True
    for row in info["rows"]:
        for i in range(len(row) - 1):
            observed_gap = row[i + 1]["x"] - (row[i]["x"] + row[i]["w"])
            if abs(observed_gap - GAP_PX) > eps:
                ok_gap = False
    check(f"{label}: adjacent cells separated by exactly {GAP_PX}px (no doubled/missing divider)", ok_gap)

    ok_left = all(abs(row[0]["x"] - info["gridLeft"]) <= eps for row in info["rows"])
    check(f"{label}: every row starts flush with the grid's left edge", ok_left)

    row_counts = [len(r) for r in info["rows"]]
    if len(row_counts) > 1:
        # Every row must use the same column count (uniform grid tracks) --
        # only the LAST row may legitimately have fewer items than columns
        # is not allowed here: balancedColumnsExact() guarantees an exact
        # divisor, so ALL rows (including the last) must be equal length.
        check(f"{label}: all {len(row_counts)} rows have equal item count (exact-divisor column count)", len(set(row_counts)) == 1)


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Novos: Coparticipado (6 cells) + Linear (8 cells) ----------
        for width in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.add_init_script(AUTH_SCRIPT)
            page.route(GOVERNED_RPC_URL + "*", lambda route: route.fulfill(status=200, content_type="application/json", body=_json.dumps(GOVERNED_CONTRACT)))
            page.goto(NOVOS_BASE)
            page.wait_for_function("!!window.NX_SIMULADOR_NOVOS_PAGE")
            page.evaluate("window.NX_SIMULADOR_NOVOS_PAGE.render(document.getElementById('smOutlet'))")

            page.click('.smModeBtn[data-mode="campanha"]')
            page.wait_for_function("window.NX_SIMULADOR_NOVOS_PAGE.getCampState() === 'READY'")
            page.select_option("#nModelo", "ECLIPSE CROSS RUSH")
            page.fill("#nSale", "200000")
            page.fill("#nEntry", "120000")
            page.click("#nCalc")
            page.wait_for_timeout(120)
            info = analyze_grid(page)
            check(f"Novos Coparticipado @{width}px: 6 cards rendered", info is not None and info["cardCount"] == 6)
            assert_geometry(f"Novos Coparticipado @{width}px", info)
            check(f"Novos Coparticipado @{width}px: page horizontal overflow clean", page_overflow_ok(page))
            check(f"Novos Coparticipado @{width}px: grid wrapper horizontal overflow clean", grid_wrapper_overflow_ok(page))
            check(f"Novos Coparticipado @{width}px: no overflow-masking relied on", no_overflow_hidden_masking(page))

            page.click('.smModeBtn[data-mode="linear"]')
            page.fill("#nBem", "100000")
            page.fill("#nEntrada", "20000")
            page.wait_for_timeout(120)
            info2 = analyze_grid(page)
            check(f"Novos Linear @{width}px: 8 cards rendered", info2 is not None and info2["cardCount"] == 8)
            assert_geometry(f"Novos Linear @{width}px", info2)
            check(f"Novos Linear @{width}px: page horizontal overflow clean", page_overflow_ok(page))
            check(f"Novos Linear @{width}px: grid wrapper horizontal overflow clean", grid_wrapper_overflow_ok(page))
            page.close()

        # ---------- Seminovos: Linear/RateTable (9 cells) ----------
        for width in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(SEMINOVOS_BASE)
            page.wait_for_function("!!window.NX_SIMULADOR_SEMINOVOS_PAGE")
            page.evaluate("window.NX_SIMULADOR_SEMINOVOS_PAGE.render(document.getElementById('smOutlet'))")
            page.click('.smModeBtn[data-mode="ratetable"]')
            page.fill("#sAnoRT", "2020")
            page.fill("#sValorRT", "80000")
            page.fill("#sEntradaRT", "0")
            page.click("#sCalc")
            page.wait_for_timeout(120)
            info3 = analyze_grid(page)
            check(f"Seminovos Linear @{width}px: 9 cards rendered", info3 is not None and info3["cardCount"] == 9)
            assert_geometry(f"Seminovos Linear @{width}px", info3)
            check(f"Seminovos Linear @{width}px: page horizontal overflow clean", page_overflow_ok(page))
            check(f"Seminovos Linear @{width}px: grid wrapper horizontal overflow clean", grid_wrapper_overflow_ok(page))
            page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulator Installment Grid Geometry: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
