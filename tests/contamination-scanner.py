#!/usr/bin/env python3
"""
Gates 33-34 — contamination scanners.

Gate 33 (prototype contamination): V2 must not have accidentally
imported facelift-prototype-01's fictional mock data, fake sellers,
fake financial values, its Voice Orb LAB variant switcher, its Guided
Tour, its LAB-only controls, or its own visual Design Trace/lab
banner. V2's OWN Design Trace dev panel is fine — it's a different,
Foundation-native tool, not an import.

Gate 34 (V1 contamination): the real portal-financiamento-brabus-secure
repo must show ZERO diff caused by this phase. Verified separately by
comparing the before/after baseline files at the Lab root — this
script only re-states the expectation and reports whether those
baseline files agree (if both are present).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(V2_ROOT)

PROTOTYPE_CONTAMINATION_PATTERNS = [
    (r"mock-data\.js", "facelift-prototype-01 mock data file name"),
    (r"DEMO_SEQUENCE", "facelift-prototype-01 Voice Orb demo sequence"),
    (r"labOnlyBanner", "facelift-prototype-01's own LAB banner class"),
    (r"Guided ?Tour", "facelift-prototype-01 Guided Tour feature"),
    (r"voiceOrbVariantSwitcher|ORB_VARIANT_SWITCHER", "facelift-prototype-01 LAB Orb variant switcher"),
    (r"FICT[IÍ]CIO", "facelift-prototype-01's fictional-data disclosure text"),
    (r"simulateVoiceAmplitude", "facelift-prototype-01 fake mic amplitude generator"),
]

def scan_prototype_contamination():
    findings = []
    for root, dirs, files in os.walk(V2_ROOT):
        if ".git" in root.split(os.sep):
            continue
        for fn in files:
            if not fn.endswith((".js", ".html", ".css", ".json")):
                continue
            path = os.path.join(root, fn)
            try:
                content = open(path, encoding="utf-8").read()
            except Exception:
                continue
            for pattern, label in PROTOTYPE_CONTAMINATION_PATTERNS:
                for m in re.finditer(pattern, content):
                    line_no = content.count("\n", 0, m.start()) + 1
                    findings.append((path, line_no, label, m.group(0)))
    return findings

def check_v1_baseline_diff():
    before = os.path.join(LAB_ROOT, ".baseline-portalnext02-before.txt")
    after = os.path.join(LAB_ROOT, ".baseline-portalnext02-after.txt")
    if not (os.path.isfile(before) and os.path.isfile(after)):
        return None, "baseline files not both present yet — run the isolation capture first"
    b = open(before, encoding="utf-8").read()
    a = open(after, encoding="utf-8").read()
    return (b == a), None

def main():
    print("=== Gate 33: Prototype contamination scan ===")
    findings = scan_prototype_contamination()
    if findings:
        print(f"[FAIL] {len(findings)} prototype-contamination pattern(s) found:")
        for path, line, label, match in findings:
            print(f"  {os.path.relpath(path, V2_ROOT)}:{line}  {label}  ({match!r})")
    else:
        print("[PASS] 0 prototype-contamination patterns found.")

    print()
    print("=== Gate 34: V1 contamination (baseline diff) ===")
    identical, note = check_v1_baseline_diff()
    if identical is None:
        print(f"[SKIP] {note}")
    elif identical:
        print("[PASS] before/after V1 worktree baselines are byte-identical.")
    else:
        print("[FAIL] before/after V1 worktree baselines DIFFER — investigate before declaring green.")

    print()
    ok = (not findings) and (identical is not False)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
