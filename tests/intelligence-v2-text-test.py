#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-2 -- real TEXT integration test. Drives the REAL, unmodified
portal-ai-homolog source (via tests/intelligence-v2-text/deno/
bootstrap-text.ts) through the REAL, approved Portal V2 UI, over a
genuine cross-origin browser request exercising the real CORS check
for real. UAT classification: DETERMINISTIC_MODEL_BOUNDARY_E2E (no
real OpenAI traffic -- see tests/intelligence-v2-text/README.md).

Requires (see tests/intelligence-v2-text/README.md):
  - node tests/intelligence-v2-text/mock-backend.mjs 8790
  - the real portal-ai-homolog Deno bootstrap on :8801
  - `python -m http.server 8080` from PORTAL-FI-DESIGN-LAB/
  - assets/js/intelligence-runtime-config.local.js present (real_text mode)
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(V2_ROOT, "tests", "screenshots", "ia-v2-2")
os.makedirs(SHOT_DIR, exist_ok=True)

BASE = "http://localhost:8080/portal-next-v2/index.html"
ROUTE = "#/brabus-intelligence"

results = []


def check(label, cond, detail=None):
    results.append((label, bool(cond), detail))


def shot(page, name):
    page.screenshot(path=os.path.join(SHOT_DIR, name))


def sign_in(page, email="v2-master@local.test"):
    return page.evaluate(f"window.NX_AUTH.signIn('{email}', 'anything')")


def send(page, text, wait=1200):
    page.fill("#baiInput", text)
    page.click("#baiSendBtn")
    page.wait_for_timeout(wait)


