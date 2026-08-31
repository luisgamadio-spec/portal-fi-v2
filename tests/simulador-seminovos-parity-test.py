#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gates 26/27/29 — Simulador Seminovos engine parity harness (PORTAL-NEXT-08).

Covers the 6 REACHABLE Seminovos-specific engines only (Gate 3/33
finding, documented in docs/SIMULATOR-ENGINE-DISCOVERY-08.md): the
top-level "Financiamento Linear" tab (calcLinear/tabelaLinear) and
"Taxas Subsidiadas" (calcSubsidiadas/montaDadosSubsidiadas) are
confirmed DEAD CODE in Seminovos -- their target DOM elements
(#lValorBem/#lEntrada/#lResultados, id="subsidizedScreen") do not
exist anywhere in the real production markup, only in defensively-
guarded JS that safely no-ops. There is no live production DOM path to
verify those two against, so they are excluded here (kept in the
adapter for Gate 3 completeness only).

Drives the real, unmodified, DOM-coupled production engines (top-level
functions against the saved simulador-seminovos-origin-main.html, and
the nested RATE_TABLE Linear engine against its own decoded srcdoc
document) and compares against V2's pure re-derivation
(assets/js/adapters/simulador-seminovos.adapter.js +
simulador-shared.adapter.js).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROD_URL = "http://localhost:8700/PORTAL-NEXT-08/.source/simulador-seminovos-origin-main.html"
LINEAR_RATE_TABLE_URL = "http://localhost:8700/PORTAL-NEXT-08/.source/linear-seminovos-iframe-decoded.html"
ADAPTER_SHARED = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-shared.adapter.js"
ADAPTER_SEMINOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-seminovos.adapter.js"

CENT = 0.005


def brl_to_float(s):
    if s is None:
        return None
    s = s.strip()
    if s in ("", "--", "-", "R$ 0,00"):
        return 0.0 if s == "R$ 0,00" else None
    m = re.search(r"-?[\d.]+,\d+", s)
    if not m:
        return None
    return float(m.group(0).replace(".", "").replace(",", "."))


def pct_to_float(s):
    if s is None:
        return None
    m = re.search(r"-?[\d.]+,\d+", s)
    if not m:
        return None
    return float(m.group(0).replace(".", "").replace(",", "."))


def close(a, b, eps=CENT):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < eps


def main():
    from playwright.sync_api import sync_playwright

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        prod = browser.new_page()
        prod.goto(PROD_URL)
        prod.wait_for_timeout(300)

        adapter = browser.new_page()
        adapter.goto("about:blank")
        adapter.add_script_tag(path=ADAPTER_SHARED)
        adapter.add_script_tag(path=ADAPTER_SEMINOVOS)

        # ---- Tradicional (Balão) -- requires vehicle year band ----
        trad_cases = [
            {"id": "trad_2020_20pct_24x", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "2020", "baloes": []},
            {"id": "trad_2026_40pct_36x", "bem": 100000, "entrada": 40000, "prazo": 36, "ano": "2026", "baloes": []},
            {"id": "trad_below_min_9pct", "bem": 80000, "entrada": 7000, "prazo": 24, "ano": "2020", "baloes": [], "expect_error": True},
            {"id": "trad_year_out_of_band", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "2016", "baloes": [], "expect_error": True},
            {"id": "trad_year_missing", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "", "baloes": [], "expect_error": True},
            {"id": "trad_small_value", "bem": 12000, "entrada": 3000, "prazo": 12, "ano": "2022", "baloes": []},
            {"id": "trad_large_value", "bem": 700000, "entrada": 300000, "prazo": 48, "ano": "2025", "baloes": []},
            {"id": "trad_with_balloon", "bem": 90000, "entrada": 20000, "prazo": 36, "ano": "2021", "baloes": [{"mes": 24, "valor": 12000}]},
        ]
        for c in trad_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('tBem').value = String(c.bem);
                    document.getElementById('tEntrada').value = String(c.entrada);
                    document.getElementById('tPrazo').value = String(c.prazo);
                    document.getElementById('tAno').value = c.ano;
                    document.getElementById('tQtd').value = String(c.baloes.length);
                    renderBaloes();
                    const mesEls = document.querySelectorAll('.tMes');
                    const valEls = document.querySelectorAll('.tValor');
                    c.baloes.forEach((b, i) => { mesEls[i].value = String(b.mes); valEls[i].value = String(b.valor); });
                    calcTrad(true);
                }""",
                c,
            )
            prod_parcela = brl_to_float(prod.evaluate("document.getElementById('tParcela').textContent"))
            prod_error = "error" in (prod.evaluate("document.getElementById('tMsg').className") or "")

            r = adapter.evaluate(
                "(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularTradicional({bem:c.bem, entrada:c.entrada, prazo:c.prazo, ano:c.ano, baloes:c.baloes})",
                c,
            )
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                ok = r.get("error") is None and not prod_error and close(prod_parcela, r.get("parcela"))
            results.append((f"Tradicional/{c['id']}", ok, prod_parcela, r.get("parcela")))

        # ---- Periódico (Semestral/Anual) ----
        period_cases = [
            {"id": "period_semestral_48x", "bem": 80000, "entrada": 20000, "prazo": 48, "tipo": "semestral"},
            {"id": "period_anual_36x", "bem": 90000, "entrada": 25000, "prazo": 36, "tipo": "anual"},
            {"id": "period_below_min", "bem": 60000, "entrada": 5000, "prazo": 24, "tipo": "semestral", "expect_error": True},
            {"id": "period_unsupported_term", "bem": 60000, "entrada": 20000, "prazo": 30, "tipo": "semestral", "expect_error": True},
        ]
        for c in period_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('pBem').value = String(c.bem);
                    document.getElementById('pEntrada').value = String(c.entrada);
                    document.getElementById('pPrazo').value = String(c.prazo);
                    document.getElementById('pTipo').value = c.tipo;
                    calcPeriod(true);
                }""",
                c,
            )
            prod_parcela = brl_to_float(prod.evaluate("document.getElementById('pParcela').textContent"))
            prod_error = "error" in (prod.evaluate("document.getElementById('pMsg').className") or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularPeriodico(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                ok = r.get("error") is None and not prod_error and close(prod_parcela, r.get("parcela"))
            results.append((f"Periodico/{c['id']}", ok, prod_parcela, r.get("parcela")))

        # ---- Descobridor de Taxa ----
        desc_cases = [
            {"id": "desc_typical", "financiado": 70000, "prazo": 36, "parcela": 2400},
            {"id": "desc_invalid_too_low", "financiado": 70000, "prazo": 36, "parcela": 100, "expect_error": True},
        ]
        for c in desc_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('dFinanciado').value = String(c.financiado);
                    document.getElementById('dPrazo').value = String(c.prazo);
                    document.getElementById('dParcela').value = String(c.parcela);
                    calcDescobridor(true);
                }""",
                c,
            )
            prod_taxa = pct_to_float(prod.evaluate("document.getElementById('dTaxa').textContent"))
            prod_error = "error" in (prod.evaluate("document.getElementById('dMsg').className") or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularDescobridor(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                adapter_taxa_pct = r.get("taxaNet") * 100 if r.get("taxaNet") is not None else None
                ok = r.get("error") is None and not prod_error and close(prod_taxa, adapter_taxa_pct, 0.02)
            results.append((f"Descobridor/{c['id']}", ok, prod_taxa, r.get("taxaNet")))

        # ---- Antecipação ----
        ant_cases = [
            {"id": "ant_typical", "prazo": 36, "parcela": 1800, "primeira": "2025-01-10", "data": "2025-05-10", "tipo": "todo"},
            {"id": "ant_prazo_invalid_0", "prazo": 0, "parcela": 1500, "primeira": "2025-01-10", "data": "2025-03-10", "tipo": "todo", "expect_error": True},
        ]
        for c in ant_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('aPrazo').value = String(c.prazo);
                    document.getElementById('aParcela').value = String(c.parcela);
                    document.getElementById('aPrimeiroVenc').value = c.primeira;
                    document.getElementById('aData').value = c.data;
                    document.getElementById('aTipo').value = c.tipo;
                    document.getElementById('aTemBalao').value = 'nao';
                    renderAntecipacaoBaloes();
                    calcAntecipacao(true);
                }""",
                c,
            )
            prod_final = brl_to_float(prod.evaluate("document.getElementById('aValorFinal').textContent"))
            prod_error = "error" in (prod.evaluate("document.getElementById('aMsg').className") or "") and not prod_final

            r = adapter.evaluate(
                """(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularAntecipacao({
                    prazo: c.prazo, parcela: c.parcela,
                    primeiraParcela: new Date(c.primeira + 'T00:00:00'),
                    dataAntecipacao: new Date(c.data + 'T00:00:00'),
                    tipo: c.tipo, baloes: []
                })""",
                c,
            )
            if c.get("expect_error"):
                ok = r.get("error") is not None
            else:
                ok = r.get("error") is None and close(prod_final, r.get("finalTotal"), 0.02)
            results.append((f"Antecipacao/{c['id']}", ok, prod_final, r.get("finalTotal")))

        # ---- Semestral Triton — renderStc() is private; trigger it via
        # the stcBem 'input' event listener wired at IIFE load time. ----
        stc_cases = [
            {"id": "stc_triton_hpe", "bem": 180000, "modelo": "TRITON HPE"},
            {"id": "stc_triton_savana", "bem": 220000, "modelo": "TRITON SAVANA"},
            {"id": "stc_zero_bem", "bem": 0, "modelo": "TRITON HPE", "expect_error": True},
        ]
        for c in stc_cases:
            prod.evaluate(
                """(c) => {
                    const modelSel = document.getElementById('stcModelo');
                    if (modelSel) { modelSel.value = c.modelo; modelSel.dispatchEvent(new Event('change')); }
                    const bemEl = document.getElementById('stcBem');
                    bemEl.value = String(c.bem);
                    bemEl.dispatchEvent(new Event('input'));
                }""",
                c,
            )
            prod_parcela = brl_to_float(prod.evaluate("(() => { const e = document.querySelector('#stcFluxo .stc-flow-item strong'); return e ? e.textContent : null; })()"))
            prod_final_venda = brl_to_float(prod.evaluate("document.getElementById('stcValorFinalVenda') ? document.getElementById('stcValorFinalVenda').textContent : null"))

            r = adapter.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularSemestralTriton(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None
            else:
                ok = r.get("error") is None and close(prod_parcela, r.get("parcela"), 0.02) and close(prod_final_venda, r.get("valorFinalVenda"), 0.02)
            results.append((f"SemestralTriton/{c['id']}", ok, prod_parcela, r.get("parcela")))

        prod.close()

        # ---- "Financiamento Seminovos" — nested RATE_TABLE Linear engine ----
        lin = browser.new_page()
        lin.goto(LINEAR_RATE_TABLE_URL)
        lin.wait_for_timeout(200)

        lrt_cases = [
            {"id": "lrt_2020_0pct", "ano": 2020, "valor": 80000, "entrada": 0},
            {"id": "lrt_2012_20pct", "ano": 2012, "valor": 60000, "entrada": 12000},
            {"id": "lrt_2023_40pct", "ano": 2023, "valor": 100000, "entrada": 42000},
            {"id": "lrt_year_out_of_range", "ano": 2003, "valor": 50000, "entrada": 10000, "expect_invalid": True},
            {"id": "lrt_entry_above_100pct", "ano": 2020, "valor": 50000, "entrada": 60000, "expect_invalid": True},
        ]
        for c in lrt_cases:
            lin.evaluate(
                """(c) => {
                    document.getElementById('ano').value = String(c.ano);
                    document.getElementById('valorVeiculo').value = fmtBRL.format(c.valor);
                    document.getElementById('valorEntrada').value = fmtBRL.format(c.entrada);
                    calculate();
                }""",
                c,
            )
            prod_payments = [
                brl_to_float(x) if x != "" else None
                for x in lin.evaluate("[...document.querySelectorAll('#cards .payment')].map(e => e.textContent)")
            ]
            r = adapter.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularLinearRateTable(c)", c)
            adapter_payments = [t["payment"] for t in r["terms"]]
            if c.get("expect_invalid"):
                ok = r.get("invalid") is True and all(p is None for p in adapter_payments)
            else:
                ok = (
                    r.get("invalid") is False
                    and len(prod_payments) == len(adapter_payments)
                    and all(close(a, b, 0.02) for a, b in zip(prod_payments, adapter_payments))
                )
            results.append((f"LinearRateTable/{c['id']}", ok, prod_payments, adapter_payments))
        lin.close()

        adapter.close()
        browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, prod_v, adapter_v in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  prod={prod_v!r} adapter={adapter_v!r}")
    print(f"\n=== Simulador Seminovos Parity: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
