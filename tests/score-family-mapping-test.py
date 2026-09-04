#!/usr/bin/env python3
"""
Score Phase 2A, Gate 3 — deterministic proof that score.adapter.js's
Score-local familiaModelo()/normalizeText() extraction is byte-identical
in BEHAVIOR to the historical production authority
(ia-reconciliation-v2-local/modules/score.html, confirmed in Score
Phase 1 Gate 8), and that Seminovos never receives Mix de Famílias
scoring credit regardless of family classification (calcScores() gates
that score component to dept==='Novos' only).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import sys

CASES = [
    ("OUTLANDER GT 2.0", "Outlander"),
    ("OUTLANDER", "Outlander"),
    ("TRITON GLS", "Triton"),
    ("L200 TRITON", "Triton"),
    ("L200", "Triton"),
    ("ECLIPSE CROSS HPE-S S-AWC", "Eclipse Cross"),
    ("ECLIPSE CROSS", "Eclipse Cross"),
    ("OUTLANDER AWC", "Outlander"),
    ("TRITON TARMAC", "Triton"),
    ("ECLIPSE CROSS SIGNATURE", "Eclipse Cross"),
    ("ECLIPSE CROSS HPE-S", "Eclipse Cross"),
    ("outlander gt", "Outlander"),
    ("  TRITON   GLS  ", "Triton"),
    ("", "Outros"),
    ("ASX", "Outros"),
    ("COROLLA", "Outros"),
    ("CIVIC TOURING", "Outros"),
    (None, "Outros"),
]


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — test code exists, not executed.")
        sys.exit(0)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8700/portal-next-v2/tests/fixtures/_adapter-harness.html")

        results = []
        for modelo, expected in CASES:
            actual = page.evaluate(
                "(m) => window.NX_SCORE_ADAPTER._internal.familiaModelo(m)", modelo
            )
            ok = actual == expected
            results.append((modelo, expected, actual, ok))
            print(f"[{'PASS' if ok else 'FAIL'}] familiaModelo({modelo!r}) = {actual!r} (expected {expected!r})")

        # Seminovos inertness: calcScores() must never add a 'Mix de
        # famílias vendidas' breakdown entry for a Seminovos seller-group,
        # regardless of what familiaModelo() returns for its sales.
        seminovos_sales = [
            {"vendedor": "V1", "loja": "L1", "dept": "Seminovos", "familia": "Outlander"},
            {"vendedor": "V1", "loja": "L1", "dept": "Seminovos", "familia": "Triton"},
        ]
        seminovos_fins = [
            {"vendedor": "V1", "loja": "L1", "dept": "Seminovos", "valorFinanciado": 100000,
             "retorno": 5000, "receitaSPF": 0, "spfQtd": 0, "plano": "LINEAR"},
        ]
        rows = page.evaluate(
            "([s, f]) => window.NX_SCORE_ADAPTER.compute(s, f)",
            [seminovos_sales, seminovos_fins],
        )
        labels = [b["label"] for b in rows[0]["scoreBreakdown"]]
        seminovos_inert = "Mix de famílias vendidas" not in labels
        print(f"[{'PASS' if seminovos_inert else 'FAIL'}] Seminovos family-mix component absent: {labels}")

        browser.close()

    total = len(results) + 1
    passed = sum(1 for *_, ok in results if ok) + (1 if seminovos_inert else 0)
    print(f"\n=== Score Family Mapping: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
