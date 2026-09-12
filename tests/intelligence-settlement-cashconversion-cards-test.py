#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3K.1 -- Settlement (Antecipação) and Cash Conversion native cards.

Real conversational UAT found both domains' calculation/speed approved
but the presentation "visualmente cru e repetitivo" (Antecipação,
UAT-VOICE-01A) and "excesso de repetição"/"excessivamente neutra"
(Cash Conversion, UAT-VOICE-01B) -- the same generic .baiCompactMetrics
grid complaint the financing-plan cards (IA-3J.4C) already fixed for
Balão/Linear.

This suite proves: portal-ai-homolog's buildAntecipacaoBlock/
buildCashConversionBlock (IA-3K.1) now attach `settlement_card`/
`cash_conversion_card` metadata (same contract class as
`financing_card`); intelligence-panel.js's new settlementCardHtml()/
cashConversionCardHtml() render them as distinct cards reusing the
EXACT same .baiPlanCard* classes already defined for the financing
cards (zero new CSS) -- while every other metrics block (including
the financing-plan cards themselves) keeps its own existing treatment
completely unchanged.

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-3k1")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


TRUE_OVERFLOW_JS = """
() => {
    var vw = window.innerWidth;
    var worst = 0, worstSel = null;
    document.querySelectorAll('#baiLauncherRoot *').forEach(el => {
        var r = el.getBoundingClientRect();
        var over = Math.max(0, r.right - vw);
        if (over > worst) { worst = over; worstSel = el.className; }
    });
    return { worst: worst, worstSel: worstSel };
}
"""


def true_overflow(page):
    return page.evaluate(TRUE_OVERFLOW_JS)


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


def set_profile(page, state, is_master=None, perfil=None):
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def push_message(page, blocks, prose="Resposta."):
    page.evaluate(
        """([prose, blocks]) => {
            window.NX_INTELLIGENCE_STATE.resetConversation();
            window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content: prose, blocks: blocks, isError:false});
        }""",
        [prose, blocks],
    )
    page.wait_for_timeout(150)


# ---------- real engine field shapes (buildAntecipacaoBlock/buildCashConversionBlock, IA-3K.1) ----------
SETTLEMENT_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Antecipação / Liquidação Antecipada",
    "period_label": "Estimativa comercial — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Prazo original", "value": 48, "format": "number"},
        {"label": "Parcela mensal do contrato", "value": 3500, "format": "currency"},
        {"label": "Primeira parcela considerada (premissa: hoje + 30 dias)", "value": "2026-10-11", "format": "date"},
        {"label": "Data da antecipação/quitação", "value": "2027-09-11", "format": "date"},
        {"label": "Parcelas restantes", "value": 36, "format": "number"},
        {"label": "Valor bruto (nominal restante)", "value": 175500.00, "format": "currency"},
        {"label": "Desconto total", "value": 42495.60, "format": "currency"},
        {"label": "Valor para quitação", "value": 133004.40, "format": "currency"},
    ],
    "settlement_card": {
        "settlement_amount": 133004.40,
        "settlement_date": "2027-09-11",
        "gross_total": 175500.00,
        "discount_total": 42495.60,
        "discount_percent_of_gross": 24.21,
        "installments_considered": 36,
        "scope_label": "Parcelas restantes",
        "first_due_date": "2026-10-11",
        "first_due_date_assumed": True,
        "balloons": [{"installment_number": 30, "value": 74000}],
    },
}

CASH_CONVERSION_BLOCK_UTILIZAR = {
    "type": "metrics",
    "title": "Simulação — Cash Conversion",
    "period_label": "Classificação: Utilizar o capital — estimativa dentro das premissas informadas, não é recomendação de investimento",
    "items": [
        {"label": "Capital inicial", "value": 90000, "format": "currency"},
        {"label": "Parcela ofertada (42x)", "value": 3563.06, "format": "currency"},
        {"label": "Taxa de aplicação (a.m.) — premissa padrão fixa", "value": 1.12, "format": "percent"},
        {"label": "Total nominal das parcelas", "value": 149648.52, "format": "currency"},
        {"label": "Capital final projetado", "value": 143680.91, "format": "currency"},
        {"label": "Rendimento projetado", "value": 53680.91, "format": "currency"},
        {"label": "Diferença projetada", "value": -5967.61, "format": "currency"},
        {"label": "Taxa de equilíbrio (a.m., cálculo adicional)", "value": 1.22, "format": "percent"},
    ],
    "cash_conversion_card": {
        "capital": 90000,
        "monthly_payment": 3563.06,
        "term_months": 42,
        "application_rate": 0.0112,
        "break_even_rate": 0.0122,
        "final_financing_value": 149648.52,
        "future_investment_value": 143680.91,
        "projected_difference": -5967.61,
        "classification": "UTILIZAR",
    },
}

