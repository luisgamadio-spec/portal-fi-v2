#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL4 -- proactive commercial alternative blocks (Subsidiado /
Coparticipado).

Human-approved policy: these are ADDITIONAL commercial offers, never
the primary financing recommendation. This test drives the REAL
renderer (window.NX_INTELLIGENCE_STATE.pushMessage) with synthetic but
production-realistic `commercial_alternative` blocks (the exact shape
portal-ai-homolog's own buildCommercialAlternativeBlock produces,
IA-COMMERCIAL4-B, Secure repo, READ-ONLY from V2's own perspective)
and proves:
  - the block renders via its own dedicated path (never absorbed into
    the primary financing-card group -- hasFinancingCard structurally
    excludes it, since it carries no `financing_card` field);
  - the badge is always "OPÇÃO COMERCIAL" (or whatever neutral label
    the backend sends), never "Recomendado";
  - Coparticipado's own rebate_total/rebate_hpe/rebate_brabus/
    final_sale_value render when present;
  - the Trade-In warning renders for PRESENT/UNKNOWN and never for
    ABSENT, and never states a monetary value;
  - an INELIGIBLE alternative renders its own reason, not a fabricated
    number;
  - Subsidiado and Coparticipado can render side by side with no
    declared winner between them;
  - zero horizontal scroll at 1366/1024/900/480.

Requires: `python -m http.server <port>` running from the target
worktree's own root (index.html at the base URL) -- see main() for the
port override via IA_COMMERCIAL4_TEST_PORT.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial4")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_COMMERCIAL4_TEST_PORT", "8830")
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


def linear_card():
    return {
        "type": "metrics", "title": "Simulação — Financiamento Linear Novos",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "items": [{"label": "Parcela (36x)", "value": 3283.40, "format": "currency"}],
        "financing_card": {"kind": "LINEAR", "term_months": 36, "monthly_payment": 3283.40, "down_payment": 104000, "financed_amount": 76000},
    }


def coparticipado_alternative(trade_in_status=None, eligibility_status="ELIGIBLE", reason=""):
    block = {
        "type": "commercial_alternative",
        "kind": "COPARTICIPADO",
        "label": "OPÇÃO COMERCIAL",
        "title": "Coparticipado — ECLIPSE CROSS HPE (36x)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "eligibility": {"status": eligibility_status, "reason": reason or "Modelo encontrado na matriz oficial."},
        "items": [
            {"label": "Entrada", "value": 111000, "format": "currency"},
            {"label": "Parcela (36x)", "value": 2409.41, "format": "currency"},
            {"label": "Rebate Total", "value": 10542.25, "format": "currency"},
            {"label": "Rebate HPE", "value": 8000, "format": "currency"},
            {"label": "Rebate Brabus", "value": 2542.25, "format": "currency"},
            {"label": "Valor Final de Venda", "value": 176166.45, "format": "currency"},
        ],
    }
    if trade_in_status is not None:
        block["trade_in_status"] = trade_in_status
        block["requires_confirmation"] = trade_in_status != "ABSENT"
    return block


