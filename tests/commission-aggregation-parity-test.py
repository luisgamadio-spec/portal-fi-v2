#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM-5J -- full aggregation-layer parity between the REAL V1/Authority
secure-mode closing preview (calcularPreviewFechamentoCompetenciaSegura
+ snapshotRowsPayload + the literal p_summary object inside
fecharCompetencia, all extracted byte-identically in tests/.source/
commission-aggregation-v1-reference.js) and the new V2 production
engine (assets/js/adapters/master-competence-closing-engine.js).

Same real-browser-execution technique as PM-5I's commission-engine-
parity-test.py and this repo's own cash-conversion-parity-test.py --
never a Python reimplementation.

0 real financial data. All fixtures synthetic.
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CALC_REF_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/tests/.source/commission-calc-v1-reference.js"
AGG_REF_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/tests/.source/commission-aggregation-v1-reference.js"
V2_ENGINE_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/master-competence-closing-engine.js"

DEFAULT_CFG = {
    "share_minimo": 40, "spf_liquido_percentual": 70, "bonus_spf_analista": 150,
    "limite_retorno_novos": 12000, "limite_retorno_seminovos": 8000,
    "vendedor_faixa_baixo_share_baixo": 10, "vendedor_faixa_baixo_share_alto": 15,
    "vendedor_faixa_alto_share_baixo": 15, "vendedor_faixa_alto_share_alto": 20,
    "gerente_faixa_share_baixo": 3, "gerente_faixa_share_alto": 4,
    "analista_faixa_share_baixo": 3.5, "analista_faixa_share_alto": 4.5
}

PERIODO = {"id": "per-synthetic-001", "nome_periodo": "21/07 a 20/08/2026 (sintético)",
           "data_inicio": "2026-07-21", "data_fim": "2026-08-20"}

GESTOR_IDENTITY = {"nome": "Gestor F&I Sintético", "cpf": "00000000000"}

# ---------- Full population fixture (Gate 12) ----------
VEND_ROWS = [
    # multiple sellers, multiple stores, NOVOS/SEMINOVOS/combined
    {"seller_name": "Vendedor Novos Alpha", "store": "LOJA CENTRO", "department": "NOVOS",
     "sold_count": 10, "financed_count": 3, "production_value": 500000, "return_value": 5000, "spf_value": 0, "spf_count": 0},  # share=30<40, rent=5000<12000
    {"seller_name": "Vendedor Novos Beta", "store": "LOJA CENTRO", "department": "NOVOS",
     "sold_count": 10, "financed_count": 5, "production_value": 700000, "return_value": 15000, "spf_value": 2000, "spf_count": 1},  # share=50>=40, rent alto
    {"seller_name": "Vendedor Seminovos Gamma", "store": "ALPHAVILLE", "department": "SEMINOVOS",
     "sold_count": 8, "financed_count": 4, "production_value": 300000, "return_value": 7999, "spf_value": 0, "spf_count": 0},  # rent just below seminovos limite
    {"seller_name": "Vendedor Combinado Delta", "store": "EUROPA", "department": "NOVOS/SEMINOVOS",
     "sold_count": 12, "financed_count": 6, "production_value": 900000, "return_value": 20000, "spf_value": 1000, "spf_count": 1},  # contributes to BOTH manager buckets
    {"seller_name": "Vendedor Zero Epsilon", "store": "GASTAO", "department": "NOVOS",
     "sold_count": 0, "financed_count": 0, "production_value": 0, "return_value": 0, "spf_value": 0, "spf_count": 0},  # must be discarded entirely
    {"seller_name": "Vendedor Boundary Zeta", "store": "NACOES", "department": "NOVOS",
     "sold_count": 10, "financed_count": 4, "production_value": 400000, "return_value": 12000, "spf_value": 0, "spf_count": 0},  # share=40 exact, retorno=12000 exact (both boundaries)
]
VEND_TOTALS = {
    "sold_count": sum(r["sold_count"] for r in VEND_ROWS),
    "financed_count": sum(r["financed_count"] for r in VEND_ROWS),
    "production_value": sum(r["production_value"] for r in VEND_ROWS),
    "return_value": sum(r["return_value"] for r in VEND_ROWS),
    "spf_value": sum(r["spf_value"] for r in VEND_ROWS),
    "spf_count": sum(r["spf_count"] for r in VEND_ROWS),
}
ANALYST_ROWS = [
    {"analyst_name": "Analista Um", "store": "LOJA CENTRO", "sold_count": 20, "financed_count": 7,
     "production_value": 600000, "return_value": 18000, "spf_value": 500, "spf_count": 1, "transfer": False},
    {"analyst_name": "Analista Substituta Dois", "store": "ALPHAVILLE", "sold_count": 5, "financed_count": 2,
     "production_value": 100000, "return_value": 3000, "spf_value": 0, "spf_count": 0, "transfer": True,
     "covered_start": "2026-07-25", "covered_end": "2026-08-05"},
]
MANAGER_ROWS = [
    {"store": "LOJA CENTRO", "department": "NOVOS", "manager_name": "Gerente Centro Novos"},
    # EUROPA/SEMINOVOS deliberately absent -> exercises "NÃO LOCALIZADO" fallback
    {"store": "europa", "department": "NOVOS", "manager_name": "Gerente Europa Novos"},  # lowercase, tests normalization
]


