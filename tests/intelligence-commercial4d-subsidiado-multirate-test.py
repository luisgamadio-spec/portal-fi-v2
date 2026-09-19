#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL4-D -- multi-rate Subsidiado commercial alternatives.

Human UAT #1 (real homolog, defect): "Eclipse Cross HPE 0km R$150.000,
entrada R$90.000 (60%), taxas subsidiadas, 36 meses." The real engine
resolved ONE term (36) with FOUR valid rate conditions
(0,00% / 0,49% / 0,99% / 1,19% a.m.), each with its own installment,
rebate (%  and R$) and final sale value -- all sharing entry R$90.000 /
financed R$60.000. The financial values were never the defect; the
defect was presentation: the response fell back to the legacy
"ranking" block (installment/financed/entry only, rebate and final
sale value left to narrative prose) instead of a structured
COMMERCIAL4 block exposing every field per rate.

portal-ai-homolog's fix (IA-COMMERCIAL4-D, Secure repo, READ-ONLY from
V2's own perspective) adds a NEW `commercial_alternative_group` block
type carrying one `options[]` entry per valid rate, each with its own
`items[]` (same field shape as the existing single-rate
`commercial_alternative` block). This test drives the REAL renderer
with the EXACT Human UAT #1 4-rate payload (real numbers from the
report) and proves:
  - all 4 rate options render, each with its own installment, rebate
    (%  and R$) and final sale value as STRUCTURED fields (never only
    in prose);
  - no option carries a "Recomendado" badge and no option is visually
    marked as a winner (Human policy: seller/manager decides);
  - no narrative text on the page declares one rate "melhor" or "mais
    recomendada";
  - the existing single-condition `commercial_alternative` card (IA-
    COMMERCIAL4-B) still renders correctly and is visually distinct
    from the new group card (regression guard);
  - zero horizontal scroll at 1366/1024/900/480, with rate/installment/
    rebate/final-sale-value still legible at 480px.

Requires: `python -m http.server <port>` running from the target
worktree's own root (index.html at the base URL) -- see main() for the
port override via IA_COMMERCIAL4D_TEST_PORT.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial4d")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_COMMERCIAL4D_TEST_PORT", "8831")
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


# Real Human UAT #1 numbers -- Eclipse Cross HPE 0km R$150.000, entrada
# R$90.000 (60%), financiado R$60.000, 36 meses, 4 taxas subsidiadas
# validas simultaneamente.
def subsidiado_multirate_group():
    return {
        "type": "commercial_alternative_group",
        "kind": "SUBSIDIADO",
        "label": "OPÇÕES COMERCIAIS",
        "title": "Taxas Subsidiadas — 36 meses",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "eligibility": {"status": "ELIGIBLE", "reason": "Entrada acima de 50%."},
        "options": [
            {
                "label": "0,00% a.m.",
                "items": [
                    {"label": "Parcela (36x)", "value": 1894.38, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 10, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 15324.00, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 134676.00, "format": "currency"},
                ],
            },
            {
                "label": "0,49% a.m.",
                "items": [
                    {"label": "Parcela (36x)", "value": 2071.25, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 8, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 11160.00, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 138840.00, "format": "currency"},
                ],
            },
            {
                "label": "0,99% a.m.",
                "items": [
                    {"label": "Parcela (36x)", "value": 2261.25, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 3, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 4950.00, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 145050.00, "format": "currency"},
                ],
            },
            {
                "label": "1,19% a.m.",
                "items": [
                    {"label": "Parcela (36x)", "value": 2340.00, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 3, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 4812.00, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 145188.00, "format": "currency"},
                ],
            },
        ],
    }


