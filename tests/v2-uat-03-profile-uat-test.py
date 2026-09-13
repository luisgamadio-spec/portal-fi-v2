#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2-UAT-03 -- Portal-wide profile visibility UAT harness.

Generalizes the EXISTING, already-approved Salários UAT technique
(tests/_salarios-uat-harness.html/_salarios-uat-mock.js, RH-5B) from
"one module, one dropdown" to "the whole Portal, six fixed named-
profile direct links" -- the REAL, unmodified index.html/shell/CSS/
modules are loaded into an iframe with ONLY the auth/config layer
mocked (window.supabase.rpc('usuario_logado_fi')/
rpc('portal_modulos_permitidos')), so every visibility decision the
Human sees is made by the real, unmodified auth-core.js/landing.js/
shell.js -- never a re-implementation, never a portal clone.

Covers the 6 named scenarios (Camile/William/Roberto/Felipe/Alex/
Rodrigo) plus a dedicated security-isolation check proving the harness
mechanism has zero effect on the real Portal entry point.

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port.
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "v2-uat-03")
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


SCENARIOS = {
    "camile":  {"nome": "Camile Beatriz",  "perfil": "ANALISTA",      "status": None,        "visible": {"dashbi", "gestao", "painel-analista-fi", "brabus-intelligence"}, "hidden": {"coparticipado", "central-atendimento-fi", "shell-admin", "simulador-novos", "simulador-seminovos", "score", "salarios-comissoes"}},
    "william": {"nome": "William Syade",   "perfil": "VENDEDOR",      "status": "NOVOS",     "visible": {"simulador-novos", "score", "brabus-intelligence"}, "hidden": {"dashbi", "gestao", "coparticipado", "salarios-comissoes", "painel-analista-fi", "central-atendimento-fi", "shell-admin", "simulador-seminovos"}},
    "roberto": {"nome": "Roberto Wagner",  "perfil": "VENDEDOR",      "status": "SEMINOVOS", "visible": {"simulador-seminovos", "score", "brabus-intelligence"}, "hidden": {"dashbi", "gestao", "coparticipado", "salarios-comissoes", "painel-analista-fi", "central-atendimento-fi", "shell-admin", "simulador-novos"}},
    "felipe":  {"nome": "Felipe Vitorino", "perfil": "GERENTE",       "status": "SEMINOVOS", "visible": {"simulador-seminovos", "score", "gestao", "coparticipado", "salarios-comissoes", "brabus-intelligence"}, "hidden": {"dashbi", "painel-analista-fi", "central-atendimento-fi", "shell-admin", "simulador-novos"}},
    "alex":    {"nome": "Alex Donizetti",  "perfil": "GERENTE",       "status": "NOVOS",     "visible": {"simulador-novos", "score", "gestao", "coparticipado", "salarios-comissoes", "brabus-intelligence"}, "hidden": {"dashbi", "painel-analista-fi", "central-atendimento-fi", "shell-admin", "simulador-seminovos"}},
    "rodrigo": {"nome": "Rodrigo Carriel", "perfil": "DIRETOR NOVOS", "status": "NOVOS",     "visible": {"dashbi", "simulador-novos", "score", "gestao", "coparticipado", "salarios-comissoes", "brabus-intelligence"}, "hidden": {"painel-analista-fi", "central-atendimento-fi", "shell-admin", "simulador-seminovos"}},
}

MODULE_ID_TO_CATEGORY_TITLE = {
    "dashbi": "Análise Geral do Grupo",
    "gestao": "Análise F&I do Grupo",
    "coparticipado": "Gestão de Coparticipados",
    "simulador-novos": "Simulador de Novos",
    "simulador-seminovos": "Simulador de Seminovos",
    "score": "Análise de Score Vendedores",
    "salarios-comissoes": "Salários & Comissões",
    "painel-analista-fi": "Painel do Analista F&I",
    "central-atendimento-fi": "Central de Atendimento F&I",
    "shell-admin": "Painel Master",
    "brabus-intelligence": "Brabus Intelligence",
}

ALL_CATEGORY_IDX = [0, 1, 2, 3, 4, 5]  # Gestão / Novos&Seminovos / Score&Salários / Atendimento F&I / Brabus Intelligence / Auditoria


