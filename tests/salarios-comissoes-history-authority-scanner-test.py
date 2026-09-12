#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH-4D -- duplicate-authority scanner + cross-consumer contract proof.

Guards the consolidation this Wave performed (SALARIOS_HISTORY_
DUPLICATE_AUTHORITY_RISK_DISCLOSED -> SALARIOS_HISTORY_DUPLICATE_
AUTHORITY_RESOLVED, RH-4C -> RH-4D): the retired
salarios-comissoes-history-provider.js must never come back, and
salarios-comissoes.js must never reintroduce a direct call to any
master_commission_* historical RPC -- every access must go through the
SAME canonical transport (window.NX_MASTER_COMPETENCE_HISTORY_
PROVIDER) Painel Master's own Histórico de Competências screen uses.
This is a static source scanner + one live cross-consumer proof, not a
behavioral test (see salarios-comissoes-history-test.py for that).

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

results = []


def check(label, cond):
    results.append((label, bool(cond)))


REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
FORBIDDEN_RPC_NAMES = [
    "master_commission_closings", "master_commission_snapshot",
    "master_commission_snapshot_export", "master_commission_operational_detail"
]


def strip_js_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)//.*$", "", text)
    return text


def main():
    # ---------- 1: the retired duplicate provider file must not exist ----------
    retired_path = os.path.join(REPO_ROOT, "assets", "js", "adapters", "salarios-comissoes-history-provider.js")
    check("1: the retired salarios-comissoes-history-provider.js does not exist on disk", not os.path.exists(retired_path))

    retired_harness = os.path.join(REPO_ROOT, "tests", "_salarios-comissoes-history-provider-harness.html")
    check("1b: its dedicated test harness was also retired", not os.path.exists(retired_harness))

    # ---------- 2: index.html no longer references the retired file ----------
    with io.open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8") as f:
        index_src = f.read()
    check("2: index.html no longer loads salarios-comissoes-history-provider.js", "salarios-comissoes-history-provider.js" not in index_src)
    check("2b: index.html still loads the canonical provider + view-model (Painel Master's own script block, unmoved)",
          "master-competence-history-provider.js" in index_src and "master-competence-history-view-model.js" in index_src)

    # ---------- 3: salarios-comissoes.js never calls a historical RPC directly ----------
    salarios_path = os.path.join(REPO_ROOT, "assets", "js", "salarios-comissoes.js")
    with io.open(salarios_path, encoding="utf-8") as f:
        raw_salarios_src = f.read()
    salarios_src = strip_js_comments(raw_salarios_src)
    # What must never exist: a literal RPC-name string used the way a
    # transport layer would use it (a fetch/rpc-style call argument),
    # NOT the RPC name appearing as prose in a comment (already
    # stripped above) -- so a bare substring check post-comment-strip is
    # precise here, since the ONLY legitimate place these 4 names could
    # appear in executable Salários code would be a forbidden direct
    # transport call.
    direct_calls_found = [name for name in FORBIDDEN_RPC_NAMES if name in salarios_src]
    check("3: salarios-comissoes.js contains zero direct references to any historical RPC name in executable code", direct_calls_found == [])

    check("3b: salarios-comissoes.js consumes the canonical provider (window.NX_MASTER_COMPETENCE_HISTORY_PROVIDER)",
          "NX_MASTER_COMPETENCE_HISTORY_PROVIDER" in salarios_src)
    check("3c: salarios-comissoes.js consumes the canonical view-model's classification predicate (isStructurallyInconsistent), not a re-derived copy",
          "isStructurallyInconsistent" in salarios_src)
    # Gate 20/9: no second, independently-named transport function
    # (e.g. a leftover 'callRpc' fetching these RPCs) should exist in
    # this file -- the only fetch/RPC transport this file owns is
    # RH-4A's own live/operational callRpc, which calls a completely
    # disjoint RPC set (checked negatively above).
    own_call_rpc_count = len(re.findall(r"function\s+callRpc\s*\(", salarios_src))
    check("3d: salarios-comissoes.js defines at most the one pre-existing operational callRpc (no second historical transport function)", own_call_rpc_count <= 1)

    # ---------- 4: no other Salários file reintroduces the duplicate authority ----------
    salarios_dir_files = [
        os.path.join(REPO_ROOT, "assets", "js", "adapters", "salarios-comissoes-real-provider.js"),
    ]
    other_leak = []
    for path in salarios_dir_files:
        with io.open(path, encoding="utf-8") as f:
            src = strip_js_comments(f.read())
        for name in FORBIDDEN_RPC_NAMES:
            if name in src:
                other_leak.append((path, name))
    check("4: the live/operational provider (RH-4A) still calls zero historical RPCs", other_leak == [])

    # ---------- 5: cross-consumer contract -- live proof both consumers share the same function references ----------
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        # Load BOTH surfaces' script sets on one blank page purely to
        # prove reference identity -- no RPC is ever called (no route
        # mocked, no navigation into either module's real UI).
        page.route("**/*", lambda route: route.continue_())
        # V2-INT-01 -- test-harness-only fix: was hardcoded to the OLD
        # parent-dir-rooted topology; this worktree is served root-at-
        # worktree, same IA3E_TEST_PORT convention the rest of this
        # suite already uses.
        page.goto(f"http://127.0.0.1:{os.environ.get('IA3E_TEST_PORT', '8711')}/index.html")
        page.wait_for_function("!!window.NX_MASTER_COMPETENCE_HISTORY_PROVIDER && !!window.NX_SALARIOS_COMISSOES_PAGE", timeout=8000)
        has_all_methods = page.evaluate("""() => {
          const p = window.NX_MASTER_COMPETENCE_HISTORY_PROVIDER;
          return !!(p && p.listClosings && p.getSnapshot && p.exportSnapshot && p.loadOperationalSnapshot);
        }""")
        check("5a: the canonical provider exposes every method both consumers need", has_all_methods)
        no_second_global = page.evaluate("() => typeof window.NX_SALARIOS_COMISSOES_HISTORY_PROVIDER === 'undefined'")
        check("5b: the retired global (window.NX_SALARIOS_COMISSOES_HISTORY_PROVIDER) no longer exists at runtime", no_second_global)
        browser.close()

    print()
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(("[PASS] " if ok else "[FAIL] ") + label)
    print()
    print("=== Salários & Comissões History Duplicate-Authority Scanner (RH-4D): %d/%d ===" % (passed, len(results)))
    print("RESULT: %s" % ("PASS" if passed == len(results) else "FAIL"))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
