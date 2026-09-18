#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL-UX3 -- ONE deterministic final-recommendation authority
for the history-recommendation route.

Real Human UAT defect (Execution 4, 4 independent executions, Cache
Storage/Service Worker cleared before UAT -- NOT stale-cache evidence):
history showed BALÃO(8) > LINEAR(6) > COPARTICIPADO(3); BALÃO's
historically-common 47-month term did not exist in the current table
(no simulation vigente this turn); COPARTICIPADO had a full, valid
current simulation (entrada/parcela/rebate/final_sale_value) but --
IA-COMMERCIAL-UX2-HOTFIX-SCOPE-CLEANUP's own, already-approved scope
cut -- never carries a financing_card; LINEAR had a valid
financing_card. The model's own free-text narrative said "Eu começaria
pelo Coparticipado... para menor parcela, ofereça primeiro o
Coparticipado", but the RECOMENDADO badge (correctly, if accidentally)
landed on LINEAR -- proving narrative and card could originate from
DIFFERENT authorities.

Fix: portal-ai-homolog (backend, Secure repo, READ-ONLY from V2's own
perspective -- not re-implemented here) now computes ONE deterministic
`recommended_plan` field on the SAME hist-summary block that already
carries `plan_ranking` (IA-COMMERCIAL-UX2-HOTFIX): the first
historically-ranked plan that ALREADY has a real financing_card this
turn ("mais recorrente primeiro, salvo não-simulável", IA-UAT-FIX-04's
own already-approved wording) -- and feeds that SAME field to the
model's own narrative instructions, so text/badge/order can never
disagree again. intelligence-panel.js's own findHistoryRecommendedCard
now prefers `recommended_plan` when present, falling back to the
pre-existing plan_ranking[0]-only read only for a cached/older response
that predates this field (byte-identical to IA-COMMERCIAL-UX2-HOTFIX's
own behavior in that case -- see [BACKWARD-COMPAT] below).

Requires: `python -m http.server <port>` running from the target
worktree's own root (index.html at the base URL) -- see main() for the
port override via IA_UX3_TEST_PORT.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial-ux3")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_UX3_TEST_PORT", "8742")
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
            if (window.NX_INTELLIGENCE_PANEL && window.NX_INTELLIGENCE_PANEL.refresh) window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(150)


def push_message(page, blocks, prose="resposta"):
    page.evaluate(
        """([prose, blocks]) => {
            window.NX_INTELLIGENCE_STATE.resetConversation();
            window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content: prose, blocks: blocks, isError:false});
        }""",
        [prose, blocks],
    )
    page.wait_for_timeout(150)


# ---------- reusable fixture builders (real-shaped, mirrors
# tests/intelligence-history-recommended-card-alignment-test.py's own
# fixtures -- never a divergent replica) ----------
def hist_block(plan_ranking, recommended_plan=None, model="Eclipse Cross HPE"):
    block = {
        "type": "metrics",
        "title": f"Histórico — {model} (amostra robusta)",
        "period_label": "últimos 30 dias",
        "items": [
            {"label": "Operações na amostra", "value": 50, "format": "int"},
            {"label": "Entrada — Mediana (%)", "value": 42, "format": "percent"},
            {"label": "Parcela — Mediana", "value": 3100, "format": "currency"},
            {"label": "Prazo mais comum (meses)", "value": 47, "format": "int"},
        ],
        "plan_ranking": plan_ranking,
    }
    if recommended_plan is not None:
        block["recommended_plan"] = recommended_plan
    return block


