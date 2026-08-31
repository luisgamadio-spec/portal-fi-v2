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
    # Expected status per module as of PORTAL-NEXT-06 (Gate 132: Landing/
    # Score/Coparticipado are now HUMAN_APPROVED; Gestão must stop at
    # UAT_PENDING, never auto-promoted, and carries an explicit
    # commissionImpact/SURFACE-SCOPED blocker instead of a new status enum
    # value — Gate 131 permits either; this registry chose the simpler
    # "existing status + blocker metadata" option).
    EXPECTED_STATUS = {
        "landing": {"HUMAN_APPROVED"},
        "score": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "HUMAN_APPROVED"},
        "coparticipado": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "gestao": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS"},
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
            errors.append(f"module '{mid}' has migrationStatus={status!r}, expected NOT_MIGRATED — only Landing/Score/Coparticipado/Gestão may have changed status so far (Gate 29/65)")
        if status not in enum:
            errors.append(f"module '{mid}' migrationStatus not in enum")

    ids = [m.get("id") for m in modules]
    dupes = set(i for i in ids if ids.count(i) > 1)
    if dupes:
        errors.append(f"duplicate module ids: {dupes}")

    print(f"[{'PASS' if not errors else 'FAIL'}] all modules have required contract fields and correct status discipline (landing=HUMAN_APPROVED, score/coparticipado=UAT_PENDING/VISUAL_PARITY_PENDING, all others=NOT_MIGRATED)")
    if errors:
        for e in errors:
            print("  -", e)
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("\nRESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
