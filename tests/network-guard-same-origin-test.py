#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GL-1K -- network-guard same-origin false-positive regression.

Behavioral proof against the real built artifact, navigating the browser
to each candidate hosting origin (Playwright route interception answers
every request locally, no real DNS/network egress needed) and calling
window.NX_NETWORK_GUARD.isRealBackendUrl(...) directly -- the guard's
own real, live decision function -- rather than asserting anything about
source text.

Proves:
  1. relative same-origin JSON is NOT a false-positive backend call;
  2. a same-origin ABSOLUTE URL is NOT a false-positive backend call;
  3. Supabase host STILL classifies as real-backend (protection intact);
  4. an unrelated external host retains its established (non-)treatment;
  5. api.openai.com STILL classifies as real-backend (browser OpenAI
     access stays flagged/prohibited by this guard's own contract);
  6. the app's own GitHub Pages hosting origin is not classified as a
     real backend merely because it happens to host the frontend --
     checked from two different possible hosting origins, proving this
     is a general same-origin rule, not a special case for one host.

0 real network calls beyond the intercepted local artifact. 0 credentials.
"""
import io
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ARTIFACT_ROOT = os.environ.get("GL1K_ARTIFACT_ROOT")
if not ARTIFACT_ROOT:
    print("SKIP: set GL1K_ARTIFACT_ROOT to the built Pages artifact directory")
    sys.exit(0)

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def serve_local(route, artifact_root):
    url = route.request.url
    path = url.split("://", 1)[1].split("/", 1)[1] if "/" in url.split("://", 1)[1] else ""
    if path == "" or path.endswith("/"):
        path += "index.html"
    local_path = os.path.join(artifact_root, path)
    if os.path.isfile(local_path):
        with open(local_path, "rb") as f:
            body = f.read()
        ctype = "application/javascript" if path.endswith(".js") else "text/html"
        route.fulfill(status=200, body=body, content_type=ctype)
    else:
        route.abort()


# (hosting_origin, url_to_test, expect_real_backend, label)
CASES = [
    ("luisgamadio-spec.github.io", "config/module-registry.json", False, "relative same-origin JSON (GL-1J hosting origin)"),
    ("luisgamadio-spec.github.io", "http://luisgamadio-spec.github.io/config/landing-groups.json", False, "same-origin ABSOLUTE URL (GL-1J hosting origin)"),
    ("luisgamadio-spec.github.io", "https://yacqlelpzchcotgngwbh.supabase.co/rest/v1/rpc/x", True, "Supabase host (protection intact)"),
    ("luisgamadio-spec.github.io", "https://api.openai.com/v1/x", True, "api.openai.com (browser OpenAI stays flagged)"),
    ("luisgamadio-spec.github.io", "https://example-unrelated-host.com/x", False, "unrelated external host (unchanged: not in allowlist)"),
    ("someone-elses-pages-clone.github.io", "config/module-registry.json", False, "relative same-origin JSON (a DIFFERENT hosting origin -- proves general rule, not a hardcoded special case)"),
]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for hosting_origin, target_url, expect_real_backend, label in CASES:
            page = browser.new_page()
            page.route("**/*", lambda route: serve_local(route, ARTIFACT_ROOT))
            page.goto(f"http://{hosting_origin}/index.html", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(200)
            is_real = page.evaluate("(u) => window.NX_NETWORK_GUARD.isRealBackendUrl(u)", target_url)
            check(f"{label}: isRealBackendUrl == {expect_real_backend}", is_real == expect_real_backend)
            page.close()
        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== GL-1K Network Guard Same-Origin Contract: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
