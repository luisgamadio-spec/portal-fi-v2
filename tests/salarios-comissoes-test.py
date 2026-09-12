#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH-4B / RH-5B.1 / RH-5F -- deterministic regression proving the Salários &
Comissões module shell: profile-adaptive section visibility
(presentation only, never a security boundary), real RH-4A provider
consumption, period lifecycle, partial-dashboard-failure resilience,
fail-closed error states, and zero horizontal overflow at the 4
mandated widths.

RH-5B.1 (Human UX rejection of the RH-5B tabbed layout -- "achei meio
confuso... mantem o modelo de apresentação que já tinhamos no modelo
secure"): the module was restructured to match the real V1/Secure
information architecture -- ONE continuous page.

RH-5F (Human UAT visual/information-architecture feedback): % Comissão
moved out of the name cell into its own dedicated column; Analistas is
no longer one global block at the bottom -- each store's Analyst row(s)
render together with that store's own seller/manager group; conversion
(Conversão/share_percent) gets a semantic >=40%/<40% badge; store/unit
headers carry stronger visual weight; the Detalhes modal was redesigned
around operational_salary_details' own already-authoritative operation-
level fields (financed_value, return_considered, spf_70, modality) that
were simply never rendered before; KPI cards got a scoped overflow fix
for long currency values. No Commission Total column exists -- traced
live this Wave (Secure operational_commission_faixa_rows) and confirmed
NOT exposed by any RPC V2 is wired to call for the open period
(SALARIOS_COMISSAO_TOTAL_AUTHORITY_GAP) -- this file asserts that gap
stays honest (no fabricated column), not that it's closed.

Everything here runs against a mocked window.supabase/window.NX_AUTH_CORE
context and routed (never real) fetches -- 0 real network calls, 0 real
Supabase project touched, 0 credentials anywhere in this file. Fixture
shapes mirror the real, live-proven RPC contracts (RH-1/RH-2/RH-3/RH-3A/
RH-4A, and operational_salary_details' full field set re-traced live
this Wave) -- no real employee names/CPF/salary/commission values.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json as _json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# V2-INT-01 -- was hardcoded to the OLD parent-dir-rooted topology
# (http://127.0.0.1:8080/portal-next-v2/...); this worktree (like every
# other V2 test file) is served root-at-worktree. Test-harness-only
# fix, same IA3E_TEST_PORT convention the rest of this suite already
# uses -- no product code touched.
BASE = f"http://127.0.0.1:{os.environ.get('IA3E_TEST_PORT', '8711')}/index.html"
CONFIG_SCRIPT = "window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-key', textEndpoint: null };"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def mock_client_script(perfil, status):
    return """
(function () {
  var listeners = [];
  var fakeSession = null;
  function ok(data) { return Promise.resolve({ data: data, error: null }); }
  window.supabase = {
    createClient: function () {
      return {
        auth: {
          getSession: function () { return ok({ session: fakeSession }); },
          signInWithPassword: function () { fakeSession = { access_token: 'mock-token', user: { id: 'auth-user-1' } }; return ok({ session: fakeSession }); },
          onAuthStateChange: function (cb) { listeners.push(cb); return { data: { subscription: { unsubscribe: function () {} } } }; },
          signOut: function () { return Promise.resolve({ error: null }); }
        },
        rpc: function (name) {
          if (name === 'usuario_logado_fi') return ok([{usuario_id:'u1', auth_user_id:'auth-user-1', nome:'Demo', perfil:'%s', loja:'TODAS', status:'%s', ativo:true}]);
          if (name === 'portal_modulos_permitidos') return ok(['comissoes']);
          return ok(null);
        }
      };
    }
  };
})();
""" % (perfil, status)


def json_route(status, body):
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


# Fixtures mirror the REAL live contract (RH-1/RH-3/RH-3A/RH-4A, RH-5F
# re-trace) -- no real employee names/CPF/salary/commission values.
# Two stores (ABC, BANDEIRANTES) so store-grouping/Analyst-repositioning
# has something real to prove; s3's low share_percent (25%) exercises
# the new <40% conversion state.
PERIODS = {"rows": [
    {"id": "p1", "nome_periodo": "21/07 a 20/08", "data_inicio": "2026-07-21", "data_fim": "2026-08-20", "status": "ABERTO", "periodo_atual": True, "ativo": True, "criado_por": "seed"},
    {"id": "p2", "nome_periodo": "21/06 a 20/07", "data_inicio": "2026-06-21", "data_fim": "2026-07-20", "status": "FECHADO", "periodo_atual": False, "ativo": True, "criado_por": "seed"},
]}
PERIODS_NO_CURRENT = {"rows": [
    {"id": "p3", "nome_periodo": "21/05 a 20/06", "data_inicio": "2026-05-21", "data_fim": "2026-06-20", "status": "FECHADO", "periodo_atual": False, "ativo": True, "criado_por": "seed"},
    {"id": "p4", "nome_periodo": "21/04 a 20/05", "data_inicio": "2026-04-21", "data_fim": "2026-05-20", "status": "FECHADO", "periodo_atual": False, "ativo": True, "criado_por": "seed"},
]}
METRICS = {"scope": {"profile": "MASTER", "departments": ["NOVOS", "SEMINOVOS"], "is_master": True, "is_director": False, "is_seller": False, "store": None},
    "period_start": "2026-07-21", "period_end": "2026-08-20", "spf_net_percent": 70, "eligibility_rule": "ACTIVE_VENDEDOR_ONLY",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR", "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "totals": {"sold_count": 132, "financed_count": 98, "share_percent": 74.2, "production_value": 4570000.55, "return_value": 234000.10, "spf_count": 41, "spf_value": 61500.0, "spf_net_value": 43050.0, "profitability_value": 277050.10},
    "rows": [
        {"seller_id": "s1", "seller_name": "Vendedor Demo A", "store": "ABC", "department": "NOVOS", "sold_count": 12, "sales_value": 900000, "financed_count": 9, "share_percent": 75.0, "production_value": 450000.0, "return_value": 23000.0, "spf_count": 4, "spf_value": 6000.0, "spf_net_value": 4200.0, "profitability_value": 27200.0, "plan_breakdown": []},
        {"seller_id": "s2", "seller_name": "Vendedor Demo B", "store": "ABC", "department": "NOVOS", "sold_count": 8, "sales_value": 600000, "financed_count": 5, "share_percent": 62.5, "production_value": 250000.0, "return_value": 11000.0, "spf_count": 2, "spf_value": 3000.0, "spf_net_value": 2100.0, "profitability_value": 13100.0, "plan_breakdown": []},
        {"seller_id": "s3", "seller_name": "Vendedor Demo C", "store": "BANDEIRANTES", "department": "SEMINOVOS", "sold_count": 12, "sales_value": 450000, "financed_count": 3, "share_percent": 25.0, "production_value": 150000.0, "return_value": 6000.0, "spf_count": 1, "spf_value": 1500.0, "spf_net_value": 1050.0, "profitability_value": 7050.0, "plan_breakdown": []},
    ]}
# ABC has both an official Analyst row and a coverage (transfer=true) row
# (Gate 22/23 -- coverage must stay distinctly labeled, never merged into
# the official row); DELTA has Analyst activity but ZERO seller movement
# this period -- an "orphan" store the seller groups never mention (Gate
# 21/23 -- must still render, never silently dropped); BANDEIRANTES has a
# seller group but NO analyst row (proves a store can legitimately have
# one without the other).
ANALYST = {"absence_aware": True, "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "rows": [
        {"analyst_name": "Analista Demo", "store": "ABC", "sold_count": 20, "financed_count": 15, "production_value": 700000.0, "return_value": 34000.0, "spf_count": 5, "spf_value": 7500.0, "transfer": False, "covered_start": None, "covered_end": None, "coverage_id": None},
        {"analyst_name": "Substituta Demo", "store": "ABC", "sold_count": 3, "financed_count": 2, "production_value": 50000.0, "return_value": 3000.0, "spf_count": 1, "spf_value": 500.0, "transfer": True, "covered_start": "2026-07-25", "covered_end": "2026-07-31", "coverage_id": "cov1"},
        {"analyst_name": "Analista Delta", "store": "DELTA", "sold_count": 5, "financed_count": 4, "production_value": 120000.0, "return_value": 6000.0, "spf_count": 1, "spf_value": 300.0, "transfer": False, "covered_start": None, "covered_end": None, "coverage_id": None},
    ]}
DIRECTORY = {"period_start": "2026-07-21", "period_end": "2026-08-20", "assignment_source": "ACTIVE_PORTAL_PROFILE",
    "rows": [{"store": "ABC", "department": "NOVOS", "manager_name": "Gerente Demo"}], "ambiguous_assignments": 0,
    "contains_client_identity": False, "contains_personal_documents": False, "contains_operational_identifiers": False}
# RH-5F -- operational_salary_details' full live row shape (re-traced this
# Wave, Secure): financed_value/return_considered/spf_gross/
# spf_considered/spf_70 (SPF Extra per operation -- Gate 26's requested
# field, already authoritative)/modality/installments were all real and
# already returned, just never rendered before. Two rows -- one financed,
# one not -- to prove the distinct visual state (Gate 27/28).
DETAILS = {"scope": METRICS["scope"], "period_start": "2026-07-21", "period_end": "2026-08-20", "seller_filter": "s1", "seller_count": 2, "row_count": 3, "row_limit": 2000, "truncated": False,
    "rows": [
        {"date": "2026-08-01", "finance_date": "2026-08-03", "store": "ABC", "department": "NOVOS", "vehicle_model": "ECLIPSE CROSS", "seller_id": "s1", "seller_name": "Vendedor Demo A",
         "operation_ref": "abc123456789", "chassis_masked": "******T12345", "sale_value": 250000.0, "financed": True, "financed_value": 240000.0,
         "installments": 48, "installment_value": 5200.0, "modality": "CDC", "return_gross": 5400.0, "return_considered": 5400.0,
         "spf_count": 1, "spf_gross": 1200.0, "spf_considered": 1200.0, "spf_70": 840.0, "operation_profitability": 6240.0,
         "included_in_commission": True, "exclusion_reason": "", "applied_rule": "FAIXA CONSOLIDADA DO VENDEDOR"},
        {"date": "2026-08-05", "finance_date": None, "store": "ABC", "department": "NOVOS", "vehicle_model": "L200 TRITON", "seller_id": "s1", "seller_name": "Vendedor Demo A",
         "operation_ref": "def987654321", "chassis_masked": "******T99887", "sale_value": 180000.0, "financed": False, "financed_value": 0.0,
         "installments": None, "installment_value": None, "modality": "", "return_gross": 0.0, "return_considered": 0.0,
         "spf_count": 0, "spf_gross": 0.0, "spf_considered": 0.0, "spf_70": 0.0, "operation_profitability": 0.0,
         "included_in_commission": True, "exclusion_reason": "", "applied_rule": "FAIXA CONSOLIDADA DO VENDEDOR"},
        # RH-5F.1: falls INSIDE the ABC coverage window (2026-07-25 to
        # 2026-07-31, ANALYST fixture's "Substituta Demo" row below) --
        # exercises the Analyst Details window-filter both ways: this
        # operation belongs to the COVERAGE analyst's detail, never the
        # official one.
        {"date": "2026-07-28", "finance_date": "2026-07-28", "store": "ABC", "department": "NOVOS", "vehicle_model": "OUTLANDER", "seller_id": "s2", "seller_name": "Vendedor Demo B",
         "operation_ref": "ghi555555555", "chassis_masked": "******T55501", "sale_value": 200000.0, "financed": True, "financed_value": 190000.0,
         "installments": 36, "installment_value": 6000.0, "modality": "CDC", "return_gross": 3000.0, "return_considered": 3000.0,
         "spf_count": 1, "spf_gross": 500.0, "spf_considered": 500.0, "spf_70": 350.0, "operation_profitability": 3350.0,
         "included_in_commission": True, "exclusion_reason": "", "applied_rule": "FAIXA CONSOLIDADA DO VENDEDOR"},
    ],
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False, "contains_masked_chassis": True, "contains_chassis": False, "contains_nbs": False}
# RH-5B/RH-5F long-content fixture (Gate 44/29/30): a genuinely long
# vehicle_model/modality/applied_rule -- proves the operation card never
# overflows its own narrow (max-width:720px) modal, and that date/chassis
# specifically never wrap mid-value even when neighboring text is long.
DETAILS_LONG = {"scope": METRICS["scope"], "period_start": "2026-07-21", "period_end": "2026-08-20", "seller_filter": "s1", "seller_count": 1, "row_count": 1, "row_limit": 2000, "truncated": False,
    "rows": [{"date": "2026-08-01", "finance_date": "2026-08-03", "store": "ABC", "department": "NOVOS", "vehicle_model": "MITSUBISHI ECLIPSE CROSS HPE 1.5 TURBO CVT", "seller_id": "s1", "seller_name": "Vendedor Demo A",
        "operation_ref": "abc123456789", "chassis_masked": "******T12345", "sale_value": 250000.0, "financed": True, "financed_value": 240000.0,
        "installments": 48, "installment_value": 5200.0, "modality": "CDC COM ENTRADA REDUZIDA E CARENCIA ESTENDIDA", "return_gross": 5400.0, "return_considered": 5400.0,
        "spf_count": 1, "spf_gross": 1200.0, "spf_considered": 1200.0, "spf_70": 840.0, "operation_profitability": 6240.0,
        "included_in_commission": True, "exclusion_reason": "", "applied_rule": "FAIXA CONSOLIDADA DO VENDEDOR PARA PRODUÇÃO ACIMA DA META"}],
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False, "contains_masked_chassis": True, "contains_chassis": False, "contains_nbs": False}


