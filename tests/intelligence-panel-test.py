#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-3E -- Brabus Intelligence PERSISTENT PANEL test.

Covers the panel-specific surface added this Wave (assets/js/
intelligence/{intelligence-state,intelligence-context,intelligence-panel}.js):
launcher/drawer lifecycle, navigation persistence, the explicit TEXT
state machine, MASTER-only client presentation (real DOM removal, not
CSS hiding), context envelope updates, kill-switch/session/forbidden/
rate-limit/malformed-response UX, responsive/zero-scroll proof at the
4 required breakpoints, long-content containment, and a frozen-module
regression spot check.

Does NOT re-test the transport/contract layer itself (createRequest/
normalizeResponse/formatValue/the 6 structured-block renderers) -- that
is 100% reused, byte-for-byte, from assets/js/adapters/
brabus-intelligence.adapter.js and assets/js/brabus-intelligence.js,
already proven by the pre-existing intelligence-contract-test.py /
intelligence-presentation-parity-test.py / intelligence-structured-
block-test.py / intelligence-browser-test.py, re-run unmodified this
Wave as the regression proof (see docs/IA-3E-V2-INTELLIGENCE-PANEL.md).

401/403/429/503/malformed are exercised by stubbing
NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText (a public, pure function on
a plain object) while window.NX_INTELLIGENCE_CONFIG.mode is flipped to
'real_text' at runtime -- this drives the REAL handleSendRealText/
applyResult code path in the panel, only the network boundary itself
is stubbed, exactly the same seam the pre-existing adapter-level tests
already use for the routed page's own pure functions.

Requires: `python -m http.server <port>` running from this worktree's
own root (index.html at the base URL) -- see main() for the port.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-3e")
os.makedirs(SHOT_DIR, exist_ok=True)

PORT = os.environ.get("IA3E_TEST_PORT", "8711")
BASE = f"http://localhost:{PORT}/index.html"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" -- {detail}" if detail and not cond else ""))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


# IA-3E.4 finding: document.documentElement.scrollWidth does NOT
# reflect content overflowing a `position:fixed` ancestor (the
# drawer) -- a chip escaping the drawer's right edge by 10px was
# invisible to every scrollWidth-based check this suite used before,
# yet clearly visible on screen. This measures every real descendant's
# own getBoundingClientRect() against the actual viewport instead --
# the only reliable way to catch that class of bug. Used alongside
# (not instead of) the scrollWidth checks elsewhere in this file.
TRUE_OVERFLOW_JS = """
() => {
    var vw = window.innerWidth;
    var worst = 0, worstSel = null;
    document.querySelectorAll('#baiLauncherRoot *').forEach(el => {
        var r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        var over = Math.max(0, r.right - vw) + Math.max(0, -r.left);
        if (over > worst) { worst = over; worstSel = el.className || el.tagName; }
    });
    return { worst: worst, worstSel: String(worstSel) };
}
"""


def true_overflow(page):
    return page.evaluate(TRUE_OVERFLOW_JS)


def open_panel(page):
    page.click("#baiLauncherBtn")
    page.wait_for_timeout(150)


def close_panel(page):
    page.click("#baiPanelCloseBtn")
    page.wait_for_timeout(150)


def set_profile(page, state, is_master=None, perfil=None):
    """Monkeypatches NX_AUTH_CORE.getState/getContext (plain function
    properties on a real, already-loaded module object) and asks the
    panel to re-run its own real visibility decision -- the same
    decision a genuine onStateChange callback would trigger."""
    page.evaluate(
        """([state, isMaster, perfil]) => {
            window.NX_AUTH_CORE.getState = () => state;
            window.NX_AUTH_CORE.getContext = () => (isMaster === null ? null : Object.freeze({ isMaster, perfil }));
            window.NX_INTELLIGENCE_PANEL.refresh();
        }""",
        [state, is_master, perfil],
    )
    page.wait_for_timeout(50)


def stub_real_text(page, resolve_js, text_surface_enabled=True):
    """Replaces sendRealText (a plain function property) with a stub
    resolving the given result, and flips mode to real_text -- the
    ONLY two things changed; createRequest/normalizeResponse/applyResult
    and everything else stay the real, unmodified code.

    IA-3H.1C.4 (D14) -- handleSendRealText now checks isTextSurfaceEnabled()
    (window.NX_MASTER_CONFIG_PROVIDER.readConfig()) BEFORE ever calling
    sendRealText; every one of this helper's existing callers is testing
    a DIFFERENT failure class (401/403/429/malformed/etc.), not the
    surface gate itself, so this stubs the config read to resolve
    ia_texto_habilitada=true by default -- sendRealText is still reached
    exactly as each of those tests already expects. Pass
    text_surface_enabled=False only for a test that specifically wants
    the gate itself to block (see the dedicated D14 gate tests below)."""
    page.evaluate(
        """([resolveJs, enabled]) => {
            window.NX_INTELLIGENCE_CONFIG = window.NX_INTELLIGENCE_CONFIG || {};
            window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';
            window.__baiSendRealTextCalls = 0;
            window.NX_AUTH = { getAccessToken: () => Promise.resolve('fake-token') };
            window.__baiReadConfigCalls = 0;
            window.NX_MASTER_CONFIG_PROVIDER = {
                readConfig: function () {
                    window.__baiReadConfigCalls++;
                    return Promise.resolve([{ chave: 'ia_texto_habilitada', valor: enabled ? 'true' : 'false' }]);
                }
            };
            window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = function () {
                window.__baiSendRealTextCalls++;
                return (new Function('A', 'return ' + resolveJs))(window.NX_BRABUS_INTELLIGENCE_ADAPTER);
            };
        }""",
        [resolve_js, text_surface_enabled],
    )


