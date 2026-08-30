#!/usr/bin/env python3
"""
Gate 21 — Landing Reference Resolution test.

Proves V2 CAN locate the Human Approved Executable Landing Reference —
does NOT render it, does NOT migrate Landing. Resolution only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(V2_ROOT)
NORMATIVE_JSON = os.path.join(LAB_ROOT, "design-system-2.1", "design-system.normative.json")

def main():
    errors = []
    normative = json.load(open(NORMATIVE_JSON, encoding="utf-8"))
    refs = normative.get("approvedReferences", [])
    landing = next((r for r in refs if r.get("id") == "module-landing"), None)

    if not landing:
        print("[FAIL] approvedReferences[id=module-landing] not found in design-system.normative.json")
        sys.exit(1)

    print(f"[PASS] module-landing entry found. status={landing['status']} criticality={landing['criticality']}")

    if landing["status"] != "APPROVED":
        errors.append(f"module-landing status is {landing['status']}, expected APPROVED")

    source_rel = landing["sourcePath"].split("#")[0]  # strip #landing fragment
    source_abs = os.path.join(LAB_ROOT, source_rel)
    exists = os.path.isfile(source_abs)
    print(f"[{'PASS' if exists else 'FAIL'}] sourcePath resolves to a real file: {source_rel}")
    if not exists:
        errors.append(f"sourcePath does not resolve: {source_abs}")

    for shot in landing.get("screenshots", []):
        shot_abs = os.path.join(LAB_ROOT, "design-system-2.1", shot)
        shot_exists = os.path.isfile(shot_abs)
        print(f"[{'PASS' if shot_exists else 'FAIL'}] screenshot resolves: {shot}")
        if not shot_exists:
            errors.append(f"screenshot does not resolve: {shot_abs}")

    print()
    if errors:
        print(f"RESULT: FAIL ({len(errors)} issue(s))")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("RESULT: PASS — V2 can resolve the Landing Approved Reference.")
    print("NOTE: this test does NOT render the reference and Landing was NOT migrated this phase.")
    sys.exit(0)

if __name__ == "__main__":
    main()
