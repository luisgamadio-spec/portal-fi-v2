#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Painel Master Phase PM-5H -- deterministic tests for the Histórico de
Competências module (master-competence-history-provider.js, master-
competence-history-view-model.js, shell-admin.js), mounted via the
same lightweight harness used by every sibling Painel Master surface.

STRICTLY READ-ONLY CAPABILITY (PM-5H Gate 4/33) -- no create/edit/
close/reopen/archive/delete/correct/recalculate action exists anywhere
in this file's target code, and this suite explicitly proves that
(checks 1-3: source-text allowlist over the real provider file, not an
assumption). Exactly 3 real RPCs are ever called: master_commission_
closings() (list), master_commission_snapshot(p_closing_id) (viewer,
unguarded), master_commission_snapshot_export(p_closing_id) (export,
server-side fail-closed). Contract reconstructed in PM-5G/PM-5H from
real Git sources -- see the provider file's own header comment for
exact citations (master_commission_snapshot_export's full SQL body is
readable verbatim in portal-financiamento-brabus-secure; the other two
RPCs' real return shape is reconstructed from that same repo's already
ground-truth-audited production TypeScript, supabase/functions/
portal-ai/index.ts). Their literal SQL bodies are NOT in Git and this
session has no live database/Management API/service-role credential
available -- documented limitation, not assumed away.

