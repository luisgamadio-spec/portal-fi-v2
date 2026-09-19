#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-COMMERCIAL4-E2 -- adapter block-type contract fix, real Human
payload regression.

COMMERCIAL4-E's own runtime trace proved the backend, the financial
engine, buildCommercialAlternativeGroupBlock, and the V2 group
renderer all correct. The Human then captured the REAL server
response body for Human UAT #1 (instrumented fetch interception, not
a screenshot) and ran the REAL, deployed adapter's own
validateBlock/normalizeResponse against it: `commercial_alternative`
(COMMERCIAL4-B) and `commercial_alternative_group` (COMMERCIAL4-D)
were never added to brabus-intelligence.adapter.js's BLOCK_TYPES
whitelist when those Waves shipped -- every one of THEIR OWN test
suites drove the renderer directly via
NX_INTELLIGENCE_STATE.pushMessage(), bypassing this adapter's
normalizeResponse() entirely, so the gap stayed invisible until a
real fetch response went through it. validateBlock() rejected the
unrecognized type; normalizeResponse()'s own .filter(validateBlock)
silently zeroed `blocks` to null -- reply text intact, structured
card gone, zero console output. This is the file COMMERCIAL4-E2's own
final report refers to for the full real-payload regression.

This test:
  - reproduces the EXACT real Human-captured payload shape (Phase 9);
  - proves malformed/unknown blocks are still rejected post-fix,
    never a "accept everything" weakening (Phase 7/8);
  - proves the console.warn observability fix fires with the
    rejected type only, no payload dump (Phase 6);
  - drives the REAL end-to-end pipeline: adapter.normalizeResponse()
    (previously bypassed by every COMMERCIAL4-B/D/D2 test) -> real
    pushMessage -> real renderConversation -> real DOM (Phase 10-12);
  - checks responsive/zero-horizontal-scroll at 1366/1024/900/480,
    legibility at 480 (Phase 16).

Requires: `python -m http.server 8700` running from a directory whose
child is literally named `portal-next-v2` (same convention as
tests/intelligence-contract-test.py) -- override via
IA_COMMERCIAL4E2_TEST_PORT if a different port is already serving
that layout.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-commercial4e2")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA_COMMERCIAL4E2_TEST_PORT", "8700")
HARNESS_URL = f"http://localhost:{PORT}/portal-next-v2/tests/fixtures/_brabus-intelligence-harness.html"
APP_URL = f"http://localhost:{PORT}/portal-next-v2/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


