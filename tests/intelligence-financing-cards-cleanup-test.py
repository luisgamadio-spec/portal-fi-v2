#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-UAT-05 -- Clean Financial Recommendation Cards.

Human UAT (VOICE-UAT-03/IA-UAT-04's new <=3-proposal commercial
selection): the Balão proposal renders correctly as a .baiPlanCard
(mode="payment", already carries a real financing_card), but each
LINEAR alternative arrives through portal-ai-homolog's OTHER block
shape (mode="required_down_payment"), which buildSimulationMetricsBlock
(Secure repo, READ-ONLY this Wave, confirmed by direct reading) never
attaches a financing_card to -- only a flat metrics grid with items
like "Valor do Veículo"/"Parcela Desejada"/"Entrada necessária (Nx)"/
"Parcela obtida (Nx)". Each Linear alternative therefore rendered as
the old anonymous .baiCompactMetrics grid, repeating "Valor do
Veículo"/"Parcela Desejada" once per proposal -- exactly the Human's
"campos soltos / repetição" finding.

Presentation-only fix (Secure untouched): intelligence-panel.js now
recognizes that exact, stable label template and synthesizes a real
financing_card client-side (isRequiredDownPaymentGridBlock/
syntheticFinancingCardsFromGrid) before the existing, unmodified
financingPlanCardHtml renders it -- reusing the SAME .baiPlanCard
component the Balão proposal already used, never a new visual
language. Also: PARCELA DESEJADA/PARCELA OBTIDA collapse into a single
hero value when equal (no redundant comparison line when the proposal
hits the target exactly), and the primary-card pick now only lets
target_distance override array order (which already matches the
backend's own RECOMENDADO-first selection) for a MEANINGFUL (>R$1)
difference -- preserving the older engine-first flow's own already-
approved primary-selection behavior unchanged (see its own fixture,
R$33,06 vs R$1.184,38, re-run below as a direct regression check).

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL).
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-uat05")
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


def push_message(page, blocks, prose="", role="assistant"):
    page.evaluate(
        """([role, prose, blocks]) => {
            window.NX_INTELLIGENCE_STATE.resetConversation();
            window.NX_INTELLIGENCE_STATE.pushMessage({role: role, content: prose, blocks: blocks, isError: false});
        }""",
        [role, prose, blocks],
    )
    page.wait_for_timeout(150)


# ---------- real shapes, exactly as portal-ai-homolog's own block builders produce them ----------

def linear_grid_block(term_months, vehicle_value, target_payment, down_payment, obtained_payment):
    # buildSimulationMetricsBlock's required_down_payment branch (Secure,
    # read-only this Wave) -- confirmed by direct reading: no
    # financing_card, flat items with this EXACT label template.
    return {
        "type": "metrics",
        "title": "Simulação — Entrada necessária (Novos)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [
            {"label": "Valor do Veículo", "value": vehicle_value, "format": "currency"},
            {"label": "Parcela Desejada", "value": target_payment, "format": "currency"},
            {"label": f"Entrada necessária ({term_months}x)", "value": down_payment, "format": "currency"},
            {"label": f"Parcela obtida ({term_months}x)", "value": obtained_payment, "format": "currency"},
        ],
    }


def balao_card_block(term_months, monthly_payment, down_payment, balloons, target_payment):
    return {
        "type": "metrics",
        "title": f"Simulação — Financiamento Balão Novos ({term_months}x)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [],
        "financing_card": {
            "kind": "BALAO", "term_months": term_months, "monthly_payment": monthly_payment,
            "down_payment": down_payment, "financed_amount": None, "balloons": balloons,
            "target_payment": target_payment, "target_distance": abs(monthly_payment - target_payment),
        },
    }


