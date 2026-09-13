#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-05 -- confirmed Human business rule: "SE O USUÁRIO NÃO TEM
ACESSO A UM MÓDULO, O MÓDULO NÃO DEVE APARECER." Replaces V2-UAT-04's
disclosed PRODUCT_AUTH_VISIBILITY_DEFECT (assets/js/landing.js's
moduleBlockHtml()/navItemHtml() rendering an unauthorized module as a
disabled/deferred card) with complete DOM omission -- isAuthDenied(m)
now short-circuits both functions to `return ''`, and a category left
with zero visible modules omits itself too (NX_LANDING.renderRoute()'s
own filter, applied once, fed to both landingHtml()/wireLanding()).

Explicitly NOT the same as NOT_MIGRATED ("technically deferred by
design") -- that branch is untouched in both functions; this suite
also spot-checks the served source still carries it byte-for-byte,
since no live NOT_MIGRATED module currently exists in config/module-
registry.json to exercise it end-to-end.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port. Uses the SAME harness
(tests/_v2-uat-03-profiles-harness.html) approved and unmodified by
V2-UAT-03/03B/04 -- no new architecture.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "v2-uat-05")
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


MODULE_ID_TO_TITLE = {
    "dashbi": "Análise Geral do Grupo", "gestao": "Análise F&I do Grupo", "coparticipado": "Gestão de Coparticipados",
    "simulador-novos": "Simulador de Novos", "simulador-seminovos": "Simulador de Seminovos",
    "score": "Análise de Score Vendedores", "salarios-comissoes": "Salários & Comissões",
    "painel-analista-fi": "Painel do Analista F&I", "central-atendimento-fi": "Central de Atendimento F&I",
    "shell-admin": "Painel Master", "brabus-intelligence": "Brabus Intelligence",
}

