#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3J.4E.1 -- stage_ms end-to-end delivery proof.

IA-3J.4E added a `timings` (per-stage) breakdown to portal-ai-homolog's
`_homolog_edge_timing.stage_ms` (v50+), on the theory that
brabus-intelligence.adapter.js's `buildDevTiming()` + intelligence-
panel.js's `logDevTiming()` would carry it through to the browser
console's `[bai-timing]` line automatically -- based on `logDevTiming`'s
own generic `for (var k in devTiming) out[k] = devTiming[k]` copy.

A real Human capture (correlation_id 94fbedc7-6fe5-48fc-aed8-ad4228f1408e,
v50 already deployed and confirmed byte-identical to the local source)
proved `stage_ms` was still absent from the final object. Root cause:
`buildDevTiming()` (the PRODUCER of `_devTiming`, not `logDevTiming`,
its consumer) never read the real, generic `_homolog_edge_timing`
object -- it hand-copied 6 specific known fields off `edge` and simply
never listed `stage_ms` among them. This Wave added exactly one line
inside that existing `if (edge && ...)` block: `if (edge.stage_ms) t.stage_ms = edge.stage_ms;`.

The pre-existing dev-timing test in intelligence-panel-test.py (its own
"IA-3G.5A: dev-timing diagnostic safety" section) stubs
`NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText` itself with a HAND-BUILT
`_devTiming` object -- this proves logDevTiming's CONSUMER side only
and never exercises `buildDevTiming()` at all, which is exactly why
this gap went undetected. This test instead stubs `window.fetch` (one
level lower, the network boundary sendRealText itself calls), so the
REAL sendRealText -> REAL buildDevTiming -> REAL logDevTiming chain
runs unmodified, end to end, on a representative response shaped like
portal-ai-homolog v50's actual success payload.

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
    """Same helper as intelligence-panel-test.py's own set_profile --
    monkeypatches NX_AUTH_CORE.getState/getContext and asks the panel to
    re-run its real visibility decision."""
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


# A representative real success payload, shaped exactly like portal-ai-
# homolog v50's actual response.reply/blocks/scenario_reset/request_id/
# _homolog_debug/_homolog_edge_timing contract (confirmed against the
# deployed source this Wave), with `stage_ms` populated the way a real
# 2-tool-call financing recommendation would produce it.
FAKE_RESPONSE_BODY = {
    "reply": "resposta de teste",
    "blocks": None,
    "request_id": "r-stagems-1",
    "scenario_reset": False,
    "_homolog_debug": {"tools_used": ["simular_financiamento_balao_otimizado_veiculos_novos"], "tool_call_count": 1, "calls": []},
    "_homolog_edge_timing": {
        "handler_entry_epoch_ms": 1000,
        "response_ready_epoch_ms": 1500,
        "instance_id": "inst-stagems-test",
        "instance_age_ms": 42,
        "latency_ms": 500,
        "stage_ms": {
            "auth_ms": 80,
            "master_gate_ms": 60,
            "config_scope_ms": 120,
            "openai_pass_ms": [210, 30],
            "tool_dispatch_ms": [{"name": "simular_financiamento_balao_otimizado_veiculos_novos", "ms": 15}]
        }
    }
}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")

        # Capture console.log('[bai-timing]', out) calls page-side (not
        # via the `console` Playwright event, which truncates/summarizes
        # a large object argument in Chromium's own console formatting)
        # -- same robust pattern intelligence-panel-test.py's own
        # dev-timing test uses.
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

        # Stub ONLY the network boundary (window.fetch) and the auth/
        # surface-gate dependencies sendRealText itself needs -- NOT
        # sendRealText, NOT buildDevTiming, NOT logDevTiming. Everything
        # from handleSend() down through applyResult()/logDevTiming() is
        # the real, unmodified code.
        page.evaluate(
            """([body]) => {
                window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
                window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
                window.NX_INTELLIGENCE_CONFIG.textEndpoint = 'https://fake.local/portal-ai-homolog';
                window.NX_INTELLIGENCE_CONFIG.supabasePublishableKey = 'fake-key';
                window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
                window.NX_MASTER_CONFIG_PROVIDER = {
                    readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }])
                };
                window.__origFetch = window.fetch;
                window.fetch = function (url) {
                    return Promise.resolve({
                        ok: true,
                        status: 200,
                        json: () => Promise.resolve(body)
                    });
                };
            }""",
            [FAKE_RESPONSE_BODY],
        )

        page.click("#baiLauncherBtn")
        page.wait_for_timeout(150)
        page.fill("#baiPanelInput", "teste stage_ms end-to-end")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(400)

        timing_calls = page.evaluate("window.__baiTimingCalls")
        check("[bai-timing] emitted exactly once", isinstance(timing_calls, list) and len(timing_calls) == 1, timing_calls)

        t = timing_calls[0] if timing_calls else {}
        line = json.dumps(t)

        check("stage_ms is present as an own property of the final [bai-timing] object", "stage_ms" in t, t)
        stage = t.get("stage_ms") or {}
        check("stage_ms.auth_ms == 80 (survived the real buildDevTiming/logDevTiming path unchanged)", stage.get("auth_ms") == 80, stage)
        check("stage_ms.master_gate_ms == 60", stage.get("master_gate_ms") == 60, stage)
        check("stage_ms.config_scope_ms == 120", stage.get("config_scope_ms") == 120, stage)
        check("stage_ms.openai_pass_ms is an array", isinstance(stage.get("openai_pass_ms"), list), stage)
        check("stage_ms.openai_pass_ms == [210, 30]", stage.get("openai_pass_ms") == [210, 30], stage)
        check("stage_ms.tool_dispatch_ms is an array", isinstance(stage.get("tool_dispatch_ms"), list), stage)
        check(
            "stage_ms.tool_dispatch_ms entries carry only name/ms",
            isinstance(stage.get("tool_dispatch_ms"), list)
            and len(stage["tool_dispatch_ms"]) == 1
            and set(stage["tool_dispatch_ms"][0].keys()) == {"name", "ms"},
            stage,
        )

        # Pre-existing top-level fields must still be present alongside
        # stage_ms -- this is an additive fix, nothing was removed.
        check("edge_instance_id still present (pre-existing field unaffected)", t.get("edge_instance_id") == "inst-stagems-test", t)
        check("edge_latency_ms still present (pre-existing field unaffected)", t.get("edge_latency_ms") == 500, t)
        check("render_ms/total_ui_ms still computed by logDevTiming itself", isinstance(t.get("render_ms"), (int, float)), t)

        # Security: no prompt/reply content, no tool args/results beyond
        # name, in the final logged object.
        check("no prompt text leaked into [bai-timing]", "teste stage_ms end-to-end" not in line, line)
        check("no reply text leaked into [bai-timing]", "resposta de teste" not in line, line)
        check("no tool arguments/results leaked (only name+ms per entry)", '"args"' not in line and '"result"' not in line and '"output"' not in line, line)

        page.evaluate("window.fetch = window.__origFetch;")
        page.close()
        browser.close()

    n_pass = sum(1 for _, ok in results if ok)
    n_fail = sum(1 for _, ok in results if not ok)
    print(f"\n=== stage_ms End-to-End Delivery Tests (IA-3J.4E.1): {n_pass}/{len(results)} ===")
    print("RESULT: " + ("PASS" if n_fail == 0 else "FAIL"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
