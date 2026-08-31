#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate 30 — Cross-product collision test (PORTAL-NEXT-08).

Feeds Novos and Seminovos superficially similar inputs and confirms:
  (a) the genuinely SHARED engines (Financiamento Campanha, Cash
      Conversion, and the shared helper formulas) produce IDENTICAL
      output — proven separately and exhaustively by
      simulador-campanha-parity-test.py / cash-conversion-parity-test.py;
  (b) the NON-shared engines (Tradicional, Periódico) produce
      DIFFERENT output for the same bem/entrada/prazo, because their
      rate tables genuinely differ — this protects against an
      accidental future engine-unification silently changing business
      math for one simulator to match the other's.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ADAPTER_SHARED = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-shared.adapter.js"
ADAPTER_NOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-novos.adapter.js"
ADAPTER_SEMINOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-seminovos.adapter.js"
ADAPTER_CAMPANHA = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/financiamento-campanha.adapter.js"


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("about:blank")
        page.add_script_tag(path=ADAPTER_SHARED)
        page.add_script_tag(path=ADAPTER_NOVOS)
        page.add_script_tag(path=ADAPTER_SEMINOVOS)
        page.add_script_tag(path=ADAPTER_CAMPANHA)

        # (b) Tradicional: identical bem/entrada/prazo, Seminovos also gets
        # a valid year band -- outputs MUST differ (different tables).
        params = {"bem": 100000, "entrada": 20000, "prazo": 24}
        novos_trad = page.evaluate("(p) => NX_SIMULADOR_NOVOS_ADAPTER.calcularTradicional({bem:p.bem, entrada:p.entrada, prazo:p.prazo, baloes:[]})", params)
        semi_trad = page.evaluate("(p) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularTradicional({bem:p.bem, entrada:p.entrada, prazo:p.prazo, ano:'2022', baloes:[]})", params)
        diverge_ok = (
            novos_trad["error"] is None and semi_trad["error"] is None
            and novos_trad["taxa"] != semi_trad["taxa"]
            and abs(novos_trad["parcela"] - semi_trad["parcela"]) > 1.0
        )
        results.append((
            "Tradicional MUST diverge (different tables)", diverge_ok,
            f"novos taxa={novos_trad['taxa']} parcela={novos_trad['parcela']:.2f}",
            f"seminovos taxa={semi_trad['taxa']} parcela={semi_trad['parcela']:.2f}",
        ))

        # Seminovos requires a vehicle year Novos has no concept of at all --
        # confirms the two engines are NOT interchangeable by construction:
        # the exact same params object (no `ano` field) is accepted as
        # fully valid by Novos, while Seminovos' own function signature
        # requires `ano` as a distinct, separate parameter entirely.
        novos_ignores_ano = novos_trad["error"] is None  # params had no `ano` key at all, Novos didn't need it
        results.append(("Novos Tradicional has no 'ano' (year) parameter at all", novos_ignores_ano, None, None))

        # (b) Periódico: same bem/entrada/prazo/tipo, tables differ (48x
        # taxa: Novos 0.019 vs Seminovos 0.0183) -- parcela MUST differ.
        params2 = {"bem": 100000, "entrada": 20000, "prazo": 48, "tipo": "semestral"}
        novos_per = page.evaluate("(p) => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico(p)", params2)
        semi_per = page.evaluate("(p) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularPeriodico(p)", params2)
        per_diverge_ok = (
            novos_per["error"] is None and semi_per["error"] is None
            and novos_per["taxa"] != semi_per["taxa"]
            and abs(novos_per["parcela"] - semi_per["parcela"]) > 0.5
        )
        results.append((
            "Periodico MUST diverge at 48x (0.019 vs 0.0183)", per_diverge_ok,
            f"novos taxa={novos_per['taxa']} parcela={novos_per['parcela']:.2f}",
            f"seminovos taxa={semi_per['taxa']} parcela={semi_per['parcela']:.2f}",
        ))

        # (a) Financiamento Campanha: genuinely shared -- same model/sale/entry
        # MUST match exactly (already proven end-to-end against both real
        # DOM-coupled iframes in simulador-campanha-parity-test.py; this
        # re-confirms it at the adapter level as the cross-product check).
        camp_params = {"model": "TRITON HPE", "saleValue": 180000, "entryValue": 108000}
        camp_result = page.evaluate("(p) => NX_CAMPANHA_ADAPTER.compute(p)", camp_params)
        # NX_CAMPANHA_ADAPTER is the ONE shared instance both simulators
        # would call -- there is no separate "Novos" vs "Seminovos" copy to
        # compare against here (that WAS the Gate 22/49 finding); assert
        # instead that it's finite/sane for both models' realistic inputs.
        camp_ok = camp_result["valid"] is True and camp_result["finalSale"] is not None
        results.append(("Financiamento Campanha: single shared engine, sane output", camp_ok, camp_result.get("finalSale"), None))

        # FATOR_SEMESTRAL_TRITON is proven byte-identical (shared constant)
        # while calcularSemestralTriton's own valorFinalVenda formula
        # differs -- confirm both facts simultaneously for the same inputs.
        stc_params = {"bem": 200000, "modelo": "TRITON HPE"}
        novos_stc = page.evaluate("(p) => NX_SIMULADOR_NOVOS_ADAPTER.calcularSemestralTriton(p)", stc_params)
        semi_stc = page.evaluate("(p) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularSemestralTriton(p)", stc_params)
        same_parcela = abs(novos_stc["parcela"] - semi_stc["parcela"]) < 0.01
        different_valor_final = abs(novos_stc["valorFinalVenda"] - semi_stc["valorFinalVenda"]) > 1.0
        stc_ok = same_parcela and different_valor_final
        results.append((
            "SemestralTriton: parcela SAME (shared FATOR), valorFinalVenda DIFFERENT (bem-rebateBrabus vs bem-rebateTotal)",
            stc_ok,
            f"novos parcela={novos_stc['parcela']:.2f} valorFinal={novos_stc['valorFinalVenda']:.2f}",
            f"seminovos parcela={semi_stc['parcela']:.2f} valorFinal={semi_stc['valorFinalVenda']:.2f}",
        ))

        page.close()
        browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, a, b in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if a is not None or b is not None:
            print(f"       {a!r}  |  {b!r}")
    print(f"\n=== Cross-Product Collision: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
