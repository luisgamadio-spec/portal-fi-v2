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
    for m in modules:
        for field in REQUIRED_FIELDS:
            if field not in m:
                errors.append(f"module '{m.get('id','?')}' missing field '{field}'")
        # Gate 31 (PORTAL-NEXT-03): only Landing may have moved past
        # NOT_MIGRATED this Wave. Every other module must still be
        # NOT_MIGRATED — a silent status change anywhere else is a bug.
        if m.get("id") == "landing":
            if m.get("migrationStatus") not in ("UAT_PENDING", "VISUAL_PARITY_PENDING"):
                errors.append(f"module 'landing' has migrationStatus={m.get('migrationStatus')!r}, expected UAT_PENDING or VISUAL_PARITY_PENDING after PORTAL-NEXT-03")
        elif m.get("migrationStatus") != "NOT_MIGRATED":
            errors.append(f"module '{m.get('id')}' has migrationStatus={m.get('migrationStatus')!r}, expected NOT_MIGRATED — only Landing may change status this Wave (Gate 31)")
        if m.get("migrationStatus") not in enum:
            errors.append(f"module '{m.get('id')}' migrationStatus not in enum")

    ids = [m.get("id") for m in modules]
    dupes = set(i for i in ids if ids.count(i) > 1)
    if dupes:
        errors.append(f"duplicate module ids: {dupes}")

    print(f"[{'PASS' if not errors else 'FAIL'}] all modules have required contract fields and correct status discipline (landing=UAT_PENDING/VISUAL_PARITY_PENDING, all others=NOT_MIGRATED)")
    if errors:
        for e in errors:
            print("  -", e)
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("\nRESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
