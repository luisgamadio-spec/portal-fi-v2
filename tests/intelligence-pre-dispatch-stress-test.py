#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-R2C.1 -- CONSECUTIVE TURN STRESS (Phase 8).

Runs many four-turn sequences (B1-B4 shape) against the REAL, unmodified
intelligence-panel.js send/state machine, using deterministic mocked
backend responses (never a real LLM call), to prove the IA-R2C.1 fix
(isTextSurfaceEnabled() returning {enabled, confirmed}, see
intelligence-pre-dispatch-availability-recovery-test.py's own docstring
for the full root-cause writeup) holds under volume, not just the single
reproduction case.

Same harness conventions as the other tests in this file's own suite
(stub only NX_MASTER_CONFIG_PROVIDER.readConfig/window.fetch/sendRealText,
never handleSend/handleSendRealText/applyResult/isTextSurfaceEnabled).

Run: python tests/intelligence-pre-dispatch-stress-test.py [sequences]
(default 100 sequences x 4 turns = 400 submit cycles)
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PORT = os.environ.get("IA_R2C1_TEST_PORT", "8797")
BASE = f"http://localhost:{PORT}/index.html"
N_SEQUENCES = int(sys.argv[1]) if len(sys.argv) > 1 else 100

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def open_panel_authorized(page):
    page.evaluate(
        """() => {
            window.NX_AUTH_CORE.getState = () => 'AUTHORIZED';
            window.NX_AUTH_CORE.getContext = () => Object.freeze({ isMaster: true, perfil: 'MASTER' });
            window.NX_AUTH_CORE.isModuleAuthorized = () => true;
            window.NX_INTELLIGENCE_PANEL.refresh();
        }"""
    )
    page.wait_for_timeout(50)
    page.evaluate("window.NX_INTELLIGENCE_PANEL.openPanel()")
    page.wait_for_timeout(100)


def reset_conversation(page):
    page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation(); window.NX_INTELLIGENCE_STATE.setTextState('OPEN_IDLE');")


def send_message(page, text):
    page.evaluate(
        """(text) => {
            var input = document.getElementById('baiPanelInput');
            input.value = text;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }""",
        text,
    )
    page.evaluate("document.getElementById('baiPanelSendBtn').click()")


def stub_success(page, reply):
    page.evaluate(
        """(reply) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = { readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }]) };
            window.__dispatchCount = (window.__dispatchCount || 0);
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function (m, c) {
                window.__dispatchCount++;
                return Promise.resolve({ response: window.NX_BRABUS_INTELLIGENCE_ADAPTER.normalizeResponse({ reply: reply, blocks: null }) });
            };
        }""",
        reply,
    )


def stub_indeterminate_failure(page):
    page.evaluate(
        """() => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = { readConfig: () => Promise.reject(new Error('transient')) };
        }"""
    )


def stub_network_rejection(page):
    page.evaluate(
        """() => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.NX_MASTER_CONFIG_PROVIDER = { readConfig: () => Promise.resolve([{ chave: 'ia_texto_habilitada', valor: 'true' }]) };
            window.__dispatchCount = (window.__dispatchCount || 0);
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function (m, c) {
                window.__dispatchCount++;
                return Promise.resolve({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
            };
        }"""
    )


def input_disabled(page):
    return page.evaluate("document.getElementById('baiPanelInput').disabled")


