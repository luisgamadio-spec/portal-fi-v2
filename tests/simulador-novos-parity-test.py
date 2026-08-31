#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gates 26/27/29 — Simulador Novos engine parity harness (PORTAL-NEXT-08).

Compares the REAL, unmodified, DOM-coupled production engines (driven
live in a browser against the saved origin/main copy at
PORTAL-FI-DESIGN-LAB/PORTAL-NEXT-08/.source/simulador-novos-origin-main.html
-- loaded as a plain top-level page, which structurally guarantees the
FALLBACK-only code path since window.parent===window makes SB_LOADER
throw immediately, Gate 21: 0 backend calls) against V2's pure
re-derivation (assets/js/adapters/simulador-novos.adapter.js +
simulador-shared.adapter.js).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROD_URL = "http://localhost:8700/PORTAL-NEXT-08/.source/simulador-novos-origin-main.html"
ADAPTER_SHARED = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-shared.adapter.js"
ADAPTER_NOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/simulador-novos.adapter.js"

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
        adapter.add_script_tag(path=ADAPTER_NOVOS)

        # ---- Tradicional (Balão) ----
        trad_cases = [
            {"id": "trad_20pct_48x", "bem": 100000, "entrada": 20000, "prazo": 48, "baloes": []},
            {"id": "trad_10pct_min_exact", "bem": 100000, "entrada": 10000, "prazo": 12, "baloes": []},
            {"id": "trad_below_min_9pct", "bem": 100000, "entrada": 9000, "prazo": 12, "baloes": [], "expect_error": True},
            {"id": "trad_small_value", "bem": 15000, "entrada": 3000, "prazo": 24, "baloes": []},
            {"id": "trad_large_value", "bem": 950000, "entrada": 200000, "prazo": 30, "baloes": []},
            {"id": "trad_term_40", "bem": 80000, "entrada": 16000, "prazo": 40, "baloes": []},
            {"id": "trad_term_42", "bem": 80000, "entrada": 16000, "prazo": 42, "baloes": []},
            {"id": "trad_with_balloon", "bem": 100000, "entrada": 20000, "prazo": 48, "baloes": [{"mes": 24, "valor": 15000}]},
            {"id": "trad_balloon_over_limit", "bem": 100000, "entrada": 20000, "prazo": 48, "baloes": [{"mes": 24, "valor": 90000}], "expect_error": True},
            {"id": "trad_entry_equals_bem", "bem": 50000, "entrada": 50000, "prazo": 24, "baloes": [], "expect_error": True},
            {"id": "trad_zero_bem", "bem": 0, "entrada": 0, "prazo": 24, "baloes": [], "expect_empty": True},
        ]
        for c in trad_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('tBem').value = String(c.bem);
                    document.getElementById('tEntrada').value = String(c.entrada);
                    document.getElementById('tPrazo').value = String(c.prazo);
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
            prod_msg = prod.evaluate("document.getElementById('tMsg').innerHTML")
            prod_error = ("error" in prod.evaluate("document.getElementById('tMsg').className")) if prod_msg else False

            r = adapter.evaluate(
                "(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularTradicional({bem:c.bem, entrada:c.entrada, prazo:c.prazo, baloes:c.baloes})",
                c,
            )
            if c.get("expect_empty"):
                ok = r.get("empty") is True
            elif c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                ok = r.get("error") is None and not prod_error and close(prod_parcela, r.get("parcela"))
            results.append((f"Tradicional/{c['id']}", ok, prod_parcela, r.get("parcela")))

        # ---- Periódico (Semestral/Anual) ----
        period_cases = [
            {"id": "period_semestral_48x", "bem": 100000, "entrada": 20000, "prazo": 48, "tipo": "semestral"},
            {"id": "period_anual_48x", "bem": 100000, "entrada": 20000, "prazo": 48, "tipo": "anual"},
            {"id": "period_24x_min_entry", "bem": 60000, "entrada": 12000, "prazo": 24, "tipo": "semestral"},
            {"id": "period_below_min_entry", "bem": 60000, "entrada": 5000, "prazo": 24, "tipo": "semestral", "expect_error": True},
            {"id": "period_large_value", "bem": 900000, "entrada": 300000, "prazo": 36, "tipo": "anual"},
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
            prod_msg_cls = prod.evaluate("document.getElementById('pMsg').className")
            prod_error = "error" in (prod_msg_cls or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                ok = r.get("error") is None and not prod_error and close(prod_parcela, r.get("parcela"))
            results.append((f"Periodico/{c['id']}", ok, prod_parcela, r.get("parcela")))

        # ---- Parcela Única ----
        pu_cases = [
            {"id": "pu_exact_min_50pct", "bem": 100000, "entrada": 50000},
            {"id": "pu_above_min", "bem": 100000, "entrada": 70000},
            {"id": "pu_below_min_49pct", "bem": 100000, "entrada": 49000, "expect_error": True},
            {"id": "pu_large_value", "bem": 800000, "entrada": 500000},
        ]
        for c in pu_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('uBem').value = String(c.bem);
                    document.getElementById('uEntrada').value = String(c.entrada);
                    calcParcelaUnica(true);
                }""",
                c,
            )
            prod_parcela = brl_to_float(prod.evaluate("document.getElementById('uParcela').textContent"))
            prod_msg_cls = prod.evaluate("document.getElementById('uMsg').className")
            prod_error = "error" in (prod_msg_cls or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularParcelaUnica(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                ok = r.get("error") is None and not prod_error and close(prod_parcela, r.get("parcela"))
            results.append((f"ParcelaUnica/{c['id']}", ok, prod_parcela, r.get("parcela")))

        # ---- Linear ----
        lin_cases = [
            {"id": "lin_0pct_entry", "bem": 100000, "entrada": 0},
            {"id": "lin_20pct_entry", "bem": 100000, "entrada": 20000},
            {"id": "lin_50pct_entry", "bem": 100000, "entrada": 50000},
            {"id": "lin_entry_ge_bem", "bem": 50000, "entrada": 50000, "expect_error": True},
            {"id": "lin_large_value", "bem": 900000, "entrada": 180000},
        ]
        for c in lin_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('lValorBem').value = String(c.bem);
                    document.getElementById('lEntrada').value = String(c.entrada);
                    calcLinear(true);
                }""",
                c,
            )
            prod_msg_cls = prod.evaluate("document.getElementById('lMsg') ? document.getElementById('lMsg').className : ''")
            prod_error = "error" in (prod_msg_cls or "")
            prod_cards = prod.evaluate(
                "[...document.querySelectorAll('#lResultados .linear-payment')].map(e => e.textContent)"
            )
            prod_parcelas = [brl_to_float(x) for x in prod_cards]

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularLinear(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                adapter_parcelas = [it["parcela"] for it in r.get("itens", [])]
                ok = (
                    r.get("error") is None
                    and not prod_error
                    and len(prod_parcelas) == len(adapter_parcelas)
                    and all(close(a, b, 0.02) for a, b in zip(prod_parcelas, adapter_parcelas))
                )
            results.append((f"Linear/{c['id']}", ok, prod_parcelas, r.get("itens")))

        # ---- Descobridor de Taxa ----
        desc_cases = [
            {"id": "desc_typical", "financiado": 80000, "prazo": 48, "parcela": 2200},
            {"id": "desc_short_term", "financiado": 30000, "prazo": 12, "parcela": 2800},
            {"id": "desc_invalid_parcela_too_low", "financiado": 80000, "prazo": 48, "parcela": 100, "expect_error": True},
            {"id": "desc_prazo_boundary_60", "financiado": 50000, "prazo": 60, "parcela": 1200},
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
            prod_msg_cls = prod.evaluate("document.getElementById('dMsg').className")
            prod_error = "error" in (prod_msg_cls or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularDescobridor(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                adapter_taxa_pct = r.get("taxaNet") * 100 if r.get("taxaNet") is not None else None
                ok = r.get("error") is None and not prod_error and close(prod_taxa, adapter_taxa_pct, 0.02)
            results.append((f"Descobridor/{c['id']}", ok, prod_taxa, r.get("taxaNet")))

        # ---- Taxas Subsidiadas ----
        sub_cases = [
            {"id": "sub_exact_min_50pct", "bem": 100000, "entrada": 50000, "minVenda": 0},
            {"id": "sub_above_min", "bem": 100000, "entrada": 70000, "minVenda": 0},
            {"id": "sub_below_min_49pct", "bem": 100000, "entrada": 49000, "minVenda": 0, "expect_error": True},
            {"id": "sub_with_min_venda", "bem": 100000, "entrada": 60000, "minVenda": 90000},
        ]
        for c in sub_cases:
            prod.evaluate(
                """(c) => {
                    document.getElementById('sValorBem').value = String(c.bem);
                    document.getElementById('sEntrada').value = String(c.entrada);
                    document.getElementById('sMinVenda').value = c.minVenda ? String(c.minVenda) : '';
                    calcSubsidiadas(true);
                }""",
                c,
            )
            # Each .subsidiada-row renders 4 <b> values in order: prazo, parcela, rebateValor, valorFinalVenda.
            prod_rows_raw = prod.evaluate(
                "[...document.querySelectorAll('#sOpcoesGrid .subsidiada-row')].map(row => [...row.querySelectorAll('b')].map(b => b.textContent))"
            )
            prod_rows = []
            for cells in prod_rows_raw:
                if len(cells) >= 4:
                    prod_rows.append({
                        "prazo": int(re.sub(r"\D", "", cells[0])),
                        "parcela": brl_to_float(cells[1]),
                        "rebateValor": brl_to_float(cells[2]),
                        "valorFinalVenda": brl_to_float(cells[3]),
                    })
            # calcSubsidiadas() does NOT clear #sOpcoesGrid on error (real
            # production behavior -- the stale grid from a prior valid input
            # persists) -- error must be read from #sMsg, not grid emptiness.
            prod_error = "error" in (prod.evaluate("document.getElementById('sMsg').className") or "")

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularSubsidiadas(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None and prod_error
            else:
                adapter_rows = r.get("rows", [])
                ok = (
                    r.get("error") is None and not prod_error
                    and len(prod_rows) == len(adapter_rows) == 32
                    and all(
                        pr["prazo"] == ar["prazo"]
                        and close(pr["parcela"], ar["parcela"], 0.02)
                        and close(pr["rebateValor"], ar["rebateValor"], 0.02)
                        and close(pr["valorFinalVenda"], ar["valorFinalVenda"], 0.02)
                        for pr, ar in zip(
                            sorted(prod_rows, key=lambda x: (x["prazo"], x["parcela"])),
                            sorted(adapter_rows, key=lambda x: (x["prazo"], x["parcela"])),
                        )
                    )
                )
            results.append((f"Subsidiadas/{c['id']}", ok, len(prod_rows), len(r.get("rows", []))))

        # ---- Antecipação ----
        ant_cases = [
            {"id": "ant_typical", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-06-10", "tipo": "todo"},
            {"id": "ant_short_prazo", "prazo": 12, "parcela": 1500, "primeira": "2025-01-10", "data": "2025-03-10", "tipo": "todo"},
            {"id": "ant_prazo_invalid_61", "prazo": 61, "parcela": 1500, "primeira": "2025-01-10", "data": "2025-03-10", "tipo": "todo", "expect_error": True},
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
            prod_msg_cls = prod.evaluate("document.getElementById('aMsg').className")
            prod_error = "error" in (prod_msg_cls or "") and not prod_final

            r = adapter.evaluate(
                """(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularAntecipacao({
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

        # ---- Semestral Triton/Outlander ----
        stc_cases = [
            {"id": "stc_triton_hpe", "bem": 200000, "modelo": "TRITON HPE"},
            {"id": "stc_triton_katana", "bem": 250000, "modelo": "TRITON KATANA"},
            {"id": "stc_zero_bem", "bem": 0, "modelo": "TRITON HPE", "expect_error": True},
        ]
        for c in stc_cases:
            prod.evaluate(
                """async (c) => {
                    // renderStc() is private to its own IIFE; the only exposed
                    // entry point is window.carregarBaseSemestral(), which calls
                    // renderStc() only on its SECOND invocation (first call just
                    // sets the load-once guard and returns early since SB_LOADER
                    // is undefined standalone -- see source lines 3608-3612).
                    await window.carregarBaseSemestral();
                    const modelSel = document.getElementById('stcModelo');
                    if (modelSel) modelSel.value = c.modelo;
                    document.getElementById('stcBem').value = String(c.bem);
                    await window.carregarBaseSemestral();
                }""",
                c,
            )
            # stcParcelaPrincipal/stcTotal don't exist in current markup (setText()
            # no-ops safely) -- the parcela is only rendered per flow item now.
            prod_parcela = brl_to_float(prod.evaluate("(() => { const e = document.querySelector('#stcFluxo .stc-flow-item strong'); return e ? e.textContent : null; })()"))
            prod_final_venda = brl_to_float(prod.evaluate("document.getElementById('stcValorFinalVenda') ? document.getElementById('stcValorFinalVenda').textContent : null"))

            r = adapter.evaluate("(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularSemestralTriton(c)", c)
            if c.get("expect_error"):
                ok = r.get("error") is not None
            else:
                ok = r.get("error") is None and close(prod_parcela, r.get("parcela"), 0.02) and close(prod_final_venda, r.get("valorFinalVenda"), 0.02)
            results.append((f"SemestralTriton/{c['id']}", ok, prod_parcela, r.get("parcela")))

        prod.close()
        adapter.close()
        browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, prod_v, adapter_v in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  prod={prod_v!r} adapter={adapter_v!r}")
    print(f"\n=== Simulador Novos Parity: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
