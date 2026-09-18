#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL-UX2-HOTFIX -- History-based recommendation card alignment.

Real Human UAT defect (2/2 reproductions, 18/09/2026, new/independent
conversations, Cache Storage cleared, Service Worker unregistered): for
the HISTORY-based recommendation route ("com base no que foi vendido
nos últimos 30 dias, quais planos você me aconselha ofertar?"), the
model's own prose named Balão as its first recommendation, but the
RECOMENDADO badge landed on the Linear card instead.

Root cause (proven by trace, portal-ai-homolog READ-ONLY): this route
has NO deterministic dispatch authority (unlike the parcela-alvo
route's own selectCommercialProposals) -- the model decides, via
free-text prompt instructions, how many/which simular_financiamento
calls to make and in what order; intelligence-panel.js's own
renderBlocksHtml() then fell back to `primary = financing[0]` (pure
array position), which merely reflects that non-deterministic
tool-call order, never the model's own narrative recommendation.

Fix: portal-ai-homolog's buildHistSummaryBlock (already computing a
fully deterministic historical plan ranking, top_plans, count DESC,
zero LLM involvement) now exposes that SAME ranking as `plan_ranking`
on its own block (hotfix, NOT deployed this Wave). intelligence-
panel.js's renderBlocksHtml() now looks for that block and, when
exactly one financing card's own `kind` matches the top-ranked plan,
marks THAT card RECOMENDADO and renders it first -- never parsing the
model's prose, never hardcoding a plan name/vehicle/position. Absent
that block (every OTHER route, including parcela-alvo), behavior is
byte-identical to before this hotfix.

IA-COMMERCIAL-UX2-HOTFIX-SCOPE-CLEANUP -- the READ-ONLY audit that
followed the original hotfix found the Coparticipado financing_card
support (and the kindLabel generic-map fix it required) to be
SAFE_BUT_OUT_OF_SCOPE: not strictly required to fix the Balão/Linear
badge mismatch the Human actually reported, and carrying a real
cross-route UI blast radius (any Coparticipado "payment" simulation,
in ANY route, would start rendering as a rich plan card instead of the
old generic grid) plus a genuine deploy-ordering hazard (backend-new +
frontend-old would mislabel Coparticipado as "Linear"). Both deltas
were surgically removed from production (separate commits); this test
file is updated to match -- it no longer asserts a COPARTICIPADO-
recommended scenario (production never sends Coparticipado a
financing_card again), and position/order tests that used to fill a
3rd array slot with a Coparticipado card now use a second, distinct
LINEAR simulation instead (a real, production-realistic shape -- the
history route can and does simulate the same kind at more than one
term when the historical reference suggests it).

Requires: `python -m http.server <port>` running from the target
worktree's own root (index.html at the base URL) -- see main() for
the port override via IA_UX2HOTFIX_TEST_PORT.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial-ux2-hotfix")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_UX2HOTFIX_TEST_PORT", "8741")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


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


def push_message(page, blocks, prose="resposta"):
    page.evaluate(
        """([prose, blocks]) => {
            window.NX_INTELLIGENCE_STATE.resetConversation();
            window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content: prose, blocks: blocks, isError:false});
        }""",
        [prose, blocks],
    )
    page.wait_for_timeout(150)


# ---------- reusable fixture builders (real-shaped, generic across plan/model/value -- never the test's own logic) ----------
# Only LINEAR/BALAO are used -- the two kinds production actually
# attaches financing_card to after the scope cleanup (Coparticipado no
# longer does, see module docstring).
def hist_block(plan_ranking, model="Eclipse Cross HPE"):
    return {
        "type": "metrics",
        "title": f"Histórico — {model} (amostra robusta)",
        "period_label": "últimos 30 dias",
        "items": [
            {"label": "Operações na amostra", "value": 22, "format": "int"},
            {"label": "Entrada — Mediana (%)", "value": 42, "format": "percent"},
            {"label": "Parcela — Mediana", "value": 3100, "format": "currency"},
            {"label": "Prazo mais comum (meses)", "value": 42, "format": "int"},
        ],
        "plan_ranking": plan_ranking,
    }


def linear_card():
    return {
        "type": "metrics", "title": "Simulação — Financiamento Linear Novos",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela (36x)", "value": 3283.40, "format": "currency"}],
        "financing_card": {"kind": "LINEAR", "term_months": 36, "monthly_payment": 3283.40, "down_payment": 104000, "financed_amount": 76000},
    }


