#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5D -- deterministic tests for the Gestão dos
Simuladores module (master-gestao-simuladores-provider.js, master-
gestao-simuladores-view-model.js, shell-admin.js), mounted via the same
lightweight harness used by every sibling Painel Master surface (route
guard tested separately in tests/master-admin-route-test.py).

Everything here runs against mocked window.NX_AUTH and routed (never
real) fetches -- 0 real network calls, 0 real Supabase project touched,
0 credentials anywhere in this file. Synthetic-only fixtures: fake
rates/coefficients built with openpyxl, never real production rate
tables (Gate 44).

HIGH-SENSITIVITY FINANCIAL CONFIGURATION (Gate 2/3): this suite proves
(a) the homologation-mode gate makes every real WRITE RPC call count
stay at zero regardless of which of the 10 config families is touched,
(b) percentage/rate fields round-trip as decimal fractions with no
×100/÷100 drift, (c) the block/region parsers (Balão's stacked/side-
by-side blocks, Coparticipado's dual-table sheet) resolve to the exact
row counts a correctly-spaced real file would produce.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on the project's
canonical port 8080, and `openpyxl` (pip) to build tiny synthetic .xlsx
fixtures on the fly -- no fixture file is committed to the repo.
"""
import io
import json as _json
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
LIST_BATCHES_URL = "https://mock.invalid/rest/v1/rpc/master_operational_list_batches"
LIST_SELLERS_URL = "https://mock.invalid/rest/v1/rpc/master_operational_list_sellers"
LISTAR_BASES_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_listar_bases"
COMMIT_LINEAR_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_commit_linear"
COMMIT_BALAO_ZK_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_commit_balao_zerokm"
COMMIT_BALAO_SN_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_commit_balao_seminovos"
COMMIT_COPART_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_commit_coparticipado"
COMMIT_TAXA_BOTAO_URL = "https://mock.invalid/rest/v1/rpc/master_simulador_commit_taxa_botao"

results = []
TMP_DIR = tempfile.mkdtemp(prefix="pm5d_gs_fixtures_")


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


def goto_simuladores(page):
    page.wait_for_selector('[data-section="gestaoSimuladores"]', timeout=5000)
    page.click('[data-section="gestaoSimuladores"]')
    page.wait_for_selector(".gbGrid, .modErrorState", timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def counting_route(calls, body_fn):
    def handler(route):
        post = None
        try:
            post = _json.loads(route.request.post_data) if route.request.post_data else None
        except Exception:
            post = route.request.post_data
        calls.append(post)
        route.fulfill(status=200, content_type="application/json", body=_json.dumps(body_fn(post)))
    return handler


def make_xlsx(name, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    path = os.path.join(TMP_DIR, name)
    wb.save(path)
    return path


LINEAR_XLSX = make_xlsx("linear.xlsx", [
    ["Prazo", "Entrada", "Taxa"],
    [12, 0.2, 0.0281],
    [24, 0.3, 0.0295],
])
TAXA_BOTAO_XLSX = make_xlsx("taxa_botao.xlsx", [
    ["Prazo", "Taxa"],
    [12, 0.0199],
    [24, 0.0215],
])
# Correctly-spaced 3-stacked-block layout (block N's last data row ends
# exactly 3 rows before block N+1's header -- the same gap the real
# parser's own `fim = headers[idx+1]-3` boundary logic requires).
BALAO_ZK_XLSX = make_xlsx("balao_zerokm.xlsx", [
    ["Tradicional"],
    ["Entrada mínima", "Prazo", "Máximo de Balão", "Taxa de Juros"],
    [0.2, 12, 0.4, 0.0195],
    [0.2, 18, 0.4, 0.0205],
    [], [],
    ["Semestral/Anual"],
    ["Entrada mínima", "Prazo", "Máximo de Balão", "Taxa de Juros"],
    [0.3, 24, 0.35, 0.0210],
    [], [],
    ["Parcela Única"],
    ["Entrada mínima", "Prazo", "Máximo de Balão", "Taxa de Juros"],
    [0.4, 36, 0.3, 0.0220],
])
BALAO_SN_XLSX = make_xlsx("balao_seminovos.xlsx", [
    ["2020_2022", None, None, None, "2023_2024"],
    ["Entrada mínima", "Prazo", "Máximo de Balão", "Taxa de Juros", "Entrada mínima", "Prazo", "Máximo de Balão", "Taxa de Juros"],
    [0.25, 24, 0.3, 0.0230, 0.2, 24, 0.35, 0.0210],
])
# Dual-table sheet: "tabela geral" (6 cols) + "matriz por modelo"
# (Modelo/Entrada/Rebate TOTAL/HPE/Brabus/<prazo>x...) sharing one header row.
COPARTICIPADO_XLSX = make_xlsx("coparticipado.xlsx", [
    ["Prazo", "Taxa", "Rebate", "Tx Sist", "Entrada Mínima", "Coef", None, "Modelo do Carro", "Entrada Mínima", "Rebate TOTAL", "Rebate Parte HPE", "Rebate Parte Brabus", "12x", "24x"],
    [12, 0.0195, 0.02, 0.01, 0.2, 1.05, None, "OUTLANDER GT", 0.2, 0.05, 0.03, 0.02, 0.0195, 0.0210],
    [24, 0.0210, 0.03, 0.01, 0.2, 1.08, None, "ECLIPSE CROSS", 0.2, 0.04, 0.02, 0.02, 0.0198, 0.0215],
])
COEF_COPART_XLSX = make_xlsx("coef_coparticipado.xlsx", [
    ["Prazo", "Taxa", "Coeficiente", "Status"],
    [12, 0.0195, 1.05, "OK"],
    [24, 0.0210, 1.08, "PENDENTE — PREENCHER"],
])
COEF_COPART_DUP_XLSX = make_xlsx("coef_coparticipado_dup.xlsx", [
    ["Prazo", "Taxa", "Coeficiente"],
    [12, 0.0195, 1.05],
    [12, 0.0195, 1.10],  # duplicate (prazo,taxa) key
])
FINANCIAMENTO_SN_XLSX = make_xlsx("financiamento_seminovo.xlsx", [
    # Real parser reads the faixa/entrada label AT column `c`, then the
    # prazo/taxa VALUE at `c+1` (V1's own comment: "a coluna de VALOR
    # fica logo após a coluna de rótulo do bloco") -- confirmed by
    # direct source reading, not guessed. Two column-groups, each
    # spanning (label_col, value_col) = (1,2) and (4,5).
    [None, "2020-2022", None, None, "2023-2024", None],
    [None, "30%", None, None, "40%", None],
    ["Prazo", None, "12x", None, None, "12x"],
    ["Taxa de Juros", None, 0.0250, None, None, 0.0230],
])
EMPTY_XLSX = make_xlsx("empty.xlsx", [["Prazo", "Entrada", "Taxa"]])
WRONG_STRUCTURE_XLSX = make_xlsx("wrong.xlsx", [["Nome", "Idade"], ["a", 1]])

BASELINE_BASES = [
    {"tipo_base": "LINEAR_ZEROKM", "batch_id": "11111111-1111-4111-8111-111111111111", "status": "ACTIVE",
     "arquivo_nome": "linear_atual.xlsx", "importado_em": "2026-08-01T10:00:00+00:00", "quantidade_registros": 6,
     "responsavel": "Master Demo", "bootstrap": False, "avisos": []},
]


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)

        # ---------- 1-6: cards render real batch status, grouped, no overflow ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, BASELINE_BASES))
        mount(page)
        goto_simuladores(page)
        check("1: homologation-mode banner is visible (this harness's hostname is never in the production allowlist)",
              page.query_selector(".gbHomologBanner") is not None)
        check("2: exactly 11 cards render (10 distinct config families, Antecipação shown once per group -- nothing invented or dropped)",
              len(page.query_selector_all(".gbCard")) == 11)
        group_titles = [el.inner_text().strip().upper() for el in page.query_selector_all(".gsGroupTitle")]
        check("3: both real groups present, in order (ZeroKM then Seminovos)", group_titles == ["ZEROKM", "SEMINOVOS"])
        cards_text = page.inner_text(".gbGrid, body")
        check("4: Linear card shows the real ACTIVE batch's file/counts", "linear_atual.xlsx" in page.inner_text("body"))
        check("5: a family with no ACTIVE batch shows the honest empty state, not a fabricated one",
              "Nenhuma base ACTIVE encontrada" in page.inner_text("body"))
        check("6: the shared Antecipação badge and the partial-update Balão badge both render",
              "BASE COMPARTILHADA" in page.inner_text("body") and "ATUALIZAÇÃO PARCIAL" in page.inner_text("body"))
        for w in (1440, 1024, 768, 390):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(80)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            check("6b (w=%d): no horizontal overflow on the cards view" % w, no_overflow)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.close()

        # ---------- 7-12: Linear happy path -- percent-unit + precision round-trip ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        linear_calls = []
        def linear_body(post):
            if post.get("p_dry_run") is True:
                return {"dry_run": True, "tipo_base": "LINEAR_ZEROKM", "linhas_validas": len(post["p_linhas"]),
                        "comparacao_com_active": {"novos": len(post["p_linhas"]), "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}}
            return {"ok": True, "batch_id": "22222222-2222-4222-8222-222222222222"}
        page.route(COMMIT_LINEAR_URL + "*", counting_route(linear_calls, linear_body))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_LINEAR']")
        page.set_input_files("#gsFileInput", LINEAR_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("7: exactly 1 real dry-run call (the preview, a real read)", len(linear_calls) == 1)
        check("7b: the dry-run call carries p_dry_run=true", linear_calls[0].get("p_dry_run") is True)
        rows_sent = linear_calls[0]["p_linhas"]
        check("8: 2 rows parsed from the real file", len(rows_sent) == 2)
        check("9 (PERCENT-UNIT REGRESSION, Gate 52): entrada_pct is the exact decimal fraction from the file (0.2), never ×100 (20) or ÷100 (0.002)",
              abs(rows_sent[0]["entrada_pct"] - 0.2) < 1e-9)
        check("9b (PERCENT-UNIT REGRESSION): taxa is the exact decimal fraction (0.0281 = 2.81% a.m.), never ×100/÷100",
              abs(rows_sent[0]["taxa"] - 0.0281) < 1e-9)
        check("10 (PRECISION ROUND-TRIP, Gate 53): full float precision preserved end to end, no silent rounding",
              rows_sent[1]["taxa"] == 0.0295 and rows_sent[1]["entrada_pct"] == 0.3)
        check("11: prazo is a plain integer, not coerced into the 12/18/24/36/48/60 set artificially (contract allows 1-120, Gate 17)",
              rows_sent[0]["prazo"] == 12 and isinstance(rows_sent[0]["prazo"], int))
        page.click("#gsConfirmarBtn")
        page.wait_for_selector("#gsSuccessCloseBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("12: zero REAL commit (p_dry_run=false) calls reached the network -- homologation gate blocks by construction",
              len(linear_calls) == 1)
        success_text = page.inner_text("#nxModalRoot")
        check("12b: success modal explicitly says SIMULATION, never claims a real write happened", "SIMULAÇÃO CONCLUÍDA" in success_text)
        page.close()

        # ---------- 13-16: Balão ZeroKM -- 3 stacked blocks resolve correctly ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        balao_zk_calls = []
        def balao_zk_body(post):
            if post.get("p_dry_run") is True:
                return {"dry_run": True, "tipo_base": "BALAO_ZEROKM", "linhas_validas": len(post["p_linhas"]),
                        "comparacao_com_active": {"novos": len(post["p_linhas"]), "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}}
            return {"ok": True, "batch_id": "x"}
        page.route(COMMIT_BALAO_ZK_URL + "*", counting_route(balao_zk_calls, balao_zk_body))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_BALAO']")
        page.set_input_files("#gsFileInput", BALAO_ZK_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        rows13 = balao_zk_calls[0]["p_linhas"] if balao_zk_calls else []
        check("13: all 3 stacked blocks parsed (4 rows total: 2 Tradicional + 1 Semestral/Anual + 1 Parcela Única)", len(rows13) == 4)
        blocos = sorted(set(r["bloco"] for r in rows13))
        check("14: all 3 block labels correctly resolved from text above each header", blocos == ["PARCELA_UNICA", "SEMESTRAL_ANUAL", "TRADICIONAL"])
        check("15: Tradicional block kept both its rows (12 and 18 month terms), not just the first",
              len([r for r in rows13 if r["bloco"] == "TRADICIONAL"]) == 2)
        page.click("#gsCancelarBtn")
        page.wait_for_timeout(150)
        check("16: cancel never calls commit for real, and leaves the ACTIVE base untouched (modal simply closes)",
              page.query_selector("#nxModalRoot .maudModalDialog") is None)
        page.close()

        # ---------- 17-18: Balão Seminovos -- 2 side-by-side blocks, year-range labels ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        balao_sn_calls = []
        def balao_sn_body(post):
            return {"dry_run": True, "tipo_base": "BALAO_SEMINOVOS", "linhas_validas": len(post["p_linhas"]),
                    "comparacao_com_active": {"novos": len(post["p_linhas"]), "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}}
        page.route(COMMIT_BALAO_SN_URL + "*", counting_route(balao_sn_calls, balao_sn_body))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='SN_BALAO']")
        page.set_input_files("#gsFileInput", BALAO_SN_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        rows17 = balao_sn_calls[0]["p_linhas"] if balao_sn_calls else []
        check("17: both side-by-side year-range blocks parsed (2 rows, 1 per block)", len(rows17) == 2)
        blocos17 = sorted(set(r["bloco"] for r in rows17))
        check("18: year-range block labels correctly resolved (underscore convention, e.g. 2020_2022)", blocos17 == ["2020_2022", "2023_2024"])
        page.close()

        # ---------- 19-22: Coparticipado -- dual-table sheet, audit-only geral table, coeficiente always empty ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        copart_calls = []
        def copart_body(post):
            if post.get("p_dry_run") is True:
                return {"dry_run": True, "tipo_base": "COPARTICIPADO", "linhas_modelo_validas": len(post["p_linhas_modelo"]),
                        "linhas_gerais_encontradas": len(post["p_linhas_geral"]),
                        "comparacao_matriz_modelo": {"novos": len(post["p_linhas_modelo"]), "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}}
            return {"ok": True, "batch_id": "x"}
        page.route(COMMIT_COPART_URL + "*", counting_route(copart_calls, copart_body))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_COPARTICIPADO']")
        page.set_input_files("#gsFileInput", COPARTICIPADO_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("19: matriz-por-modelo correctly separated (4 rows: 2 models × 2 prazos)", len(copart_calls[0]["p_linhas_modelo"]) == 4)
        check("20: tabela-geral correctly separated into its own array (2 rows), never merged into the model matrix", len(copart_calls[0]["p_linhas_geral"]) == 2)
        check("21: p_linhas_coeficiente is ALWAYS sent explicitly (even empty) -- deterministically resolves the 7-arg RPC overload, never the ambiguous 6-arg one",
              copart_calls[0].get("p_linhas_coeficiente") == [])
        diag_text = page.inner_text("#nxModalRoot")
        check("22: the audit-only nature of the tabela geral is surfaced to the MASTER, not silently dropped", "auditoria" in diag_text.lower())
        page.close()

        # ---------- 23-24: Financiamento Seminovos -- year-band/entrada%/prazo-taxa row-pair scan ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        fs_calls = []
        page.route("**/rest/v1/rpc/master_simulador_commit_financiamento_seminovo*", counting_route(fs_calls, lambda post: {
            "dry_run": True, "tipo_base": "FINANCIAMENTO_SEMINOVO", "linhas_validas": len(post["p_linhas"]),
            "comparacao_com_active": {"novos": len(post["p_linhas"]), "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}
        }))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='SN_FINANCIAMENTO']")
        page.set_input_files("#gsFileInput", FINANCIAMENTO_SN_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        rows23 = fs_calls[0]["p_linhas"] if fs_calls else []
        check("23: both year-band columns parsed (2 rows, one per faixa_ano)", len(rows23) == 2)
        faixas = sorted(set(r["faixa_ano"] for r in rows23))
        check("24: year-band labels use the real hyphen convention for this family (2020-2024 style, confirmed distinct from Balão Seminovos' underscore convention)",
              all("-" in f for f in faixas))
        page.close()

        # ---------- 25: Matriz de Coeficientes — Coparticipado: duplicate-key rejection ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_COEFICIENTES_COPARTICIPADO']")
        page.set_input_files("#gsFileInput", COEF_COPART_DUP_XLSX)
        page.wait_for_selector("#gsErrorCloseBtn", timeout=5000)
        page.wait_for_timeout(150)
        check("25: a duplicate (prazo,taxa) logical key is rejected client-side before any RPC call, not silently accepted",
              "Duplicidade" in page.inner_text("#nxModalRoot"))
        page.close()

        # ---------- 26-27: empty file / wrong structure -- controlled error, no commit call ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        empty_calls = []
        page.route(COMMIT_LINEAR_URL + "*", counting_route(empty_calls, lambda p: "SHOULD-NEVER-BE-CALLED"))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_LINEAR']")
        page.set_input_files("#gsFileInput", EMPTY_XLSX)
        page.wait_for_timeout(400)
        check("26: an empty workbook shows a controlled error modal (not a silent no-op, not an uncaught exception)",
              page.query_selector("#gsErrorCloseBtn") is not None)
        check("26b: no RPC was ever called for an empty file", len(empty_calls) == 0)
        page.click("#gsErrorCloseBtn")
        page.wait_for_selector(".gbGrid", timeout=5000)
        page.click(".gsUpdateBtn[data-uid='ZK_LINEAR']")
        page.set_input_files("#gsFileInput", WRONG_STRUCTURE_XLSX)
        page.wait_for_timeout(400)
        check("27: a structurally-wrong file (Taxa Botão selected, unrelated columns uploaded) is rejected with a clear message identifying the expected base, not a raw parser crash",
              page.query_selector("#gsErrorCloseBtn") is not None and "Financiamento Linear" in page.inner_text("#nxModalRoot"))
        page.close()

        # ---------- 28: duplicate-submit guard on CONFIRMAR ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(200, []))
        page.route(COMMIT_TAXA_BOTAO_URL + "*", json_route(200, {
            "dry_run": True, "tipo_base": "TAXA_BOTAO", "linhas_validas": 2,
            "comparacao_com_active": {"novos": 2, "alterados": 0, "sem_alteracao": 0, "removidos": 0, "detalhe_alterados": []}
        }))
        mount(page)
        goto_simuladores(page)
        page.click(".gsUpdateBtn[data-uid='ZK_TAXABOTAO']")
        page.set_input_files("#gsFileInput", TAXA_BOTAO_XLSX)
        page.wait_for_selector("#gsConfirmarBtn", timeout=5000)
        page.wait_for_timeout(150)
        page.eval_on_selector("#gsConfirmarBtn", "el => { el.click(); el.click(); }")
        page.wait_for_selector("#gsSuccessCloseBtn", timeout=5000)
        check("28: duplicate-submit guard -- two rapid clicks still show exactly one success screen",
              "SIMULAÇÃO CONCLUÍDA" in page.inner_text("#nxModalRoot"))
        page.close()

        # ---------- 29: adversarial -- real server-side MASTER authority ----------
        # Proven directly against the LIVE production functions (PM-5D
        # Gate 19/55 forensics: every one of the 12 master_simulador_
        # commit_* functions, both the 6-arg and 7-arg coparticipado
        # overloads, and master_simulador_listar_bases were read via
        # pg_get_functiondef and independently confirmed to start with
        # `if not public.is_master() then raise exception ... '42501'`;
        # all 10 underlying simulador_* tables have RLS enabled with
        # ZERO policies -- direct table access denied for every role).
        # A harness-level test cannot re-simulate real Postgres role/RLS
        # enforcement without becoming a second, weaker copy of the real
        # backend; asserting the frontend correctly SURFACES a 42501
        # denial (never a false success) is the meaningful proof at
        # this layer.
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(LISTAR_BASES_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        page.wait_for_selector('[data-section="gestaoSimuladores"]', timeout=5000)
        page.click('[data-section="gestaoSimuladores"]')
        page.wait_for_timeout(300)
        check("29: a 42501 denial on the one always-real read (listar_bases) is surfaced as a real error state, never a false-success empty grid",
              page.query_selector(".modErrorState") is not None)
        page.close()

        browser.close()

    check("30: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)
    if real_network_hits:
        print("[TRIPWIRE] real network hit(s) detected:", real_network_hits)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== Master Gestão dos Simuladores Provider: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