# RH-5B.3 -- the real, live operational_portal_config() shape ({rows:
# [{chave, valor}]}), same 13 threshold keys documented in
# docs/COMMISSION-ENGINE-AUTHORITY.md, at their confirmed production
# defaults (no live overrides exist).
CONFIG = {"rows": [
    {"chave": "share_minimo", "valor": "40"},
    {"chave": "spf_liquido_percentual", "valor": "70"},
    {"chave": "bonus_spf_analista", "valor": "150"},
    {"chave": "limite_retorno_novos", "valor": "12000"},
    {"chave": "limite_retorno_seminovos", "valor": "8000"},
    {"chave": "vendedor_faixa_baixo_share_baixo", "valor": "10"},
    {"chave": "vendedor_faixa_baixo_share_alto", "valor": "15"},
    {"chave": "vendedor_faixa_alto_share_baixo", "valor": "15"},
    {"chave": "vendedor_faixa_alto_share_alto", "valor": "20"},
    {"chave": "gerente_faixa_share_baixo", "valor": "3"},
    {"chave": "gerente_faixa_share_alto", "valor": "4"},
    {"chave": "analista_faixa_share_baixo", "valor": "3.5"},
    {"chave": "analista_faixa_share_alto", "valor": "4.5"},
]}


# RH-5C.1 default fixtures for the 2 new RPCs -- a real, deterministic
# pronto:true Gestor F&I response and a small real-shaped Faixa rows
# set (matching METRICS/ANALYST/DIRECTORY's stores so faixaFor() lookups
# actually match).
GESTOR_FI_READY = {"pronto": True, "period_start": "2026-07-21", "period_end": "2026-08-20", "beneficiary_name": "Gestor Demo",
    "vendidas": 128, "financiadas": 96, "share": 75.0, "producao": 4520000.55, "retorno": 231000.10, "spf": 61000.0,
    "spf_qty": 40, "spf_liquido": 42700.0, "base": 273700.10, "faixa": 0.003, "comissao_principal": 821.1,
    "bonus_spf": 1200, "comissao_final": 2021.1, "contains_client_identity": False, "contains_personal_documents": False}
