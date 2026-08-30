#!/usr/bin/env python3
"""
Gate 27 — Pre-Wave Check.

Run this before starting ANY future Wave (PORTAL-NEXT-03 onward). It
does not block anything automatically -- it makes context errors
EVIDENT, which is the actual requirement ("nao precisa bloquear tudo
automaticamente, mas deve tornar erro de contexto evidente").
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(V2_ROOT)
DS21 = os.path.join(LAB_ROOT, "design-system-2.1")
SKILL = os.path.join(LAB_ROOT, "design-system-skill-01")

def git(args, cwd):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception as e:
        return f"<error: {e}>"

def main():
    print("=== PORTAL-NEXT V2 — Pre-Wave Check ===\n")

    print(f"V2 root:            {V2_ROOT}")
    branch = git(["branch", "--show-current"], V2_ROOT)
    head_raw = git(["rev-parse", "HEAD"], V2_ROOT)
    head = head_raw if "error" not in head_raw else "<no commits yet>"
    remotes = git(["remote", "-v"], V2_ROOT)
    print(f"V2 git branch:       {branch or '<no branch / no commits yet>'}")
    print(f"V2 HEAD:             {head}")
    print(f"V2 remotes:          {remotes or '(none — correct, no remote should exist)'}")

    print(f"\nEnvironment:         NEXT_LOCAL (see assets/js/environment-guard.js)")

    print("\nNetwork targets expected: 0 (Supabase / Edge / OpenAI / brabus.blistiq.com.br)")
    print("  -> verify with tests/foundation-regression.py and a real-browser network capture.")

    print(f"\nDesign System authority: {DS21}")
    print(f"  exists: {os.path.isdir(DS21)}")
    print(f"  NORMATIVE.md exists: {os.path.isfile(os.path.join(DS21, 'NORMATIVE.md'))}")

    print(f"\nSkill authority: {SKILL}")
    print(f"  exists: {os.path.isdir(SKILL)}")
    print(f"  SKILL.md exists: {os.path.isfile(os.path.join(SKILL, 'SKILL.md'))}")

    fp = json.load(open(os.path.join(HERE, "production-fingerprint.json"), encoding="utf-8"))
    print(f"\nProduction main fingerprint (recorded): {fp['realRemoteMainHead']}")
    print("  -> run config/v1-change-detection.py for a LIVE comparison against this.")

    v1_repo = os.path.join(os.path.dirname(LAB_ROOT), "portal-financiamento-brabus-secure")
    v1_branch = git(["branch", "--show-current"], v1_repo)
    print(f"\nV1 production repo current branch (sanity check — must be 'main', never")
    print(f"a feature branch you might accidentally commit V2 work into): {v1_branch}")
    if v1_branch != "main":
        print("  *** CONTEXT ERROR: V1 checkout is not on main. STOP and investigate")
        print("  *** before doing anything else — this is exactly the ambiguous-context")
        print("  *** situation Gate 35 requires treating as a STOP, given main has no")
        print("  *** branch protection (PORTAL-NEXT-01.1 Blocker #4).")

    print("\n=== End of Pre-Wave Check — review above before starting a Wave. ===")

if __name__ == "__main__":
    main()
