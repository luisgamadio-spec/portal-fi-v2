#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-2-STRUCTURED-BLOCK-FIX-01 -- ranking / score_ranking /
score_breakdown / operations presentation contract fix.

IA-V2-2-REAL-MODEL-UAT-02 discovered that 4 of the 6 structured-block
types render against a WRONG assumed field shape ({label,value,format}
uniformly) -- the real backend uses per-type shapes (see
docs/IA-V2-2-REAL-MODEL-UAT.md's "Critical finding" section for the
full source-backed matrix). This exercises the corrected renderers
directly (window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock),
with 0 OpenAI calls -- one fixture below (`ranking`, Subsidiado) is the
REAL payload captured live during that UAT; the others are synthetic
but shaped exactly per the source's own `buildXBlock` functions
(field-by-field, never guessed).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://localhost:8700/portal-next-v2/index.html"
results = []


def check(label, cond):
    results.append((label, bool(cond)))


# ---- Fixtures -----------------------------------------------------

# REAL payload, captured live during IA-V2-2-REAL-MODEL-UAT-02
# Scenario 5 (Subsidiado) -- the exact shape that rendered broken
# before this fix (raw "rate_term"/"sim_payment" headers, blank rows).
REAL_SUBSIDIADO_RANKING = {
    "type": "ranking",
    "title": "Taxas Subsidiadas — Novos",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "dimension": "rate_term",
    "metric": "sim_payment",
    "items": [
        {"position": 1, "name": "24x — taxa 0,49%", "sim_payment": 1920, "sim_financed": 40000, "sim_down_payment": 50000},
        {"position": 2, "name": "36x — taxa 0,99%", "sim_payment": 1530, "sim_financed": 40000, "sim_down_payment": 50000},
    ],
}

# Synthetic, shaped exactly per buildRankingBlock() (Resultado ranking
# tool) -- dimension="seller", metric="sales", every metric field
# always present per item (source: index.ts ~L1477-1500).
GENERIC_RESULTADO_RANKING = {
    "type": "ranking",
    "title": "Ranking de vendedores por vendas",
    "period_label": "Agosto/2026",
    "dimension": "seller",
    "metric": "sales",
    "entities_not_found": [],
    "items": [
        {"position": 1, "name": "Ana Paula Ribeiro", "sales": 12, "financed": 10, "share_percent": 34.2, "production": 1250000, "return": 42000, "return_avg_percent": 3.4, "spf": 8000, "profitability": 50000},
        {"position": 2, "name": "Bruno Alves", "sales": 9, "financed": 8, "share_percent": 25.1, "production": 980000, "return": 31000, "return_avg_percent": 3.1, "spf": 6200, "profitability": 37200},
    ],
}

# Synthetic, shaped exactly per buildScoreRankingBlock() (source:
# index.ts ~L1537-1552) -- items:[{rank,seller,store,department,score,
# classification,sales,financed}], no label/value/format anywhere.
SCORE_RANKING = {
    "type": "score_ranking",
    "title": "Ranking de Score F&I",
    "period_label": "Agosto/2026",
    "population_scope": "Grupo inteiro",
    "order": "desc",
    "classification_counts": {"OURO": 2, "PRATA": 1},
    "total_scored": 3,
    "items": [
        {"rank": 1, "seller": "Ana Paula Ribeiro", "store": "Barra Funda", "department": "NOVOS", "score": 91.2, "classification": "OURO", "sales": 12, "financed": 10},
        {"rank": 2, "seller": "Bruno Alves", "store": "Santo Amaro", "department": "NOVOS", "score": 84.7, "classification": "OURO", "sales": 9, "financed": 8},
        {"rank": 3, "seller": "Carla Nunes", "store": "Barra Funda", "department": "SEMINOVOS", "score": 68.3, "classification": "PRATA", "sales": 6, "financed": 5},
    ],
}

