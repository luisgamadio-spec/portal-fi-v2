#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTH FOUNDATION Phase 2B, Gate 27 -- module registry <-> backend
permission-catalog drift detection.

Static/structural only, no browser, no network. Compares every V2
registry module's permissionId/authMode against a fixture snapshot of
the real modulos_portal catalog captured during AUTH FOUNDATION Phase
2A's read-only forensics (see that phase's report, Section 3) -- not a
live Supabase call. A later, separate real-homolog test re-validates
against the live catalog periodically; this one catches renamed/
removed backend IDs and structural registry mistakes on every run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
REGISTRY_PATH = os.path.join(V2_ROOT, "config", "module-registry.json")

VALID_AUTH_MODES = {
    "LOGIN_REQUIRED", "PERMISSION_MATRIX", "MASTER_ONLY",
    "ANALISTA_OR_MASTER", "SEPARATE_AUTHORITY"
}

# AUTH FOUNDATION Phase 2A, Section 3 -- the audited live modulos_portal
# catalog (id -> configuravel), captured read-only from the real
# project. Fixture, not a live query.
KNOWN_BACKEND_PERMISSION_IDS = {
    "simuladorCompleto": True,
    "simuladorSeminovos": True,
    "dashbi": True,
    "gestao": True,
    "coparticipadoPortal": True,
    "analiseScoreVendedores": True,
    "comissoes": True,
    "painelAnalistaFi": False,
    "centralAtendimentoFi": False,
    "painelMaster": False,
    "gestaoBases": False,
    "gestaoSimuladores": False,
}

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def main():
    data = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    modules = data["modules"]
    check(f"registry has modules", len(modules) > 0)

    seen_permission_ids = {}
    for m in modules:
        mid = m["id"]
        auth_mode = m.get("authMode")
        permission_id = m.get("permissionId")

        check(f"{mid}: has a valid authMode ({auth_mode})", auth_mode in VALID_AUTH_MODES)

        if auth_mode == "PERMISSION_MATRIX":
            check(f"{mid}: PERMISSION_MATRIX has a permissionId", permission_id is not None)
            if permission_id is not None:
                check(f"{mid}: permissionId '{permission_id}' maps to a known, configurable backend catalog entry",
                      KNOWN_BACKEND_PERMISSION_IDS.get(permission_id) is True)
        elif auth_mode == "MASTER_ONLY":
            # MASTER_ONLY modules may legitimately reference a
            # non-configurable backend id (hardcoded-gated, per AUTH
            # FOUNDATION Phase 2A Section 17) or none at all.
            if permission_id is not None:
                check(f"{mid}: MASTER_ONLY permissionId '{permission_id}' is a known backend catalog entry",
                      permission_id in KNOWN_BACKEND_PERMISSION_IDS)
        elif auth_mode == "ANALISTA_OR_MASTER":
            check(f"{mid}: ANALISTA_OR_MASTER has a permissionId", permission_id is not None)
            if permission_id is not None:
                check(f"{mid}: permissionId '{permission_id}' is a known backend catalog entry",
                      permission_id in KNOWN_BACKEND_PERMISSION_IDS)
        elif auth_mode in ("LOGIN_REQUIRED", "SEPARATE_AUTHORITY"):
            check(f"{mid}: {auth_mode} has no permissionId (Gate 26/9: not appropriate here)", permission_id is None)

        if permission_id is not None:
            if permission_id in seen_permission_ids:
                check(f"{mid}: permissionId '{permission_id}' not duplicated (also used by {seen_permission_ids[permission_id]})", False)
            else:
                seen_permission_ids[permission_id] = mid

    # Reverse direction: every CONFIGURABLE backend catalog entry
    # should be claimed by exactly one PERMISSION_MATRIX module --
    # catches a module silently losing its mapping.
    matrix_permission_ids = {m.get("permissionId") for m in modules if m.get("authMode") == "PERMISSION_MATRIX"}
    for backend_id, configurable in KNOWN_BACKEND_PERMISSION_IDS.items():
        if configurable:
            check(f"backend catalog entry '{backend_id}' (configurable) is claimed by some PERMISSION_MATRIX module",
                  backend_id in matrix_permission_ids)

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Auth Catalog Drift Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
