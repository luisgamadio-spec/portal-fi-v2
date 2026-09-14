#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SESSIONSEC1 -- cross-user conversation isolation regression.

Proves the fix for the CRITICAL_SECURITY_DEFECT_CROSS_USER_CONVERSATION_LEAK
Human incident: a previous authenticated identity's Brabus Intelligence
conversation (visible AND, if a message is sent, actually resubmitted as
model context to portal-ai-homolog) survived a real logout/login identity
change without a page reload.

Root cause (confirmed by direct source read, not guessed):
  assets/js/intelligence/intelligence-state.js's own `conversation` array
  is a module-level singleton with NO identity/ownership field at all --
  by design, so it SURVIVES route navigation (its own header comment).
  Nothing in the auth lifecycle (auth-core.js's login()/logout(), or any
  of the FOUR pre-existing independent NX_AUTH_CORE.onStateChange
  subscribers -- shell.js, login.js, intelligence-panel.js's own
  refreshVisibility) ever reset it. The only pre-existing caller of
  resetConversation() was the explicit Human "Nova Conversa" button.
  Worse: brabus-intelligence.adapter.js's createRequest() embeds up to
  the last 8 conversation turns verbatim into the request body, and
  portal-ai-homolog/index.ts (line ~8442, confirmed by direct read of the
  Secure repo, READ-ONLY this Wave) spreads that array directly into the
  model's own message list -- so an un-reset conversation is a genuine
  model-context leak, not merely a UI leak.

Fix (assets/js/intelligence/intelligence-state.js, intelligence-panel.js,
intelligence-voice.js -- see this Wave's own report): intelligence-state.js
becomes the SOLE authority for conversation ownership, keyed to
NX_AUTH_CORE's own real authUserId (never profile/store/department),
driven exclusively by the real NX_AUTH_CORE.onStateChange event stream
(never a second identity read). Any identity change (including logout)
resets the conversation and bumps a generation counter; Text and Voice
both capture that generation before any async work and discard a result
that comes back after it has moved on.

TECHNIQUE NOTE: unlike prior waves' tests (e.g. voiceuat1-voice-
activation-test.py), this test does NOT use the getState()/getContext()
override + panel.refresh() shortcut -- that shortcut never calls the
real auth-core.js setState(), so it would never invoke the very
onStateChange listener this fix depends on and would prove nothing about
it. Instead this test stubs window.NX_AUTH's methods and drives the REAL
NX_AUTH_CORE.login()/logout() state machine, exercising the exact code
path the incident and the fix are both about.

No real microphone/getUserMedia/RTCPeerConnection is ever completed
(same safe boundary as VOICE-UAT-1's own test -- a stubbed mint fetch
fails before doStart() can reach getUserMedia). No real salary/CPF value
is used or logged -- only synthetic sentinel markers (Section 17).

Requires: a static server for this worktree's own root (index.html at
the base URL) -- see main() for the port; start/stop it externally,
matching this repo's established test convention.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)

PORT = os.environ.get("SESSIONSEC1_TEST_PORT", "8713")
BASE = f"http://127.0.0.1:{PORT}"

MASTER_SENTINEL = "MASTER_SECRET_SENTINEL_9F31"
VENDEDOR_B_SENTINEL = "VENDEDOR_B_SECRET_SENTINEL_4C21"
LATE_A_SENTINEL = "LATE_RESPONSE_FROM_A_SENTINEL_7788"

USER_A = {"userId": "row-uat-a", "authUserId": "AUTHUSER-A-1111-1111-1111", "nome": "UAT MASTER A", "perfil": "MASTER", "loja": None, "status": "ATIVO", "ativo": True}
USER_B = {"userId": "row-uat-b", "authUserId": "AUTHUSER-B-2222-2222-2222", "nome": "UAT VENDEDOR B", "perfil": "VENDEDOR", "loja": "BARRA FUNDA", "status": "NOVOS", "ativo": True}
USER_C = {"userId": "row-uat-c", "authUserId": "AUTHUSER-C-3333-3333-3333", "nome": "UAT VENDEDOR C", "perfil": "VENDEDOR", "loja": "EUROPA", "status": "NOVOS", "ativo": True}