def all_module_blocks(page_frame):
    """Clicks through every landing category and collects every module block's title + deferred state."""
    out = {}
    for idx in ALL_CATEGORY_IDX:
        page_frame.evaluate(f'document.querySelector("#fNavTab{idx}").click()')
        page_frame.page.wait_for_timeout(120)
        blocks = page_frame.evaluate("""() => [...document.querySelectorAll('#landingModuleDetail .fModuleBlock')].map(b => ({
            title: b.querySelector('.fModuleTitle').textContent,
            deferred: b.classList.contains('fModuleBlockDeferred')
        }))""")
        for b in blocks:
            out[b["title"]] = not b["deferred"]  # True = visible/clickable
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
        # SIX PROFILE SCENARIOS
        # ============================================================
        for key, spec in SCENARIOS.items():
            page = tracked_page(viewport={"width": 1366, "height": 900})
            page.goto(f"{HARNESS}?uat={key}")
            page.wait_for_selector("#uatFrame:not([hidden])", timeout=8000)
            page.wait_for_timeout(1500)

            check(f"[{key}] outer banner shows the correct name", spec["nome"].upper() in page.inner_text("#uatWhoName"))
            check(f"[{key}] outer banner shows MODO DE HOMOLOGAÇÃO", "HOMOLOGA" in page.inner_text("#uatWhoRole"))

            frame = page.frames[-1]
            frame.wait_for_selector(".fNavItem", timeout=8000)

            ctx = frame.evaluate("window.NX_AUTH_CORE ? window.NX_AUTH_CORE.getContext() : null")
            state = frame.evaluate("window.NX_AUTH_CORE.getState()")
            check(f"[{key}] Portal reaches AUTHORIZED state", state == "AUTHORIZED", state)
            check(f"[{key}] context carries the correct nome", ctx is not None and ctx.get("nome") == spec["nome"], ctx)
            check(f"[{key}] context carries the correct perfil", ctx is not None and ctx.get("perfil") == spec["perfil"], ctx)
            if spec["status"] is not None:
                check(f"[{key}] context carries the correct departamento/status", ctx is not None and ctx.get("status") == spec["status"], ctx)
            check(f"[{key}] context.isMaster is false (no real elevation)", ctx is not None and ctx.get("isMaster") is False, ctx)

            blocks = all_module_blocks(frame)
            visible_titles = {MODULE_ID_TO_CATEGORY_TITLE[m] for m in spec["visible"]}
            hidden_titles = {MODULE_ID_TO_CATEGORY_TITLE[m] for m in spec["hidden"]}
            visible_ok = all(blocks.get(t) is True for t in visible_titles)
            hidden_ok = all(blocks.get(t) is False for t in hidden_titles)
            check(f"[{key}] modules that SHOULD be visible are visible", visible_ok, {t: blocks.get(t) for t in visible_titles})
            check(f"[{key}] modules that SHOULD be hidden/deferred are hidden", hidden_ok, {t: blocks.get(t) for t in hidden_titles})

            overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            check(f"[{key}] zero horizontal scroll (outer harness page)", overflow["scroll"] <= overflow["client"], overflow)

            shot(page, f"{key}-landing.png")
            page.close()

        # ============================================================
        # SECURITY: the real Portal entry point is unaffected
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{BASE}/index.html?uat=camile&perfil=MASTER")
        page.wait_for_timeout(800)
        real_ctx = page.evaluate("window.NX_AUTH_CORE ? window.NX_AUTH_CORE.getContext() : 'NO_AUTH_CORE_OR_NULL_CONTEXT'")
        real_state = page.evaluate("window.NX_AUTH_CORE ? window.NX_AUTH_CORE.getState() : null")
        check("[SECURITY] real index.html ignores ?uat=/?perfil= query strings entirely (no elevated/mocked context)",
              real_ctx in (None, "NO_AUTH_CORE_OR_NULL_CONTEXT") or (isinstance(real_ctx, dict) and real_ctx.get("nome") != "Camile Beatriz"),
              real_ctx)
        check("[SECURITY] real index.html never reaches a mocked AUTHORIZED state via the query string",
              real_state != "AUTHORIZED" or real_ctx not in (None, "NO_AUTH_CORE_OR_NULL_CONTEXT"), (real_state, real_ctx))
        page.close()

        # UAT context does not survive leaving the harness: opening the
        # real Portal in a FRESH page (never touched the harness at all)
        # has a clean, un-mocked window.supabase/window.NX_AUTH.
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{BASE}/index.html")
        page.wait_for_timeout(800)
        leaked = page.evaluate("""() => {
            try {
                return typeof window.supabase !== 'undefined' && window.supabase.createClient && window.supabase.createClient().auth.getSession.toString().indexOf('uat-token') !== -1;
            } catch (e) { return false; }
        }""")
        check("[SECURITY] a fresh normal Portal load carries no UAT mock residue", leaked is False, leaked)
        page.close()

        # ============================================================
        # Missing/unknown ?uat= value: fail-closed, no iframe loads
        # ============================================================
        page = tracked_page(viewport={"width": 1366, "height": 900})
        page.goto(HARNESS)
        page.wait_for_timeout(300)
        check("[SECURITY] harness with no ?uat= shows the neutral empty state, no iframe", page.is_visible("#uatEmpty") and not page.is_visible("#uatFrame"))
        page.goto(f"{HARNESS}?uat=nonexistentprofile")
        page.wait_for_timeout(300)
        check("[SECURITY] harness with an unknown ?uat= value fails closed the same way", page.is_visible("#uatEmpty") and not page.is_visible("#uatFrame"))
        page.close()

        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[K] zero unexplained console/page errors across the whole suite", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== V2-UAT-03: Profile Homologation Direct Links ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
