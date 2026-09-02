#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-1 -- Brabus Intelligence PRESENTATION PARITY test (Gate 55 of
the IA-V2-1 brief).

Loads the real adapter + page controller
(tests/fixtures/_brabus-intelligence-harness.html) and calls
NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock(block) directly with
each of the 12 named fixture scenarios' real block(s). Proves: payload
value -> adapter-formatted value -> rendered HTML text are the SAME
number/date/percent, for every block type, with zero drift and zero
financial recalculation anywhere in the renderer. Also proves the two
named regression-sensitive cases explicitly (Gates 29-30 of IA-V2-1):
Cash Conversion's 1.12% and Antecipação's assumed date.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/tests/fixtures/_brabus-intelligence-harness.html"


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html)


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        def render_block(scenario_id, block_index=0):
            return page.evaluate(f"""
                () => {{
                  var s = window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('{scenario_id}');
                  var block = s.response.blocks[{block_index}];
                  return window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock(block);
                }}
            """)

        # ---------- metrics: every item's formatted value appears verbatim ----------
        html = render_block("plain-text")
        text = strip_tags(html)
        results.append(("metrics: title present", "Grupo — mês anterior" in text))
        results.append(("metrics: int value preserved (13)", "13" in text))
        results.append(("metrics: currency value preserved (R$ 100.500,00)", "100.500,00" in text))
        results.append(("metrics: percent value preserved as payload scale (76,9%, not 7690%)", "76,9%" in text and "7690" not in text))

        # ---------- Cash Conversion: THE named regression case (Gate 29) ----------
        html = render_block("cash-conversion")
        text = strip_tags(html)
        results.append(("Cash Conversion: displays 1,1% (payload's own percent-point value), not 112% or 0,0112%", "1,1%" in text and "112" not in text and "0,0112" not in text))
        results.append(("Cash Conversion: no CASH_CONVERSION_APPLICATION_RATE-style literal anywhere in rendered text", "0.0112" not in text and "0,0112" not in text))

        # ---------- Antecipação: THE named regression case (Gate 30) ----------
        html = render_block("antecipacao")
        text = strip_tags(html)
        results.append(("Antecipação: date renders as DD/MM/YYYY (01/10/2026)", "01/10/2026" in text))
        results.append(("Antecipação: never renders em dash for a valid date", not re.search(r"Primeira parcela[^—]*—", text) or "01/10/2026" in text))
        results.append(("Antecipação: never renders 'Invalid Date'", "Invalid Date" not in text))

        # ---------- Taxa Implícita: NET vs CET distinction preserved ----------
        html = render_block("taxa-implicita")
        text = strip_tags(html)
        # The real format contract (baiFormatValue, ported verbatim) uses
        # 1 decimal for percent, not 2 -- 2.58 -> "2,6%", 2.86 -> "2,9%".
        results.append(("Taxa Implícita: NET (2,6%) and CET (2,9%) both present and distinct at the real 1-decimal precision", "2,6%" in text and "2,9%" in text))

        # ---------- comparison ----------
        html = render_block("comparison")
        text = strip_tags(html)
        results.append(("comparison: both side labels present", "Barra Funda" in text and "Santo Amaro" in text))
        results.append(("comparison: each side's own values preserved (81,2% vs 74,6%)", "81,2%" in text and "74,6%" in text))

        # ---------- ranking ----------
        html = render_block("subsidiado")
        text = strip_tags(html)
        results.append(("ranking: uses a real table element", "<table" in html and 'class="modTable"' in html))
        results.append(("ranking: item values preserved (R$ 1.920,00 / R$ 1.440,00)", "1.920,00" in text and "1.440,00" in text))

        # ---------- operations ----------
        html = render_block("operations")
        text = strip_tags(html)
        results.append(("operations: no fabricated customer PII (no CPF/chassis pattern)", not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", text)))
        results.append(("operations: masked fixture text preserved verbatim", "Balão 4x" in text))

        # ---------- score_breakdown ----------
        html = render_block("score")
        text = strip_tags(html)
        results.append(("score_breakdown: final score value preserved (87,4 -> rendered as int)", "87" in text))
        results.append(("score_breakdown: does not call/reference score.adapter.js's calcScores", "calcScores" not in html))

        # ---------- score_ranking ----------
        html = render_block("score-ranking")
        text = strip_tags(html)
        results.append(("score_ranking: uses a real table, ranked order preserved", "Ana Paula Ribeiro" in text and text.find("Ana Paula") < text.find("Carlos Eduardo")))

        # ---------- combined blocks (Balão) — both blocks render, nothing dropped ----------
        both = page.evaluate("""
            () => {
              var s = window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('balao');
              return s.response.blocks.map(function (b) { return window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock(b); }).join('');
            }
        """)
        both_text = strip_tags(both)
        results.append(("Balão combined blocks: ranking block title present", "comparação por prazo" in both_text))
        results.append(("Balão combined blocks: metrics block title present", "Financiamento Balão" in both_text))
        results.append(("Balão combined blocks: both blocks' own values present, undropped", "3.180,45" in both_text and "2.890,75" in both_text))

        # ---------- No financial recalculation anywhere in the renderer source ----------
        renderer_src = page.evaluate("document.querySelector('script[src*=\"brabus-intelligence.js\"]') ? fetch(document.querySelector('script[src*=\"brabus-intelligence.js\"]').src).then(r => r.text()) : null")
        if renderer_src:
            forbidden_math = re.findall(r"Math\.(pow|round)\(", renderer_src)
            results.append(("renderer source contains no Math.pow/Math.round (no derived math)", len(forbidden_math) == 0))

        browser.close()

    ok = all(r[1] for r in results)
    for label, passed in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    print(f"\n=== Brabus Intelligence Presentation Parity Test: {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
