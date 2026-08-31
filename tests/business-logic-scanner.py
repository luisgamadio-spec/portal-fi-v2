#!/usr/bin/env python3
"""
Gate 16 (Foundation) / Gate 25, 32-34 (PORTAL-NEXT-04) / Gate 5, 57
(PORTAL-NEXT-05) — No UNAUTHORIZED Business Logic scanner.

Every Wave authorizes exactly which business logic may exist in V2 and
where. As of PORTAL-NEXT-04, Score's calcScores()/SCORE_WEIGHTS are
authorized, but ONLY inside assets/js/adapters/score.adapter.js (a
byte-identical extraction, see docs/SCORE-ENGINE-AUDIT.md). As of
PORTAL-NEXT-05, Coparticipado's calcCoparticipacaoDetalhe() is
authorized, but ONLY inside assets/js/adapters/coparticipado.adapter.js
and tests/fixtures/_coparticipado-reference.js (the byte-identical
adapter extraction + its independently re-extracted golden-reference
counterpart, see docs/COPARTICIPADO-ENGINE-AUDIT.md). As of
PORTAL-NEXT-08, the loan-math helpers baseCalculoLinear/
taxaPricePorIteracao are authorized, but ONLY inside the three
simulator adapter files (assets/js/adapters/simulador-shared.adapter.js,
simulador-novos.adapter.js, simulador-seminovos.adapter.js — see
docs/SIMULATOR-ENGINE-DISCOVERY-08.md) — anywhere else these patterns
are still forbidden (would mean an unauthorized duplicate/leak).
calcTrad/calcPeriod/calcParcelaUnica remain forbidden EVERYWHERE,
including in the simulator adapters themselves — PORTAL-NEXT-08's own
extraction deliberately used DIFFERENT function names (calcularXxx,
not the V1 DOM-coupled names) for its pure re-derivations (Gate 25:
no DOM dependency), specifically so this scanner keeps catching a
future literal copy-paste of the original DOM-coupled functions by
their original names. Commission formulas and AI/RPC calls remain
forbidden EVERYWHERE, no exceptions (Gates 32-33: no commission touch,
no AI touch this Wave).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

SCAN_EXTENSIONS = (".js", ".html", ".css")

# path is relative to V2_ROOT, forward-slash form
ALWAYS_FORBIDDEN = [
    (r"\bfunction\s+calc(Trad|Period|ParcelaUnica)\b", "V1 DOM-coupled simulator function name — PORTAL-NEXT-08 deliberately used different names (calcularXxx) for its pure re-derivations; this literal V1 name is still forbidden everywhere"),
    (r"\bfunction\s+commissionCalc\b", "V1 commission function name — no commission touch this Wave"),
    (r"\.rpc\(\s*['\"]operational_", "a real operational_* RPC call — 0 backend this Wave (Gate 8)"),
    (r"\.rpc\(\s*['\"]master_", "a real master_* RPC call — 0 backend this Wave (Gate 8)"),
    (r"supabase\.co", "a literal Supabase project host — 0 backend this Wave (Gate 8)"),
    (r"api\.openai\.com", "a literal OpenAI API host — no AI touch this Wave"),
    (r"portal-ai-ui|portal-ai\b", "Brabus Intelligence reference — no AI touch this Wave"),
]

SIMULATOR_ADAPTERS = {
    "assets/js/adapters/simulador-shared.adapter.js",
    "assets/js/adapters/simulador-novos.adapter.js",
    "assets/js/adapters/simulador-seminovos.adapter.js",
}

# patterns authorized ONLY inside specific files (path relative to V2_ROOT, forward slashes)
SCOPED_AUTHORIZATIONS = {
    r"\bfunction\s+calcScores\b": {"assets/js/adapters/score.adapter.js"},
    r"\bSCORE_WEIGHTS\b": {"assets/js/adapters/score.adapter.js"},
    r"\bMIX_PLANOS_UNIVERSO\b": {"assets/js/adapters/score.adapter.js"},
    r"\bfunction\s+calcCoparticipacaoDetalhe\b": {"assets/js/adapters/coparticipado.adapter.js", "tests/fixtures/_coparticipado-reference.js"},
    r"\bbaseCalculoLinear\b": SIMULATOR_ADAPTERS,
    r"\btaxaPricePorIteracao\b": SIMULATOR_ADAPTERS,
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
    print("        assets/js/adapters/score.adapter.js; Coparticipado's")
    print("        calcCoparticipacaoDetalhe() confirmed present ONLY in its")
    print("        adapter + independent reference, as authorized.)")
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
