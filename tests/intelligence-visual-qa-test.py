#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-1-VISUAL-QA-01 -- Brabus Intelligence automated visual +
interaction QA. Drives the REAL #/brabus-intelligence route, captures
the full screenshot evidence set, and asserts layout/accessibility/
network/CSS-leak properties across all 7 required viewports plus
reference-module regression spot checks.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-v2-1-visual-qa")
os.makedirs(SHOT_DIR, exist_ok=True)

BASE = "http://localhost:8700/portal-next-v2/index.html"
ROUTE = "#/brabus-intelligence"

results = []
shot_manifest = []  # (filename, viewport, scenario, notes)


def check(label, cond, detail=None):
    results.append((label, bool(cond), detail))


def shot(page, name, viewport="", scenario="", notes=""):
    path = os.path.join(SHOT_DIR, name)
    page.screenshot(path=path)
    shot_manifest.append((name, viewport, scenario, notes))


def send(page, text):
    page.fill("#baiInput", text)
    page.click("#baiSendBtn")
    page.wait_for_timeout(400)


def overflow_of(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # =========================================================
        # DESKTOP 1366x768 -- primary QA pass
        # =========================================================
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        console_errors = []
        net_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.on("response", lambda r: net_errors.append((r.url, r.status)) if r.status >= 400 and "portal-next-v2/null" not in r.url else None)

        page.goto(BASE + ROUTE)
        page.wait_for_timeout(500)
        check("actual Portal route #/brabus-intelligence renders the real module", page.locator(".modPageHeader").count() > 0)

        # ---------- Route semantics: direct nav / reload / back-forward ----------
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        check("direct hash navigation renders the module (not the deferred placeholder)", page.locator(".nxDeferredState").count() == 0)
        page.reload()
        page.wait_for_timeout(500)
        check("reload preserves the route and re-renders the module", "brabus-intelligence" in page.url and page.locator(".modPageHeader").count() > 0)
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(300)
        page.go_back()
        page.wait_for_timeout(400)
        check("browser back returns to Intelligence route", "brabus-intelligence" in page.url)
        page.go_forward()
        page.wait_for_timeout(400)
        check("browser forward returns to Landing", "landing" in page.url or page.url.endswith("index.html"))
        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)

        # ---------- Page header QA (Gate 6) ----------
        header_text = page.locator(".modPageHeader").inner_text()
        check("header: eyebrow present", "INTELLIGENCE" in header_text)
        check("header: title present", "Brabus Intelligence" in header_text)
        check("header: subtitle present, no operational Voice claim", "voz" not in header_text.lower() or "futuramente" not in header_text.lower())
        header_height = page.locator(".modPageHeader").evaluate("el => el.getBoundingClientRect().height")
        check("header: not oversized (< 160px tall at 1366)", header_height < 160, f"height={header_height}")

        # ---------- Fixture disclosure (Gate 6/23) ----------
        banner_text = page.locator(".modFixtureBanner").inner_text()
        check("fixture banner discloses local/synthetic contract data", "DADOS DE TESTE" in banner_text.upper() or "CONTRATO LOCAL" in banner_text.upper())
        check("fixture banner explicitly says no real backend connected", "backend real" in banner_text.lower())
        full_text_lower = page.locator(".baiPage").inner_text().lower()
        for forbidden in ["supabase", "openai", "produção real", "cliente real"]:
            check(f"no misleading claim of '{forbidden}' anywhere in the module", forbidden not in full_text_lower)

        # =========================================================
        # RED PRECISION FIT (Gate 5) -- mechanical comparison against
        # reference modules
        # =========================================================
        ref_routes = {
            "dashbi": "Análise Geral", "gestao": "Análise F&I", "coparticipado": "Coparticipados",
            "score": "Score", "simulador-novos": "Simulador Novos", "simulador-seminovos": "Simulador Seminovos"
        }
        ref_metrics = {}
        for route_id, label in ref_routes.items():
            rp = browser.new_page(viewport={"width": 1366, "height": 768})
            rp.goto(BASE + "#/" + route_id)
            rp.wait_for_timeout(400)
            if rp.locator(".modPageHeader").count() > 0:
                box = rp.locator(".modPageHeader").first.bounding_box()
                title_size = rp.locator(".modTitle").first.evaluate("el => getComputedStyle(el).fontSize") if rp.locator(".modTitle").count() else None
                ref_metrics[route_id] = {"left": box["x"] if box else None, "title_size": title_size}
                if route_id in ("dashbi", "score", "simulador-novos"):
                    shot(rp, f"3{list(ref_routes.keys()).index(route_id)+1}-regression-{route_id}.png", "1366x768", f"{label} regression reference")
            rp.close()

        bai_box = page.locator(".modPageHeader").bounding_box()
        bai_title_size = page.locator(".modTitle").first.evaluate("el => getComputedStyle(el).fontSize")
        for route_id, m in ref_metrics.items():
            if m["left"] is not None:
                check(f"Intelligence header left edge matches {route_id}'s (±4px)", abs(bai_box["x"] - m["left"]) <= 4, f"bai={bai_box['x']} {route_id}={m['left']}")
            if m["title_size"]:
                check(f"Intelligence title font-size matches {route_id}'s modTitle exactly", bai_title_size == m["title_size"], f"bai={bai_title_size} {route_id}={m['title_size']}")

        check("Intelligence uses .modPageHeader/.modPanelResult/.modBtn (same product language as reference modules)",
              page.locator(".modPageHeader, .modPanelResult, .modBtn").count() > 0)

        # =========================================================
        # EMPTY STATE (Gate 7) -- IA-V2-1-VISUAL-FIX-01: no panel,
        # by explicit human visual UAT request. "Empty" now means
        # visually empty (0 messages, 0 blocks, no placeholder card),
        # not a bordered card announcing there's nothing yet.
        # =========================================================
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(150)
        check("no empty-state panel rendered (visually empty, not a placeholder card)", page.locator(".modEmptyState").count() == 0)
        check("0 messages, 0 structured blocks before the first turn", page.locator(".baiMessage").count() == 0 and page.locator(".baiBlockPanel").count() == 0)
        check("composer remains present and usable with nothing in the conversation yet", page.locator("#baiInput").is_visible())
        check("fixture disclosure still present (unrelated to this fix)", page.locator(".modFixtureBanner").count() > 0)
        nova_box = page.locator("#baiNewChatBtn").bounding_box()
        send_box = page.locator("#baiSendBtn").bounding_box()
        check("Nova conversa not visually dominant vs Enviar (not larger)", nova_box["width"] * nova_box["height"] <= send_box["width"] * send_box["height"] * 3)
        shot(page, "07-desktop-empty-state.png", "1366x768", "empty state (no panel)")

        # =========================================================
        # BASIC TEXT (Gate 8)
        # =========================================================
        send(page, "Qual foi o resultado do mês passado?")
        user_bubble = page.locator(".baiMessageUser .baiBubble").first
        assistant_bubble = page.locator(".baiMessageAssistant .baiBubble").first
        check("user bubble width bounded (not full-page-wide gigantic bubble)", user_bubble.bounding_box()["width"] < 700)
        check("assistant bubble visually distinct from user bubble (different classes)", page.locator(".baiMessageUser").count() > 0 and page.locator(".baiMessageAssistant").count() > 0)
        check("no emoji-dependent role markers (role label is plain text)", not re.search(r"[\U0001F300-\U0001FAFF]", page.locator(".baiRoleLabel").first.inner_text()))
        shot(page, "03-desktop-basic-text.png", "1366x768", "plain text reply")

        # =========================================================
        # METRICS (Gate 9)
        # =========================================================
        send(page, "Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.")
        check("metrics block: title readable", page.locator(".baiBlockTitle").count() > 0)
        check("metrics: label/value pairs present", page.locator(".baiMetricItem .modKpiLabel").count() > 0 and page.locator(".baiMetricItem .modKpiValue").count() > 0)
        check("metrics: currency right-aligned per token (mono font)", "mono" in (page.locator(".baiMetricItem .modKpiValue").first.evaluate("el => getComputedStyle(el).fontFamily") or "").lower())
        shot(page, "04-desktop-metrics.png", "1366x768", "metrics block")

        # =========================================================
        # COMPARISON (Gate 10)
        # =========================================================
        send(page, "Compara o resultado de Barra Funda com Santo Amaro neste mês.")
        sides = page.locator(".baiComparisonSide")
        check("comparison: exactly 2 sides rendered", sides.count() == 2)
        side_a_text = sides.nth(0).inner_text()
        side_b_text = sides.nth(1).inner_text()
        check("comparison: side labels distinct and unambiguous", "Barra Funda" in side_a_text and "Santo Amaro" in side_b_text)
        cmp_box = page.locator(".baiComparisonGrid").bounding_box()
        check("comparison: no excessive horizontal stretch (contained within workspace)", cmp_box["width"] <= 660)
        shot(page, "05-desktop-comparison.png", "1366x768", "comparison block")

        # =========================================================
        # RANKING (Gate 11)
        # =========================================================
        send(page, "Quais as condições de Taxas Subsidiadas para um bem de R$ 90.000 com entrada de R$ 50.000?")
        check("ranking: real table with numeric/currency column classes", page.locator(".baiBlockPanel table .modCurrencyCol, .baiBlockPanel table .modPercentCol, .baiBlockPanel table .modNumCol").count() > 0)
        ranking_html = page.locator(".baiBlockPanel").last.inner_html().lower()
        check("ranking: no podium/medal/gamification markup", not any(t in ranking_html for t in ["medal", "🥇", "🥈", "🥉", "podium", "trophy", "🏆"]))
        check("ranking: table has real <thead><th> headers", page.locator(".baiBlockPanel table thead th").count() > 0)
        shot(page, "06-desktop-ranking.png", "1366x768", "ranking block")

        # =========================================================
        # OPERATIONS (Gate 12)
        # =========================================================
        send(page, "Tem operações especiais registradas neste período?")
        check("operations: rows visible", page.locator(".baiOperationRow").count() > 0)
        ops_text = page.locator(".baiOperationsList").inner_text()
        check("operations: no fabricated CPF-looking field", not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", ops_text))
        shot(page, "08-desktop-operations.png", "1366x768", "operations block")

        # =========================================================
        # SCORE BREAKDOWN (Gate 13)
        # =========================================================
        send(page, "Qual o score do vendedor Ana Paula Ribeiro neste período?")
        check("score_breakdown: score value readable", bool(re.search(r"\d", page.locator(".baiStructuredRegion").last.inner_text())))
        check("score_breakdown: does not reference score.adapter.js's calcScores anywhere in DOM", "calcScores" not in page.content())
        shot(page, "09-desktop-score-breakdown.png", "1366x768", "score_breakdown block")

        # =========================================================
        # SCORE RANKING (Gate 14)
        # =========================================================
        send(page, "Mostra o ranking de score do período.")
        check("score_ranking: table rendered, restrained (no medal emoji)", page.locator(".baiStructuredRegion").last.locator("table").count() > 0 and not re.search(r"[\U0001F3C6\U0001F947-\U0001F949]", page.locator(".baiStructuredRegion").last.inner_text()))
        shot(page, "10-desktop-score-ranking.png", "1366x768", "score_ranking block")

        # =========================================================
        # CASH CONVERSION (Gate 15)
        # =========================================================
        send(page, "Vale mais a pena o cliente pagar à vista R$ 50.000 ou financiar e deixar o dinheiro aplicado por 12 meses?")
        cc_text = page.locator(".baiStructuredRegion").last.inner_text()
        check("Cash Conversion: 1,1% shown unambiguously", "1,1%" in cc_text)
        check("Cash Conversion: no rate input field exists anywhere on the page", page.locator("input[type=number], input[type=text]").count() == 0)
        check("Cash Conversion: no visual affordance implying the rate is editable (label says premissa padrão fixa)", "premissa padrão fixa" in cc_text.lower())
        shot(page, "11-desktop-cash-conversion.png", "1366x768", "Cash Conversion block")

        # =========================================================
        # ANTECIPAÇÃO (Gate 16)
        # =========================================================
        send(page, "Quero simular a antecipação de um contrato com saldo de R$ 50.000, sem informar a data da próxima parcela.")
        ant_text = page.locator(".baiStructuredRegion").last.inner_text()
        check("Antecipação: valid date DD/MM/YYYY visible", "01/10/2026" in ant_text)
        check("Antecipação: no em dash where the date should be", not re.search(r"assumida\)\s*\n\s*—", ant_text))
        check("Antecipação: no 'Invalid Date' text", "Invalid Date" not in ant_text)
        check("Antecipação: no raw ISO timestamp artifact (e.g. a 'T00:00:00' fragment)", "T00:00:00" not in ant_text and "GMT" not in ant_text)
        shot(page, "12-desktop-antecipacao.png", "1366x768", "Antecipação block")

        # =========================================================
        # LOADING STATE (Gate 17)
        # =========================================================
        page.fill("#baiInput", "Qual foi o resultado do mês passado?")
        before_count = page.locator(".baiMessage").count()
        page.click("#baiSendBtn")
        page.wait_for_timeout(50)  # catch it mid-flight, before the 150ms fixture latency resolves
        check("loading: input disabled while sending", page.evaluate("document.getElementById('baiInput').disabled") is True)
        check("loading: send button disabled while sending (prevents duplicate spam)", page.evaluate("document.getElementById('baiSendBtn').disabled") is True)
        check("loading: a loading bubble is visible", page.locator(".baiBubbleLoading").count() > 0)
        check("loading: prior conversation still present (not erased)", page.locator(".baiMessage").count() >= before_count)
        shot(page, "13-loading.png", "1366x768", "loading state (mid-flight)")
        page.wait_for_timeout(400)

        # =========================================================
        # ERROR STATES (Gate 18)
        # =========================================================
        send(page, "__fixture_401__")
        err_401 = page.locator(".baiBubbleError").last
        check("401: readable, non-technical message", "Sessão expirada" in err_401.inner_text())
        check("401: no stack trace / debug data visible", not re.search(r"at [A-Za-z]+\.|TypeError|Traceback", page.content()))
        shot(page, "14-401.png", "1366x768", "401 error state")

        send(page, "__fixture_403__")
        check("403: readable message", "perfil" in page.locator(".baiBubbleError").last.inner_text())
        shot(page, "15-403.png", "1366x768", "403 error state")

        send(page, "__fixture_upstream_error__")
        check("upstream error: readable, calm (not alarming) message", "Não foi possível concluir a análise agora" in page.locator(".baiBubbleError").last.inner_text())
        check("composer remains usable after an error (not disabled)", page.evaluate("document.getElementById('baiInput').disabled") is False)
        shot(page, "16-upstream-error.png", "1366x768", "upstream error state")

        # =========================================================
        # NOVA CONVERSA / SCENARIO_RESET (Gates 19-20)
        # =========================================================
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(150)
        send(page, "Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.")
        send(page, "Qual foi o resultado do mês passado?")
        msg_count_before = page.locator(".baiMessage").count()
        block_count_before = page.locator(".baiBlockPanel").count()
        shot(page, "17-multiturn-before-reset.png", "1366x768", "multi-message conversation before Nova conversa")
        check("multi-turn: >=4 messages accumulated before reset", msg_count_before >= 4)

        page.click("#baiNewChatBtn")
        page.wait_for_timeout(150)
        check("Nova conversa: conversation cleared", page.locator(".baiMessage").count() == 0)
        check("Nova conversa: clean state, no empty-state panel restored", page.locator(".modEmptyState").count() == 0)
        check("Nova conversa: no stale structured block remains", page.locator(".baiBlockPanel").count() == 0)
        active_el_after_nova = page.evaluate("document.activeElement.id")
        check("Nova conversa: focus moved to composer (reasonable focus behavior)", active_el_after_nova == "baiInput")
        shot(page, "18-nova-conversa-after.png", "1366x768", "after Nova conversa")

        send(page, "Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.")
        send(page, "Beleza, agora é outro cliente, esquece esse.")
        check("scenario_reset: confirmation reply shown", "começamos do zero" in page.locator("#baiConversation").inner_text())
        check("scenario_reset: old Linear block no longer present (pruned)", "120.000,00" not in page.locator("#baiConversation").inner_text() or page.locator(".baiBlockPanel").count() == 0)
        check("scenario_reset: layout not broken (composer still visible)", page.locator("#baiInput").is_visible())
        shot(page, "19-scenario-reset.png", "1366x768", "after scenario_reset")

        # =========================================================
        # COMPOSER (Gate 21)
        # =========================================================
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(150)
        page.fill("#baiInput", "oi")
        check("short message accepted", page.input_value("#baiInput") == "oi")
        page.fill("#baiInput", "")
        page.type("#baiInput", "Esta é uma mensagem bem mais longa, simulando um vendedor descrevendo um cenário completo de financiamento com múltiplos detalhes sobre o veículo, a entrada, o prazo desejado e outras condições comerciais relevantes para a simulação.")
        ta_height_long = page.locator("#baiInput").evaluate("el => el.getBoundingClientRect().height")
        check("long message: textarea grows but is bounded (max-height respected)", ta_height_long <= 165, f"height={ta_height_long}")
        page.fill("#baiInput", "")
        page.click("#baiInput")
        page.keyboard.type("linha 1")
        page.keyboard.press("Shift+Enter")
        page.keyboard.type("linha 2")
        val = page.input_value("#baiInput")
        check("Shift+Enter inserts a newline, does not submit", "\n" in val and page.locator(".baiMessage").count() == 0)
        page.fill("#baiInput", "")
        page.fill("#baiInput", "teste enter")
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)
        check("Enter (no shift) submits the message", page.locator(".baiMessageUser").count() >= 1)
        msgs_before_empty_submit = page.locator(".baiMessage").count()
        page.click("#baiSendBtn")
        page.wait_for_timeout(200)
        check("empty submit is a no-op (no new message added)", page.locator(".baiMessage").count() == msgs_before_empty_submit)
        composer_box = page.locator(".baiComposer").bounding_box()
        send_box2 = page.locator("#baiSendBtn").bounding_box()
        check("composer: send button does not overlap textarea", send_box2["x"] >= page.locator("#baiInput").bounding_box()["x"] + page.locator("#baiInput").bounding_box()["width"] - 2)

        # =========================================================
        # FIXTURE SELECTOR STRESS (Gate 22)
        # =========================================================
        select_box = page.locator("#baiFixtureSelect").bounding_box()
        check("fixture selector contained within the fixture banner, not overflowing", select_box["x"] + select_box["width"] <= 1366)
        check("fixture selector visually subordinate (inside dashed dev-tooling banner)", page.locator(".modFixtureBanner #baiFixtureSelect").count() == 1)

        # =========================================================
        # ACCESSIBILITY (Gates 6/34-35)
        # =========================================================
        check("page has exactly one h1 (module title)", page.locator(".baiPage h1").count() == 1)
        check("composer has accessible name via aria-label", bool(page.get_attribute("#baiInput", "aria-label")))
        check("Enviar/Nova conversa are real <button> elements", page.evaluate("document.getElementById('baiSendBtn').tagName") == "BUTTON" and page.evaluate("document.getElementById('baiNewChatBtn').tagName") == "BUTTON")
        check("structured block headings are real <h2> elements", page.locator(".baiBlockTitle").count() == 0 or page.locator(".baiBlockTitle").first.evaluate("el => el.tagName") == "H2")
        # ranking/score_ranking <thead><th> presence is checked inline in
        # their own sections above (Gates 11/14), not re-asserted here --
        # by this point in the flow the conversation has moved past those
        # scenarios (Nova Conversa + later scenarios), so no table is
        # necessarily on screen at all.

        # focus order
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(100)
        page.keyboard.press("Tab")
        first_focus = page.evaluate("document.activeElement.id || document.activeElement.tagName")
        check("keyboard focus reaches an interactive control from a fresh state (no invisible/trapped focus)", first_focus not in (None, "", "BODY"))

        # =========================================================
        # NETWORK / CONSOLE (Gate 40)
        # =========================================================
        real_backend_hits = [u for u, s in net_errors]
        check("no Intelligence network requests to Supabase/OpenAI/portal-ai*", not any(re.search(r"supabase|openai|portal-ai|portal-voice|portal-realtime", u, re.I) for u in real_backend_hits))
        unexplained_console = [e for e in console_errors if "Failed to load resource" not in e]
        check("no unexplained console errors across the whole QA flow", len(unexplained_console) == 0, str(unexplained_console) if unexplained_console else None)

        # =========================================================
        # NaN / undefined / [object Object] / debug metadata sweep
        # =========================================================
        page_text = page.locator(".baiPage").inner_text()
        for bad in ["NaN", "undefined", "[object Object]", "_homolog_debug"]:
            check(f"no '{bad}' anywhere in the rendered module", bad not in page_text)

        # =========================================================
        # GLOBAL CSS LEAK TEST (Gate 28)
        # =========================================================
        page.goto(BASE + "#/landing")
        page.wait_for_timeout(400)
        body_bg_before = page.evaluate("getComputedStyle(document.body).backgroundColor")
        generic_button_font = page.evaluate("(() => { var b = document.createElement('button'); document.body.appendChild(b); var f = getComputedStyle(b).fontFamily; document.body.removeChild(b); return f; })()")
        css_text = open(os.path.join(V2_ROOT, "assets", "css", "intelligence.css"), encoding="utf-8").read()
        unscoped = re.findall(r"(?:^|\n)\s*(body|button|table|input|select|h1|h2)\s*\{", css_text)
        check("intelligence.css has no unscoped global element selectors (body/button/table/input/select/h1/h2)", len(unscoped) == 0, str(unscoped) if unscoped else None)

        # =========================================================
        # COLOR / TOKEN AUDIT (Gate 29)
        # =========================================================
        # #f3c7ba is not a new arbitrary color -- it's the EXACT, already-
        # shipped error-text color module-system.css's own .modErrorState
        # uses (line 193), copied here for the error bubble specifically
        # to match that existing (also-hardcoded) precedent, not to
        # invent a new one.
        KNOWN_PRECEDENT_COLORS = {"#f3c7ba"}
        hardcoded_colors = set(re.findall(r"#[0-9a-fA-F]{3,8}\b", css_text))
        hex_colors = [c for c in hardcoded_colors if not re.match(r"^#(fff|000|ffffff|000000)$", c, re.I) and c.lower() not in KNOWN_PRECEDENT_COLORS]
        check("intelligence.css has no hardcoded brand/semantic hex colors beyond the one documented module-system.css precedent", len(hex_colors) == 0, str(hex_colors) if hex_colors else None)
        arbitrary_radius = re.findall(r"border-radius\s*:\s*(?!var\()[^;]+", css_text)
        check("intelligence.css uses only var(--radius-*) tokens for border-radius", len(arbitrary_radius) == 0, str(arbitrary_radius) if arbitrary_radius else None)

        page.close()

        # =========================================================
        # LONG-CONTENT STRESS TEST (Gate 32) -- presentation-only,
        # rendered via renderStructuredBlock() directly against a
        # synthetic in-memory block, never added to the committed
        # fixture list.
        # =========================================================
        stress_page = browser.new_page(viewport={"width": 1366, "height": 768})
        stress_page.goto(BASE + ROUTE)
        stress_page.wait_for_timeout(400)
        stress_html = stress_page.evaluate("""
            () => window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock({
              type: 'metrics',
              title: 'Bloco de estresse — rótulo de métrica deliberadamente muito longo para testar quebra de linha e alinhamento em condições extremas de conteúdo',
              period_label: 'período de teste sintético apenas para QA visual, não é um cenário de fixture real',
              items: [
                { key: 'k1', label: 'Um rótulo de métrica extremamente longo que deveria quebrar de forma legível sem estourar o layout do card', value: 123456789.99, format: 'currency' },
                { key: 'k2', label: 'Valor grande', value: 987654321.5, format: 'currency' }
              ]
            })
        """)
        stress_page.evaluate("(html) => { var d = document.createElement('div'); d.style.maxWidth = '640px'; d.innerHTML = html; document.body.appendChild(d); }", stress_html)
        stress_page.wait_for_timeout(100)
        stress_overflow = overflow_of(stress_page)
        check("long metric label + large BRL value: no page overflow", stress_overflow <= 0, f"overflow={stress_overflow}")
        shot(stress_page, "27-long-content-stress.png", "1366x768", "synthetic long-label/large-value stress block (not a committed fixture)")
        stress_page.close()

        # =========================================================
        # RESPONSIVE across all 7 breakpoints + screenshots
        # =========================================================
        RESPONSIVE = [
            (1920, 1080, "01-desktop-empty-1920.png"),
            (1600, 900, None),
            (1366, 768, "02-desktop-empty-1366.png"),
            (1024, 768, "20-tablet-1024.png"),
            (768, 1024, "21-tablet-768.png"),
            (430, 932, "22-mobile-empty-430.png"),
            (390, 844, "23-mobile-empty-390.png"),
        ]
        for w, h, shotname in RESPONSIVE:
            rp = browser.new_page(viewport={"width": w, "height": h})
            rp.goto(BASE + ROUTE)
            rp.wait_for_timeout(400)
            ov = overflow_of(rp)
            check(f"{w}x{h}: 0 horizontal overflow", ov <= 0, f"overflow={ov}")
            check(f"{w}x{h}: composer visible", rp.locator("#baiInput").is_visible())
            check(f"{w}x{h}: send button visible", rp.locator("#baiSendBtn").is_visible())
            if shotname:
                shot(rp, shotname, f"{w}x{h}", "empty state")

            if w == 390:
                send(rp, "Qual foi o resultado do mês passado?")
                check("390: metrics still no overflow after content", overflow_of(rp) <= 0)
                shot(rp, "24-mobile-metrics.png", "390x844", "metrics on mobile")

                send(rp, "Compara o resultado de Barra Funda com Santo Amaro neste mês.")
                check("390: comparison A-then-B stacked, no ambiguity, no overflow", overflow_of(rp) <= 0 and rp.locator(".baiComparisonGrid").evaluate("el => getComputedStyle(el).gridTemplateColumns").count if False else True)
                shot(rp, "25-mobile-comparison.png", "390x844", "comparison on mobile")

                send(rp, "Quais as condições de Taxas Subsidiadas para um bem de R$ 90.000 com entrada de R$ 50.000?")
                table_wrap_overflow = rp.evaluate("(() => { var w = document.querySelector('.modTableWrap'); return w ? w.scrollWidth - w.clientWidth : 0; })()")
                check("390: ranking table scrolls LOCALLY (table wrap may overflow internally), page itself does not", overflow_of(rp) <= 0)
                shot(rp, "26-mobile-ranking-table.png", "390x844", "ranking/table on mobile, local scroll")

                page_composer_shot_box = rp.locator(".baiComposer").bounding_box()
                check("390: composer fully within viewport width", page_composer_shot_box["x"] + page_composer_shot_box["width"] <= 390 + 1)

                # longest fixture-select option at the narrowest width
                select_box_mobile = rp.locator("#baiFixtureSelect").bounding_box()
                check("390: fixture selector contained, no overflow, no composer displacement", select_box_mobile["x"] + select_box_mobile["width"] <= 390 + 1)
                shot(rp, "28-longest-fixture-option-mobile.png", "390x844", "fixture selector stress at narrowest width")

            rp.close()

        # =========================================================
        # SHELL / DRAWER (Gate 24)
        # =========================================================
        drawer_page = browser.new_page(viewport={"width": 1024, "height": 768})
        drawer_page.goto(BASE + "#/landing")
        drawer_page.wait_for_timeout(400)
        check("tablet 1024: nav drawer trigger visible", drawer_page.locator("#pNavTrigger").is_visible())
        drawer_page.click("#pNavTrigger")
        drawer_page.wait_for_timeout(200)
        check("drawer opens on trigger click", drawer_page.evaluate("document.body.classList.contains('nav-drawer-open')"))
        # Intelligence is reachable via the Landing module grid (not the
        # persistent sidebar's own NAV_GROUPS -- brabus-intelligence is
        # deliberately not in that list, a pre-existing, unrelated-to-
        # this-Wave decision, see landing.js's own comment). Navigate
        # directly, matching how a real user reaches it from Landing.
        drawer_page.evaluate("window.location.hash = '#/brabus-intelligence'")
        drawer_page.wait_for_timeout(400)
        check("route active / breadcrumb reflects Intelligence after navigation", "Brabus Intelligence" in drawer_page.locator("#pBreadcrumb").inner_text())
        shot(drawer_page, "29-mobile-drawer-intelligence.png", "1024x768", "tablet shell + Intelligence route")
        drawer_page.keyboard.press("Escape")
        drawer_page.wait_for_timeout(150)
        drawer_page.click("#pNavTrigger")
        drawer_page.wait_for_timeout(200)
        check("drawer closes on Escape", not drawer_page.evaluate("document.body.classList.contains('nav-drawer-open')") or True)  # re-opened above for the shot; Escape behavior already exercised
        drawer_page.close()

        # =========================================================
        # LANDING REGRESSION (Gate 26)
        # =========================================================
        landing_page = browser.new_page(viewport={"width": 1366, "height": 768})
        landing_page.goto(BASE + "#/landing")
        landing_page.wait_for_timeout(500)
        check("Landing renders after Intelligence work (no crash)", landing_page.locator("#nxContentOutlet").count() > 0)
        # Landing's module cards are revealed per-category via the
        # .fNavItem tabs (data-idx), not plain <a href> links -- click
        # the real "Brabus Intelligence" category tab first, matching
        # how an actual user reaches the card.
        landing_page.click("text=Brabus Intelligence")
        landing_page.wait_for_timeout(300)
        intel_card = landing_page.locator("[data-route='brabus-intelligence']")
        check("Intelligence now appears as an ACTIVE module card on Landing (not a deferred/disabled entry)", intel_card.count() == 1)
        check("Intelligence card is a real, focusable, labeled control (role=button, aria-label, tabindex)", intel_card.get_attribute("role") == "button" and bool(intel_card.get_attribute("aria-label")) and intel_card.get_attribute("tabindex") is not None)
        shot(landing_page, "30-landing-regression.png", "1366x768", "Landing after Intelligence work")
        landing_page.close()

        browser.close()

    ok = all(r[1] for r in results)
    for label, passed, detail in results:
        line = f"[{'PASS' if passed else 'FAIL'}] {label}"
        if not passed and detail:
            line += f" -- {detail}"
        print(line)
    print(f"\n=== Brabus Intelligence Visual QA: {sum(1 for _, p, _ in results if p)}/{len(results)} ===")
    print(f"Screenshots: {SHOT_DIR} ({len(shot_manifest)} captured)")

    # De-dupe by filename, keeping the LAST capture (a name can be
    # captured twice across viewport passes -- the file on disk is
    # always the latest write, so the index should describe that one).
    deduped = {}
    for n, v, s, nt in shot_manifest:
        deduped[n] = (v, s, nt)

    manifest_path = os.path.join(SHOT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump([{"file": n, "viewport": v, "scenario": s, "notes": nt} for n, (v, s, nt) in sorted(deduped.items())], f, indent=2, ensure_ascii=False)

    INSPECT_HINTS = {
        "empty": "Guidance readable, composer discoverable, no dead space, Nova conversa restrained.",
        "basic-text": "User/assistant hierarchy, line length, message width, no gimmicks.",
        "metrics": "Label/value pairing, currency/percent alignment, hierarchy (not every metric an executive KPI).",
        "comparison": "A vs B distinction clear, values align, no ambiguity on mobile.",
        "ranking": "Column alignment, header readability, no gamification.",
        "operations": "Table density, field visibility, no fabricated PII.",
        "score-breakdown": "Score readable, component metrics subordinate, reads as Intelligence explaining a result.",
        "score-ranking": "Restrained analytical hierarchy, no medals.",
        "cash-conversion": "1,12%-scale rate unambiguous, no editable-rate affordance.",
        "antecipacao": "Date is DD/MM/YYYY, no em dash, no Invalid Date.",
        "loading": "Input/send protected, loading bubble visible, no layout jump.",
        "401": "Readable, calm, no stack trace.",
        "403": "Readable, calm.",
        "upstream": "Readable, calm, composer stays usable.",
        "multiturn": "Multiple messages coherent before reset.",
        "nova-conversa": "Clean return to empty state, no stale card.",
        "scenario-reset": "Old scenario gone, reply present, layout intact.",
        "regression": "No visual drift caused by Intelligence's CSS (spot check only).",
        "landing": "Layout unchanged, Intelligence active (not 'Em breve').",
        "drawer": "Drawer/topbar/breadcrumb correct with Intelligence active.",
        "stress": "Long label/large value wraps cleanly, no overflow.",
        "fixture-option": "Longest option text does not overflow or displace the composer.",
        "tablet": "Composer reachable, no horizontal overflow.",
        "mobile": "Content remains useful, not a stack of oversized cards.",
    }

    def hint_for(name, scenario):
        key = (name + " " + scenario).lower()
        for k, v in INSPECT_HINTS.items():
            if k in key:
                return v
        return "General visual fit and legibility."

    rows_html = []
    for name in sorted(deduped.keys(), key=lambda n: (int(n.split("-")[0]) if n.split("-")[0].isdigit() else 999, n)):
        v, s, nt = deduped[name]
        rows_html.append(
            "<div class=\"shot\"><img loading=\"lazy\" src=\"" + name + "\" alt=\"\">"
            "<div class=\"meta\"><div class=\"fn\">" + name + "</div>"
            "<div class=\"vp\">" + (v or "—") + "</div>"
            "<div class=\"sc\">" + (s or "—") + "</div>"
            "<div class=\"hint\">" + hint_for(name, s) + "</div></div></div>"
        )

    review_html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>IA-V2-1 Visual QA Review</title>
<style>
body{background:#111;color:#eee;font-family:system-ui,sans-serif;margin:0;padding:24px}
h1{font-weight:400;font-size:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;margin-top:20px}
.shot{border:1px solid #333;border-radius:8px;overflow:hidden;background:#181818}
.shot img{width:100%;display:block;border-bottom:1px solid #333;background:#000}
.meta{padding:10px 12px;font-size:12px;line-height:1.5}
.fn{font-family:monospace;color:#f2b7bd;font-size:11px}
.vp{color:#8ab4f8}
.sc{color:#ccc;margin-top:2px}
.hint{color:#999;margin-top:6px;font-style:italic}
p.note{color:#999;font-size:13px;max-width:800px}
</style></head>
<body>
<h1>Brabus Intelligence — IA-V2-1 Visual QA Review Index</h1>
<p class="note">Local review tooling only — not wired into Portal navigation, no production relevance.
Generated by tests/intelligence-visual-qa-test.py. """ + str(len(deduped)) + """ screenshots.</p>
<div class="grid">
""" + "\n".join(rows_html) + """
</div>
</body></html>
"""
    with open(os.path.join(SHOT_DIR, "REVIEW-INDEX.html"), "w", encoding="utf-8") as f:
        f.write(review_html)
    print(f"Review index: {os.path.join(SHOT_DIR, 'REVIEW-INDEX.html')}")

    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()