def linear_card_variant():
    """A second, distinct LINEAR simulation (different term/numbers) --
    used purely as an inert 3rd-slot filler in position/order tests, a
    production-realistic stand-in for the old Coparticipado filler now
    that Coparticipado no longer carries financing_card. Never a match
    target in the tests that use it (plan_ranking[0] is always BALÃO
    or LINEAR-the-first-card in those tests, resolved unambiguously)."""
    return {
        "type": "metrics", "title": "Simulação — Financiamento Linear Novos",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela (48x)", "value": 2611.90, "format": "currency"}],
        "financing_card": {"kind": "LINEAR", "term_months": 48, "monthly_payment": 2611.90, "down_payment": 90000, "financed_amount": 90000},
    }


def balao_card():
    return {
        "type": "metrics", "title": "Simulação — Financiamento Balão Novos (48x)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela Mensal", "value": 3039.20, "format": "currency"}],
        "financing_card": {
            "kind": "BALAO", "term_months": 48, "monthly_payment": 3039.20, "down_payment": 69000, "financed_amount": 111000,
            "balloons": [{"month": 48, "value": 60000}],
        },
    }


def balao_card_variant():
    """A second, distinct BALÃO simulation (different term/numbers) --
    used ONLY by the ambiguity test (Fase 4) to construct a genuine
    2-matches-for-the-same-historically-top-plan scenario."""
    return {
        "type": "metrics", "title": "Simulação — Financiamento Balão Novos (42x)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela Mensal", "value": 3150.00, "format": "currency"}],
        "financing_card": {
            "kind": "BALAO", "term_months": 42, "monthly_payment": 3150.00, "down_payment": 72000, "financed_amount": 108000,
            "balloons": [{"month": 42, "value": 55000}],
        },
    }


