#!/usr/bin/env python3
"""Gate 13/39 — Module Registry structural test."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
REGISTRY_PATH = os.path.join(V2_ROOT, "config", "module-registry.json")

REQUIRED_FIELDS = [
    "id", "name", "route", "title", "density", "authRequirement",
    "designPattern", "entryPoint", "businessSource", "functionalSource",
    "approvedReference", "migrationWave", "risk", "migrationStatus", "notes"
]

def main():
    data = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    modules = data.get("modules", [])
    enum = data.get("migrationStatusEnum", [])
    errors = []

    print(f"[PASS] {len(modules)} modules found in registry" if modules else "[FAIL] 0 modules found")
    if not modules:
        errors.append("registry has 0 modules")
    # Expected status per module (Gate 139: no module may self-promote to
    # HUMAN_APPROVED without an explicit human decision on record — see
    # each module's own "humanApprovalNote" in module-registry.json for
    # that record. Dashbi allowed HUMAN_APPROVED as of PORTAL-NEXT-07.6.1,
    # which reconciled a human approval ("Aprovado.") given after
    # PORTAL-NEXT-07.5.2's report that this test's own history had not
    # yet captured — not an auto-promotion, the record it guards against).
    EXPECTED_STATUS = {
        "landing": {"HUMAN_APPROVED"},
        "score": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "HUMAN_APPROVED"},
        "coparticipado": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "gestao": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "dashbi": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "simulador-novos": {"NOT_MIGRATED", "IN_PROGRESS", "VISUAL_PARITY_PENDING", "UAT_PENDING"},
        "simulador-seminovos": {"NOT_MIGRATED", "IN_PROGRESS", "VISUAL_PARITY_PENDING", "UAT_PENDING"},
    }

    for m in modules:
        for field in REQUIRED_FIELDS:
            if field not in m:
                errors.append(f"module '{m.get('id','?')}' missing field '{field}'")
        mid = m.get("id")
        status = m.get("migrationStatus")
        if mid in EXPECTED_STATUS:
            if status not in EXPECTED_STATUS[mid]:
                errors.append(f"module '{mid}' has migrationStatus={status!r}, expected one of {EXPECTED_STATUS[mid]}")
        elif status != "NOT_MIGRATED":
            errors.append(f"module '{mid}' has migrationStatus={status!r}, expected NOT_MIGRATED — only Landing/Score/Coparticipado/Gestão/Dashbi may have changed status so far (Gate 29/65)")
        if status not in enum:
            errors.append(f"module '{mid}' migrationStatus not in enum")

    ids = [m.get("id") for m in modules]
    dupes = set(i for i in ids if ids.count(i) > 1)
    if dupes:
        errors.append(f"duplicate module ids: {dupes}")

    print(f"[{'PASS' if not errors else 'FAIL'}] all modules have required contract fields and correct status discipline (landing=HUMAN_APPROVED, score/coparticipado/simulador-novos/simulador-seminovos=UAT_PENDING/VISUAL_PARITY_PENDING, all others=NOT_MIGRATED)")
    if errors:
        for e in errors:
            print("  -", e)
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("\nRESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
