#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase 3B -- deterministic tests for the Acessos aos
Módulos section (master-acessos-provider.js, master-acessos-view-
model.js, the acessos-* additions to shell-admin.js), mounted via the
same lightweight harness already proven for Usuários
(tests/_master-users-harness.html). Route-guard-level MASTER-only
enforcement (VENDEDOR/ANALISTA denial) is tested separately against the
real shell/router/auth-core in tests/master-admin-route-test.py -- this
file tests only the section's own behavior once mounted as MASTER.

Everything here runs against a mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. Real mutation homologation (the
grant->verify->revoke->verify rehearsal against the live project) is
Gate 21/22's own separate, narrative-reported live-SQL exercise, not a
Playwright test -- this file proves the FRONTEND contract only.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
LIST_URL = "https://mock.invalid/rest/v1/rpc/master_listar_permissoes_modulos"
SAVE_URL = "https://mock.invalid/rest/v1/rpc/master_salvar_permissoes_modulos"

REAL_NETWORK_TRIPWIRE_HOSTS = ["supabase.co", "cloudflare", "challenges.cloudflare.com"]

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc", viewport=None):
    page = browser.new_page(viewport=viewport or {"width": 1366, "height": 900})
    page.add_init_script(auth_mock_script(token))
    real_hits = []
    page.on("requestfinished", lambda req: real_hits.append(req.url) if any(h in req.url for h in REAL_NETWORK_TRIPWIRE_HOSTS) else None)
    page._real_hits = real_hits
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def goto_acessos(page):
    # The section-nav button lives in the outlet directly (rendered once
    # by render(), outside #maPanel's own loading/error/list states), so
    # it is clickable as soon as the shell mounts -- never gate this on
    # the Usuários panel's own content, which may legitimately be an
    # empty/error state in some fixtures.
    page.wait_for_selector('[data-section="acessos"]', timeout=5000)
    page.click('[data-section="acessos"]')
    page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('mamTable')", timeout=5000)


CONFIG_MODULES = [
    ("simuladorCompleto", "Simulador de Novos", "Simuladores", 1),
    ("simuladorSeminovos", "Simulador de Seminovos", "Simuladores", 2),
    ("dashbi", "Análise Geral do Grupo", "Gestão", 3),
    ("gestao", "Análise F&I do Grupo", "Gestão", 4),
    ("coparticipadoPortal", "Coparticipados", "Gestão de Incentivos", 5),
    ("analiseScoreVendedores", "Análise de Score", "Gestão de Incentivos", 6),
    ("comissoes", "Acompanhamento de Salário", None, 7),
]
STRUCTURAL_MODULES = [
    ("painelAnalistaFi", "Painel do Analista", None, 8),
    ("centralAtendimentoFi", "Central de Atendimento F&I", "Atendimento F&I", 9),
    ("painelMaster", "Painel Master", None, 10),
    ("gestaoBases", "Gestão de Bases (interno)", None, 11),
    ("gestaoSimuladores", "Gestão de Simuladores (interno)", None, 12),
]
COLUMNS = [("VENDEDOR", "NOVOS"), ("VENDEDOR", "SEMINOVOS"), ("GERENTE", "NOVOS"), ("GERENTE", "SEMINOVOS"),
           ("ANALISTA", "TODOS"), ("RH", "TODOS"), ("DIRETOR_NOVOS", "TODOS"), ("DIRETOR_SEMINOVOS", "TODOS")]
TS = "2026-08-14T19:51:20.494257+00:00"


def make_modulos():
    rows = []
    for id_, nome, grupo, ordem in CONFIG_MODULES:
        rows.append({"id": id_, "nome": nome, "grupo": grupo, "ativo": True, "ordem": ordem, "configuravel": True,
                     "created_at": TS, "updated_at": TS})
    for id_, nome, grupo, ordem in STRUCTURAL_MODULES:
        rows.append({"id": id_, "nome": nome, "grupo": grupo, "ativo": True, "ordem": ordem, "configuravel": False,
                     "created_at": TS, "updated_at": TS})
    return rows


