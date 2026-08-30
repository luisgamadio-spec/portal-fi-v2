#!/usr/bin/env python3
"""
Gate 8/9 — token authority sync check.

V2 does NOT retype any hex value or token name by hand anywhere. The
shell (index.html) links design-system-2/tokens.css directly, by
relative path, exactly the same way the Human Approved Executable
Landing Reference itself does
(design-system-2.1/references/baselines/module-landing-approved/index.html
links ../../../../design-system-2/tokens.css). This script exists only
to catch the day that file and design-system-2.1's normative JSON
(the documentation-level authority) drift apart — it does not generate
or duplicate anything.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
LAB_ROOT = os.path.dirname(V2_ROOT)

TOKENS_CSS = os.path.join(LAB_ROOT, "design-system-2", "tokens.css")
NORMATIVE_JSON = os.path.join(LAB_ROOT, "design-system-2.1", "design-system.normative.json")

# coreIdentity.tokens key -> the CSS custom property (or literal, for
# keyword-only fields) that must carry the same value in tokens.css.
CHECKS = [
    ("canvas", "--p-black-1"),
    ("surface1", "--p-black-2"),
    ("surface2", "--p-black-3"),
    ("accentPrimary", "--p-red-1"),
    ("brandRed", "--p-red-2"),
]

def main():
    errors = []
    if not os.path.isfile(TOKENS_CSS):
        print(f"[FAIL] token authority file not found: {TOKENS_CSS}")
        sys.exit(1)
    if not os.path.isfile(NORMATIVE_JSON):
        print(f"[FAIL] normative JSON not found: {NORMATIVE_JSON}")
        sys.exit(1)

    css = open(TOKENS_CSS, encoding="utf-8").read()
    normative = json.load(open(NORMATIVE_JSON, encoding="utf-8"))
    core = normative["coreIdentity"]["tokens"]

    for json_key, css_var in CHECKS:
        expected_hex = core[json_key].lower()
        m = re.search(re.escape(css_var) + r"\s*:\s*(#[0-9a-fA-F]{6})", css)
        if not m:
            errors.append(f"{css_var} not found in tokens.css")
            continue
        actual_hex = m.group(1).lower()
        ok = actual_hex == expected_hex
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {json_key} ({css_var}): normative={expected_hex} tokens.css={actual_hex}")
        if not ok:
            errors.append(f"{css_var} mismatch: normative={expected_hex} tokens.css={actual_hex}")

    ui = normative["coreIdentity"]["typography"]["ui"]
    mono = normative["coreIdentity"]["typography"]["mono"]
    ok_ui = f"--font-ui: '{ui}'" in css
    ok_mono = f"--font-mono: '{mono}'" in css
    print(f"[{'PASS' if ok_ui else 'FAIL'}] typography.ui ({ui}) present in --font-ui")
    print(f"[{'PASS' if ok_mono else 'FAIL'}] typography.mono ({mono}) present in --font-mono")
    if not ok_ui:
        errors.append("--font-ui does not reference " + ui)
    if not ok_mono:
        errors.append("--font-mono does not reference " + mono)

    print()
    if errors:
        print(f"RESULT: FAIL ({len(errors)} divergence(s) between design-system-2.1's")
        print("normative JSON and the executable tokens.css authority — this is a")
        print("STOP condition per the Skill's Authority Order, not something to")
        print("silently pick a winner for.")
        sys.exit(1)
    print("RESULT: PASS — 0 divergence. V2's token runtime (a direct link to")
    print("tokens.css, not a copy) is consistent with the normative authority.")
    sys.exit(0)

if __name__ == "__main__":
    main()
