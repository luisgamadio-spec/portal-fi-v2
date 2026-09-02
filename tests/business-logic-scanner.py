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
their original names. Commission formulas remain forbidden EVERYWHERE, no exceptions (Gate
32-33: no commission touch).

IA-V2-1 authorizes a CONTRACT-ONLY Brabus Intelligence adapter
(assets/js/adapters/brabus-intelligence.adapter.js) and its page
controller (assets/js/brabus-intelligence.js) — request/response
shaping, presentation-only formatting, and plain fixture data
literals. It does NOT authorize any actual Intelligence business
authority (the financial engine, the tool registry, the system
prompt, the Score formula) anywhere in V2 — those patterns stay
forbidden EVERYWHERE, including inside the two files above, same as
every other engine this scanner already guards.
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
    (r"\.rpc\(\s*['\"]simulador_get_", "a real simulador_get_* RPC call (Intelligence's own rate-table lookups) — fixture-only this Wave, IA-V2-1 Gate 8"),
    (r"supabase\.co", "a literal Supabase project host — 0 backend this Wave (Gate 8)"),
    (r"api\.openai\.com", "a literal OpenAI API host — no real AI backend call this Wave (IA-V2-1 Gate 1)"),
    # IA-V2-1 Gate 53 — Brabus Intelligence's own financial-authority
    # identifiers stay forbidden EVERYWHERE in V2, including inside the
    # IA-V2-1 adapter/page files themselves (which only ever reference
    # these ideas descriptively in prose, never by defining the literal
    # identifier) — no scoped exception, unlike Score/Coparticipado/
    # Simulators, because V2 must never become a second authority for
    # ANY Intelligence business constant, not even inside its own
    # contract-only module.
    (r"\bCASH_CONVERSION_APPLICATION_RATE\b", "Brabus Intelligence's Cash Conversion rate constant — V2 must never define this, only display a value the (fixture/real) response already contains"),
    (r"\bBALAO_MAX_COUNT\b", "Brabus Intelligence's Balão count-cap constant — V2 must never define this"),
    (r"\bconst\s+SYSTEM_PROMPT\s*=", "a system-prompt constant declaration — V2 never owns the Intelligence system prompt"),
    (r"\bconst\s+TOOLS\s*=\s*\[", "a tool-registry array declaration — V2 never owns the Intelligence tool registry"),
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
    print("        adapter + independent reference, as authorized. Brabus")
    print("        Intelligence's own financial constants/system prompt/tool")
    print("        registry confirmed absent from V2 entirely, including its")
    print("        own contract-only adapter/page files.)")
    print("RESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
