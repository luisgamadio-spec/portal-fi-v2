#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3J.4C -- Financing plan cards test.

Real Human UAT ("continua confuso... precisamos separar em cards para
entender do que se trata cada plano") traced to compactMetricsHtml
(intelligence-panel.js) rendering a metrics block's own title as
screen-reader-only -- correct for a block whose title just repeats the
prose above it, wrong for a financing recommendation, where the title
is the ONLY thing distinguishing a Balão card from a Linear card.

This suite proves the fix: portal-ai-homolog's buildBalaoMetricsBlock/
buildSimulationMetricsBlock (IA-3J.4C) now attach a `financing_card`
metadata object to exactly these two block shapes; intelligence-
panel.js's new renderBlocksHtml()/financingPlanCardHtml() render them
as distinct, visibly-labeled cards instead of the generic anonymous
metric grid -- while every OTHER metrics block (Score, Comissões,
Resultado, etc.) keeps using compactMetricsHtml completely unchanged.

Uses the exact real Human scenario numbers (Eclipse HPE 0km,
R$180.000, entrada R$90.000, meta R$1.800) already proven against the
real engine in IA-3J.4A/4B: Balão 30x/R$1.766,94/2 balões (meses 15 e
30) selected over Linear's own best 60x/R$2.984,38.

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-3j4c")
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


# ---------- the exact real Human scenario, real engine numbers (IA-3J.4A/4B) ----------
BALAO_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Financiamento Balão Novos (30x) — prazo e balão determinados automaticamente (mais próximo da parcela-alvo)",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Valor do Veículo", "value": 180000, "format": "currency"},
        {"label": "Entrada", "value": 90000, "format": "currency"},
        {"label": "Entrada (%)", "value": 50, "format": "percent"},
        {"label": "Financiado", "value": 90000, "format": "currency"},
        {"label": "Parcela Mensal", "value": 1766.94, "format": "currency"},
        {"label": "Balão 1 (mês 15)", "value": 45000, "format": "currency"},
        {"label": "Balão 2 (mês 30)", "value": 45000, "format": "currency"},
        {"label": "Total em balões (2)", "value": 90000, "format": "currency"},
        {"label": "Parcela-alvo informada", "value": 1800, "format": "currency"},
    ],
    "financing_card": {
        "kind": "BALAO", "term_months": 30, "monthly_payment": 1766.94,
        "down_payment": 90000, "financed_amount": 90000,
        "balloons": [{"month": 15, "value": 45000}, {"month": 30, "value": 45000}],
        "target_payment": 1800, "target_distance": 33.06,
    },
}
LINEAR_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Financiamento Linear Novos",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Valor do Veículo", "value": 180000, "format": "currency"},
        {"label": "Entrada", "value": 90000, "format": "currency"},
        {"label": "Entrada (%)", "value": 50, "format": "percent"},
        {"label": "Financiado", "value": 90000, "format": "currency"},
        {"label": "Melhor parcela (60x)", "value": 2984.38, "format": "currency"},
    ],
    "financing_card": {
        "kind": "LINEAR", "term_months": 60, "monthly_payment": 2984.38,
        "down_payment": 90000, "financed_amount": 90000,
        "target_payment": 1800, "target_distance": 1184.38,
    },
}
RECOMMEND_PROSE = "Recomendo o Balão em 30 meses. A parcela fica em R$ 1.766,94, apenas R$ 33,06 abaixo da meta. O Linear mais próximo ainda fica em R$ 2.984,38."