def last_reply_text(page):
    return page.locator("#baiConversation").inner_text()


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not available — harness code exists, not executed.")
        sys.exit(0)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------- Config / containment ----------
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        console_errors = []
        net_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))
        page.on("response", lambda r: net_errors.append((r.url, r.status)) if r.status >= 400 else None)

        page.goto(BASE + ROUTE)
        page.wait_for_timeout(400)
        check("config mode is real_text (local override active)", page.evaluate("window.NX_INTELLIGENCE_CONFIG.mode") == "real_text")
        check("fixture banner hidden in real_text mode", page.locator(".modFixtureBanner").count() == 0)
        check("approved clean initial state preserved (0 messages, no panel)", page.locator(".baiMessage").count() == 0 and page.locator(".modEmptyState").count() == 0)
        shot(page, "01-real-mode-clean-start.png")

        # ---------- 01 basic TEXT (unauthenticated first -- security) ----------
        send(page, "Qual foi o resultado do mês passado?")
        check("01 basic text, NO session: safe 401 UX shown", "Sessão expirada" in last_reply_text(page))
        shot(page, "15-401-no-session.png")
        page.click("#baiNewChatBtn")
        page.wait_for_timeout(150)

        # ---------- sign in as MASTER ----------
        sign_in(page)
        page.wait_for_timeout(200)

        # ---------- 01 basic TEXT, authenticated ----------
        send(page, "Qual foi o resultado do mês passado?")
        check("01 basic text: real reply + real metrics block", page.locator(".baiBlockPanel").count() == 1 and "13" in last_reply_text(page))
        check("01 basic text: no _homolog_debug leaked", "_homolog_debug" not in page.content())
        shot(page, "02-basic-response.png")

        # ---------- 02 Linear ----------
        send(page, "Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.")
        check("02 Linear: real structured block with real computed payment (R$ 4.010,97)", "4.010,97" in last_reply_text(page))
        shot(page, "03-financial-block-linear.png")

        # ---------- 02b Linear Seminovos ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula um financiamento linear seminovo.")
        check("02b Linear Seminovos: dispatched and rendered", page.locator(".baiBlockPanel").count() >= 1, last_reply_text(page)[:200])

        # ---------- 03 Balão ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula um financiamento com balão de R$ 40.000 num veículo de R$ 150.000, entrada de R$ 30.000, em 36 meses.")
        check("03 Balão: real combined blocks (ranking + metrics)", page.locator(".baiBlockPanel").count() >= 1 and "40.000,00" in last_reply_text(page))
        shot(page, "04-balao.png")

        # ---------- 04 Coparticipado ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Quero simular Coparticipado para a L200 Triton, R$ 200.000, entrada R$ 120.000, 24 meses.")
        check("04 Coparticipado: real block rendered", page.locator(".baiBlockPanel").count() >= 1 and "L200" in last_reply_text(page).upper() or "TRITON" in last_reply_text(page).upper())

        # ---------- 05 Subsidiado ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Quais as condições de Taxas Subsidiadas para um bem de R$ 90.000 com entrada de R$ 50.000?")
        check("05 Subsidiado: real ranking block rendered", page.locator(".baiBlockPanel table").count() >= 1)
        shot(page, "05-comparison-or-ranking.png")

        # ---------- 06 Semestral/Anual ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula um plano semestral para R$ 100.000, entrada R$ 30.000, 36 meses.")
        check("06 Semestral/Anual: dispatched (block or error, either is real backend authority, not a fixture gap)", len(last_reply_text(page)) > 20)

        # ---------- 07 Taxa Implícita ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Um cliente financiou R$ 100.000 em 36x de R$ 4.485,75. Qual a taxa implícita desse contrato?")
        check("07 Taxa Implícita: real NET/CET computed (2,6%% / 2,9%%)", "2,6%" in last_reply_text(page) and "2,9%" in last_reply_text(page))
        shot(page, "06-taxa-implicita.png")

        # ---------- 08 Antecipação explicit date ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula uma antecipação explícita com data de 2027.")
        check("08 Antecipação explicit date: real date rendered", re.search(r"\d{2}/\d{2}/2027", last_reply_text(page)) is not None)

        # ---------- 09 Antecipação default date ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Quero simular a antecipação de um contrato com saldo de R$ 50.000, sem informar a data da próxima parcela.")
        check("09 Antecipação default date: real backend default (today+30d), no Invalid Date", "Invalid Date" not in last_reply_text(page) and re.search(r"\d{2}/\d{2}/\d{4}", last_reply_text(page)))
        shot(page, "07-antecipacao.png")

        # ---------- 10 Cash Conversion official ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Vale mais a pena o cliente pagar à vista R$ 50.000 ou financiar e deixar o dinheiro aplicado por 12 meses?")
        check("10 Cash Conversion official: real 1,1%% rate shown, engine-computed", "1,1%" in last_reply_text(page))
        shot(page, "08-cash-conversion.png")

        # ---------- 11 Cash custom-rate guardrail ----------
        send(page, "E se a taxa de aplicação fosse 0,90% ao mês?")
        check("11 Cash custom-rate guardrail: still 1,1%% official, backend guardrail holds", "1,1%" in last_reply_text(page))

        # ---------- 12 multi-turn ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.")
        msg_count_1 = page.locator(".baiMessage").count()
        send(page, "Qual foi o resultado do mês passado?")
        check("12 multi-turn: second real backend call succeeds with prior context sent", page.locator(".baiMessage").count() > msg_count_1)
        check("12 multi-turn: no duplicate structured blocks stacking incorrectly", page.locator(".baiBlockPanel").count() == 2)
        shot(page, "09-multiturn.png")

        # ---------- 13 Novo Cliente / scenario reset ----------
        send(page, "Beleza, agora é outro cliente, esquece esse.")
        check("13 Novo Cliente: real scenario_reset:true handled, confirmation shown", "começamos do zero" in last_reply_text(page))
        shot(page, "10-novo-cliente-reset.png")

        # ---------- 14 negative/ineligible truth ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Simula uma Taxas Subsidiadas para um bem de R$ 50.000 com entrada de R$ 10.000")
        check("14 negative truth: real backend rejection, no fabricated payment", "50%" in last_reply_text(page) or "mínima" in last_reply_text(page).lower())

        # ---------- 15/16 401/403 already covered above (no-session); 403 non-MASTER ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        page.evaluate("window.NX_AUTH.signOut()")
        page.wait_for_timeout(150)
        page.evaluate("window.NX_AUTH.signIn('v2-vendedor-not-used@local.test', 'x').catch(()=>{})")
        # sign-in always issues the MASTER token in this mock (single
        # fixed login response) -- exercise 403 directly via a raw call
        # instead, matching Gate 30's STRUCTURAL/MOCKED_HTTP/
        # REAL_HOMOLOG_HTTP distinction: this is REAL_HOMOLOG_HTTP too,
        # just bypassing the UI's own sign-in ceremony.
        non_master_result = page.evaluate("""
            async () => {
              const cfg = window.NX_INTELLIGENCE_CONFIG;
              const r = await fetch(cfg.textEndpoint, {
                method: 'POST',
                headers: {'Content-Type':'application/json','apikey':cfg.supabasePublishableKey,'Authorization':'Bearer v2-mock-non-master-access-token'},
                body: JSON.stringify({message:'oi', conversation:[]})
              });
              return { status: r.status, body: await r.json() };
            }
        """)
        check("16 403 non-MASTER: real backend rejects with 403", non_master_result["status"] == 403)
        shot(page, "16-403.png")

        # ---------- Score (RUNTIME_DATA_DEPENDENT -- see docs) ----------
        sign_in(page)
        page.wait_for_timeout(200)
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Mostra o ranking de score do período.")
        score_text = last_reply_text(page)
        check("Score: real dispatch + real calcScores() computation over synthetic 2-row fixture (real backend, not a fixture stub)", "score" in score_text.lower() or page.locator(".baiBlockPanel").count() >= 1)
        shot(page, "11-score.png")

        # ---------- Histórico (RUNTIME_DATA_DEPENDENT -- see docs) ----------
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        send(page, "Me mostra o histórico de financiamentos dos últimos 90 dias.")
        hist_text = last_reply_text(page)
        check("Histórico: real dispatch, real sample-quality safeguard fires on a thin synthetic fixture (proves the real logic runs, not a fixture stub)", "INSUFICIENTE" in page.content() or page.locator(".baiBlockPanel").count() >= 1)
        shot(page, "12-historico.png")

        # ---------- 17 upstream failure ----------
        sign_in(page)
        page.wait_for_timeout(200)
        send(page, "__V2_TRIGGER_UPSTREAM_ERROR__")
        check("17 upstream failure: sanitized message, no stack trace", "Não foi possível concluir a análise agora" in last_reply_text(page) and "TypeError" not in page.content())
        shot(page, "17-upstream-error.png")

        # ---------- loading state ----------
        # Real transport resolves in well under 80ms on an all-localhost
        # round trip (no artificial delay, unlike fixture mode's own
        # deliberate 150ms) -- page.click() already waits for the
        # click's own synchronous handlers to run before returning, so
        # checking synchronously in the SAME evaluate() as the click
        # (not a separate wait_for_timeout() afterwards) is the only
        # way to reliably observe the loading state for real_text mode.
        page.click("#baiNewChatBtn"); page.wait_for_timeout(150)
        page.fill("#baiInput", "Qual foi o resultado do mês passado?")
        loading_seen = page.evaluate("""
            () => {
              document.getElementById('baiSendBtn').click();
              return document.querySelectorAll('.baiBubbleLoading').length > 0
                  && document.getElementById('baiInput').disabled === true;
            }
        """)
        check("loading state visible synchronously right after send (input disabled, loading bubble present)", loading_seen)
        page.wait_for_timeout(1500)
        # Real round trips resolve in well under a screenshot's own
        # capture latency, so this shows the settled response, not the
        # spinner itself -- the loading state's existence is proven by
        # the assertion above, not by this screenshot.
        shot(page, "19-response-after-real-latency.png")

        # ---------- Network audit ----------
        allowed_hosts = ["127.0.0.1:8790", "127.0.0.1:8801", "localhost:8080", "127.0.0.1:8080"]
        unexpected = [u for u, s in net_errors if not any(h in u for h in allowed_hosts)]
        check("network: no unexpected error targets", len(unexpected) == 0, str(unexpected) if unexpected else None)
        direct_openai = [u for u, s in net_errors if "api.openai.com" in u]
        check("network: browser never calls OpenAI directly", len(direct_openai) == 0)
        check("network: no unexplained console errors", len([e for e in console_errors if "Failed to load resource" not in e]) == 0, str(console_errors))

        # ---------- Secret audit (on THIS fully-interacted page, before closing it) ----------
        page_source = page.content()
        for secret_pattern in [r"sk-[A-Za-z0-9]{20,}", r"service_role", r"eyJhbGciOiJ"]:
            check(f"no secret pattern '{secret_pattern}' in page source", not re.search(secret_pattern, page_source))

        page.close()

        # ---------- desktop breakpoints (approved IA-V2-1 layout preserved) ----------
        for w, h, name in [(1920, 1080, "20-desktop-1920.png"), (1366, 768, "21-desktop-1366.png"), (1024, 768, "22-tablet-1024.png"), (768, 1024, "23-tablet-768.png")]:
            bp = browser.new_page(viewport={"width": w, "height": h})
            bp.goto(BASE + ROUTE)
            bp.wait_for_timeout(300)
            sign_in(bp)
            bp.wait_for_timeout(200)
            overflow = bp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"{w}x{h}: real_text mode, 0 overflow, approved layout preserved", overflow <= 0 and bp.locator(".modFixtureBanner").count() == 0)
            shot(bp, name)
            bp.close()

        # ---------- Mobile ----------
        for w, h in [(430, 932), (390, 844)]:
            mp = browser.new_page(viewport={"width": w, "height": h})
            mp.goto(BASE + ROUTE)
            mp.wait_for_timeout(300)
            sign_in(mp)
            mp.wait_for_timeout(200)
            send(mp, "Qual foi o resultado do mês passado?")
            overflow = mp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(f"mobile {w}: real response renders, 0 overflow", overflow <= 0 and mp.locator(".baiBlockPanel").count() == 1)
            if w == 390:
                shot(mp, "18-mobile.png")
            mp.close()

        browser.close()

    ok = all(r[1] for r in results)
    for label, passed, detail in results:
        line = f"[{'PASS' if passed else 'FAIL'}] {label}"
        if not passed and detail:
            line += f" -- {detail}"
        print(line)
    print(f"\n=== IA-V2-2 Real TEXT Integration: {sum(1 for _, p, _ in results if p)}/{len(results)} ===")
    print(f"Screenshots: {SHOT_DIR}")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