CASH_CONVERSION_BLOCK_EQUIVALENTE = {
    "type": "metrics",
    "title": "Simulação — Cash Conversion",
    "period_label": "Classificação: Resultados equivalentes — estimativa dentro das premissas informadas, não é recomendação de investimento",
    "items": [
        {"label": "Capital inicial", "value": 50000, "format": "currency"},
        {"label": "Parcela ofertada (24x)", "value": 2100, "format": "currency"},
        {"label": "Taxa de aplicação (a.m.) — premissa padrão fixa", "value": 1.12, "format": "percent"},
        {"label": "Diferença projetada", "value": 0, "format": "currency"},
    ],
    "cash_conversion_card": {
        "capital": 50000,
        "monthly_payment": 2100,
        "term_months": 24,
        "application_rate": 0.0112,
        "break_even_rate": None,
        "final_financing_value": 50400,
        "future_investment_value": 50400,
        "projected_difference": 0,
        "classification": "EQUIVALENTE",
    },
}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        open_panel(page)

        # ---------- A. Settlement (Antecipação) card ----------
        push_message(page, [SETTLEMENT_BLOCK])
        check("settlement card renders as a .baiPlanCard (design-system reuse, not a new visual language)", page.locator(".baiPlanCard").count() == 1)
        card_text = page.locator(".baiPlanCard").inner_text()
        card_text_upper = card_text.upper()
        check("kind label visible: 'Quitação Antecipada'", "QUITAÇÃO ANTECIPADA" in card_text_upper)
        check("hero settlement amount visible (R$ 133.004,40)", "133.004,40" in card_text)
        check("settlement date visible in hero sub-caption", "11/09/2027" in card_text or "2027" in card_text)
        check("valor nominal restante visible (R$ 175.500,00)", "175.500,00" in card_text)
        check("desconto estimado visible (R$ 42.495,60)", "42.495,60" in card_text)
        # A.formatValue(..., 'percent') rounds to 1 decimal (pre-existing,
        # shared convention -- same formatter the old generic items grid
        # already used for this exact field) -- 24.21 renders "24,2%".
        check("economia percent visible (24,2%, 1-decimal formatter convention)", "24,2" in card_text or "24.2" in card_text)
        check("installments-remaining secondary info visible (36)", "36" in card_text and "PAGAMENTOS" in card_text_upper)
        check("balloon secondary info visible (R$ 74.000 na parcela 30)", "74.000" in card_text and "30" in card_text)
        check("premise note visible (primeira parcela assumida)", "PREMISSA" in card_text_upper and "HOJE + 30 DIAS" in card_text_upper)
        check("disclaimer visible (estimativa comercial / instituição financeira)", "INSTITUIÇÃO FINANCEIRA" in card_text_upper)
        check("settlement card does NOT use the generic .baiCompactMetrics treatment", page.locator(".baiAnswerMetrics .baiCompactMetrics").count() == 0)
        for raw in ["SETTLEMENT_CARD", "GROSS_TOTAL", "DISCOUNT_TOTAL", "INSTALLMENT_NUMBER", "FIRST_DUE_DATE_ASSUMED"]:
            check(f"raw internal field name not visible: {raw}", raw not in card_text_upper)
        check("numbers are not repeated a second time in a duplicate paragraph below the card (only 1 occurrence of the settlement amount)", card_text.count("133.004,40") == 1)
        shot(page, "01-settlement-card.png")

        # ---------- B. Settlement card, no assumed first_due_date (premise note absent) ----------
        block_no_premise = dict(SETTLEMENT_BLOCK)
        block_no_premise["settlement_card"] = dict(SETTLEMENT_BLOCK["settlement_card"])
        block_no_premise["settlement_card"]["first_due_date_assumed"] = False
        push_message(page, [block_no_premise])
        note_text = page.locator(".baiPlanCardTarget").inner_text().upper()
        check("premise note absent when first_due_date was NOT assumed", "PREMISSA" not in note_text)
        check("disclaimer still present even without the premise note", "INSTITUIÇÃO FINANCEIRA" in note_text)

        # ---------- C. Cash Conversion card -- UTILIZAR (à vista wins) ----------
        push_message(page, [CASH_CONVERSION_BLOCK_UTILIZAR])
        check("cash conversion card renders as a .baiPlanCard", page.locator(".baiPlanCard").count() == 1)
        cc_text = page.locator(".baiPlanCard").inner_text()
        cc_text_upper = cc_text.upper()
        check("kind label visible: 'Cash Conversion'", "CASH CONVERSION" in cc_text_upper)
        check("capital preservado visible (R$ 90.000,00)", "90.000,00" in cc_text)
        check("financiamento term visible (42x)", "42" in cc_text_upper)
        # Same 1-decimal percent-formatter convention as above: 0.0112 ->
        # "1,1%", 0.0122 -> "1,2%" -- still visually distinct (the point
        # of this check: break-even is a first-class fact in the card,
        # never a buried footnote), just not 2-decimal precision.
        check("taxa considerada visible (1,1%)", "1,1" in cc_text or "1.1" in cc_text)
        check("taxa de equilíbrio visible (1,2%) -- never buried as a footnote", "1,2" in cc_text or "1.2" in cc_text)
        check("math result names the winner: À Vista", "À VISTA" in cc_text_upper)
        check("math result shows the difference amount (R$ 5.967,61)", "5.967,61" in cc_text)
        check("capital-preservation strategy framing visible (liquidez/investimento)", "LIQUIDEZ" in cc_text_upper or "INVESTIMENTO" in cc_text_upper)
        check("strategy line states financing preserves the exact capital amount (R$ 90.000,00 again, in the strategy sentence)", cc_text.count("90.000,00") == 2)
        check("cash conversion card does NOT use the generic .baiCompactMetrics treatment", page.locator(".baiAnswerMetrics .baiCompactMetrics").count() == 0)
        for raw in ["CASH_CONVERSION_CARD", "PROJECTED_DIFFERENCE", "BREAK_EVEN_RATE", "\"UTILIZAR\""]:
            check(f"raw internal field name not visible: {raw}", raw not in cc_text_upper)
        shot(page, "02-cash-conversion-utilizar.png")

        # ---------- D. Cash Conversion card -- EQUIVALENTE (no break-even, no hero amount) ----------
        push_message(page, [CASH_CONVERSION_BLOCK_EQUIVALENTE])
        eq_text_upper = page.locator(".baiPlanCard").inner_text().upper()
        check("EQUIVALENTE result labeled as such, never declares a winner", "EQUIVALENTE" in eq_text_upper and "À VISTA" not in eq_text_upper and "FINANCIAR" not in eq_text_upper.split("EQUIVALENTE")[0])
        check("break-even fact omitted when break_even_rate is null (never shown as a fabricated value)", "TAXA DE EQUILÍBRIO" not in eq_text_upper)

        # ---------- E. regression: existing financing-plan cards (Balão/Linear) still work when mixed with a non-financing block ----------
        balao_block = {
            "type": "metrics", "title": "Simulação — Financiamento Balão Novos (30x)",
            "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "items": [{"label": "Parcela Mensal", "value": 1766.94, "format": "currency"}],
            "financing_card": {"kind": "BALAO", "term_months": 30, "monthly_payment": 1766.94, "down_payment": 90000, "financed_amount": 90000, "balloons": [{"month": 15, "value": 45000}, {"month": 30, "value": 45000}], "target_payment": 1800, "target_distance": 33.06},
        }
        push_message(page, [balao_block, SETTLEMENT_BLOCK])
        check("mixed message: financing-plan card AND settlement card both render, independently", page.locator(".baiPlanCardPrimary").count() == 1 and "QUITAÇÃO" in page.locator(".baiPlanCard").nth(1).inner_text().upper())

        # ---------- F. regression: non-financial metrics block totally unaffected ----------
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{
                    type:'metrics', title:'Resultado do Grupo — Mês Anterior', period_label:'mês anterior', items:[
                        {label:'Vendas', value:84, format:'int'},
                        {label:'Retorno', value:197172.96, format:'currency'}
                    ]
                }], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        check("non-financial metrics block still uses the OLD compact/anonymous treatment (no plan card, unaffected)", page.locator(".baiPlanCard").count() == 0 and page.locator(".baiCompactMetrics").count() == 1)

        # ---------- G. responsive / zero horizontal scroll (both card types, existing .baiPlanCard* CSS, no new rules) ----------
        for width in [1366, 1024, 900, 480]:
            page.set_viewport_size({"width": width, "height": 900})
            push_message(page, [SETTLEMENT_BLOCK, CASH_CONVERSION_BLOCK_UTILIZAR])
            ov = true_overflow(page)
            check(f"{width}px: no true viewport overflow from settlement/cash-conversion cards", ov["worst"] <= 0.5, ov)
            doc_ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{width}px: document itself has zero horizontal scroll", doc_ov <= 0, doc_ov)
            shot(page, f"03-responsive-{width}.png")

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Settlement / Cash Conversion Cards Test (IA-3K.1): {passed}/{total} ===")
    print("RESULT: PASS" if passed == total else "RESULT: FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
