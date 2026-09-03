#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-3B -- server-authoritative kill switch for Brabus F&I
Intelligence TEXT.

Drives the REAL, unmodified (as of this phase's own small, disclosed
addition) portal-ai-homolog source against the local mock Supabase,
with a DUMMY OpenAI key -- every scenario here is designed to prove
the request never reaches the OpenAI call at all, so a dummy key is
sufficient and 0 real OpenAI cost is incurred.

Starts two local subprocesses itself (mock Supabase on a scratch port,
the real Deno bootstrap on another scratch port) so this test is
fully self-contained and does not depend on, or disturb, any
human-owned 8790/8801/8080 session that may already be running.

Requires: Node.js and Deno (via `npx`) on PATH.
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
MOCK_PORT = 18790
REAL_PORT = 18801
MOCK_BASE = f"http://127.0.0.1:{MOCK_PORT}"
REAL_BASE = f"http://127.0.0.1:{REAL_PORT}/"

MASTER_TOKEN = "v2-mock-master-access-token"
NON_MASTER_TOKEN = "v2-mock-non-master-access-token"
ORIGIN = "http://127.0.0.1:8080"

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def post(path_or_url, body=None, headers=None, method="POST", base=None):
    url = path_or_url if path_or_url.startswith("http") else (base or MOCK_BASE) + path_or_url
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"_raw": raw}
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"_raw": raw}
        return e.code, parsed
    except Exception as e:
        return 0, {"_error": str(e)}


def mock_log():
    status, body = post("/__v2/log", method="GET")
    return body if isinstance(body, list) else []


def openai_count():
    return len([e for e in mock_log() if str(e.get("kind", "")).startswith("openai")])


def wait_healthy(url, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = post(url, method="GET")
        if status:
            return True
        time.sleep(0.5)
    return False


def real_request(message_body, token=None, extra_headers=None):
    headers = {"Content-Type": "application/json", "apikey": "local-mock-anon-key", "Origin": ORIGIN}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    return post(REAL_BASE, body=message_body, headers=headers)


def start_mock(ia_texto_env):
    env = dict(os.environ)
    if ia_texto_env is not None:
        env["V2_IA_TEXTO_HABILITADA"] = ia_texto_env
    else:
        env.pop("V2_IA_TEXTO_HABILITADA", None)
    return subprocess.Popen(
        ["node", os.path.join(HERE, "intelligence-v2-text", "mock-backend.mjs"), str(MOCK_PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def start_real():
    env = dict(os.environ)
    env.update({
        "V2_TEXT_PORT": str(REAL_PORT),
        "SUPABASE_URL": MOCK_BASE,
        "SUPABASE_ANON_KEY": "v2-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "v2-service-key",
        # Dummy key -- every scenario below is designed to be rejected
        # (kill switch, auth, MASTER, or a deliberately invalid body)
        # strictly BEFORE the OpenAI call, so this never needs to be a
        # real key. See docstring.
        "OPENAI_API_KEY": "v2-dummy-key",
    })
    deno_dir = os.path.join(HERE, "intelligence-v2-text", "deno")
    return subprocess.Popen(
        ["npx", "--yes", "deno", "run", "--allow-net", "--allow-env", "--allow-read",
         "--import-map=import_map.json", "bootstrap-text-real.ts"],
        cwd=deno_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        shell=(os.name == "nt"),
    )


def run_scenario(label, mock_env, expect_status, expect_error_substr=None, body=None, token=MASTER_TOKEN):
    mock_proc = start_mock(mock_env)
    try:
        if not wait_healthy(MOCK_BASE + "/__v2/ping"):
            check(f"{label}: mock backend started", False)
            return
        actual_body = body if body is not None else {"message": "teste", "conversation": []}
        before = openai_count()
        status, resp = real_request(actual_body, token=token)
        check(f"{label}: HTTP status == {expect_status}", status == expect_status)
        if expect_error_substr:
            check(f"{label}: error message contains '{expect_error_substr}'",
                  expect_error_substr in str(resp.get("error", "")))
        after = openai_count()
        check(f"{label}: 0 OpenAI calls (mock openai-log delta)", after == before)
    finally:
        mock_proc.terminate()
        try:
            mock_proc.wait(timeout=5)
        except Exception:
            mock_proc.kill()


def main():
    print("Starting isolated real bootstrap (dummy key, scratch port)...")
    real_proc = start_real()
    try:
        # The real process needs the mock up first to prove itself
        # ready (it doesn't check Supabase at boot, only per-request),
        # so just wait for its own listener.
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            status, _ = post(REAL_BASE, method="OPTIONS")
            if status:
                ready = True
                break
            time.sleep(1)
        check("real bootstrap process listening", ready)
        if not ready:
            print("FATAL: real bootstrap never came up; aborting.")
            sys.exit(1)

        # ---- Gate 12 invariants ----
        run_scenario("disabled config (explicit false)", "false", 503, "temporariamente indisponível")
        run_scenario("missing config (empty rows, fail-closed)", "missing", 503, "temporariamente indisponível")
        run_scenario("enabled config, no auth", "true", 401, None, token=None)
        run_scenario("enabled config, non-MASTER", "true", 403, None, token=NON_MASTER_TOKEN)
        # Enabled + MASTER + deliberately invalid body -> must reach
        # body validation (400), proving it passed the kill switch,
        # all without ever needing a real OpenAI call.
        run_scenario("enabled config, MASTER, proceeds past kill switch", "true", 400,
                     "Campo message", body={})

        # ---- Frontend contract check (no backend needed) ----
        adapter_path = os.path.join(V2_ROOT, "assets", "js", "adapters", "brabus-intelligence.adapter.js")
        adapter_src = open(adapter_path, encoding="utf-8").read()
        check("adapter: 503 mapped to a distinct, non-technical message",
              "503:" in adapter_src and "temporariamente indisponível" in adapter_src)
        check("adapter: 401/403 mappings unchanged", "401:" in adapter_src and "403:" in adapter_src)

        # ---- Tool registry invariant (source-level) ----
        authority_src_path = r"C:\Projetos\ia-reconciliation-v2-local\supabase\functions\portal-ai-homolog\index.ts"
        authority_src = open(authority_src_path, encoding="utf-8").read()
        import re
        tool_names = re.findall(r'    name: "([a-z_]+)",', authority_src)
        check("tool registry remains exactly 12", len(tool_names) == 12)
        check("iniciar_novo_cliente reset exception still present", "iniciar_novo_cliente" in tool_names)
        check("kill switch check present in source", "ia_texto_habilitada" in authority_src)
        # 2 call sites expected: the pre-existing fetchCommissionConfig()
        # usage plus the new kill-switch check -- both reuse the SAME
        # already-official RPC, no new RPC/endpoint was created.
        check("kill switch reuses the existing operational_portal_config RPC (no new endpoint)",
              authority_src.count('userClient.rpc("operational_portal_config")') == 2)

    finally:
        real_proc.terminate()
        try:
            real_proc.wait(timeout=8)
        except Exception:
            real_proc.kill()
        # npx spawns deno as a child process; terminate() on the npx
        # wrapper doesn't always reach it. Fall back to a port-based
        # kill (Windows) so no stray process survives this test.
        if os.name == "nt":
            try:
                out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5).stdout
                for line in out.splitlines():
                    if f":{REAL_PORT} " in line and "LISTENING" in line:
                        pid = line.split()[-1]
                        subprocess.run(["powershell", "-Command", f"Stop-Process -Id {pid} -Force"],
                                        capture_output=True, timeout=5)
            except Exception:
                pass

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Brabus Intelligence Kill Switch Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()