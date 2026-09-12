#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GL-1J -- exact-hostname authorization contract for the GitHub Pages
homologation host.

Behavioral proof, not implementation-text matching: for each candidate
hostname, actually navigates the browser to that hostname (Playwright's
route interception answers the request locally, before/instead of a real
DNS lookup, so no real network egress or DNS control is needed) and reads
window.NX_ENVIRONMENT after DOMContentLoaded -- the same object
environment-guard.js itself publishes -- rather than asserting anything
about index.html's own source text.

Proves, against the real built artifact:
  A. the exact proven hostname (luisgamadio-spec.github.io) is authorized;
  B. a different *.github.io hostname is NOT authorized (no wildcard);
  C. an unrelated hostname is NOT authorized;
  D/localhost/127.0.0.1: local dev remains allowed, unaffected;
  E. the hosted config is visible to the guard's authoritative check,
     i.e. loaded before DOMContentLoaded fires (host config before guard);
  F/G. the hosted config that loads never activates Intelligence
     (mode stays 'fixture') and carries no OPENAI_API_KEY-shaped field.

0 real network calls beyond the intercepted local artifact. 0 credentials.
"""
import io
import sys
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_ROOT = os.environ.get("GL1J_ARTIFACT_ROOT")
if not ARTIFACT_ROOT:
    print("SKIP: set GL1J_ARTIFACT_ROOT to the built Pages artifact directory")
    sys.exit(0)

results = []


def check(label, cond):
    results.append((label, bool(cond)))


CASES = [
    ("luisgamadio-spec.github.io", True, "AUTHORIZED_PRODUCTION"),
    ("someoneelse.github.io", False, "UNKNOWN_HOST"),
    ("random-imposter-host.com", False, "UNKNOWN_HOST"),
    ("localhost", True, "LOCAL_DEV"),
    ("127.0.0.1", True, "LOCAL_DEV"),
]


def serve_local(route, artifact_root):
    url = route.request.url
    path = url.split("://", 1)[1].split("/", 1)[1] if "/" in url.split("://", 1)[1] else ""
    if path == "" or path.endswith("/"):
        path += "index.html"
    local_path = os.path.join(artifact_root, path)
    if os.path.isfile(local_path):
        with open(local_path, "rb") as f:
            body = f.read()
        ctype = "text/html"
        if path.endswith(".js"):
            ctype = "application/javascript"
        elif path.endswith(".css"):
            ctype = "text/css"
        elif path.endswith(".json"):
            ctype = "application/json"
        elif path.endswith(".png"):
            ctype = "image/png"
        elif path.endswith(".woff2"):
            ctype = "font/woff2"
        route.fulfill(status=200, body=body, content_type=ctype)
    else:
        route.abort()


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for hostname, expect_allowed, expect_name in CASES:
            page = browser.new_page()
            page.route("**/supabase-js@*", lambda route: route.abort())
            page.route("**/*", lambda route: serve_local(route, ARTIFACT_ROOT))
            try:
                page.goto(f"http://{hostname}/index.html", timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(400)
                env = page.evaluate("window.NX_ENVIRONMENT")
            except Exception as e:
                env = {"name": "NAVIGATION_ERROR", "allowed": False, "_error": str(e)}
            check(f"{hostname}: NX_ENVIRONMENT.name == {expect_name}", env and env.get("name") == expect_name)
            check(f"{hostname}: NX_ENVIRONMENT.allowed == {expect_allowed}", env and env.get("allowed") == expect_allowed)

            if hostname == "luisgamadio-spec.github.io":
                cfg = page.evaluate("window.NX_INTELLIGENCE_CONFIG")
                check("hosted config: mode stays 'fixture' (Intelligence inert)", cfg and cfg.get("mode") == "fixture")
                check("hosted config: no OPENAI_API_KEY-shaped field present", cfg and "OPENAI_API_KEY" not in str(cfg) and "openaiApiKey" not in cfg)
                check("hosted config: authorizedHostnames contains exact hostname only", cfg and cfg.get("authorizedHostnames") == ["luisgamadio-spec.github.io"])

            page.close()
        browser.close()

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== GL-1J Environment Guard Hostname Contract: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