def push_financing_message(page, blocks, prose=RECOMMEND_PROSE):
    page.evaluate(
        """([prose, blocks]) => {
            window.NX_INTELLIGENCE_STATE.resetConversation();
            window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content: prose, blocks: blocks, isError:false});
        }""",
        [prose, blocks],
    )
    page.wait_for_timeout(150)


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

        # ---------- A/B/C/D: two distinct, visibly-labeled plan cards ----------
        # NOTE: .baiPlanCardKind/.baiPlanFactLabel both carry an
        # intentional text-transform:uppercase (matching the existing
        # .baiBlockTitle/.baiMetricFactLabel/.baiRankMetricLabel visual
        # convention elsewhere in this file/CSS, and the brief's own
        # worked example, which shows "BALÃO · 30 MESES" in caps) --
        # Playwright's inner_text() returns the RENDERED (post-CSS-
        # transform) text, so label/kind assertions below compare
        # case-insensitively, exactly like intelligence-panel-test.py's
        # own established convention for the same class of element.
        push_financing_message(page, [BALAO_BLOCK, LINEAR_BLOCK])
        cards = page.locator(".baiPlanCard")
        check("two plan cards render (Balão + Linear)", cards.count() == 2)
        group_text = page.locator(".baiPlanCardGroup").inner_text()
        group_text_upper = group_text.upper()
        check("plan type visible: 'Balão'", "BALÃO" in group_text_upper)
        check("plan type visible: 'Linear'", "LINEAR" in group_text_upper)
        check("Balão term visible (30 meses)", "30" in group_text_upper and "MESES" in group_text_upper)
        linear_section = group_text_upper.split("LINEAR")[-1] if "LINEAR" in group_text_upper else ""
        check("Linear term visible (60 meses)", "60" in linear_section and "MESES" in linear_section)
        check("Balão hero payment visible (R$ 1.766,94)", "1.766,94" in group_text or "1766,94" in group_text)
        check("Linear hero payment visible (R$ 2.984,38)", "2.984,38" in group_text or "2984,38" in group_text)
        shot(page, "01-two-plan-cards.png")

        # ---------- E/F: recommendation marking ----------
        primary = page.locator(".baiPlanCardPrimary")
        secondary = page.locator(".baiPlanCardSecondary")
        check("exactly one card marked primary (recommended)", primary.count() == 1)
        check("exactly one card marked secondary", secondary.count() == 1)
        primary_text_upper = primary.inner_text().upper()
        secondary_text_upper = secondary.inner_text().upper()
        check("the PRIMARY card is the Balão one (closer to target: R$33,06 < R$1.184,38)", "BALÃO" in primary_text_upper)
        check("the SECONDARY card is the Linear one", "LINEAR" in secondary_text_upper)
        check("'Recomendado' badge appears on the primary card", "RECOMENDADO" in primary_text_upper)
        check("'Recomendado' badge does NOT appear on the secondary card", "RECOMENDADO" not in secondary_text_upper)

        # ---------- G: accurate balloon schedule ----------
        check("Balão 1 month visible (mês 15)", "MÊS 15" in group_text_upper)
        check("Balão 2 month visible (mês 30)", "MÊS 30" in group_text_upper)
        check("both balloon values visible (R$ 45.000 each)", group_text.count("45.000") >= 2 or group_text.count("45000") >= 2)

        # ---------- H: no anonymous adjacent metric grid for these blocks ----------
        check("financing blocks do NOT use the generic .baiCompactMetrics treatment", page.locator(".baiPlanCardGroup .baiCompactMetrics").count() == 0)

        # ---------- I: no raw internal field names visible ----------
        group_text_upper = group_text.upper()
        for raw in ["FINANCING_CARD", "TARGET_DISTANCE", "MONTHLY_PAYMENT", "DOWN_PAYMENT", "TERM_MONTHS", "\"KIND\""]:
            check(f"raw internal field name not visible: {raw}", raw not in group_text_upper)

        # ---------- distance/target fact ----------
        check("target/distance fact shown on the primary card", "META" in primary_text_upper)

        # ---------- J: default remains compact (no comparison table alongside) ----------
        check("no ranking/comparison table rendered by default alongside the cards", page.locator(".baiAnswerMetrics table").count() == 0)
        check("prose is not duplicated inside the card group itself", "Recomendo o Balão" not in group_text)

        # ---------- single-plan case (no comparison needed) ----------
        push_financing_message(page, [BALAO_BLOCK], prose="Balão em 30 meses.")
        check("a single financing block still renders as a plan card (not the old anonymous grid)", page.locator(".baiPlanCard").count() == 1)
        check("a lone card still gets marked primary/recommended (nothing to be secondary to, but still the answer)", page.locator(".baiPlanCardPrimary").count() == 1)

        # ---------- regression: non-financing metrics blocks totally unaffected ----------
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
        check("non-financing metrics block still uses the OLD compact/anonymous treatment (no plan card, unaffected)", page.locator(".baiPlanCard").count() == 0 and page.locator(".baiCompactMetrics").count() == 1)

        # ---------- K: responsive / zero horizontal scroll ----------
        for width in [1366, 1024, 900, 480]:
            page.set_viewport_size({"width": width, "height": 900})
            push_financing_message(page, [BALAO_BLOCK, LINEAR_BLOCK])
            ov = true_overflow(page)
            check(f"{width}px: no true viewport overflow from plan cards", ov["worst"] <= 0.5, ov)
            doc_ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{width}px: document itself has zero horizontal scroll", doc_ov <= 0, doc_ov)
            shot(page, f"02-responsive-{width}.png")

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Financing Plan Cards Test (IA-3J.4C): {passed}/{total} ===")
    print("RESULT: PASS" if passed == total else "RESULT: FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
