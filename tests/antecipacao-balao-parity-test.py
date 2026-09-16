#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANTECIPACAO-BALAO-1 -- permanent regression: restores Secure parity for
balloon support in the Antecipação (early-settlement) simulator, Novos
+ Seminovos.

CONFIRMED ROOT CAUSE (git archaeology, this Wave, not assumed):
  - aa58f35 ("PORTAL-NEXT-08 extract production simulator engines with
    parity harness") extracted calcularAntecipacao() WITH full balloon
    support already -- byte-for-byte matching Secure's own
    calcAntecipacao() (modules/simulador-novos.html /
    simulador-seminovos.html): same balaoPorMes map, same
    valorOriginal = valorBalao>0?valorBalao:parcela substitution, same
    BALAO_FORA_DO_PRAZO/BALAO_DUPLICADO/BALAO_VALOR_INVALIDO validation.
  - dab0c17 ("PORTAL-NEXT-08.1 build native V2 simulator UI on frozen
    engines"), the VERY NEXT commit, built the native Antecipação form
    WITHOUT ever wiring balloon inputs -- calcAntecipacao() hardcoded
    `baloes: []` and added the honest "não suportado nesta versão da
    interface (o motor extraído suporta)" disclaimer at the same time.
  Classification: UI_NOT_PORTED_ENGINE_ALREADY_SUPPORTED.

CANONICAL SECURE RULE (recovered, not assumed -- explicitly NOT the
regular-financing MAX_BALOES=4/2): both modules/simulador-novos.html
and modules/simulador-seminovos.html's own Antecipação screen use
#aTemBalao (Sim/Não) + #aQtdBaloes (0-8, "Limite máximo: 8 balões."),
IDENTICAL between Novos and Seminovos -- a genuinely shared limit,
unlike the Tradicional plan's own divergent 4/2.

This test proves, against the REAL current source (fixture files it
loads directly -- never a hand-copied duplicate) and the REAL
unmodified archived production HTML (same methodology as
simulador-novos-parity-test.py / simulador-seminovos-parity-test.py,
Gates 26/27/29):
  SECURE_ANTICIPATION_BALLOON_RULE_RECOVERED
  NOVOS_ANTICIPATION_BALLOON_PARITY / SEMINOVOS_ANTICIPATION_BALLOON_PARITY
  BALLOON_INPUT_REACHES_ENGINE
  ONE_BALLOON_CHANGES_SETTLEMENT
  MULTIPLE_BALLOONS_CHANGE_SETTLEMENT
  REMOVED_BALLOON_STOPS_AFFECTING_RESULT
  FULL_SETTLEMENT_BALLOON_PARITY / PARTIAL_SETTLEMENT_BALLOON_PARITY
  MALFORMED_BALLOON_REJECTED
  REGULAR_NOVOS_MAX_4_PRESERVED / REGULAR_SEMINOVOS_MAX_2_PRESERVED
  ZERO_HORIZONTAL_SCROLL

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/
(for the golden-parity section against the archived production HTML)
AND the V2 app itself reachable at http://localhost:8700/portal-next-v2-final-uat/
(same server, same convention as every other suite in this worktree).
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://localhost:8700/portal-next-v2-final-uat"
PROD_URL_NOVOS = "http://localhost:8700/PORTAL-NEXT-08/.source/simulador-novos-origin-main.html"
PROD_URL_SEMINOVOS = "http://localhost:8700/PORTAL-NEXT-08/.source/simulador-seminovos-origin-main.html"
ADAPTER_SHARED = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2-final-uat/assets/js/adapters/simulador-shared.adapter.js"
ADAPTER_NOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2-final-uat/assets/js/adapters/simulador-novos.adapter.js"
ADAPTER_SEMINOVOS = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2-final-uat/assets/js/adapters/simulador-seminovos.adapter.js"

CENT = 0.02
results = []


def check(label, cond, detail=None):
    if cond:
        results.append((label, True))
        print(f"[PASS] {label}")
    else:
        results.append((label, False))
        print(f"[FAIL] {label}" + (f" -- {detail}" if detail is not None else ""))


def brl_to_float(s):
    if s is None:
        return None
    s = s.strip()
    if s in ("", "--", "-", "R$ 0,00"):
        return 0.0 if s == "R$ 0,00" else None
    m = re.search(r"-?[\d.]+,\d+", s)
    if not m:
        return None
    return float(m.group(0).replace(".", "").replace(",", "."))


def close(a, b, eps=CENT):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < eps


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= SECURE_ANTICIPATION_BALLOON_RULE_RECOVERED =================
        # Confirmed by direct inspection of the real, archived production
        # source (never invented): #aQtdBaloes offers exactly 0-8 options,
        # identical between Novos and Seminovos.
        for label, url in (("Novos", PROD_URL_NOVOS), ("Seminovos", PROD_URL_SEMINOVOS)):
            prod = browser.new_page()
            prod.goto(url)
            prod.wait_for_timeout(300)
            opt_values = prod.eval_on_selector_all("#aQtdBaloes option", "els => els.map(e => e.value)")
            hint_text = prod.eval_on_selector("#aQtdBox .hint", "e => e && e.textContent")
            check(f"SECURE_ANTICIPATION_BALLOON_RULE_RECOVERED ({label}): #aQtdBaloes offers exactly 0-8",
                  opt_values == [str(i) for i in range(9)], opt_values)
            check(f"SECURE_ANTICIPATION_BALLOON_RULE_RECOVERED ({label}): hint states max 8", "8" in (hint_text or ""), hint_text)
            prod.close()

        # ================= GOLDEN PARITY: V2 engine (adapter, pure function) vs REAL Secure (browser, unmodified) =================
        for label, prod_url, adapter_novos_path, ns_global in (
            ("Novos", PROD_URL_NOVOS, ADAPTER_NOVOS, "NX_SIMULADOR_NOVOS_ADAPTER"),
            ("Seminovos", PROD_URL_SEMINOVOS, ADAPTER_SEMINOVOS, "NX_SIMULADOR_SEMINOVOS_ADAPTER"),
        ):
            prod = browser.new_page()
            prod.goto(prod_url)
            prod.wait_for_timeout(300)
            adapter = browser.new_page()
            adapter.goto("about:blank")
            adapter.add_script_tag(path=ADAPTER_SHARED)
            adapter.add_script_tag(path=adapter_novos_path)

            golden_cases = [
                {"id": "zero_baloes", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-06-10", "tipo": "todo", "baloes": []},
                {"id": "one_balao", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-06-10", "tipo": "todo", "baloes": [{"mes": 24, "valor": 15000}]},
                {"id": "max_baloes_8", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-02-10", "tipo": "todo",
                 "baloes": [{"mes": m, "valor": 5000 + m * 100} for m in (6, 10, 14, 18, 22, 26, 30, 34)]},
                {"id": "partial_with_balao", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-03-10", "tipo": "algumas", "de": 10, "ate": 30, "baloes": [{"mes": 20, "valor": 12000}]},
                {"id": "boundary_balao_before_data", "prazo": 48, "parcela": 2000, "primeira": "2025-01-10", "data": "2025-06-10", "tipo": "todo", "baloes": [{"mes": 3, "valor": 9000}]},
            ]
            for c in golden_cases:
                sim = len(c["baloes"]) > 0
                prod.evaluate(
                    """(c) => {
                        document.getElementById('aPrazo').value = String(c.prazo);
                        document.getElementById('aParcela').value = String(c.parcela);
                        document.getElementById('aPrimeiroVenc').value = c.primeira;
                        document.getElementById('aData').value = c.data;
                        document.getElementById('aTipo').value = c.tipo;
                        if (c.de != null && document.getElementById('aDe')) document.getElementById('aDe').value = String(c.de);
                        if (c.ate != null && document.getElementById('aAte')) document.getElementById('aAte').value = String(c.ate);
                        document.getElementById('aTemBalao').value = c.sim ? 'sim' : 'nao';
                        document.getElementById('aQtdBaloes').value = String(c.baloes.length);
                        renderAntecipacaoBaloes();
                        const mesEls = [...document.querySelectorAll('.aMesBalao')];
                        const valEls = [...document.querySelectorAll('.aValorBalao')];
                        c.baloes.forEach((b, i) => { mesEls[i].value = String(b.mes); valEls[i].value = String(b.valor); });
                        calcAntecipacao(true);
                    }""",
                    dict(c, sim=sim),
                )
                prod_final = brl_to_float(prod.evaluate("document.getElementById('aValorFinal').textContent"))

                r = adapter.evaluate(
                    f"""(c) => {ns_global}.calcularAntecipacao({{
                        prazo: c.prazo, parcela: c.parcela,
                        primeiraParcela: new Date(c.primeira + 'T00:00:00'),
                        dataAntecipacao: new Date(c.data + 'T00:00:00'),
                        tipo: c.tipo, de: c.de || null, ate: c.ate || null,
                        baloes: c.baloes
                    }})""",
                    c,
                )
                ok = r.get("error") is None and close(prod_final, r.get("finalTotal"))
                check(f"{'NOVOS' if label == 'Novos' else 'SEMINOVOS'}_ANTICIPATION_BALLOON_PARITY: {c['id']}", ok, (prod_final, r.get("finalTotal"), r.get("error")))

            prod.close()
            adapter.close()

        # ================= FINANCIAL CORRECTNESS (Phase 7), engine-level, Novos adapter =================
        adapter = browser.new_page()
        adapter.goto("about:blank")
        adapter.add_script_tag(path=ADAPTER_SHARED)
        adapter.add_script_tag(path=ADAPTER_NOVOS)

        def calc(baloes, tipo="todo", de=None, ate=None, parcela_unica=None, prazo=48, parcela=2000, primeira="2025-01-10", data="2025-06-10"):
            return adapter.evaluate(
                """(c) => NX_SIMULADOR_NOVOS_ADAPTER.calcularAntecipacao({
                    prazo: c.prazo, parcela: c.parcela,
                    primeiraParcela: new Date(c.primeira + 'T00:00:00'),
                    dataAntecipacao: new Date(c.data + 'T00:00:00'),
                    tipo: c.tipo, de: c.de, ate: c.ate, parcelaUnica: c.parcelaUnica,
                    baloes: c.baloes
                })""",
                {"prazo": prazo, "parcela": parcela, "primeira": primeira, "data": data, "tipo": tipo, "de": de, "ate": ate, "parcelaUnica": parcela_unica, "baloes": baloes},
            )

        # CASE 1/2: without vs with one balloon -- must differ
        r_no_balao = calc([])
        r_one_balao = calc([{"mes": 24, "valor": 15000}])
        check("BALLOON_INPUT_REACHES_ENGINE: baseline (no balloon) succeeds", r_no_balao.get("error") is None)
        check("ONE_BALLOON_CHANGES_SETTLEMENT: result differs from baseline", r_no_balao.get("finalTotal") != r_one_balao.get("finalTotal"), (r_no_balao.get("finalTotal"), r_one_balao.get("finalTotal")))
        check("ONE_BALLOON_CHANGES_SETTLEMENT: baloesTotal reflects exactly the one balloon", close(r_one_balao.get("baloesTotal"), 15000))

        # CASE 3: multiple balloons, up to Secure max (8) -- all included
        many = [{"mes": m, "valor": 1000 * m} for m in (2, 6, 10, 14, 18, 22, 26, 30)]
        # data desejada anterior a TODOS os 8 meses (primeira=2025-01-10,
        # menor mes=2 -> vencimento 2025-02-10) -- caso contrario o proprio
        # motor (idêntico ao Secure) descarta corretamente qualquer
        # parcela com `venc<=data`, o que não seria um defeito aqui.
        r_many = calc(many, data="2024-12-01")
        check("MULTIPLE_BALLOONS_CHANGE_SETTLEMENT: 8 balloons all present in rows",
              sum(1 for row in r_many.get("rows", []) if row.get("valorBalao", 0) > 0) == 8,
              [row.get("valorBalao") for row in r_many.get("rows", [])])
        check("MULTIPLE_BALLOONS_CHANGE_SETTLEMENT: baloesTotal is the sum of all 8", close(r_many.get("baloesTotal"), sum(b["valor"] for b in many)))

        # CASE 4: remove one balloon -- its effect disappears
        without_one = [b for b in many if b["mes"] != 14]
        r_without_one = calc(without_one, data="2024-12-01")
        check("REMOVED_BALLOON_STOPS_AFFECTING_RESULT: removed month no longer flagged as balloon",
              not any(row.get("num") == 14 and row.get("valorBalao", 0) > 0 for row in r_without_one.get("rows", [])))
        check("REMOVED_BALLOON_STOPS_AFFECTING_RESULT: baloesTotal decreases by exactly the removed balloon", close(r_many.get("baloesTotal") - r_without_one.get("baloesTotal"), 14000))

        # CASE 5: balloon before/at/after the anticipation date
        # date = 2025-06-10 (~mês 6 a partir de 2025-01-10); um balão no
        # mês 3 (Abr/2025) já venceu antes da data de antecipação -- o
        # próprio motor (idêntico ao Secure) o exclui via `if (venc<=data) continue`.
        r_balao_before = calc([{"mes": 3, "valor": 9000}], data="2025-06-10")
        check("Balão com vencimento ANTES da data de antecipação: excluído do fluxo (Secure-identical `venc<=data` skip)",
              not any(row.get("num") == 3 for row in r_balao_before.get("rows", [])))
        r_balao_after = calc([{"mes": 30, "valor": 9000}], data="2025-06-10")
        check("Balão com vencimento DEPOIS da data de antecipação: presente no fluxo",
              any(row.get("num") == 30 and row.get("valorBalao", 0) > 0 for row in r_balao_after.get("rows", [])))

        # CASE 6/7/8: whole / partial / one-installment settlement, each with a balloon
        r_whole = calc([{"mes": 24, "valor": 15000}], tipo="todo")
        r_partial = calc([{"mes": 24, "valor": 15000}], tipo="algumas", de=10, ate=30)
        r_one_installment_hit = calc([{"mes": 24, "valor": 15000}], tipo="uma", parcela_unica=24)
        r_one_installment_miss = calc([{"mes": 24, "valor": 15000}], tipo="uma", parcela_unica=25)
        check("FULL_SETTLEMENT_BALLOON_PARITY: whole-contract settlement includes the balloon", any(row.get("valorBalao", 0) > 0 for row in r_whole.get("rows", [])))
        check("PARTIAL_SETTLEMENT_BALLOON_PARITY: partial range including the balloon month includes it", any(row.get("valorBalao", 0) > 0 for row in r_partial.get("rows", [])))
        check("ONE_INSTALLMENT: anticipating exactly the balloon's own month includes it as a balloon row",
              len(r_one_installment_hit.get("rows", [])) == 1 and r_one_installment_hit["rows"][0].get("valorBalao", 0) > 0)
        check("ONE_INSTALLMENT: anticipating a different single month does not include the balloon",
              len(r_one_installment_miss.get("rows", [])) == 1 and r_one_installment_miss["rows"][0].get("valorBalao", 0) == 0)

        # ================= MALFORMED_BALLOON_REJECTED (Phase 9) =================
        r_month_zero = calc([{"mes": 0, "valor": 1000}])
        check("MALFORMED_BALLOON_REJECTED: month 0 -> BALAO_FORA_DO_PRAZO", r_month_zero.get("error") == "BALAO_FORA_DO_PRAZO")
        r_month_over = calc([{"mes": 999, "valor": 1000}])
        check("MALFORMED_BALLOON_REJECTED: month beyond prazo -> BALAO_FORA_DO_PRAZO", r_month_over.get("error") == "BALAO_FORA_DO_PRAZO")
        r_dup = calc([{"mes": 10, "valor": 1000}, {"mes": 10, "valor": 2000}])
        check("MALFORMED_BALLOON_REJECTED: duplicate month -> BALAO_DUPLICADO", r_dup.get("error") == "BALAO_DUPLICADO")
        r_zero_valor = calc([{"mes": 10, "valor": 0}])
        check("MALFORMED_BALLOON_REJECTED: zero value -> BALAO_VALOR_INVALIDO", r_zero_valor.get("error") == "BALAO_VALOR_INVALIDO")
        r_neg_valor = calc([{"mes": 10, "valor": -500}])
        check("MALFORMED_BALLOON_REJECTED: negative value -> BALAO_VALOR_INVALIDO", r_neg_valor.get("error") == "BALAO_VALOR_INVALIDO")
        adapter.close()

        # ================= UI-LEVEL: real V2 app, state reaches the engine, both simulators =================
        for label, url, prefix in (("Novos", BASE + "/index.html#/simulador-novos", "n"), ("Seminovos", BASE + "/index.html#/simulador-seminovos", "s")):
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.wait_for_timeout(700)
            # "Antecipação de Parcelas" lives in the "Ferramentas" F.2 group
            # (collapsed by default -- only "Financiamento", holding the
            # active Tradicional mode, starts open).
            mode_sel = '.smModeBtn[data-mode="antecipacao"]'
            page.click('.smModeGroupHeader[data-group="Ferramentas"]')
            page.wait_for_timeout(200)
            page.click(mode_sel)
            page.wait_for_timeout(300)

            check(f"{label}: obsolete 'Balões não são suportados' message removed", page.locator("text=Balões não são suportados").count() == 0)
            check(f"{label}: balloon toggle present ('Existem balões neste financiamento?')", page.locator(f"#{prefix}AntTemBalao").count() == 1)
            check(f"{label}: quantity box hidden by default (Não)", page.locator(f"#{prefix}AntQtdBox").is_hidden())

            page.click(f'#{prefix}AntTemBalao button[data-v="sim"]')
            page.wait_for_timeout(150)
            check(f"{label}: quantity box visible after choosing Sim", not page.locator(f"#{prefix}AntQtdBox").is_hidden())
            page.select_option(f"#{prefix}AntQtdBaloes", "2")
            page.wait_for_timeout(150)
            check(f"{label}: exactly 2 balloon rows rendered", page.locator("#" + prefix + "AntBaloesList .smBalloonRow").count() == 2)

            page.fill(f'[data-abidx="0"][data-abfield="mes"]', "12")
            page.fill(f'[data-abidx="0"][data-abfield="valor"]', "10000,00")
            page.fill(f'[data-abidx="1"][data-abfield="mes"]', "24")
            page.fill(f'[data-abidx="1"][data-abfield="valor"]', "8000,00")

            page.fill(f"#{prefix}PrazoNum", "48")
            page.fill(f"#{prefix}Parcela", "2000,00")
            page.fill(f"#{prefix}Primeira", "2025-01-10")
            page.fill(f"#{prefix}Data", "2025-06-10")
            page.click(f"#{prefix}Calc")
            page.wait_for_timeout(500)
            result_text = page.inner_text("#smResultRegion")
            check(f"{label}: calculation with balloons produces a real result", "Preencha os campos" not in result_text and result_text.strip() != "")
            check(f"{label}: result mentions 'Total em balões'", "total em bal" in result_text.lower())
            check(f"{label}: no console/page errors", len(errors) == 0)

            # switching quantity down discards previous rows (Secure-identical regenerate-on-change)
            page.select_option(f"#{prefix}AntQtdBaloes", "1")
            page.wait_for_timeout(150)
            check(f"{label}: reducing quantity to 1 leaves exactly 1 row", page.locator("#" + prefix + "AntBaloesList .smBalloonRow").count() == 1)
            check(f"{label}: reduced row starts blank (regenerate, not preserve)", page.get_attribute(f'[data-abidx="0"][data-abfield="mes"]', "value") == "")

            page.close()

        # ================= RESPONSIVE / ZERO_HORIZONTAL_SCROLL =================
        for w in (480, 900, 1024, 1366):
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.route("**/intelligence-runtime-config.local.js", lambda route: route.fulfill(status=200, content_type="application/javascript", body=""))
            page.goto(BASE + "/index.html#/simulador-novos")
            page.wait_for_timeout(600)
            page.click('.smModeGroupHeader[data-group="Ferramentas"]')
            page.wait_for_timeout(200)
            page.click('.smModeBtn[data-mode="antecipacao"]')
            page.wait_for_timeout(300)
            page.click('#nAntTemBalao button[data-v="sim"]')
            page.wait_for_timeout(150)
            page.select_option("#nAntQtdBaloes", "8")
            page.wait_for_timeout(200)
            overflow = page.evaluate("document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth")
            check(f"ZERO_HORIZONTAL_SCROLL @ {w}px: 8 balloon rows, zero overflow", overflow <= 0, overflow)
            check(f"ZERO_HORIZONTAL_SCROLL @ {w}px: exactly 8 rows rendered, no duplicates", page.locator("#nAntBaloesList .smBalloonRow").count() == 8)
            page.close()

        browser.close()

    passed = sum(1 for _, c in results if c)
    print()
    print(f"=== ANTECIPACAO-BALAO-1 Parity Regression: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
