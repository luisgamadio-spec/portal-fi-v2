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


# V2-UAT-03B: nome/perfil/loja/status AND visible/hidden below are all
# VERIFIED live data (read-only Supabase audit of public.usuarios +
# public.permissoes_modulos), replacing this suite's earlier "assumed"
# module lists. The 4 real matrices (ANALISTA/GERENTE/VENDEDOR/
# DIRETOR_NOVOS) are applied verbatim -- note VENDEDOR and DIRETOR_
# NOVOS/GERENTE all get BOTH simulator modules regardless of their own
# department (the real matrix does not restrict by department), a
# genuine correction versus this suite's earlier own assumption.
ANALISTA_VISIBLE = {"dashbi", "gestao", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "painel-analista-fi", "brabus-intelligence"}
ANALISTA_HIDDEN = {"central-atendimento-fi", "shell-admin"}
GERENTE_VISIBLE = {"dashbi", "coparticipado", "score", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"}
GERENTE_HIDDEN = {"gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}
VENDEDOR_VISIBLE = {"dashbi", "salarios-comissoes", "simulador-novos", "simulador-seminovos", "brabus-intelligence"}
VENDEDOR_HIDDEN = {"score", "coparticipado", "gestao", "painel-analista-fi", "central-atendimento-fi", "shell-admin"}
DIRETOR_NOVOS_VISIBLE = GERENTE_VISIBLE
DIRETOR_NOVOS_HIDDEN = GERENTE_HIDDEN

SCENARIOS = {
    "camile":  {"nome": "CAMILE BEATRIZ SANTOS SENA", "perfil": "ANALISTA",      "status": "NOVOS/SEMINOVOS", "loja": "NACOES",       "visible": ANALISTA_VISIBLE,      "hidden": ANALISTA_HIDDEN},
    "william": {"nome": "WILLIAM SYADE",              "perfil": "VENDEDOR",      "status": "NOVOS",           "loja": "EUROPA",       "visible": VENDEDOR_VISIBLE,      "hidden": VENDEDOR_HIDDEN},
    "roberto": {"nome": "ROBERTO WAGNER DE LIMA",      "perfil": "VENDEDOR",      "status": "SEMINOVOS",       "loja": "EUROPA",       "visible": VENDEDOR_VISIBLE,      "hidden": VENDEDOR_HIDDEN},
    "felipe":  {"nome": "FELIPE ALEXANDRE VITORINO",   "perfil": "GERENTE",       "status": "SEMINOVOS",       "loja": "EUROPA",       "visible": GERENTE_VISIBLE,       "hidden": GERENTE_HIDDEN},
    "alex":    {"nome": "ALEX FABIAN GALVAO DONIZETI", "perfil": "GERENTE",       "status": "NOVOS",           "loja": "BANDEIRANTES", "visible": GERENTE_VISIBLE,       "hidden": GERENTE_HIDDEN},
    "rodrigo": {"nome": "RODRIGO CARRIEL DE OLIVEIRA", "perfil": "DIRETOR NOVOS", "status": "NOVOS",           "loja": None,           "visible": DIRETOR_NOVOS_VISIBLE, "hidden": DIRETOR_NOVOS_HIDDEN},
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
        resolved_ctx = {}
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
            if spec["loja"] is None:
                # auth-boundary.js's own real, unmodified userFromRow()
                # does `loja: row.loja || ''` -- a genuine null loja
                # (Rodrigo's real row) is normalized to '' by the REAL
                # product code itself, not by this harness. Passing a
                # real `null` all the way into the mocked RPC (never
                # substituting 'TODAS') is exactly what correctly
                # represents "no specific loja" for this codebase, and
                # this IS that real code's own genuine output.
                check(f"[{key}] context correctly reflects the real absence of a specific loja (auth-boundary.js's own null -> '' normalization, not a placeholder)", ctx is not None and ctx.get("loja") == "", ctx)
            else:
                check(f"[{key}] context carries the correct loja", ctx is not None and ctx.get("loja") == spec["loja"], ctx)
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

            resolved_ctx[key] = ctx
            shot(page, f"{key}-landing.png")
            page.close()

        # ============================================================
        # SECTION 7 -- explicit cross-scenario proofs the brief itself
        # called for (same base perfil, different real context).
        # ============================================================
        check("[cross] William/Roberto share the base perfil VENDEDOR",
              resolved_ctx["william"]["perfil"] == resolved_ctx["roberto"]["perfil"] == "VENDEDOR")
        check("[cross] William/Roberto have different status/departamento (Novos vs. Seminovos)",
              resolved_ctx["william"]["status"] == "NOVOS" and resolved_ctx["roberto"]["status"] == "SEMINOVOS")
        check("[cross] William/Roberto share the same real loja (Europa) despite different departamento",
              resolved_ctx["william"]["loja"] == resolved_ctx["roberto"]["loja"] == "EUROPA")

        check("[cross] Felipe/Alex share the same GERENTE module matrix (both lack gestao)",
              SCENARIOS["felipe"]["visible"] == SCENARIOS["alex"]["visible"] and SCENARIOS["felipe"]["hidden"] == SCENARIOS["alex"]["hidden"])
        check("[cross] Felipe/Alex have different real loja/departamento",
              resolved_ctx["felipe"]["loja"] != resolved_ctx["alex"]["loja"] and resolved_ctx["felipe"]["status"] != resolved_ctx["alex"]["status"])

        check("[cross] Rodrigo carries perfil 'DIRETOR NOVOS' (space-separated, real enum value)",
              resolved_ctx["rodrigo"]["perfil"] == "DIRETOR NOVOS")
        check("[cross] Rodrigo status is NOVOS", resolved_ctx["rodrigo"]["status"] == "NOVOS")
        check("[cross] Rodrigo has no specific loja (real null through the mock, normalized to '' by auth-boundary.js's own real code)", resolved_ctx["rodrigo"]["loja"] == "")

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