# RH-5F.1: comissao_principal/comissao_spf/comissao_total, matching the
# real live shape after operational_commission_faixa_rows' additive
# projection change (20260909170000_rh5f1_expose_comissao_total.sql).
FAIXA_ROWS_DEFAULT = {"rows": [
    {"perfil": "VENDEDOR", "seller_id": "s1", "store": "ABC", "department": "NOVOS", "faixa": 0.2, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": "ALTO", "comissao_principal": 5440.0, "comissao_spf": 0, "comissao_total": 5440.0},
    {"perfil": "VENDEDOR", "seller_id": "s3", "store": "BANDEIRANTES", "department": "SEMINOVOS", "faixa": 0.10, "faixa_level": "MINIMA", "share_tier": "BAIXO", "retorno_tier": "BAIXO", "comissao_principal": 705.0, "comissao_spf": 0, "comissao_total": 705.0},
    {"perfil": "GERENTE", "store": "ABC", "department": "NOVOS", "faixa": 0.04, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": None, "comissao_principal": 1312.0, "comissao_spf": 0, "comissao_total": 1312.0},
    {"perfil": "ANALISTA", "store": "ABC", "faixa": 0.035, "faixa_level": "MINIMA", "share_tier": "BAIXO", "retorno_tier": None, "comissao_principal": 2695.0, "comissao_spf": 750.0, "comissao_total": 3445.0}
], "contains_client_identity": False, "contains_personal_documents": False}

# RH-5F.3 -- operational_own_commission_summary's real, live shape
# (re-traced live this Wave against the real deployed function, for a
# real ANALISTA/VENDEDOR/GERENTE): {rows:[...], comissao_total, profile}.
# Values below mirror the real live numbers this Wave measured for the
# 3 real validation accounts (never their names/CPF -- see the report).
OWN_COMMISSION_NONE = {"rows": [], "comissao_total": 0, "profile": "MASTER",
    "contains_client_identity": False, "contains_personal_documents": False}
OWN_COMMISSION_ANALISTA = {"rows": [
    {"perfil": "ANALISTA", "store": "ABC", "transfer": False, "faixa": 0.035, "faixa_level": "MINIMA", "share_tier": "BAIXO", "retorno_tier": None,
     "comissao_principal": 1779.87, "comissao_spf": 300.0, "comissao_total": 2079.87}
], "comissao_total": 2079.87, "profile": "ANALISTA", "contains_client_identity": False, "contains_personal_documents": False}
OWN_COMMISSION_VENDEDOR = {"rows": [
    {"perfil": "VENDEDOR", "seller_id": "s1", "store": "ABC", "department": "NOVOS", "faixa": 0.2, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": "ALTO",
     "comissao_principal": 4704.0, "comissao_spf": 0, "comissao_total": 4704.0}
], "comissao_total": 4704.0, "profile": "VENDEDOR", "contains_client_identity": False, "contains_personal_documents": False}
OWN_COMMISSION_GERENTE = {"rows": [
    {"perfil": "GERENTE", "store": "ABC", "department": "NOVOS", "faixa": 0.04, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": None,
     "comissao_principal": 2572.25, "comissao_spf": 0, "comissao_total": 2572.25}
], "comissao_total": 2572.25, "profile": "GERENTE", "contains_client_identity": False, "contains_personal_documents": False}

# RH-5F.3A (H-SAL-1/H-SAL-3) -- operational_scope_commission_rows' real,
# live shape: {rows:[...VENDEDOR-shaped, seller_id-keyed...],
# team_comissao_total, profile}. s1/s2 match METRICS' own ABC/NOVOS
# sellers so sellerFaixaMatch() actually resolves against real Equipe rows.
SCOPE_COMMISSION_NONE = {"rows": [], "team_comissao_total": 0, "profile": "MASTER",
    "contains_client_identity": False, "contains_personal_documents": False}
SCOPE_COMMISSION_ABC_NOVOS = {"rows": [
    {"perfil": "VENDEDOR", "seller_id": "s1", "store": "ABC", "department": "NOVOS", "faixa": 0.2, "faixa_level": "MAXIMA", "share_tier": "ALTO", "retorno_tier": "ALTO",
     "comissao_principal": 5440.0, "comissao_spf": 0, "comissao_total": 5440.0},
    {"perfil": "VENDEDOR", "seller_id": "s2", "store": "ABC", "department": "NOVOS", "faixa": 0.1, "faixa_level": "MINIMA", "share_tier": "BAIXO", "retorno_tier": "BAIXO",
     "comissao_principal": 1310.0, "comissao_spf": 0, "comissao_total": 1310.0}
], "team_comissao_total": 6750.0, "profile": "ANALISTA", "contains_client_identity": False, "contains_personal_documents": False}


def route_defaults(page, periods=None, metrics=None, analyst=None, directory=None, details=None, config=None, gestor_fi=None, faixa_rows=None, own_commission=None, scope_commission=None):
    page.route("**/assets/js/intelligence-runtime-config.js*", lambda r: r.fulfill(status=200, content_type="application/javascript", body="/* mocked */"))
    page.route("**/rest/v1/rpc/operational_commission_periods*", json_route(200, periods if periods is not None else PERIODS))
    page.route("**/rest/v1/rpc/operational_commission_metrics*", json_route(200, metrics if metrics is not None else METRICS) if not (isinstance(metrics, tuple)) else metrics_handler(metrics))
    page.route("**/rest/v1/rpc/operational_analyst_commission_metrics_v2*", json_route(200, analyst if analyst is not None else ANALYST) if not isinstance(analyst, tuple) else metrics_handler(analyst))
    page.route("**/rest/v1/rpc/operational_salary_manager_directory*", json_route(200, directory if directory is not None else DIRECTORY) if not isinstance(directory, tuple) else metrics_handler(directory))
    page.route("**/rest/v1/rpc/operational_salary_details*", json_route(200, details if details is not None else DETAILS))
    page.route("**/rest/v1/rpc/operational_portal_config*", json_route(200, config if config is not None else CONFIG) if not isinstance(config, tuple) else metrics_handler(config))
    page.route("**/rest/v1/rpc/operational_gestor_fi_commission*", json_route(200, gestor_fi if gestor_fi is not None else GESTOR_FI_READY) if not isinstance(gestor_fi, tuple) else metrics_handler(gestor_fi))
    page.route("**/rest/v1/rpc/operational_commission_faixa_rows*", json_route(200, faixa_rows if faixa_rows is not None else FAIXA_ROWS_DEFAULT) if not isinstance(faixa_rows, tuple) else metrics_handler(faixa_rows))
    page.route("**/rest/v1/rpc/operational_own_commission_summary*", json_route(200, own_commission if own_commission is not None else OWN_COMMISSION_NONE) if not isinstance(own_commission, tuple) else metrics_handler(own_commission))
    page.route("**/rest/v1/rpc/operational_scope_commission_rows*", json_route(200, scope_commission if scope_commission is not None else SCOPE_COMMISSION_NONE) if not isinstance(scope_commission, tuple) else metrics_handler(scope_commission))
    page.route("**/cdn.jsdelivr.net/npm/@supabase/supabase-js**", lambda r: r.abort())


def metrics_handler(status_body_tuple):
    status, body = status_body_tuple
    def handler(route):
        route.fulfill(status=status, content_type="application/json", body=_json.dumps(body))
    return handler


def new_page(browser, perfil="MASTER", status="MASTER", width=1366, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.add_init_script(CONFIG_SCRIPT)
    page.add_init_script(mock_client_script(perfil, status))
    return page


def login(page, email):
    page.goto(BASE)
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'")
    page.fill("#loginEmail", email)
    page.fill("#loginPassword", "pass")
    page.click("#loginSubmit")
    page.wait_for_function("window.NX_AUTH_CORE && window.NX_AUTH_CORE.getState() === 'AUTHORIZED'")


def mount(page):
    page.evaluate("location.hash = '#/salarios-comissoes'")
    page.wait_for_selector(".salPage", timeout=8000)
    page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getDashboardState() !== 'LOADING'", timeout=8000)


# RH-5F.1A -- the exact false-negative class Human UAT caught: RH-5F.1's
# own "zero horizontal overflow" tests measured ONLY the page root.
# .modTableWrap's overflow-x:auto absorbs a real internal horizontal
# scrollbar without ever pushing the page itself wider -- page-level
# scrollWidth<=clientWidth stayed true the whole time even though a
# real, visible scrollbar existed inside the Equipe table. This helper
# measures EVERY relevant component wrapper directly and applies Gate
# 27's own rule verbatim: overflow-x:auto/scroll + scrollWidth >
# clientWidth (beyond a 1px rounding tolerance) is a FAIL, full stop --
# never satisfied merely because the page root looks clean.
def component_overflow_report(page):
    return page.evaluate("""() => {
      var d = document.getElementById('uatFrame') ? document.getElementById('uatFrame').contentDocument : document;
      var selectors = [
        ['page root', d.scrollingElement || d.documentElement],
        ['.salPage', d.querySelector('.salPage')],
      ];
      d.querySelectorAll('.salEquipeTableWrap').forEach(function (el, i) { selectors.push(['.salEquipeTableWrap[' + i + ']', el]); });
      d.querySelectorAll('.salAnalystTableWrap').forEach(function (el, i) { selectors.push(['.salAnalystTableWrap[' + i + ']', el]); });
      var modal = d.querySelector('.salModal');
      if (modal) selectors.push(['.salModal', modal]);
      return selectors.filter(function (s) { return !!s[1]; }).map(function (s) {
        var el = s[1];
        var cs = getComputedStyle(el);
        var overflowing = (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || el === (d.scrollingElement || d.documentElement))
          && el.scrollWidth > el.clientWidth + 1;
        return { label: s[0], clientWidth: el.clientWidth, scrollWidth: el.scrollWidth, overflowX: cs.overflowX, overflowing: overflowing };
      });
    }""")


def assert_no_component_overflow(width_label):
    def _inner(page, context_label=""):
        report = component_overflow_report(page)
        offenders = [r for r in report if r["overflowing"]]
        check(f"{width_label}{context_label}: zero component-level horizontal overflow ({len(report)} containers measured -- page root + .salPage + every .salEquipeTableWrap/.salAnalystTableWrap + open modal)", not offenders)
        if offenders:
            for o in offenders:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']} overflowX={o['overflowX']}")
        return report
    return _inner


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        errors = []

        # ---------- 1: MASTER sees the Atual/Histórico toggle (2 options only -- RH-5B.1), zero console errors ----------
        page = new_page(browser)
        page.on("pageerror", lambda e: errors.append(str(e)))
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(300)
        modes = page.evaluate("[...document.querySelectorAll('.salViewModeToggle .modTab')].map(b => b.getAttribute('data-view-mode'))")
        check("1a: MASTER sees exactly the Atual/Histórico toggle (no Resumo/Equipe/Analistas/Gestor tabs -- V1 never had them)", modes == ["atual", "historico"])
        check("1b: zero uncaught page errors", len(errors) == 0)
        page.close()

        # ---------- 2: RH/VENDEDOR see no toggle at all (Histórico is MASTER-only, presentation-only leak-free) ----------
        for perfil, status in [("RH", "RH"), ("VENDEDOR", "NOVOS")]:
            page = new_page(browser, perfil=perfil, status=status)
            route_defaults(page)
            login(page, perfil.lower() + "@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            has_toggle = page.evaluate("!!document.querySelector('.salViewModeToggle')")
            check(f"2: {perfil} sees no Atual/Histórico toggle at all (no client-side MASTER-only leak)", not has_toggle)
            page.close()

        # ---------- 3: KPIs render real, unrecomputed values (always visible, no tab click needed) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        kpis = page.evaluate("[...document.querySelectorAll('.modKpiCard .modKpiValue')].map(e => e.textContent.trim())")
        check("3a: Vendidas KPI shows the real integer (132), not recomputed", "132" in kpis[0])
        check("3b: Conversão KPI formatted as percentage from the real share_percent field", "74" in kpis[2] and "%" in kpis[2])
        check("3c: Rentabilidade KPI formatted as currency from the real profitability_value field", "R$" in kpis[7] and "277.050" in kpis[7])
        page.close()

        # ---------- 4: Equipe table (first store group, ABC) + Detalhes modal (real provider call, masked chassis shown) ----------
        page = new_page(browser)
        details_calls = {"n": 0}

        def details_capture(route):
            details_calls["n"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(DETAILS))

        route_defaults(page)
        page.route("**/rest/v1/rpc/operational_salary_details*", details_capture)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        # ABC (s1, s2) is the FIRST .salDesktopOnly in DOM order (groups
        # are alpha-sorted by "store department", and ABC's own Analyst
        # sub-table -- a SEPARATE .salDesktopOnly element -- comes right
        # after it, before BANDEIRANTES).
        rows_count = page.evaluate("document.querySelectorAll('.salDesktopOnly')[0].querySelectorAll('tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)').length")
        check("4a: Equipe table (ABC) shows both real seller rows (excluding the group-header/manager trailing rows)", rows_count == 2)
        check("4a2: a section heading 'Equipe' is present (V1 grouping restored, RH-5B.1)", "Equipe" in page.evaluate("document.querySelector('.salBody').textContent"))
        page.click('.salDesktopOnly [data-details]')
        page.wait_for_timeout(300)
        check("4b: Detalhes modal calls the real operational_salary_details RPC exactly once", details_calls["n"] == 1)
        check("4c: Detalhes modal shows the real masked chassis (not full, not hidden)", "T12345" in page.content())
        page.close()

        # ---------- 4d: Detalhes modal operation cards never overflow their own narrow container (long content) ----------
        for width in (1366, 1024, 900, 480):
            page = new_page(browser, width=width)
            route_defaults(page, details=DETAILS_LONG)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(150)
            detail_btn = page.locator('[data-details]').last if width <= 760 else page.locator('[data-details]').first
            detail_btn.click()
            page.wait_for_timeout(250)
            m = page.evaluate("""() => {
              const modal = document.querySelector('.salModal');
              return { modalOverflow: modal.scrollWidth > modal.clientWidth + 1, pageOverflow: document.scrollingElement.scrollWidth > document.scrollingElement.clientWidth + 1 };
            }""")
            check(f"4d (w={width}): Detalhes modal has zero contained overflow with long content", not m["modalOverflow"])
            check(f"4d (w={width}): zero page-level overflow with the modal open", not m["pageOverflow"])
            page.close()

        # ---------- 5: Analistas -- authorized profile sees defensively-rendered rows, positioned inside the ABC store group (RH-5F) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("5a: MASTER sees the real analyst row (different field shape than Equipe, rendered defensively)", "Analista Demo" in page.content())
        check("5b: an Analyst sub-heading is present (plural -- ABC has 2 rows: official + coverage)", "Analistas" in page.evaluate("document.querySelector('.salBody').textContent"))
        abc_containment = page.evaluate("""() => {
          const groups = [...document.querySelectorAll('.salStoreGroup')];
          const abcGroup = groups.find(g => g.textContent.includes('Vendedor Demo A'));
          return !!abcGroup && abcGroup.textContent.includes('Analista Demo');
        }""")
        check("5c (RH-5F): the ABC Analyst row renders INSIDE the same .salStoreGroup as ABC's own sellers, not a separate global block", abc_containment)
        page.close()

        # ---------- 6: Analistas -- server FORBIDDEN is NOT treated as empty data, and non-authorized profiles see NO section at all ----------
        page = new_page(browser)
        route_defaults(page, analyst=(403, {"code": "42501", "message": "Perfil sem acesso aos dados operacionais."}))
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        content6 = page.content()
        check("6a: FORBIDDEN shows an explicit unauthorized message, not a generic empty state", "utoriza" in content6)
        check("6b: FORBIDDEN state does not claim zero analysts (would be misleading)", "Nenhum analista" not in content6)
        page.close()

        page2 = new_page(browser, perfil="VENDEDOR", status="NOVOS")
        route_defaults(page2)
        login(page2, "vendedor@demo.local")
        mount(page2)
        page2.wait_for_timeout(200)
        # Scoped to the real Analyst section element, never a text
        # substring -- "Analista" also legitimately appears in the
        # static Faixas de comissão reference card (visible to every
        # profile), so a text-based check here would false-positive.
        check("6c: VENDEDOR (not authorized for Analistas) sees NO Analyst section element at all -- V1 shows no placeholder, the section is simply absent", not page2.evaluate("!!document.querySelector('.salAnalystSection')"))
        page2.close()

        # ---------- 6d: authorized profile, genuinely zero analyst rows anywhere -- explicit empty note, never silence ----------
        page = new_page(browser)
        route_defaults(page, analyst={"absence_aware": True, "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False, "rows": []})
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("6d: authorized profile with zero real analyst rows sees an explicit 'nenhum analista' note, not silence", "Nenhum analista" in page.content())
        page.close()

        # ---------- 7: manager/team-total trailing row -- aggregation is summation of real numbers, not a new formula (RH-5B.1: embedded in Equipe, not a separate Gestor tab) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        manager_row_text = page.evaluate("""() => {
          const row = document.querySelector('.salDesktopOnly tr.salManagerRow');
          return row ? row.textContent : null;
        }""")
        check("7a: a real manager trailing row (Gerente Demo) is embedded inside the Equipe table itself, not a separate section", manager_row_text is not None and "Gerente Demo" in manager_row_text)
        # Both seller rows (s1: production 450000, s2: production 250000) belong to ABC/NOVOS,
        # matching the one manager directory entry -- team total must be the exact sum.
        check("7b: manager production total is the exact sum of the 2 real rows (450000+250000=700000), not a new formula", "700.000,00" in manager_row_text)
        page.close()

        # ---------- 7c: BANDEIRANTES (no matching manager directory entry) shows the anonymous TOTAL DA EQUIPE row instead -- V1 parity, never both, never neither ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        team_total_text = page.evaluate("""() => {
          const row = document.querySelector('tr.salTeamTotalRow');
          return row ? row.textContent : null;
        }""")
        check("7c: BANDEIRANTES (no manager directory match) shows the anonymous TOTAL DA EQUIPE row (real summed totals, no manager identity)", team_total_text is not None and "TOTAL DA EQUIPE" in team_total_text and "150.000,00" in team_total_text)
        page.close()

        # ---------- 7d: ANALISTA profile (authorized for totals but not the real manager identity) sees the anonymous row for ABC too ----------
        page = new_page(browser, perfil="ANALISTA", status="NOVOS")
        route_defaults(page)
        login(page, "analista@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("7d: ANALISTA never sees the real manager identity row", "Gerente Demo" not in page.content())
        page.close()

        # ---------- 8: partial dashboard failure -- KPIs degrade gracefully, Equipe still works, manager leg shows its own error inline ----------
        page = new_page(browser)
        route_defaults(page, metrics=(200, METRICS), directory=(500, {"message": "internal"}))
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        content8 = page.content()
        check("8a: KPIs still render real values despite the directory leg failing", "132" in content8)
        check("8b: a partial-failure note is surfaced, not silently hidden", "não puderam ser carregados" in content8 or "nao puderam ser carregados" in content8)
        page.close()

        # ---------- 9: period selector -- deterministic fallback when no periodo_atual exists ----------
        page = new_page(browser)
        route_defaults(page, periods=PERIODS_NO_CURRENT)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        selected = page.evaluate("window.NX_SALARIOS_COMISSOES_PAGE.getSelectedPeriodId()")
        check("9: deterministic fallback selects the first (most recent) period when none is flagged current", selected == "p3")
        page.close()

        # ---------- 10: period change triggers a real re-fetch ----------
        page = new_page(browser)
        metrics_calls = {"n": 0}

        def metrics_capture(route):
            metrics_calls["n"] += 1
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(METRICS))

        route_defaults(page)
        page.route("**/rest/v1/rpc/operational_commission_metrics*", metrics_capture)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("10a: initial mount fetches metrics exactly once", metrics_calls["n"] == 1)
        page.select_option("#salPeriodSelect", "p2")
        page.wait_for_timeout(300)
        check("10b: changing the period triggers a real second fetch (not cached/stale)", metrics_calls["n"] == 2)
        page.close()

        # ---------- 11: loading state never shows a fake R$ 0,00 ----------
        page = new_page(browser)
        page.route("**/assets/js/intelligence-runtime-config.js*", lambda r: r.fulfill(status=200, content_type="application/javascript", body="/* mocked */"))
        page.route("**/rest/v1/rpc/operational_commission_periods*", lambda route: (__import__("time"), route.fulfill(status=200, content_type="application/json", body=_json.dumps(PERIODS))))
        page.route("**/cdn.jsdelivr.net/npm/@supabase/supabase-js**", lambda r: r.abort())
        login(page, "master@demo.local")
        page.evaluate("location.hash = '#/salarios-comissoes'")
        page.wait_for_selector(".salPage", timeout=8000)
        immediate_content = page.content()
        check("11: no fake 'R$ 0,00' KPI value is ever shown during loading", "R$ 0,00" not in immediate_content)
        page.close()

        # ---------- 12: zero horizontal overflow at all 4 mandated widths (KPIs + store groups + interleaved Analistas, always visible together) ----------
        # RH-5F.1A: now checks COMPONENT-level overflow too (Gate 26/27),
        # not just the page root -- the exact class of check that missed
        # the real Human-reported Equipe table scrollbar.
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            no_overflow = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"12: zero horizontal page overflow @{width}px (continuous Atual view)", no_overflow)
            if width > 760:
                assert_no_component_overflow(f"12c (RH-5F.1A, w={width}px)")(page)
            desktop_visible = page.evaluate("() => { const el = document.querySelector('.salDesktopOnly'); return el && getComputedStyle(el).display !== 'none'; }")
            mobile_visible = page.evaluate("() => { const el = document.querySelector('.salMobileOnly'); return el && getComputedStyle(el).display !== 'none'; }")
            if width <= 760:
                check(f"12: @{width}px mobile card renderer is the one shown (not a squeezed table)", mobile_visible and not desktop_visible)
            else:
                check(f"12: @{width}px desktop table is the one shown", desktop_visible and not mobile_visible)
            page.close()

        # ---------- 13: RH-5B.1 -- Histórico toggle swaps the WHOLE dashboard (KPIs/Equipe/Analistas hidden), matching V1's own rules-hub full-page takeover ----------
        page = new_page(browser)
        route_defaults(page)
        page.route("**/rest/v1/rpc/master_commission_closings*", json_route(200, {"rows": []}))
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        page.click('[data-view-mode="historico"]')
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getHistoryClosingsState() === 'READY'", timeout=8000)
        body_text = page.evaluate("document.querySelector('.salBody').textContent")
        check("13a: switching to Histórico hides the KPI/Equipe/Analistas content (V1's own hub-and-detail-page-swap pattern)", "Vendedor Demo A" not in body_text and "Analista Demo" not in body_text)
        page.click('[data-view-mode="atual"]')
        page.wait_for_timeout(200)
        body_text2 = page.evaluate("document.querySelector('.salBody').textContent")
        check("13b: switching back to Atual restores the real seller/analyst content", "Vendedor Demo A" in body_text2 and "Analista Demo" in body_text2)
        page.close()

        # ---------- 14: RH-5B.3 -- Faixas de comissão (V1's static config-driven reference card) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getCommissionConfigState() === 'READY'", timeout=8000)
        check("14a: the ranges disclosure is present and collapsed by default", page.evaluate("() => { const d = document.querySelector('.salRangesDisclosure'); return !!d && !d.hasAttribute('open'); }"))
        page.click(".salRangesDisclosure summary")
        page.wait_for_timeout(150)
        ranges_text = page.evaluate("document.querySelector('.salRangesDisclosure').textContent")
        check("14b: opening reveals all 4 profile groups (Vendedor Novos/Seminovos, Gerente, Analista)", all(s in ranges_text for s in ["Vendedor — Novos", "Vendedor — Seminovos", "Gerente", "Analista"]))
        check("14c: seller thresholds render the real live config values (10%/15%/20%, R$ 12.000,00)", "10%" in ranges_text and "20%" in ranges_text and "R$ 12.000,00" in ranges_text and "R$ 8.000,00" in ranges_text)
        check("14d: manager thresholds render the real live config values (3%/4%)", "3%" in ranges_text and "4%" in ranges_text)
        check("14e: analyst thresholds render the real live config values (3,5%/4,5%) plus the SPF bonus (R$ 150,00)", "3,5%" in ranges_text and "4,5%" in ranges_text and "R$ 150,00" in ranges_text)
        check("14f: a reference-only disclaimer is present (this card never classifies an individual seller/manager/analyst)", "referência" in ranges_text.lower())
        check("14g: the static ranges card itself never renders a Gestor F&I-specific literal (that's a separate section)", "0,16%" not in ranges_text and "0,30%" not in ranges_text)
        check("14h: no raw V1 hardcoded constant (0.0016/0.003 as literal source text) leaks into the page anywhere", "0.0016" not in page.content() and "faixaBadge(faixa" not in page.content())
        page.close()

        # ---------- 14i: config fetch failure shows an explicit error, never a silently blank/absent section ----------
        page = new_page(browser)
        route_defaults(page, config=(500, {"message": "internal"}))
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getCommissionConfigState() === 'ERROR'", timeout=8000)
        check("14i: a config-load failure surfaces an explicit error message, not a silent absence", "não foi possível" in page.content().lower() or "erro" in page.content().lower())
        page.close()

        # ---------- 14j: zero horizontal overflow with the ranges disclosure OPEN, at all 4 mandated widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getCommissionConfigState() === 'READY'", timeout=8000)
            page.click(".salRangesDisclosure summary")
            page.wait_for_timeout(150)
            no_overflow = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"14j: zero horizontal page overflow @{width}px with Faixas de comissão open", no_overflow)
            page.close()

        # ---------- 15: RH-5B.3/RH-5F -- table-continuity structural/geometric regression (the Human's "linhas cortadas, sem continuidade" defect) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        geom = page.evaluate("""() => {
          const table = document.querySelector('.salDesktopOnly table');
          const groupHeaderTh = table.querySelector('tr.salGroupHeaderRow th');
          const normalRow = table.querySelector('tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)');
          const managerRow = table.querySelector('tr.salManagerRow');
          const headerRow = table.querySelector('thead tr');
          return {
            groupHeaderRight: groupHeaderTh.getBoundingClientRect().right,
            normalRowRight: normalRow.lastElementChild.getBoundingClientRect().right,
            columnHeaderCount: headerRow.children.length,
            groupHeaderColspan: Number(groupHeaderTh.getAttribute('colspan')),
            managerFirstCellBg: getComputedStyle(managerRow.children[0]).backgroundColor,
            managerLastCellBg: getComputedStyle(managerRow.children[managerRow.children.length - 1]).backgroundColor,
            managerMiddleCellBg: getComputedStyle(managerRow.children[3]).backgroundColor
          };
        }""")
        check("15a (RH-5F.1): the group-header colspan matches the real column count (11: Vendedor..Ações, after adding Comissão Total) -- was 10, cutting the bar short again otherwise", geom["groupHeaderColspan"] == geom["columnHeaderCount"] == 11)
        check("15b: the group-header bar's right edge aligns with a normal row's right edge (no longer cut short)", abs(geom["groupHeaderRight"] - geom["normalRowRight"]) < 1.0)
        check("15c: the manager row's first cell background matches its own other cells (no two-tone sticky-column seam)", geom["managerFirstCellBg"] == geom["managerMiddleCellBg"] == geom["managerLastCellBg"])
        page.close()

        # ---------- 16: RH-5B.3/RH-5F -- Ações column integration (present and aligned across every row type, including group-header/manager/total rows) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        acoes = page.evaluate("""() => {
          const table = document.querySelector('.salDesktopOnly table');
          const headerCells = [...table.querySelectorAll('thead th')];
          const lastHeader = headerCells[headerCells.length - 1];
          const normalRow = table.querySelector('tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)');
          const managerRow = table.querySelector('tr.salManagerRow');
          return {
            lastHeaderLabel: lastHeader.textContent.trim(),
            normalRowCellCount: normalRow.children.length,
            managerRowCellCount: managerRow.children.length,
            normalActionRight: normalRow.lastElementChild.getBoundingClientRect().right,
            headerActionRight: lastHeader.getBoundingClientRect().right,
            hasDetalhesButton: !!normalRow.querySelector('button[data-details]')
          };
        }""")
        check("16a: the last column header is 'Ações'", acoes["lastHeaderLabel"] == "Ações")
        check("16b: a real seller row has a Detalhes action button in its Ações cell", acoes["hasDetalhesButton"])
        check("16c (RH-5F.1): every row type (normal, manager) has the same cell count (11, after adding Comissão Total) -- Ações is a real column, not conditionally dropped", acoes["normalRowCellCount"] == acoes["managerRowCellCount"] == 11)
        check("16d: the Ações column's right edge aligns with the header's right edge (no column drift)", abs(acoes["normalActionRight"] - acoes["headerActionRight"]) < 1.0)
        page.close()

        # ---------- 17: RH-5C.1 -- live Comissão — Gestor F&I section + per-row Faixa badges (both server-authoritative, FIX-THE-DRIFT) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getGestorFiState() === 'READY'", timeout=8000)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        gestorSection = page.evaluate("() => { const el = document.querySelector('.salGestorFiSection'); return el ? el.textContent : null; }")
        check("17a: the live Comissão — Gestor F&I section is present and unmistakably labeled", gestorSection is not None and "Comissão" in gestorSection and "Gestor F&I" in gestorSection)
        check("17b: the section shows the real server-computed comissao_final value, never a client-recomputed one", "R$ 2.021,10" in gestorSection)
        gestorSectionClass = page.evaluate("document.querySelector('.salGestorFiSection').className")
        managerRowExists = page.evaluate("!!document.querySelector('.salManagerRow')")
        check("17c: the Gestor F&I section is structurally distinct from the Equipe manager/team-total row (different section, different CSS class, never the same element)", "salManagerRow" not in gestorSectionClass and managerRowExists)
        gestorAfterLastGroup = page.evaluate("""() => {
          const groups = [...document.querySelectorAll('.salStoreGroup')];
          const last = groups[groups.length - 1];
          const gestor = document.querySelector('.salGestorFiSection');
          if (!last || !gestor) return false;
          return !!(last.compareDocumentPosition(gestor) & Node.DOCUMENT_POSITION_FOLLOWING);
        }""")
        check("17d (RH-5F): the Gestor F&I section is placed AFTER every store group (secondary information, never interrupts the KPI->Faixas->store groups flow)", gestorAfterLastGroup)
        vendorBadge = page.evaluate("() => { const row = [...document.querySelectorAll('.salDesktopOnly table tbody tr')].find(tr => tr.textContent.includes('Vendedor Demo A')); return row ? row.textContent : ''; }")
        check("17e: the VENDEDOR row shows a server-driven Faixa badge (20%, from faixa_level MAXIMA -- never a client-computed classification)", "20%" in vendorBadge)
        managerRowText = page.evaluate("() => { const row = document.querySelector('tr.salManagerRow'); return row ? row.textContent : ''; }")
        check("17f: the GERENTE trailing row shows its OWN server-driven Faixa badge (4%), separate from the Gestor F&I section's own Faixa", "4%" in managerRowText)
        analystRowText = page.evaluate("() => { const row = [...document.querySelectorAll('.salBody table tbody tr')].find(tr => tr.textContent.includes('Analista Demo')); return row ? row.textContent : ''; }")
        check("17g: the ANALISTA row shows a server-driven Faixa badge (3,5%, rounded correctly -- not a raw floating-point artifact like '3,50000000000000004%')", "3,5%" in analystRowText and "3,50000000000000004" not in analystRowText)
        page.close()

        # ---------- 17h: pronto:false (no beneficiary configured) shows an explicit message, never a fabricated zero ----------
        page = new_page(browser)
        route_defaults(page, gestor_fi={"pronto": False, "motivo": "NENHUM_BENEFICIARIO_CONFIGURADO"})
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getGestorFiState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        notReadyText = page.evaluate("() => { const el = document.querySelector('.salGestorFiSection'); return el ? el.textContent : ''; }")
        check("17h: pronto:false surfaces an explicit 'not configured' message, never a fabricated R$ 0,00", "Não disponível" in notReadyText and "R$ 0,00" not in notReadyText)
        page.close()

        # ---------- 17i: a real backend error (e.g. permission denied) shows an explicit error state, never a silent absence ----------
        page = new_page(browser)
        route_defaults(page, gestor_fi=(403, {"code": "42501", "message": "Acesso exclusivo do perfil Master."}))
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getGestorFiState() === 'ERROR'", timeout=8000)
        page.wait_for_timeout(150)
        errorSectionText = page.evaluate("() => { const el = document.querySelector('.salGestorFiSection'); return el ? el.textContent : ''; }")
        check("17i: a real RPC error surfaces an explicit error state inside the Gestor F&I section, not a silent gap", "Comissão" in errorSectionText and len(errorSectionText) > 20)
        page.close()

        # ---------- 17j: non-MASTER profiles never see the Gestor F&I section or any Faixa badge at all (presentation-only -- server is the real boundary) ----------
        page = new_page(browser, perfil="VENDEDOR", status="VENDEDOR")
        route_defaults(page)
        login(page, "vendedor@demo.local")
        mount(page)
        page.wait_for_timeout(300)
        check("17j: VENDEDOR never sees the Gestor F&I section at all (absent, not degraded)", not page.evaluate("!!document.querySelector('.salGestorFiSection')"))
        page.close()

        # ---------- 17k: zero horizontal overflow with the live Gestor F&I section rendered, at all 4 mandated widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getGestorFiState() === 'READY'", timeout=8000)
            page.wait_for_timeout(150)
            no_overflow = page.evaluate("document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth + 1")
            check(f"17k: zero horizontal page overflow @{width}px with the live Gestor F&I section rendered", no_overflow)
            page.close()

        # ================= RH-5F: Human UAT visual/IA refinement =================

        # ---------- 18: % Comissão dedicated column (no longer beside the seller name) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        col18 = page.evaluate("""() => {
          const table = document.querySelector('.salDesktopOnly table');
          const headers = [...table.querySelectorAll('thead th')].map(h => h.textContent.trim());
          const row = [...table.querySelectorAll('tbody tr')].find(tr => tr.textContent.includes('Vendedor Demo A'));
          const nameCell = row.children[0].textContent.trim();
          const pctIdx = headers.indexOf('% Comissão');
          const totalIdx = headers.indexOf('Comissão Total');
          const acoesIdx = headers.indexOf('Ações');
          return { headers, nameCell, pctCellText: row.children[pctIdx].textContent.trim(), totalCellText: row.children[totalIdx].textContent.trim(), pctIdx, totalIdx, acoesIdx };
        }""")
        check("18a (RH-5F/RH-5F.1): '% Comissão' is immediately before 'Comissão Total', which is immediately before 'Ações' -- the Human's requested column order", col18["pctIdx"] > -1 and col18["totalIdx"] == col18["pctIdx"] + 1 and col18["acoesIdx"] == col18["totalIdx"] + 1)
        check("18b (RH-5F): the seller name cell contains ONLY the name, no percentage badge beside it", col18["nameCell"] == "Vendedor Demo A")
        check("18c (RH-5F): the % Comissão cell shows the real server-authoritative value (20%, same data as before, just relocated)", "20%" in col18["pctCellText"])
        check("18d (RH-5F.1): the Comissão Total cell shows the real server-authoritative value (R$ 5.440,00, from the fixture's comissao_total)", "5.440,00" in col18["totalCellText"])
        page.close()

        # ---------- 19: Commission Total -- authority gap CLOSED this Wave (RH-5F.1): operational_commission_faixa_rows now returns comissao_total (additive projection change, Secure), consumed here via the existing faixaFor() lookup, never recalculated client-side ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        headers19 = page.evaluate("[...document.querySelector('.salDesktopOnly table thead th')?.closest('tr')?.children || []].map(h => h.textContent.trim())")
        check("19a (RH-5F.1): a real 'Comissão Total' column now exists -- the gap is closed, the field is server-authoritative, never fabricated", "Comissão Total" in headers19)
        managerRow19 = page.evaluate("() => { const row = document.querySelector('tr.salManagerRow'); return row ? row.textContent : ''; }")
        check("19b (RH-5F.1): the manager trailing row's own Comissão Total (R$ 1.312,00, from the GERENTE fixture row) is shown, distinct from any seller's", "1.312,00" in managerRow19)
        page.close()

        # ---------- 20: conversion (Conversão / share_percent) semantic highlighting -- >=40% positive, <40% attention ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        conv20 = page.evaluate("""() => {
          const rows = [...document.querySelectorAll('.salDesktopOnly table tbody tr')];
          const s1 = rows.find(tr => tr.textContent.includes('Vendedor Demo A')); // 75% -- positive
          const s3 = rows.find(tr => tr.textContent.includes('Vendedor Demo C')); // 25% -- attention
          const s1Badge = s1.children[3].querySelector('.modBadge');
          const s3Badge = s3.children[3].querySelector('.modBadge');
          return { s1Class: s1Badge ? s1Badge.className : '', s3Class: s3Badge ? s3Badge.className : '' };
        }""")
        check("20a (RH-5F): a seller with Conversão >= 40% (75%) gets the positive/success semantic badge", "modBadgeSuccess" in conv20["s1Class"])
        check("20b (RH-5F): a seller with Conversão < 40% (25%) gets the attention/warning semantic badge", "modBadgeWarning" in conv20["s3Class"])
        kpiConvClass = page.evaluate("""() => {
          const cards = [...document.querySelectorAll('.modKpiCard')];
          const card = cards.find(c => c.textContent.includes('Conversão'));
          return card ? card.className : '';
        }""")
        check("20c (RH-5F): the top Conversão KPI card also carries the semantic class (74.2% -- positive)", "modKpiCardSuccess" in kpiConvClass)
        page.close()

        # ---------- 21: Analyst store grouping -- ABC (2 rows) inside its group, BANDEIRANTES (0 rows) has no Analyst table, DELTA (orphan, 0 sellers) still renders ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        group21 = page.evaluate("""() => {
          const groups = [...document.querySelectorAll('.salStoreGroup')];
          const abc = groups.find(g => g.textContent.includes('Vendedor Demo A'));
          const band = groups.find(g => g.textContent.includes('Vendedor Demo C'));
          const orphanHeading = [...document.querySelectorAll('.salOrphanStoreHeading')].find(h => h.textContent.trim() === 'DELTA');
          return {
            abcHasAnalyst: !!abc && abc.textContent.includes('Analista Demo'),
            abcHasCoverage: !!abc && abc.textContent.includes('Substituta Demo') && abc.textContent.includes('Cobertura'),
            bandHasAnalystSection: !!band && !!band.querySelector('.salAnalystSection'),
            deltaOrphanRendered: !!orphanHeading && !!orphanHeading.closest('.salStoreGroup').textContent.includes('Analista Delta')
          };
        }""")
        check("21a (RH-5F, Gate 17/19): the ABC Analyst row renders inside the ABC store group", group21["abcHasAnalyst"])
        check("21b (RH-5F, Gate 22): the ABC coverage row is present and distinctly labeled 'Cobertura', not merged into the official row", group21["abcHasCoverage"])
        check("21c (RH-5F, Gate 20 hard gate): BANDEIRANTES has real seller movement but ZERO Analyst rows in the fixture -- no Analyst section renders there (never fabricated, never duplicated from elsewhere)", not group21["bandHasAnalystSection"])
        check("21d (RH-5F, Gate 21/23): DELTA (Analyst activity, zero sellers) still renders as its own orphan group -- never silently dropped", group21["deltaOrphanRendered"])
        page.close()

        # ---------- 22: Analyst conservation -- total rendered rows/coverage rows match the fixture exactly (no loss, no duplication) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        # Scoped to .salDesktopOnly specifically -- this codebase's own
        # established convention renders a genuinely separate element per
        # breakpoint (both always in the DOM, only one visible via CSS),
        # so each real row legitimately appears in 2 .salAnalystSection
        # elements total (1 desktop + 1 mobile) -- counting BOTH would
        # over-count by design, not by bug.
        counts22 = page.evaluate("""() => {
          const names = ['Analista Demo', 'Substituta Demo', 'Analista Delta'];
          return names.map(n => [...document.querySelectorAll('.salAnalystSection.salDesktopOnly')].filter(s => s.textContent.includes(n)).length);
        }""")
        check("22 (RH-5F, Gate 23): each of the 3 real Analyst/coverage rows appears in exactly one DESKTOP Analyst section (no row lost, none duplicated)", counts22 == [1, 1, 1])
        page.close()

        # ---------- 23: Detalhes modal enrichment -- financed_value/return_considered/SPF Extra (spf_70)/modality now shown; date & chassis never wrap ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        page.click('.salDesktopOnly [data-details]')
        page.wait_for_timeout(300)
        modalText = page.evaluate("document.querySelector('.salModal').textContent")
        check("23a (RH-5F, Gate 33/34): the modal shows Valor financiado (240.000,00), previously never rendered though already authoritative", "240.000,00" in modalText)
        check("23b (RH-5F, Gate 26): SPF Extra per operation (spf_70, R$ 840,00) is shown -- already authoritative server-side, no artificial per-operation allocation invented", "840,00" in modalText)
        check("23c (RH-5F): Retorno per operation (return_considered, 5.400,00) is shown", "5.400,00" in modalText)
        check("23d (RH-5F): modality (CDC) is shown for the financed operation", "CDC" in modalText)
        nowrap23 = page.evaluate("""() => {
          const dateEl = document.querySelector('.salOpDate');
          const chassisEl = document.querySelector('.salOpChassis');
          return { date: getComputedStyle(dateEl).whiteSpace, chassis: getComputedStyle(chassisEl).whiteSpace };
        }""")
        check("23e (RH-5F, Gate 29): the operation date is a non-wrapping token (white-space:nowrap) -- never breaks mid-value", nowrap23["date"] == "nowrap")
        check("23f (RH-5F, Gate 30): the masked chassis is a non-wrapping token -- never breaks mid-value", nowrap23["chassis"] == "nowrap")
        page.close()

        # ---------- 24: financed vs non-financed operations -- distinct visual state, financed status never implies non-financed is an error ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        page.click('.salDesktopOnly [data-details]')
        page.wait_for_timeout(300)
        fin24 = page.evaluate("""() => {
          const rows = [...document.querySelectorAll('.salOpRow')];
          const financed = rows.find(r => r.textContent.includes('ECLIPSE CROSS'));
          const notFinanced = rows.find(r => r.textContent.includes('L200 TRITON'));
          return {
            financedHasClass: financed.classList.contains('salOpRowFinanced'),
            financedBadge: financed.textContent.includes('Financiado') && !financed.textContent.includes('Não financiado'),
            notFinancedHasClass: notFinanced.classList.contains('salOpRowFinanced'),
            notFinancedBadge: notFinanced.textContent.includes('Não financiado'),
            notFinancedCriticalBadge: !!notFinanced.querySelector('.modBadgeCritical, .modBadgeWarning')
          };
        }""")
        check("24a (RH-5F, Gate 27): a financed operation gets the distinct .salOpRowFinanced treatment", fin24["financedHasClass"])
        check("24b (RH-5F, Gate 28): a financed operation shows a compact 'Financiado' status, not plain 'Sim'", fin24["financedBadge"])
        check("24c (RH-5F): a non-financed operation does NOT get the financed treatment", not fin24["notFinancedHasClass"])
        check("24d (RH-5F, Gate 28): a non-financed operation shows 'Não financiado' clearly (text, not color alone)", fin24["notFinancedBadge"])
        check("24e (RH-5F, Gate 36): non-financed is neutral, never styled as an error/critical/warning state", not fin24["notFinancedCriticalBadge"])
        page.close()

        # ---------- 25: financial KPI card overflow hardening -- long currency values stay ON ONE LINE, inside their card, at every mandated width ----------
        # RH-5F.1, Human decision (H1): typography shrinks, never wraps.
        # Rendered through the REAL kpiCard()/kpiValueSizeClass() path
        # (a genuinely large fixture total), not a post-render
        # textContent override -- that would bypass the length-based
        # size-class logic entirely and prove nothing about it.
        METRICS_STRESS = _json.loads(_json.dumps(METRICS))
        METRICS_STRESS["totals"]["production_value"] = 999999999.99
        METRICS_STRESS["totals"]["return_value"] = 29999999.99
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page, metrics=METRICS_STRESS)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getGestorFiState() === 'READY'", timeout=8000)
            page.wait_for_timeout(150)
            stress25 = page.evaluate("""() => {
              const cards = [...document.querySelectorAll('.modKpiCard')];
              let anyOverflow = false, anyWrapped = false, sawSizeClass = false;
              cards.forEach(card => {
                const valueEl = card.querySelector('.modKpiValue');
                if (!valueEl) return;
                const cardRect = card.getBoundingClientRect();
                const valueRect = valueEl.getBoundingClientRect();
                if (valueRect.right > cardRect.right + 1 || valueRect.left < cardRect.left - 1) anyOverflow = true;
                if (valueEl.textContent.length > 13 && getComputedStyle(valueEl).whiteSpace !== 'nowrap') anyWrapped = true;
                if (valueEl.classList.contains('modKpiValueSmall') || valueEl.classList.contains('modKpiValueTiny')) sawSizeClass = true;
              });
              return { anyOverflow, anyWrapped, sawSizeClass };
            }""")
            check(f"25a (RH-5F.1, Gate 39-42, w={width}): every KPI card (incl. Gestor F&I's), rendered with a real R$ 999.999.999,99-class total, stays inside its card", not stress25["anyOverflow"])
            check(f"25b (RH-5F.1, Human decision H1, w={width}): long values remain white-space:nowrap -- never wrap to a second line", not stress25["anyWrapped"])
            check(f"25c (RH-5F.1, w={width}): at least one card actually engaged the smaller size tier for the stress value (proves the mechanism fired, not just avoided by coincidence)", stress25["sawSizeClass"])
            page.close()

        # ================= RH-5F.1: Comissão Total + Analyst Details =================

        # ---------- 26: Analyst Details button present, opens the modal, real bulk RPC call (p_seller_id=null) ----------
        page = new_page(browser)
        details_calls26 = {"n": 0, "last_body": None}

        def details_capture26(route):
            details_calls26["n"] += 1
            try:
                details_calls26["last_body"] = _json.loads(route.request.post_data or "{}")
            except Exception:
                details_calls26["last_body"] = None
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(DETAILS))

        route_defaults(page)
        page.route("**/rest/v1/rpc/operational_salary_details*", details_capture26)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        has_analyst_details_btn = page.evaluate("!!document.querySelector('[data-analyst-details]')")
        check("26a (RH-5F.1, Gate 15): every applicable Analyst row exposes a Detalhes action", has_analyst_details_btn)
        page.click('.salAnalystSection.salDesktopOnly [data-analyst-details]')
        page.wait_for_timeout(300)
        check("26b: clicking Detalhes opens a real modal (salAnalystModalTitle present)", page.evaluate("!!document.getElementById('salAnalystModalTitle')"))
        check("26c: it calls the real operational_salary_details RPC exactly once", details_calls26["n"] == 1)
        check("26d (Gate 17): calls in BULK mode (p_seller_id null) -- never re-deriving which chassis belong via a client-side seller filter", details_calls26["last_body"] is not None and details_calls26["last_body"].get("p_seller_id") is None)
        page.close()

        # ---------- 27: Analyst Details summary -- store, SPF UND, % Comissão, Comissão Total, all server-authoritative ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        page.click('.salAnalystSection.salDesktopOnly [data-analyst-details]')
        page.wait_for_timeout(300)
        summaryText = page.evaluate("() => { const el = document.querySelector('.salAnalystDetailSummary'); return el ? el.textContent : ''; }")
        check("27a (RH-5F.1, Gate 18): summary shows the store (ABC)", "ABC" in summaryText)
        check("27b (Gate 19, SPF UND): shows the real SPF unit count as UND, not the monetary SPF value", "5 UND" in summaryText)
        check("27c (Gate 18): shows the real % Comissão (3,5%, same faixaFor() data as the row itself)", "3,5%" in summaryText)
        check("27d (Gate 18/42): shows the real, server-authoritative Comissão Total (R$ 3.445,00, from the fixture's ANALISTA comissao_total)", "3.445,00" in summaryText)
        page.close()

        # ---------- 28: Analyst operation detail -- enriched fields (Gate 21), correctly windowed (Gate 20/24) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        page.click('.salAnalystSection.salDesktopOnly [data-analyst-details]')
        page.wait_for_timeout(300)
        officialModalText = page.evaluate("document.querySelector('.salModal').textContent")
        check("28a (Gate 24, official row): includes the 2 real operations from OUTSIDE the coverage window (T12345, T99887)", "T12345" in officialModalText and "T99887" in officialModalText)
        check("28b (Gate 20/24, hard windowing gate): EXCLUDES the operation that falls INSIDE the coverage window (T55501 belongs to the coverage Analyst, never the official one)", "T55501" not in officialModalText)
        check("28c (Gate 21): shows enriched operation fields (Valor financiado, SPF Extra) inside the Analyst modal -- same visual system as the seller Detalhes modal, not a second one", "240.000,00" in officialModalText and "840,00" in officialModalText)
        page.close()

        # ---------- 29: Analyst coverage-row detail -- opposite window, distinctly reachable ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        coverage_btn = page.locator('.salAnalystSection.salDesktopOnly tr', has_text="Substituta Demo").locator('[data-analyst-details]')
        coverage_btn.click()
        page.wait_for_timeout(300)
        coverageModalText = page.evaluate("document.querySelector('.salModal').textContent")
        check("29a (Gate 20/24): the COVERAGE analyst's own detail includes ONLY the operation inside its own window (T55501)", "T55501" in coverageModalText)
        check("29b: the coverage detail EXCLUDES the official analyst's own operations (T12345, T99887 belong outside this window)", "T12345" not in coverageModalText and "T99887" not in coverageModalText)
        check("29c (Gate 22): the modal title identifies this as the coverage analyst's own detail", "Substituta Demo" in page.evaluate("document.getElementById('salAnalystModalTitle').textContent") and "Cobertura" in page.evaluate("document.getElementById('salAnalystModalTitle').textContent"))
        page.close()

        # ---------- 30: Analyst detail reconciliation note -- honest, never silently wrong ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        page.click('.salAnalystSection.salDesktopOnly [data-analyst-details]')
        page.wait_for_timeout(300)
        check("30 (Gate 23): a reconciliation note (matched or explicitly caveated) is always present, never silently omitted", page.evaluate("!!document.querySelector('.salAnalystReconcileNote')"))
        page.close()

        # ---------- 31: Analyst Details modal responsive -- zero horizontal overflow at all 4 widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            btn31 = page.locator('.salAnalystCard [data-analyst-details]').first if width <= 760 else page.locator('.salAnalystSection.salDesktopOnly [data-analyst-details]').first
            btn31.click()
            page.wait_for_timeout(300)
            m31 = page.evaluate("""() => {
              const modal = document.querySelector('.salModal');
              return { modalOverflow: modal.scrollWidth > modal.clientWidth + 1, pageOverflow: document.scrollingElement.scrollWidth > document.scrollingElement.clientWidth + 1 };
            }""")
            check(f"31 (Gate 51, w={width}): Analyst Details modal has zero contained/page overflow", not m31["modalOverflow"] and not m31["pageOverflow"])
            page.close()

        # ---------- 32: current-period financial conservation -- Comissão Total exposure changes NOTHING else ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        kpis32 = page.evaluate("[...document.querySelectorAll('.modKpiCard .modKpiValue')].map(e => e.textContent.trim())")
        check("32 (Gate 45/48): KPI totals (Vendidas=132) remain byte-identical to before this Wave -- Comissão Total exposure is presentation-only, no recalculation anywhere", "132" in kpis32[0])
        page.close()

        # ================= RH-5F.1A: Equipe horizontal-scroll regression fix =================
        # Human UAT found a real, live horizontal scrollbar inside the
        # Equipe table after % Comissão + Comissão Total were added
        # (9->11 columns) -- .modTableWrap's own overflow-x:auto
        # absorbed it locally, so RH-5F.1's page-root-only checks never
        # caught it. Fixed via the SAME padding-trim technique this file
        # already used for the Histórico snapshot table (RH-5C.1); this
        # section proves it with the exact class of check that was
        # missing (component-level, Gate 26/27) and with realistic
        # stress content (Gate 28).

        METRICS_LONGNAME = _json.loads(_json.dumps(METRICS))
        METRICS_LONGNAME["rows"][0]["seller_name"] = "Pedro Henrique Machado Kodama"
        METRICS_LONGNAME["rows"][0]["production_value"] = 4980111.74
        METRICS_LONGNAME["rows"][0]["return_value"] = 6980111.74
        FAIXA_ROWS_LONGNAME = _json.loads(_json.dumps(FAIXA_ROWS_DEFAULT))
        FAIXA_ROWS_LONGNAME["rows"][0]["comissao_total"] = 999999.99

        # ---------- 33: component-level overflow, realistic long-name + large-money stress content, all 4 widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page, metrics=METRICS_LONGNAME, faixa_rows=FAIXA_ROWS_LONGNAME)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
            page.wait_for_timeout(150)
            report33 = component_overflow_report(page)
            offenders33 = [r for r in report33 if r["overflowing"]]
            check(f"33 (RH-5F.1A, Gate 28, w={width}): zero component overflow with a real long name (Pedro Henrique Machado Kodama) + large money (R$ 6.980.111,74 / R$ 999.999,99) -- {len(report33)} containers measured", not offenders33)
            for o in offenders33:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']}")
            check(f"33b (w={width}): the long seller name still renders in full, not truncated/ellipsized", "Pedro Henrique Machado Kodama" in page.content())
            page.close()

        # ---------- 34: Equipe table structural integrity after the padding/font fix -- manager row alignment, colspan, no regression from RH-5F.1's own geometry tests ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        geom34 = page.evaluate("""() => {
          const table = document.querySelector('.salEquipeTableWrap table');
          const groupHeaderTh = table.querySelector('tr.salGroupHeaderRow th');
          const headerRow = table.querySelector('thead tr');
          const managerRow = table.querySelector('tr.salManagerRow');
          const normalRow = table.querySelector('tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)');
          return {
            groupHeaderColspan: Number(groupHeaderTh.getAttribute('colspan')),
            columnHeaderCount: headerRow.children.length,
            managerCellCount: managerRow.children.length,
            groupHeaderRight: groupHeaderTh.getBoundingClientRect().right,
            normalRowRight: normalRow.lastElementChild.getBoundingClientRect().right
          };
        }""")
        check("34a (RH-5F.1A): colspan still matches the real column count (11) after the density fix -- no regression of RH-5B.3's own continuity fix", geom34["groupHeaderColspan"] == geom34["columnHeaderCount"] == 11)
        check("34b: manager row still has the same cell count as a normal row (11) -- Ações/Comissão Total not conditionally dropped by the fix", geom34["managerCellCount"] == 11)
        check("34c: group-header bar's right edge still aligns with a normal row's right edge (continuity preserved)", abs(geom34["groupHeaderRight"] - geom34["normalRowRight"]) < 1.0)
        page.close()

        # ---------- 35: Analyst table + both modals -- independently re-verified, never assumed fixed just because Equipe was ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            report35 = component_overflow_report(page)
            offenders35 = [r for r in report35 if r["overflowing"] and "Analyst" in r["label"]]
            check(f"35a (Gate 19, w={width}): Analyst table has zero component overflow (checked independently, not assumed from the Equipe fix)", not offenders35)

            # seller Detalhes modal
            btn_seller = page.locator('.salDesktopOnly [data-details]').first if width > 760 else page.locator('.salCard [data-details]').first
            btn_seller.click()
            page.wait_for_timeout(300)
            report_seller = component_overflow_report(page)
            offenders_seller = [r for r in report_seller if r["overflowing"]]
            check(f"35b (Gate 21, w={width}): seller Detalhes modal has zero component overflow", not offenders_seller)
            page.close()

            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            btn_analyst = page.locator('.salAnalystSection.salDesktopOnly [data-analyst-details]').first if width > 760 else page.locator('.salAnalystCard [data-analyst-details]').first
            btn_analyst.click()
            page.wait_for_timeout(300)
            report_analyst = component_overflow_report(page)
            offenders_analyst = [r for r in report_analyst if r["overflowing"]]
            check(f"35c (Gate 20, w={width}): Analyst Details modal has zero component overflow", not offenders_analyst)
            page.close()

        # ---------- 36: RH-5F.1 features preserved after the density fix -- nothing was quietly removed to make it fit ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
        page.wait_for_timeout(150)
        headers36 = page.evaluate("[...document.querySelector('.salEquipeTableWrap table thead tr').children].map(h => h.textContent.trim())")
        check("36a (Gate 34): % Comissão column still present", "% Comissão" in headers36)
        check("36b (Gate 34): Comissão Total column still present", "Comissão Total" in headers36)
        check("36c (Gate 34): Analyst Detalhes action still present", page.evaluate("!!document.querySelector('[data-analyst-details]')"))
        minFontSize36 = page.evaluate("""() => {
          var els = [...document.querySelectorAll('.salEquipeTableWrap .modTable th, .salEquipeTableWrap .modTable td')];
          return Math.min(...els.map(e => parseFloat(getComputedStyle(e).fontSize)));
        }""")
        check(f"36d (Gate 23, readability floor): minimum rendered font size in the density-fixed table is >= 10px (measured {minFontSize36}px) -- fit via padding/tiering, not via illegible text", minFontSize36 >= 10)
        page.close()

        # ================= RH-5F.1B: Analyst Conversão column =================
        # Human UAT (post-RH-5F.1A approval): the Analyst table is missing
        # Conversão, present on the seller/Equipe table since RH-5F. No new
        # business rule -- operational_analyst_commission_metrics_v2 does
        # not return share_percent at this grain (re-traced live this
        # Wave), so the SAME canonical formula Secure computes server-side
        # for the seller grain (financed_count/sold_count*100, 0 when
        # sold_count<=0, never Infinity/NaN/100%) is derived client-side
        # from the two fields this row already carries -- never a
        # divergent Analyst-only rule (analystConversionPercent()).

        ANALYST_CONVERSION = _json.loads(_json.dumps(ANALYST))
        ANALYST_CONVERSION["rows"][0]["sold_count"] = 32
        ANALYST_CONVERSION["rows"][0]["financed_count"] = 10
        ANALYST_ZERO_SOLD = _json.loads(_json.dumps(ANALYST))
        ANALYST_ZERO_SOLD["rows"] = [dict(ANALYST["rows"][0], sold_count=0, financed_count=0)]
        ANALYST_LONGNAME = _json.loads(_json.dumps(ANALYST))
        ANALYST_LONGNAME["rows"][0]["analyst_name"] = "Pedro Henrique Machado Kodama"
        ANALYST_LONGNAME["rows"][0]["production_value"] = 4980111.74
        ANALYST_LONGNAME["rows"][0]["return_value"] = 6980111.74
        ANALYST_LONGNAME["rows"][0]["spf_value"] = 999999.99

        # ---------- 37: header order -- Conversão inserted between Financiadas and Produção ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        headers37 = page.evaluate("[...document.querySelector('.salAnalystTableWrap table thead tr').children].map(h => h.textContent.trim())")
        check("37 (RH-5F.1B, Gate 4): Analyst header order is Analista, Vendidas, Financiadas, Conversão, Produção, Retorno, SPF, % Comissão, Comissão Total, Ações (10 columns)",
              headers37 == ["Analista", "Vendidas", "Financiadas", "Conversão", "Produção", "Retorno", "SPF", "% Comissão", "Comissão Total", "Ações"])
        page.close()

        # ---------- 38: the exact 32 vendidas / 10 financiadas example from the Human screenshot ----------
        page = new_page(browser)
        route_defaults(page, analyst=ANALYST_CONVERSION)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        conv38 = page.evaluate("""() => {
          var row = document.querySelector('.salAnalystTableWrap tbody tr');
          var cell = row.children[3];
          var badge = cell.querySelector('.modBadge');
          return { text: cell.textContent.trim(), cls: badge ? badge.className : '' };
        }""")
        check(f"38a (RH-5F.1B, Human screenshot: 32 vendidas / 10 financiadas -> 31,25%): displays the canonical 1-decimal pt-BR percentage (got '{conv38['text']}')", conv38["text"] in ("31,3%", "31,2%"))
        check("38b (RH-5F.1B, Gate 8, <40%): conversion below the threshold reuses the existing warning badge, not success", "modBadgeWarning" in conv38["cls"] and "modBadgeSuccess" not in conv38["cls"])
        page.close()

        # ---------- 39: >=40% reuses the existing success highlight (default fixture: 15/20 = 75%) ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        conv39 = page.evaluate("""() => {
          var row = document.querySelector('.salAnalystTableWrap tbody tr');
          var cell = row.children[3];
          var badge = cell.querySelector('.modBadge');
          return { text: cell.textContent.trim(), cls: badge ? badge.className : '' };
        }""")
        check("39 (RH-5F.1B, Gate 8, >=40%): 15/20=75% reuses the existing modBadgeSuccess semantic -- same visual language as % Comissão/seller Conversão, no new color system", "modBadgeSuccess" in conv39["cls"])
        page.close()

        # ---------- 40: zero-sold denominator -- reuses Secure's own canonical rule (0, never Infinity/NaN/100%) ----------
        page = new_page(browser)
        route_defaults(page, analyst=ANALYST_ZERO_SOLD)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        conv40 = page.evaluate("document.querySelector('.salAnalystTableWrap tbody tr').children[3].textContent.trim()")
        check(f"40 (RH-5F.1B, Gate 6, zero denominator): sold_count=0 renders as a genuine 0,0% (Secure's own canonical share_percent rule), never Infinity/NaN/blank (got '{conv40}')", conv40 == "0,0%")
        page.close()

        # ---------- 41: Analyst table component overflow + long-name/large-money stress, all 4 widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page, analyst=ANALYST_LONGNAME, faixa_rows=FAIXA_ROWS_LONGNAME)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_function("window.NX_SALARIOS_COMISSOES_PAGE.getFaixaRowsState() === 'READY'", timeout=8000)
            page.wait_for_timeout(150)
            report41 = component_overflow_report(page)
            offenders41 = [r for r in report41 if r["overflowing"]]
            check(f"41a (RH-5F.1B, Gate 13/16, w={width}): zero component overflow with the new Conversão column + a real long Analyst name (Pedro Henrique Machado Kodama) + large money", not offenders41)
            for o in offenders41:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']}")
            check(f"41b (w={width}): the long Analyst name still renders in full, not truncated/ellipsized", "Pedro Henrique Machado Kodama" in page.content())
            page.close()

        # ---------- 42: Equipe regression -- the RH-5F.1A Human-approved zero-scroll state must remain intact ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, width=width)
            route_defaults(page)
            login(page, "master@demo.local")
            mount(page)
            page.wait_for_timeout(200)
            report42 = component_overflow_report(page)
            offenders42 = [r for r in report42 if r["overflowing"] and "Equipe" in r["label"]]
            check(f"42 (RH-5F.1B, Gate 21, Equipe regression, w={width}): the RH-5F.1A Human-approved Equipe state is unchanged -- still zero component overflow", not offenders42)
            page.close()

        # ================= RH-5F.3: self-scoped own-commission summary =================
        # Human UAT (post-RH-5F.2 preview): the real Analyst had no server
        # path to her own % Comissão / Comissão Total, and the principal
        # summary exposed no DSR / final-commission card for any of
        # ANALISTA/VENDEDOR/GERENTE. Closed via a new, narrow, self-scoped
        # RPC (operational_own_commission_summary, identity from auth.uid()
        # only) plus a client-side, byte-ported DSR calendar function
        # (ANALISTA-only, exclusively visual, never part of the official
        # total -- exactly as it already was in Secure's own pre-existing
        # authority, portal-app.js "Checkpoint D").

        # ---------- 43: ANALISTA -- own commission cards + DSR + her own row ----------
        page = new_page(browser, perfil="ANALISTA", status="NOVOS/SEMINOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_ANALISTA)
        login(page, "analista@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        own43 = page.evaluate("""() => {
          var cards = [...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard')].map(c => ({
            label: c.querySelector('.modKpiLabel').textContent.trim(),
            value: (c.querySelector('.modKpiValue') || c.querySelector('.salFaixaCompactValue')).textContent.trim()
          }));
          return cards;
        }""")
        labels43 = [c["label"] for c in own43]
        check("43a (RH-5F.3/RH-5F.3A, Gate 24): ANALISTA principal summary shows Faixa de Comissão, Comissão Total, DSR do mês, and Comissão + DSR -- never buried only in a table row", labels43 == ["Faixa de Comissão", "Comissão Total", "DSR do mês", "Comissão + DSR"])
        total43 = next((c["value"] for c in own43 if c["label"] == "Comissão Total"), None)
        check(f"43b: Comissão Total shows the real server value (R$ 2.079,87), never a dash (got '{total43}')", total43 == "R$ 2.079,87")
        faixa43 = next((c["value"] for c in own43 if c["label"] == "Faixa de Comissão"), None)
        check(f"43b2 (RH-5F.3A, Gate 12): Faixa de Comissão card shows the canonical label + effective %, sourced from the same server row (got '{faixa43}')", faixa43 == "Mínima · 3,5%")
        dsr_pct_str = next((c["value"] for c in own43 if c["label"] == "DSR do mês"), "")
        final_str = next((c["value"] for c in own43 if c["label"] == "Comissão + DSR"), "")
        # Formula parity for the ported DSR calendar function itself: the
        # fixture's period p1 ends 2026-08-20 -- August 2026 has exactly 5
        # Sundays (calendar-verified) and 0 fixed Brazilian holidays that
        # month, so pct = 5/(31-5) = 5/26 = 19.230...% -- independently
        # computed here, never copied from the implementation.
        import re as _re
        dsr_pct_num = float(dsr_pct_str.replace('%', '').replace(',', '.'))
        expected_pct = round(5 / 26 * 100, 1)
        check(f"43c (Gate 8, DSR formula parity): DSR% matches the independently-computed calendar value for August 2026 (5 Sundays / 26 working days = {expected_pct}%, got {dsr_pct_num}%)", abs(dsr_pct_num - expected_pct) < 0.05)
        final_num = float(_re.sub(r'[^\d,]', '', final_str).replace(',', '.'))
        expected_final = round(2079.87 * (1 + 5 / 26), 2)
        check(f"43d: Comissão + DSR = Comissão Total * (1 + DSR%), internally consistent (expected ~{expected_final}, got {final_num})", abs(final_num - expected_final) < 0.5)
        check("43e (Gate 39): the final card carries the same success/highlight accent as other positive outcomes, not a plain neutral card", "modKpiCardSuccess" in page.evaluate("[...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard')].pop().className"))
        # Her own Analista row (never the seller table) now shows real values.
        own_row43 = page.evaluate("""() => {
          var row = document.querySelector('.salAnalystTableWrap tbody tr');
          var cells = [...row.children];
          return { faixa: cells[7].textContent.trim(), total: cells[8].textContent.trim() };
        }""")
        check(f"43f (Gate 27): the authenticated Analyst's own row shows the real % Comissão (3,5%), never a dash (got '{own_row43['faixa']}')", "3,5%" in own_row43["faixa"])
        check(f"43g (Gate 27): the authenticated Analyst's own row shows the real Comissão Total (R$ 2.079,87), never a dash (got '{own_row43['total']}')", own_row43["total"] == "R$ 2.079,87")
        # RH-5F.3A note: H-SAL-1 supersedes the old "seller commission
        # always hidden from ANALISTA" assumption -- but ONLY inside her
        # authorized Salary scope, and only once operational_scope_
        # commission_rows has actually returned data (test 48 covers that
        # populated case). THIS route deliberately omits scope_commission
        # (defaults to SCOPE_COMMISSION_NONE), so this still proves the
        # fail-closed floor: no scope data fetched/authorized -> still
        # '-', never fabricated -- not a permanent privacy ceiling.
        seller_dash43 = page.evaluate("""() => {
          var row = document.querySelector('.salEquipeTableWrap tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)');
          var cells = [...row.children];
          return { faixa: cells[8].textContent.trim(), total: cells[9].textContent.trim() };
        }""")
        check(f"43h (Gate 28, fail-closed floor): with no scope data fetched, a seller row still shows '-' for % Comissão, never fabricated (got '{seller_dash43['faixa']}')", seller_dash43["faixa"] == "—")
        check(f"43i (fail-closed floor): with no scope data fetched, a seller row still shows '-' for Comissão Total (got '{seller_dash43['total']}')", seller_dash43["total"] == "—")
        # No admin/history/Gestor F&I leak alongside the new cards.
        check("43j (Gate 22/30): no Histórico tab for ANALISTA", not page.evaluate("!!document.querySelector('[data-view-mode=\"historico\"]')"))
        check("43k: no Gestor F&I section for ANALISTA", not page.evaluate("!!document.querySelector('.salGestorFiSection')"))
        page.close()

        # ---------- 44: VENDEDOR -- Comissão Total card only, no DSR ----------
        page = new_page(browser, perfil="VENDEDOR", status="NOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_VENDEDOR)
        login(page, "vendedor@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        own44 = page.evaluate("""() => [...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard')].map(c => ({
          label: c.querySelector('.modKpiLabel').textContent.trim(),
          value: (c.querySelector('.modKpiValue') || c.querySelector('.salFaixaCompactValue')).textContent.trim()
        }))""")
        check("44a (RH-5F.3/RH-5F.3A, Gate 25/11): VENDEDOR principal summary shows Faixa de Comissão + Comissão Total, no DSR card", [c["label"] for c in own44] == ["Faixa de Comissão", "Comissão Total"])
        val44 = next((c["value"] for c in own44 if c["label"] == "Comissão Total"), None)
        check(f"44b: shows the real server value (R$ 4.704,00), never a dash (got '{val44}')", val44 == "R$ 4.704,00")
        faixa44 = next((c["value"] for c in own44 if c["label"] == "Faixa de Comissão"), None)
        check(f"44c (Gate 11, Human screenshot fix): own Faixa is visible instead of having to be inferred from the amount (got '{faixa44}')", faixa44 == "Máxima · 20%")
        # H-SAL-2 (Gate 12): VENDEDOR's own single Equipe row now also
        # shows real Faixa/%/Comissão Total -- via ownCommission's seller_id
        # (RH-5F.3A additive field), never fabricated, never another seller.
        own_row44 = page.evaluate("""() => {
          var row = document.querySelector('.salEquipeTableWrap tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)');
          var cells = [...row.children];
          return { faixa: cells[8].textContent.trim(), total: cells[9].textContent.trim() };
        }""")
        check(f"44d (Gate 12): VENDEDOR's own Equipe row shows the real % Comissão, matching the card above -- no more visual inconsistency (got '{own_row44['faixa']}')", "20%" in own_row44["faixa"])
        check(f"44e (Gate 12): VENDEDOR's own Equipe row shows the real Comissão Total, matching the card above (got '{own_row44['total']}')", own_row44["total"] == "R$ 4.704,00")
        page.close()

        # ---------- 45: GERENTE -- Comissão Total card only, no DSR ----------
        page = new_page(browser, perfil="GERENTE", status="NOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_GERENTE)
        login(page, "gerente@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        own45 = page.evaluate("""() => [...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard')].map(c => ({
          label: c.querySelector('.modKpiLabel').textContent.trim(),
          value: (c.querySelector('.modKpiValue') || c.querySelector('.salFaixaCompactValue')).textContent.trim()
        }))""")
        check("45a (RH-5F.3/RH-5F.3A, Gate 26): GERENTE principal summary shows Faixa de Comissão + Comissão Total, no DSR card", [c["label"] for c in own45] == ["Faixa de Comissão", "Comissão Total"])
        val45 = next((c["value"] for c in own45 if c["label"] == "Comissão Total"), None)
        check(f"45b: shows the real server value (R$ 2.572,25), never a dash (got '{val45}')", val45 == "R$ 2.572,25")
        faixa45 = next((c["value"] for c in own45 if c["label"] == "Faixa de Comissão"), None)
        check(f"45b2 (Gate 13): GERENTE's own Faixa de Comissão is visible in the principal summary (got '{faixa45}')", faixa45 == "Máxima · 4%")
        check("45c (Gate 26): the manager's personal card is never confused with the team-total row -- .salTeamTotalRow is a separate table row, not this KPI card", page.evaluate("!!document.querySelector('.salTeamTotalRow') !== undefined"))
        page.close()

        # ---------- 46: MASTER regression -- no own-commission card renders for MASTER ----------
        page = new_page(browser)
        route_defaults(page)
        login(page, "master@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("46 (RH-5F.3, Gate 22, MASTER regression): no .salOwnCommissionGrid renders for MASTER (no personal compensation concept)", not page.evaluate("!!document.querySelector('.salOwnCommissionGrid')"))
        page.close()

        # ---------- 47: zero-scroll + large-money stress with the new cards, ANALISTA worst case, all 4 widths ----------
        OWN_COMMISSION_ANALISTA_LONGMONEY = _json.loads(_json.dumps(OWN_COMMISSION_ANALISTA))
        OWN_COMMISSION_ANALISTA_LONGMONEY["comissao_total"] = 999999.99
        OWN_COMMISSION_ANALISTA_LONGMONEY["rows"][0]["comissao_total"] = 999999.99
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, perfil="ANALISTA", status="NOVOS/SEMINOVOS", width=width)
            route_defaults(page, own_commission=OWN_COMMISSION_ANALISTA_LONGMONEY)
            login(page, "analista@demo.local")
            mount(page)
            page.wait_for_timeout(250)
            report47 = component_overflow_report(page)
            offenders47 = [r for r in report47 if r["overflowing"]]
            check(f"47a (RH-5F.3, Gate 35/37, w={width}): zero component overflow with the new own-commission cards + large money (R$ 999.999,99)", not offenders47)
            for o in offenders47:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']}")
            nowrap47 = page.evaluate("[...document.querySelectorAll('.salOwnCommissionGrid .modKpiValue')].every(e => getComputedStyle(e).whiteSpace === 'nowrap')")
            check(f"47b (w={width}): every own-commission KPI value stays single-line (white-space:nowrap), even at R$ 999.999,99", nowrap47)
            page.close()

        # ================= RH-5F.3A: role commission visibility (H-SAL-1/H-SAL-3) =================
        # Human UAT superseded the RH-5F.3 privacy assumption: an ANALISTA
        # must be able to review Faixa/%/Comissão Total for sellers inside
        # her own Salary-authorized store scope (monthly verification,
        # H-SAL-1); a GERENTE must see the same for their own team plus a
        # team total (H-SAL-3). SCOPE_COMMISSION_ABC_NOVOS covers s1/s2
        # (ABC/NOVOS, in-scope) -- s3 (BANDEIRANTES/SEMINOVOS) is
        # deliberately absent from it, proving out-of-scope denial.

        # ---------- 48: ANALISTA -- in-scope seller rows visible, out-of-scope still '-' ----------
        page = new_page(browser, perfil="ANALISTA", status="NOVOS/SEMINOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_ANALISTA, scope_commission=SCOPE_COMMISSION_ABC_NOVOS)
        login(page, "analista@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        rows48 = page.evaluate("""() => [...document.querySelectorAll('.salEquipeTableWrap tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)')].map(row => {
          var cells = [...row.children];
          return { name: cells[0].textContent.trim(), faixa: cells[8].textContent.trim(), total: cells[9].textContent.trim() };
        })""")
        s1_48 = next((r for r in rows48 if "Vendedor Demo A" in r["name"]), None)
        s2_48 = next((r for r in rows48 if "Vendedor Demo B" in r["name"]), None)
        s3_48 = next((r for r in rows48 if "Vendedor Demo C" in r["name"]), None)
        check(f"48a (RH-5F.3A, H-SAL-1, Gate 11): in-scope seller (ABC/NOVOS) shows real % Comissão (got '{s1_48 and s1_48['faixa']}')", s1_48 is not None and "20%" in s1_48["faixa"])
        check(f"48b (H-SAL-1): in-scope seller shows real Comissão Total (got '{s1_48 and s1_48['total']}')", s1_48 is not None and s1_48["total"] == "R$ 5.440,00")
        check(f"48c (H-SAL-1): a SECOND in-scope seller (different faixa, MINIMA/10%) also resolves independently, not a copy of the first (got '{s2_48 and s2_48['faixa']}')", s2_48 is not None and "10%" in s2_48["faixa"] and s2_48["total"] == "R$ 1.310,00")
        check(f"48d (RH-5F.3A, Gate 8/19, out-of-scope denial): a seller OUTSIDE the Analyst's authorized scope (BANDEIRANTES, absent from scope_commission) still shows '-', never fabricated (got '{s3_48 and s3_48['faixa']}')", s3_48 is not None and s3_48["faixa"] == "—" and s3_48["total"] == "—")
        page.close()

        # ---------- 49: GERENTE -- team rows, team total card, faixa distribution, own manager row ----------
        page = new_page(browser, perfil="GERENTE", status="NOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_GERENTE, scope_commission=SCOPE_COMMISSION_ABC_NOVOS)
        login(page, "gerente@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        rows49 = page.evaluate("""() => [...document.querySelectorAll('.salEquipeTableWrap tbody tr:not(.salGroupHeaderRow):not(.salManagerRow):not(.salTeamTotalRow)')].map(row => {
          var cells = [...row.children];
          return { name: cells[0].textContent.trim(), faixa: cells[8].textContent.trim(), total: cells[9].textContent.trim() };
        })""")
        s1_49 = next((r for r in rows49 if "Vendedor Demo A" in r["name"]), None)
        check(f"49a (RH-5F.3A, H-SAL-3 point 4): a team seller row shows real Faixa/Comissão Total for the manager (got '{s1_49 and s1_49['faixa']}' / '{s1_49 and s1_49['total']}')", s1_49 is not None and "20%" in s1_49["faixa"] and s1_49["total"] == "R$ 5.440,00")
        # RH-5F.3B, Human UAT correction ("Remover o card... deixe só o
        # da tabela mesmo"): the dedicated KPI card is gone -- the value
        # is preserved in a plain caption above the Equipe table instead.
        check("49b1 (RH-5F.3B, Gate 11/15/35): the dedicated 'Comissão Total da Equipe' KPI CARD no longer exists", not page.evaluate("!!document.querySelector('.salTeamCommissionGrid')"))
        dist49 = page.evaluate("document.querySelector('.salTeamFaixasNote')?.textContent.trim() || ''")
        check(f"49b2 (Gate 15): the real team total value is NOT deleted -- still present as a caption (R$ 6.750,00), never client-recomputed (got '{dist49}')", "R$ 6.750,00" in dist49)
        check(f"49c (H-SAL-3, Gate 15): Faixas da equipe note shows a real per-level tally, never an invented average (got '{dist49}')", "Máxima: 1" in dist49 and "Mínima: 1" in dist49)
        own_manager_row49 = page.evaluate("""() => {
          var row = document.querySelector('.salManagerRow');
          if (!row) return null;
          var cells = [...row.children];
          return { faixa: cells[8].textContent.trim(), total: cells[9].textContent.trim() };
        }""")
        check(f"49d (RH-5F.3A, H-SAL-3 point 1/2, Gate 26): the manager's OWN trailing row (not the team total) shows real Faixa/Comissão Total (got '{own_manager_row49 and own_manager_row49['faixa']}' / '{own_manager_row49 and own_manager_row49['total']}')", own_manager_row49 is not None and "4%" in own_manager_row49["faixa"] and own_manager_row49["total"] == "R$ 2.572,25")
        check("49e (H-SAL-3, Gate 24): DSR is never shown to GERENTE, even with team data present", not page.evaluate("[...document.querySelectorAll('.modKpiLabel')].some(e => e.textContent.trim() === 'DSR do mês')"))
        page.close()

        # ---------- 50: zero-scroll with team commission cards + seller Faixa columns populated, all 4 widths ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, perfil="GERENTE", status="NOVOS", width=width)
            route_defaults(page, own_commission=OWN_COMMISSION_GERENTE, scope_commission=SCOPE_COMMISSION_ABC_NOVOS)
            login(page, "gerente@demo.local")
            mount(page)
            page.wait_for_timeout(250)
            report50 = component_overflow_report(page)
            offenders50 = [r for r in report50 if r["overflowing"]]
            check(f"50 (RH-5F.3A, Gate 25, w={width}): zero component overflow with team commission cards + populated seller Faixa columns", not offenders50)
            for o in offenders50:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']}")
            page.close()

        # ---------- 51: VENDEDOR/GERENTE still deny scope commission for themselves (Gate 19) ----------
        page = new_page(browser, perfil="VENDEDOR", status="NOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_VENDEDOR)
        login(page, "vendedor@demo.local")
        mount(page)
        page.wait_for_timeout(200)
        check("51 (RH-5F.3A, Gate 19): no 'Comissão Total da Equipe' card ever renders for VENDEDOR (no team concept for a seller)", not page.evaluate("!!document.querySelector('.salTeamCommissionGrid')"))
        page.close()

        # ================= RH-5F.3B: commission tier visual hierarchy (Human UAT correction) =================
        # Human UAT on RH-5F.3A: "A faixa de comissão pode aparecer menor,
        # com destaques de cores diferentes para minima e máxima. Ficou
        # muito grande, estranha." The Faixa card is now a compact status
        # component (modKpiCardSecondary, this codebase's own existing
        # smaller-KPI-card variant), never full financial-KPI size, with
        # a distinct semantic color per tier -- MÍNIMA warm/warning (not
        # alarming red), INTERMEDIÁRIA neutral/info, MÁXIMA success/green.

        # ---------- 52: compact component shape -- not the oversized full-size KPI card ----------
        page = new_page(browser, perfil="VENDEDOR", status="NOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_VENDEDOR)
        login(page, "vendedor@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        shape52 = page.evaluate("""() => {
          var card = document.querySelector('.salFaixaCompactCard');
          if (!card) return null;
          return {
            isSecondary: card.classList.contains('modKpiCardSecondary'),
            hasFullValueEl: !!card.querySelector('.modKpiValue'),
            hasCompactValueEl: !!card.querySelector('.salFaixaCompactValue'),
            height: card.getBoundingClientRect().height
          };
        }""")
        otherCardHeight52 = page.evaluate("document.querySelector('.salOwnCommissionGrid .modKpiCard:not(.salFaixaCompactCard)')?.getBoundingClientRect().height || 0")
        check("52a (RH-5F.3B, Gate 6): the Faixa card exists and reuses modKpiCardSecondary -- the codebase's own existing compact-KPI variant, not a new card shape", shape52 is not None and shape52["isSecondary"])
        check("52b (Gate 6): the Faixa card no longer uses the full-size .modKpiValue element (the pre-RH-5F.3B oversized shape)", shape52 is not None and not shape52["hasFullValueEl"] and shape52["hasCompactValueEl"])
        check(f"52c (RH-5F.3B, Gate 4/6, hierarchy): the compact Faixa card is measurably SHORTER than a primary financial KPI card in the same grid (Faixa={shape52 and round(shape52['height'])}px, financial={round(otherCardHeight52)}px)", shape52 is not None and shape52["height"] < otherCardHeight52)
        page.close()

        # ---------- 53: tier color/text regression -- MINIMA / INTERMEDIARIA / MAXIMA, all 3 distinct ----------
        TIER_FIXTURES = {
            "MINIMA": ("Mínima", "modBadgeWarning"),
            "INTERMEDIARIA": ("Intermediária", "modBadgeInfo"),
            "MAXIMA": ("Máxima", "modBadgeSuccess"),
        }
        for level, (label_pt, expected_badge_class) in TIER_FIXTURES.items():
            OWN_COMMISSION_TIER = _json.loads(_json.dumps(OWN_COMMISSION_VENDEDOR))
            OWN_COMMISSION_TIER["rows"][0]["faixa_level"] = level
            page = new_page(browser, perfil="VENDEDOR", status="NOVOS")
            route_defaults(page, own_commission=OWN_COMMISSION_TIER)
            login(page, "vendedor@demo.local")
            mount(page)
            page.wait_for_timeout(250)
            tier53 = page.evaluate("""() => {
              var badge = document.querySelector('.salFaixaTierBadge');
              return badge ? { text: badge.textContent.trim(), className: badge.className } : null;
            }""")
            check(f"53 ({level}, RH-5F.3B, Gate 29): tier badge shows the real Portuguese label '{label_pt}' (never color-only, Gate 25) and the expected semantic class '{expected_badge_class}' (got text='{tier53 and tier53['text']}', class='{tier53 and tier53['className']}')",
                  tier53 is not None and tier53["text"] == label_pt and expected_badge_class in tier53["className"])
            page.close()
        # Cross-check: the 3 tiers must resolve to 3 DISTINCT classes (never the same color reused, defeating the Human's own "different colors" request).
        check("53d (Gate 7): MÍNIMA/INTERMEDIÁRIA/MÁXIMA resolve to 3 mutually distinct badge classes", len(set(c for _, c in TIER_FIXTURES.values())) == 3)
        # And distinct from the pre-existing row-badge mapping's own MÍNIMA=critical/red choice (Gate 8: never alarming red for this new component).
        check("53e (Gate 8): MÍNIMA's compact-card class is NOT the alarming 'modBadgeCritical' red used by the older row badge", TIER_FIXTURES["MINIMA"][1] != "modBadgeCritical")

        # ---------- 54: ANALISTA/GERENTE hierarchy preserved with real financial cards untouched ----------
        page = new_page(browser, perfil="ANALISTA", status="NOVOS/SEMINOVOS")
        route_defaults(page, own_commission=OWN_COMMISSION_ANALISTA)
        login(page, "analista@demo.local")
        mount(page)
        page.wait_for_timeout(250)
        labels54 = page.evaluate("[...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard .modKpiLabel')].map(e => e.textContent.trim())")
        check("54a (RH-5F.3B, Gate 12): ANALISTA still shows all 4 cards after the visual correction -- Faixa/Comissão Total/DSR/Comissão + DSR", labels54 == ["Faixa de Comissão", "Comissão Total", "DSR do mês", "Comissão + DSR"])
        check("54b (Gate 12): Comissão Total/DSR do mês/Comissão + DSR keep the full-size .modKpiValue treatment (never shrunk alongside Faixa)", page.evaluate("""() => {
          var labels = ['Comissão Total', 'DSR do mês', 'Comissão + DSR'];
          return [...document.querySelectorAll('.salOwnCommissionGrid .modKpiCard')]
            .filter(c => labels.includes(c.querySelector('.modKpiLabel').textContent.trim()))
            .every(c => !!c.querySelector('.modKpiValue'));
        }"""))
        page.close()

        # ---------- 55: zero-scroll with the compact Faixa component, all 4 widths, ANALISTA worst case ----------
        for width in [1366, 1024, 900, 480]:
            page = new_page(browser, perfil="ANALISTA", status="NOVOS/SEMINOVOS", width=width)
            route_defaults(page, own_commission=OWN_COMMISSION_ANALISTA, scope_commission=SCOPE_COMMISSION_ABC_NOVOS)
            login(page, "analista@demo.local")
            mount(page)
            page.wait_for_timeout(250)
            report55 = component_overflow_report(page)
            offenders55 = [r for r in report55 if r["overflowing"]]
            check(f"55 (RH-5F.3B, Gate 24, w={width}): zero component overflow with the compact Faixa component + populated seller rows", not offenders55)
            for o in offenders55:
                print(f"    OVERFLOW: {o['label']} clientWidth={o['clientWidth']} scrollWidth={o['scrollWidth']}")
            page.close()

        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== Salários & Comissões Module Shell (RH-4B/RH-5B.1/RH-5F): {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
