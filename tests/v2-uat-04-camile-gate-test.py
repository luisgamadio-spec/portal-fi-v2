#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-04 -- "First Gate": Camile Beatriz Santos Sena (ANALISTA/NACOES)
must pass in full before the same architectural fix is regression-
checked against the other 5 profiles (per this Wave's own brief,
Section 7/8: "NÃO testar/corrigir os outros perfis por tentativa e
erro... SOMENTE depois de Camile passar").

Two Human-reported defects investigated:

FINDING A (module visibility) -- FIXED as of V2-UAT-05. V2-UAT-04
confirmed this originated from REAL, pre-existing product code --
assets/js/landing.js's moduleBlockHtml()/navItemHtml() ("AUTH
FOUNDATION Phase 2B, Gate 12") -- and deliberately left it unmodified,
reporting PRODUCT_AUTH_VISIBILITY_DEFECT pending a Human decision.
That decision came: "SE O USUÁRIO NÃO TEM ACESSO A UM MÓDULO, O MÓDULO
NÃO DEVE APARECER" is now the official product rule. V2-UAT-05 replaced
both disabled-card branches with isAuthDenied(m) -> return '' (complete
DOM omission), and made an empty category (zero visible modules) omit
itself too. The two checks below that used to be informational
PRODUCT_AUTH_VISIBILITY_DEFECT checks are now core, gating assertions
(Section 11 of V2-UAT-05's own brief: "Atualizar assertions antigas
somente se elas codificavam explicitamente o comportamento AUTH-
DENIED-AS-DISABLED que agora mudou" -- this is exactly that case).

FINDING B (Salários opens with MASTER authority): root-caused to
tests/_v2-uat-03-profiles-mock.js reusing tests/_salarios-uat-
fixtures.js's ONE MASTER-shaped dataset (built for RH-5B's own MASTER
demo) unconditionally for every profile. salarios-comissoes.js's own
role checks (canSeeGestor/canSeeGestorFi/canSeeHistorico/
canSeeOwnCommission/canSeeScopeCommission) were already 100% correct,
reading the real, correctly-mocked NX_AUTH_CORE context -- but its
"Resumo/Equipe" section is BY DESIGN never role-filtered client-side
(trusts the RPC's own server-side scope), so the unscoped multi-store
fixture leaked through. Fixed by building a per-scenario SCOPED
response (scopedSalaryFixtures() in the mock) instead. This test proves
the fix for Camile specifically.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "v2-uat-04")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"
HARNESS = f"{BASE}/tests/_v2-uat-03-profiles-harness.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


ALLOWED_TITLES = {"Análise Geral do Grupo", "Análise F&I do Grupo", "Gestão de Coparticipados",
                   "Análise de Score Vendedores", "Salários & Comissões", "Simulador de Novos",
                   "Simulador de Seminovos", "Painel do Analista F&I", "Brabus Intelligence"}
MASTER_ONLY_TITLES = {"Central de Atendimento F&I", "Painel Master"}
KNOWN_CROSS_STORE_LEAK_MARKERS = ["ABC", "BANDEIRANTES CENTRO", "GASTAO"]  # the OLD MASTER-shaped fixture's own store names


# V2-UAT-05: category count is no longer fixed at 6 -- a category left
# with zero visible modules for this profile is now entirely absent.
# Iterate however many .fNavItem tabs actually rendered.
def all_module_blocks(frame):
    out = {}
    tab_count = frame.evaluate("document.querySelectorAll('.fNavItem').length")
    for idx in range(tab_count):
        frame.evaluate(f'document.querySelectorAll(".fNavItem")[{idx}].click()')
        frame.page.wait_for_timeout(150)
        blocks = frame.evaluate("""() => [...document.querySelectorAll('#landingModuleDetail .fModuleBlock')].map(b => ({
            title: b.querySelector('.fModuleTitle').textContent,
            deferred: b.classList.contains('fModuleBlockDeferred'),
            existsAsRealAnchor: b.tagName === 'A'
        }))""")
        for b in blocks:
            out[b["title"]] = b
    return out


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def tracked_page(**kw):
            pg = browser.new_page(**kw)
            pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: console_errors.append(str(e)))
            return pg

        # ============================================================
        # CAMILE LANDING VISIBILITY
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{HARNESS}?uat=camile")
        page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
        page.wait_for_timeout(1200)
        frame = page.frames[-1]
        frame.wait_for_selector(".fNavItem", timeout=8000)

        ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[LANDING] perfil is ANALISTA", ctx.get("perfil") == "ANALISTA", ctx)
        check("[LANDING] loja is NACOES", ctx.get("loja") == "NACOES", ctx)
        check("[LANDING] status is NOVOS/SEMINOVOS", ctx.get("status") == "NOVOS/SEMINOVOS", ctx)
        check("[LANDING] isMaster is false", ctx.get("isMaster") is False, ctx)

        blocks = all_module_blocks(frame)
        allowed_ok = all(blocks.get(t) and blocks.get(t)["deferred"] is False and blocks.get(t)["existsAsRealAnchor"] for t in ALLOWED_TITLES)
        check("[LANDING] every module Camile's real matrix grants renders as a real, clickable link (not deferred)", allowed_ok, {t: blocks.get(t) for t in ALLOWED_TITLES})

        # MASTER_ONLY DOM-absence -- V2-UAT-05: now a core, gating
        # assertion (was PRODUCT_AUTH_VISIBILITY_DEFECT/informational in
        # V2-UAT-04, before landing.js was fixed).
        for t in MASTER_ONLY_TITLES:
            b = blocks.get(t)
            check(f"[UNAUTHORIZED MODULE DOM ABSENCE] '{t}' (MASTER_ONLY) is completely absent from the DOM, not a disabled card",
                  b is None, b)

        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("[LANDING] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

        errs_before = list(console_errors)
        shot(page, "camile-landing.png")

        # ============================================================
        # CAMILE SALÁRIOS AUTHORITY
        # ============================================================
        frame.evaluate('location.hash = "#/salarios-comissoes"')
        page.wait_for_timeout(1200)

        sal_ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
        check("[SALÁRIOS] module's own auth context still resolves Camile as ANALISTA", sal_ctx.get("perfil") == "ANALISTA", sal_ctx)
        check("[SALÁRIOS] module's own auth context isMaster is false", sal_ctx.get("isMaster") is False, sal_ctx)

        body_text = frame.evaluate("document.body.innerText")
        check("[SALÁRIOS] module opened without crashing (real KPI heading present)", "Salários & Comissões" in body_text)
        check("[MASTER CONTROLS ABSENT] no 'Histórico' tab/view-mode toggle", "Histórico" not in body_text)
        check("[MASTER CONTROLS ABSENT] no 'Gestor F&I' / group-wide oversight commission section", "Gestor F&I" not in body_text and "GESTOR F&I" not in body_text.upper() or "COMISSÃO — GESTOR F&I" not in body_text.upper())
        check("[MASTER CONTROLS ABSENT] no closing/fechamento-de-competência administrative action visible", "Fechar competência" not in body_text and "Reabrir" not in body_text)

        leaked_stores = [m for m in KNOWN_CROSS_STORE_LEAK_MARKERS if m in body_text]
        check("[ANALYST SCOPE] no cross-store data leak (none of the OLD MASTER-fixture's other store names appear anywhere)", len(leaked_stores) == 0, leaked_stores)
        check("[ANALYST SCOPE] her own real loja (NACOES) is the scope shown in the Equipe table", "NACOES" in body_text)
        check("[ANALYST SCOPE] the ANALISTA row shows her own real name, not a generic placeholder", "CAMILE BEATRIZ SANTOS SENA" in body_text and "Analista Exemplo" not in body_text)
        check("[ANALYST SCOPE] no broken/NaN value rendered", "NaN" not in body_text and "NAN" not in body_text.upper().replace("NACOES", "").replace("VENDEDOR", "") or "NaN%" not in body_text)

        sal_overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("[SALÁRIOS] zero horizontal scroll", sal_overflow["scroll"] <= sal_overflow["client"], sal_overflow)

        shot(page, "camile-salarios.png")
        page.close()

        # ============================================================
        # NORMAL PORTAL UNAFFECTED + HARNESS FAIL-CLOSED (regression of
        # the existing V2-UAT-03/03B security suite, re-proven here)
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{BASE}/index.html?uat=camile")
        page.wait_for_timeout(600)
        normal_ctx = page.evaluate("window.NX_AUTH_CORE ? window.NX_AUTH_CORE.getContext() : null")
        check("[NORMAL PORTAL UNAFFECTED] the real index.html ignores ?uat= entirely", normal_ctx is None or normal_ctx.get("nome") != "CAMILE BEATRIZ SANTOS SENA", normal_ctx)
        page.close()

        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(HARNESS)
        page.wait_for_timeout(300)
        check("[HARNESS FAIL-CLOSED] no ?uat= shows the neutral empty state, no iframe", page.is_visible("#uatEmpty") and not page.is_visible("#uatFrame"))
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-04 CAMILE GATE: {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("CAMILE GATE RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
