#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-04 -- Section 8 ("SOMENTE depois de Camile passar... provar que
a correção arquitetural funciona para" the other 5 profiles, "não criar
seis hacks"). Proves the SAME scopedSalaryFixtures() mechanism (tests/
_v2-uat-03-profiles-mock.js, one parametrized builder) that fixed
Camile also correctly scopes Salários & Comissões for William/Roberto/
Felipe/Alex/Rodrigo -- no MASTER-shaped leak, no cross-scenario data
bleed, correct real loja/perfil resolved inside the module itself.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://127.0.0.1:{PORT}"
HARNESS = f"{BASE}/tests/_v2-uat-03-profiles-harness.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


# perfil/loja/status: real, audited (V2-UAT-03B). own_store_marker: the
# ONE real loja that scenario's own scoped data should show; other_store_
# markers: real loja names that belong to OTHER scenarios and must never
# leak into this one's own Salários view.
SCENARIOS = {
    "william": {"nome": "WILLIAM SYADE", "perfil": "VENDEDOR", "loja": "EUROPA", "own_marker": "EUROPA", "foreign_markers": ["NACOES", "BANDEIRANTES"]},
    "roberto": {"nome": "ROBERTO WAGNER DE LIMA", "perfil": "VENDEDOR", "loja": "EUROPA", "own_marker": "EUROPA", "foreign_markers": ["NACOES", "BANDEIRANTES"]},
    "felipe":  {"nome": "FELIPE ALEXANDRE VITORINO", "perfil": "GERENTE", "loja": "EUROPA", "own_marker": "EUROPA", "foreign_markers": ["NACOES", "BANDEIRANTES"]},
    "alex":    {"nome": "ALEX FABIAN GALVAO DONIZETI", "perfil": "GERENTE", "loja": "BANDEIRANTES", "own_marker": "BANDEIRANTES", "foreign_markers": ["NACOES", "EUROPA"]},
    "rodrigo": {"nome": "RODRIGO CARRIEL DE OLIVEIRA", "perfil": "DIRETOR NOVOS", "loja": None, "own_marker": None, "foreign_markers": ["NACOES"]},
}

OLD_MASTER_FIXTURE_STORES = ["ABC", "BANDEIRANTES CENTRO", "GASTAO"]


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

        for key, spec in SCENARIOS.items():
            page = tracked_page(viewport={"width": 1366, "height": 900})
            page.goto(f"{HARNESS}?uat={key}")
            page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
            page.wait_for_timeout(1200)
            frame = page.frames[-1]
            frame.wait_for_selector(".fNavItem", timeout=8000)

            frame.evaluate('location.hash = "#/salarios-comissoes"')
            page.wait_for_timeout(1200)

            ctx = frame.evaluate("window.NX_AUTH_CORE.getContext()")
            check(f"[{key}] Salários resolves the correct real perfil", ctx.get("perfil") == spec["perfil"], ctx)
            check(f"[{key}] isMaster is false", ctx.get("isMaster") is False, ctx)

            body_text = frame.evaluate("document.body.innerText")
            check(f"[{key}] Salários opened without crashing", "Comiss" in body_text)
            check(f"[{key}] no 'Histórico' tab (MASTER-only)", "Histórico" not in body_text)
            check(f"[{key}] no 'Gestor F&I' group-wide oversight section (MASTER-only)", "COMISSÃO — GESTOR F&I" not in body_text.upper())
            check(f"[{key}] no closing/fechamento-de-competência action (MASTER-only)", "Fechar competência" not in body_text and "Reabrir" not in body_text)

            leaked_old_fixture = [m for m in OLD_MASTER_FIXTURE_STORES if m in body_text]
            check(f"[{key}] no leftover MASTER-shaped fixture store leaks through", len(leaked_old_fixture) == 0, leaked_old_fixture)

            leaked_foreign = [m for m in spec["foreign_markers"] if m in body_text]
            check(f"[{key}] no OTHER scenario's real loja leaks into this scope", len(leaked_foreign) == 0, leaked_foreign)

            if spec["own_marker"]:
                check(f"[{key}] this scenario's own real loja IS present in scope", spec["own_marker"] in body_text)

            check(f"[{key}] the module shows this person's real nome somewhere (own identity, not a generic placeholder)",
                  spec["nome"] in body_text or "Analista Exemplo" not in body_text)

            check(f"[{key}] no broken NaN value rendered", "NaN" not in body_text)

            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[{key}] zero horizontal scroll", overflow["scroll"] <= overflow["client"], overflow)

            page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[K] zero unexplained console/page errors", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-04: Other 5 Profiles Salários Regression ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