# The EXACT real Human-captured payload shape for Human UAT #1 (4
# rate options for 36 months, ELIGIBLE, real installment/entry/
# financed/rebate/final-sale-value fields per option).
def real_raw_server_response():
    return {
        "reply": "Encontrei 4 condições de Taxas Subsidiadas válidas para 36 meses. A escolha da taxa é do vendedor/gerente.",
        "blocks": [{
            "type": "commercial_alternative_group",
            "kind": "SUBSIDIADO",
            "label": "OPÇÕES COMERCIAIS",
            "title": "Taxas Subsidiadas — 36 meses",
            "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "eligibility": {"status": "ELIGIBLE", "reason": "Entrada acima de 50% e condição encontrada na tabela oficial de Taxas Subsidiadas (Novos)."},
            "options": [
                {"label": "0% a.m.", "items": [
                    {"label": "Parcela (36x)", "value": 1894.38, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 25.54, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 15324, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 134676, "format": "currency"},
                ]},
                {"label": "0,49% a.m.", "items": [
                    {"label": "Parcela (36x)", "value": 2071.25, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 18.60, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 11160, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 138840, "format": "currency"},
                ]},
                {"label": "0,99% a.m.", "items": [
                    {"label": "Parcela (36x)", "value": 2261.25, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 8.25, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 4950, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 145050, "format": "currency"},
                ]},
                {"label": "1,19% a.m.", "items": [
                    {"label": "Parcela (36x)", "value": 2340.00, "format": "currency"},
                    {"label": "Entrada", "value": 90000, "format": "currency"},
                    {"label": "Financiado", "value": 60000, "format": "currency"},
                    {"label": "Rebate (%)", "value": 8.02, "format": "percent"},
                    {"label": "Rebate (R$)", "value": 4812, "format": "currency"},
                    {"label": "Valor Final de Venda", "value": 145188, "format": "currency"},
                ]},
            ],
        }],
        "request_id": "req-uat1-real",
        "scenario_reset": False,
        # homolog-only debug metadata -- must never survive normalizeResponse.
        "_homolog_debug": {"tools_used": ["simular_financiamento"], "tool_call_count": 1, "calls": [{"name": "simular_financiamento", "args": {"financing_type": "TAXAS_SUBSIDIADAS"}, "result": {}}]},
        "_homolog_edge_timing": {"latency_ms": 8180},
    }


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


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= PART A: adapter contract, harness-only (Phase 6/7/8/9) =================
        page = browser.new_page()
        console_warnings = []
        page.on("console", lambda m: console_warnings.append(m.text) if m.type == "warning" else None)
        page.goto(HARNESS_URL)

        raw = real_raw_server_response()

        # Phase 9 -- exact real payload structure.
        is_valid = page.evaluate("(b) => window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock(b)", raw["blocks"][0])
        check("[Phase 9] validateBlock(real Human UAT #1 group payload) === true", is_valid is True)

        normalized = page.evaluate("(payload) => window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse(payload)", raw)
        check("[Phase 9/10] normalizeResponse(real payload).blocks.length === 1", isinstance(normalized.get("blocks"), list) and len(normalized["blocks"]) == 1)
        check("[Phase 9/10] normalized block type === commercial_alternative_group", normalized["blocks"][0]["type"] == "commercial_alternative_group" if normalized.get("blocks") else False)
        check("[Phase 9] normalized block preserves all 4 options", len(normalized["blocks"][0]["options"]) == 4 if normalized.get("blocks") else False)
        check("[Phase 9] _homolog_debug stripped by normalizeResponse (never reaches the renderer)", "_homolog_debug" not in normalized)
        check("[Phase 9] reply text passes through unmodified", normalized.get("reply") == raw["reply"])

        # Phase 7 -- unknown types must still be rejected.
        console_warnings.clear()
        unknown_valid = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock({type: '__unknown_test_block__'})")
        page.wait_for_timeout(50)
        check("[Phase 7] validateBlock rejects a genuinely unknown type", unknown_valid is False)
        check("[Phase 7] normalizeResponse excludes the unknown-type block", page.evaluate("() => window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply:'x', blocks:[{type:'__unknown_test_block__'}]}).blocks") is None)
        check("[Phase 6/7] console.warn fired with the rejected type for the unknown block", any("__unknown_test_block__" in w for w in console_warnings))
        check("[Phase 6] console.warn does NOT dump the whole block/payload (no 'Entrada'/'90000' leak)", not any("90000" in w or "Entrada" in w for w in console_warnings))

        # Phase 8 -- malformed commercial_alternative_group variants must still be rejected.
        malformed_cases = [
            ("missing options entirely", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "label": "x"}),
            ("options is not an array", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "options": "not-an-array"}),
            ("options is an empty array", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "options": []}),
            ("option missing items", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "options": [{"label": "0%"}]}),
            ("option items missing label", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "options": [{"label": "0%", "items": [{"value": 1, "format": "currency"}]}]}),
            ("option items empty array", {"type": "commercial_alternative_group", "kind": "SUBSIDIADO", "options": [{"label": "0%", "items": []}]}),
            ("missing kind", {"type": "commercial_alternative_group", "options": [{"label": "0%", "items": [{"label": "Entrada", "value": 1, "format": "currency"}]}]}),
        ]
        for label, block in malformed_cases:
            console_warnings.clear()
            ok = page.evaluate("(b) => window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock(b)", block)
            page.wait_for_timeout(30)
            check(f"[Phase 8] malformed group rejected -- {label}", ok is False)
            check(f"[Phase 8] malformed group discard logged a warning -- {label}", len(console_warnings) >= 1)

        # Phase 5 -- single commercial_alternative validation (real COMMERCIAL4-B contract).
        real_single = {
            "type": "commercial_alternative", "kind": "COPARTICIPADO", "label": "OPÇÃO COMERCIAL",
            "title": "Coparticipado — ECLIPSE CROSS HPE (36x)", "period_label": "Simulação — não é proposta nem aprovação de crédito",
            "eligibility": {"status": "ELIGIBLE", "reason": "Modelo encontrado na matriz oficial."},
            "items": [{"label": "Entrada", "value": 111000, "format": "currency"}, {"label": "Parcela (36x)", "value": 2409.41, "format": "currency"}],
        }
        check("[Phase 5] validateBlock accepts the real COMMERCIAL4-B commercial_alternative contract", page.evaluate("(b) => window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock(b)", real_single) is True)
        check("[Phase 5] malformed commercial_alternative (missing items) is rejected", page.evaluate("() => window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock({type:'commercial_alternative', kind:'COPARTICIPADO'})") is False)

        page.close()

        # ================= PART B: real end-to-end pipeline through the actual app (Phase 10-12, 16, 18) =================
        page2 = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page2.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page2.on("pageerror", lambda e: errors.append(str(e)))
        page2.goto(APP_URL + "#/landing")
        page2.wait_for_timeout(600)
        set_profile(page2, "AUTHORIZED", True, "MASTER")
        open_panel(page2)

        # This is the critical difference from every prior COMMERCIAL4-B/D/
        # D2 frontend test: those called S.pushMessage() directly with a
        # hand-built block, bypassing the adapter entirely. This drives the
        # REAL adapter.normalizeResponse() first -- the exact stage proven
        # to have silently discarded the block in production -- then feeds
        # its own real output into pushMessage, closing that gap.
        page2.evaluate(
            """(raw) => {
                var normalized = window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse(raw);
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content: normalized.reply, blocks: normalized.blocks, isError:false});
            }""",
            real_raw_server_response(),
        )
        page2.wait_for_timeout(200)

        check("[Phase 10] panel receives the group (.baiCommercialAltCard present)", page2.locator(".baiCommercialAltCard").count() == 1)
        check("[Phase 10] badge is 'OPÇÕES COMERCIAIS'", page2.locator(".baiCommercialAltBadge").inner_text().strip().upper() == "OPÇÕES COMERCIAIS")
        check("[Phase 10] title 'Taxas Subsidiadas — 36 meses' visible", "36 meses" in page2.locator(".baiCommercialAltTitle").inner_text())
        check("[Phase 10] four option sections rendered", page2.locator(".baiCommercialAltOption").count() == 4)

        card_text = page2.locator(".baiCommercialAltCard").inner_text()
        card_text_upper = card_text.upper()
        check("[Phase 11] TAXA visible per option (rate labels 0%/0,49%/0,99%/1,19%)", all(r in card_text for r in ["0% a.m.", "0,49% a.m.", "0,99% a.m.", "1,19% a.m."]))
        check("[Phase 11] PARCELA visible per option", card_text_upper.count("PARCELA") == 4)
        check("[Phase 11] ENTRADA visible per option", card_text_upper.count("ENTRADA") == 4)
        check("[Phase 11] FINANCIADO visible per option", card_text_upper.count("FINANCIADO") == 4)
        check("[Phase 11] REBATE visible per option (rate % + R$ labels, 2 per option)", card_text_upper.count("REBATE") == 8)
        check("[Phase 11] VALOR FINAL DE VENDA visible per option", card_text_upper.count("VALOR FINAL DE VENDA") == 4)

        check("[Phase 12] no RECOMENDADO badge anywhere on the card", "RECOMENDADO" not in card_text_upper)
        check("[Phase 12] zero .baiPlanCardPrimary (never absorbed into primary recommendation)", page2.locator(".baiPlanCardPrimary").count() == 0)
        check("[Phase 12] no winner language ('melhor'/'recomendada'/'recomendo')", not any(w in card_text.lower() for w in ["melhor opção", "mais recomendada", "eu recomendo esta taxa"]))
        check("[Phase 12] no legacy ranking cards present (.baiRankCard absent)", page2.locator(".baiRankCard").count() == 0)

        page2.screenshot(path=os.path.join(SHOT_DIR, "01-real-payload-through-real-adapter.png"))

        # ================= Phase 16: responsive =================
        for w in (1366, 1024, 900, 480):
            page2.set_viewport_size({"width": w, "height": 900})
            page2.wait_for_timeout(120)
            overflow = page2.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"[Phase 16] {w}px: zero horizontal scroll", overflow <= 0, overflow)
            check(f"[Phase 16] {w}px: all 4 option sections still present", page2.locator(".baiCommercialAltOption").count() == 4)
            page2.screenshot(path=os.path.join(SHOT_DIR, f"02-responsive-{w}.png"))
        check("[Phase 16] 480px legibility: rebate (R$) value visible", "15.324" in page2.locator(".baiCommercialAltCard").inner_text())
        check("[Phase 16] 480px legibility: valor final de venda visible", "134.676" in page2.locator(".baiCommercialAltCard").inner_text())
        page2.set_viewport_size({"width": 1366, "height": 900})

        real_errors = [e for e in errors if "favicon" not in e.lower() and "Failed to load resource: the server responded with a status of 404" not in e]
        check("[sanity] no unexplained console/page errors across the real-pipeline flow", len(real_errors) == 0, real_errors)

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Commercial4-E2 Adapter Real-Payload Regression: {passed}/{total} ===")
    print("RESULT: " + ("PASS" if passed == total else "FAIL"))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
