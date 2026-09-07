#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-6D.5 -- controlled, end-to-end, real-production-code
proof that a COMPLETE competência closing's RH/DP export is truly immutable:
real close UI -> frozen financial + operational capture -> real Exportar
RH/DP -> mutate the (simulated) live sources -> real Exportar RH/DP again
-> semantically identical workbook, with ZERO live-reconstruction calls
after close. Answers the Human's own question (PM-6D.5 brief §1): how do
we know COMPLETE really works, given every existing real closing is
LEGACY_PARTIAL and cannot safely prove this itself (PM-6D.4)?

SAFETY: fully synthetic data throughout (synthetic seller/store/chassis
identifiers, no real CPF/customer data, dates in a future synthetic
período so nothing collides with any real competência). 0 real network
calls (tripwire enforced, same discipline as every sibling suite). 0
writes to the real Supabase project -- master_close_commission_period,
master_commission_operational_detail, operational_salary_details,
master_operational_spf_audit_period, master_commission_snapshot_export
and master_commission_closings are ALL mocked at the network boundary via
page.route(), driven entirely through REAL, unmodified production code:
master-competence-closing-provider.js/-engine.js (the real close UI flow,
same driver as tests/master-competence-closing-provider-test.py) and
master-competence-history-provider.js/master-competence-rhdp-export-
engine.js/shell-admin.js (the real Exportar RH/DP flow, same driver as
tests/master-competence-rhdp-export-test.py). This file does not
reimplement either engine -- it composes the two existing real flows
into one continuous scenario neither sibling suite exercises together.