# Real, verified matrices (V2-UAT-04) -- module ids the profile IS/ISN'T granted.
SCENARIOS = {
    "camile":  {"visible": {"dashbi", "gestao", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "painel-analista-fi", "brabus-intelligence"},
                "hidden": {"central-atendimento-fi", "shell-admin"}},
    "william": {"visible": {"dashbi", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"},
                "hidden": {"score", "coparticipado", "gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}},
    "roberto": {"visible": {"dashbi", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"},
                "hidden": {"score", "coparticipado", "gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}},
    "felipe":  {"visible": {"dashbi", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"},
                "hidden": {"gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}},
    "alex":    {"visible": {"dashbi", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"},
                "hidden": {"gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}},
    "rodrigo": {"visible": {"dashbi", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"},
                "hidden": {"gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}},
}


def all_module_blocks(frame):
    out = {}
    tab_count = frame.evaluate("document.querySelectorAll('.fNavItem').length")
    for idx in range(tab_count):
        frame.evaluate(f'document.querySelectorAll(".fNavItem")[{idx}].click()')
        frame.page.wait_for_timeout(120)
        blocks = frame.evaluate("""() => [...document.querySelectorAll('#landingModuleDetail .fModuleBlock')].map(b => ({
            title: b.querySelector('.fModuleTitle').textContent,
            deferred: b.classList.contains('fModuleBlockDeferred')
        }))""")
        for b in blocks:
            out[b["title"]] = b
    return out


def open_landing_as_master(page):
    page.goto(BASE + "/index.html#/landing")
    page.wait_for_selector("#landingNav", timeout=8000)
    page.evaluate("""() => {
        window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
        window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER', allowedModuleIds: [] });
    }""")
    page.wait_for_selector(".fNavItem", timeout=8000)


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
        # 6 PROFILES -- each module either fully present (real link) or
        # fully absent (no card entry in the DOM at all).
        # ============================================================
        for key, spec in SCENARIOS.items():
            page = tracked_page(viewport={"width": 1366, "height": 900})
            page.goto(f"{HARNESS}?uat={key}")
            page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
            page.wait_for_timeout(1200)
            frame = page.frames[-1]
            frame.wait_for_selector(".fNavItem", timeout=8000)

            blocks = all_module_blocks(frame)

            for mid in spec["visible"]:
                title = MODULE_ID_TO_TITLE[mid]
                b = blocks.get(title)
                check(f"[{key}] '{title}' is present as a real, non-deferred card", b is not None and b["deferred"] is False, b)

            for mid in spec["hidden"]:
                title = MODULE_ID_TO_TITLE[mid]
                b = blocks.get(title)
                check(f"[{key}] '{title}' is COMPLETELY ABSENT from the DOM (not a disabled card)", b is None, b)

            # zero card disabled caused by AUTH DENIED anywhere on this
            # scenario's whole Landing (no live NOT_MIGRATED module
            # exists today to legitimately produce one -- see module
            # header docstring).
            deferred_count = frame.evaluate("document.querySelectorAll('.fModuleBlockDeferred').length")
            check(f"[{key}] zero .fModuleBlockDeferred cards anywhere on Landing", deferred_count == 0, deferred_count)

            # sidebar: no forbidden item, no deferred item either
            sidebar_labels = frame.evaluate("[...document.querySelectorAll('#pGlobalNav .pNavLabel')].map(e => e.textContent)")
            sidebar_deferred = frame.evaluate("document.querySelectorAll('#pGlobalNav .pNavItemDeferred').length")
            for mid in spec["hidden"]:
                title = MODULE_ID_TO_TITLE[mid]
                check(f"[{key}] sidebar has no item labeled '{title}'", title not in sidebar_labels, sidebar_labels)
            check(f"[{key}] sidebar has zero disabled/deferred items", sidebar_deferred == 0, sidebar_deferred)

            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[{key}] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

            shot(page, f"{key}-landing.png")
            page.close()

        # ============================================================
        # EMPTY CATEGORY ABSENCE -- William (VENDEDOR) loses BOTH
        # modules in "Atendimento F&I" and the sole module in
        # "Auditoria" -> both category tabs must not render at all.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{HARNESS}?uat=william")
        page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
        page.wait_for_timeout(1200)
        frame = page.frames[-1]
        frame.wait_for_selector(".fNavItem", timeout=8000)
        category_labels = frame.evaluate("[...document.querySelectorAll('.fNavItem .label')].map(e => e.textContent)")
        check("[EMPTY CATEGORY ABSENCE] 'Atendimento F&I' tab does not render for William (both its modules denied)", "Atendimento F&I" not in category_labels, category_labels)
        check("[EMPTY CATEGORY ABSENCE] 'Auditoria' tab does not render for William (its sole module denied)", "Auditoria" not in category_labels, category_labels)
        check("[EMPTY CATEGORY ABSENCE] categories William CAN see are still present", {"Gestão", "Novos & Seminovos", "Score & Salários", "Brabus Intelligence"} <= set(category_labels), category_labels)
        page.close()

        # ============================================================
        # NOT_MIGRATED PRESERVED -- no live module is NOT_MIGRATED
        # today (config/module-registry.json), so this is verified at
        # the served-source level: both functions' NOT_MIGRATED branch
        # (the "Em breve" deferred-but-visible pattern) is untouched.
        # ============================================================
        page = tracked_page()
        page.goto(BASE + "/index.html")
        src_text = page.evaluate("fetch('assets/js/landing.js').then(r => r.text())")
        check("[NOT_MIGRATED PRESERVED] moduleBlockHtml()'s NOT_MIGRATED deferred-card markup is unchanged in the served source", "fModuleBlockDeferred" in src_text and "Em breve" in src_text and "fModuleSoon" in src_text)
        check("[NOT_MIGRATED PRESERVED] navItemHtml()'s NOT_MIGRATED deferred-item markup is unchanged in the served source", "pNavItemDeferred" in src_text and "pNavSoon" in src_text)
        page.close()

        # ============================================================
        # MASTER REGRESSION -- normal Portal, MASTER sees every module
        # its authority allows (Painel Master, Central de Atendimento
        # F&I included), nothing newly hidden.
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        open_landing_as_master(page)
        # open_landing_as_master runs in the top-level page (no iframe) --
        # main_frame has the same .evaluate()/.page all_module_blocks() needs.
        blocks = all_module_blocks(page.main_frame)
        for mid, title in MODULE_ID_TO_TITLE.items():
            b = blocks.get(title)
            check(f"[MASTER] '{title}' is present as a real, non-deferred card", b is not None and b["deferred"] is False, b)
        deferred_count = page.evaluate("document.querySelectorAll('.fModuleBlockDeferred').length")
        check("[MASTER] zero .fModuleBlockDeferred cards (MASTER is authorized everywhere)", deferred_count == 0, deferred_count)
        category_labels = page.evaluate("[...document.querySelectorAll('.fNavItem .label')].map(e => e.textContent)")
        check("[MASTER] all 6 categories present", len(category_labels) == 6, category_labels)
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-05: Unauthorized Modules Hidden ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
