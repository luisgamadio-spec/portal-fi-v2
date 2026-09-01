#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wave 3D Gate 27 -- Score presentation parity harness.

Same philosophy as coparticipado-presentation-parity-test.py /
simulador-novos-presentation-test.py: 0 hardcoded expected field
values -- everything the DOM shows is compared against
window.NX_SCORE_ADAPTER.compute() (the SAME calculation the page
itself calls), computed live in the same page. This validates the
CURRENT markup against the CURRENT adapter on every run, so it keeps
guarding presentation-vs-business parity for any future Wave, not just
this one.

Covers all 12 fixtures in tests/fixtures/score-fixtures.json (rank,
seller, store, department, score, financiamento count, and the
resolved score-band label) -- record count, record order, and every
rendered field. Also exercises the desktop table AND the mobile card
renderer directly (score.js keeps two independent renderers fed by the
same computed rows -- Gate 18/Gate 20 requires both to agree with the
adapter, and this test proves it, not just one presentation).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/score"

FIXTURE_IDS = ['low', 'high', 'very_low', 'middle', 'very_high', 'confidence_boundary',
               'zero_values', 'missing_optional_data', 'large_values', 'long_name',
               'tie_case', 'sorting_case']


def expected_rows(page, case_data):
    """Compute the expected rendered rows live via the real adapter +
    the same band classifier the page itself uses -- independent of
    the DOM."""
    return page.evaluate(
        """
        (caseData) => {
          const rows = window.NX_SCORE_ADAPTER.compute(caseData.sales, caseData.fins);
          return rows.map((r, i) => {
            const band = window.NX_SCORE_PAGE.classifyScoreBand(r.score);
            return {
              rank: String(i + 1),
              vendedor: r.vendedor,
              loja: r.loja,
              dept: r.dept,
              score: String(r.score),
              fin: String(r.fin || 0),
              band: band ? band.label : '',
            };
          });
        }
        """,
        case_data,
    )


def dom_desktop_rows(page):
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('.scDesktopOnly .scTable tbody tr')).map(tr => {
          const cells = tr.children;
          return {
            rank: cells[0].textContent.trim(),
            vendedor: cells[1].textContent.trim(),
            loja: cells[2].textContent.trim(),
            dept: cells[3].textContent.trim(),
            score: cells[4].querySelector('.scScoreValueRow > span:last-child').textContent.trim(),
            fin: cells[5].textContent.trim(),
            band: (cells[4].querySelector('.scBand') || {}).textContent || '',
          };
        })
        """
    )


def dom_mobile_rows(page):
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('.scMobileOnly .scMobileCard')).map(card => ({
          rank: card.querySelector('.scMobileRank').textContent.trim().replace('#', ''),
          vendedor: card.querySelector('.scMobileName').textContent.trim(),
          loja_dept: card.querySelector('.scMobileSub').textContent.trim(),
          score: card.querySelector('.scMobileScoreValue').textContent.trim(),
          fin: card.querySelector('.scMobileValue').textContent.trim(),
          band: (card.querySelector('.scBand') || {}).textContent || '',
        }))
        """
    )


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # desktop presentation (>=768px)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(500)

        fixtures = page.evaluate(
            "() => fetch('tests/fixtures/score-fixtures.json').then(r => r.json()).then(d => d.cases)"
        )
        by_id = {c["id"]: c for c in fixtures}

        for fixture_id in FIXTURE_IDS:
            page.select_option("#scFixtureSelect", fixture_id)
            page.wait_for_timeout(200)

            exp = expected_rows(page, by_id[fixture_id])
            exp_simple = [(r["rank"], r["vendedor"], r["loja"], r["dept"], r["score"], r["fin"], r["band"]) for r in exp]

            actual = dom_desktop_rows(page)
            actual_simple = [(r["rank"], r["vendedor"], r["loja"], r["dept"], r["score"], r["fin"], r["band"]) for r in actual]

            name = f"{fixture_id}::desktop"
            ok = actual_simple == exp_simple
            results.append((name, ok, None if ok else f"dom={actual_simple} expected={exp_simple}"))

        page.close()

        # mobile presentation (<768px) -- same fixtures, different renderer
        page = browser.new_page(viewport={"width": 390, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(500)

        for fixture_id in FIXTURE_IDS:
            page.select_option("#scFixtureSelect", fixture_id)
            page.wait_for_timeout(200)

            exp = expected_rows(page, by_id[fixture_id])
            exp_simple = [(r["rank"], r["vendedor"], r["loja"] + " · " + r["dept"], r["score"], r["fin"], r["band"]) for r in exp]

            actual = dom_mobile_rows(page)
            actual_simple = [(r["rank"], r["vendedor"], r["loja_dept"], r["score"], r["fin"], r["band"]) for r in actual]

            name = f"{fixture_id}::mobile"
            ok = actual_simple == exp_simple
            results.append((name, ok, None if ok else f"dom={actual_simple} expected={exp_simple}"))

        page.close()

        if errors:
            print("[FATAL] page errors:", errors)
            sys.exit(1)
        browser.close()

    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== Score Presentation Parity: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