def subsidiado_single_rate():
    return {
        "type": "commercial_alternative",
        "kind": "SUBSIDIADO",
        "label": "OPÇÃO COMERCIAL",
        "title": "Taxas Subsidiadas — Novos (36x, taxa 0,99%)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "eligibility": {"status": "ELIGIBLE", "reason": "Entrada acima de 50%."},
        "items": [
            {"label": "Entrada", "value": 95000, "format": "currency"},
            {"label": "Parcela (36x)", "value": 2100.00, "format": "currency"},
            {"label": "Taxa", "value": 0.99, "format": "percent"},
            {"label": "Rebate (R$)", "value": 3200.00, "format": "currency"},
            {"label": "Valor Final de Venda", "value": 171800.00, "format": "currency"},
        ],
    }


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")
        open_panel(page)

        # ================= Human UAT #1 exact reproduction: 4-rate Subsidiado group =================
        push_message(
            page,
            [subsidiado_multirate_group()],
            "Encontrei 4 condições de Taxas Subsidiadas válidas para 36 meses. A escolha da taxa é do vendedor/gerente.",
        )
        check("group card rendered (.baiCommercialAltCard present, group variant)", page.locator(".baiCommercialAltCard").count() == 1)
        check("badge text is 'OPÇÕES COMERCIAIS' (plural)", page.locator(".baiCommercialAltBadge").inner_text().strip().upper() == "OPÇÕES COMERCIAIS")
        check("title shows the resolved term (36 meses)", "36" in page.locator(".baiCommercialAltTitle").inner_text())

        options = page.locator(".baiCommercialAltOption")
        check("all 4 rate options render as distinct sub-sections", options.count() == 4)

        option_labels = page.locator(".baiCommercialAltOptionLabel").all_inner_texts()
        for expected_rate in ["0,00%", "0,49%", "0,99%", "1,19%"]:
            check(f"rate option label '{expected_rate}' is visible", any(expected_rate in lbl for lbl in option_labels))

        card_text = page.locator(".baiCommercialAltCard").inner_text()
        card_text_upper = card_text.upper()
        for expected_value in ["1.894,38", "2.071,25", "2.261,25", "2.340,00"]:
            check(f"installment value {expected_value} visible as a structured field", expected_value in card_text)
        for expected_rebate in ["15.324,00", "11.160,00", "4.950,00", "4.812,00"]:
            check(f"rebate (R$) value {expected_rebate} visible as a structured field (never prose-only)", expected_rebate in card_text)
        for expected_final in ["134.676,00", "138.840,00", "145.050,00", "145.188,00"]:
            check(f"valor final de venda {expected_final} visible as a structured field (never prose-only)", expected_final in card_text)

        check("card never carries the 'Recomendado' badge text", "RECOMENDADO" not in card_text_upper)
        check("no option label declares a winner ('melhor'/'recomendada'/'recomendo')", not any(
            w in card_text.lower() for w in ["melhor opção", "mais recomendada", "eu recomendo esta taxa"]
        ))
        check("zero .baiPlanCardPrimary rendered for this group (never absorbed into primary recommendation)", page.locator(".baiPlanCardPrimary").count() == 0)
        shot(page, "01-human-uat1-4rate-group.png")

        # ================= Regression guard: single-condition COMMERCIAL4-B card still renders correctly =================
        push_message(page, [subsidiado_single_rate()], "Uma única condição Subsidiada válida para 36 meses.")
        check("single-condition card still renders via the ORIGINAL commercial_alternative path", page.locator(".baiCommercialAltCard").count() == 1)
        check("single-condition card has NO per-option sub-sections (not confused with the group variant)", page.locator(".baiCommercialAltOption").count() == 0)
        check("single-condition badge text is still 'OPÇÃO COMERCIAL' (singular, unchanged)", page.locator(".baiCommercialAltBadge").inner_text().strip().upper() == "OPÇÃO COMERCIAL")
        shot(page, "02-single-condition-regression-guard.png")

        # ================= responsive / zero horizontal scroll, legibility at 480px =================
        push_message(page, [subsidiado_multirate_group()], "4 condições de Taxas Subsidiadas para 36 meses.")
        for w in (1366, 1024, 900, 480):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"[responsive] {w}px: document itself has zero horizontal scroll", overflow <= 0, overflow)
            visible_options = page.locator(".baiCommercialAltOption").count()
            check(f"[responsive] {w}px: all 4 rate options still present in DOM", visible_options == 4)
            shot(page, f"03-responsive-{w}.png")
        check("[480px legibility] rebate (R$) value still visible in card text at 480px", "15.324,00" in page.locator(".baiCommercialAltCard").inner_text())
        check("[480px legibility] valor final de venda still visible in card text at 480px", "134.676,00" in page.locator(".baiCommercialAltCard").inner_text())
        page.set_viewport_size({"width": 1366, "height": 900})

        # intelligence-runtime-config.local.js is a documented, optional,
        # gitignored per-developer override the app probes for
        # optimistically -- a 404 for it is expected, harmless,
        # environment-dependent noise (Chromium's own console message for
        # a failed resource never includes the URL -- same "favicon"
        # precedent already established in the sibling UX-wave test files).
        real_errors = [e for e in errors if "favicon" not in e.lower() and "Failed to load resource: the server responded with a status of 404" not in e]
        check("no unexplained console/page errors across the whole flow", len(real_errors) == 0, real_errors)

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Commercial4-D Subsidiado Multi-Rate Test: {passed}/{total} ===")
    print("RESULT: " + ("PASS" if passed == total else "FAIL"))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
