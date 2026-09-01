#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORTAL-NEXT-08.2 — Deterministic presentation tests for Simulador
Novos' UAT Refinement 01 (mode nav, term grid, balloon input width,
balloon payment-structure story).

Exercises window.NX_SIMULADOR_NOVOS_PAGE.balloonScheduleSummary() and
.balancedColumns() directly (pure presentation functions, PORTAL-
NEXT-08.2 Change 4/2) plus live DOM checks for the currency-
duplication fix and term-grid rendering.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/simulador-novos"


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
