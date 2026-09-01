#!/usr/bin/env python3
"""
PORTAL V2 SECURE-DELTA WAVE 2 -- Gestão RPC Contract Tests (Gate 19).

Validates the RPC-shaped local contract reconciliation: store-display
lookup, the fixture provider's mechanical filtering (no business
logic), and the thin adapter's response normalization. Does NOT
validate business-rule correctness (that's the backend RPC's job,
proven read-only in Wave 1) -- these tests only prove the LOCAL
surface (a) never re-derives identity/authorization and (b) correctly
passes through whatever shape it's given.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import json
import sys

BASE = "http://localhost:8700/portal-next-v2/tests/fixtures/_gestao-rpc-contract-harness.html"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available -- harness code exists, not executed.")
        sys.exit(0)

    results = []

    def check(name, ok, detail=""):
        results.append((name, ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not ok else ""))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE)
        if errors:
            print("[FATAL] harness page errors:", errors)
            sys.exit(1)

        # 1. canonical store selector values
        codes = page.evaluate("() => window.NX_STORE_DISPLAY.CANONICAL_STORES")
        expected_codes = ["ABC", "ALPHAVILLE", "ANALIA FRANCO", "BANDEIRANTES", "BARRA FUNDA", "EUROPA", "GASTAO", "NACOES"]
        check("1. canonical store selector values", codes == expected_codes, f"got {codes}")

        # 2. storeDisplayName()
        display = page.evaluate("() => window.NX_STORE_DISPLAY.storeDisplayName('GASTAO')")
        check("2. storeDisplayName()", display == "Gastão Vidigal", f"got {display!r}")

        # 3. unknown display fallback
        fallback = page.evaluate("() => window.NX_STORE_DISPLAY.storeDisplayName('XYZ-UNKNOWN')")
        check("3. unknown display fallback", fallback == "XYZ-UNKNOWN", f"got {fallback!r}")

        # 4. adapter does not canonicalize store strings
        src = page.evaluate("() => window.NX_GESTAO_ADAPTER.normalizeResponse.toString() + ' ' + Object.keys(window.NX_GESTAO_ADAPTER).join(',')")
        no_canon_fn = not any(name in src for name in ["lojaCurta", "normalizeStoreName", "cleanTextKey"])
        check("4. adapter does not canonicalize store strings", no_canon_fn, src[:200])

        # 5. adapter does not contain profile authorization
        adapter_keys = page.evaluate("() => Object.keys(window.NX_GESTAO_ADAPTER)")
        no_rbac = not any(k in adapter_keys for k in ["storeMatches", "vehicleMatches", "buildCpfAnalysis"]) and \
            "ANALISTA" not in json.dumps(adapter_keys)
        check("5. adapter does not contain profile authorization", no_rbac, str(adapter_keys))

        # 6. ANALISTA ALL fixture contract (no profile concept -- store=null proves group-wide)
        r = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({start:'2026-01-01',end:'2026-06-30',store:null,department:null})")
        check("6. ANALISTA ALL fixture contract (group-wide)", len(r["stores"]) == 8, f"stores={len(r['stores'])}")

        # 7. ANALISTA specific-store fixture contract
        r2 = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({start:'2026-01-01',end:'2026-06-30',store:'BARRA FUNDA',department:null})")
        check("7. ANALISTA specific-store fixture contract", len(r2["stores"]) == 1 and r2["stores"][0]["store"] == "BARRA FUNDA", json.dumps(r2["stores"]))

        # 8. unknown-store fail-closed fixture contract
        r3 = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({start:'2026-01-01',end:'2026-06-30',store:'XYZ-UNKNOWN',department:null})")
        empty = (r3["stores"] == [] and r3["proposal_outcomes"] == [] and r3["summary"]["operational_quantity"] == 0)
        check("8. unknown-store fail-closed (empty, not group-wide)", empty, json.dumps(r3))

        # 9. long status_by_store handling
        r4 = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({store:null,department:null})")
        sbs_shape_ok = all(set(row.keys()) == {"store", "status", "quantity", "financed_value"} for row in r4["status_by_store"])
        check("9. long status_by_store handling", sbs_shape_ok and len(r4["status_by_store"]) > 8, f"n={len(r4['status_by_store'])}")

        # 10. long status_by_bank handling
        sbb_shape_ok = all(set(row.keys()) == {"bank", "status", "quantity", "financed_value"} for row in r4["status_by_bank"])
        check("10. long status_by_bank handling", sbb_shape_ok, json.dumps(r4["status_by_bank"][:1]))

        # 11. plans_by_store_department handling
        pbsd_shape_ok = all(set(row.keys()) == {"store", "department", "plan_type", "quantity"} for row in r4["plans_by_store_department"])
        check("11. plans_by_store_department handling", pbsd_shape_ok, json.dumps(r4["plans_by_store_department"][:1]))

        # 12. proposal_outcomes APROVADA
        aprovadas = [o for o in r4["proposal_outcomes"] if o["outcome"] == "APROVADA"]
        check("12. proposal_outcomes APROVADA", len(aprovadas) > 0 and all(o["quantity"] > 0 for o in aprovadas), f"n={len(aprovadas)}")

        # 13. proposal_outcomes RECUSADA
        recusadas = [o for o in r4["proposal_outcomes"] if o["outcome"] == "RECUSADA"]
        check("13. proposal_outcomes RECUSADA", len(recusadas) > 0 and all(o["quantity"] > 0 for o in recusadas), f"n={len(recusadas)}")

        # 14. summary passthrough
        expected_qty = sum(s["quantity"] for s in r4["stores"])
        check("14. summary passthrough", r4["summary"]["operational_quantity"] == expected_qty, f"{r4['summary']['operational_quantity']} vs {expected_qty}")

        # 15. SPF spf_70_value passthrough (0 local recompute -- exactly value*0.70 as supplied, not re-derived by a different formula)
        spf_ok = all(abs(row["spf_70_value"] - round(row["spf_value"] * 0.70, 2)) < 0.01 for row in r4["spf_extra"]) and len(r4["spf_extra"]) > 0
        check("15. SPF spf_70_value passthrough", spf_ok, json.dumps(r4["spf_extra"][:2]))

        # 16. NOVOS department filter
        r5 = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({store:null,department:'NOVOS'})")
        novos_ok = all(s["used_quantity"] == 0 for s in r5["stores"]) and all(row["department"] == "NOVOS" for row in r5["plans_by_store_department"])
        check("16. NOVOS department filter", novos_ok, json.dumps(r5["stores"][:1]))

        # 17. SEMINOVOS department filter
        r6 = page.evaluate("() => window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({store:null,department:'SEMINOVOS'})")
        semi_ok = all(s["new_quantity"] == 0 for s in r6["stores"]) and all(row["department"] == "SEMINOVOS" for row in r6["plans_by_store_department"])
        check("17. SEMINOVOS department filter", semi_ok, json.dumps(r6["stores"][:1]))

        # 18. ALL department (department=null) returns both
        both_depts = set(row["department"] for row in r4["plans_by_store_department"])
        check("18. ALL department returns both NOVOS+SEMINOVOS", both_depts == {"NOVOS", "SEMINOVOS"}, str(both_depts))

        # 19. no old CPF proposal-outcome algorithm remains active in the active adapter
        active_adapter_keys = page.evaluate("() => Object.keys(window.NX_GESTAO_ADAPTER)")
        no_old_algo = not any(k in active_adapter_keys for k in ["buildCpfAnalysis", "compute", "normalizeRows"])
        check("19. no old CPF proposal-outcome algorithm active", no_old_algo, str(active_adapter_keys))

        # 20. no lojaCurta identity path remains active
        check("20. no lojaCurta identity path active", "lojaCurta" not in active_adapter_keys, str(active_adapter_keys))

        browser.close()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Gestão RPC Contract: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
