#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GL-1J, extended GL-ENV-AUTH-WRITE-BOUNDARY -- exact-hostname
authorization contract for the GitHub Pages homologation host AND the
Human-designated future production hostname.

Behavioral proof, not implementation-text matching: for each candidate
hostname, actually navigates the browser to that hostname (Playwright's
route interception answers the request locally, before/instead of a real
DNS lookup, so no real network egress or DNS control is needed) and reads
window.NX_ENVIRONMENT after DOMContentLoaded -- the same object
environment-guard.js itself publishes -- rather than asserting anything
about index.html's own source text.

Proves, against the real built artifact:
  A. the exact proven GitHub Pages hostname (luisgamadio-spec.github.io)
     classifies as AUTHORIZED_HOMOLOGATION, never AUTHORIZED_PRODUCTION
     (GL-ENV-AUTH-WRITE-BOUNDARY's own R1/R2 fix);
  B. the Human-designated future production hostname
     (brabus.blistiq.com.br) classifies as AUTHORIZED_PRODUCTION when its
     prepared config is present in the artifact -- PREPARED, not
     ACTIVATED: this proves the classification logic only, never implies
     V2 is actually deployed there;
  C. a different *.github.io hostname is NOT authorized (no wildcard);
  D. an unrelated hostname is NOT authorized;
  E/localhost/127.0.0.1: local dev remains allowed, unaffected;
  F. the homolog config is visible to the guard's authoritative check,
     i.e. loaded before DOMContentLoaded fires (host config before guard),
     carries no OPENAI_API_KEY-shaped field, uses
     authorizedHomologationHostnames (never authorizedHostnames), and
     points textEndpoint at portal-ai-homolog;
  G. the production config uses authorizedHostnames (never
     authorizedHomologationHostnames) and points textEndpoint at
     portal-ai (never portal-ai-homolog).

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
    ("luisgamadio-spec.github.io", True, "AUTHORIZED_HOMOLOGATION"),
    ("brabus.blistiq.com.br", True, "AUTHORIZED_PRODUCTION"),
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
                # GL-ENV-AUTH-WRITE-BOUNDARY -- corrected alongside this
                # wave's own hostname-classification changes: the prior
                # "mode stays 'fixture'" assertion was already stale
                # before this wave (the real committed homolog-flavored
                # config has shipped mode:'real_text' since GL-1J/SEC-1C.3
                # activated Intelligence TEXT for this host; this test
                # simply never ran in an environment with
                # GL1J_ARTIFACT_ROOT set, so the drift went unnoticed).
                # Corrected here to match the real, current, live-verified
                # content rather than left further out of date while this
                # exact block was already being touched for the
                # authorizedHomologationHostnames rename below.
                check("homolog config: mode is 'real_text' (Intelligence TEXT active, homolog)", cfg and cfg.get("mode") == "real_text")
                check("homolog config: no OPENAI_API_KEY-shaped field present", cfg and "OPENAI_API_KEY" not in str(cfg) and "openaiApiKey" not in cfg)
                check("homolog config: authorizedHomologationHostnames contains exact hostname only", cfg and cfg.get("authorizedHomologationHostnames") == ["luisgamadio-spec.github.io"])
                check("homolog config: authorizedHostnames (production) is NOT set here", cfg and not cfg.get("authorizedHostnames"))
                check("homolog config: textEndpoint uses portal-ai-homolog", cfg and "/portal-ai-homolog" in (cfg.get("textEndpoint") or ""))

            if hostname == "brabus.blistiq.com.br":
                cfg = page.evaluate("window.NX_INTELLIGENCE_CONFIG")
                check("production config: authorizedHostnames contains exact hostname only", cfg and cfg.get("authorizedHostnames") == ["brabus.blistiq.com.br"])
                check("production config: authorizedHomologationHostnames (homolog) is NOT set here", cfg and not cfg.get("authorizedHomologationHostnames"))
                check("production config: textEndpoint uses portal-ai (never portal-ai-homolog)", cfg and (cfg.get("textEndpoint") or "").endswith("/portal-ai"))
                check("production config: voiceRealtimeEndpoint is null (no production portal-realtime function could be proven to exist -- not invented)", cfg and cfg.get("voiceRealtimeEndpoint") is None)

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