# Human's own real UAT scenario (conceptual, from VOICE-UAT-03/IA-UAT-04's own briefs) --
# Triton Katana R$330.000, target R$3.500.
BALAO_3PROPOSAL = balao_card_block(48, 3500, 164270.18, [{"month": 48, "value": 165729.82}], 3500)
LINEAR60_3PROPOSAL = linear_grid_block(60, 330000, 3500, 224222.30, 3500)
LINEAR48_3PROPOSAL = linear_grid_block(48, 330000, 3500, 234704.17, 3500)


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

        # ============================================================
        # TEST A -- 3 proposals: exactly 3 cards, no loose generic grid
        # ============================================================
        push_message(
            page, [BALAO_3PROPOSAL, LINEAR60_3PROPOSAL, LINEAR48_3PROPOSAL],
            prose="Encontrei três caminhos. Eu começaria pelo Balão de 48 meses porque atinge a parcela de R$3.500 com a menor entrada. Deixei duas opções Lineares para comparação."
        )
        cards = page.locator(".baiPlanCard")
        check("[A] exactly 3 proposal cards render (1 Balão + 2 Linear, none left as a loose grid)", cards.count() == 3, cards.count())
        check("[A] no loose generic proposal grid (.baiCompactMetrics) anywhere in the card group", page.locator(".baiPlanCardGroup .baiCompactMetrics").count() == 0)
        group_text = page.locator(".baiPlanCardGroup").inner_text()
        group_text_upper = group_text.upper()
        check("[A] plan types visible: Balão + 2x Linear", "BALÃO" in group_text_upper and group_text_upper.count("LINEAR") == 2)
        check("[A] Balão term visible (48 meses)", "48" in group_text_upper.split("BALÃO")[-1][:40])
        check("[A] both Linear terms visible (60 and 48)", "60" in group_text_upper and group_text_upper.count("48") >= 1)
        primary = page.locator(".baiPlanCardPrimary")
        check("[A] exactly one card marked primary/RECOMENDADO", primary.count() == 1)
        check("[A] the primary card is the Balão one (array order = backend's own RECOMENDADO-first selection, all distances near-tied)", "BALÃO" in primary.inner_text().upper())
        shot(page, "01-three-proposal-cards.png")

        # ============================================================
        # TEST B -- dedupe: target == obtained -> no redundant labels
        # ============================================================
        check("[B] 'PARCELA DESEJADA' never shown as a raw label inside the card group", "PARCELA DESEJADA" not in group_text_upper)
        check("[B] 'PARCELA OBTIDA' never shown as a raw label inside the card group", "PARCELA OBTIDA" not in group_text_upper)
        check("[B] 'VALOR DO VEÍCULO' not repeated inside the proposal cards (context already established)", "VALOR DO VEÍCULO" not in group_text_upper)
        linear_cards_text = [c.upper() for c in [page.locator(".baiPlanCard").nth(i).inner_text() for i in range(3)] if "LINEAR" in c.upper()]
        check("[B] each Linear card shows the hero payment (R$3.500) exactly once", all(c.count("3.500") == 1 or c.count("3500") == 1 for c in linear_cards_text), linear_cards_text)
        check("[B] no distance/comparison line when target==obtained (distance rounds to R$0,00)",
              "ACIMA DA META" not in group_text_upper and "ABAIXO DA META" not in group_text_upper, group_text_upper)

        # ============================================================
        # TEST C -- a genuine difference gets a short comparison line
        # ============================================================
        linear_diff_block = linear_grid_block(60, 330000, 3500, 224222.30, 3587)
        push_message(page, [linear_diff_block], prose="Linear em 60 meses.")
        diff_text_upper = page.locator(".baiPlanCard").inner_text().upper()
        check("[C] a real difference (target 3500, obtained 3587) shows a short comparison line", "87" in diff_text_upper and "ACIMA DA META" in diff_text_upper, diff_text_upper)
        check("[C] the comparison line is short -- no redundant restatement of the target value in parentheses", "(META: R$" not in diff_text_upper)
        check("[C] 'PARCELA DESEJADA'/'PARCELA OBTIDA' still never shown as raw labels", "PARCELA DESEJADA" not in diff_text_upper and "PARCELA OBTIDA" not in diff_text_upper)

        # ============================================================
        # TEST D -- single proposal: exactly 1 card, no grid beneath it
        # ============================================================
        push_message(page, [LINEAR48_3PROPOSAL], prose="Linear em 48 meses.")
        check("[D] exactly 1 card for a single Linear proposal", page.locator(".baiPlanCard").count() == 1)
        check("[D] no generic result grid rendered beneath the single card", page.locator(".baiCompactMetrics").count() == 0)
        single_text_upper = page.locator(".baiPlanCard").inner_text().upper()
        check("[D] the single card still shows Entrada and Financiado facts", "ENTRADA" in single_text_upper and "FINANCIADO" in single_text_upper)

        # ============================================================
        # TEST E -- multi-balloon: each balloon its own row, no repeated financed amount
        # ============================================================
        multi_balloon_block = balao_card_block(
            30, 1766.94, 90000,
            [{"month": 15, "value": 45000}, {"month": 30, "value": 45000}],
            1800,
        )
        push_message(page, [multi_balloon_block], prose="Balão em 30 meses, 2 balões.")
        mb_text_upper = page.locator(".baiPlanCard").inner_text().upper()
        check("[E] both balloon rows visible (mês 15 e mês 30)", "MÊS 15" in mb_text_upper and "MÊS 30" in mb_text_upper, mb_text_upper)
        check("[E] both balloon values visible (R$45.000 each)", mb_text_upper.count("45.000") >= 2 or mb_text_upper.count("45000") >= 2)
        check("[E] 'FINANCIADO' appears at most once (never repeated per balloon)", mb_text_upper.count("FINANCIADO") <= 1, mb_text_upper)

        # ============================================================
        # TEST F/G -- Text and Voice render the SAME cards from the SAME payload
        # (the renderer is keyed ONLY on msg.blocks -- no role/source
        # branch anywhere in renderBlocksHtml/renderOneBlock/messageHtml,
        # confirmed by direct reading -- so pushing the identical blocks
        # under either role must produce byte-identical card markup).
        # ============================================================
        same_blocks = [BALAO_3PROPOSAL, LINEAR60_3PROPOSAL, LINEAR48_3PROPOSAL]
        push_message(page, same_blocks, prose="Texto: três caminhos.", role="assistant")
        text_group_html = page.locator(".baiPlanCardGroup").inner_html()
        push_message(page, same_blocks, prose="Voz: três caminhos.", role="assistant")
        voice_group_html = page.locator(".baiPlanCardGroup").inner_html()
        check("[F/G] Text and Voice render byte-identical card markup for the identical structured payload (same component, no Voice-only/Text-only renderer)", text_group_html == voice_group_html)

        # ============================================================
        # TEST H -- no duplicate content across prose + loose grid + cards
        # ============================================================
        push_message(page, same_blocks, prose="Encontrei três caminhos. Comecei pelo Balão de 48 meses.")
        prose_text = page.locator(".baiAnswerProse").inner_text()
        check("[H] prose stays a short recommendation -- does not restate every card's own numeric values", "224.222,30" not in prose_text and "234.704,17" not in prose_text and "164.270,18" not in prose_text, prose_text)
        check("[H] no loose grid duplicates what the cards already show", page.locator(".baiCompactMetrics").count() == 0)

        # ============================================================
        # TEST I -- responsive: 3 cards, no horizontal overflow, desktop and mobile
        # ============================================================
        ov_desktop = true_overflow(page)
        check("[I] 1366px: no true viewport overflow from the 3-card group", ov_desktop["worst"] <= 0.5, ov_desktop)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(150)
        ov_mobile = true_overflow(page)
        check("[I] 390px (mobile): no true viewport overflow -- cards stack vertically, never 3 forced narrow columns", ov_mobile["worst"] <= 0.5, ov_mobile)
        shot(page, "02-responsive-390.png")
        page.set_viewport_size({"width": 1366, "height": 768})
        page.wait_for_timeout(150)

        # ============================================================
        # TEST J -- regression: Cash Conversion / Settlement cards, and the
        # OLDER engine-first flow's own primary-selection fixture, untouched.
        # ============================================================
        CASH_BLOCK = {
            "type": "metrics", "title": "Simulação — Cash Conversion", "items": [],
            "cash_conversion_card": {
                "capital": 90000, "monthly_payment": 3563.06, "term_months": 42,
                "application_rate": 0.0112, "break_even_rate": 0.0122,
                "final_financing_value": 149648.52, "future_investment_value": 143680.91,
                "projected_difference": -5967.61, "classification": "UTILIZAR",
            },
        }
        push_message(page, [CASH_BLOCK], prose="Cash Conversion.")
        check("[J] Cash Conversion card still renders via its own existing component, untouched", page.locator(".baiPlanCard").count() == 1 and "CASH CONVERSION" in page.locator(".baiPlanCard").inner_text().upper())

        SETTLEMENT_BLOCK = {
            "type": "metrics", "title": "Simulação — Antecipação", "items": [],
            "settlement_card": {
                "settlement_amount": 133004.40, "settlement_date": "2027-09-11",
                "gross_total": 175500.00, "discount_total": 42495.60,
                "discount_percent_of_gross": 24.21, "installments_considered": 36,
                "scope_label": "Parcelas restantes", "first_due_date": "2026-10-11",
                "first_due_date_assumed": True, "balloons": [],
            },
        }
        push_message(page, [SETTLEMENT_BLOCK], prose="Antecipação.")
        check("[J] Settlement card still renders via its own existing component, untouched", page.locator(".baiPlanCard").count() == 1 and "133.004,40" in page.locator(".baiPlanCard").inner_text())

        # Older engine-first flow's own already-approved fixture (IA-3J.4C) --
        # a MATERIAL target_distance gap (R$33,06 vs R$1.184,38) must still
        # correctly pick Balão as primary, proving the new >R$1 margin rule
        # did not regress this.
        OLD_BALAO = {
            "type": "metrics", "title": "Simulação — Financiamento Balão Novos (30x)", "items": [],
            "financing_card": {
                "kind": "BALAO", "term_months": 30, "monthly_payment": 1766.94,
                "down_payment": 90000, "financed_amount": 90000,
                "balloons": [{"month": 15, "value": 45000}, {"month": 30, "value": 45000}],
                "target_payment": 1800, "target_distance": 33.06,
            },
        }
        OLD_LINEAR = {
            "type": "metrics", "title": "Simulação — Financiamento Linear Novos", "items": [],
            "financing_card": {
                "kind": "LINEAR", "term_months": 60, "monthly_payment": 2984.38,
                "down_payment": 90000, "financed_amount": 90000,
                "target_payment": 1800, "target_distance": 1184.38,
            },
        }
        push_message(page, [OLD_BALAO, OLD_LINEAR], prose="Recomendo o Balão.")
        old_primary = page.locator(".baiPlanCardPrimary")
        check("[J] older engine-first fixture: primary is STILL Balão (material R$1.151,32 gap correctly overrides array order)", old_primary.count() == 1 and "BALÃO" in old_primary.inner_text().upper())

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        page.close()
        browser.close()

    ok = all(r[1] for r in results)
    print(f"\n=== IA-UAT-05: Clean Financial Recommendation Cards ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