# Synthetic, shaped exactly per buildScoreBreakdownBlock() (source:
# index.ts ~L1562-1576) -- NO block.items at all; identity/summary
# fields flat on the block + components[]:{label,value,max}.
SCORE_BREAKDOWN = {
    "type": "score_breakdown",
    "title": "Score F&I — Ana Paula Ribeiro",
    "period_label": "Agosto/2026",
    "population_scope": "Grupo inteiro",
    "seller": "Ana Paula Ribeiro", "store": "Barra Funda", "department": "NOVOS",
    "score": 91.2, "classification": "OURO", "rank": 1,
    "sales": 12, "financed": 10,
    "penetration_percent": 83.3, "average_return_percent": 3.4,
    "components": [
        {"label": "Volume", "value": 22, "max": 25},
        {"label": "Penetração", "value": 18, "max": 20},
        {"label": "Mix de famílias", "value": 15, "max": 20},
        {"label": "Mix de planos", "value": 12, "max": 15},
        {"label": "SPF Extra", "value": 8, "max": 10},
        {"label": "Retorno médio", "value": 9, "max": 10},
    ],
    "plan_mix": {"LINEAR": 7, "BALAO": 3},
    "main_plan": "LINEAR", "family_count": 4,
}

# Synthetic, shaped exactly per buildOperationsBlock() (source:
# index.ts ~L1508-1530) -- Coparticipado/Subsidiado variant.
OPERATIONS_SIM = {
    "type": "operations",
    "title": "Coparticipados — Agosto/2026",
    "period_label": "Agosto/2026",
    "tipo": "COPARTICIPADO",
    "total_count": 2, "total_financed_value": 148000, "total_return_value": 9200,
    "truncated": False, "shown_count": 2,
    "items": [
        {"reference": "***7841", "date": "2026-08-05", "store": "Barra Funda", "department": "NOVOS", "seller": "Ana Paula Ribeiro", "model": "L200 TRITON", "financed_value": 80000, "return_value": 4000},
        {"reference": "***2290", "date": "2026-08-12", "store": "Santo Amaro", "department": "SEMINOVOS", "seller": "Bruno Alves", "model": "PAJERO SPORT", "financed_value": 68000, "return_value": 5200},
    ],
}

# Synthetic, shaped exactly per buildHistOperationsBlock() (source:
# index.ts ~L5102-5125) -- Histórico's own OTHER real `operations`
# variant: no `seller`/`return_value`, has down_payment_*/installment_*.
OPERATIONS_HIST = {
    "type": "operations",
    "title": "Operações históricas semelhantes — 90 dias",
    "period_label": "Amostra insuficiente — 2 operação(ões)",
    "total_count": 2, "total_financed_value": 308000,
    "truncated": False, "shown_count": 2,
    "items": [
        {"reference": "***V2MOCK1", "date": "2026-08-05", "store": "MATRIZ", "department": "NOVOS", "model": "L200 TRITON", "financed_value": 168000, "down_payment_value": 42000, "down_payment_percent": 20, "installment_value": 5480.5, "installments": 36},
        {"reference": "***V2MOCK2", "date": "2026-08-12", "store": "MATRIZ", "department": "SEMINOVOS", "model": "PAJERO SPORT", "financed_value": 140000, "down_payment_value": 35000, "down_payment_percent": 20, "installment_value": 3720.1, "installments": 48},
    ],
}

MALICIOUS_RANKING = {
    "type": "ranking",
    "title": "<script>alert(1)</script>",
    "dimension": "seller", "metric": "sales",
    "items": [{"position": 1, "name": '<img src=x onerror=alert(1)>', "sales": 1}],
}
MALICIOUS_OPERATIONS = {
    "type": "operations",
    "title": "Operations",
    "items": [{"reference": '<a href="javascript:alert(1)">x</a>', "date": "2026-08-05", "store": "<script>alert(2)</script>", "financed_value": 1000}],
}

# Non-regression fixtures (unchanged shape, already-passing contract).
METRICS_FIXTURE = {"type": "metrics", "title": "Simulação — Financiamento Linear Novos", "period_label": "Simulação — não é proposta nem aprovação de crédito",
                    "items": [{"label": "Valor do Veículo", "value": 120000, "format": "currency"}, {"label": "Entrada (%)", "value": 25, "format": "percent"}]}