def get_text_state(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()")


def user_msg_count(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation().filter(m => m.role === 'user').length")


def active_controller_is_null(page):
    # activeAbortController is a closure-private var, not exposed --
    # inferred instead via textState: between settled turns it must
    # always be a non-busy state (SENDING/THINKING would indicate a
    # controller is legitimately still tracked; anything else means it
    # was cleared, matching the source's own "cleared the moment it
    # settles" comment).
    return get_text_state(page) not in ("SENDING", "THINKING")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(500)
        open_panel_authorized(page)

        # ============================================================
        # PART 1 -- N_SEQUENCES x 4 successful turns (all-success path)
        # ============================================================
        total_cycles = 0
        permanent_disabled = 0
        stuck_busy = 0
        unavailable_terminal = 0
        duplicated_dispatches = 0

        for seq in range(N_SEQUENCES):
            reset_conversation(page)
            page.evaluate("window.__dispatchCount = 0;")
            for turn in range(1, 5):
                stub_success(page, "seq%d-turn%d-ok" % (seq, turn))
                before = page.evaluate("window.__dispatchCount")
                send_message(page, "seq%d turn%d" % (seq, turn))
                page.wait_for_timeout(30)
                after = page.evaluate("window.__dispatchCount")
                total_cycles += 1
                if after != before + 1:
                    duplicated_dispatches += 1
                if input_disabled(page):
                    permanent_disabled += 1
                if not active_controller_is_null(page):
                    stuck_busy += 1
                if get_text_state(page) in ("DISABLED", "SESSION_EXPIRED", "FORBIDDEN"):
                    unavailable_terminal += 1

        check(f"PART 1: {N_SEQUENCES * 4}/{N_SEQUENCES * 4} dispatches when backend mock succeeds", total_cycles == N_SEQUENCES * 4 and duplicated_dispatches == 0, {"total_cycles": total_cycles, "duplicated_dispatches": duplicated_dispatches})
        check("PART 1: 0 permanent disabled states across all successful turns", permanent_disabled == 0, permanent_disabled)
        check("PART 1: 0 stale/stuck busy states left behind between turns", stuck_busy == 0, stuck_busy)
        check("PART 1: 0 unavailable terminal states (DISABLED/SESSION_EXPIRED/FORBIDDEN) from pure success sequences", unavailable_terminal == 0, unavailable_terminal)
        check("PART 1: 0 duplicated dispatches", duplicated_dispatches == 0, duplicated_dispatches)

        # ============================================================
        # PART 2 -- MIXED FAILURE STRESS: an indeterminate-gate failure
        # or a network rejection injected on turn 2 or 3 of some
        # sequences; the SAME conversation must still accept and
        # dispatch the following turn.
        # ============================================================
        mixed_total = 0
        mixed_recovered = 0
        N_MIXED = max(20, N_SEQUENCES // 5)
        for seq in range(N_MIXED):
            reset_conversation(page)
            page.evaluate("window.__dispatchCount = 0;")
            stub_success(page, "mix%d-turn1-ok" % seq)
            send_message(page, "mix%d turn1" % seq)
            page.wait_for_timeout(30)

            if seq % 2 == 0:
                stub_indeterminate_failure(page)
            else:
                stub_network_rejection(page)
            send_message(page, "mix%d turn2 (injected failure)" % seq)
            page.wait_for_timeout(30)
            mixed_total += 1
            failure_recovered = input_disabled(page) is False and get_text_state(page) not in ("DISABLED", "SESSION_EXPIRED", "FORBIDDEN")

            stub_success(page, "mix%d-turn3-ok-after-failure" % seq)
            before = page.evaluate("window.__dispatchCount")
            send_message(page, "mix%d turn3 (retry after injected failure)" % seq)
            page.wait_for_timeout(30)
            after = page.evaluate("window.__dispatchCount")
            turn3_dispatched = after == before + 1 and ("mix%d-turn3-ok-after-failure" % seq) in page.locator("#baiPanelConversation").inner_text()

            if failure_recovered and turn3_dispatched:
                mixed_recovered += 1

        check(f"PART 2: mixed-failure stress -- next turn remains possible after an injected failure ({mixed_recovered}/{mixed_total})", mixed_recovered == mixed_total, {"recovered": mixed_recovered, "total": mixed_total})

        browser.close()

    print()
    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== IA-R2C.1 -- Consecutive Turn Stress ({N_SEQUENCES} sequences, {N_SEQUENCES * 4} cycles + {max(20, N_SEQUENCES // 5)} mixed-failure sequences): {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