0 real network calls, 0 real Supabase project touched, 0 credentials
anywhere in this file. Synthetic period/closing/snapshot data only --
no real financial or personal data (see PM-5H Gate 30).
"""
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
SNAPSHOT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot"
EXPORT_URL = "https://mock.invalid/rest/v1/rpc/master_commission_snapshot_export"

PROVIDER_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "js", "adapters", "master-competence-history-provider.js")

results = []

# ---------- synthetic fixture (no real financial/personal data) ----------
CLOSING_HEALTHY = {
    "id": "hc-001", "periodo_id": "per-001", "nome_periodo": "21/07 a 20/08/2026",
    "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "versao": 1, "status": "FECHADO",
    "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-08-21T10:15:00+00:00",
    "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-08-21T10:15:00+00:00",
    "observacao": '{"comissao_total": 9500}'
}
CLOSING_DIVERGENT = {
    "id": "hc-002", "periodo_id": "per-002", "nome_periodo": "21/06 a 20/07/2026",
    "data_inicio": "2026-06-21", "data_fim": "2026-07-20", "versao": 1, "status": "FECHADO",
    "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-07-21T09:00:00+00:00",
    "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-07-21T09:00:00+00:00",
    "observacao": '{"comissao_total": 207397.56}'
}
CLOSING_ZEROED = {
    "id": "hc-003", "periodo_id": "per-003", "nome_periodo": "21/05 a 20/06/2026",
    "data_inicio": "2026-05-21", "data_fim": "2026-06-20", "versao": 1, "status": "FECHADO",
    "ativo": True, "fechado_por": "Bruno Master", "fechado_em": "2026-06-21T08:00:00+00:00",
    "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-06-21T08:00:00+00:00",
    "observacao": None
}
CLOSING_V1_REABERTO = {
    "id": "hc-004", "periodo_id": "per-004",
    "nome_periodo": "21/04 a 20/05/2026 (Competência Com Nome Extremamente Longo Para Teste De Estresse De Layout Em Tabela E Cartao Mobile)",
    "data_inicio": "2026-04-21", "data_fim": "2026-05-20", "versao": 1, "status": "REABERTO",
    "ativo": True, "fechado_por": "Carla Master", "fechado_em": "2026-05-21T08:00:00+00:00",
    "reaberto_por": "Ana Master", "reaberto_em": "2026-05-25T14:30:00+00:00", "criado_em": "2026-05-21T08:00:00+00:00",
    "observacao": "Primeiro fechamento oficial de teste. | Reabertura: teste"
}
CLOSING_V2_FECHADO = {
    "id": "hc-005", "periodo_id": "per-004",
    "nome_periodo": "21/04 a 20/05/2026 (Competência Com Nome Extremamente Longo Para Teste De Estresse De Layout Em Tabela E Cartao Mobile)",
    "data_inicio": "2026-04-21", "data_fim": "2026-05-20", "versao": 2, "status": "FECHADO",
    "ativo": True, "fechado_por": "Ana Master", "fechado_em": "2026-05-26T09:00:00+00:00",
    "reaberto_por": None, "reaberto_em": None, "criado_em": "2026-05-26T09:00:00+00:00",
    "observacao": '{"comissao_total": 8500}'
}
CLOSINGS = [CLOSING_HEALTHY, CLOSING_DIVERGENT, CLOSING_ZEROED, CLOSING_V1_REABERTO, CLOSING_V2_FECHADO]

SNAPSHOT_HEALTHY = [
    {"nome": "Vendedor Com Nome Extremamente Longo Para Teste De Estresse De Layout Em Tabela E Cartao Mobile",
     "perfil": "VENDEDOR", "loja": "BANDEIRANTES", "departamento": "SEMINOVOS",
     "vendidas": 15, "financiadas": 12, "share": 80.0, "producao": 1100000, "retorno": 90000,
     "spf_extra": 6000, "spf_liquido": 4200, "rentabilidade_total": 14.0, "faixa": 3, "comissao": 9500,
     "detalhes": {"comissao_principal": 8000, "comissao_spf": 1500, "comissao_total": 9500}}
]
SNAPSHOT_DIVERGENT = [
    {"nome": "Analista Um", "perfil": "ANALISTA", "loja": "ALPHAVILLE", "departamento": "NOVOS/SEMINOVOS",
     "vendidas": 5, "financiadas": 4, "share": 80, "producao": 250000, "retorno": 18000,
     "spf_extra": 1200, "spf_liquido": 840, "rentabilidade_total": 7.2, "faixa": 1, "comissao": 2500,
     "detalhes": {"comissao_principal": 2200, "comissao_spf": 300, "comissao_total": 2500}}
]
SNAPSHOT_ZEROED = [
    {"nome": "Analista Quatro", "perfil": "ANALISTA", "loja": "NACOES", "departamento": "NOVOS/SEMINOVOS",
     "vendidas": 0, "financiadas": 0, "share": 0, "producao": 0, "retorno": 0,
     "spf_extra": 0, "spf_liquido": 0, "rentabilidade_total": 0, "faixa": 0, "comissao": 0, "detalhes": None}
]
SNAPSHOT_V1 = [
    {"nome": "Vendedor V1 Alpha", "perfil": "VENDEDOR", "loja": "LOJA CENTRO", "departamento": "NOVOS",
     "vendidas": 5, "financiadas": 4, "share": 80, "producao": 300000, "retorno": 20000,
     "spf_extra": 1000, "spf_liquido": 700, "rentabilidade_total": 6.7, "faixa": 1, "comissao": 3000,
     "detalhes": {"comissao_principal": 2800, "comissao_spf": 200, "comissao_total": 3000}}
]
SNAPSHOT_V2 = [
    {"nome": "Vendedor V2 Beta", "perfil": "VENDEDOR", "loja": "EUROPA", "departamento": "SEMINOVOS",
     "vendidas": 8, "financiadas": 6, "share": 75, "producao": 500000, "retorno": 35000,
     "spf_extra": 2000, "spf_liquido": 1400, "rentabilidade_total": 7.0, "faixa": 2, "comissao": 8500,
     "detalhes": {"comissao_principal": 7500, "comissao_spf": 1000, "comissao_total": 8500}}
]
SNAPSHOTS = {"hc-001": SNAPSHOT_HEALTHY, "hc-002": SNAPSHOT_DIVERGENT, "hc-003": SNAPSHOT_ZEROED,
             "hc-004": SNAPSHOT_V1, "hc-005": SNAPSHOT_V2}


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


def goto_hc(page):
    page.wait_for_selector('[data-section="historicoCompetencias"]', timeout=5000)
    page.click('[data-section="historicoCompetencias"]')
    page.wait_for_selector(".hcTable, .hcMobileCard, .modErrorState, .note", timeout=5000)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def snapshot_route(rows_by_id, status=200):
    def handler(route):
        post = _json.loads(route.request.post_data or "{}")
        cid = post.get("p_closing_id")
        route.fulfill(status=status, content_type="application/json", body=_json.dumps({"rows": rows_by_id.get(cid, [])}))
    return handler


def export_route_fail_closed():
    def handler(route):
        post = _json.loads(route.request.post_data or "{}")
        cid = post.get("p_closing_id")
        rows = SNAPSHOTS.get(cid, [])
        all_zero_null = len(rows) > 0 and all((r.get("comissao") or 0) == 0 and r.get("detalhes") is None for r in rows)
        if len(rows) == 0 or all_zero_null:
            route.fulfill(status=400, content_type="application/json", body=_json.dumps({
                "code": "22023",
                "message": "Exportação bloqueada: o fechamento desta competência possui um snapshot histórico inconsistente. Procure a Administração/RH F&I."
            }))
            return
        route.fulfill(status=200, content_type="application/json", body=_json.dumps({"rows": rows}))
    return handler


def main():
    from playwright.sync_api import sync_playwright

    real_network_hits = []
    dialogs_fired = []

    # ---------- 1-3: READ-ONLY PROOF (source-text allowlist, Gate 33) ----------
    import re
    with io.open(PROVIDER_PATH, "r", encoding="utf-8") as f:
        provider_src = f.read()
    # Checks against actual EXECUTABLE calls, not prose -- the file's own
    # header comment legitimately NAMES the forbidden write RPCs (to
    # document why they're excluded), so a raw substring search over the
    # whole file (including comments) would false-positive on its own
    # documentation. What must never exist is an actual callRpc(...)
    # invocation of a write RPC, or a real js write-method call.
    forbidden_rpc_calls = ["master_close_commission_period", "master_reopen_commission_period", "master_admin_manage"]
    forbidden_write_methods = [".insert(", ".update(", ".delete(", ".upsert("]
    no_forbidden_rpc_calls = all(("callRpc('%s'" % name) not in provider_src for name in forbidden_rpc_calls)
    no_forbidden_write_methods = all(tok not in provider_src for tok in forbidden_write_methods)
    check("1 (READ-ONLY PROOF): provider source contains NO callRpc(...) invocation of a write RPC and no write-method call", no_forbidden_rpc_calls and no_forbidden_write_methods)
    allowed_rpcs = {"master_commission_closings", "master_commission_snapshot", "master_commission_snapshot_export"}
    called_rpcs = set(re.findall(r"callRpc\('([a-zA-Z_]+)'", provider_src))
    check("2 (READ-ONLY PROOF): every RPC name the provider calls is in the reconciled read-only allowlist", called_rpcs and called_rpcs.issubset(allowed_rpcs))
    check("3 (READ-ONLY PROOF): the provider calls all 3 allowlisted RPCs (no missing capability)", called_rpcs == allowed_rpcs)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def install_tripwire(page):
            page.on("requestfinished", lambda req: real_network_hits.append(req.url)
                    if ("supabase.co" in req.url or "challenges.cloudflare.com" in req.url) else None)
            page.on("dialog", lambda d: (dialogs_fired.append(d.message), d.dismiss()))

        # ---------- 4-12: list renders real fields, version isolation, dates safe ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(200, {"rows": CLOSINGS}))
        page.route(SNAPSHOT_URL + "*", snapshot_route(SNAPSHOTS))
        mount(page)
        goto_hc(page)
        body_text = page.inner_text("body")
        check("4: period name/date range renders for a real closing", "21/07 a 20/08/2026" in body_text and "21/07/2026" in body_text and "20/08/2026" in body_text)
        check("5 (DATE SAFETY): 2026-08-21T10:15:00 fechado_em renders as 21/08/2026 10:15 -- pure string slicing, no toISOString/timezone drift possible", "21/08/2026 10:15" in body_text)
        # innerText reflects the RENDERED (CSS text-transform:uppercase-
        # applied) text, not the raw DOM text node -- .maBadge renders
        # these as uppercase pills, so match what actually appears on
        # screen.
        check("6: both FECHADO and REABERTO status labels render for their real records", "FECHADO" in body_text and "REABERTO" in body_text)
        check("7: reaberto_por/reaberto_em render when present", "25/05/2026 14:30" in body_text and "Ana Master" in body_text)
        check("8: version label renders for both versions of the same period (Gate 15 -- never hidden)", "v1" in body_text and "v2" in body_text)
        check("9: official resumo (comissao_total) renders when observacao is valid JSON", "R$ 9.500,00" in body_text or "9.500,00" in body_text)
        check("10 (Parte AQ real finding): a legacy free-text observacao never throws and degrades to 'Resumo indisponível', never a raw JSON dump", "Resumo indisponível" in body_text and "Primeiro fechamento oficial de teste" not in body_text)
        check("11: long period name renders in full (no silent truncation)", "Competência Com Nome Extremamente Longo" in body_text)
        check("12: no native window.confirm/alert/prompt dialog ever fired on the list view (shared modal only)", len(dialogs_fired) == 0)
        page.close()

        # ---------- 13-16: version isolation (Gate 15/35) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(200, {"rows": CLOSINGS}))
        page.route(SNAPSHOT_URL + "*", snapshot_route(SNAPSHOTS))
        mount(page)
        goto_hc(page)
        page.click('.hcViewBtn[data-id="hc-004"]')
        page.wait_for_timeout(200)
        detail_v1 = page.inner_text("body")
        check("13: opening v1 (REABERTO) shows ONLY its own row (Vendedor V1 Alpha)", "Vendedor V1 Alpha" in detail_v1 and "Vendedor V2 Beta" not in detail_v1)
        page.click("#hcBackBtn")
        page.wait_for_timeout(100)
        page.click('.hcViewBtn[data-id="hc-005"]')
        page.wait_for_timeout(200)
        detail_v2 = page.inner_text("body")
        check("14: opening v2 (FECHADO) shows ONLY its own row (Vendedor V2 Beta), never v1's", "Vendedor V2 Beta" in detail_v2 and "Vendedor V1 Alpha" not in detail_v2)
        check("15: v2's own official total (comissao_total=8500) matches its own row sum -- no integrity warning shown for a healthy, isolated snapshot", "Snapshot histórico com inconsistência" not in detail_v2)
        page.close()

        # ---------- 16-18: HISTORICAL IMMUTABILITY (Gate 36) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(200, {"rows": CLOSINGS}))
        mutable_rows = {"hc-001": list(SNAPSHOT_HEALTHY)}
        page.route(SNAPSHOT_URL + "*", snapshot_route(mutable_rows))
        operational_rpc_calls = []
        page.route("**/rpc/operational_*", lambda r: (operational_rpc_calls.append(r.request.url), r.fulfill(status=500, content_type="application/json", body="{}")))
        mount(page)
        goto_hc(page)
        page.click('.hcViewBtn[data-id="hc-001"]')
        page.wait_for_timeout(200)
        before_mutation = page.inner_text("body")
        # Simulate "live" data changing after the snapshot was already loaded --
        # the already-rendered detail must NOT reflect this (no live recompute).
        mutable_rows["hc-001"] = [dict(SNAPSHOT_HEALTHY[0], comissao=999999, nome="DEVERIA NUNCA APARECER")]
        page.wait_for_timeout(100)
        after_mutation = page.inner_text("body")
        check("16 (HISTORICAL IMMUTABILITY): already-rendered snapshot detail is byte-identical after the underlying mock 'live' data changes -- no automatic recompute/refetch", before_mutation == after_mutation and "DEVERIA NUNCA APARECER" not in after_mutation)
        check("17 (SNAPSHOT-ONLY PROOF): zero calls to any operational_* RPC were ever made from this screen -- history never combines snapshot with live data", len(operational_rpc_calls) == 0)
        page.close()

        # ---------- 18-21: FAIL-CLOSED EXPORT (Gate 13/22/37) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(200, {"rows": CLOSINGS}))
        page.route(SNAPSHOT_URL + "*", snapshot_route(SNAPSHOTS))
        export_calls = []
        page.route(EXPORT_URL + "*", lambda r: (export_calls.append(r.request.post_data), export_route_fail_closed()(r)))
        mount(page)
        goto_hc(page)
        page.click('.hcViewBtn[data-id="hc-003"]')
        page.wait_for_timeout(200)
        check("18 (FAIL-CLOSED, Gate 12/26): structurally inconsistent snapshot (all rows comissao=0 AND detalhes null) shows the proactive warning in the VIEWER, before any export attempt", "Snapshot histórico com inconsistência" in page.inner_text("body"))
        page.click('.hcExportBtn[data-id="hc-003"]')
        page.wait_for_timeout(300)
        export_body = page.inner_text("body")
        check("19: the real server rejection (22023) is shown verbatim, not a generic error", "Exportação bloqueada" in export_body and "Administração/RH F&I" in export_body)
        check("19b: exactly one export call was made -- no retry, no alternate RPC used to work around the rejection", len(export_calls) == 1)
        page.click("#hcBackBtn")
        page.wait_for_timeout(100)
        page.click('.hcViewBtn[data-id="hc-002"]')
        page.wait_for_timeout(200)
        check("20: a DIVERGENT-but-not-structural snapshot (row sum != official total) still shows the proactive warning, distinct message from the structural case", "diverge do total oficial" in page.inner_text("body"))
        page.close()

        # ---------- 21-23: adversarial / error states ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        mount(page)
        goto_hc(page)
        check("21 (NON-MASTER PROOF, Gate 9/44): a 42501 denial on the list read is surfaced as a real error state, never a false-success empty list", "modErrorState" in page.content() or "Sem permiss" in page.inner_text("body"))
        page.close()

        page = new_page(browser, token=None)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        mount(page)
        goto_hc(page)
        check("22 (SESSION EXPIRY, Gate 38): a missing session shows a real error state, not a false-success empty list", "modErrorState" in page.content() or "Sess" in page.inner_text("body"))
        page.close()

        check("23: no native window.confirm/alert/prompt dialog ever fired across the whole suite (shared modal only)", len(dialogs_fired) == 0)
        check("24: network tripwire -- zero requests reached a real Supabase project or Cloudflare Turnstile across the whole suite", len(real_network_hits) == 0)

        # ---------- 25-33: responsive matrix + row-grid integrity (Gate 26/27/48/49/50) ----------
        page = new_page(browser)
        install_tripwire(page)
        page.route(SEC_URL + "*", json_route(200, {"users": [], "configurations": [], "audit": []}))
        page.route(CONV_URL + "*", json_route(200, []))
        page.route(READ_URL + "*", json_route(200, {"periods": [], "absences": [], "store_changes": []}))
        page.route(CLOSINGS_URL + "*", json_route(200, {"rows": CLOSINGS}))
        page.route(SNAPSHOT_URL + "*", snapshot_route(SNAPSHOTS))
        mount(page)
        goto_hc(page)
        for w in (1440, 1366, 1280, 1100, 1024, 1000, 900, 899, 768, 430, 390, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            measurements = page.evaluate("""
