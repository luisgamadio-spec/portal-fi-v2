#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM-5J Gate 10 -- re-runs the exact same 33 PM-5I formula-level cases
(imported verbatim from commission-engine-parity-test.py, never
retyped/duplicated) against the actual V2 PRODUCTION module
(assets/js/adapters/master-competence-closing-engine.js), not the
narrower tests/.source/ reference copy PM-5I itself validated. Proves
the module V2 will really ship achieves the same exact parity, not
just its test-only extraction.
"""
import io
import json
import sys

V1_REF_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/tests/.source/commission-calc-v1-reference.js"
V2_ENGINE_JS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/master-competence-closing-engine.js"

# Import CASES/GESTOR_CASES/DEFAULT_CFG verbatim from commission-engine-
# parity-test.py (PM-5I) WITHOUT re-executing its own stdout-wrapping/
# main-guard top-level code (that file wraps sys.stdout at module level,
# which would double-wrap and close the buffer if exec'd normally here).
_pm5i_src = io.open("C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/tests/commission-engine-parity-test.py", "r", encoding="utf-8").read()
_pm5i_src = _pm5i_src.replace("sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=\"utf-8\")", "")
_pm5i_ns = {"__name__": "commission_engine_parity_imported"}
exec(compile(_pm5i_src, "commission-engine-parity-test.py", "exec"), _pm5i_ns)
CASES = _pm5i_ns["CASES"]
GESTOR_CASES = _pm5i_ns["GESTOR_CASES"]
DEFAULT_CFG = _pm5i_ns["DEFAULT_CFG"]

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        ref = browser.new_page()
        ref.goto("about:blank")
        ref.add_script_tag(path=V1_REF_JS)

        v2 = browser.new_page()
        v2.goto("about:blank")
        v2.add_script_tag(path=V2_ENGINE_JS)

        for c in CASES:
            ref_r = ref.evaluate("(c) => window.V1_REFERENCE.commissionCalc(c.status, c.m, c.cls)", c)
            v2_r = v2.evaluate("(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.commissionCalc(args.c.status, args.c.m, args.c.cls, args.cfg)", {"c": c, "cfg": DEFAULT_CFG})
            ok = json.dumps(ref_r, sort_keys=True) == json.dumps(v2_r, sort_keys=True)
            results.append((c["id"], ok, ref_r, v2_r))

        for c in GESTOR_CASES:
            ref_r = ref.evaluate("(c) => window.V1_REFERENCE.calcGestorFIGrupo(c.m)", c)
            # V1_REFERENCE.calcGestorFIGrupo (PM-5I) takes the internal
            # metric shape (vendidas/financiadas/...) directly, matching
            # portal-app.js's own module-global `t`. The V2 PRODUCTION
            # module's calcGestorFIGrupo(totals, cfg) instead takes the
            # RAW RPC totals shape (sold_count/financed_count/...) per
            # its own header comment/contract (it is meant to be called
            # directly with operational_commission_metrics's own
            # `totals` object, never a pre-renamed copy) -- convert here,
            # this is a test-fixture shape adapter, not a formula change.
            rpc_totals = {
                "sold_count": c["m"]["vendidas"], "financed_count": c["m"]["financiadas"],
                "production_value": c["m"]["producao"], "return_value": c["m"]["retorno"],
                "spf_value": c["m"]["spf"], "spf_count": c["m"]["spfQty"]
            }
            v2_r = v2.evaluate("(args) => window.NX_MASTER_COMPETENCE_CLOSING_ENGINE.calcGestorFIGrupo(args.totals, args.cfg)", {"totals": rpc_totals, "cfg": DEFAULT_CFG})
            ref_norm = {"share": ref_r["share"], "faixa": ref_r["faixa"], "spfLiquido": ref_r["spfLiquido"],
                        "rentTotal": ref_r["base"], "comissaoPrincipal": ref_r["comissaoPrincipal"],
                        "bonusSpf": ref_r["bonusSpf"], "comissaoFinal": ref_r["comissaoFinal"]}
            v2_norm = {"share": v2_r["share"], "faixa": v2_r["faixa"], "spfLiquido": v2_r["spfLiquido"],
                       "rentTotal": v2_r["base"], "comissaoPrincipal": v2_r["comissaoPrincipal"],
                       "bonusSpf": v2_r["bonusSpf"], "comissaoFinal": v2_r["comissaoFinal"]}
            ok = json.dumps(ref_norm, sort_keys=True) == json.dumps(v2_norm, sort_keys=True)
            results.append(("gestor:" + c["id"], ok, ref_norm, v2_norm))

        browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, rv, av in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  ref={rv!r} v2_production={av!r}")
    print(f"\n=== Commission Engine V1 x V2-PRODUCTION-MODULE Parity: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