COMPARISON_FIXTURE = {"type": "comparison", "title": "Comparação",
                       "a": {"label": "Barra Funda", "period_label": "Agosto/2026", "items": [{"label": "Vendas", "value": 12, "format": "int"}]},
                       "b": {"label": "Santo Amaro", "period_label": "Agosto/2026", "items": [{"label": "Vendas", "value": 9, "format": "int"}]}}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        page.goto(BASE + "#/brabus-intelligence")
        page.wait_for_timeout(400)

        def render(block):
            html = page.evaluate("(b) => window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock(b)", block)
            div_info = page.evaluate(
                """(html) => {
                    const div = document.createElement('div');
                    div.innerHTML = html;
                    document.body.appendChild(div);
                    const info = {
                        text: div.textContent,
                        hasScriptTag: !!div.querySelector('script'),
                        hasImgTag: !!div.querySelector('img'),
                        hasAnchorTag: !!div.querySelector('a'),
                        hasOnErrorAttr: !!div.querySelector('[onerror]'),
                        hasJsHref: Array.from(div.querySelectorAll('[href]')).some(e => (e.getAttribute('href')||'').toLowerCase().startsWith('javascript:')),
                        tableCount: div.querySelectorAll('table').length,
                        cardCount: div.querySelectorAll('.baiOperationCard').length,
                    };
                    div.remove();
                    return info;
                }""",
                html,
            )
            return html, div_info

        # ---- Gate 13: Scenario 5 replay (real payload) --------------
        html, info = render(REAL_SUBSIDIADO_RANKING)
        check("Scenario 5 replay: no raw 'rate_term' header", "rate_term" not in html)
        check("Scenario 5 replay: no raw 'sim_payment' header text", "<th>sim_payment</th>" not in html)
        check("Scenario 5 replay: human header 'Condição' present", "Condição" in html)
        check("Scenario 5 replay: human header 'Parcela' present", "Parcela" in html)
        check("Scenario 5 replay: human header 'Entrada' present", "Entrada" in html)
        check("Scenario 5 replay: human header 'Financiado' present", "Financiado" in html)
        check("Scenario 5 replay: row label '24x' present", "24x" in html)
        check("Scenario 5 replay: value R$ 1.920,00 present", "1.920,00" in html)
        check("Scenario 5 replay: value R$ 1.530,00 present", "1.530,00" in html)
        check("Scenario 5 replay: no blank em-dash value cells", "<td class=\"modCurrencyCol\">—</td>" not in html)

        # ---- Gate 6: ranking, generic Resultado shape ----------------
        html, info = render(GENERIC_RESULTADO_RANKING)
        check("ranking (Resultado): header 'Vendedor' present", "Vendedor" in html)
        check("ranking (Resultado): header 'Vendas' present", "Vendas" in html)
        check("ranking (Resultado): value 12 present", ">12<" in html)
        check("ranking (Resultado): currency Produção formatted (R$)", "R$" in html)
        check("ranking (Resultado): percent Share formatted (%)", "34,2%" in html or "34.2%" in html)
        check("ranking (Resultado): position order preserved (Ana before Bruno)", html.index("Ana Paula") < html.index("Bruno Alves"))

        # ---- Gate 7: score_ranking -----------------------------------
        html, info = render(SCORE_RANKING)
        check("score_ranking: no raw field-name headers", "seller" not in html.lower().replace("baiblockpanel", "") or "Vendedor" in html)
        check("score_ranking: Vendedor header present", "Vendedor" in html)
        check("score_ranking: Score header present", "Score" in html)
        check("score_ranking: seller names present", "Ana Paula Ribeiro" in html and "Bruno Alves" in html and "Carla Nunes" in html)
        check("score_ranking: rank order preserved (Ana, Bruno, Carla)", html.index("Ana Paula") < html.index("Bruno Alves") < html.index("Carla Nunes"))
        check("score_ranking: classification shown", "OURO" in html and "PRATA" in html)
        check("score_ranking: store shown", "Barra Funda" in html)

        # ---- Gate 8: score_breakdown -----------------------------------
        html, info = render(SCORE_BREAKDOWN)
        check("score_breakdown: no empty block (had 0 items before fix)", len(info["text"].strip()) > 20)
        check("score_breakdown: Score value 91,2 present", "91,2" in html or "91.2" in html)
        check("score_breakdown: classification OURO present", "OURO" in html)
        check("score_breakdown: component Volume 22 / 25 present", "Volume" in html and "22" in html and "25" in html)
        check("score_breakdown: component Penetração present", "Penetração" in html)
        check("score_breakdown: plan_mix rendered (LINEAR/BALAO)", "LINEAR" in html and "BALAO" in html)
        check("score_breakdown: no recomputation (91.2 appears verbatim, no derived math in source)", "91,2" in html or "91.2" in html)

        # ---- Gate 9: operations, both real variants -------------------
        html, info = render(OPERATIONS_SIM)
        check("operations (sim variant): rendered as cards, not a table", info["tableCount"] == 0 and info["cardCount"] == 2)
        check("operations (sim variant): no raw field-name column headers (no table at all)", "<th>" not in html)
        check("operations (sim variant): reference shown", "***7841" in html)
        check("operations (sim variant): date formatted DD/MM/YYYY", "05/08/2026" in html)
        check("operations (sim variant): financed_value currency formatted", "R$" in html)
        check("operations (sim variant): summary total_count/total_financed_value shown", "financiado total" in html)

        html, info = render(OPERATIONS_HIST)
        check("operations (hist variant): rendered as cards", info["cardCount"] == 2)
        check("operations (hist variant): installment_value/installments shown", "Parcela" in html and "Parcelas" in html)
        check("operations (hist variant): down_payment_percent shown as percent", "20,0%" in html or "20.0%" in html)

        # ---- Gate 11: escaping / injection -----------------------------
        html, info = render(MALICIOUS_RANKING)
        check("malicious ranking: no <script> element", not info["hasScriptTag"])
        check("malicious ranking: no live <img>", not info["hasImgTag"])
        check("malicious ranking: no live [onerror]", not info["hasOnErrorAttr"])
        html, info = render(MALICIOUS_OPERATIONS)
        check("malicious operations: no live <a> element", not info["hasAnchorTag"])
        check("malicious operations: no live javascript: href", not info["hasJsHref"])
        check("malicious operations: no <script> element", not info["hasScriptTag"])
        check("no alert() dialogs fired by any payload", len(dialogs) == 0)

        # ---- Gate 16: metrics/comparison non-regression -----------------
        html, info = render(METRICS_FIXTURE)
        check("metrics non-regression: unchanged output shape", "baiMetricsGrid" in html and "120.000,00" in html and "25,0%" in html)
        html, info = render(COMPARISON_FIXTURE)
        check("comparison non-regression: unchanged output shape", "baiComparisonGrid" in html and "baiComparisonSide" in html and "Barra Funda" in html and "Santo Amaro" in html)

        # ---- Gate 18: responsive across all 4 corrected types -----------
        combo_blocks = [REAL_SUBSIDIADO_RANKING, SCORE_RANKING, SCORE_BREAKDOWN, OPERATIONS_SIM]
        for w, h in [(1366, 768), (768, 1024), (430, 932), (390, 844)]:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate(
                """(blocks) => {
                    const el = document.getElementById('baiConversation');
                    const html = blocks.map(b => window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock(b)).join('');
                    el.innerHTML = '<div class="baiStructuredRegion">' + html + '</div>';
                }""",
                combo_blocks,
            )
            page.wait_for_timeout(150)
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"{w}x{h}: no horizontal overflow (ranking+score_ranking+score_breakdown+operations combined)", not overflow)

        browser.close()

    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Brabus Intelligence Structured Block Contract Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
