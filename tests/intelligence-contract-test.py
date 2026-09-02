#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-1 -- Brabus Intelligence adapter CONTRACT test.

Loads assets/js/adapters/brabus-intelligence.adapter.js in isolation
(tests/fixtures/_brabus-intelligence-harness.html) and exercises its
pure, DOM-independent contract functions directly. Proves the request
shape, the last-8-turns history rule, that blocks are never resent,
response normalization (including _homolog_debug stripping), all 6
block-type validation, and the format contract -- most importantly
that `percent` values are NOT multiplied by 100 (see the adapter's own
contract-note comment; this is the exact class of bug this test exists
to catch before it ships).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/tests/fixtures/_brabus-intelligence-harness.html"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        # ---------- Request contract ----------
        req = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.createRequest('oi', [])")
        results.append(("request has message+conversation fields", req.get("message") == "oi" and req.get("conversation") == []))

        long_history = page.evaluate("""
            () => {
              var conv = [];
              for (var i = 0; i < 12; i++) conv.push({role: i % 2 === 0 ? 'user' : 'assistant', content: 'turn ' + i, blocks: [{type:'metrics', items:[]}]});
              var req = window.NX_BRABUS_INTELLIGENCE_ADAPTER.createRequest('latest', conv);
              return req.conversation;
            }
        """)
        results.append(("history limited to last 8 turns", len(long_history) == 8))
        results.append(("history keeps only the LAST 8 (not the first 8)", long_history[0]["content"] == "turn 4" and long_history[-1]["content"] == "turn 11"))
        results.append(("blocks never resent in conversation history", all("blocks" not in t for t in long_history)))
        results.append(("history items are {role, content} only", all(set(t.keys()) == {"role", "content"} for t in long_history)))

        # ---------- Response contract ----------
        normalized = page.evaluate("""
            () => window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({
              reply: 'oi', blocks: [{type:'metrics', items:[]}], request_id: 'r1',
              scenario_reset: false, _homolog_debug: {secret: 'should not leak'}
            })
        """)
        results.append(("normalizeResponse strips _homolog_debug", "_homolog_debug" not in normalized))
        results.append(("normalizeResponse keeps reply/blocks/request_id/scenario_reset", normalized.get("reply") == "oi" and normalized.get("request_id") == "r1" and normalized.get("scenario_reset") is False))

        malformed = page.evaluate("""
            () => window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({
              reply: 'oi', blocks: [{type:'not_a_real_type', items:[]}, {type:'metrics', items:[]}]
            })
        """)
        results.append(("normalizeResponse silently drops an unrecognized block type", len(malformed["blocks"]) == 1 and malformed["blocks"][0]["type"] == "metrics"))

        empty_blocks = page.evaluate("() => window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({reply: 'oi', blocks: []})")
        results.append(("normalizeResponse turns an empty blocks array into null", empty_blocks["blocks"] is None))

        # ---------- Block type validation (all 6) ----------
        block_types = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.BLOCK_TYPES")
        results.append(("exactly 6 block types declared", sorted(block_types) == sorted(["metrics", "comparison", "ranking", "operations", "score_breakdown", "score_ranking"])))
        for t in block_types:
            ok = page.evaluate(f"window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock({{type: '{t}'}})")
            results.append((f"validateBlock accepts type={t}", ok is True))
        results.append(("validateBlock rejects an unknown type", page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock({type:'unknown_type'})") is False))
        results.append(("validateBlock rejects null", page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.validateBlock(null)") is False))

        # ---------- Format contract -- THE critical percent-scale check ----------
        pct = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue(1.12, 'percent')")
        results.append(("percent format does NOT multiply by 100 (1.12 -> '1,1%', never '112,0%')", pct["text"] == "1,1%"))

        cur = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue(90000, 'currency')")
        results.append(("currency format is pt-BR BRL", "R$" in cur["text"] and "90.000,00" in cur["text"]))

        cur_compact = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue(1500000, 'currency')")
        results.append(("currency >= 1M compacts to 'R$ X mi' with full value in title", "mi" in cur_compact["text"] and cur_compact["title"] is not None))

        integer = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue(13, 'int')")
        results.append(("int format renders a plain pt-BR number", integer["text"] == "13"))

        txt = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue('Balão 4x, R$ 189.900,00', 'text')")
        results.append(("text format renders a free-text value verbatim", txt["text"] == "Balão 4x, R$ 189.900,00"))
        txt_null = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue(null, 'text')")
        results.append(("text format: null -> em dash", txt_null["text"] == "—"))

        date_ok = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue('2026-10-01', 'date')")
        results.append(("date format: YYYY-MM-DD -> DD/MM/YYYY", date_ok["text"] == "01/10/2026"))
        date_bad = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue('not-a-date', 'date')")
        results.append(("date format: malformed string -> em dash, not Invalid Date", date_bad["text"] == "—"))

        for label, val, fmt in [("null currency", "null", "currency"), ("undefined percent", "undefined", "percent"), ("NaN int", "NaN", "int")]:
            r = page.evaluate(f"window.NX_BRABUS_INTELLIGENCE_ADAPTER.formatValue({val}, '{fmt}')")
            results.append((f"{label} -> em dash, never NaN/undefined/[object Object]", r["text"] == "—"))

        # ---------- Fixture scenario resolution (14 required + 3 bonus) ----------
        scenario_count = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.SCENARIOS.length")
        results.append((">= 14 fixture scenarios present", scenario_count >= 14))

        required_ids = ["plain-text", "linear", "balao", "coparticipado", "subsidiado", "taxa-implicita",
                         "antecipacao", "cash-conversion", "score", "historico", "unauthenticated",
                         "forbidden", "upstream-error", "scenario-reset"]
        for sid in required_ids:
            found = page.evaluate(f"!!window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('{sid}')")
            results.append((f"fixture scenario '{sid}' resolvable by id", found))

        for sid in required_ids:
            resolved = page.evaluate(f"""
                () => {{
                  var s = window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('{sid}');
                  var m = window.NX_BRABUS_INTELLIGENCE_ADAPTER.resolveFixtureScenario(s.prompt);
                  return m && m.id === '{sid}';
                }}
            """)
            results.append((f"fixture scenario '{sid}' own prompt resolves back to itself", resolved))

        combined = page.evaluate("window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('balao').response.blocks.length")
        results.append(("combined-blocks contract exercised (Balão fixture returns 2 blocks)", combined == 2))

        # ---------- Errors ----------
        for sid, status in [("unauthenticated", 401), ("forbidden", 403), ("upstream-error", 502)]:
            code = page.evaluate(f"window.NX_BRABUS_INTELLIGENCE_ADAPTER.loadFixtureScenario('{sid}').error.status")
            results.append((f"'{sid}' fixture carries status {status}", code == status))

        browser.close()

    ok = all(r[1] for r in results)
    for label, passed in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    print(f"\n=== Brabus Intelligence Contract Test: {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