INSTALL_STUB_JS = """
(() => {
  window.__uatFakeSession = null;
  window.__uatPendingProfile = null;
  window.NX_AUTH = {
    isAuthConfigured: true,
    getSession: () => Promise.resolve(window.__uatFakeSession),
    signIn: () => {
      window.__uatFakeSession = { user: { id: (window.__uatPendingProfile || {}).authUserId } };
      return Promise.resolve();
    },
    signOut: () => { window.__uatFakeSession = null; return Promise.resolve(); },
    resolveAuthorizedProfile: () => Promise.resolve(window.__uatPendingProfile),
    resolveAllowedModules: () => Promise.resolve(['dashbi', 'simuladorCompleto', 'comissoes']),
    getAccessToken: () => Promise.resolve(window.__uatFakeSession ? ('uat-token-' + window.__uatFakeSession.user.id) : null),
    onAuthStateChange: () => {}
  };
})();
"""

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def login_as(page, profile):
    page.evaluate(
        "(p) => { window.__uatPendingProfile = p; return window.NX_AUTH_CORE.login('uat@test.invalid', 'x', 'uat-captcha'); }",
        profile
    )
    page.wait_for_function(
        "(id) => window.NX_AUTH_CORE.getState() === 'AUTHORIZED' && window.NX_AUTH_CORE.getContext() && window.NX_AUTH_CORE.getContext().authUserId === id",
        arg=profile["authUserId"], timeout=5000
    )


def logout(page):
    page.evaluate("() => window.NX_AUTH_CORE.logout()")
    page.wait_for_function("() => window.NX_AUTH_CORE.getState() === 'SIGNED_OUT'", timeout=5000)


def open_panel(page):
    launcher = page.locator("#baiLauncherBtn")
    assert launcher.count() == 1, "Living Core launcher missing -- cannot proceed"
    launcher.click(position={"x": 13, "y": 10}, force=True)
    page.wait_for_timeout(300)


def push_sentinel(page, text):
    page.evaluate(
        "(t) => window.NX_INTELLIGENCE_STATE.pushMessage({role: 'assistant', content: t, blocks: null, isError: false})",
        text
    )


def get_conversation(page):
    return page.evaluate("window.NX_INTELLIGENCE_STATE.getConversation()")


