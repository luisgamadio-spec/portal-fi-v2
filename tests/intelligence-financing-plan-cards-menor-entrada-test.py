#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL-UX2 -- Minimum-entry card label rendering test.

Real Human UAT (v84) defect: portal-ai-homolog (IA-COMMERCIAL-UX1)
already attaches an optional, presentation-only `financing_card.card_label`
("MENOR ENTRADA") to the real, materially-cheaper unconstrained
alternative it exposes alongside the commercial-tier RECOMENDADO --
but intelligence-panel.js's own financingPlanCardHtml() never read
that field at all (only `isPrimary`, which governs the "Recomendado"
badge), so the fourth card rendered as plain "BALÃO · 48 MESES",
visually indistinguishable from every other alternative.

This suite proves the fix: financingPlanCardHtml() now renders
fc.card_label verbatim (reusing the EXACT same .baiPlanCardBadge
visual language already used for "Recomendado", never a new class),
strictly when the card is NOT the primary/recommended one -- and
proves, via the SAME test run against the pre-fix commit on a
separate port, that the defect genuinely reproduces there (Missão
anti-false-green).

Requires: `python -m http.server <port>` running from the target
worktree's own root (index.html at the base URL) -- see main() for
the port and BASE_URL override via IA_UX2_TEST_PORT.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial-ux2")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_UX2_TEST_PORT", "8722")
# When set, this run is checking the PRE-FIX baseline: the card_label
# badge is expected to be ABSENT, and this script inverts its own
# pass/fail interpretation for exactly that one assertion group
# instead of treating it as a hard failure of the suite -- see
# EXPECT_FIX below.
EXPECT_FIX = os.environ.get("IA_UX2_EXPECT_FIX", "1") == "1"
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


