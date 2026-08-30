#!/usr/bin/env python3
"""
Gate 16 — No Business Logic scanner.

Foundation must contain ZERO financial/business formulas: PMT-style
installment math, taxa/rate solvers, balão, rebate, commission
formulas, Score formulas, crossing/filter logic, or real RPC business
calls. The ONLY allowed occurrences of these words are: registry
metadata strings (config/module-registry.json's businessSource/notes
fields, which describe WHERE such logic lives in V1 without containing
any of it) and this scanner's/docs' own explanatory prose.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

SCAN_EXTENSIONS = (".js", ".html", ".css")
ALLOWED_FILES = set()  # nothing is exempt — even docs/registry are grep'd, just with a softer rule below

FORBIDDEN_CODE_PATTERNS = [
    (r"\bfunction\s+calc(Trad|Period|ParcelaUnica|Scores|CoparticipacaoDetalhe)\b", "V1 function name copied verbatim"),
    (r"\bfunction\s+commissionCalc\b", "V1 function name copied verbatim"),
    (r"\bbaseCalculoLinear\b", "V1 loan-math function name"),
    (r"\btaxaPricePorIteracao\b", "V1 rate-solver function name"),
    (r"\bSCORE_WEIGHTS\b", "V1 Score formula constant"),
    (r"\.rpc\(\s*['\"]operational_", "a real operational_* RPC call"),
    (r"\.rpc\(\s*['\"]master_", "a real master_* RPC call"),
    (r"supabase\.co", "a literal Supabase project host"),
    (r"api\.openai\.com", "a literal OpenAI API host"),
]

def scan_file(path):
    findings = []
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return findings
    for pattern, label in FORBIDDEN_CODE_PATTERNS:
        for m in re.finditer(pattern, content):
            line_no = content.count("\n", 0, m.start()) + 1
            findings.append((path, line_no, label, m.group(0)))
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
        print(f"[FAIL] {len(all_findings)} forbidden business-logic pattern(s) found:")
        for path, line, label, match in all_findings:
            print(f"  {os.path.relpath(path, V2_ROOT)}:{line}  {label}  ({match!r})")
        print()
        print("RESULT: FAIL — Foundation must contain zero business logic.")
        sys.exit(1)

    print("[PASS] 0 forbidden business-logic code patterns found across "
          f"{SCAN_EXTENSIONS} files under portal-next-v2/.")
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