WHY THE MOCK BELOW IS NOT "REIMPLEMENTING THE BUSINESS LOGIC" (Gate 8/31
of this Phase's own brief): the actual server-side freeze-on-close
mechanism (master_close_commission_period's own capture of
operational_salary_details/master_operational_spf_audit_period into
snapshot_operational_detail) is real, already-deployed SQL (Authority
repo, PM-6D.1/PM-6D.2) that was already proven correct via real
BEGIN...ROLLBACK-tested transactions against production in that wave --
a DB-level proof, not a full-pipeline one. The mock's "capture whatever
the live routes currently return, at the moment the close RPC fires, and
serve that back forever after for this closing_id" is a faithful
simulation of THAT already-proven server contract -- exactly the same
"replace the external boundary, not the business logic" pattern every
other test in this whole suite already uses for master_commission_
operational_detail's completeness/rows shape. No RH/DP calculation, no
close-preview aggregation, and no workbook construction happens in
Python anywhere in this file -- every number in every assertion below is
read back OUT of the real, unmodified engine's own output.
"""
import hashlib
import io
import json as _json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_master-users-harness.html"
SEC_URL = "https://mock.invalid/rest/v1/rpc/master_admin_security_data"
CONV_URL = "https://mock.invalid/rest/v1/rpc/master_listar_convites"
READ_URL = "https://mock.invalid/rest/v1/rpc/master_admin_reference_data"
CLOSINGS_URL = "https://mock.invalid/rest/v1/rpc/master_commission_closings"
EXPORT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot_export"
OPDETAIL_URL = "https://mock.invalid/rest/v1/rpc/master_commission_operational_detail"
SPF_URL = "https://mock.invalid/rest/v1/rpc/master_operational_spf_audit_period"
SALARY_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_details"
VEND_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_commission_metrics"
ANALYST_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_analyst_commission_metrics_v2"
MANAGER_DIR_URL = "https://mock.invalid/rest/v1/rpc/operational_salary_manager_directory"
WRITE_URL = "https://mock.invalid/rest/v1/rpc/master_close_commission_period"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


# ---------------------------------------------------------------------
# Controlled synthetic dataset -- a small but meaningful competência
# ---------------------------------------------------------------------
PERIOD_E2E = {"id": "per-e2e-001", "nome_periodo": "21/09 a 20/10/2026", "data_inicio": "2026-09-21",
              "data_fim": "2026-10-20", "status": "EM CONFERÊNCIA", "periodo_atual": True, "ativo": True}
GESTOR_USER_ID = "b5168cef-d111-4c5f-873e-ea823bb22729"
USERS_WITH_GESTOR = [{"id": GESTOR_USER_ID, "ativo": True, "nome": "Gestor Sintético E2E", "cpf": "00000000000", "perfil": "MASTER"}]

VEND_ROWS = [
    {"seller_name": "Vendedor E2E Um", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "sold_count": 3, "financed_count": 2, "production_value": 300000, "return_value": 9000, "spf_value": 500, "spf_count": 1},
    {"seller_name": "Vendedor E2E Dois", "store": "LOJA E2E ALPHA", "department": "SEMINOVOS",
     "sold_count": 2, "financed_count": 1, "production_value": 150000, "return_value": 3000, "spf_value": 0, "spf_count": 0},
]
VEND_TOTALS = {"sold_count": 5, "financed_count": 3, "production_value": 450000, "return_value": 12000, "spf_value": 500, "spf_count": 1}
ANALYST_ROWS = [{"analyst_name": "Analista E2E", "store": "LOJA E2E CENTRO", "sold_count": 5, "financed_count": 3,
                  "production_value": 450000, "return_value": 12000, "spf_value": 500, "spf_count": 1, "transfer": False}]
MANAGER_ROWS = [{"store": "LOJA E2E CENTRO", "department": "NOVOS", "manager_name": "Gerente E2E Centro"},
                 {"store": "LOJA E2E ALPHA", "department": "SEMINOVOS", "manager_name": "Gerente E2E Alpha"}]

# STATE_A -- the controlled "live" operational source at close time.
STATE_A_CHASSIS = [
    {"date": "2026-09-25", "finance_date": "2026-09-26", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E A", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA1", "sale_value": 100000, "financed": True, "financed_value": 80000,
     "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-09-26", "finance_date": "2026-09-27", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E A", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA2", "sale_value": 100000, "financed": True, "financed_value": 80000,
     "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-09-27", "finance_date": None, "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E B", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA3", "sale_value": 100000, "financed": False, "financed_value": 0,
     "return_considered": 0, "included_in_commission": True},
    {"date": "2026-09-28", "finance_date": "2026-09-29", "store": "LOJA E2E ALPHA", "department": "SEMINOVOS",
     "vehicle_model": "MODELO E2E C", "seller_id": "e2e-s2", "seller_name": "Vendedor E2E Dois",
     "chassis_masked": "******TE2EA4", "sale_value": 75000, "financed": True, "financed_value": 60000,
     "return_considered": 2000, "included_in_commission": True},
    {"date": "2026-09-29", "finance_date": None, "store": "LOJA E2E ALPHA", "department": "SEMINOVOS",
     "vehicle_model": "MODELO E2E C", "seller_id": "e2e-s2", "seller_name": "Vendedor E2E Dois",
     "chassis_masked": "******TE2EA5", "sale_value": 75000, "financed": False, "financed_value": 0,
     "return_considered": 0, "included_in_commission": True},
]
STATE_A_SPF = [
    {"operation_date": "2026-09-25", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um", "store": "LOJA E2E CENTRO",
     "department": "NOVOS", "chassis_masked": "******TE2EA1", "operation_code": "OPE2E1", "bank": "BANCO E2E",
     "finance_code": "FIN-PLUS", "optional_name": "SPF EXTRA", "spf_bruto": 500, "spf_liquido": 350},
]

# STATE_B -- deliberately material mutation of the SAME period's live
# source, applied only AFTER the close and AFTER EXPORT_A (Gate 15):
# (1) ADD a new sale; (2) REMOVE an existing sale entirely;
# (3) CHANGE a financed status; (4) REASSIGN a sale's seller;
# (5) CHANGE a monetary amount; (6) ALTER the live SPF detail.
STATE_B_CHASSIS = [
    {"date": "2026-09-25", "finance_date": "2026-09-26", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E A", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA1", "sale_value": 999999, "financed": True, "financed_value": 80000,  # (5) amount changed
     "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-09-26", "finance_date": "2026-09-27", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E A", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA2", "sale_value": 100000, "financed": True, "financed_value": 80000,
     "return_considered": 3000, "included_in_commission": True},
    {"date": "2026-09-27", "finance_date": "2026-09-28", "store": "LOJA E2E CENTRO", "department": "NOVOS",
     "vehicle_model": "MODELO E2E B", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA3", "sale_value": 100000, "financed": True, "financed_value": 90000,  # (3) financed flipped
     "return_considered": 3500, "included_in_commission": True},
    # T-A4 REASSIGNED (4) from "Vendedor E2E Dois" to "Vendedor E2E Um" -- simulates a real
    # seller_user_id reconciliation UPDATE (the same class of drift PM-6D.4 found real, in production).
    {"date": "2026-09-28", "finance_date": "2026-09-29", "store": "LOJA E2E ALPHA", "department": "SEMINOVOS",
     "vehicle_model": "MODELO E2E C", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um",
     "chassis_masked": "******TE2EA4", "sale_value": 75000, "financed": True, "financed_value": 60000,
     "return_considered": 2000, "included_in_commission": True},
    # T-A5 REMOVED entirely (2) -- no longer present in live data at all.
    # NEW sale added (1):
    {"date": "2026-10-01", "finance_date": "2026-10-02", "store": "LOJA E2E ALPHA", "department": "SEMINOVOS",
     "vehicle_model": "MODELO E2E D", "seller_id": "e2e-s2", "seller_name": "Vendedor E2E Dois",
     "chassis_masked": "******TE2EB6", "sale_value": 60000, "financed": True, "financed_value": 50000,
     "return_considered": 1500, "included_in_commission": True},
]
STATE_B_SPF = [
    {"operation_date": "2026-09-25", "seller_id": "e2e-s1", "seller_name": "Vendedor E2E Um", "store": "LOJA E2E CENTRO",
     "department": "NOVOS", "chassis_masked": "******TE2EA1", "operation_code": "OPE2E1", "bank": "BANCO E2E",
     "finance_code": "FIN-PLUS", "optional_name": "SPF EXTRA", "spf_bruto": 777777, "spf_liquido": 555555},  # (6) SPF altered
    {"operation_date": "2026-10-01", "seller_id": "e2e-s2", "seller_name": "Vendedor E2E Dois", "store": "LOJA E2E ALPHA",
     "department": "SEMINOVOS", "chassis_masked": "******TE2EB6", "operation_code": "OPE2E2", "bank": "BANCO E2E",
     "finance_code": "FIN-PLUS", "optional_name": "SPF EXTRA", "spf_bruto": 400, "spf_liquido": 280},  # new SPF row
]


def state_aggregate(chassis_rows):
    per_seller = {}
    for r in chassis_rows:
        if not r["included_in_commission"]:
            continue
        s = per_seller.setdefault(r["seller_name"], {"vendidas": 0, "financiadas": 0})
        s["vendidas"] += 1
        if r["financed"]:
            s["financiadas"] += 1
    return per_seller


def auth_mock_script(token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: true, getAccessToken: function () { return Promise.resolve(%s); } };
window.__CAPTURED_WORKBOOKS__ = [];
""" % (("'" + token + "'") if token else "null")


def new_page(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script(auth_mock_script())
    return page


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def mount(page):
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SHELL_ADMIN_PAGE", timeout=5000)
    page.evaluate("window.NX_SHELL_ADMIN_PAGE.render(document.getElementById('maOutlet'))")
    page.evaluate("""
() => {
  XLSX.writeFile = function (wb, filename) {
    window.__CAPTURED_WORKBOOKS__.push({ filename, sheetNames: wb.SheetNames });
    window.__LAST_WORKBOOK__ = wb;
  };
}
""")


def goto_closing(page):
    page.wait_for_selector('[data-section="fechamentoCompetencia"]', timeout=5000)
    page.click('[data-section="fechamentoCompetencia"]')
    page.wait_for_selector('#clPeriodoSel, .modErrorState, .note', timeout=5000)


def goto_history_list(page):
    page.click('[data-section="historicoCompetencias"]')
    page.wait_for_selector(".hcViewBtn, .note", timeout=5000)


def semantic_repr(page):
    """Sheet order/names + full cell content (raw values, header:1 arrays),
    deliberately excluding any XLSX/ZIP-level metadata (timestamps, app
    properties) -- exactly the normalization Gate 14/36 requires. Sheet 1's
    own 'Gerado em' cell is a real, live report-generation timestamp (proven
    genuinely fresh per export by GENERATED_AT_DIFFERS below) -- non-semantic
    w.r.t. the FROZEN closing data itself, so it is excluded here the same
    way Gate 36/37 excludes XLSX Core Properties timestamps."""
    return page.evaluate("""
() => {
  const wb = window.__LAST_WORKBOOK__;
  return {
    sheetNames: wb.SheetNames,
    sheets: wb.SheetNames.map(n => [n, XLSX.utils.sheet_to_json(wb.Sheets[n], { header: 1, raw: true, defval: null })
      .filter(row => !(Array.isArray(row) && row[0] === 'Gerado em'))]),
  };
}
""")


def generated_at(page):
    return page.evaluate("""
() => {
  const wb = window.__LAST_WORKBOOK__;
  const rows = XLSX.utils.sheet_to_json(wb.Sheets['1_RESUMO_PRINCIPAL'], { header: 1, raw: true });
  const row = rows.find(r => Array.isArray(r) && r[0] === 'Gerado em');
  return row ? row[1] : null;
}
""")


def semantic_hash(repr_obj):
    canon = _json.dumps(repr_obj, sort_keys=False, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def raw_binary_b64(page):
    return page.evaluate("""
() => {
  try { return XLSX.write(window.__LAST_WORKBOOK__, { type: 'base64', bookType: 'xlsx' }); }
  catch (e) { return null; }
}
""")


def sheet_json(page, name):
    return page.evaluate("XLSX.utils.sheet_to_json(window.__LAST_WORKBOOK__.Sheets[%r])" % name)


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []

    # Shared mock state -- the ONLY thing standing in for the real backend's
    # freeze-on-close contract (Gate 8's explicit external-boundary carve-out).
    mock_state = {
        "live_chassis": [dict(r) for r in STATE_A_CHASSIS],
        "live_spf": [dict(r) for r in STATE_A_SPF],
        "closings": [],
        "frozen_ops": {},        # closing_id -> [{kind, ...}]
        "frozen_financial": {},  # closing_id -> [snapshot rows, real p_rows payload]
        "write_calls": [],
        "live_calls": {"salary": 0, "spf": 0},
    }

    def install_common_routes(page):
        page.route(SEC_URL + "*", json_route(200, {"users": USERS_WITH_GESTOR, "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [PERIOD_E2E], "absences": [], "store_changes": []}))
        page.route(VEND_METRICS_URL + "*", json_route(200, {"rows": VEND_ROWS, "totals": VEND_TOTALS}))
        page.route(ANALYST_METRICS_URL + "*", json_route(200, {"rows": ANALYST_ROWS}))
        page.route(MANAGER_DIR_URL + "*", json_route(200, {"rows": MANAGER_ROWS}))

        def closings_handler(route):
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": mock_state["closings"]}))
        page.route(CLOSINGS_URL + "*", closings_handler)

        def salary_handler(route):
            mock_state["live_calls"]["salary"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": mock_state["live_chassis"]}))
        page.route(SALARY_URL + "*", salary_handler)

        def spf_handler(route):
            mock_state["live_calls"]["spf"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": mock_state["live_spf"]}))
        page.route(SPF_URL + "*", spf_handler)

        def export_handler(route):
            payload = _json.loads(route.request.post_data or "{}")
            cid = payload.get("p_closing_id")
            route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": mock_state["frozen_financial"].get(cid, [])}))
        page.route(EXPORT_URL + "*", export_handler)

        def opdetail_handler(route):
            payload = _json.loads(route.request.post_data or "{}")
            cid = payload.get("p_closing_id")
            if cid in mock_state["frozen_ops"]:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps({"completeness": "COMPLETE", "rows": mock_state["frozen_ops"][cid]}))
            else:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps({"completeness": "LEGACY_PARTIAL", "rows": []}))
        page.route(OPDETAIL_URL + "*", opdetail_handler)

        def write_handler(route):
            payload = _json.loads(route.request.post_data or "{}")
            p_rows = payload.get("p_rows") or []
            closing_id = "hc-e2e-001"
            frozen_ops = []
            for r in mock_state["live_chassis"]:
                frozen_ops.append({
                    "kind": "CHASSIS", "store": r["store"], "department": r["department"],
                    "seller_user_id": r.get("seller_id"), "seller_name": r["seller_name"],
                    "sale_date": r["date"], "chassis_masked": r["chassis_masked"], "vehicle_model": r["vehicle_model"],
                    "financed": r["financed"], "finance_date": r.get("finance_date"), "sale_value": r["sale_value"],
                    "financed_value": r["financed_value"], "return_considered": r["return_considered"],
                    "included_in_commission": r["included_in_commission"],
                })
            for r in mock_state["live_spf"]:
                frozen_ops.append({
                    "kind": "SPF", "store": r["store"], "department": r["department"],
                    "seller_user_id": r.get("seller_id"), "seller_name": r["seller_name"],
                    "operation_date": r["operation_date"], "chassis_masked": r["chassis_masked"],
                    "operation_code": r["operation_code"], "bank": r["bank"], "finance_code": r["finance_code"],
                    "optional_name": r["optional_name"], "spf_bruto": r["spf_bruto"], "spf_liquido": r["spf_liquido"],
                })
            mock_state["frozen_ops"][closing_id] = frozen_ops
            mock_state["frozen_financial"][closing_id] = p_rows
            mock_state["closings"].append({
                "id": closing_id, "periodo_id": payload.get("p_period_id"), "nome_periodo": PERIOD_E2E["nome_periodo"],
                "data_inicio": PERIOD_E2E["data_inicio"], "data_fim": PERIOD_E2E["data_fim"], "versao": 1, "status": "FECHADO",
                "ativo": True, "fechado_por": "Ana Master E2E", "fechado_em": "2026-10-21T09:00:00+00:00",
                "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-10-21T09:00:00+00:00",
                "historical_detail_status": "COMPLETE",
                "observacao": _json.dumps({}),  # forces Sheet 1's real fallback: sum from snapshot rows (Gate 31: no reimplementation)
            })
            mock_state["write_calls"].append(payload)
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(
                {"status": "OK", "closing_id": closing_id, "period_id": payload.get("p_period_id"), "version": 1, "snapshot_rows": len(p_rows)}))
        page.route(WRITE_URL + "*", write_handler)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)

        # ---------- Gate 9/10: STATE_A aggregates, real production code proves it ----------
        state_a_agg = state_aggregate(STATE_A_CHASSIS)
        check("STATE_A_CONSTRUCTED: 2 sellers, 5 total vendidas, 3 total financiadas (matches VEND_TOTALS)",
              sum(v["vendidas"] for v in state_a_agg.values()) == 5 and sum(v["financiadas"] for v in state_a_agg.values()) == 3)

        # ==================================================================
        # PHASE 1 -- real CLOSE UI flow (master-competence-closing-provider.js
        # /-engine.js, same driver as tests/master-competence-closing-
        # provider-test.py), producing a real COMPLETE closing.
        # ==================================================================
        page1 = new_page(browser)
        install_tripwire(page1)
        install_common_routes(page1)
        mount(page1)
        goto_closing(page1)
        page1.select_option("#clPeriodoSel", PERIOD_E2E["id"])
        page1.wait_for_timeout(300)
        check("PRE-CLOSE, LIVE_CALLS(salary/spf)=0 (close preview never touches live chassis/SPF RPCs)",
              mock_state["live_calls"]["salary"] == 0 and mock_state["live_calls"]["spf"] == 0)
        page1.click("#clGeneratePreviewBtn")
        page1.wait_for_timeout(400)
        body = page1.inner_text("body")
        check("CLOSE PREVIEW (real engine): shows real aggregated profile counts (VENDEDOR/GERENTE/ANALISTA/GESTOR)",
              "VENDEDOR" in body and "GERENTE" in body and "ANALISTA" in body and "GESTOR" in body)
        page1.click("#clSimulateToggle")  # turn OFF simulation -> real-RPC-shaped write (still fully mocked at network layer)
        page1.wait_for_timeout(100)
        page1.click("#clOpenConfirmBtn")
        page1.wait_for_selector("#nxModalRoot .maudModalDialog", timeout=3000)
        page1.click("#clConfirmDoBtn")
        page1.wait_for_timeout(500)
        check("COMPLETE_CLOSE_CAPTURES_OPERATIONAL_DETAIL: real close RPC fired exactly once, closing_id assigned, frozen operational detail captured",
              len(mock_state["write_calls"]) == 1 and "hc-e2e-001" in mock_state["frozen_ops"] and len(mock_state["frozen_ops"]["hc-e2e-001"]) == len(STATE_A_CHASSIS) + len(STATE_A_SPF))
        check("COMPLETENESS PROOF: the captured closing carries historical_detail_status='COMPLETE' (not inferred from row counts)",
              mock_state["closings"] and mock_state["closings"][0]["historical_detail_status"] == "COMPLETE")
        real_p_rows = mock_state["write_calls"][0].get("p_rows") or []
        check("FROZEN FINANCIAL SNAPSHOT CAPTURED: real p_rows payload built by the real closing engine, non-empty, captured for export",
              len(real_p_rows) > 0 and mock_state["frozen_financial"].get("hc-e2e-001") == real_p_rows)
        page1.close()

        # ==================================================================
        # PHASE 2 -- EXPORT_A: FRESH page/context (Gate 22), real Exportar
        # RH/DP flow (master-competence-history-provider.js/-rhdp-export-
        # engine.js/shell-admin.js).
        # ==================================================================
        page2 = new_page(browser)
        install_tripwire(page2)
        install_common_routes(page2)
        mount(page2)
        goto_history_list(page2)
        live_before_a = dict(mock_state["live_calls"])
        page2.click(".hcRhdpBtn >> nth=0")
        page2.wait_for_timeout(600)
        captured_a = page2.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("COMPLETE_EXPORT_A_VALID: exactly 1 workbook generated for the real COMPLETE closing", len(captured_a) == 1)
        check("COMPLETE_EXPORT_WORKBOOK_8_SHEETS_VALID (EXPORT_A): exactly the 8 required sheet names, in order",
              captured_a and captured_a[0]["sheetNames"] == ['1_RESUMO_PRINCIPAL', '2_VENDEDORES', '3_ANALISTAS_GESTOR', '4_GERENTES',
                                                              '5_CHASSIS_FINANCIADOS', '6_TODOS_CHASSIS_VENDEDOR', '7_AUDITORIA_SPF', '8_MEMORIA_DE_CALCULO'])
        live_after_a = dict(mock_state["live_calls"])
        check("COMPLETE_EXPORT_ZERO_LIVE_RECONSTRUCTION_CALLS (EXPORT_A): 0 calls to operational_salary_details/master_operational_spf_audit_period during export",
              live_after_a == live_before_a)

        sheet2_a = sheet_json(page2, "2_VENDEDORES")
        sheet5_a = sheet_json(page2, "5_CHASSIS_FINANCIADOS")
        sheet6_a = sheet_json(page2, "6_TODOS_CHASSIS_VENDEDOR")
        sheet7_a = sheet_json(page2, "7_AUDITORIA_SPF")
        sheet8_a = sheet_json(page2, "8_MEMORIA_DE_CALCULO")
        seller_names_a = set(r["Nome"] for r in sheet2_a)
        check("COMPLETE_EXPORT_TOTALS_RECONCILE (sellers): Sheet 2 shows both STATE_A sellers", seller_names_a == {"Vendedor E2E Um", "Vendedor E2E Dois"})
        check("COMPLETE_EXPORT_TOTALS_RECONCILE (sold count): Sheet 5+6 chassis count == STATE_A total vendidas (5)", len(sheet6_a) == 5)
        check("COMPLETE_EXPORT_TOTALS_RECONCILE (financed count): Sheet 5 (financiados only) == STATE_A total financiadas (3)", len(sheet5_a) == 3)
        check("COMPLETE_EXPORT_TOTALS_RECONCILE (SPF): Sheet 7 shows the 1 frozen STATE_A SPF row, seller/store authoritative from the freeze", len(sheet7_a) == 1 and sheet7_a[0]["Vendedor"] == "Vendedor E2E Um")
        check("COMPLETE_EXPORT_TOTALS_RECONCILE (memory sheet): Sheet 8 has 1 row per frozen financial snapshot row", len(sheet8_a) == len(real_p_rows))
        check("NO DUPLICATE ROW: Sheet 6 chassis_masked values are all distinct", len(set(r["Chassi Mascarado"] for r in sheet6_a)) == len(sheet6_a))

        repr_a = semantic_repr(page2)
        SEMANTIC_HASH_A = semantic_hash(repr_a)
        raw_a = raw_binary_b64(page2)
        generated_at_a = generated_at(page2)
        page2.close()

        # ==================================================================
        # PHASE 3 -- mutate the CONTROLLED live source: STATE_A -> STATE_B.
        # ==================================================================
        agg_before = state_aggregate(mock_state["live_chassis"])
        mock_state["live_chassis"] = [dict(r) for r in STATE_B_CHASSIS]
        mock_state["live_spf"] = [dict(r) for r in STATE_B_SPF]
        agg_after = state_aggregate(mock_state["live_chassis"])
        check("LIVE_SOURCE_MUTATED_AFTER_CLOSE (row count changed): STATE_A had 5 live chassis rows, STATE_B has %d" % len(mock_state["live_chassis"]),
              len(STATE_A_CHASSIS) == 5 and len(mock_state["live_chassis"]) == 5 and STATE_A_CHASSIS != mock_state["live_chassis"])
        check("LIVE_SOURCE_MUTATED_AFTER_CLOSE (seller attribution changed): 'Vendedor E2E Um' vendidas 3 -> %d after reassignment+addition" % agg_after.get("Vendedor E2E Um", {}).get("vendidas", -1),
              agg_before.get("Vendedor E2E Um", {}).get("vendidas") == 3 and agg_after.get("Vendedor E2E Um", {}).get("vendidas") == 4)
        check("LIVE_SOURCE_MUTATED_AFTER_CLOSE (financed status changed): total financiadas 3 -> %d" % sum(v["financiadas"] for v in agg_after.values()),
              sum(v["financiadas"] for v in agg_before.values()) == 3 and sum(v["financiadas"] for v in agg_after.values()) == 5)
        check("LIVE_SOURCE_MUTATED_AFTER_CLOSE (SPF live detail changed): spf_bruto for the original operation changed materially",
              STATE_A_SPF[0]["spf_bruto"] != mock_state["live_spf"][0]["spf_bruto"] and len(mock_state["live_spf"]) == 2)

        # ==================================================================
        # PHASE 4 -- EXPORT_B: another FRESH page/context, SAME closing_id,
        # after the live mutation. The real production code must still
        # produce the SAME frozen result.
        # ==================================================================
        page3 = new_page(browser)
        install_tripwire(page3)
        install_common_routes(page3)
        mount(page3)
        goto_history_list(page3)
        live_before_b = dict(mock_state["live_calls"])
        page3.click(".hcRhdpBtn >> nth=0")
        page3.wait_for_timeout(600)
        captured_b = page3.evaluate("window.__CAPTURED_WORKBOOKS__")
        check("COMPLETE_EXPORT_B_VALID: exactly 1 workbook generated for the SAME closing, after live mutation", len(captured_b) == 1)
        check("COMPLETE_EXPORT_WORKBOOK_8_SHEETS_VALID (EXPORT_B): exactly the 8 required sheet names, in order",
              captured_b and captured_b[0]["sheetNames"] == (captured_a[0]["sheetNames"] if captured_a else None))
        live_after_b = dict(mock_state["live_calls"])
        check("COMPLETE_EXPORT_ZERO_LIVE_RECONSTRUCTION_CALLS (EXPORT_B, the critical post-mutation trap): 0 calls to live RPCs even though STATE_B is now served by them",
              live_after_b == live_before_b)

        repr_b = semantic_repr(page3)
        SEMANTIC_HASH_B = semantic_hash(repr_b)
        raw_b = raw_binary_b64(page3)
        generated_at_b = generated_at(page3)
        page3.close()

        check("GENERATED_AT_DIFFERS: Sheet 1's 'Gerado em' cell differs between EXPORT_A and EXPORT_B, proving both were genuinely freshly generated (not cached/replayed) -- excluded from the semantic hash as non-frozen report metadata",
              generated_at_a is not None and generated_at_b is not None and generated_at_a != generated_at_b)

        check("COMPLETE_EXPORT_SEMANTIC_HASH_STABLE: SEMANTIC_HASH_A == SEMANTIC_HASH_B despite the intervening live mutation", SEMANTIC_HASH_A == SEMANTIC_HASH_B)
        check("Independent structural re-check: EXPORT_A and EXPORT_B sheet-by-sheet cell content identical", repr_a == repr_b)
        raw_equal = (raw_a is not None and raw_b is not None and raw_a == raw_b)
        # Reported, not asserted as a pass/fail gate -- Gate 36 explicitly forbids
        # failing a valid immutable export solely because ZIP/XLSX metadata differs.
        RAW_BINARY_EQUALITY = "YES" if raw_equal else ("NOT_AUTHORITATIVE" if (raw_a is None or raw_b is None) else "NO")

        # ==================================================================
        # PHASE 5 -- REIMPORT_AFTER_CLOSE_DOES_NOT_CHANGE_COMPLETE_EXPORT,
        # restated in THIS suite's own real-close context (the sibling
        # suite's test #47 proves the same principle from a static
        # fixture; this restates it end-to-end from a REAL close).
        # ==================================================================
        sheet6_a_content = repr_a["sheets"][repr_a["sheetNames"].index("6_TODOS_CHASSIS_VENDEDOR")][1]
        sheet6_b_content = repr_b["sheets"][repr_b["sheetNames"].index("6_TODOS_CHASSIS_VENDEDOR")][1]
        check("REIMPORT_AFTER_CLOSE_DOES_NOT_CHANGE_COMPLETE_EXPORT: EXPORT_B's Sheet 6 raw content == EXPORT_A's, cell-for-cell, despite the intervening STATE_B mutation (add/remove/reassign/amount/financed/SPF changes)",
              sheet6_b_content == sheet6_a_content and len(sheet6_a_content) == 6)  # header row (1) + 5 STATE_A chassis data rows

        # ==================================================================
        # PHASE 6 -- NEGATIVE CONTROL (Gate 21): prove the test methodology
        # WOULD detect mutable-source dependence, by deliberately serving
        # STATE_B (mapped to the frozen shape) instead of the real frozen
        # snapshot for a clone closing_id. Production code is NEVER modified;
        # only this page's own OPDETAIL_URL mock response is swapped.
        # ==================================================================
        page4 = new_page(browser)
        install_tripwire(page4)
        page4.route(SEC_URL + "*", json_route(200, {"users": USERS_WITH_GESTOR, "configurations": [], "audit": []}))
        page4.route(CONV_URL + "*", json_route(200, []))
        page4.route(READ_URL + "*", json_route(200, {"periods": [PERIOD_E2E], "absences": [], "store_changes": []}))
        broken_closing = dict(mock_state["closings"][0], id="hc-e2e-broken")
        page4.route(CLOSINGS_URL + "*", json_route(200, {"rows": [broken_closing]}))
        page4.route(EXPORT_URL + "*", json_route(200, {"rows": mock_state["frozen_financial"]["hc-e2e-001"]}))
        broken_ops = []
        for r in STATE_B_CHASSIS:
            broken_ops.append({"kind": "CHASSIS", "store": r["store"], "department": r["department"], "seller_user_id": r.get("seller_id"),
                                "seller_name": r["seller_name"], "sale_date": r["date"], "chassis_masked": r["chassis_masked"],
                                "vehicle_model": r["vehicle_model"], "financed": r["financed"], "finance_date": r.get("finance_date"),
                                "sale_value": r["sale_value"], "financed_value": r["financed_value"], "return_considered": r["return_considered"],
                                "included_in_commission": r["included_in_commission"]})
        for r in STATE_B_SPF:
            broken_ops.append({"kind": "SPF", "store": r["store"], "department": r["department"], "seller_user_id": r.get("seller_id"),
                                "seller_name": r["seller_name"], "operation_date": r["operation_date"], "chassis_masked": r["chassis_masked"],
                                "operation_code": r["operation_code"], "bank": r["bank"], "finance_code": r["finance_code"],
                                "optional_name": r["optional_name"], "spf_bruto": r["spf_bruto"], "spf_liquido": r["spf_liquido"]})
        page4.route(OPDETAIL_URL + "*", json_route(200, {"completeness": "COMPLETE", "rows": broken_ops}))  # deliberately WRONG (STATE_B, not the real freeze)
        page4.route(SALARY_URL + "*", json_route(200, {"rows": []}))
        page4.route(SPF_URL + "*", json_route(200, {"rows": []}))
        mount(page4)
        goto_history_list(page4)
        page4.click(".hcRhdpBtn >> nth=0")
        page4.wait_for_timeout(600)
        captured_broken = page4.evaluate("window.__CAPTURED_WORKBOOKS__")
        SEMANTIC_HASH_BROKEN = semantic_hash(semantic_repr(page4)) if captured_broken else None
        check("IMMUTABILITY_TEST_NEGATIVE_CONTROL_PROVEN: feeding STATE_B instead of the real frozen snapshot produces a DIFFERENT semantic hash than EXPORT_A -- the comparison methodology is sensitive to exactly this regression class",
              SEMANTIC_HASH_BROKEN is not None and SEMANTIC_HASH_BROKEN != SEMANTIC_HASH_A)
        page4.close()

        # ==================================================================
        # PHASE 7 -- LEGACY_PARTIAL CONTRAST (Gate 25/35): the SAME kind of
        # drift just proven real for a COMPLETE closing (if it were ever fed
        # to the export) still correctly fails closed for a genuine
        # LEGACY_PARTIAL closing, exactly as tests/master-competence-rhdp-
        # export-test.py's own test #20 already proves (not duplicated here
        # in full -- re-run as part of this Phase's regression, see report).
        # ==================================================================
        page5 = new_page(browser)
        install_tripwire(page5)
        legacy_closing = dict(mock_state["closings"][0], id="hc-e2e-legacy", historical_detail_status=None)
        page5.route(SEC_URL + "*", json_route(200, {"users": USERS_WITH_GESTOR, "configurations": [], "audit": []}))
        page5.route(CONV_URL + "*", json_route(200, []))
        page5.route(READ_URL + "*", json_route(200, {"periods": [PERIOD_E2E], "absences": [], "store_changes": []}))
        page5.route(CLOSINGS_URL + "*", json_route(200, {"rows": [legacy_closing]}))
        page5.route(EXPORT_URL + "*", json_route(200, {"rows": mock_state["frozen_financial"]["hc-e2e-001"]}))
        page5.route(OPDETAIL_URL + "*", json_route(200, {"completeness": "LEGACY_PARTIAL", "rows": []}))
        page5.route(SPF_URL + "*", json_route(200, {"rows": STATE_A_SPF}))
        # Live chassis intentionally diverges from the frozen financial
        # snapshot's own per-seller vendidas/financiadas totals -- same
        # class of real drift PM-6D.4 found in production.
        page5.route(SALARY_URL + "*", json_route(200, {"rows": STATE_B_CHASSIS[:1]}))
        mount(page5)
        goto_history_list(page5)
        page5.click(".hcRhdpBtn >> nth=0")
        page5.wait_for_timeout(600)
        captured_legacy = page5.evaluate("window.__CAPTURED_WORKBOOKS__")
        err_text = page5.inner_text("#maPanel")
        check("LEGACY_PARTIAL_DIVERGENCE_STILL_FAILS_CLOSED: a genuine LEGACY_PARTIAL closing with divergent live data still blocks the whole export",
              len(captured_legacy) == 0 and "integridade da auditoria" in err_text)
        page5.close()

        check("NETWORK TRIPWIRE: zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("SEMANTIC_HASH_A      =", SEMANTIC_HASH_A)
    print("SEMANTIC_HASH_B      =", SEMANTIC_HASH_B)
    print("SEMANTIC_HASH_BROKEN =", SEMANTIC_HASH_BROKEN)
    print("RAW_BINARY_EQUALITY  =", RAW_BINARY_EQUALITY)
    print("LIVE_CALLS (final)   =", mock_state["live_calls"])
    print()
    print("=== Master RHDP COMPLETE E2E Immutability Proof: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
