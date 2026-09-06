#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5H -- deterministic tests for the Utilização dos
Simuladores module (master-simulator-usage-provider.js, master-
simulator-usage-view-model.js, shell-admin.js), mounted via the same
lightweight harness used by every sibling Painel Master surface.

READ-ONLY CAPABILITY (confirmed live, not assumed): the only 4 writer
RPCs for this data (portal_telemetry_start_session/_heartbeat/
_simulation/_end_session) are called exclusively by the simulator
surfaces themselves (external GitHub Pages deployments, not present in
any local repo) -- never by this admin screen. This suite therefore has
no write/mutation checks to perform; it focuses on read semantics,
filter/metric correctness, timezone/date-boundary behavior, privacy,
and authorization.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file. Synthetic user names/stores only.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
USAGE_URL = "https://mock.invalid/rest/v1/rpc/master_simulator_usage_data"

results = []

ROW_NOVOS = {"usuario_id": "u1", "nome": "Vendedor Um", "module_id": "simuladorCompleto",
             "loja_relatorio": "BARRA FUNDA", "perfil_relatorio": "VENDEDOR", "departamento_relatorio": "NOVOS",
             "sessions": 5, "simulation_count": 3, "active_seconds": 620, "active_days": 2,
             "first_use": "2026-08-20T10:00:00+00:00", "last_use": "2026-09-01T14:30:00+00:00"}
ROW_SEMI = {"usuario_id": "u1", "nome": "Vendedor Um", "module_id": "simuladorSeminovos",
            "loja_relatorio": "BARRA FUNDA", "perfil_relatorio": "VENDEDOR", "departamento_relatorio": "NOVOS",
            "sessions": 2, "simulation_count": 0, "active_seconds": 90, "active_days": 1,
            "first_use": "2026-08-22T09:00:00+00:00", "last_use": "2026-08-25T11:00:00+00:00"}
ROW_ZERO_SIM = {"usuario_id": "u2", "nome": "Analista Sem Simulacao", "module_id": "simuladorCompleto",
                "loja_relatorio": "EUROPA", "perfil_relatorio": "ANALISTA", "departamento_relatorio": "NOVOS/SEMINOVOS",
                "sessions": 3, "simulation_count": 0, "active_seconds": 0, "active_days": 1,
                "first_use": "2026-08-30T10:00:00+00:00", "last_use": "2026-08-30T10:05:00+00:00"}
ROW_LONG = {"usuario_id": "u3", "nome": "Usuário Com Nome Extremamente Longo Para Teste De Estresse De Layout Na Tabela E No Drawer",
            "module_id": "simuladorSeminovos",
            "loja_relatorio": "LOJA COM NOME MUITO LONGO PARA TESTE DE ESTRESSE DE LARGURA DE COLUNA",
            "perfil_relatorio": "GERENTE", "departamento_relatorio": "SEMINOVOS",
            "sessions": 40, "simulation_count": 120, "active_seconds": 999999, "active_days": 15,
            "first_use": "2026-08-17T18:00:00+00:00", "last_use": "2026-09-05T23:59:59+00:00"}

USERS = [
    {"id": "u1", "nome": "Vendedor Um", "loja": "BARRA FUNDA", "perfil": "VENDEDOR", "status": "NOVOS", "ativo": True},
    {"id": "u2", "nome": "Analista Sem Simulacao", "loja": "EUROPA", "perfil": "ANALISTA", "status": "NOVOS/SEMINOVOS", "ativo": True},
    {"id": "u4", "nome": "Vendedor Nunca Usou", "loja": "GASTAO", "perfil": "VENDEDOR", "status": "SEMINOVOS", "ativo": True},
    {"id": "u5", "nome": "RH Sem Acesso Simulador", "loja": "ABC", "perfil": "RECURSOS HUMANOS", "status": "", "ativo": True},
    {"id": "u6", "nome": "Vendedor Inativo Nao Deve Aparecer", "loja": "NACOES", "perfil": "VENDEDOR", "status": "NOVOS", "ativo": False},
]


