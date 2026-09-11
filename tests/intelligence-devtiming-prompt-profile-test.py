#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3J.4J.1 -- prompt_profile/prompt_chars end-to-end delivery proof.

IA-3J.4I added `prompt_profile` ("finance"|"full") and `prompt_chars`
(a plain character count) to portal-ai-homolog's `_homolog_edge_timing`
as siblings of `stage_ms` (v52+). IA-3J.4J found, BEFORE spending a
real Human request on it, that `buildDevTiming()` -- the exact same
hand-listed-copy function that once dropped `stage_ms` (IA-3J.4E.1) --
never listed these two new fields either, so they would have been
silently lost the same way. This Wave added exactly two lines inside
the same existing `if (edge && ...)` block, right after the `stage_ms`
line:
  if (typeof edge.prompt_profile === 'string' && edge.prompt_profile.length > 0) t.prompt_profile = edge.prompt_profile;
  if (typeof edge.prompt_chars === 'number') t.prompt_chars = edge.prompt_chars;

Same methodology as intelligence-devtiming-stage-ms-test.py: stubs
ONLY `window.fetch` (the network boundary sendRealText itself calls),
so the REAL sendRealText -> REAL buildDevTiming -> REAL logDevTiming
chain runs unmodified, end to end, for several representative
responses (finance profile, full profile, and deliberately malformed/
absent cases) sent as separate turns in one conversation.

Requires: `python -m http.server 8711` running from this worktree's
own root (same server/port intelligence-panel-test.py uses).
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def set_profile(page, state, is_master=None, perfil=None):
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def base_edge_timing(**overrides):
    edge = {
        "handler_entry_epoch_ms": 1000,
        "response_ready_epoch_ms": 1500,
        "instance_id": "inst-promptprofile-test",
        "instance_age_ms": 42,
        "latency_ms": 500,
    }
    edge.update(overrides)
    return edge


# Case 1: canonical finance profile, full stage_ms breakdown (the
# shape a real Balão+Linear recommendation produces).
BODY_FINANCE = {
    "reply": "resposta de teste finance", "blocks": None, "request_id": "r-finance-1", "scenario_reset": False,
    "_homolog_debug": {"tools_used": ["simular_financiamento", "simular_financiamento"], "tool_call_count": 2, "calls": []},
    "_homolog_edge_timing": base_edge_timing(
        prompt_profile="finance",
        prompt_chars=44431,
        stage_ms={
            "auth_ms": 100, "master_gate_ms": 200, "config_scope_ms": 300,
            "openai_pass_ms": [4000, 5000],
            "tool_dispatch_ms": [
                {"name": "simular_financiamento", "ms": 150},
                {"name": "simular_financiamento", "ms": 160},
            ],
            "tools_sent_count": 2,
        },
    ),
}

# Case 2: full profile -- proves forwarding is profile-agnostic, not
# hardcoded to "finance"/44431.
BODY_FULL = {
    "reply": "resposta de teste full", "blocks": None, "request_id": "r-full-1", "scenario_reset": False,
    "_homolog_debug": {"tools_used": ["consultar_score_vendedores"], "tool_call_count": 1, "calls": []},
    "_homolog_edge_timing": base_edge_timing(
        prompt_profile="full",
        prompt_chars=104609,
        stage_ms={
            "auth_ms": 90, "master_gate_ms": 180, "config_scope_ms": 270,
            "openai_pass_ms": [3000],
            "tool_dispatch_ms": [{"name": "consultar_score_vendedores", "ms": 120}],
            "tools_sent_count": 12,
        },
    ),
}

# Case 3: negative -- prompt_profile/prompt_chars absent entirely
# (e.g. an older deployed version, or a response shape that never set
# them) -- must not be fabricated.
BODY_MISSING = {
    "reply": "resposta de teste missing", "blocks": None, "request_id": "r-missing-1", "scenario_reset": False,
    "_homolog_debug": {"tools_used": [], "tool_call_count": 0, "calls": []},
    "_homolog_edge_timing": base_edge_timing(stage_ms={"auth_ms": 1, "master_gate_ms": 1, "config_scope_ms": 1, "openai_pass_ms": [1], "tool_dispatch_ms": [], "tools_sent_count": 12}),
}

# Case 4: negative -- prompt_chars sent as a STRING, never coerced/
# forwarded as if it were valid numeric telemetry.
BODY_STRING_CHARS = {
    "reply": "resposta de teste string-chars", "blocks": None, "request_id": "r-strchars-1", "scenario_reset": False,
    "_homolog_debug": {"tools_used": [], "tool_call_count": 0, "calls": []},
    "_homolog_edge_timing": base_edge_timing(
        prompt_profile="finance",
        prompt_chars="44431",
        stage_ms={"auth_ms": 1, "master_gate_ms": 1, "config_scope_ms": 1, "openai_pass_ms": [1], "tool_dispatch_ms": [], "tools_sent_count": 2},
    ),
}