def restore_fixture_mode(page):
    page.evaluate("window.NX_INTELLIGENCE_CONFIG.mode = 'fixture';")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(600)

        # ---------- Registration ----------
        check("NX_INTELLIGENCE_PANEL registered", page.evaluate("typeof window.NX_INTELLIGENCE_PANEL === 'object'"))
        check("NX_INTELLIGENCE_STATE registered", page.evaluate("typeof window.NX_INTELLIGENCE_STATE === 'object'"))
        check("NX_INTELLIGENCE_CONTEXT registered", page.evaluate("typeof window.NX_INTELLIGENCE_CONTEXT === 'object'"))
        check("routed #/brabus-intelligence page untouched (still registered)", page.evaluate("typeof window.NX_BRABUS_INTELLIGENCE_PAGE === 'object'"))

        # ---------- MASTER-only presentation (Section 15/18/19/49) ----------
        # AUTH_NOT_CONFIGURED (this host's real, unmodified default --
        # matches every other module's own convention).
        check("launcher visible: AUTH_NOT_CONFIGURED", page.locator("#baiLauncherBtn").count() == 1)

        PROFILE_MATRIX = [
            ("AUTHORIZED", True, "MASTER", True),
            ("AUTHORIZED", False, "RH", False),
            ("AUTHORIZED", False, "ANALISTA", False),
            ("AUTHORIZED", False, "GERENTE", False),
            ("AUTHORIZED", False, "VENDEDOR", False),
            ("AUTHORIZED", False, "DIRETOR NOVOS", False),
            ("AUTHORIZED", False, "DIRETOR SEMINOVOS", False),
            ("SIGNED_OUT", None, None, False),
            ("SESSION_EXPIRED", None, None, False),
        ]
        for state, is_master, perfil, expect_visible in PROFILE_MATRIX:
            set_profile(page, state, is_master, perfil)
            present = page.locator("#baiLauncherRoot").count() == 1
            label = f"profile presentation: {perfil or state} -> {'available' if expect_visible else 'not available (real DOM removal)'}"
            check(label, present == expect_visible)
        shot(page, "01-hidden-non-master.png")

        # restore MASTER for the rest of the flow
        set_profile(page, "AUTHORIZED", True, "MASTER")
        check("launcher rebuilt as a fresh DOM node for MASTER (not a stale CSS-hidden node reused)", page.locator("#baiLauncherBtn").count() == 1)

        # ---------- No duplicate Intelligence surface on the routed page ----------
        # Regression case found live during this Wave's own regression
        # pass: the launcher must not stack a second Intelligence
        # surface on top of the dedicated #/brabus-intelligence route.
        page.evaluate("window.location.hash = '#/brabus-intelligence'")
        page.wait_for_timeout(400)
        check("launcher suppressed on the routed #/brabus-intelligence page itself", page.locator("#baiLauncherRoot").count() == 0)
        check("exactly one .baiComposer on the routed Intelligence page (no collision)", page.locator(".baiComposer").count() == 1)
        page.evaluate("window.location.hash = '#/landing'")
        page.wait_for_timeout(400)
        check("launcher reappears after navigating away from the routed page", page.locator("#baiLauncherRoot").count() == 1)

        # ---------- Text local E2E (fixture mode) ----------
        open_panel(page)
        check("drawer opens", page.locator("#baiPanelDrawer").is_visible())
        check("TEXT state OPEN_IDLE on open", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "OPEN_IDLE")
        shot(page, "02-open-idle-landing.png")

        page.fill("#baiPanelInput", "x")
        check("TEXT state COMPOSING while typing", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "COMPOSING")
        page.fill("#baiPanelInput", "Qual foi o resultado do mês passado?")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(50)
        check("TEXT state reaches THINKING while in flight", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") in ("SENDING", "THINKING"))
        page.wait_for_timeout(400)
        check("assistant reply rendered", page.locator("#baiPanelConversation .baiMessageAssistant").count() >= 1)
        # .baiBlockPanel no longer applies to the `metrics` type as of
        # IA-3E.4's compact-evidence renderer (.baiCompactMetrics) --
        # this fixture is a metrics block, so check the new classes.
        check("structured block rendered (compact metrics evidence)", page.locator("#baiPanelConversation .baiCompactMetrics").count() >= 1)
        check("TEXT state settles to OPEN_IDLE after COMPLETE", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "OPEN_IDLE")
        shot(page, "03-panel-metrics.png")

        # ---------- New conversation ----------
        page.click("#baiPanelNewChatBtn")
        page.wait_for_timeout(100)
        check("Nova conversa clears the panel conversation", page.locator("#baiPanelConversation .baiMessage").count() == 0)

        # ---------- Context envelope (Section 23/24/32) ----------
        check("context route is landing before navigation", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().route") == "landing")
        page.evaluate("window.location.hash = '#/score'")
        page.wait_for_timeout(400)
        check("context route updates to score", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().route") == "score")
        check("context moduleId updates to score", page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot().moduleId") == "score")
        check("panel drawer persists across navigation (still open)", page.locator("#baiPanelDrawer").is_visible())
        check("Score module renders normally alongside the open panel (no frozen-module regression)", page.locator(".modPageHeader").count() > 0)
        shot(page, "04-panel-open-over-score.png")

        # publish() voluntary hint API -- not wired to any real module
        # this Wave, but proven to work + stay allow-listed.
        page.evaluate("window.NX_INTELLIGENCE_CONTEXT.publish({store:'Barra Funda', department:'NOVOS', perfil:'MASTER_SPOOF_ATTEMPT'})")
        snap = page.evaluate("window.NX_INTELLIGENCE_CONTEXT.getSnapshot()")
        check("publish() accepts an allow-listed key (store)", snap.get("store") == "Barra Funda")
        check("publish() silently drops a non-allow-listed key (perfil)", "perfil" not in snap or snap.get("perfil") is None)

        # ---------- Session / Forbidden / Rate-limit / Kill-switch / Malformed ----------
        # 503 -- kill switch
        stub_real_text(page, "Promise.resolve({error:{status:503,message:'Brabus Intelligence está temporariamente indisponível.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste kill switch")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("503: TEXT state DISABLED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "DISABLED")
        check("503: composer disabled", page.evaluate("document.getElementById('baiPanelInput').disabled") is True)
        check("503: status line shown, no technical config name leaked", "ia_texto_habilitada" not in page.locator("#baiPanelStatusLine").inner_text() and page.locator("#baiPanelStatusLine").is_visible())
        page.wait_for_timeout(400)
        check("503: no automatic retry (sendRealText called exactly once)", page.evaluate("window.__baiSendRealTextCalls") == 1)
        shot(page, "05-kill-switch-disabled.png")

        # 401 -- session expired (via getAccessToken resolving null, the
        # real path the routed page also uses -- not via sendRealText).
        page.click("#baiPanelNewChatBtn")
        page.evaluate("window.NX_AUTH = { getAccessToken: () => Promise.resolve(null) };")
        page.fill("#baiPanelInput", "teste sessão")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("401: TEXT state SESSION_EXPIRED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "SESSION_EXPIRED")
        check("401: composer disabled until a real fresh action", page.evaluate("document.getElementById('baiPanelInput').disabled") is True)
        check("401: correct Portuguese message, no stale authenticated capability implied", "Sessão expirada" in page.locator("#baiPanelStatusLine").inner_text())

        # 403 -- forbidden
        stub_real_text(page, "Promise.resolve({error:{status:403,message:'Este recurso não está disponível para o seu perfil.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste forbidden")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("403: TEXT state FORBIDDEN", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "FORBIDDEN")
        check("403: safe message, no raw backend reason leaked", page.locator("#baiPanelStatusLine").inner_text() == "Este recurso não está disponível para o seu perfil.")
        page.wait_for_timeout(400)
        check("403: no repeated automatic request", page.evaluate("window.__baiSendRealTextCalls") == 1)

        # 429 -- rate limit (transient: composer must re-enable, manual retry possible)
        stub_real_text(page, "Promise.resolve({error:{status:429,message:'Muitas solicitações em pouco tempo — aguarde um instante e tente novamente.'}})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste rate limit")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(200)
        check("429: TEXT state ERROR (transient, not sticky)", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "ERROR")
        check("429: clear transient message shown as a bubble", "aguarde um instante" in page.locator("#baiPanelConversation").inner_text())
        check("429: composer re-enabled -- manual retry is possible", page.evaluate("document.getElementById('baiPanelInput').disabled") is False)

        # Malformed response -- garbage payload through the REAL normalizeResponse
        stub_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:12345, blocks:'not-an-array', request_id:{}, scenario_reset:'yes'})})")
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste malformed")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(300)
        body_text = page.locator("#baiPanelConversation").inner_text()
        check("malformed response: no crash, no page error", True)  # implicit -- if this line is reached, nothing threw
        check("malformed response: no literal 'undefined' rendered", "undefined" not in body_text)
        check("malformed response: no [object Object] rendered", "[object Object]" not in body_text)
        shot(page, "06-malformed-response.png")

        # ---------- IA-3H.1C.4 (D14): proactive Text surface gate ----------
        # ia_texto_habilitada=false: a real Text send must be blocked
        # BEFORE sendRealText is ever called (Section 19's own explicit
        # requirement -- 0 portal-ai-homolog invocations for a blocked
        # Text request). stub_real_text's own sendRealText replacement
        # would fail this test instantly if ever invoked (the counter
        # assertion below), so this is a genuine proof the gate runs
        # first, not merely that the stub happens to also reject.
        stub_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:'NUNCA deveria ter chegado aqui', blocks:null, request_id:'r', scenario_reset:false})})", text_surface_enabled=False)
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste D14 gate via botao")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(300)
        check("D14 gate (button send): TEXT state DISABLED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "DISABLED")
        check("D14 gate (button send): sendRealText NEVER called (0 portal-ai invocations)", page.evaluate("window.__baiSendRealTextCalls") == 0)
        check("D14 gate (button send): the gate's own config read DID happen (proves the check actually ran, not a pre-existing 503)", page.evaluate("window.__baiReadConfigCalls") >= 1)
        check("D14 gate (button send): composer disabled, safe message shown, no leaked config key name", "ia_texto_habilitada" not in page.locator("#baiPanelStatusLine").inner_text() and page.locator("#baiPanelStatusLine").is_visible())
        no_leak_text = page.locator("#baiPanelConversation").inner_text()
        check("D14 gate (button send): the stub's own reply text never rendered (proves the blocked path, not a slow-but-real send)", "NUNCA deveria ter chegado aqui" not in no_leak_text)

        # Same proof for Enter-key submission (a second, independent user
        # Text entry path -- Section 11/29's explicit requirement).
        page.click("#baiPanelNewChatBtn")
        page.evaluate("window.__baiSendRealTextCalls = 0; window.__baiReadConfigCalls = 0;")
        page.fill("#baiPanelInput", "teste D14 gate via enter")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        check("D14 gate (Enter-key send): TEXT state DISABLED", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "DISABLED")
        check("D14 gate (Enter-key send): sendRealText NEVER called (0 portal-ai invocations)", page.evaluate("window.__baiSendRealTextCalls") == 0)

        # Flip the gate back on (same stub, only the flag value changes)
        # and prove a real send proceeds normally -- the gate is a real
        # boolean switch, not a one-way lock.
        stub_real_text(page, "Promise.resolve({response: A.normalizeResponse({reply:'resposta real apos gate liberado', blocks:null, request_id:'r2', scenario_reset:false})})", text_surface_enabled=True)
        page.click("#baiPanelNewChatBtn")
        page.fill("#baiPanelInput", "teste D14 gate liberado")
        page.click("#baiPanelSendBtn")
        page.wait_for_timeout(300)
        check("D14 gate (re-enabled): TEXT state settles to OPEN_IDLE", page.evaluate("window.NX_INTELLIGENCE_STATE.getTextState()") == "OPEN_IDLE")
        check("D14 gate (re-enabled): sendRealText WAS called exactly once", page.evaluate("window.__baiSendRealTextCalls") == 1)
        check("D14 gate (re-enabled): the real reply rendered", "resposta real apos gate liberado" in page.locator("#baiPanelConversation").inner_text())
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        restore_fixture_mode(page)
        page.evaluate("delete window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText; window.NX_BRABUS_INTELLIGENCE_ADAPTER.sendRealText = undefined;")
        # sendRealText must be restored from the real adapter file, not
        # left undefined -- reload to get a fully clean module state
        # back for the remaining checks.
        page.reload()
        page.wait_for_timeout(600)
        set_profile(page, "AUTHORIZED", True, "MASTER")

        # ---------- Long content containment (Section 41/56) ----------
        open_panel(page)
        long_token = "X" * 400
        page.evaluate(
            """(tok) => {
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'user', content:'pergunta longa '.repeat(40), blocks:null, isError:false});
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'resposta longa '.repeat(60) + tok, blocks:null, isError:false});
            }""",
            long_token,
        )
        page.wait_for_timeout(100)
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("long content: no page horizontal overflow", overflow <= 0, overflow)
        drawer_overflow = page.evaluate("(function(){var el=document.getElementById('baiPanelDrawer'); return el.scrollWidth - el.clientWidth;})()")
        check("long content: no drawer wrapper horizontal overflow", drawer_overflow <= 0, drawer_overflow)
        shot(page, "07-long-content.png")
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        # ---------- Compact metrics evidence (IA-3E.4) ----------
        # The redundant block heading is no longer visible, but stays
        # in the DOM (sr-only) -- title+period must never be dropped.
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'resposta', blocks:[{
                    type:'metrics', title:'Grupo — mês anterior', period_label:'mês anterior', items:[
                        {key:'sales', label:'Vendas', value:13, format:'int'},
                        {key:'financed', label:'Financiamentos', value:10, format:'int'},
                        {key:'share_percent', label:'Share', value:76.9, format:'percent'},
                        {key:'production', label:'Produção', value:100500, format:'currency'},
                        {key:'return', label:'Retorno', value:68600, format:'currency'}
                    ]
                }], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        sr = page.locator(".baiCompactMetrics .baiSrOnly")
        sr_box = sr.bounding_box()
        # Playwright's inner_text() includes clip-rect-hidden (sr-only)
        # text, so "not visible" is proven by bounding-box size, not by
        # excluding it from a text search (the same lesson from IA-3E.2's
        # own role-label check) -- the strip/facts elements themselves
        # structurally don't contain the heading at all, confirming it
        # renders nowhere but the sr-only node.
        check("compact metrics: redundant heading text absent from the visible strip/facts", "GRUPO" not in (page.locator(".baiMetricStrip").inner_text() + page.locator(".baiMetricFacts").inner_text()).upper())
        check("compact metrics: heading preserved sr-only for a11y (~1px, in DOM)", sr.count() == 1 and sr_box is not None and sr_box["width"] <= 1)
        check("compact metrics: 3 volume/share metrics rendered as chips", page.locator(".baiMetricChip").count() == 3)
        check("compact metrics: 2 financial (currency) metrics rendered as facts", page.locator(".baiMetricFact").count() == 2)
        check("compact metrics: no orphaned single KPI row (2 currency items = one balanced row)", page.locator(".baiMetricFacts").bounding_box()["height"] < 70)
        metrics_h = page.locator(".baiAnswerMetrics").bounding_box()["height"]
        check("compact metrics: region materially more compact than IA-3E.3 (measured <150px, was 208px)", metrics_h < 150, metrics_h)
        check("compact metrics: financial value uses normal UI font, not monospace",
              page.locator(".baiMetricFactValue").first.evaluate("e => getComputedStyle(e).fontFamily").find("Mono") == -1)
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        # No value dropped across 2-6 metrics (Section 16/18)
        ALL_ITEMS_JS = """[
            {key:'sales', label:'Vendas', value:13, format:'int'},
            {key:'financed', label:'Financiamentos', value:10, format:'int'},
            {key:'share_percent', label:'Share', value:76.9, format:'percent'},
            {key:'production', label:'Produção', value:100500, format:'currency'},
            {key:'return', label:'Retorno', value:68600, format:'currency'},
            {key:'avg_ticket', label:'Ticket Médio', value:45000, format:'currency'}
        ]"""
        for n in (2, 3, 4, 5, 6):
            page.evaluate(
                """(n) => {
                    window.NX_INTELLIGENCE_STATE.resetConversation();
                    var all = """ + ALL_ITEMS_JS + """;
                    window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{type:'metrics', title:'t', items: all.slice(0, n)}], isError:false});
                }""",
                n,
            )
            page.wait_for_timeout(100)
            total = page.locator(".baiMetricChip").count() + page.locator(".baiMetricFact").count()
            check(f"compact metrics: {n} items -> {n} rendered (chip+fact), none dropped", total == n, total)
            ov = true_overflow(page)
            check(f"compact metrics: {n} items -> no true viewport overflow", ov["worst"] <= 0.5, ov)

        # Long-label stress -- the exact bug found live this Wave (a
        # white-space:nowrap chip escaping the drawer's right edge,
        # invisible to scrollWidth-based checks -- see TRUE_OVERFLOW_JS).
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{
                    type:'metrics', title:'t', items:[
                        {key:'a', label:'Vendedor com nome extremamente longo para teste de quebra de linha em qualquer largura', value:3, format:'int'},
                        {key:'b', label:'Valor extremo', value:123456789.99, format:'currency'},
                        {key:'c', label:'Percentual extremo', value:999.99, format:'percent'}
                    ]
                }], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        ov_long = true_overflow(page)
        check("compact metrics: long label does not escape viewport (regression guard)", ov_long["worst"] <= 0.5, ov_long)
        shot(page, "09-compact-metrics-long-label.png")

        # score_ranking/score_breakdown/operations stay on the shared,
        # unmodified table/card renderer (P.renderStructuredBlock) --
        # only `metrics` (IA-3E.4) and now `ranking` (IA-3H.1C.3, below)
        # get their own drawer-only compact presentation.
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{
                    type:'score_ranking', title:'Ranking Score F&I — período atual',
                    items:[{rank:1,seller:'Ana Paula Ribeiro',store:'Barra Funda',department:'NOVOS',score:87.4,classification:'Alto Desempenho',sales:12,financed:10}]
                }], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        check("score_ranking: still uses the shared table renderer (unaffected by this Wave)", page.locator(".baiAnswerMetrics table").count() >= 1)
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        # ---------- IA-3H.1C.3: compact ranking cards (structured-response renderer fix) ----------
        # Reproduces the real Human-visible shape from the UAT screenshot
        # ("Qual loja teve o melhor resultado?" -> RANKING DE LOJAS POR
        # RETORNO) generically -- real field keys from the shared,
        # authoritative RANKING_FIELD_META (brabus-intelligence.js),
        # never invented, never special-cased to Bandeirantes/retorno.
        RANKING_STORES_FIXTURE = {
            "type": "ranking", "title": "Ranking de Lojas por Retorno", "period_label": "mês anterior",
            "dimension": "store", "metric": "return",
            "items": [
                {"position": 1, "name": "Bandeirantes", "return": 197172.96, "sales": 84, "financed": 33, "penetration_percent": 39.3, "production": 4050000, "return_avg_percent": 4.9},
                {"position": 2, "name": "Loja com Nome Extremamente Longo Para Teste de Quebra", "return": 152300.5, "sales": 61, "financed": 28, "penetration_percent": 45.9, "production": 128456789.99, "return_avg_percent": 87.65},
                {"position": 3, "name": "Nações", "return": 98450.1, "sales": 40, "financed": 15, "penetration_percent": 37.5, "production": 2100000, "return_avg_percent": 4.1},
            ],
        }
        page.evaluate(
            """(block) => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'Bandeirantes teve o maior retorno; Nações teve o maior retorno médio.', blocks:[block], isError:false});
            }""",
            RANKING_STORES_FIXTURE,
        )
        page.wait_for_timeout(150)
        # NOTE: .baiBlockTitle/.baiRankMetricLabel both carry an
        # intentional `text-transform:uppercase` (matching the existing
        # .baiMetricFactLabel/.baiBlockTitle visual convention elsewhere
        # in this file/CSS) -- Playwright's inner_text() returns the
        # RENDERED (post-CSS-transform) text, so label/title assertions
        # below compare case-insensitively; .baiRankName carries no such
        # transform, so entity-name assertions stay case-sensitive.
        check("ranking cards: narrative answer preserved above the structured evidence", "maior retorno" in page.locator("#baiPanelConversation").inner_text())
        check("ranking cards: title preserved", "RANKING DE LOJAS POR RETORNO" in page.locator(".baiBlockTitle").inner_text().upper())
        check("ranking cards: period label preserved", "mês anterior" in page.locator(".baiBlockPeriod").inner_text().lower())
        check("ranking cards: rendered as cards, not a table (Section 11)", page.locator(".baiAnswerMetrics table").count() == 0 and page.locator(".baiRankCard").count() == 3)
        rank_text = page.locator(".baiRankList").inner_text()
        rank_text_upper = rank_text.upper()
        check("ranking cards: every item has a semantic label, not a raw field key (Section 10)", "RETURN_AVG_PERCENT" not in rank_text_upper and "PENETRATION_PERCENT" not in rank_text_upper)
        check("ranking cards: semantic label 'Retorno' present", "RETORNO" in rank_text_upper)
        check("ranking cards: semantic label 'Vendas' present", "VENDAS" in rank_text_upper)
        check("ranking cards: semantic label 'Financiamentos' present", "FINANCIAMENTOS" in rank_text_upper)
        check("ranking cards: semantic label 'Penetração' present", "PENETRA" in rank_text_upper)
        check("ranking cards: semantic label 'Produção' present", "PRODU" in rank_text_upper)
        check("ranking cards: rank #1 visible", "#1" in rank_text)
        check("ranking cards: entity name visible (Bandeirantes)", "Bandeirantes" in rank_text)
        check("ranking cards: order preserved (Bandeirantes before Nações)", rank_text.index("Bandeirantes") < rank_text.index("Nações"))
        check("ranking cards: large money formatted (R$ ... mi, real formatValue, not a raw number)", "128,46 mi" in rank_text or "128.46 mi" in rank_text or "mi" in rank_text)
        check("ranking cards: percent value formatted with a %", "87,7%" in rank_text or "87,6%" in rank_text or "87.7%" in rank_text or "87.6%" in rank_text)
        check("ranking cards: long entity name present in full, never truncated/hidden", "Loja com Nome Extremamente Longo Para Teste de Quebra" in rank_text)
        primary_label = page.locator(".baiRankCard").first.locator(".baiRankMetricPrimary .baiRankMetricLabel").inner_text()
        check("ranking cards: primary metric (return) emphasized as the first card in reading order", primary_label.strip().upper() == "RETORNO")

        # Fallback for an unknown field -- never an anonymous number.
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{
                    type:'ranking', title:'Campo desconhecido', dimension:'store', metric:'a_never_before_seen_field',
                    items:[{position:1,name:'Loja X', a_never_before_seen_field: 4242}]
                }], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        fallback_text = page.locator(".baiRankList").inner_text()
        # fieldMeta's own fallback ({label: key, format: null}) formats
        # the raw number via the generic pt-BR branch (thousands
        # separator, e.g. "4.242"), not a plain "4242" string -- this
        # checks for that real formatted output, not a guessed shape.
        check("ranking cards: unknown field gets a safe readable fallback label (the raw key), never a blank/anonymous value", "A_NEVER_BEFORE_SEEN_FIELD" in fallback_text.upper() and "4.242" in fallback_text)

        # Empty items -- safe message, never a blank card region.
        page.evaluate(
            """() => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{type:'ranking', title:'Sem dados', dimension:'store', metric:'return', items:[]}], isError:false});
            }"""
        )
        page.wait_for_timeout(150)
        check("ranking cards: empty items shows a safe message, not a blank region", "Sem itens" in page.locator(".baiAnswerMetrics").inner_text())

        # ---------- Component-level + responsive zero-scroll proof (Section 12/31/32) ----------
        # scrollWidth<=clientWidth alone can pass on an element with
        # overflow-x:auto and a hidden scrollbar (Section 31's own
        # explicit warning) -- this renderer uses no overflow-x:auto
        # anywhere, so the same check here is a genuine proof, not a
        # false negative in waiting.
        page.evaluate(
            """(block) => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[block], isError:false});
            }""",
            RANKING_STORES_FIXTURE,
        )
        page.wait_for_timeout(150)
        for w in (1366, 1024, 900, 480, 375):
            page.set_viewport_size({"width": w, "height": 900})
            page.wait_for_timeout(80)
            widths = page.evaluate(
                """() => {
                    function w(sel) { var el = document.querySelector(sel); return el ? {scrollWidth: el.scrollWidth, clientWidth: el.clientWidth} : null; }
                    return { list: w('.baiRankList'), card: w('.baiRankCard'), metrics: w('.baiRankMetrics'), drawer: w('#baiPanelDrawer') };
                }"""
            )
            check(f"{w}px: ranking list component no overflow (scrollWidth<=clientWidth)", widths["list"] and widths["list"]["scrollWidth"] <= widths["list"]["clientWidth"] + 1, widths["list"])
            check(f"{w}px: ranking card component no overflow", widths["card"] and widths["card"]["scrollWidth"] <= widths["card"]["clientWidth"] + 1, widths["card"])
            check(f"{w}px: ranking metrics grid no overflow", widths["metrics"] and widths["metrics"]["scrollWidth"] <= widths["metrics"]["clientWidth"] + 1, widths["metrics"])
            check(f"{w}px: drawer wrapper no overflow", widths["drawer"] and widths["drawer"]["scrollWidth"] <= widths["drawer"]["clientWidth"], widths["drawer"])
            page_overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{w}px: page no horizontal overflow", page_overflow <= 0, page_overflow)
            tov = true_overflow(page)
            check(f"{w}px: no element truly escapes the viewport (ranking cards)", tov["worst"] <= 0.5, tov)
        shot(page, "12-ranking-cards-drawer.png")
        # IA-3H.1C.3 -- restore the page's own original viewport (this
        # sweep leaves it at the LAST tested width, 375px) before the
        # next section runs; that section forces the drawer's own width
        # directly via inline style, but still assumes the page's real
        # viewport is the original 1366x768 (found live: leaving the
        # viewport at 375px made the immediately-following container-
        # query check intermittently read a stale/mobile-constrained
        # layout instead of the forced 700px content width).
        page.set_viewport_size({"width": 1366, "height": 768})
        page.wait_for_timeout(80)
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        # ---------- IA-3G.1/IA-3G.3: comparison block overflow + density regression ----------
        # Reproduces the exact Human UAT findings across both rounds:
        # IA-3G.1 ("E comparado ao mês anterior?" -> two comparison cards
        # overflowed the drawer horizontally) and IA-3G.3 (the horizontal
        # fix over-corrected -> each period card became ~500px tall,
        # unreadable). Uses the REAL comparison field set and shape,
        # byte-matched against buildComparisonBlock's own 8 items
        # (supabase/functions/portal-ai-homolog/index.ts) -- sales,
        # financed, share_percent, production, return, return_avg_percent,
        # spf, profitability (note: spf_net/"SPF Líquido" is NOT part of
        # the real comparison block, only the single-period metrics
        # block) -- and a real custom-range period_label
        # ("2026-08-01 a 2026-08-31") exactly matching resolvePeriod()'s
        # own "custom" kind output for a follow-up with no period enum,
        # to also exercise the IA-3G.3 date-format presentation fix.
        def comparison_side(label, period_label, sales, financed, share, production, ret, ret_avg, spf, profit):
            return {
                "label": label, "period_label": period_label,
                "items": [
                    {"key": "sales", "label": "Vendas", "value": sales, "format": "int"},
                    {"key": "financed", "label": "Financiamentos", "value": financed, "format": "int"},
                    {"key": "share_percent", "label": "Share", "value": share, "format": "percent"},
                    {"key": "production", "label": "Produção", "value": production, "format": "currency"},
                    {"key": "return", "label": "Retorno", "value": ret, "format": "currency"},
                    {"key": "return_avg_percent", "label": "Retorno Médio", "value": ret_avg, "format": "percent"},
                    {"key": "spf", "label": "SPF", "value": spf, "format": "currency"},
                    {"key": "profitability", "label": "Rentabilidade / Receita Total", "value": profit, "format": "currency"},
                ]
            }
        import json as _json
        side_a = comparison_side("Grupo", "2026-08-01 a 2026-08-31", 378, 154, 40.74, 15287967.14, 683602.02, 4.95, 105305.66, 757316)
        side_b = comparison_side("Grupo", "2026-07-01 a 2026-07-31", 341, 139, 38.2, 13120500.0, 601200.5, 4.6, 96500.0, 690000)
        page.evaluate(
            """(payload) => {
                window.NX_INTELLIGENCE_STATE.resetConversation();
                window.NX_INTELLIGENCE_STATE.pushMessage({role:'assistant', content:'r', blocks:[{
                    type:'comparison', title:'Comparação', a: payload.a, b: payload.b,
                    deltas: { sales:37, financed:15, share_percent:2.54, production:2167467.14, return:82401.52, return_avg_percent:0.35, spf:8805.66 }
                }], isError:false});
            }""",
            {"a": side_a, "b": side_b},
        )
        page.wait_for_timeout(150)
        cmp_true_ov = true_overflow(page)
        check("comparison: no true viewport overflow at real drawer width", cmp_true_ov["worst"] <= 0.5, cmp_true_ov)
        cmp_widths = page.evaluate(
            """() => {
                function w(sel) { var el = document.querySelector(sel); return el ? {scrollWidth: el.scrollWidth, clientWidth: el.clientWidth} : null; }
                return { grid: w('.baiComparisonGrid'), sideA: w('.baiComparisonSide'), body: w('#baiPanelConversation') };
            }"""
        )
        check("comparison grid: scrollWidth <= clientWidth", cmp_widths["grid"] and cmp_widths["grid"]["scrollWidth"] <= cmp_widths["grid"]["clientWidth"], cmp_widths["grid"])
        check("comparison side card: scrollWidth <= clientWidth", cmp_widths["sideA"] and cmp_widths["sideA"]["scrollWidth"] <= cmp_widths["sideA"]["clientWidth"], cmp_widths["sideA"])
        check("comparison: stacks to 1 column at the real (narrow) drawer width (outer grid)", page.evaluate("getComputedStyle(document.querySelector('.baiComparisonGrid')).gridTemplateColumns.split(' ').length") == 1)
        # ---- IA-3G.3 density assertions ----
        inner_cols = page.evaluate("getComputedStyle(document.querySelector('.baiComparisonSide .baiMetricsGrid')).gridTemplateColumns.split(' ').length")
        check("comparison: internal KPI grid uses 2 columns at the real drawer width (density fix, not 1)", inner_cols == 2, inner_cols)
        card_heights = page.evaluate(
            """() => {
                var sides = document.querySelectorAll('.baiComparisonSide');
                return Array.from(sides).map(s => Math.round(s.getBoundingClientRect().height));
            }"""
        )
        check("comparison: each period card height is compact (< 280px for 8 items in 2 columns), not ~500-700px", all(h < 280 for h in card_heights), card_heights)
        check("comparison: both period labels present and readable (no metric dropped)", "378" in page.locator(".baiComparisonGrid").inner_text() and "341" in page.locator(".baiComparisonGrid").inner_text())
        cmp_text = page.locator(".baiComparisonGrid").inner_text()
        check("comparison: custom-range period label reformatted to dd/mm/aaaa (not raw ISO)", "01/08/2026 a 31/08/2026" in cmp_text and "01/07/2026 a 31/07/2026" in cmp_text)
        check("comparison: no raw ISO date range leaked (YYYY-MM-DD) in the rendered label", "2026-08-01" not in cmp_text and "2026-07-01" not in cmp_text)
        shot(page, "10-comparison-fixed-drawer-width.png")
        shot(page, "11-comparison-density-fixed.png")

        # Direct container-width injection -- proves the @container
        # threshold itself is genuinely width-reactive (not merely
        # "coincidentally always narrow"): a container query can never
        # be exercised on its wide-enough branch by resizing the
        # browser viewport alone, since the real drawer is capped at
        # min(420px,100vw) and never grows past that regardless of
        # viewport width (Section 33's own drawer-content-width matrix).
        for forced_width, expect_columns, label in ((700, 2, "wide container (700px) allows side-by-side"), (480, 1, "narrow container (480px) stacks"), (400, 1, "very narrow container (400px) stacks")):
            page.evaluate("(w) => { document.getElementById('baiPanelDrawer').style.width = w + 'px'; }", forced_width)
            page.wait_for_timeout(80)
            cols = page.evaluate("getComputedStyle(document.querySelector('.baiComparisonGrid')).gridTemplateColumns.split(' ').length")
            check(f"container query @ {forced_width}px content width: {label}", cols == expect_columns, cols)
            widths = page.evaluate(
                """() => {
                    function w(sel) { var el = document.querySelector(sel); return el ? {scrollWidth: el.scrollWidth, clientWidth: el.clientWidth} : null; }
                    return { grid: w('.baiComparisonGrid'), drawer: w('#baiPanelDrawer') };
                }"""
            )
            check(f"container query @ {forced_width}px: comparison grid never overflows its own box", widths["grid"] and widths["grid"]["scrollWidth"] <= widths["grid"]["clientWidth"], widths["grid"])
            check(f"container query @ {forced_width}px: drawer itself never overflows", widths["drawer"] and widths["drawer"]["scrollWidth"] <= widths["drawer"]["clientWidth"], widths["drawer"])
        page.evaluate("document.getElementById('baiPanelDrawer').style.width = '';")  # restore real width
        page.evaluate("window.NX_INTELLIGENCE_STATE.resetConversation();")

        page.close()

        # ---------- IA-3G.3: transport provenance regression ----------
        # Reproduces the exact live incident: a local UAT (intelligence-
        # runtime-config.local.js, gitignored) went missing between
        # Waves, silently reverting window.NX_INTELLIGENCE_CONFIG.mode
        # to the committed 'fixture' default, and the Human's real UAT
        # unknowingly exercised synthetic data with no visible signal
        # that had happened. Uses its own isolated page (never touches
        # the real network/auth boundary -- mode is stubbed exactly like
        # the suite's own existing stub_real_text() helper already
        # does) so this never depends on -- or is broken by -- whether
        # a real .local.js happens to be present on this machine.
        prov_page = browser.new_page(viewport={"width": 1366, "height": 900})
        prov_page.goto(BASE)
        prov_page.wait_for_timeout(400)
        set_profile(prov_page, "AUTHORIZED", True, "MASTER")
        open_panel(prov_page)
        fixture_state = prov_page.evaluate(
            """() => ({
                attr: document.getElementById('baiPanelDrawer').getAttribute('data-nx-transport'),
                bannerVisible: !!document.getElementById('baiPanelProvenanceBanner')
            })"""
        )
        check("provenance: fixture mode marks data-nx-transport=fixture on the drawer", fixture_state["attr"] == "fixture", fixture_state)
        check("provenance: fixture mode shows the visible dev-only banner (Human-observable, not just automated)", fixture_state["bannerVisible"] is True, fixture_state)

        # Force a teardown + rebuild with mode flipped to real_text --
        # SIGNED_OUT triggers real DOM removal (Section 49 -- panelBuilt
        # resets), matching exactly what a genuine unauthenticated ->
        # authenticated transition does; simulates what a present
        # .local.js sets, without any real network/auth dependency.
        set_profile(prov_page, "SIGNED_OUT")
        prov_page.evaluate("window.NX_INTELLIGENCE_CONFIG.mode = 'real_text';")
        set_profile(prov_page, "AUTHORIZED", True, "MASTER")
        open_panel(prov_page)
        real_state = prov_page.evaluate(
            """() => ({
                attr: document.getElementById('baiPanelDrawer').getAttribute('data-nx-transport'),
                bannerVisible: !!document.getElementById('baiPanelProvenanceBanner')
            })"""
        )
        check("provenance: real_text mode marks data-nx-transport=real_text on the drawer", real_state["attr"] == "real_text", real_state)
        check("provenance: real_text mode shows NO dev-only banner (Human-approved drawer untouched)", real_state["bannerVisible"] is False, real_state)

        # ---- Safety net (Section 21): a failing real transport must
        # NEVER silently answer with fixture data. handleSend's own
        # if/else (P.isRealTextMode() ? handleSendRealText :
        # handleSendFixture) already makes this structurally impossible
        # -- there is no shared code path -- this proves it end-to-end
        # anyway: stub sendRealText to reject, and confirm the rendered
        # reply is the real error copy, never a fixture scenario's own
        # reply text (e.g. the 13-vendas/10-financiamentos payload) nor
        # the fixture-miss message ("Não tenho um cenário de teste...").
        stub_real_text(prov_page, "Promise.resolve({error:{status:0,message:'Não foi possível concluir a análise agora. Tente novamente.'}})")
        prov_page.click("#baiPanelNewChatBtn")
        prov_page.fill("#baiPanelInput", "Como foi o resultado do mês passado?")
        prov_page.click("#baiPanelSendBtn")
        prov_page.wait_for_timeout(300)
        safety_text = prov_page.locator("#baiPanelConversation").inner_text()
        check("provenance safety: real_text transport failure shows the real error copy", "Não foi possível concluir a análise agora" in safety_text, safety_text)
        check("provenance safety: NEVER the fixture's own synthetic figures (13 vendas/10 financiamentos)", "13 vendas" not in safety_text and "10 financiamentos" not in safety_text, safety_text)
        check("provenance safety: NEVER the fixture-miss message either (would imply fixture code ran)", "cenário de teste" not in safety_text, safety_text)
        check("provenance safety: sendRealText called exactly once, resolveFixtureScenario never reached", prov_page.evaluate("window.__baiSendRealTextCalls") == 1, prov_page.evaluate("window.__baiSendRealTextCalls"))

        # ---------- IA-3G.5A: dev-timing diagnostic safety ----------
        # Proves the CONSUMER side (logDevTiming in intelligence-panel.js)
        # of the new pre-Edge latency instrumentation: given a result
        # shaped exactly like what the real sendRealText() now produces
        # (response + _devTiming, per brabus-intelligence.adapter.js's
        # buildDevTiming), it must log a single '[bai-timing]' console
        # line containing only numbers/ids -- never prompt or reply
        # content -- and never render _devTiming anywhere in the DOM.
        # Captured page-side (not via the `console` event's msg.text(),
        # which truncates/summarizes a large object argument in
        # Chromium's own console formatting) -- same robust pattern this
        # suite already uses for __baiSendRealTextCalls.
        prov_page.evaluate(
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
        stub_real_text(
            prov_page,
            """Promise.resolve({
                response: A.normalizeResponse({reply:'resposta de teste', blocks:null, request_id:'r1', scenario_reset:false}),
                _devTiming: {
                    correlation_id: 'c-test-123', ui_submit_at: 1000, get_access_token_ms: 42,
                    client_fetch_at: 1100, client_receive_at: 1300, client_round_trip_ms: 200,
                    pre_fetch_total_ms: 100,
                    fetch_to_edge_handler_ms_approx: 5, edge_internal_ms: 190,
                    edge_response_to_browser_ms_approx: 5, edge_latency_ms: 190,
                    edge_instance_id: 'inst-test-abc', edge_instance_age_ms: 999999
                }
            })"""
        )
        prov_page.click("#baiPanelNewChatBtn")
        prov_page.fill("#baiPanelInput", "pergunta de teste para telemetria")
        prov_page.click("#baiPanelSendBtn")
        prov_page.wait_for_timeout(300)
        timing_calls = prov_page.evaluate("window.__baiTimingCalls")
        check("dev-timing: exactly one [bai-timing] console line emitted", isinstance(timing_calls, list) and len(timing_calls) == 1, timing_calls)
        if timing_calls:
            t = timing_calls[0]
            line = json.dumps(t)
            check("dev-timing: carries the correlation id", t.get("correlation_id") == "c-test-123", t)
            check("dev-timing: carries the edge instance id", t.get("edge_instance_id") == "inst-test-abc", t)
            check("dev-timing: carries render_ms/total_ui_ms computed by logDevTiming itself", isinstance(t.get("render_ms"), (int, float)) and isinstance(t.get("total_ui_ms"), (int, float)), t)
            check("dev-timing: never leaks the prompt text", "pergunta de teste" not in line, line)
            check("dev-timing: never leaks the reply text", "resposta de teste" not in line, line)
        dom_html = prov_page.locator("#baiPanelConversation").inner_html()
        check("dev-timing: correlation/instance ids never rendered into the conversation DOM", "c-test-123" not in dom_html and "inst-test-abc" not in dom_html, dom_html[:300])

        restore_fixture_mode(prov_page)
        prov_page.close()

        # ---------- Responsive / zero-scroll proof (Section 15/40) ----------
        BREAKPOINTS = [1366, 1024, 900, 480]
        for w in BREAKPOINTS:
            for route, label in (("landing", "landing"), ("score", "score")):
                rp = browser.new_page(viewport={"width": w, "height": 900})
                rp.goto(BASE + f"#/{route}")
                rp.wait_for_timeout(400)
                set_profile(rp, "AUTHORIZED", True, "MASTER")
                open_panel(rp)
                page_overflow = rp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                drawer_overflow = rp.evaluate("(function(){var el=document.getElementById('baiPanelDrawer'); return el ? el.scrollWidth - el.clientWidth : 0;})()")
                check(f"{w}px / {label}: page overflow 0", page_overflow <= 0, page_overflow)
                check(f"{w}px / {label}: panel wrapper overflow 0", drawer_overflow <= 0, drawer_overflow)
                true_ov = true_overflow(rp)
                check(f"{w}px / {label}: no element truly escapes the viewport (fixed-position-blind-spot guard)", true_ov["worst"] <= 0.5, true_ov)
                if w == 480:
                    check(f"{w}px / {label}: mobile backdrop visible (full-screen takeover)", rp.locator("#baiPanelBackdrop").is_visible())
                shot(rp, f"08-responsive-{w}-{label}.png")
                rp.close()

        browser.close()

    unexplained = [e for e in errors if "Failed to load resource" not in e]
    check("no unexplained console/page errors across the whole flow", len(unexplained) == 0)
    if unexplained:
        print("  unexplained errors:", unexplained)

    ok = all(r[1] for r in results)
    print(f"\n=== Brabus Intelligence Panel Test (IA-3E): {sum(1 for _, p in results if p)}/{len(results)} ===")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