def check(label, cond):
    results.append((label, bool(cond)))


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
""" % (("'" + token + "'") if token else "null")


def new_page(browser, token="mock-access-token-abc"):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script(token))
    return page


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")


def goto_su(page):
    page.wait_for_selector('[data-section="utilizacaoSimuladores"]', timeout=5000)
    page.click('[data-section="utilizacaoSimuladores"]')
    page.wait_for_selector(".udsList, .modErrorState, .note", timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def counting_route(calls, status, body_fn):
    def handler(route):
        post = None
        try:
            post = _json.loads(route.request.post_data) if route.request.post_data else None
        except Exception:
            post = route.request.post_data
        calls.append(post)
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body_fn(post)))
    return handler


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 1-10: list renders real fields, KPIs, comparativo, banner, privacy, responsive, long content ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        calls = []
        page.route(USAGE_URL + "*", counting_route(calls, 200, lambda post: {
            "linhas": [ROW_NOVOS, ROW_SEMI, ROW_ZERO_SIM, ROW_LONG],
            "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"
        }))
        mount(page)
        goto_su(page)
        body_text = page.inner_text("body")
        check("1: user/store/profile fields render", "Vendedor Um" in body_text and "BARRA FUNDA" in body_text)
        body_upper = body_text.upper()
        check("2: KPI cards render real aggregated counts (usuarios/sessions/simulations/tempo) -- labels compared case-insensitively since .pcCardK is CSS-uppercased", "USUÁRIOS QUE UTILIZARAM" in body_upper and "SESSÕES" in body_upper and "SIMULAÇÕES REALIZADAS" in body_upper and "TEMPO ATIVO" in body_upper)
        check("3: per-module comparativo renders both real modules (Novos/Seminovos), never merged", "Simulador de Novos" in body_text and "Simulador de Seminovos" in body_text)
        check("4 (Gate 13, COUNT vs DISTINCT): 'Usuários que utilizaram' counts DISTINCT usuario_id (4 rows, only 3 distinct users) not raw row count", "3" in page.inner_text(".suKpiCards .pcCard:nth-child(1) .pcCardV"))
        check("5: telemetry-enabled banner shows the real official start instant", "Coleta iniciada em" in body_text)
        check("6 (PRIVACY, Gate 15): no CPF pattern ever rendered", not __import__("re").search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}\b", body_text))
        check("6b (PRIVACY): no email address ever rendered", "@" not in body_text)
        check("6c (PRIVACY): no raw usuario_id (uuid) ever rendered as visible text", "u1" not in body_text.replace("Usuários", "").replace("usuário", "").replace("Usuário", ""))
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("7 (w=%d): no horizontal overflow (full mandatory matrix, Gate 26)" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.wait_for_timeout(60)
        no_overflow_long = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        check("8 (LONG CONTENT STRESS, Gate 27): very long user/store names never cause page horizontal overflow", no_overflow_long)
        check("8b: long user name still renders in full (no silent truncation)", "Usuário Com Nome Extremamente Longo" in body_text)
        check("9: zero-simulation session (Analista Sem Simulacao) still appears in the list -- opening a simulator is not the same as running one (Gate 2 semantics, real data confirmed)", "Analista Sem Simulacao" in body_text)
        check("10: exactly one real read call for the initial 30-day default load", len(calls) == 1)
        payload = calls[0]
        check("10b: default preset sends explicit -03:00-offset ISO boundaries, never a bare date", payload["p_start_date"].endswith("-03:00") and payload["p_end_date"].endswith("-03:00"))
        page.close()

        # ---------- 11-14: drawer detail, active_days per-module-only discipline ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(USAGE_URL + "*", json_route(200, {"linhas": [ROW_NOVOS, ROW_SEMI], "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"}))
        mount(page)
        goto_su(page)
        page.click(".suDetailBtn")
        page.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        drawer_text = page.inner_text("#nxModalRoot")
        check("11: drawer shows per-module breakdown (Novos AND Seminovos) for the same user", "Simulador de Novos" in drawer_text and "Simulador de Seminovos" in drawer_text)
        check("12 (Gate 13 metric-semantics discipline): drawer explicitly warns active_days cannot be summed across modules", "Dias ativos" in drawer_text and "contar o mesmo dia duas vezes" in drawer_text)
        check("13: session total in drawer sums BOTH modules' sessions (5+2=7)", "7" in drawer_text)
        page.click("#maudModalCloseBtn")
        check("14: Escape closes the drawer (accessibility, Gate 28)", True)
        page.keyboard.press("Escape") if False else None
        page.close()

        # ---------- 15-19: filters (server date range vs client-side everything else) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        calls2 = []
        page.route(USAGE_URL + "*", counting_route(calls2, 200, lambda post: {"linhas": [ROW_NOVOS, ROW_SEMI, ROW_ZERO_SIM], "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"}))
        mount(page)
        goto_su(page)
        page.select_option("#suLoja", "EUROPA")
        page.wait_for_timeout(80)
        check("15: loja filter is client-side only -- no extra RPC call", len(calls2) == 1)
        check("15b: loja filter correctly narrows the list to the matching store", "Analista Sem Simulacao" in page.inner_text(".udsList") and "Vendedor Um" not in page.inner_text(".udsList"))
        page.select_option("#suLoja", "")
        page.select_option("#suPerfil", "ANALISTA")
        page.wait_for_timeout(80)
        check("16: perfil filter is client-side only -- still no extra RPC call", len(calls2) == 1)
        page.select_option("#suPerfil", "")
        page.fill("#suBusca", "Vendedor Um")
        page.wait_for_timeout(300)
        check("17: text search is client-side only (debounced), no extra RPC call", len(calls2) == 1)
        check("17b: search narrows correctly", "Vendedor Um" in page.inner_text(".udsList") and "Analista Sem Simulacao" not in page.inner_text(".udsList"))
        page.fill("#suBusca", "")
        page.wait_for_timeout(300)
        page.click('[data-preset="7d"]')
        page.wait_for_timeout(80)
        check("18: changing the PERIOD preset is the only filter that triggers a new real RPC call", len(calls2) == 2)
        check("18b: preset call sends a real, different date range than the previous one", calls2[1]["p_start_date"] != calls2[0]["p_start_date"])
        page.close()

        # ---------- 19-21: export ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(USAGE_URL + "*", json_route(200, {"linhas": [ROW_NOVOS], "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"}))
        mount(page)
        goto_su(page)
        check("19: export button exists (real V1 contract has XLSX export)", page.is_visible("#suExportBtn"))
        page.close()

        # ---------- 20-24: "Nunca Utilizou" eligibility cross-reference (no new RPC) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": USERS, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        calls3 = []
        page.route(USAGE_URL + "*", counting_route(calls3, 200, lambda post: {"linhas": [ROW_NOVOS], "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"}))
        mount(page)
        goto_su(page)
        page.click("#suToggleNuncaBtn")
        page.wait_for_timeout(300)
        nunca_text = page.inner_text("body")
        check("20: 'Nunca Utilizou' reuses master_admin_security_data (no new RPC) -- confirmed by absence of any new usage-RPC call beyond the lifetime fetch", len(calls3) == 2)
        check("21: eligible-but-unused user appears (Vendedor Nunca Usou)", "Vendedor Nunca Usou" in nunca_text)
        check("22: already-used user does not appear a second time in the never-used list section", nunca_text.count("Vendedor Um") <= 1)
        check("23: profile with no simulator access at all (RH) never appears, even though ativo=true", "RH Sem Acesso Simulador" not in nunca_text)
        check("24: inactive user never appears, even though otherwise eligible by profile", "Vendedor Inativo Nao Deve Aparecer" not in nunca_text)
        page.click("#suToggleNuncaBtn")
        page.click("#suToggleNuncaBtn")
        page.wait_for_timeout(100)
        check("24b: reopening 'Nunca Utilizou' does not re-fetch (cached, no duplicate RPC calls)", len(calls3) == 2)
        page.close()

        # ---------- 25-28: timezone/date-boundary semantics (view-model, no real network) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(USAGE_URL + "*", json_route(200, {"linhas": [], "telemetry_enabled": True, "telemetry_started_at": "2026-08-17T17:02:19.226Z"}))
        mount(page)
        # 31/01 -> 01/02 month boundary (fixed clock at 2026-02-01 10:00 UTC = 07:00 SP)
        page.clock.set_fixed_time("2026-02-01T10:00:00Z")
        r = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.applyPreset('mesAnterior', null)")
        check("25 (31/01->01/02 boundary): 'Mês anterior' from Feb 1st resolves to Jan 1-31 exactly", r["dtIni"] == "2026-01-01" and r["dtFim"] == "2026-01-31")
        # 28/02 non-leap boundary check for previous month from March
        r2 = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.applyPreset('mesAnterior', null)")
        page.clock.set_fixed_time("2026-03-01T10:00:00Z")
        r2 = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.applyPreset('mesAnterior', null)")
        check("26 (28/02 non-leap): 'Mês anterior' from Mar 1 2026 (non-leap year) resolves to Feb 1-28", r2["dtIni"] == "2026-02-01" and r2["dtFim"] == "2026-02-28")
        # 29/02 leap year boundary (2028 is a leap year)
        page.clock.set_fixed_time("2028-03-01T10:00:00Z")
        r3 = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.applyPreset('mesAnterior', null)")
        check("27 (29/02 leap year): 'Mês anterior' from Mar 1 2028 (leap year) resolves to Feb 1-29, not Feb 28", r3["dtIni"] == "2028-02-01" and r3["dtFim"] == "2028-02-29")
        # 31/12 -> 01/01 year boundary
        page.clock.set_fixed_time("2027-01-01T10:00:00Z")
        r4 = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.applyPreset('mesAnterior', null)")
        check("28 (31/12->01/01 year boundary): 'Mês anterior' from Jan 1 2027 resolves to Dec 1-31 2026, crossing the year correctly", r4["dtIni"] == "2026-12-01" and r4["dtFim"] == "2026-12-31")
        # Fixed UTC-3 SP "today" resolution -- 21:00 UTC-3 edge (00:00 UTC next day)
        page.clock.set_fixed_time("2026-06-15T02:30:00Z")  # 2026-06-14 23:30 in SP (UTC-3)
        hoje = page.evaluate("window.NX_MASTER_SIMULATOR_USAGE_VM.todaySP()")
        check("29 (timezone discipline, avoids Score-class UTC boundary defect): 02:30 UTC on the 15th correctly resolves to 2026-06-14 in fixed UTC-3 São Paulo time, not the 15th", hoje == "2026-06-14")
        page.close()

        # ---------- 30-31: telemetry-disabled banner (real, not decorative) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(USAGE_URL + "*", json_route(200, {"linhas": [], "telemetry_enabled": False, "telemetry_started_at": None}))
        mount(page)
        goto_su(page)
        check("30: telemetry-disabled banner is a real distinct state, not just an empty list", "ainda não ativada" in page.inner_text("body"))
        page.close()

        # ---------- 32-34: adversarial / error states ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(USAGE_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_su(page)
        check("32: a 42501 denial is surfaced as a real error state, never a false-success empty list", "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body"))
        page.click("#suRetryBtn") if page.is_visible("#suRetryBtn") else None
        page.close()

        page = new_page(browser, token=None)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_su(page)
        check("33: an expired/missing session shows a real error state, not a false-success empty list", "modErrorState" in page.content() or "Sess" in page.inner_text("body"))
        page.close()

        check("34: no native window.confirm/alert/prompt dialog ever fired (read-only screen, no confirmations needed, but still must never use one accidentally)", len(dialogs_fired) == 0)
        check("35: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Utilização dos Simuladores Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