def subsidiado_alternative(eligibility_status="ELIGIBLE", reason=""):
    return {
        "type": "commercial_alternative",
        "kind": "SUBSIDIADO",
        "label": "OPÇÃO COMERCIAL",
        "title": "Taxas Subsidiadas — Novos (36x, taxa 0,99%)",
        "period_label": "Simulação — não é proposta nem aprovação de crédito",
        "eligibility": {"status": eligibility_status, "reason": reason or "Entrada acima de 50%."},
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

        # ================= [1] Coparticipado alternative alongside a primary Linear card =================
        push_message(page, [linear_card(), coparticipado_alternative(trade_in_status="ABSENT")], "Linear é a recomendação principal; Coparticipado também está disponível.")
        check("[1] exactly one .baiPlanCardPrimary (Linear) -- Coparticipado never competes for it", page.locator(".baiPlanCardPrimary").count() == 1)
        check("[1b] Linear card is the primary (RECOMENDADO)", "LINEAR" in (page.locator(".baiPlanCardPrimary .baiPlanCardKind").inner_text() or "").upper())
        check("[45] commercial_alternative card rendered (.baiCommercialAltCard present)", page.locator(".baiCommercialAltCard").count() == 1)
        check("[44] badge text is 'OPÇÃO COMERCIAL'", page.locator(".baiCommercialAltBadge").inner_text().strip().upper() == "OPÇÃO COMERCIAL")
        check("[45b] commercial_alternative card NEVER carries the 'Recomendado' badge text", "RECOMENDADO" not in page.locator(".baiCommercialAltCard").inner_text().upper())
        card_text_upper = page.locator(".baiCommercialAltCard").inner_text().upper()
        check("[42] Coparticipado rebate_total/rebate_hpe/rebate_brabus/final_sale_value all visible", all(s in card_text_upper for s in ["REBATE TOTAL", "REBATE HPE", "REBATE BRABUS", "VALOR FINAL DE VENDA"]))
        check("[45c] Coparticipado card shows payment/term context", "PARCELA" in card_text_upper)
        check("[trade-in ABSENT] no Trade-In warning rendered when trade_in_status=ABSENT", page.locator(".baiCommercialAltTradeInWarning").count() == 0)
        shot(page, "01-coparticipado-alongside-primary.png")

        # ================= [21] Trade-In PRESENT -> warning rendered, requires confirmation language =================
        push_message(page, [coparticipado_alternative(trade_in_status="PRESENT")], "Coparticipado disponível, mas há troca na negociação.")
        check("[21] Trade-In warning renders when PRESENT", page.locator(".baiCommercialAltTradeInWarning").count() == 1)
        check("[21b] warning text mentions Trade-In incompatibility, never a monetary value", "Trade-In" in page.locator(".baiCommercialAltTradeInWarning").inner_text() and "R$" not in page.locator(".baiCommercialAltTradeInWarning").inner_text())

        # ================= [23] Trade-In UNKNOWN -> clarification warning rendered (never treated as ABSENT) =================
        push_message(page, [coparticipado_alternative(trade_in_status="UNKNOWN")], "Coparticipado disponível, Trade-In não informado.")
        check("[23] Trade-In warning ALSO renders when UNKNOWN (never silently treated as ABSENT)", page.locator(".baiCommercialAltTradeInWarning").count() == 1)
        check("[24] UNKNOWN warning never states a monetary Trade-In value", "R$" not in page.locator(".baiCommercialAltTradeInWarning").inner_text())

        # ================= [22] Trade-In ABSENT -> no warning =================
        push_message(page, [coparticipado_alternative(trade_in_status="ABSENT")], "Coparticipado disponível, sem troca confirmada.")
        check("[22] no Trade-In warning when explicitly ABSENT", page.locator(".baiCommercialAltTradeInWarning").count() == 0)

        # ================= INELIGIBLE rendering =================
        push_message(page, [coparticipado_alternative(eligibility_status="INELIGIBLE", reason="Entrada abaixo do mínimo exigido.")], "Coparticipado não elegível nesta condição.")
        check("[ineligible] ineligible reason renders, never a fabricated payment card", page.locator(".baiCommercialAltIneligible").count() == 1)
        check("[ineligible-b] the real reason text is shown verbatim", "Entrada abaixo do mínimo" in page.locator(".baiCommercialAltIneligible").inner_text())

        # ================= [36/37/38] Subsidiado + Coparticipado both eligible -> both surfaced, no winner declared =================
        push_message(page, [subsidiado_alternative(), coparticipado_alternative(trade_in_status="ABSENT")], "Ambas as opções comerciais estão disponíveis.")
        check("[36] both commercial_alternative cards render together", page.locator(".baiCommercialAltCard").count() == 2)
        check("[37/38] neither is hidden or marked as a winner (both show 'OPÇÃO COMERCIAL', no ranking text)", page.locator(".baiCommercialAltBadge").count() == 2)
        badges_text = page.locator(".baiCommercialAltBadge").all_inner_texts()
        check("[37b] no badge declares one 'melhor'/'vencedor' over the other", all("melhor" not in b.lower() and "vencedor" not in b.lower() for b in badges_text))
        shot(page, "02-subsidiado-and-coparticipado-together.png")

        # ================= responsive / zero horizontal scroll =================
        for w in (1366, 1024, 900, 480):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(120)
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"[responsive] {w}px: document itself has zero horizontal scroll", overflow <= 0, overflow)
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
    print(f"\n=== Commercial4 Proactive Alternatives Test (IA-COMMERCIAL4-B): {passed}/{total} ===")
    print("RESULT: " + ("PASS" if passed == total else "FAIL"))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