() => {
  const doc = document.documentElement;
  const table = document.querySelector('.hcTable');
  const wrap = table ? table.closest('.modTableWrap') : null;
  const isDesktop = !!(table && table.offsetParent);
  let gridFailures = 0, rows = 0;
  if (isDesktop) {
    const rowEls = [...table.querySelectorAll('tbody tr')];
    rows = rowEls.length;
    rowEls.forEach(row => {
      const rowRect = row.getBoundingClientRect();
      [...row.children].forEach(td => {
        const r = td.getBoundingClientRect();
        const topOk = Math.abs(r.top - rowRect.top) <= 1;
        const bottomOk = Math.abs(r.bottom - rowRect.bottom) <= 1;
        if (!topOk || !bottomOk || getComputedStyle(td).display !== 'table-cell') gridFailures++;
      });
    });
  }
  return {
    isDesktop,
    doc_ok: doc.scrollWidth <= doc.clientWidth + 1,
    wrap_ok: !wrap || !isDesktop || wrap.scrollWidth <= wrap.clientWidth + 1,
    gridFailures, rows
  };
}
""")
            check("25 (w=%d): no horizontal overflow at the page level (PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE)" % w, measurements["doc_ok"])
            check("26 (w=%d): no CONTAINED horizontal overflow inside .modTableWrap either" % w, measurements["wrap_ok"])
            if measurements["isDesktop"]:
                check("27 (w=%d, ROW GRID INTEGRITY): every <td> in every row matches its row's own top/bottom within 1px, native table-cell (Ações never display:flex on the <td> itself)" % w, measurements["gridFailures"] == 0 and measurements["rows"] > 0)
        check("28: mobile cards (.hcMobileCard) render at 375px with no desktop table visible", page.evaluate("document.querySelector('.hcMobileCard') && document.querySelector('.hcMobileCard').offsetParent !== null") and not page.evaluate("document.querySelector('.hcTable').offsetParent"))
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.wait_for_timeout(60)

        # 29-30: same matrix on the DETAIL/snapshot table (Gate 48/50, second table in this capability)
        page.click('.hcViewBtn[data-id="hc-001"]')
        page.wait_for_timeout(200)
        for w in (1440, 1024, 900, 899, 768, 375):
            page.set_viewport_size({"width": w, "height": 1000})
            page.wait_for_timeout(60)
            snap_measurements = page.evaluate("""
() => {
  const doc = document.documentElement;
  const table = document.querySelector('.hcSnapshotTable');
  const isDesktop = !!(table && table.offsetParent);
  let gridFailures = 0, rows = 0;
  if (isDesktop) {
    const rowEls = [...table.querySelectorAll('tbody tr')];
    rows = rowEls.length;
    rowEls.forEach(row => {
      const rowRect = row.getBoundingClientRect();
      [...row.children].forEach(td => {
        const r = td.getBoundingClientRect();
        if (Math.abs(r.top - rowRect.top) > 1 || Math.abs(r.bottom - rowRect.bottom) > 1 || getComputedStyle(td).display !== 'table-cell') gridFailures++;
      });
    });
  }
  return { doc_ok: doc.scrollWidth <= doc.clientWidth + 1, gridFailures, rows, isDesktop };
}
""")
            check("29 (w=%d, snapshot table): no horizontal overflow at the page level" % w, snap_measurements["doc_ok"])
            if snap_measurements["isDesktop"]:
                check("30 (w=%d, snapshot table ROW GRID INTEGRITY): every cell matches its row within 1px" % w, snap_measurements["gridFailures"] == 0 and snap_measurements["rows"] > 0)
        page.close()

        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Master Histórico de Competências Provider: %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
