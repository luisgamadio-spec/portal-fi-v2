#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CUTOVER-2 -- regression lock for the first-access cutover-compatibility
port proven in CUTOVER-1/CUTOVER-2 (V1 -> V2 custom-domain transfer).

Guards exactly the failure modes identified by CUTOVER-1 Phase 6/9:
  1. concluir-acesso.html disappearing from the V2 repo root;
  2. the official Pages build artifact omitting it;
  3. the committed copy diverging from the approved V1 production
     source (byte-for-byte SHA-256 parity, not just "a file exists");
  4. the production activation link constant no longer targeting
     https://brabus.blistiq.com.br/concluir-acesso.html (already-issued
     and future links must keep working across the domain transfer).

Pure filesystem/build-script checks -- no browser, no server, no
network, 0 real Supabase project touched.
"""
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Locked at CUTOVER-2 Phase 1 directly from V1 production (git show
# origin/main:concluir-acesso.html in portal-financiamento-brabus-secure).
# Any change to this hash means the V2 copy has drifted from the
# approved, currently-live V1 source and must be re-reconciled, not
# silently accepted.
V1_PRODUCTION_SHA256 = "5084d23092818d701fb97f9a633bc1dfac49f8ff9bed1724aeaf97d28379c7f2"

TARGET_FILE = "concluir-acesso.html"
TARGET_URL = "https://brabus.blistiq.com.br/concluir-acesso.html"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    committed = REPO_ROOT / TARGET_FILE
    check("1: concluir-acesso.html exists at V2 repo root", committed.is_file())

    if committed.is_file():
        committed_hash = sha256_of(committed)
        check(
            "2: committed copy is byte-identical to the approved V1 production source (SHA-256 parity)",
            committed_hash == V1_PRODUCTION_SHA256,
        )
    else:
        check("2: committed copy is byte-identical to the approved V1 production source (SHA-256 parity)", False)

    with tempfile.TemporaryDirectory() as tmp:
        build_script = REPO_ROOT / "scripts" / "build-pages-artifact.sh"
        proc = subprocess.run(
            ["bash", str(build_script), tmp],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        check("3: official build-pages-artifact.sh runs successfully", proc.returncode == 0)

        artifact_file = Path(tmp) / TARGET_FILE
        check("4: official Pages build artifact includes concluir-acesso.html", artifact_file.is_file())

        if artifact_file.is_file():
            check(
                "5: artifact copy is byte-identical to the approved V1 production source (SHA-256 parity)",
                sha256_of(artifact_file) == V1_PRODUCTION_SHA256,
            )
        else:
            check("5: artifact copy is byte-identical to the approved V1 production source (SHA-256 parity)", False)

        artifact_index = Path(tmp) / "index.html"
        check("6: artifact still includes index.html (allowlist addition did not displace existing entries)", artifact_index.is_file())

    provider_js = REPO_ROOT / "assets" / "js" / "adapters" / "master-users-provider.js"
    provider_src = provider_js.read_text(encoding="utf-8") if provider_js.is_file() else ""
    url_match = re.search(
        r"CONTINUACAO_PRIMEIRO_ACESSO_URL_BASE\s*=\s*'([^']+)'",
        provider_src,
    )
    check(
        "7: master-users-provider.js activation URL constant still targets the live production path",
        bool(url_match) and url_match.group(1) == TARGET_URL,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"\n=== CUTOVER-2 First-Access Compatibility: {passed}/{total} ===")
    if passed != total:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