# ---------- real-shaped payload: RECOMENDADO (1 balão) + ALTERNATIVA (antecipado, no card_label)
# + ALTERNATIVA_MENOR_ENTRADA (4 balões, card_label="MENOR ENTRADA") ----------
# Numbers are the REAL Eclipse Cross HPE Human UAT scenario
# (R$180.000/target R$1.800/48 meses) exactly as portal-ai-homolog
# actually computes and returns -- never invented for this test.
RECOMENDADO_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Financiamento Balão Novos (48x)",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Valor do Veículo", "value": 180000, "format": "currency"},
        {"label": "Entrada", "value": 95756.98, "format": "currency"},
        {"label": "Financiado", "value": 84243.02, "format": "currency"},
        {"label": "Parcela Mensal", "value": 1800, "format": "currency"},
        {"label": "Balão (mês 48)", "value": 84243.02, "format": "currency"},
    ],
    "financing_card": {
        "kind": "BALAO", "term_months": 48, "monthly_payment": 1800,
        "down_payment": 95756.98, "financed_amount": 84243.02,
        "balloons": [{"month": 48, "value": 84243.02}],
    },
}
LINEAR_ALTERNATIVE_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Entrada necessária (Balão Novos)",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Valor do Veículo", "value": 180000, "format": "currency"},
        {"label": "Entrada necessária (60x)", "value": 88000, "format": "currency"},
    ],
    "financing_card": {
        "kind": "LINEAR", "term_months": 60, "monthly_payment": 1800,
        "down_payment": 88000, "financed_amount": 92000,
    },
}
MENOR_ENTRADA_BLOCK = {
    "type": "metrics",
    "title": "Simulação — Financiamento Balão Novos (48x)",
    "period_label": "Simulação — não é proposta nem aprovação de crédito",
    "items": [
        {"label": "Valor do Veículo", "value": 180000, "format": "currency"},
        {"label": "Entrada", "value": 65470.04, "format": "currency"},
        {"label": "Financiado", "value": 114529.96, "format": "currency"},
        {"label": "Parcela Mensal", "value": 1800, "format": "currency"},
    ],
    "financing_card": {
        "kind": "BALAO", "term_months": 48, "monthly_payment": 1800,
        "down_payment": 65470.04, "financed_amount": 114529.96,
        "balloons": [
            {"month": 12, "value": 28632.49}, {"month": 24, "value": 28632.49},
            {"month": 36, "value": 28632.49}, {"month": 48, "value": 28632.49},
        ],
        "card_label": "MENOR ENTRADA",
    },
}
RECOMMEND_PROSE = "A estrutura comercial recomendada é o Balão em 48 meses com 1 balão final. Também mostro a estrutura de menor entrada matemática, com 4 balões."


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

        # ---------- the real 3-card payload (RECOMENDADO + plain ALTERNATIVA + ALTERNATIVA_MENOR_ENTRADA) ----------
        push_financing_message(page, [RECOMENDADO_BLOCK, LINEAR_ALTERNATIVE_BLOCK, MENOR_ENTRADA_BLOCK])
        cards = page.locator(".baiPlanCard")
        check("three plan cards render (RECOMENDADO + ALTERNATIVA + MENOR ENTRADA)", cards.count() == 3)
        shot(page, "01-three-cards.png")

        primary = page.locator(".baiPlanCardPrimary")
        secondary = page.locator(".baiPlanCardSecondary")
        check("exactly one card marked primary (recommended)", primary.count() == 1)
        check("exactly two cards marked secondary", secondary.count() == 2)

        # ---------- THE Missão: card_label reaches the rendered DOM ----------
        card_texts_upper = [cards.nth(i).inner_text().upper() for i in range(cards.count())]
        menor_entrada_cards = [t for t in card_texts_upper if "MENOR ENTRADA" in t]
        check("[MISSÃO] 'MENOR ENTRADA' appears on exactly one rendered card (financing_card.card_label reaches the DOM)", len(menor_entrada_cards) == 1, card_texts_upper)

        if len(menor_entrada_cards) == 1:
            menor_entrada_text = menor_entrada_cards[0]
            other_texts = [t for t in card_texts_upper if t != menor_entrada_text]
            # ---------- 1. RECOMENDADO permanece no cartão recomendado ----------
            check("1. 'RECOMENDADO' still appears on exactly one card (the primary one)", sum(1 for t in card_texts_upper if "RECOMENDADO" in t) == 1)
            recommended_text = primary.inner_text().upper()
            check("1b. the RECOMENDADO card is the correct one (1 balão final, R$95.756,98)", "95.756,98" in recommended_text or "95756,98" in recommended_text)
            # ---------- 2. MENOR ENTRADA não aparece nos cartões lineares ----------
            linear_card_texts = [t for t in card_texts_upper if "LINEAR" in t]
            check("2. 'MENOR ENTRADA' does not appear on the LINEAR alternative card (no card_label was attached to it)", all("MENOR ENTRADA" not in t for t in linear_card_texts), linear_card_texts)
            # ---------- 3. MENOR ENTRADA não substitui RECOMENDADO ----------
            check("3. the card showing 'MENOR ENTRADA' does NOT also show 'RECOMENDADO'", "RECOMENDADO" not in menor_entrada_text, menor_entrada_text)
            check("3b. the card showing 'MENOR ENTRADA' is NOT the primary/recommended card (still a secondary card)", menor_entrada_text != recommended_text)

        # ---------- 4. cartão sem card_label mantém comportamento anterior ----------
        push_financing_message(page, [RECOMENDADO_BLOCK, LINEAR_ALTERNATIVE_BLOCK])
        cards2 = page.locator(".baiPlanCard")
        check("4. a 2-card response with NO card_label anywhere renders exactly as before (zero visual change)", cards2.count() == 2)
        for i in range(cards2.count()):
            t = cards2.nth(i).inner_text().upper()
            check(f"4b. card {i} (no card_label) never shows 'MENOR ENTRADA'", "MENOR ENTRADA" not in t)
        primary2 = page.locator(".baiPlanCardPrimary")
        check("4c. historical single-badge behavior unchanged: exactly one primary/Recomendado card", primary2.count() == 1 and "RECOMENDADO" in primary2.inner_text().upper())

        # ---------- 5. números permanecem byte-idênticos ----------
        push_financing_message(page, [RECOMENDADO_BLOCK, LINEAR_ALTERNATIVE_BLOCK, MENOR_ENTRADA_BLOCK])
        group_text = page.locator(".baiPlanCardGroup").inner_text()
        check("5. RECOMENDADO down_payment number unchanged (R$95.756,98)", "95.756,98" in group_text or "95756,98" in group_text)
        check("5b. MENOR ENTRADA down_payment number unchanged (R$65.470,04)", "65.470,04" in group_text or "65470,04" in group_text)
        check("5c. all four MENOR ENTRADA balloon values present (R$28.632,49 x4)", group_text.count("28.632,49") + group_text.count("28632,49") >= 4)

        # ---------- 6. ordem dos cartões permanece igual (array order preserved) ----------
        kinds_in_order = []
        for i in range(cards.count()):
            t = cards.nth(i).inner_text().upper()
            if "RECOMENDADO" in t:
                kinds_in_order.append("RECOMENDADO")
            elif "MENOR ENTRADA" in t:
                kinds_in_order.append("MENOR_ENTRADA")
            else:
                kinds_in_order.append("PLAIN")
        check("6. card order is RECOMENDADO, then plain ALTERNATIVA, then MENOR ENTRADA (array order preserved, unchanged by this Wave)", kinds_in_order == ["RECOMENDADO", "PLAIN", "MENOR_ENTRADA"], kinds_in_order)

        # ---------- 7. nenhum cálculo é executado pelo renderer para descobrir o selo ----------
        # Source-level proof, against the LOCAL worktree's own current
        # file (this check is about the source this test file ships
        # alongside, independent of which port is under test) --
        # financingPlanCardHtml's own badgeHtml assignment reads
        # fc.card_label as a plain string, never a hardcoded number/
        # term/count/index comparison to infer which card is "menor
        # entrada".
        js_path = os.path.join(V2_ROOT, "assets", "js", "intelligence", "intelligence-panel.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_source = f.read()
        fn_start = js_source.find("function financingPlanCardHtml(")
        fn_end = js_source.find("\n  }\n", fn_start)
        fn_body = js_source[fn_start:fn_end] if fn_start != -1 and fn_end != -1 else ""
        badge_assignment_start = fn_body.find("var badgeHtml")
        badge_assignment = fn_body[badge_assignment_start:badge_assignment_start + 400] if badge_assignment_start != -1 else ""
        check("7. the badge is driven by fc.card_label, read as a plain string (source invariant)", "fc.card_label" in badge_assignment, badge_assignment)
        hardcoded_markers = ["65470", "28632", "95756", "84243", "=== 4", "== 4", "term_months === 48", "balloons.length ==="]
        check("7b. the badge assignment never hardcodes a specific entrada/balloon-count/term value (no number-comparison-based detection)",
              badge_assignment_start != -1 and not any(m in badge_assignment for m in hardcoded_markers), badge_assignment)

        # ---------- I: no raw internal field name visible ----------
        for raw in ["CARD_LABEL", "FINANCING_CARD"]:
            check(f"no raw internal field name visible: {raw}", raw not in group_text.upper() or raw == "MENOR ENTRADA")

        # ---------- responsive / zero horizontal scroll ----------
        for width in [1366, 1024, 900, 480]:
            page.set_viewport_size({"width": width, "height": 900})
            push_financing_message(page, [RECOMENDADO_BLOCK, LINEAR_ALTERNATIVE_BLOCK, MENOR_ENTRADA_BLOCK])
            ov = true_overflow(page)
            check(f"{width}px: no true viewport overflow with the 3-card group", ov["worst"] <= 0.5, ov)
            doc_ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{width}px: document itself has zero horizontal scroll", doc_ov <= 0, doc_ov)
            shot(page, f"02-responsive-{width}.png")

        unexplained = [e for e in errors if "Failed to load resource" not in e]
        check("no unexplained console/page errors across the whole flow", len(unexplained) == 0, unexplained)

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Financing Plan Cards — Menor Entrada Label Test (IA-COMMERCIAL-UX2): {passed}/{total} ===")
    print(f"EXPECT_FIX={EXPECT_FIX} (informational -- this script always reports the true PASS/FAIL count; the caller decides how to interpret an anti-false-green run)")
    print("RESULT: PASS" if passed == total else "RESULT: FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
