#!/usr/bin/env python3
"""
Gate 29 — V1 change detection (read-only).

Compares config/production-fingerprint.json's recorded productionHead
against the REAL current state of origin/main, using `git ls-remote`
(lists refs only — does not fetch objects, does not touch the local
working tree, does not require write access).

If it changed: this does NOT automatically mean STOP. Per Gate 29's
own instruction, it means a REBASELINE REVIEW is required before a
future Wave trusts PORTAL-NEXT-01's audit findings or this Foundation's
production-fingerprint record as still current.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(V2_ROOT)
V1_REPO = os.path.join(os.path.dirname(LAB_ROOT), "portal-financiamento-brabus-secure")

def main():
    fp_path = os.path.join(HERE, "production-fingerprint.json")
    fp = json.load(open(fp_path, encoding="utf-8"))
    # Compare against the REAL remote tip recorded at Foundation-creation
    # time, not the (known-stale) local clone HEAD -- see
    # production-fingerprint.json's realRemoteMainHead field for why
    # these two differ as of this Foundation's creation.
    recorded = fp["realRemoteMainHead"]

    try:
        out = subprocess.run(
            ["git", "-C", V1_REPO, "ls-remote", "origin", "refs/heads/main"],
            capture_output=True, text=True, timeout=30, check=True
        )
        remote_head = out.stdout.split()[0] if out.stdout.strip() else None
    except Exception as e:
        print(f"[SKIP] could not reach origin (offline, or no network this run): {e}")
        print("This is not a failure — it means change detection could not run, not that nothing changed.")
        sys.exit(0)

    local_head = subprocess.run(
        ["git", "-C", V1_REPO, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    ).stdout.strip()

    print(f"Recorded fingerprint (realRemoteMainHead, at Foundation creation): {recorded}")
    print(f"Remote origin/main right now:                                       {remote_head}")
    print(f"(for reference only — known stale, see production-fingerprint.json)")
    print(f"Local clone HEAD right now:                                          {local_head}")
    print()

    if recorded == remote_head:
        print("RESULT: NO CHANGE — origin/main matches the fingerprint recorded when this")
        print("Foundation was created. No rebaseline review required on that basis alone.")
        sys.exit(0)
    else:
        print("RESULT: CHANGE DETECTED — origin/main has moved since this Foundation's")
        print("fingerprint was recorded. This is NOT automatically a STOP condition. It IS a")
        print("REQUIRED REBASELINE REVIEW: re-run PORTAL-NEXT-01's relevant audit sections for")
        print("anything a future Wave is about to rely on, before trusting this fingerprint's")
        print("findings (or PORTAL-NEXT-01/01.1's own findings) as still current.")
        sys.exit(2)

if __name__ == "__main__":
    main()
