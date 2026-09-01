#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORTAL-NEXT-08.4 — Deterministic presentation tests for Simulador
Seminovos' UX alignment with Novos' approved 08.2/08.3 patterns
(Gates 9-20, 32-34).

Exercises window.NX_SIMULADOR_SEMINOVOS_PAGE.balloonScheduleSummary()
and .balancedColumns() directly (pure presentation functions, ported
independently -- Seminovos file untouched by Novos, and vice versa)
plus live DOM checks against the real, frozen SEMINOVOS adapter
outputs -- 0 hardcoded expected value, everything derived from the
same engine calls the page itself makes.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/simulador-seminovos"


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

        # ==================== Gate 32: balloonScheduleSummary ====================
        def summary(prazo, parcela, baloes):
            return page.evaluate(
                "(a) => NX_SIMULADOR_SEMINOVOS_PAGE.balloonScheduleSummary(a.prazo, a.parcela, a.baloes)",
                {"prazo": prazo, "parcela": parcela, "baloes": baloes},
            )

        s = summary(36, 2500.00, [])
        ok = s["regularCount"] == 36 and s["specials"] == []
        results.append(("no_balloon: regularCount=prazo, 0 specials", ok, s))

        # Single final balloon.
        s = summary(36, 2500.00, [{"mes": 36, "valor": 18000}])
        ok = (
            s["regularCount"] == 35
            and len(s["specials"]) == 1
            and s["specials"][0]["mes"] == 36
            and abs(s["specials"][0]["total"] - (2500.00 + 18000)) < 1e-9
        )
        results.append(("single_final_balloon: 35x regular + parcela 36 special", ok, s))

        # Single intermediate balloon.
        s = summary(36, 2500.00, [{"mes": 20, "valor": 12000}])
        ok = (
            s["regularCount"] == 35
            and len(s["specials"]) == 1
            and s["specials"][0]["mes"] == 20
            and abs(s["specials"][0]["total"] - (2500.00 + 12000)) < 1e-9
        )
        results.append(("single_intermediate_balloon: correct non-misleading count", ok, s))

        # Multiple balloons.
        s = summary(40, 2500.00, [{"mes": 30, "valor": 15000}, {"mes": 15, "valor": 8000}])
        ok = (
            s["regularCount"] == 38
            and len(s["specials"]) == 2
            and [sp["mes"] for sp in s["specials"]] == [15, 30]
            and abs(s["specials"][0]["total"] - (2500.00 + 8000)) < 1e-9
            and abs(s["specials"][1]["total"] - (2500.00 + 15000)) < 1e-9
        )
        results.append(("multiple_balloons: correct unique-month count + per-month totals", ok, s))

        # ==================== balancedColumns (7 Tradicional terms) ====================
        def cols(width, itemW, n):
            return page.evaluate(
                "(a) => NX_SIMULADOR_SEMINOVOS_PAGE.balancedColumns(a.w, a.i, a.n)",
                {"w": width, "i": itemW, "n": n},
            )

        c = cols(700, 60, 7)
        results.append(("balancedColumns: 7 terms, ample width -> all fit (7 cols)", c == 7, c))
        c = cols(308, 60, 7)
        rem = 7 % c if c else None
        ok = c is not None and c <= 7 and (rem == 0 or rem is None or rem >= 2)
        results.append((f"balancedColumns: 7 terms, narrow width -> no orphan (cols={c}, 7%%{c}={rem})", ok, c))

        # ==================== Gate 34: navigation scope ====================
        mode_options = page.evaluate("[...document.querySelectorAll('.smModeBtn')].map(o => o.textContent)")
        results.append(("nav: exactly 5 modes (2 Financiamento + 3 Ferramentas)", len(mode_options) == 5, mode_options))
        results.append(("nav: Tradicional (Balão) present", "Tradicional (Balão)" in mode_options))
        results.append(("nav: Linear present (renamed from 'Financiamento Seminovos')", "Linear" in mode_options))
        results.append(("nav: 'Financiamento Seminovos' old label absent", "Financiamento Seminovos" not in mode_options))
        for dead in ["Semestral / Anual", "Financiamento Campanha", "Plano Coparticipado", "Semestral Triton", "Financiamento Linear", "Taxas Subsidiadas"]:
            results.append((f"nav: unreachable '{dead}' not exposed", dead not in mode_options))

        # ==================== Gate 11/12: money input / balloon width ====================
        page.click('.smModeBtn[data-mode="tradicional"]')
        page.wait_for_timeout(100)
        page.fill("#sBem", "150000")
        page.click("#sAddBalao")
        page.wait_for_timeout(100)
        page.fill('#sBaloesList input[data-bfield="valor"]', "35000")
        page.click('#sBaloesList input[data-bfield="mes"]')  # blur value field
        page.wait_for_timeout(100)
        val = page.eval_on_selector('#sBaloesList input[data-bfield="valor"]', "el => el.value")
        ok = val == "35.000,00" and "R$" not in val
        results.append((f"balloon_currency: single R$ prefix, no duplication (raw value={val!r})", ok, val))
        prefix_count = page.evaluate("() => document.querySelectorAll('#sBaloesList .inputAffix .prefix').length")
        results.append(("balloon_currency: exactly one .prefix element per balloon row", prefix_count == 1, prefix_count))
        month_w = page.eval_on_selector('#sBaloesList input[data-bfield="mes"]', "el => el.getBoundingClientRect().width")
        value_w = page.eval_on_selector('#sBaloesList input[data-bfield="valor"]', "el => el.getBoundingClientRect().width")
        results.append((f"balloon_width: value field wider than month field ({value_w:.0f}px > {month_w:.0f}px)", value_w > month_w, (month_w, value_w)))

        # ==================== Gate 10: term grid ====================
        trad_buttons = page.evaluate("document.querySelectorAll('#sPrazo button').length")
        results.append(("term_grid: Tradicional renders exactly 7 term buttons", trad_buttons == 7, trad_buttons))
        page.set_viewport_size({"width": 390, "height": 900})
        page.wait_for_timeout(150)
        term_cols = int(page.evaluate("getComputedStyle(document.getElementById('sPrazo')).getPropertyValue('--term-cols')") or 0)
        rem = 7 % term_cols if term_cols else None
        ok = term_cols > 0 and (rem == 0 or rem is None or rem >= 2)
        results.append((f"term_grid: 390px viewport, 7 terms -> no orphan row (cols={term_cols}, 7%%{term_cols}={rem})", ok, term_cols))
        page.set_viewport_size({"width": 1366, "height": 900})
        page.wait_for_timeout(100)

        # ==================== Gate 15: vehicle year preserved ====================
        year_visible = page.evaluate("!!document.getElementById('sAno')")
        results.append(("tradicional: vehicle year field (sAno) present", year_visible))

        # ==================== Gate 16/33: Linear -- 50x + result hierarchy ====================
        page.click('.smModeBtn[data-mode="ratetable"]')
        page.wait_for_timeout(100)
        page.fill("#sAnoRT", "2020")
        page.fill("#sValorRT", "80000")
        page.fill("#sEntradaRT", "16000")
        page.click("#sCalc")
        page.wait_for_timeout(150)
        terms_rendered = page.evaluate("[...document.querySelectorAll('.smTermCard .term')].map(e => e.textContent)")
        results.append(("ratetable: 50x present among rendered terms", "50x" in terms_rendered, terms_rendered))
        adapter_r = page.evaluate(
            "() => NX_SIMULADOR_SEMINOVOS_ADAPTER.calcularLinearRateTable({ano:2020, valor:80000, entrada:16000})"
        )
        ui_payments = [brl_to_float(x) for x in page.evaluate("[...document.querySelectorAll('.smTermCard .payment')].map(e => e.textContent)")]
        adapter_payments = [t["payment"] for t in adapter_r["terms"] if t["payment"] is not None]
        parity_ok = len(ui_payments) == len(adapter_payments) == 9 and all(close(a, b) for a, b in zip(ui_payments, adapter_payments))
        results.append(("ratetable: all 9 terms match frozen engine exactly (incl. 50x)", parity_ok, list(zip(ui_payments, adapter_payments))))
        no_coef = "Coeficiente" not in page.evaluate("document.getElementById('smResultRegion').textContent")
        results.append(("ratetable: no internal 'Coeficiente' exposed (rate shown instead)", no_coef))

        print("console/page errors:", errors)
        page.close()
        browser.close()

    passed = sum(1 for _, ok, *_ in results if ok)
    for r in results:
        name, ok = r[0], r[1]
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Simulador Seminovos Presentation Tests: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) and not errors else "FAIL")
    sys.exit(0 if passed == len(results) and not errors else 1)


if __name__ == "__main__":
    main()