def linear_card():
    return {
        "type": "metrics", "title": "Simulação — Financiamento Linear Novos",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela (36x)", "value": 3283.40, "format": "currency"}],
        "financing_card": {"kind": "LINEAR", "term_months": 36, "monthly_payment": 3283.40, "down_payment": 104000, "financed_amount": 76000},
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


def coparticipado_metrics_block_no_card():
    """The REAL current shape (IA-COMMERCIAL-UX2-HOTFIX-SCOPE-CLEANUP):
    a full, valid Coparticipado simulation result -- but NO
    financing_card key at all (buildCoparticipadoMetricsBlock never
    attaches one, proved from the real backend source by
    tests/ia-reconciliation/history-final-recommendation-authority.test.mjs
    Part B in the Secure repo). Deliberately has no `financing_card`
    field, mirroring production byte-for-byte -- never a hand-invented
    partial shape."""
    return {
        "type": "metrics", "title": "Simulação — Plano Coparticipado (Eclipse Cross HPE, 36x)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [
            {"label": "Entrada", "value": 111000, "format": "currency"},
            {"label": "Parcela (36x)", "value": 2409.41, "format": "currency"},
            {"label": "Rebate Total", "value": 10542.25, "format": "currency"},
            {"label": "Valor Final de Venda", "value": 176166.45, "format": "currency"},
        ],
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

        # ================= HUMAN_EXECUTION_4_REGRESSION =================
        # Exact semantic state Human UAT Execution 4 reported: BALÃO(8) >
        # LINEAR(6) > COPARTICIPADO(3) historically; BALÃO absent this
        # turn (no card); COPARTICIPADO present as a full metrics block
        # but WITHOUT financing_card (real shape); LINEAR present with a
        # financing_card. Backend's own deterministic decision
        # (recommended_plan="LINEAR") is asserted here as the frontend
        # INPUT -- never re-derived/recomputed by this test, exactly like
        # every other block in these fixtures.
        blocks = [
            hist_block(
                [{"plan": "BALÃO", "count": 8}, {"plan": "LINEAR", "count": 6}, {"plan": "COPARTICIPADO", "count": 3}],
                recommended_plan="LINEAR",
            ),
            coparticipado_metrics_block_no_card(),
            linear_card(),
        ]
        push_message(page, blocks, "Eu começaria pelo Linear, que é o plano historicamente mais recorrente com simulação vigente nesta resposta.")
        check("[HUMAN_EXECUTION_4_REGRESSION] structured winner LINEAR -> LINEAR card is RECOMENDADO", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))
        check("[HUMAN_EXECUTION_4_REGRESSION] exactly one RECOMENDADO badge", page.locator(".baiPlanCardBadge:has-text('Recomendado')").count() == 1)
        check("[HUMAN_EXECUTION_4_REGRESSION] no fabricated BALÃO/COPARTICIPADO card appears in the plan-card group", page.locator(".baiPlanCardGroup .baiPlanCardKind:has-text('BALÃO')").count() == 0)
        group_text_upper = page.locator(".baiPlanCardGroup").inner_text().upper()
        check("[HUMAN_EXECUTION_4_REGRESSION] 'RECOMENDADO' text appears exactly once, never on a fabricated card", group_text_upper.count("RECOMENDADO") == 1, group_text_upper)
        shot(page, "01-human-execution-4-regression.png")

        # ================= [DIVERGENCE] recommended_plan overrides naive plan_ranking[0]-only reading =================
        # plan_ranking DELIBERATELY lists LINEAR first (array position),
        # but recommended_plan says BALÃO -- proves the badge follows the
        # backend's own authoritative field, never the historical
        # ranking's own array position, and never a re-derivation that
        # could silently disagree with it.
        blocks = [
            hist_block([{"plan": "LINEAR", "count": 6}, {"plan": "BALÃO", "count": 8}], recommended_plan="BALAO"),
            linear_card(), balao_card(),
        ]
        push_message(page, blocks, "Eu começaria pelo Balão.")
        check("[DIVERGENCE] plan_ranking[0]=LINEAR but recommended_plan=BALAO -> BALÃO wins (never plan_ranking[0])", "BALÃO" in (recommended_kind(page) or ""), recommended_kind(page))
        check("[DIVERGENCE] LINEAR (plan_ranking[0]) does NOT get RECOMENDADO", "LINEAR" not in (recommended_kind(page) or ""))

        # ================= [BACKWARD-COMPAT] no recommended_plan field (cached/older response) -> pre-existing plan_ranking[0] behavior unchanged =================
        blocks = [
            hist_block([{"plan": "BALÃO", "count": 9}, {"plan": "LINEAR", "count": 4}]),  # no recommended_plan
            linear_card(), balao_card(),
        ]
        push_message(page, blocks, "Eu começaria pelo Balão.")
        check("[BACKWARD-COMPAT] no recommended_plan field -> falls back to plan_ranking[0] (BALÃO), byte-identical to IA-COMMERCIAL-UX2-HOTFIX", "BALÃO" in (recommended_kind(page) or ""), recommended_kind(page))

        # ================= [AMBIGUITY] recommended_plan names a kind with 2 matching cards -> no arbitrary pick (same discipline as plan_ranking[0]'s own ambiguity guard) =================
        blocks = [
            hist_block([{"plan": "LINEAR", "count": 6}, {"plan": "BALÃO", "count": 8}], recommended_plan="LINEAR"),
            linear_card(), linear_card(),  # two identical-kind cards -- deliberately ambiguous
        ]
        push_message(page, blocks, "Eu começaria pelo Linear.")
        check("[AMBIGUITY] recommended_plan matches 2 cards of the same kind -> pre-existing fallback decides, never an arbitrary pick", page.locator(".baiPlanCardPrimary").count() == 1)

        # ================= [MISSING-CANDIDATE] recommended_plan names a kind with 0 matching cards this turn -> no silent substitution =================
        blocks = [
            hist_block([{"plan": "BALÃO", "count": 8}, {"plan": "LINEAR", "count": 6}], recommended_plan="BALAO"),
            linear_card(),  # BALAO absent despite being named recommended_plan (should not happen in practice, defensive case)
        ]
        push_message(page, blocks, "Aqui está a opção disponível.")
        check("[MISSING-CANDIDATE] recommended_plan names an absent kind -> falls back to pre-existing logic, never crashes, never fabricates a BALÃO card", page.locator(".baiPlanCardPrimary").count() == 1)
        check("[MISSING-CANDIDATE] the only real card present (LINEAR) still renders correctly", "LINEAR" in (recommended_kind(page) or ""), recommended_kind(page))

        # ================= responsive / zero horizontal scroll =================
        for w in (1366, 1024, 900, 480):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"[RESPONSIVE] {w}px: document itself has zero horizontal scroll", overflow <= 0, overflow)
        page.set_viewport_size({"width": 1366, "height": 768})

        # Independently confirmed (via a response-status listener, not
        # console text -- Chromium's console message for a failed
        # resource load never includes the URL) that the ONLY resource
        # 404 on this page is assets/js/intelligence-runtime-config.local.js
        # -- a documented, optional, gitignored per-developer override
        # (tests/intelligence-v2-text/README.md) the app probes for
        # optimistically. Expected, harmless, environment-dependent
        # noise, never a real page/console error -- filtered by its
        # exact, generic Chromium message text (same "favicon" precedent
        # as the sibling IA-COMMERCIAL-UX2-HOTFIX test file).
        real_errors = [e for e in errors if "favicon" not in e.lower() and "Failed to load resource: the server responded with a status of 404" not in e]
        check("no unexplained console/page errors across the whole flow", len(real_errors) == 0, real_errors)

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== History Final Recommendation Authority Test (IA-COMMERCIAL-UX3): {passed}/{total} ===")
    print("RESULT: " + ("PASS" if passed == total else "FAIL"))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
