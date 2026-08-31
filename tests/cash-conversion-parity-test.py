#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate 31 — Cash Conversion goldens (PORTAL-NEXT-08).

cash-conversion.adapter.js is a byte-identical extraction (Gate 5/16/17
of PORTAL-NEXT-08's discovery doc) of origin/main:assets/js/
cash-conversion.js, shared unmodified by both simulators. This test
proves the extracted copy computes identically to the real, saved
origin/main file for a representative coverage set (Gate 31).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ORIGIN_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/PORTAL-NEXT-08/.source/cash-conversion-origin-main.js"
ADAPTER_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/cash-conversion.adapter.js"

CASES = [
    {"id": "minimo_capital", "capital": 1000, "parcela": 100, "prazoMeses": 12, "taxaAplicacao": 0.005},
    {"id": "tipico", "capital": 100000, "parcela": 2500, "prazoMeses": 36, "taxaAplicacao": 0.008},
    {"id": "capital_alto", "capital": 5000000, "parcela": 50000, "prazoMeses": 48, "taxaAplicacao": 0.01},
    {"id": "prazo_curto_1", "capital": 20000, "parcela": 1800, "prazoMeses": 1, "taxaAplicacao": 0.007},
    {"id": "prazo_longo_60", "capital": 300000, "parcela": 6500, "prazoMeses": 60, "taxaAplicacao": 0.009},
    {"id": "taxa_zero", "capital": 50000, "parcela": 2000, "prazoMeses": 24, "taxaAplicacao": 0},
    {"id": "equivalente_by_construction", "capital": 100000, "parcela": None, "prazoMeses": 24, "taxaAplicacao": 0.008},
    {"id": "invalido_capital_zero", "capital": 0, "parcela": 1000, "prazoMeses": 12, "taxaAplicacao": 0.01, "expect_null": True},
    {"id": "invalido_parcela_negativa", "capital": 10000, "parcela": -100, "prazoMeses": 12, "taxaAplicacao": 0.01, "expect_null": True},
    {"id": "invalido_prazo_zero", "capital": 10000, "parcela": 500, "prazoMeses": 0, "taxaAplicacao": 0.01, "expect_null": True},
    # NOTE: JS `isFinite(null)` is `true` (Number(null)===0) -- passing
    # None/null here would NOT trigger the invalid-input guard in either
    # the reference or the adapter (confirmed identical, not a bug).
    # Use a real non-finite value (Infinity) to exercise that guard.
    {"id": "invalido_taxa_nao_finita", "capital": 10000, "parcela": 500, "prazoMeses": 12, "taxaAplicacao": float("inf"), "expect_null": True},
]


def main():
    from playwright.sync_api import sync_playwright

    # equivalente_by_construction: choose parcela so valorFinalFinanciamento == capital*(1+taxa)^n exactly.
    c = next(x for x in CASES if x["id"] == "equivalente_by_construction")
    capital, taxa, n = c["capital"], c["taxaAplicacao"], c["prazoMeses"]
    valor_futuro = capital * (1 + taxa) ** n
    c["parcela"] = round(valor_futuro / n, 10)

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        ref = browser.new_page()
        ref.goto("about:blank")
        ref.add_script_tag(path=ORIGIN_JS)

        adapter = browser.new_page()
        adapter.goto("about:blank")
        adapter.add_script_tag(path=ADAPTER_JS)

        for c in CASES:
            params = {"capital": c["capital"], "parcela": c["parcela"], "prazoMeses": c["prazoMeses"], "taxaAplicacao": c["taxaAplicacao"]}
            ref_r = ref.evaluate("(p) => CashConversion.calcularCashConversion(p)", params)
            adapter_r = adapter.evaluate("(p) => window.NX_CASH_CONVERSION_ADAPTER.compute(p)", params)

            ref_json = json.dumps(ref_r, sort_keys=True)
            adapter_json = json.dumps(adapter_r, sort_keys=True)
            ok = ref_json == adapter_json
            if c.get("expect_null"):
                ok = ok and ref_r is None
            results.append((c["id"], ok, ref_r, adapter_r))

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, rv, av in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  ref={rv!r} adapter={av!r}")
    print(f"\n=== Cash Conversion Goldens: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