def build_v1_page(browser):
    page = browser.new_page()
    page.goto("about:blank")
    page.add_script_tag(path=CALC_REF_JS)
    page.add_script_tag(path=AGG_REF_JS)
    return page


def build_v2_page(browser, engine_path=None):
    page = browser.new_page()
    page.goto("about:blank")
    page.add_script_tag(path=engine_path or V2_ENGINE_JS)
    return page


def sort_key(line):
    return (line.get("perfil", ""), line.get("loja", ""), line.get("nome", ""))


def normalize_lines(lines):
    return sorted(lines, key=sort_key)


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        v1 = build_v1_page(browser)
        v2 = build_v2_page(browser)

        v1.evaluate("""(args) => {
            window.V1_AGGREGATION_REFERENCE.setFixture(
                { rows: args.vendRows, totals: args.vendTotals },
                args.analystRows, args.managerRows,
                [{ id: window.V1_AGGREGATION_REFERENCE.GESTOR_FI_USUARIO_ID_SEGURO, ativo: true, nome: args.gestorIdentity.nome, cpf: args.gestorIdentity.cpf }]
            );
        }""", {"vendRows": VEND_ROWS, "vendTotals": VEND_TOTALS, "analystRows": ANALYST_ROWS,
               "managerRows": MANAGER_ROWS, "gestorIdentity": GESTOR_IDENTITY})
        v1_preview = v1.evaluate("() => window.V1_AGGREGATION_REFERENCE.calcularPreviewFechamentoCompetenciaSegura()")

        v2_preview = v2.evaluate("""(args) => {
            return window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.buildPreviewLines({
                vendRows: args.vendRows, analystRows: args.analystRows, managerRows: args.managerRows,
                gestorTotals: args.vendTotals, gestorIdentity: args.gestorIdentity, cfg: args.cfg
            });
        }""", {"vendRows": VEND_ROWS, "analystRows": ANALYST_ROWS, "managerRows": MANAGER_ROWS,
               "vendTotals": VEND_TOTALS, "gestorIdentity": GESTOR_IDENTITY, "cfg": DEFAULT_CFG})

        # ---------- 1: aggregation parity (Gate 13) ----------
        v1_lines_n = normalize_lines(v1_preview["linhas"])
        v2_lines_n = normalize_lines(v2_preview["linhas"])
        results.append(("1 (AGGREGATION PARITY): same row count", len(v1_lines_n) == len(v2_lines_n), len(v1_lines_n), len(v2_lines_n)))
        results.append(("1b: expected discard of the 100%-zero seller row (Vendedor Zero Epsilon never appears)",
                         not any(l.get("nome") == "Vendedor Zero Epsilon" for l in v1_lines_n) and not any(l.get("nome") == "Vendedor Zero Epsilon" for l in v2_lines_n), None, None))
        # Real, found-not-introduced quirk of the AUTHORITATIVE V1 source
        # (portal-app.js:4924-4926, verbatim in both extractions): the
        # bucket-grouping check is `dep.includes('NOVOS')` /
        # `dep.includes('SEMINOVOS')` -- and "SEMINOVOS".includes('NOVOS')
        # is TRUE in JS (NOVOS is a literal substring/suffix of
        # SEMINOVOS), so a seller whose department is PURELY "SEMINOVOS"
        # (not the explicit combined "NOVOS/SEMINOVOS" status) still
        # contributes to BOTH the NOVOS and SEMINOVOS manager buckets for
        # their store. Confirmed present in the real V1 source itself
        # (not an artifact of this extraction) and preserved verbatim in
        # V2 per Gate 9 (No Reinterpretation) -- this fixture deliberately
        # includes a pure-SEMINOVOS seller (Vendedor Seminovos Gamma,
        # ALPHAVILLE) specifically to surface and pin this real behavior:
        # expect 6 GERENTE rows (not 4), with an "ALPHAVILLE GERENTE
        # NOVOS" row existing despite zero NOVOS sellers ever being in
        # that store, sourced entirely from the SEMINOVOS seller's own
        # metrics.
        results.append(("1c (REAL QUIRK, PRESERVED NOT FIXED): a pure-SEMINOVOS seller also contributes to the store's NOVOS manager bucket ('SEMINOVOS'.includes('NOVOS')===true) -- 6 GERENTE rows expected, identical in V1 and V2",
                         sum(1 for l in v1_lines_n if l.get("perfil") == "GERENTE") == 6 and sum(1 for l in v2_lines_n if l.get("perfil") == "GERENTE") == 6
                         and any(l.get("loja") == "ALPHAVILLE" and l.get("status") == "GERENTE NOVOS" for l in v1_lines_n)
                         and any(l.get("loja") == "ALPHAVILLE" and l.get("status") == "GERENTE NOVOS" for l in v2_lines_n),
                         sorted((l.get("loja"), l.get("status")) for l in v1_lines_n if l.get("perfil") == "GERENTE"),
                         sorted((l.get("loja"), l.get("status")) for l in v2_lines_n if l.get("perfil") == "GERENTE")))
        results.append(("1d: manager-not-found fallback matches ('GERENTE SEMINOVOS NÃO LOCALIZADO')",
                         any("NÃO LOCALIZADO" in str(l.get("nome", "")) for l in v1_lines_n) and any("NÃO LOCALIZADO" in str(l.get("nome", "")) for l in v2_lines_n), None, None))
        results.append(("1e: store-name normalization matches (lowercase 'europa' row still finds the manager)",
                         any(l.get("nome") == "Gerente Europa Novos" for l in v1_lines_n) == any(l.get("nome") == "Gerente Europa Novos" for l in v2_lines_n), None, None))

        field_mismatches = []
        for a, b in zip(v1_lines_n, v2_lines_n):
            for f in ("perfil", "loja", "nome", "status", "comissao"):
                if json.dumps(a.get(f), sort_keys=True) != json.dumps(b.get(f), sort_keys=True):
                    field_mismatches.append((a.get("nome"), f, a.get(f), b.get(f)))
            for f in ("vendidas", "financiadas", "producao", "retorno", "spf", "spfQty"):
                if json.dumps((a.get("m") or {}).get(f), sort_keys=True) != json.dumps((b.get("m") or {}).get(f), sort_keys=True):
                    field_mismatches.append((a.get("nome"), "m." + f, a.get("m"), b.get("m")))
            for f in ("share", "faixa", "rentTotal", "spfLiquido", "comissaoPrincipal", "comissaoSpf", "comissaoTotal"):
                if json.dumps((a.get("c") or {}).get(f), sort_keys=True) != json.dumps((b.get("c") or {}).get(f), sort_keys=True):
                    field_mismatches.append((a.get("nome"), "c." + f, a.get("c"), b.get("c")))
        results.append(("2 (AGGREGATION PARITY): every field of every row is EXACTLY equal (vendidas/financiadas/producao/retorno/share/spf_extra/spf_liquido/rentabilidade/faixa/comissao_principal/comissao_spf/comissao_total)", len(field_mismatches) == 0, field_mismatches[:3] if field_mismatches else None, None))

        results.append(("3: summary totals match (vendidas/financiadas/producao/retorno/spf/comissaoPrevista)",
                         json.dumps({k: v1_preview[k] for k in ("vendidas", "financiadas", "producao", "retorno", "spf", "comissaoPrevista")}, sort_keys=True) ==
                         json.dumps({k: v2_preview[k] for k in ("vendidas", "financiadas", "producao", "retorno", "spf", "comissaoPrevista")}, sort_keys=True),
                         {k: v1_preview[k] for k in ("vendidas", "financiadas", "producao", "retorno", "spf", "comissaoPrevista")},
                         {k: v2_preview[k] for k in ("vendidas", "financiadas", "producao", "retorno", "spf", "comissaoPrevista")}))

        # ---------- 4: p_rows (snapshotRowsPayload) parity (Gate 14/15) ----------
        v1_rows = v1.evaluate("(args) => window.V1_AGGREGATION_REFERENCE.snapshotRowsPayload({linhas: args.linhas}, args.periodo, null)",
                               {"linhas": v1_preview["linhas"], "periodo": PERIODO})
        v2_rows = v2.evaluate("(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.buildSnapshotRowsPayload({linhas: args.linhas}, args.periodo, null)",
                               {"linhas": v2_preview["linhas"], "periodo": PERIODO})
        v1_rows_n = sorted(v1_rows, key=lambda r: (r["perfil"], r["loja"], r["nome"]))
        v2_rows_n = sorted(v2_rows, key=lambda r: (r["perfil"], r["loja"], r["nome"]))

        v1_keys = sorted(v1_rows_n[0].keys()) if v1_rows_n else []
        v2_keys = sorted(v2_rows_n[0].keys()) if v2_rows_n else []
        results.append(("4 (P_ROWS_ACTUAL_KEY_COUNT): builder produces 21 keys per row (revalidated programmatically, not trusted from any prior report)", len(v1_keys) == 21 and len(v2_keys) == 21, len(v1_keys), len(v2_keys)))
        results.append(("4b: V1 and V2 p_rows key SETS are identical", v1_keys == v2_keys, v1_keys, v2_keys))
        results.append(("5 (P_ROWS PARITY): every row, every field, EXACTLY equal between V1 and V2 builders",
                         json.dumps(v1_rows_n, sort_keys=True) == json.dumps(v2_rows_n, sort_keys=True), None, None))

        # ---------- 6: p_summary parity (Gate 16) ----------
        v1_summary = v1.evaluate("(args) => window.V1_AGGREGATION_REFERENCE.buildSummaryPayloadV1(args.periodo, args.executivo, args.linhasCount, args.comissaoPrevista, args.cpf, args.nome)",
                                  {"periodo": PERIODO, "executivo": {"vendidas": v1_preview["vendidas"], "financiadas": v1_preview["financiadas"], "producao": v1_preview["producao"], "retorno": v1_preview["retorno"], "spf": v1_preview["spf"]},
                                   "linhasCount": len(v1_preview["linhas"]), "comissaoPrevista": v1_preview["comissaoPrevista"], "cpf": "11122233344", "nome": "Master Sintético"})
        v2_summary = v2.evaluate("(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.buildSummaryPayload({periodo: args.periodo, executivo: args.executivo, linhasCount: args.linhasCount, comissaoPrevista: args.comissaoPrevista, fechadoPorCpf: args.cpf, fechadoPorNome: args.nome})",
                                  {"periodo": PERIODO, "executivo": {"vendidas": v2_preview["vendidas"], "financiadas": v2_preview["financiadas"], "producao": v2_preview["producao"], "retorno": v2_preview["retorno"], "spf": v2_preview["spf"]},
                                   "linhasCount": len(v2_preview["linhas"]), "comissaoPrevista": v2_preview["comissaoPrevista"], "cpf": "11122233344", "nome": "Master Sintético"})
        results.append(("6 (P_SUMMARY SCHEMA): 14 keys, revalidated programmatically", len(v1_summary.keys()) == 14 and len(v2_summary.keys()) == 14, sorted(v1_summary.keys()), sorted(v2_summary.keys())))
        results.append(("7 (P_SUMMARY PARITY): every field EXACTLY equal", json.dumps(v1_summary, sort_keys=True) == json.dumps(v2_summary, sort_keys=True), v1_summary, v2_summary))

        # ---------- 8: FULL_CLOSING_PAYLOAD_PARITY (Gate 17) ----------
        v1_payload = {"p_period_id": PERIODO["id"], "p_summary": v1_summary, "p_rows": v1_rows_n}
        v2_payload = {"p_period_id": PERIODO["id"], "p_summary": v2_summary, "p_rows": v2_rows_n}
        results.append(("8 (FULL_CLOSING_PAYLOAD_PARITY): {p_period_id,p_summary,p_rows} fully equal between V1 and V2", json.dumps(v1_payload, sort_keys=True) == json.dumps(v2_payload, sort_keys=True), None, None))

        # ---------- 9-10: Gestor identity fail-closed gate (Gate 20/47) ----------
        v1.evaluate("""(args) => {
            window.V1_AGGREGATION_REFERENCE.setFixture(
                { rows: args.vendRows, totals: args.vendTotals }, args.analystRows, args.managerRows, []
            );
        }""", {"vendRows": VEND_ROWS, "vendTotals": VEND_TOTALS, "analystRows": ANALYST_ROWS, "managerRows": MANAGER_ROWS})
        v1_blocked = v1.evaluate("() => window.V1_AGGREGATION_REFERENCE.calcularPreviewFechamentoCompetenciaSegura()")
        v2_blocked = v2.evaluate("""(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.buildPreviewLines({
            vendRows: args.vendRows, analystRows: args.analystRows, managerRows: args.managerRows,
            gestorTotals: args.vendTotals, gestorIdentity: null, cfg: args.cfg
        })""", {"vendRows": VEND_ROWS, "analystRows": ANALYST_ROWS, "managerRows": MANAGER_ROWS, "vendTotals": VEND_TOTALS, "cfg": DEFAULT_CFG})
        results.append(("9 (GESTOR IDENTITY GATE, V1): missing identity blocks the WHOLE preview (returns null), not just the Gestor row", v1_blocked is None, v1_blocked, None))
        results.append(("10 (GESTOR IDENTITY GATE, V2): missing identity blocks the WHOLE preview (returns null) -- same real invariant preserved", v2_blocked is None, None, v2_blocked))

        # ---------- 11: MUTATION TEST (Gate 46) -- prove the parity test
        # actually protects the formula, using an INLINE corrupted copy
        # (never touches the real file on disk). ----------
        mutated_source = io.open(V2_ENGINE_JS, "r", encoding="utf-8").read().replace(
            "const faixa = share < 40 ? 0.0016 : 0.0030;", "const faixa = share < 40 ? 0.0020 : 0.0030;"  # Gestor F&I faixa corrupted
        )
        assert "0.0020" in mutated_source and mutated_source != io.open(V2_ENGINE_JS, "r", encoding="utf-8").read(), "mutation did not apply"
        v2_mutated = build_v2_page(browser)
        v2_mutated.add_script_tag(content=mutated_source)
        v2_mutated_preview = v2_mutated.evaluate("""(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.buildPreviewLines({
            vendRows: args.vendRows, analystRows: args.analystRows, managerRows: args.managerRows,
            gestorTotals: args.vendTotals, gestorIdentity: args.gestorIdentity, cfg: args.cfg
        })""", {"vendRows": VEND_ROWS, "analystRows": ANALYST_ROWS, "managerRows": MANAGER_ROWS, "vendTotals": VEND_TOTALS, "gestorIdentity": GESTOR_IDENTITY, "cfg": DEFAULT_CFG})
        mutation_detected = json.dumps(normalize_lines(v1_preview["linhas"]), sort_keys=True) != json.dumps(normalize_lines(v2_mutated_preview["linhas"]), sort_keys=True)
        results.append(("11a (MUTATION TEST): a deliberately corrupted Gestor F&I faixa constant IS caught by this same comparison (proves the test has teeth)", mutation_detected, None, None))
        real_file_untouched = io.open(V2_ENGINE_JS, "r", encoding="utf-8").read().find("0.0020") == -1
        results.append(("11b (MUTATION TEST): the real engine file on disk was NEVER modified (mutation was purely in-memory)", real_file_untouched, None, None))
        v2_mutated.close()

        v1.close()
        v2.close()
        browser.close()

    passed = sum(1 for r in results if r[1])
    for name, ok, a, b in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  a={a!r} b={b!r}" if (a is not None or b is not None) else ""))
    print(f"\n=== Commission Aggregation V1 x V2 Parity: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