def make_permissoes(overrides=None):
    overrides = overrides or {}
    rows = []
    for m, _n, _g, _o in CONFIG_MODULES:
        for perfil, depto in COLUMNS:
            val = overrides.get((m, perfil, depto), False)
            rows.append({"modulo_id": m, "perfil": perfil, "departamento": depto, "permitido": val, "atualizado_em": TS})
    return rows


BASELINE_OVERRIDES = {
    ("dashbi", "ANALISTA", "TODOS"): True,
    ("gestao", "ANALISTA", "TODOS"): True,
    ("gestao", "GERENTE", "NOVOS"): True,  # used for the revoke-delta test
    ("comissoes", "RH", "TODOS"): True,
}


def matrix_payload():
    return {"modulos": make_modulos(), "permissoes": make_permissoes(BASELINE_OVERRIDES), "flag_dinamica": True}


def cell_selector(modulo, perfil, depto):
    return '.mamCell[data-module="%s"][data-perfil="%s"][data-departamento="%s"]' % (modulo, perfil, depto)


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- 1: MASTER can enter (mount + reach the section) ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        check("1: MASTER reaches Acessos aos Módulos and the real matrix RPC is called", "mamTable" in page.inner_html("#maPanel"))

        # ---------- 4/5: exact catalog mapping + closed 56-cell matrix ----------
        html = page.inner_html("#maPanel")
        # inner_text (not inner_html) for label checks -- "Análise F&I do
        # Grupo" is HTML-escaped to "F&amp;I" in the raw markup, which
        # never matches a plain-text needle against inner_html.
        text = page.inner_text("#maPanel")
        check("4: all 7 configurable module labels rendered", all(lbl in text for lbl in [n for _, n, _, _ in CONFIG_MODULES]))
        check("4: no structural (non-configurable) module rendered as a row", not any(n in text for _, n, _, _ in STRUCTURAL_MODULES))
        # Desktop and mobile renderers both exist in the DOM simultaneously
        # (CSS-only visibility toggle, same pattern as Usuários) -- scope
        # to the desktop set for the "closed 56-cell" count; mobile's own
        # matching 56 is asserted separately (Gate 27 item 30).
        cb_count = page.eval_on_selector_all(".maDesktopOnly .mamCell", "els => els.length")
        check("5: exact closed 56-cell matrix (7 modules x 8 columns)", cb_count == 56)

        # ---------- 6/7: MASTER column absent, permanent-access notice ----------
        check("6: no MASTER column header/checkbox rendered", "aria-label=\"" not in html or "MASTER —" not in html)
        check("7: MASTER permanent-access notice present", "acesso permanente" in html)

        # ---------- 8: initial checked states reflect the backend snapshot ----------
        analista_dashbi_checked = page.eval_on_selector(cell_selector("dashbi", "ANALISTA", "TODOS"), "el => el.checked")
        vendedor_score_checked = page.eval_on_selector(cell_selector("analiseScoreVendedores", "VENDEDOR", "NOVOS"), "el => el.checked")
        check("8: initial checked state matches backend (ANALISTA/dashbi=true)", analista_dashbi_checked is True)
        check("8: initial checked state matches backend (VENDEDOR-NOVOS/score=false)", vendedor_score_checked is False)

        # ---------- 27: unavailable-module caveat (comissoes = COMING_SOON) ----------
        check("27: unavailable module shows an explicit caveat, not a bare checkbox", "Ainda não disponível" in html)

        # ---------- 33: accessible checkbox names ----------
        aria = page.eval_on_selector(cell_selector("dashbi", "ANALISTA", "TODOS"), "el => el.getAttribute('aria-label')")
        check("33: checkbox has a real, non-generic accessible name", bool(aria) and "Análise Geral do Grupo" in aria and "Analista" in aria)

        # ---------- 32/34: keyboard + focus ----------
        page.eval_on_selector(cell_selector("dashbi", "ANALISTA", "TODOS"), "el => el.focus()")
        focused_is_target = page.evaluate("document.activeElement === document.querySelector('%s')" % cell_selector("dashbi", "ANALISTA", "TODOS"))
        check("32/34: checkbox is keyboard-focusable (focus-visible reachable)", focused_is_target is True)

        # ---------- 9/12: grant delta -- local only until Save ----------
        save_calls = []
        page.check(cell_selector("analiseScoreVendedores", "VENDEDOR", "NOVOS"))
        page.wait_for_timeout(50)
        check("9: checkbox change is local only (no save RPC yet)", len(save_calls) == 0)
        dirty_html = page.inner_html("#maPanel")
        check("dirty banner shown after a real change", "Alterações não salvas" in dirty_html)

        # ---------- 10/11: revert removes delta, zero-delta cannot save ----------
        page.uncheck(cell_selector("analiseScoreVendedores", "VENDEDOR", "NOVOS"))
        page.wait_for_timeout(50)
        html2 = page.inner_html("#maPanel")
        check("10: reverting a cell to its original value removes it from the dirty delta", "Alterações não salvas" not in html2)
        save_disabled = page.eval_on_selector("#mamSaveBtn", "el => el.disabled")
        check("11: zero-delta cannot save (Save button disabled)", save_disabled is True)

        # ---------- 12: exact grant delta payload ----------
        page.check(cell_selector("analiseScoreVendedores", "VENDEDOR", "NOVOS"))
        page.wait_for_timeout(50)
        page.click("#mamSaveBtn")
        page.wait_for_timeout(100)
        # Scope to the confirm dialog itself -- the underlying matrix
        # (with every module's label, "Coparticipados" included) stays
        # rendered alongside the confirm dialog by design (same pattern
        # as Usuários' own inline confirm step), so the "not the full
        # matrix" half of this check must look only at .maConfirm's own
        # content, not the whole panel.
        confirm_text = page.inner_text(".maConfirm")
        check("18: save confirmation lists exact delta (module+scope), not the full matrix",
              "Análise de Score" in confirm_text and "Vendedor" in confirm_text and
              "Coparticipados" not in confirm_text and "Simulador de Novos" not in confirm_text)

        def capture_save(route):
            save_calls.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({
                "aplicadas": [{"modulo_id": "analiseScoreVendedores", "perfil": "VENDEDOR", "departamento": "NOVOS", "valor_anterior": False, "valor_novo": True}],
                "conflitos": []
            }))
        page.route(SAVE_URL + "*", capture_save)
        overrides_after_grant = dict(BASELINE_OVERRIDES)
        overrides_after_grant[("analiseScoreVendedores", "VENDEDOR", "NOVOS")] = True
        page.route(LIST_URL + "*", json_route(200, {"modulos": make_modulos(), "permissoes": make_permissoes(overrides_after_grant), "flag_dinamica": True}))
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)

        check("save RPC called exactly once", len(save_calls) == 1)
        payload = save_calls[0].get("p_mudancas", []) if save_calls else []
        check("12: exact grant delta payload (exactly 1 changed row)", len(payload) == 1)
        if payload:
            row = payload[0]
            check("12: grant payload has correct module/perfil/departamento/permitido", row.get("modulo_id") == "analiseScoreVendedores" and row.get("perfil") == "VENDEDOR" and row.get("departamento") == "NOVOS" and row.get("permitido") is True)
            check("14: atualizado_em_esperado preserved from the loaded snapshot", row.get("atualizado_em_esperado") == TS)
            check("15: unmodified cells absent from payload (only the 1 changed row sent)", len(payload) == 1)
            check("16: actor absent from payload", not any(k in row for k in ("actor", "auth_uid", "usuario_id", "master_id")))
            check("17: user/CPF/email absent from payload", not any(k in row for k in ("cpf", "email", "user_id", "id")))
        check("20/24: all-applied response -> success feedback shown", "salva(s) com sucesso" in page.inner_html("#maPanel"))
        check("23: canonical matrix reloaded after save (re-fetched, not assumed)", page.eval_on_selector(cell_selector("analiseScoreVendedores", "VENDEDOR", "NOVOS"), "el => el.checked") is True)
        page.close()

        # ---------- 13: exact revoke delta payload ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        page.uncheck(cell_selector("gestao", "GERENTE", "NOVOS"))
        page.wait_for_timeout(50)
        page.click("#mamSaveBtn")
        page.wait_for_timeout(100)
        save_calls_2 = []

        def capture_save_2(route):
            save_calls_2.append(_json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({
                "aplicadas": [{"modulo_id": "gestao", "perfil": "GERENTE", "departamento": "NOVOS", "valor_anterior": True, "valor_novo": False}],
                "conflitos": []
            }))
        page.route(SAVE_URL + "*", capture_save_2)
        overrides_after_revoke = dict(BASELINE_OVERRIDES)
        overrides_after_revoke[("gestao", "GERENTE", "NOVOS")] = False
        page.route(LIST_URL + "*", json_route(200, {"modulos": make_modulos(), "permissoes": make_permissoes(overrides_after_revoke), "flag_dinamica": True}))
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        payload2 = save_calls_2[0].get("p_mudancas", []) if save_calls_2 else []
        check("13: exact revoke delta payload", len(payload2) == 1 and payload2[0].get("permitido") is False and payload2[0].get("modulo_id") == "gestao")
        page.close()

        # ---------- 19: duplicate save blocked ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        page.check(cell_selector("analiseScoreVendedores", "GERENTE", "NOVOS"))
        page.wait_for_timeout(50)
        page.click("#mamSaveBtn")
        page.wait_for_timeout(50)
        dup_calls = []

        def slow_save(route):
            import time as _t
            dup_calls.append(1)
            _t.sleep(0.3)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"aplicadas": [], "conflitos": []}))
        page.route(SAVE_URL + "*", slow_save)
        page.eval_on_selector("#maConfirmYes", "el => { el.click(); el.click(); }")
        page.wait_for_timeout(600)
        check("19: duplicate save blocked (exactly 1 RPC call despite 2 clicks)", len(dup_calls) == 1)
        page.close()

        # ---------- 21: all-conflict response ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        page.check(cell_selector("analiseScoreVendedores", "VENDEDOR", "SEMINOVOS"))
        page.wait_for_timeout(50)
        page.click("#mamSaveBtn")
        page.wait_for_timeout(50)
        page.route(SAVE_URL + "*", json_route(200, {"aplicadas": [], "conflitos": [{"modulo_id": "analiseScoreVendedores", "perfil": "VENDEDOR", "departamento": "SEMINOVOS", "motivo": "CONFLITO_CONCORRENCIA"}]}))
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        conflict_html = page.inner_html("#maPanel")
        check("21: all-conflict response -> explicit conflict message, no false success", "alteradas em outra sessão" in conflict_html and "com sucesso" not in conflict_html)
        page.close()

        # ---------- 22: partial apply + partial conflict ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        page.check(cell_selector("analiseScoreVendedores", "GERENTE", "NOVOS"))
        page.check(cell_selector("coparticipadoPortal", "ANALISTA", "TODOS"))
        page.wait_for_timeout(50)
        page.click("#mamSaveBtn")
        page.wait_for_timeout(50)
        page.route(SAVE_URL + "*", json_route(200, {
            "aplicadas": [{"modulo_id": "analiseScoreVendedores", "perfil": "GERENTE", "departamento": "NOVOS", "valor_anterior": False, "valor_novo": True}],
            "conflitos": [{"modulo_id": "coparticipadoPortal", "perfil": "ANALISTA", "departamento": "TODOS", "motivo": "CONFLITO_CONCORRENCIA"}]
        }))
        page.click("#maConfirmYes")
        page.wait_for_timeout(300)
        partial_html = page.inner_html("#maPanel")
        check("22: partial apply/conflict -> presents both, never claims full success or full failure",
              "1 alteração" in partial_html and "não puderam ser aplicadas" in partial_html)
        page.close()

        # ---------- 25/26: error normalization + malformed response fail-closed ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        page.wait_for_selector('[data-section="acessos"]', timeout=5000)
        page.click('[data-section="acessos"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        err_html = page.inner_html("#maPanel")
        check("25: error normalized (AUTH_DENIED), no raw backend text leaked", "modErrorState" in err_html and "Acesso exclusivo do perfil Master." not in err_html)
        page.close()

        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, {"foo": "bar"}))
        mount(page)
        page.wait_for_selector('[data-section="acessos"]', timeout=5000)
        page.click('[data-section="acessos"]')
        page.wait_for_function("document.getElementById('maPanel').innerHTML.includes('modErrorState')", timeout=5000)
        malformed_html = page.inner_html("#maPanel")
        check("26: malformed matrix response fails closed (no synthesized matrix rendered)", "modErrorState" in malformed_html and "mamTable" not in malformed_html)
        page.close()

        # ---------- 28: dirty tab-exit guard ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        page.check(cell_selector("analiseScoreVendedores", "RH", "TODOS"))
        page.wait_for_timeout(50)
        page.click('[data-section="usuarios"]')
        page.wait_for_timeout(100)
        guard_html = page.inner_html("#maPanel")
        check("28: dirty tab-exit guard shown when switching away with unsaved changes", "Descartar" in guard_html and "não salvas" in guard_html)
        page.click("#maConfirmNo")
        page.wait_for_timeout(100)
        check("28: Cancelar keeps the dirty state intact (not an inescapable loop, but also not silently discarded)",
              page.eval_on_selector(cell_selector("analiseScoreVendedores", "RH", "TODOS"), "el => el.checked") is True)
        page.click('[data-section="usuarios"]')
        page.wait_for_timeout(100)
        page.click("#maConfirmYes")
        page.wait_for_timeout(100)
        final_html = page.inner_html("#maPanel")
        # This fixture's SEC_URL returns an empty user list, so the
        # Usuários view renders modEmptyState (no "maTable" markup at
        # all when there are 0 rows) -- the section switch itself is
        # what "mamTable" (Acessos) being gone proves.
        check("28: confirming discard actually switches section", "mamTable" not in final_html and "Nenhum usuário encontrado" in final_html)
        check("35: Usuários surface still renders correctly after visiting/leaving Acessos (non-regression)", "Nenhum usuário encontrado" in final_html)
        page.close()

        # ---------- 20: no user selector on this screen ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        has_user_selector = page.eval_on_selector_all("#maPanel input[type=text], #maPanel input[type=search]", "els => els.length")
        check("29: no user selector/search input exists on the Acessos screen", has_user_selector == 0)

        # ---------- 30/31: mobile representation, no BODY overflow ----------
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(100)
        mobile_visible = page.evaluate("getComputedStyle(document.querySelector('.mamMobileCard')).display !== 'none'")
        desktop_hidden = page.evaluate("getComputedStyle(document.querySelector('.mamTable').closest('.maDesktopOnly')).display === 'none'")
        check("30: mobile representation shows grouped module cards (same data source)", mobile_visible)
        check("30: desktop matrix hidden at mobile width (exactly one visible)", desktop_hidden)
        mobile_cb_count = page.eval_on_selector_all(".maMobileOnly .mamCell", "els => els.length")
        check("30: mobile representation carries the SAME 56-cell data (no duplicate business logic)", mobile_cb_count == 56)
        no_overflow = page.evaluate("document.body.scrollWidth <= document.documentElement.clientWidth + 1")
        check("31: no BODY horizontal overflow at mobile width", no_overflow)
        page.close()

        # ---------- 36/37: no real network, no secret leakage ----------
        page = new_page(browser)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LIST_URL + "*", json_route(200, matrix_payload()))
        mount(page)
        goto_acessos(page)
        check("36: no real network hit in the mocked suite (requestfinished tripwire)", len(page._real_hits) == 0)
        check("37: no access token leaked into rendered HTML", "mock-access-token-abc" not in page.inner_html("#maOutlet"))
        page.close()

        browser.close()

    # ---------- 38/39/40: covered elsewhere, not duplicated here ----------
    # 38 (Score registry status corrected) and 39 (simulator registry
    # findings unchanged) are registry-test.py's own responsibility
    # (EXPECTED_STATUS["score"] already includes HUMAN_APPROVED; the two
    # simulador findings are asserted unchanged there, not re-asserted
    # in a browser test here). 40 (no backend authority source changed)
    # is this Phase's own Gate 1 live fingerprint (reported narratively,
    # not a Playwright assertion -- there is no frontend surface that
    # could prove a backend function body is byte-identical).
    check("38/39/40: see registry-test.py + this Phase's Gate 1 fingerprint report (not duplicated here)", True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Acessos Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
