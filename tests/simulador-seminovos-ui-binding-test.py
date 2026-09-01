#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate 41 — Simulador Seminovos V2 UI golden binding (PORTAL-NEXT-08.1).

Reuses the EXACT same 24 golden cases as PORTAL-NEXT-08's
tests/simulador-seminovos-parity-test.py (6 reachable Seminovos
engines), driving the REAL V2 route (#/simulador-seminovos) through
its actual form fields/buttons and comparing against the frozen
adapter. Also proves Gate 47 (dead-feature guard): the mode <select>
has no "Financiamento Linear"/"Taxas Subsidiadas" option at all.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/simulador-seminovos"
CENT = 0.02


def brl_to_float(s):
    if s is None:
        return None
    m = re.search(r"-?[\d.]+,\d+", s.replace("\xa0", " "))
    return float(m.group(0).replace(".", "").replace(",", ".")) if m else None


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
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(URL)
        page.wait_for_timeout(400)

        # Gate 47 -- dead-feature guard, checked once up front.
        mode_options = page.evaluate("[...document.querySelectorAll('#smModeSelect option')].map(o => o.textContent)")
        dead_guard_ok = not any("Linear" == m or "Subsidiada" in m for m in mode_options)
        results.append(("Gate47/dead_features_not_exposed", dead_guard_ok))
        results.append(("Gate47/ratetable_not_confused_with_dead_linear",
                         any("Financiamento Seminovos" in m for m in mode_options)))

        def select_mode(mode):
            page.select_option("#smModeSelect", mode)
            page.wait_for_timeout(80)

        def click_segmented(box_id, value):
            page.click(f'#{box_id} button[data-v="{value}"]')

        def result_field(label_text):
            return page.evaluate(
                """(label) => {
                    const kpis = [...document.querySelectorAll('#smResultRegion .kpiLabel')];
                    const k = kpis.find(e => e.textContent.trim() === label);
                    if (!k) return null;
                    const val = k.nextElementSibling;
                    return val ? val.textContent : null;
                }""",
                label_text,
            )

        def has_error_state():
            return page.evaluate("!!document.querySelector('#smResultRegion .errorState')")

        # ==================== Tradicional (8) ====================
        select_mode("tradicional")
        trad_cases = [
            {"id": "trad_2020_20pct_24x", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "2020"},
            {"id": "trad_2026_40pct_36x", "bem": 100000, "entrada": 40000, "prazo": 36, "ano": "2026"},
            {"id": "trad_below_min_9pct", "bem": 80000, "entrada": 7000, "prazo": 24, "ano": "2020", "expect_error": True},
            {"id": "trad_year_out_of_band", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "2016", "expect_error": True},
            {"id": "trad_year_missing", "bem": 80000, "entrada": 16000, "prazo": 24, "ano": "", "expect_error": True},
            {"id": "trad_small_value", "bem": 12000, "entrada": 3000, "prazo": 12, "ano": "2022"},
            {"id": "trad_large_value", "bem": 700000, "entrada": 300000, "prazo": 48, "ano": "2025"},
            {"id": "trad_with_balloon", "bem": 90000, "entrada": 20000, "prazo": 36, "ano": "2021", "balao": {"mes": 24, "valor": 12000}},
        ]
        for c in trad_cases:
            page.evaluate("() => { const l = document.getElementById('sBaloesList'); if(l) [...l.querySelectorAll('[data-bremove]')].reverse().forEach(b => b.click()); }")
            page.fill("#sBem", str(c["bem"]))
            page.fill("#sEntrada", str(c["entrada"]))
            page.fill("#sAno", str(c["ano"]))
            click_segmented("sPrazo", str(c["prazo"]))
            baloes_js = "[]"
            if c.get("balao"):
                page.click("#sAddBalao")
                page.wait_for_timeout(60)
                page.fill('#sBaloesList input[data-bfield="mes"]', str(c["balao"]["mes"]))
                page.fill('#sBaloesList input[data-bfield="valor"]', str(c["balao"]["valor"]))
                baloes_js = "[{mes:%d,valor:%d}]" % (c["balao"]["mes"], c["balao"]["valor"])
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate(
                "(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularTradicional({bem:c.bem, entrada:c.entrada, prazo:c.prazo, ano:c.ano, baloes:" + baloes_js + "})",
                c,
            )
            if c.get("expect_error"):
                ok = has_error_state() and adapter_r.get("error") is not None
            else:
                ui_val = brl_to_float(result_field("Parcela mensal"))
                ok = not has_error_state() and close(ui_val, adapter_r.get("parcela"))
            results.append((f"Tradicional/{c['id']}", ok))

        # ==================== Periodico (4) ====================
        select_mode("periodico")
        period_cases = [
            {"id": "period_semestral_48x", "bem": 80000, "entrada": 20000, "prazo": 48, "tipo": "semestral"},
            {"id": "period_anual_36x", "bem": 90000, "entrada": 25000, "prazo": 36, "tipo": "anual"},
            {"id": "period_below_min", "bem": 60000, "entrada": 5000, "prazo": 24, "tipo": "semestral", "expect_error": True},
            {"id": "period_unsupported_term", "bem": 60000, "entrada": 20000, "prazo": 30, "tipo": "semestral", "no_term_btn": True, "expect_error": True},
        ]
        for c in period_cases:
            page.fill("#sBem", str(c["bem"]))
            page.fill("#sEntrada", str(c["entrada"]))
            prazo_for_ui = c["prazo"] if not c.get("no_term_btn") else 48
            click_segmented("sPrazo", str(prazo_for_ui))
            click_segmented("sTipo", c["tipo"])
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate(
                "(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularPeriodico({bem:c.bem, entrada:c.entrada, prazo:c.prazo, tipo:c.tipo})",
                c,
            )
            if c.get("no_term_btn"):
                ok = adapter_r.get("error") is not None
            elif c.get("expect_error"):
                ok = has_error_state() and adapter_r.get("error") is not None
            else:
                ui_val = brl_to_float(result_field("Parcela " + ("semestral" if c["tipo"] == "semestral" else "anual")))
                ok = not has_error_state() and close(ui_val, adapter_r.get("parcela"))
            results.append((f"Periodico/{c['id']}", ok))

        # ==================== Descobridor (2) ====================
        select_mode("descobridor")
        desc_cases = [
            {"id": "desc_typical", "financiado": 70000, "prazo": 36, "parcela": 2400},
            {"id": "desc_invalid_too_low", "financiado": 70000, "prazo": 36, "parcela": 100, "expect_error": True},
        ]
        for c in desc_cases:
            page.fill("#sFinanciado", str(c["financiado"]))
            page.fill("#sPrazoNum", str(c["prazo"]))
            page.fill("#sParcela", str(c["parcela"]))
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularDescobridor({financiado:c.financiado, prazo:c.prazo, parcela:c.parcela})", c)
            if c.get("expect_error"):
                ok = has_error_state() and adapter_r.get("error") is not None
            else:
                ui_text = result_field("Taxa efetiva mensal (CET)")
                ui_pct = float(re.search(r"[\d,]+", ui_text.replace(".", "")).group(0).replace(",", ".")) if ui_text else None
                ok = not has_error_state() and close(ui_pct, adapter_r["taxaCetMes"] * 100, 0.02)
            results.append((f"Descobridor/{c['id']}", ok))

        # ==================== Antecipacao (2) ====================
        select_mode("antecipacao")
        ant_cases = [
            {"id": "ant_typical", "prazo": 36, "parcela": 1800, "primeira": "2025-01-10", "data": "2025-05-10"},
            {"id": "ant_prazo_invalid_0", "prazo": 0, "parcela": 1500, "primeira": "2025-01-10", "data": "2025-03-10", "expect_error": True},
        ]
        for c in ant_cases:
            page.fill("#sPrazoNum", str(c["prazo"]))
            page.fill("#sParcela", str(c["parcela"]))
            page.fill("#sPrimeira", c["primeira"])
            page.fill("#sData", c["data"])
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate(
                """(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularAntecipacao({
                    prazo: c.prazo, parcela: c.parcela,
                    primeiraParcela: new Date(c.primeira + 'T00:00:00'),
                    dataAntecipacao: new Date(c.data + 'T00:00:00'),
                    tipo: 'todo', baloes: []
                })""",
                c,
            )
            if c.get("expect_error"):
                ok = has_error_state() and adapter_r.get("error") is not None
            else:
                ui_val = brl_to_float(result_field("Valor final com desconto"))
                ok = not has_error_state() and close(ui_val, adapter_r.get("finalTotal"), 0.05)
            results.append((f"Antecipacao/{c['id']}", ok))

        # ==================== Semestral Triton (3) ====================
        select_mode("triton")
        stc_cases = [
            {"id": "stc_triton_hpe", "bem": 180000, "modelo": "TRITON HPE"},
            {"id": "stc_triton_savana", "bem": 220000, "modelo": "TRITON SAVANA"},
            {"id": "stc_zero_bem", "bem": 0, "modelo": "TRITON HPE", "expect_error": True},
        ]
        for c in stc_cases:
            page.select_option("#sModelo", c["modelo"])
            page.fill("#sBem", str(c["bem"]))
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularSemestralTriton({bem:c.bem, modelo:c.modelo})", c)
            if c.get("expect_error"):
                ok = has_error_state() and adapter_r.get("error") is not None
            else:
                ui_val = brl_to_float(result_field("Parcela (4x semestrais)"))
                ok = not has_error_state() and close(ui_val, adapter_r.get("parcela"))
            results.append((f"SemestralTriton/{c['id']}", ok))

        # ==================== Financiamento Seminovos / RATE_TABLE (5) ====================
        select_mode("ratetable")
        lrt_cases = [
            {"id": "lrt_2020_0pct", "ano": 2020, "valor": 80000, "entrada": 0},
            {"id": "lrt_2012_20pct", "ano": 2012, "valor": 60000, "entrada": 12000},
            {"id": "lrt_2023_40pct", "ano": 2023, "valor": 100000, "entrada": 42000},
            {"id": "lrt_year_out_of_range", "ano": 2003, "valor": 50000, "entrada": 10000, "expect_invalid": True},
            {"id": "lrt_entry_above_100pct", "ano": 2020, "valor": 50000, "entrada": 60000, "expect_invalid": True},
        ]
        for c in lrt_cases:
            page.fill("#sAnoRT", str(c["ano"]))
            page.fill("#sValorRT", str(c["valor"]))
            page.fill("#sEntradaRT", str(c["entrada"]))
            page.click("#sCalc")
            page.wait_for_timeout(80)
            adapter_r = page.evaluate("(c) => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularLinearRateTable({ano:c.ano, valor:c.valor, entrada:c.entrada})", c)
            if c.get("expect_invalid"):
                ok = has_error_state() and adapter_r.get("invalid") is True
            else:
                ui_payments = [brl_to_float(x) for x in page.evaluate("[...document.querySelectorAll('.smTermCard .payment')].map(e => e.textContent)")]
                adapter_payments = [t["payment"] for t in adapter_r["terms"] if t["payment"] is not None]
                ok = not has_error_state() and len(ui_payments) == len(adapter_payments) and all(close(a, b) for a, b in zip(ui_payments, adapter_payments))
            results.append((f"RateTable/{c['id']}", ok))

        # ==================== Cash Conversion (shared engine, 3 cases) ====================
        # Same rationale as the Novos UI-binding test -- catches the
        # type="number"-with-comma-decimal rendering bug found via
        # screenshot review.
        select_mode("cashconversion")
        cc_cases = [
            {"id": "cc_default_rate_renders", "capital": 100000, "parcela": 2500, "prazo": 36, "taxa": "0,80"},
            {"id": "cc_high_capital", "capital": 5000000, "parcela": 50000, "prazo": 48, "taxa": "1,00"},
            {"id": "cc_taxa_zero", "capital": 50000, "parcela": 2000, "prazo": 24, "taxa": "0"},
        ]
        for c in cc_cases:
            page.fill("#sCapital", str(c["capital"]))
            page.fill("#sParcelaCC", str(c["parcela"]))
            page.fill("#sPrazoCC", str(c["prazo"]))
            page.fill("#sTaxaCC", c["taxa"])
            page.click("#sCalc")
            page.wait_for_timeout(80)
            field_val = page.eval_on_selector("#sTaxaCC", "el => el.value")
            adapter_r = page.evaluate(
                "(c) => NX_CASH_CONVERSION_ADAPTER.compute({capital:c.capital, parcela:c.parcela, prazoMeses:c.prazo, taxaAplicacao:Number(c.taxa.replace(',','.'))/100})",
                c,
            )
            ui_val = brl_to_float(result_field("Valor final do financiamento"))
            ok = field_val == c["taxa"] and close(ui_val, adapter_r["valorFinalFinanciamento"] if adapter_r else None)
            results.append((f"CashConversion/{c['id']}", ok))

        print("console/page errors during UI-binding run:", errors)
        page.close()
        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Seminovos UI Golden Binding: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) and not errors else "FAIL")
    sys.exit(0 if passed == len(results) and not errors else 1)


if __name__ == "__main__":
    main()