def main():
    from playwright.sync_api import sync_playwright

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        page.goto(BASE + "/index.html#/landing")
        page.wait_for_selector("#landingNav", timeout=8000)
        page.evaluate(INSTALL_STUB_JS)
        # This test exercises the real Text send pipeline (handleSendRealText),
        # so it needs real_text mode -- the base runtime config defaults to
        # 'fixture' (mode/endpoints intentionally inert everywhere but a real
        # deployed host). Endpoint values are placeholders: every network call
        # this test makes is intercepted by its own window.fetch stub below,
        # never a real request.
        page.evaluate("""() => {
            window.NX_INTELLIGENCE_CONFIG = Object.assign({}, window.NX_INTELLIGENCE_CONFIG, {
                mode: 'real_text',
                supabaseUrl: 'https://uat-test-only.invalid',
                textEndpoint: 'https://uat-test-only.invalid/functions/v1/portal-ai-homolog',
                voiceRealtimeEndpoint: 'https://uat-test-only.invalid/functions/v1/portal-realtime-homolog',
                supabasePublishableKey: 'uat-test-only-publishable-key'
            });
        }""")

        # ============================================================
        # SECTION 1 -- MASTER (USER A) conversation visible to A, wiped
        # on logout, VENDEDOR (USER B) starts clean. Reproduces the
        # exact Human incident.
        # ============================================================
        login_as(page, USER_A)
        gen0 = page.evaluate("window.NX_INTELLIGENCE_STATE.getGeneration()")
        owner_a = page.evaluate("window.NX_INTELLIGENCE_STATE.getOwnerAuthUserId()")
        check("Ownership keyed to USER A's real auth UUID (not profile/store/department)", owner_a == USER_A["authUserId"], owner_a)

        open_panel(page)
        push_sentinel(page, "Douglas comissao = R$ 3.092,14 -- " + MASTER_SENTINEL)
        conv_a_dom = page.locator("#baiPanelConversation").inner_text()
        check("Q1/1. USER A conversation visible to USER A", MASTER_SENTINEL in conv_a_dom)

        logout(page)
        conv_after_logout = get_conversation(page)
        check("Q6/2. Logout removes protected conversation immediately (in-memory, no page reload)", len(conv_after_logout) == 0, conv_after_logout)
        check("2b. Launcher DOM removed while SIGNED_OUT", page.locator("#baiLauncherRoot").count() == 0)

        login_as(page, USER_B)
        conv_b_start = get_conversation(page)
        check("Q7/3. USER B login starts clean, no page refresh used", len(conv_b_start) == 0, conv_b_start)
        owner_b = page.evaluate("window.NX_INTELLIGENCE_STATE.getOwnerAuthUserId()")
        check("Q5/'same profile' n/a here -- USER B owns a DIFFERENT auth UUID than USER A", owner_b == USER_B["authUserId"] and owner_b != owner_a, owner_b)
        gen_b = page.evaluate("window.NX_INTELLIGENCE_STATE.getGeneration()")
        check("Generation advanced on identity change (race-guard primitive armed)", gen_b > gen0, (gen0, gen_b))

        open_panel(page)
        conv_b_dom = page.locator("#baiPanelConversation").inner_text()
        check("Q4/4. USER A sentinel absent from USER B DOM", MASTER_SENTINEL not in conv_b_dom, conv_b_dom[:200])
        check("Q4/5. USER A sentinel absent from USER B in-memory state", MASTER_SENTINEL not in json.dumps(get_conversation(page)))

        # ============================================================
        # SECTION 2 -- USER B's own outbound Text payload never carries
        # USER A content (Category C: model-context leak, not just UI).
        # Also the positive-path regression check: a CURRENT-generation
        # reply still renders fine (the fix must not break normal use).
        # ============================================================
        page.evaluate("""() => {
            window.__uatCapturedBody = null;
            window.fetch = function (url, opts) {
                var u = String(url);
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_texto_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                window.__uatCapturedBody = opts.body;
                return Promise.resolve(new Response(JSON.stringify({ reply: 'ok-current-generation-reply', blocks: null }), { status: 200 }));
            };
        }""")
        page.locator("#baiPanelInput").fill("Qual e o meu score?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_timeout(600)
        body = page.evaluate("window.__uatCapturedBody") or ""
        check("Q11/6. USER B outbound Text payload (sent to portal-ai-homolog) carries NO USER A content", MASTER_SENTINEL not in body, body[:300])
        conv_b_after_send = page.locator("#baiPanelConversation").inner_text()
        check("Q17-style/17. Current-generation reply still renders (fix does not break normal Text use)", "ok-current-generation-reply" in conv_b_after_send, conv_b_after_send[:200])

        # ============================================================
        # SECTION 3 -- SAME-PROFILE, DIFFERENT USER (Section 16's own
        # explicit second case): VENDEDOR B -> logout -> VENDEDOR C.
        # Proves isolation is keyed to the real auth user, not perfil.
        # ============================================================
        push_sentinel(page, VENDEDOR_B_SENTINEL)
        logout(page)
        login_as(page, USER_C)
        open_panel(page)
        conv_c_dom = page.locator("#baiPanelConversation").inner_text()
        conv_c_state = get_conversation(page)
        check("Q12. Same-profile (VENDEDOR) different-user isolation: USER B sentinel absent from USER C DOM", VENDEDOR_B_SENTINEL not in conv_c_dom, conv_c_dom[:200])
        check("Q12. Same-profile different-user isolation: USER B sentinel absent from USER C in-memory state", VENDEDOR_B_SENTINEL not in json.dumps(conv_c_state))
        owner_c = page.evaluate("window.NX_INTELLIGENCE_STATE.getOwnerAuthUserId()")
        check("USER C owns a distinct auth UUID from USER B despite the identical perfil", owner_c == USER_C["authUserId"] and owner_c != owner_b, (owner_b, owner_c))

        # ============================================================
        # SECTION 4 -- CLIENT SPOOF CANNOT CLAIM OWNERSHIP. The only
        # writer of ownerAuthUserId is the internal clearForOwnerChange,
        # itself only reachable from the real NX_AUTH_CORE event stream
        # -- no public setter exists, and NX_INTELLIGENCE_CONTEXT's own
        # allow-listed publish() (a presentation-only hint channel) has
        # no identity-shaped key at all.
        # ============================================================
        spoof_attempt = page.evaluate("""() => {
            var before = window.NX_INTELLIGENCE_STATE.getOwnerAuthUserId();
            var hasSetter = typeof window.NX_INTELLIGENCE_STATE.setOwner === 'function' || typeof window.NX_INTELLIGENCE_STATE.setOwnerAuthUserId === 'function';
            if (window.NX_INTELLIGENCE_CONTEXT) {
                window.NX_INTELLIGENCE_CONTEXT.publish({ authUserId: 'SPOOFED-ID', isMaster: true, perfil: 'MASTER' });
            }
            var after = window.NX_INTELLIGENCE_STATE.getOwnerAuthUserId();
            return { before: before, after: after, hasSetter: hasSetter };
        }""")
        check("Q12/11. No public setter exists for conversation ownership", spoof_attempt["hasSetter"] is False, spoof_attempt)
        check("Q12/11. A spoofed NX_INTELLIGENCE_CONTEXT.publish() cannot change conversation ownership", spoof_attempt["before"] == spoof_attempt["after"] == USER_C["authUserId"], spoof_attempt)

        # ============================================================
        # SECTION 5 -- RACE PROTECTION. USER A sends a Text request that
        # never resolves until manually released; USER A logs out and
        # USER C (a different identity) logs back in WHILE it is still
        # in flight; only THEN is the response released. The late reply
        # (with a card/tool result attached, proving item 14 too) must
        # never render or persist under the new identity.
        # ============================================================
        logout(page)
        login_as(page, USER_A)
        open_panel(page)
        page.evaluate("""(lateSentinel) => {
            window.__uatReleaseLate = null;
            window.fetch = function (url, opts) {
                var u = String(url);
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_texto_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                return new Promise(function (resolve) {
                    window.__uatReleaseLate = function () {
                        resolve(new Response(JSON.stringify({
                            reply: lateSentinel,
                            blocks: [{ type: 'metrics', title: 'late-card-should-never-render', items: [] }]
                        }), { status: 200 }));
                    };
                });
            };
        }""", LATE_A_SENTINEL)
        page.locator("#baiPanelInput").fill("Qual foi o resultado da loja no mes passado?")
        page.locator("#baiPanelSendBtn").click()
        page.wait_for_function("() => typeof window.__uatReleaseLate === 'function'", timeout=5000)

        logout(page)
        login_as(page, USER_C)
        open_panel(page)
        page.evaluate("() => window.__uatReleaseLate()")
        page.wait_for_timeout(500)

        conv_c_after_race = get_conversation(page)
        dom_c_after_race = page.locator("#baiPanelConversation").inner_text()
        check("Q8/Q13/13. Late USER A Text response discarded after identity transition (in-memory)", LATE_A_SENTINEL not in json.dumps(conv_c_after_race), conv_c_after_race)
        check("Q8/Q13/13. Late USER A Text response discarded after identity transition (DOM)", LATE_A_SENTINEL not in dom_c_after_race, dom_c_after_race[:200])
        check("Q13/14. Late USER A tool/card result discarded along with it", "late-card-should-never-render" not in json.dumps(conv_c_after_race))

        # ============================================================
        # SECTION 6 -- VOICE / REALTIME. Same safe boundary as
        # VOICE-UAT-1's own test: a stubbed mint fetch fails before
        # doStart() can ever reach getUserMedia/RTCPeerConnection -- no
        # fake Human audio approval anywhere in this section.
        # ============================================================
        # 6a. Simulate "a live-ish Voice session exists" by directly
        # advancing the (already real, already transitioned) voice
        # state machine -- proves the owner-change listener this Wave
        # adds actually invokes doEnd()'s own pre-existing hard-stop
        # (RTCPeerConnection/DataChannel/mic teardown), not merely that
        # some unrelated code happens to reset an enum.
        page.evaluate("() => { window.NX_INTELLIGENCE_VOICE.mount(); window.NX_INTELLIGENCE_STATE.setVoiceState('VOICE_LISTENING'); }")
        voice_before = page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")
        check("6-setup. Voice state deliberately set to an active-looking state before the identity change", voice_before == "VOICE_LISTENING", voice_before)

        logout(page)
        voice_after_logout = page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")
        active_after_logout = page.evaluate("window.NX_INTELLIGENCE_VOICE.isActive()")
        check("Q10/9/10. Identity change (logout) hard-terminates the Voice session (VOICE_DISCONNECTED, doEnd() invoked)", voice_after_logout == "VOICE_DISCONNECTED", voice_after_logout)
        check("Q10/10. isActive() is false immediately after identity change (no session survives)", active_after_logout is False, active_after_logout)

        login_as(page, USER_B)
        page.evaluate("() => window.NX_INTELLIGENCE_VOICE.mount()")
        mint_call = page.evaluate("""() => {
            window.__uatVoiceMintCaptured = null;
            window.fetch = function (url, opts) {
                var u = String(url);
                if (u.indexOf('operational_portal_config') !== -1) {
                    return Promise.resolve(new Response(JSON.stringify({ rows: [{ chave: 'ia_voz_habilitada', valor: 'true' }] }), { status: 200 }));
                }
                window.__uatVoiceMintCaptured = u;
                return Promise.resolve(new Response(JSON.stringify({ error: 'stubbed, intentionally not ok' }), { status: 503 }));
            };
            window.NX_INTELLIGENCE_VOICE.start();
            return true;
        }""")
        page.wait_for_timeout(400)
        mint_url = page.evaluate("window.__uatVoiceMintCaptured")
        voice_state_new = page.evaluate("window.NX_INTELLIGENCE_STATE.getVoiceState()")
        check("Q10. USER B's start() performs a FRESH mint request (no reuse of any prior identity's session)", bool(mint_url), mint_url)
        check("18. Voice control still functions for the new identity (reaches VOICE_ERROR safely on a stubbed failure, never crashes/hangs)", voice_state_new == "VOICE_ERROR", voice_state_new)

        # ============================================================
        # SECTION 7 -- PAGE RELOAD cannot restore another user's
        # conversation (no persistence layer exists for conversation
        # content at all -- confirmed by source read: only Voice
        # diagnostics metadata, never message content, ever touches
        # localStorage).
        # ============================================================
        push_sentinel(page, "RELOAD-CANARY-" + VENDEDOR_B_SENTINEL)
        page.reload()
        page.wait_for_selector("#landingNav", timeout=8000)
        conv_after_reload = page.evaluate("window.NX_INTELLIGENCE_STATE ? window.NX_INTELLIGENCE_STATE.getConversation() : []")
        check("Q16-style/16. Page reload cannot restore ANY prior conversation (fresh module state, no persistence)", len(conv_after_reload) == 0, conv_after_reload)

        # ============================================================
        # SECTION 8 -- visual/responsive regression.
        # ============================================================
        overflow = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        check("19. Zero horizontal scroll (PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE)", overflow["scroll"] <= overflow["client"], overflow)

        page.close()
        browser.close()

    unexplained = [e for e in console_errors if "Failed to load resource" not in e]
    check("[ZERO JS ERROR] zero unexplained console/page errors overall", len(unexplained) == 0, unexplained[:8])

    ok = all(r[1] for r in results)
    print(f"\n=== SESSIONSEC1: Cross-User Conversation Isolation ({sum(1 for _, p in results if p)}/{len(results)}) ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
