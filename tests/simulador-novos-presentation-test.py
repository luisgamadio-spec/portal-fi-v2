#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORTAL-NEXT-08.2/08.3 — Deterministic presentation tests for Simulador
Novos' UAT Refinements 01/02 (mode nav, term grid, balloon input
width, balloon payment-structure story; product label, payment
schedules, Parcela Única rate, Coparticipado emphasis, Taxas
Subsidiadas comparison grid).

Exercises window.NX_SIMULADOR_NOVOS_PAGE.balloonScheduleSummary() and
.balancedColumns() directly (pure presentation functions) plus live
DOM checks against the real, frozen adapter outputs -- 0 hardcoded
expected schedule/value, everything is derived from the same engine
calls the page itself makes.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/simulador-novos"


def brl_to_float(s):
    if s is None:
        return None
    s = s.strip()
    if s in ("", "—", "-"):
        return None
    m = re.search(r"-?[\d.]+,\d+", s.replace("\xa0", " "))
    return float(m.group(0).replace(".", "").replace(",", ".")) if m else None


def close(a, b, eps=0.02):
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

        # ==================== balloonScheduleSummary ====================
        def summary(prazo, parcela, baloes):
            return page.evaluate(
                "(a) => NX_SIMULADOR_NOVOS_PAGE.balloonScheduleSummary(a.prazo, a.parcela, a.baloes)",
                {"prazo": prazo, "parcela": parcela, "baloes": baloes},
            )

        # No balloon: 0 specials, full regular count.
        s = summary(36, 2994.92, [])
        ok = s["regularCount"] == 36 and s["specials"] == []
        results.append(("no_balloon: regularCount=prazo, 0 specials", ok, s))

        # Single FINAL balloon (the human's own acceptance example):
        # 36x term, balloon at month 36 of R$20.000 -> 35x regular +
        # 1 special (parcela+balao), exactly.
        s = summary(36, 2994.92, [{"mes": 36, "valor": 20000}])
        ok = (
            s["regularCount"] == 35
            and len(s["specials"]) == 1
            and s["specials"][0]["mes"] == 36
            and abs(s["specials"][0]["total"] - 22994.92) < 0.005
            and abs(s["specials"][0]["total"] - (2994.92 + 20000)) < 1e-9  # exact engine-value arithmetic, no new rounding
        )
        results.append(("single_final_balloon: 35x + parcela 36 (human's exact example)", ok, s))

        # Single INTERMEDIATE balloon: 36x term, balloon at month 24 only.
        # regularCount must be 35 (36-1), NOT 35 displayed as if month 24
        # were additional on top of 36 regular payments.
        s = summary(36, 2994.92, [{"mes": 24, "valor": 15000}])
        ok = (
            s["regularCount"] == 35
            and len(s["specials"]) == 1
            and s["specials"][0]["mes"] == 24
            and abs(s["specials"][0]["total"] - (2994.92 + 15000)) < 1e-9
        )
        results.append(("single_intermediate_balloon: correct non-misleading count", ok, s))

        # Multiple balloons: 36x term, balloons at months 12 and 24.
        # regularCount = 36 - 2 unique months = 34. Both specials present,
        # sorted by month, each = parcela + that balloon's own valor.
        s = summary(36, 2994.92, [{"mes": 24, "valor": 15000}, {"mes": 12, "valor": 8000}])
        ok = (
            s["regularCount"] == 34
            and len(s["specials"]) == 2
            and [sp["mes"] for sp in s["specials"]] == [12, 24]  # sorted ascending
            and abs(s["specials"][0]["total"] - (2994.92 + 8000)) < 1e-9
            and abs(s["specials"][1]["total"] - (2994.92 + 15000)) < 1e-9
        )
        results.append(("multiple_balloons: correct unique-month count + per-month totals", ok, s))

        # Special-month total formula: exactly engine parcela + engine
        # balao value, no intermediate rounding introduced.
        s = summary(48, 1234.5678, [{"mes": 48, "valor": 9999.99}])
        ok = s["specials"][0]["total"] == 1234.5678 + 9999.99
        results.append(("special_month_math: exact parcela+balao, no new rounding", ok, s))

        # ==================== balancedColumns ====================
        def cols(width, itemW, n):
            return page.evaluate(
                "(a) => NX_SIMULADOR_NOVOS_PAGE.balancedColumns(a.w, a.i, a.n)",
                {"w": width, "i": itemW, "n": n},
            )

        # All 7 Tradicional terms fit comfortably -> single row.
        c = cols(700, 60, 7)
        results.append(("balancedColumns: 7 terms, ample width -> all fit (7 cols)", c == 7, c))

        # 7 terms, narrow container -> no isolated last row (remainder != 1).
        c = cols(308, 60, 7)
        rem = 7 % c if c else None
        ok = c is not None and c <= 7 and (rem == 0 or rem is None or rem >= 2)
        results.append((f"balancedColumns: 7 terms, narrow width -> no orphan (cols={c}, 7%%{c}={rem})", ok, c))

        # 8 terms (Linear/Campanha-sized), narrow -> also no orphan.
        c = cols(250, 60, 8)
        rem = 8 % c if c else None
        ok = c is not None and (rem == 0 or rem >= 2)
        results.append((f"balancedColumns: 8 terms, narrow width -> no orphan (cols={c}, 8%%{c}={rem})", ok, c))

        # 3 terms (Periodico) always fit in one row at any reasonable width.
        c = cols(300, 60, 3)
        results.append(("balancedColumns: 3 terms -> all fit (3 cols)", c == 3, c))

        # Single term -> 1 column (trivial, not an orphan case).
        c = cols(300, 60, 1)
        results.append(("balancedColumns: 1 term -> 1 column", c == 1, c))

        # ==================== Live DOM: currency width/duplication ====================
        page.click('.smModeBtn[data-mode="tradicional"]')
        page.wait_for_timeout(100)
        page.fill("#nBem", "150000")
        page.click("#nEntrada")  # blur nBem -- not mask-wired in Tradicional, expect raw digits unchanged
        page.click("#nAddBalao")
        page.wait_for_timeout(100)
        page.fill('#nBaloesList input[data-bfield="valor"]', "35000")
        page.click('#nBaloesList input[data-bfield="mes"]')  # blur the value field
        page.wait_for_timeout(100)
        val = page.eval_on_selector('#nBaloesList input[data-bfield="valor"]', "el => el.value")
        ok = val == "35.000,00" and "R$" not in val
        results.append((f"balloon_currency: single R$ prefix, no duplication (raw value={val!r})", ok, val))

        prefix_count = page.evaluate(
            "() => document.querySelectorAll('#nBaloesList .inputAffix .prefix').length"
        )
        results.append(("balloon_currency: exactly one .prefix element per balloon row", prefix_count == 1, prefix_count))

        # Field width check -- value field must be wider than the month field.
        month_w = page.eval_on_selector('#nBaloesList input[data-bfield="mes"]', "el => el.getBoundingClientRect().width")
        value_w = page.eval_on_selector('#nBaloesList input[data-bfield="valor"]', "el => el.getBoundingClientRect().width")
        results.append((f"balloon_width: value field wider than month field ({value_w:.0f}px > {month_w:.0f}px)", value_w > month_w, (month_w, value_w)))

        # ==================== Term-grid rendering counts ====================
        trad_buttons = page.evaluate("document.querySelectorAll('#nPrazo button').length")
        results.append(("term_grid: Tradicional renders exactly 7 term buttons", trad_buttons == 7, trad_buttons))

        page.click('.smModeBtn[data-mode="periodico"]')
        page.wait_for_timeout(100)
        period_buttons = page.evaluate("document.querySelectorAll('#nPrazo button').length")
        results.append(("term_grid: Periodico renders exactly 3 term buttons", period_buttons == 3, period_buttons))

        # No isolated single button in the last row of the rendered grid at
        # a narrow simulated width (structural check via --term-cols).
        page.click('.smModeBtn[data-mode="tradicional"]')
        page.wait_for_timeout(100)
        page.set_viewport_size({"width": 390, "height": 900})
        page.wait_for_timeout(150)
        term_cols = int(page.evaluate("getComputedStyle(document.getElementById('nPrazo')).getPropertyValue('--term-cols')") or 0)
        rem = 7 % term_cols if term_cols else None
        ok = term_cols > 0 and (rem == 0 or rem is None or rem >= 2)
        results.append((f"term_grid: 390px viewport, 7 terms -> no orphan row (cols={term_cols}, 7%%{term_cols}={rem})", ok, term_cols))

        # ==================== PORTAL-NEXT-08.3 Gate 28 ====================

        def click_mode(mode):
            page.click(f'.smModeBtn[data-mode="{mode}"]')
            page.wait_for_timeout(80)

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

        # ---- Label rename (Gate 2) ----
        mode_label = page.evaluate('document.querySelector(\'.smModeBtn[data-mode="campanha"]\').textContent')
        results.append(('label: mode button reads "Plano Coparticipado"', mode_label == "Plano Coparticipado", mode_label))
        page_text = page.evaluate("document.getElementById('nxContentOutlet').textContent")
        stale = re.search(r"Financiamento Campanha", page_text)
        results.append(("label: 0 visible 'Financiamento Campanha' anywhere on the page", stale is None, stale))

        # ---- Semestral schedule: 36x -> 6/12/18/24/30/36, derived from
        # the real adapter, not hardcoded here. ----
        click_mode("periodico")
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "20000")
        page.click('#nPrazo button[data-v="36"]')
        page.click("#nCalc")
        page.wait_for_timeout(100)
        expected_meses = page.evaluate(
            "() => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico({bem:100000, entrada:20000, prazo:36, tipo:'semestral'}).meses"
        )
        ui_markers = page.evaluate("[...document.querySelectorAll('.smScheduleMarker')].map(e => Number(e.textContent))")
        results.append((f"schedule: Semestral 36x markers match engine's own r.meses ({ui_markers} == {expected_meses})", ui_markers == expected_meses, (ui_markers, expected_meses)))
        prazo_total_txt = page.evaluate("document.querySelector('.smScheduleItem strong') ? document.querySelector('.smScheduleItem strong').textContent : null")
        results.append(("schedule: Semestral 36x shows 'Prazo total 36 meses'", prazo_total_txt == "36 meses", prazo_total_txt))

        # ---- Other Semestral term (24x) -- must NOT reuse the 36x sequence. ----
        page.click('#nPrazo button[data-v="24"]')
        page.click("#nCalc")
        page.wait_for_timeout(100)
        expected_24 = page.evaluate(
            "() => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico({bem:100000, entrada:20000, prazo:24, tipo:'semestral'}).meses"
        )
        ui_markers_24 = page.evaluate("[...document.querySelectorAll('.smScheduleMarker')].map(e => Number(e.textContent))")
        results.append((f"schedule: Semestral 24x != Semestral 36x sequence, matches engine ({ui_markers_24} == {expected_24})", ui_markers_24 == expected_24 and ui_markers_24 != ui_markers, (ui_markers_24, expected_24)))

        # ---- Anual schedule ----
        page.click('#nTipo button[data-v="anual"]')
        page.click('#nPrazo button[data-v="36"]')
        page.click("#nCalc")
        page.wait_for_timeout(100)
        expected_anual = page.evaluate(
            "() => NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico({bem:100000, entrada:20000, prazo:36, tipo:'anual'}).meses"
        )
        ui_markers_anual = page.evaluate("[...document.querySelectorAll('.smScheduleMarker')].map(e => Number(e.textContent))")
        results.append((f"schedule: Anual 36x matches engine ({ui_markers_anual} == {expected_anual})", ui_markers_anual == expected_anual, (ui_markers_anual, expected_anual)))

        # ---- Parcela Única schedule: single marker = r.plano.prazo ----
        click_mode("parcelaunica")
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "50000")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        pu_r = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularParcelaUnica({bem:100000, entrada:50000})")
        ui_markers_pu = page.evaluate("[...document.querySelectorAll('.smScheduleMarker')].map(e => Number(e.textContent))")
        results.append((f"schedule: Parcela Única single marker = plano.prazo ({ui_markers_pu} == [{pu_r['plano']['prazo']}])", ui_markers_pu == [pu_r["plano"]["prazo"]], (ui_markers_pu, pu_r["plano"]["prazo"])))

        # ---- Parcela Única: coefficient hidden, authoritative rate visible ----
        result_html = page.evaluate("document.getElementById('smResultRegion').innerHTML")
        results.append(("parcela_unica: no visible 'Coeficiente' label", "Coeficiente" not in result_html, None))
        taxa_field = result_field("Taxa da tabela")
        expected_taxa_pct = page.evaluate("(t) => t*100", pu_r["taxa"])
        ok = taxa_field is not None and abs(float(taxa_field.replace("%", "").replace(",", ".")) - expected_taxa_pct) < 0.01
        results.append((f"parcela_unica: 'Taxa da tabela' shows the engine's own r.taxa ({taxa_field!r} ~= {expected_taxa_pct:.2f}%)", ok, taxa_field))
        results.append(("parcela_unica: rate has no unproven period suffix (no 'a.m.'/'a.a.')", "a.m." not in result_html and "a.a." not in result_html, None))

        # ---- Triton/Outlander schedule: uses the shared constant, not
        # a copy of the generic Semestral/Anual sequence. ----
        click_mode("triton")
        page.fill("#nBem", "200000")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        expected_triton = page.evaluate("() => NX_SIMULADOR_SHARED.SEMESTRAL_TRITON_MESES")
        ui_markers_triton = page.evaluate("[...document.querySelectorAll('.smScheduleMarker')].map(e => Number(e.textContent))")
        results.append((f"schedule: Triton markers match S.SEMESTRAL_TRITON_MESES ({ui_markers_triton} == {expected_triton})", ui_markers_triton == expected_triton, (ui_markers_triton, expected_triton)))

        # ---- Coparticipado: Rebate Brabus + Valor Final de Venda emphasized ----
        click_mode("campanha")
        page.select_option("#nModelo", "ECLIPSE CROSS HPE-S S-AWC")
        page.fill("#nSale", "200000")
        page.fill("#nEntry", "120000")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        camp_r = page.evaluate(
            "() => NX_CAMPANHA_ADAPTER.compute({model:'ECLIPSE CROSS HPE-S S-AWC', saleValue:200000, entryValue:120000})"
        )
        rebate_in_emphasis = page.evaluate("!!document.querySelector('.smEmphasisPair .smEmphasisCard:first-child')")
        venda_in_emphasis = page.evaluate("!!document.querySelector('.smEmphasisCardPrimary')")
        rebate_txt = page.evaluate("document.querySelector('.smEmphasisPair .smEmphasisCard:first-child .smEmphasisValue') ? document.querySelector('.smEmphasisPair .smEmphasisCard:first-child .smEmphasisValue').textContent : null")
        venda_txt = page.evaluate("document.querySelector('.smEmphasisCardPrimary .smEmphasisValue') ? document.querySelector('.smEmphasisCardPrimary .smEmphasisValue').textContent : null")
        results.append(("coparticipado: Rebate Brabus rendered in the emphasis block", rebate_in_emphasis, rebate_txt))
        results.append(("coparticipado: Valor Final de Venda rendered as the PRIMARY emphasis card", venda_in_emphasis, venda_txt))

        # ---- Taxas Subsidiadas: card count + data parity (no new calc) ----
        click_mode("subsidiadas")
        page.fill("#nBem", "100000")
        page.fill("#nEntrada", "60000")
        page.click("#nCalc")
        page.wait_for_timeout(100)
        sub_r = page.evaluate("() => NX_SIMULADOR_NOVOS_ADAPTER.calcularSubsidiadas({bem:100000, entrada:60000, minVenda:0})")
        card_count = page.evaluate("document.querySelectorAll('.smSubsidiadaCard').length")
        results.append((f"subsidiadas: card count == r.rows.length ({card_count} == {len(sub_r['rows'])})", card_count == len(sub_r["rows"]) == 32, card_count))
        # Data parity: every card's Parcela value matches its own engine row (matched by prazo+taxa).
        card_data = page.evaluate(
            """() => [...document.querySelectorAll('.smSubsidiadaCard')].map(c => ({
                prazo: Number(c.querySelector('.smSubsidiadaCardPrazo').textContent.replace('x', '')),
                taxa: c.querySelector('.smSubsidiadaCardTaxa').textContent,
                parcela: c.querySelectorAll('.smSubsidiadaCardRow strong')[0].textContent
            }))"""
        )
        mismatches = 0
        for row in sub_r["rows"]:
            match = next((c for c in card_data if c["prazo"] == row["prazo"] and abs(float(c["taxa"].replace("%", "").replace(",", ".")) - row["taxa"] * 100) < 0.02), None)
            if not match or not close(brl_to_float(match["parcela"]), row["parcela"], 0.02):
                mismatches += 1
        results.append((f"subsidiadas: data parity, 0 mismatches across 32 cards vs frozen engine rows (mismatches={mismatches})", mismatches == 0, mismatches))
        # No duplicated values from the renderer migration (e.g. a stray
        # repeated Parcela line inside a single card).
        dup_check = page.evaluate(
            """() => {
                const cards = [...document.querySelectorAll('.smSubsidiadaCard')];
                return cards.every(c => c.querySelectorAll('.smSubsidiadaCardRow').length === 3);
            }"""
        )
        results.append(("subsidiadas: exactly 3 metric rows per card (Parcela/Rebate/Venda), 0 duplication", dup_check, None))

        print("console/page errors:", errors)
        page.close()
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, val in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Novos Presentation Tests: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) and not errors else "FAIL")
    sys.exit(0 if passed == len(results) and not errors else 1)


if __name__ == "__main__":
    main()
