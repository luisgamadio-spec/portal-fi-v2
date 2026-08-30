#!/usr/bin/env python3
"""
Gate 16 (Foundation) / Gate 25, 32-34 (PORTAL-NEXT-04) — No UNAUTHORIZED
Business Logic scanner.

Every Wave authorizes exactly which business logic may exist in V2 and
where. As of PORTAL-NEXT-04, Score's calcScores()/SCORE_WEIGHTS are
authorized, but ONLY inside assets/js/adapters/score.adapter.js (a
byte-identical extraction, see docs/SCORE-ENGINE-AUDIT.md) — anywhere
else is still forbidden (would mean an unauthorized duplicate/leak).
Simulator math, commission formulas, and AI/RPC calls remain forbidden
EVERYWHERE, no exceptions (Gates 32-34: no commission touch, no AI
touch, no simulator touch this Wave).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

SCAN_EXTENSIONS = (".js", ".html", ".css")

# path is relative to V2_ROOT, forward-slash form
ALWAYS_FORBIDDEN = [
    (r"\bfunction\s+calc(Trad|Period|ParcelaUnica|CoparticipacaoDetalhe)\b", "V1 simulator/coparticipado function name — Gate 34/32 forbid touching this Wave"),
    (r"\bfunction\s+commissionCalc\b", "V1 commission function name — Gate 32 forbids touching this Wave"),
    (r"\bbaseCalculoLinear\b", "V1 loan-math function name — Gate 34 forbids touching this Wave"),
    (r"\btaxaPricePorIteracao\b", "V1 rate-solver function name — Gate 34 forbids touching this Wave"),
    (r"\.rpc\(\s*['\"]operational_", "a real operational_* RPC call — 0 backend this Wave (Gate 8)"),
    (r"\.rpc\(\s*['\"]master_", "a real master_* RPC call — 0 backend this Wave (Gate 8)"),
    (r"supabase\.co", "a literal Supabase project host — 0 backend this Wave (Gate 8)"),
    (r"api\.openai\.com", "a literal OpenAI API host — Gate 33 forbids AI this Wave"),
    (r"portal-ai-ui|portal-ai\b", "Brabus Intelligence reference — Gate 33 forbids AI this Wave"),
]

# patterns authorized ONLY inside specific files (path relative to V2_ROOT, forward slashes)
SCOPED_AUTHORIZATIONS = {
    r"\bfunction\s+calcScores\b": {"assets/js/adapters/score.adapter.js"},
    r"\bSCORE_WEIGHTS\b": {"assets/js/adapters/score.adapter.js"},
    r"\bMIX_PLANOS_UNIVERSO\b": {"assets/js/adapters/score.adapter.js"},
}

def rel(path):
    return os.path.relpath(path, V2_ROOT).replace(os.sep, "/")

def scan_file(path):
    findings = []
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return findings
    r = rel(path)

    for pattern, label in ALWAYS_FORBIDDEN:
        for m in re.finditer(pattern, content):
            line_no = content.count("\n", 0, m.start()) + 1
            findings.append((path, line_no, label, m.group(0)))

    for pattern, allowed_files in SCOPED_AUTHORIZATIONS.items():
        if r in allowed_files:
            continue
        for m in re.finditer(pattern, content):
            line_no = content.count("\n", 0, m.start()) + 1
            findings.append((path, line_no, f"Score-authorized pattern found OUTSIDE its authorized file ({sorted(allowed_files)})", m.group(0)))

    return findings

def main():
    all_findings = []
    for root, dirs, files in os.walk(V2_ROOT):
        if ".git" in root.split(os.sep):
            continue
        for fn in files:
            if fn.endswith(SCAN_EXTENSIONS):
                all_findings.extend(scan_file(os.path.join(root, fn)))

    if all_findings:
        print(f"[FAIL] {len(all_findings)} unauthorized business-logic pattern(s) found:")
        for path, line, label, match in all_findings:
            print(f"  {rel(path)}:{line}  {label}  ({match!r})")
        print()
        print("RESULT: FAIL")
        sys.exit(1)

    print("[PASS] 0 unauthorized business-logic patterns found across "
          f"{SCAN_EXTENSIONS} files under portal-next-v2/.")
    print("        (Score's calcScores()/SCORE_WEIGHTS confirmed present ONLY in")
    print("        assets/js/adapters/score.adapter.js, as authorized this Wave.)")
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