CASES = [BODY_FINANCE, BODY_FULL, BODY_MISSING, BODY_STRING_CHARS]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")

        page.evaluate(
            """() => {
                window.__baiTimingCalls = [];
                var origLog = console.log.bind(console);
                console.log = function () {
                    var args = Array.prototype.slice.call(arguments);
                    if (args[0] === '[bai-timing]') window.__baiTimingCalls.push(args[1]);
                    return origLog.apply(console, args);
                };
            }"""
        )

        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
                window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
                window.NX_INTELLIGENCE_CONFIG.textEndpoint = 'https://fake.local/portal-ai-homolog';
                window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = 'fake-key';
                window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
                window.NX_MASTER_CONFIG_PROVIDER = {
                    readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }])
                };
                window.__origFetch = window.fetch;
                window.__baiNextBody = null;
                window.fetch = function (url) {
                    var body = window.__baiNextBody;
                    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
                };
            }"""
        )

        page.click("#baiLauncherBtn")
        page.wait_for_timeout(150)

        for i, body in enumerate(CASES):
            page.evaluate("(b) => { window.__baiNextBody = b; }", body)
            page.fill("#baiPanelInput", f"teste prompt_profile caso {i}")
            page.click("#baiPanelSendBtn")
            page.wait_for_timeout(350)

        timing_calls = page.evaluate("window.__baiTimingCalls")
        check(f"[bai-timing] emitted exactly {len(CASES)} times (once per turn)", isinstance(timing_calls, list) and len(timing_calls) == len(CASES), timing_calls)

        def line_of(t):
            return json.dumps(t)

        # ---------- Case 1: finance profile, full stage_ms ----------
        t = timing_calls[0] if len(timing_calls) > 0 else {}
        check("finance case: prompt_profile === 'finance'", t.get("prompt_profile") == "finance", t)
        check("finance case: prompt_chars === 44431", t.get("prompt_chars") == 44431, t)
        stage = t.get("stage_ms") or {}
        check("finance case: stage_ms.tools_sent_count === 2", stage.get("tools_sent_count") == 2, stage)
        check("finance case: stage_ms.openai_pass_ms[0] === 4000", isinstance(stage.get("openai_pass_ms"), list) and stage["openai_pass_ms"][0] == 4000, stage)
        check("finance case: stage_ms.openai_pass_ms[1] === 5000", isinstance(stage.get("openai_pass_ms"), list) and len(stage["openai_pass_ms"]) > 1 and stage["openai_pass_ms"][1] == 5000, stage)
        check(
            "finance case: stage_ms.tool_dispatch_ms has 2 simular_financiamento entries",
            isinstance(stage.get("tool_dispatch_ms"), list)
            and len(stage["tool_dispatch_ms"]) == 2
            and all(e.get("name") == "simular_financiamento" for e in stage["tool_dispatch_ms"]),
            stage,
        )
        check("finance case: no prompt/reply text leaked", "teste prompt_profile caso 0" not in line_of(t) and "resposta de teste finance" not in line_of(t), line_of(t))

        # ---------- Case 2: full profile -- profile-agnostic proof ----------
        t2 = timing_calls[1] if len(timing_calls) > 1 else {}
        check("full case: prompt_profile === 'full' (not hardcoded to 'finance')", t2.get("prompt_profile") == "full", t2)
        check("full case: prompt_chars === 104609 (not hardcoded to 44431)", t2.get("prompt_chars") == 104609, t2)
        check("full case: stage_ms.tools_sent_count === 12", (t2.get("stage_ms") or {}).get("tools_sent_count") == 12, t2)

        # ---------- Case 3: missing fields -- never fabricated ----------
        t3 = timing_calls[2] if len(timing_calls) > 2 else {}
        check("missing case: prompt_profile is NOT present (never fabricated)", "prompt_profile" not in t3, t3)
        check("missing case: prompt_chars is NOT present (never fabricated)", "prompt_chars" not in t3, t3)
        check("missing case: stage_ms still forwarded correctly (unaffected by the absence of the other two fields)", (t3.get("stage_ms") or {}).get("tools_sent_count") == 12, t3)

        # ---------- Case 4: prompt_chars as a string -- never coerced ----------
        t4 = timing_calls[3] if len(timing_calls) > 3 else {}
        check("string-chars case: prompt_profile still forwarded (it was a valid non-empty string)", t4.get("prompt_profile") == "finance", t4)
        check("string-chars case: prompt_chars is NOT forwarded (string '44431' must never be treated as valid numeric telemetry)", "prompt_chars" not in t4, t4)

        # ---------- regression: pre-existing fields/behavior unaffected ----------
        check("regression: edge_instance_id still present on case 1", t.get("edge_instance_id") == "inst-promptprofile-test", t)
        check("regression: edge_latency_ms still present on case 1", t.get("edge_latency_ms") == 500, t)
        check("regression: client_round_trip_ms still computed on case 1", isinstance(t.get("client_round_trip_ms"), (int, float)), t)
        check("regression: render_ms/total_ui_ms still computed by logDevTiming itself on case 1", isinstance(t.get("render_ms"), (int, float)) and isinstance(t.get("total_ui_ms"), (int, float)), t)

        # ---------- security: no content leaked across any of the 4 captured lines ----------
        all_lines = json.dumps(timing_calls)
        check("security: no prompt content leaked across any captured [bai-timing] line", "teste prompt_profile caso" not in all_lines)
        check("security: no reply content leaked across any captured [bai-timing] line", not any(s in all_lines for s in ["resposta de teste finance", "resposta de teste full", "resposta de teste missing", "resposta de teste string-chars"]))
        check("security: no tool args/results leaked (only name+ms per tool_dispatch_ms entry)", '"args"' not in all_lines and '"result"' not in all_lines and '"output"' not in all_lines)

        page.evaluate("window.fetch = window.__origFetch;")
        page.close()
        browser.close()

    n_pass = sum(1 for _, ok in results if ok)
    n_fail = sum(1 for _, ok in results if not ok)
    print(f"\n=== prompt_profile/prompt_chars End-to-End Delivery Tests (IA-3J.4J.1): {n_pass}/{len(results)} ===")
    print("RESULT: " + ("PASS" if n_fail == 0 else "FAIL"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