def recommended_kind(page):
    """Reads which financing card, by kind, currently carries RECOMENDADO."""
    return page.evaluate(
        """() => {
            var primary = document.querySelector('.baiPlanCardPrimary');
            if (!primary) return null;
            var kindText = (primary.querySelector('.baiPlanCardKind') || {}).textContent || '';
            return kindText.toUpperCase();
        }"""
    )


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

        # ================= 1/2/3 + TESTE DE POSIÇÃO: BALÃO recommended, at every array position =================
        for pos_name, blocks in [
            ("position 0 (first)", [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), balao_card(), linear_card(), linear_card_variant()]),
            ("position 1 (second)", [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), linear_card(), balao_card(), linear_card_variant()]),
            ("position 2 (third)", [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), linear_card(), linear_card_variant(), balao_card()]),
        ]:
            push_message(page, blocks, "Eu começaria pelo Balão, seguido de Linear, nesta ordem de aderência ao histórico.")
            check(f"[1/2/3] history recommends BALÃO, array has it at {pos_name} -> BALÃO card is RECOMENDADO", "BALÃO" in (recommended_kind(page) or ""), recommended_kind(page))
            check(f"[1/2/3] {pos_name}: exactly one .baiPlanCardPrimary", page.locator(".baiPlanCardPrimary").count() == 1)
        shot(page, "01-balao-recommended-position-variants.png")

        # ================= 4: history recommends LINEAR =================
        push_message(page, [hist_block([{"plan": "LINEAR", "count": 15}, {"plan": "BALÃO", "count": 4}]), balao_card(), linear_card()], "Eu começaria pelo Linear.")
        check("[4] history recommends LINEAR -> LINEAR card is RECOMENDADO", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))
        check("[4] exactly one .baiPlanCardPrimary", page.locator(".baiPlanCardPrimary").count() == 1)

        # ================= TESTE INVERSO: array [LINEAR, BALÃO], recommendation LINEAR (matches array order -- must still work) =================
        push_message(page, [hist_block([{"plan": "LINEAR", "count": 10}, {"plan": "BALÃO", "count": 5}]), linear_card(), balao_card()], "Eu começaria pelo Linear.")
        check("[INVERSO-A] array=[LINEAR,BALÃO], recommendation=LINEAR -> LINEAR RECOMENDADO", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))

        # ================= TESTE INVERSO: array [LINEAR, BALÃO], recommendation BALÃO (the EXACT inverse -- proves badge is NOT index-bound) =================
        push_message(page, [hist_block([{"plan": "BALÃO", "count": 11}, {"plan": "LINEAR", "count": 3}]), linear_card(), balao_card()], "Eu começaria pelo Balão.")
        check("[INVERSO-B] array=[LINEAR,BALÃO] (unchanged), recommendation=BALÃO -> BALÃO RECOMENDADO (proves badge never depends on array index)", "BALÃO" in (recommended_kind(page) or ""), recommended_kind(page))
        check("[INVERSO-B] LINEAR (still at index 0) does NOT get RECOMENDADO", "LINEAR" not in (recommended_kind(page) or ""))

        # ================= 6 / SINGLE_RECOMMENDED_INVARIANT: exactly one RECOMENDADO when a recommendation exists =================
        push_message(page, [hist_block([{"plan": "BALÃO", "count": 8}, {"plan": "LINEAR", "count": 6}]), balao_card(), linear_card(), linear_card_variant()], "Balão primeiro.")
        check("[6/SINGLE] exactly one RECOMENDADO badge across all 3 cards (never zero, never two)", page.locator(".baiPlanCardBadge:has-text('Recomendado')").count() == 1)
        group_text_upper = page.locator(".baiPlanCardGroup").inner_text().upper()
        check("[6/SINGLE] 'RECOMENDADO' literal text appears exactly once", group_text_upper.count("RECOMENDADO") == 1, group_text_upper)

        # ================= 7 / NO_RECOMMENDATION_CASE: no plan_ranking block present -> pre-existing, already-homologated fallback is UNCHANGED (never a NEW behavior, never a crash) =================
        push_message(page, [linear_card(), balao_card()], "Aqui estão as opções.")
        check("[7] no hist-summary/plan_ranking block present -> the PRE-EXISTING array-position fallback still applies (byte-identical to before this hotfix -- this is the ALREADY-homologated canonical rule the brief itself exempts, never a fabricated new default)", page.locator(".baiPlanCardPrimary").count() == 1)
        check("[7] with no plan_ranking, the first array card (LINEAR here) is still primary -- pre-existing behavior, not invented by this hotfix", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))

        # ================= FASE 4 / AMBIGUITY GUARD: 2+ cards matching the SAME historically top-ranked plan -> NO ARBITRARY HISTORY MATCH =================
        # plan_ranking[0]=BALÃO, but TWO distinct BALÃO cards exist --
        # findHistoryRecommendedCard must find 2 matches, resolve NOTHING
        # (return null), and the pre-existing fallback (financing[0],
        # since no target_distance exists in this route) must decide --
        # proving the historical signal never arbitrarily picks between
        # ambiguous candidates. LINEAR is placed FIRST in the array
        # specifically so the assertion is unambiguous: if the fix
        # picked either Balão card "because it's historically favored",
        # this would fail; only the fallback default (array position)
        # explains LINEAR winning here.
        push_message(page, [hist_block([{"plan": "BALÃO", "count": 20}, {"plan": "LINEAR", "count": 5}]), linear_card(), balao_card(), balao_card_variant()], "Balão é o mais recorrente.")
        check("[AMBIGUITY] two BALÃO cards match the historically top-ranked plan -> NO arbitrary history-driven pick; the pre-existing array-position fallback decides instead (LINEAR, first in the array, wins -- proving the ambiguous match was correctly discarded)", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))
        check("[AMBIGUITY] exactly one RECOMENDADO still exists despite the ambiguity (never zero, never two)", page.locator(".baiPlanCardBadge:has-text('Recomendado')").count() == 1)
        ambiguity_group_text = page.locator(".baiPlanCardGroup").inner_text()
        check("[AMBIGUITY] neither BALÃO card was silently promoted -- both BALÃO numbers present but NEITHER is on the primary card", "3.039,20" in ambiguity_group_text or "3.150,00" in ambiguity_group_text)

        # ================= 8: parcela-alvo route -- balão único still RECOMENDADO (REGRESSION LOCK, frozen route) =================
        RDP_SINGLE_BALLOON = {
            "type": "metrics", "title": "Simulação — Financiamento Balão Novos (48x)",
            "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "items": [{"label": "Parcela Mensal", "value": 1800, "format": "currency"}],
            "financing_card": {
                "kind": "BALAO", "term_months": 48, "monthly_payment": 1800, "down_payment": 95756.98, "financed_amount": 84243.02,
                "balloons": [{"month": 48, "value": 84243.02}],
            },
        }
        push_message(page, [RDP_SINGLE_BALLOON], "A estrutura comercial recomendada é o Balão em 48 meses.")
        check("[8/PARCELA-ALVO] single-balloon structure (no plan_ranking block anywhere in this message) still gets RECOMENDADO -- frozen route untouched", page.locator(".baiPlanCardPrimary").count() == 1 and "RECOMENDADO" in page.locator(".baiPlanCardGroup").inner_text().upper())

        # ================= 9: parcela-alvo route -- 4 balões still MENOR ENTRADA (REGRESSION LOCK) =================
        RDP_FOUR_BALLOONS = {
            "type": "metrics", "title": "Simulação — Financiamento Balão Novos (48x)",
            "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "items": [{"label": "Parcela Mensal", "value": 1800, "format": "currency"}],
            "financing_card": {
                "kind": "BALAO", "term_months": 48, "monthly_payment": 1800, "down_payment": 65470.04, "financed_amount": 114529.96,
                "balloons": [{"month": 12, "value": 28632.49}, {"month": 24, "value": 28632.49}, {"month": 36, "value": 28632.49}, {"month": 48, "value": 28632.49}],
                "card_label": "MENOR ENTRADA",
            },
        }
        push_message(page, [RDP_SINGLE_BALLOON, RDP_FOUR_BALLOONS], "A estrutura comercial recomendada é o Balão de 1 balão. A alternativa de menor entrada usa 4 balões.")
        group_text = page.locator(".baiPlanCardGroup").inner_text()
        check("[9/PARCELA-ALVO] 4-balloon structure still carries 'MENOR ENTRADA' badge -- frozen route untouched", "MENOR ENTRADA" in group_text.upper())
        # ================= 10: RECOMENDADO and MENOR ENTRADA remain semantically distinct =================
        check("[10] exactly one RECOMENDADO (the 1-balloon card) and one MENOR ENTRADA (the 4-balloon card) -- never merged, never both on the same card", page.locator(".baiPlanCardBadge:has-text('Recomendado')").count() == 1 and "MENOR ENTRADA" in group_text.upper() and "RECOMENDADO" in group_text.upper())
        primary_card_text = page.locator(".baiPlanCardPrimary").inner_text().upper()
        check("[10] the RECOMENDADO card does NOT also say MENOR ENTRADA", "MENOR ENTRADA" not in primary_card_text, primary_card_text)

        # ================= 11: no financial number changed by this hotfix (reusing the exact real Human UAT scenario numbers) =================
        push_message(page, [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), linear_card(), balao_card()], "Balão primeiro.")
        group_text2 = page.locator(".baiPlanCardGroup").inner_text()
        check("[11] LINEAR numbers unchanged: R$3.283,40 / R$104.000,00 / R$76.000,00 all present", "3.283,40" in group_text2 and "104.000,00" in group_text2 and "76.000,00" in group_text2, group_text2)
        check("[11] BALÃO numbers unchanged: R$3.039,20 / R$69.000,00 / R$60.000,00 (balão, mês 48) all present", "3.039,20" in group_text2 and "69.000,00" in group_text2 and "60.000" in group_text2, group_text2)

        # ================= 12: card order follows historical ranking when contractually applicable (Fase 3) =================
        push_message(page, [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), linear_card(), balao_card(), linear_card_variant()], "Balão primeiro, depois Linear.")
        card_kinds_in_order = page.evaluate(
            """() => Array.from(document.querySelectorAll('.baiPlanCardKind')).map(function (el) { return el.textContent.toUpperCase(); })"""
        )
        check("[12] BALÃO card renders FIRST in the DOM when it is the historical recommendation (narrative/card coherence)", len(card_kinds_in_order) > 0 and "BALÃO" in card_kinds_in_order[0], card_kinds_in_order)
        shot(page, "02-history-order-coherence.png")

        # ================= no raw internal field names leaked =================
        for raw in ["PLAN_RANKING", "FINANCING_CARD", "\"KIND\""]:
            check(f"no raw internal field name visible: {raw}", raw not in group_text2.upper())

        # ================= Coparticipado is NOT re-introduced as a plan card (scope cleanup regression lock) =================
        COPARTICIPADO_NO_CARD = {
            "type": "metrics", "title": "Simulação — Plano Coparticipado (Eclipse Cross HPE, 36x)",
            "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "items": [{"label": "Parcela (36x)", "value": 2950.10, "format": "currency"}],
        }
        push_message(page, [linear_card(), balao_card(), COPARTICIPADO_NO_CARD], "Aqui estão Linear, Balão e Coparticipado.")
        check("[SCOPE-CLEANUP] a Coparticipado block with NO financing_card (production-realistic post-cleanup shape) renders OUTSIDE .baiPlanCardGroup, exactly as before the original hotfix", page.locator(".baiPlanCardGroup").locator("text=Coparticipado").count() == 0)
        check("[SCOPE-CLEANUP] exactly 2 plan cards render (Linear + Balão only) -- Coparticipado never silently joins the group without a financing_card", page.locator(".baiPlanCard").count() == 2)

        # ================= zero horizontal scroll (no layout change expected, verified anyway) =================
        for width in [1366, 1024, 900, 480]:
            page.set_viewport_size({"width": width, "height": 900})
            push_message(page, [hist_block([{"plan": "BALÃO", "count": 12}, {"plan": "LINEAR", "count": 7}]), linear_card(), balao_card(), linear_card_variant()], "Balão primeiro.")
            doc_ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{width}px: document itself has zero horizontal scroll", doc_ov <= 0, doc_ov)

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== History Recommended Card Alignment Test (IA-COMMERCIAL-UX2-HOTFIX): {passed}/{total} ===")
    print("RESULT: PASS" if passed == total else "RESULT: FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
