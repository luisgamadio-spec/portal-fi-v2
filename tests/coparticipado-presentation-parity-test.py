#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wave 3C Gate 33 -- Coparticipado presentation parity harness.

Goal: "presentation changed, business output unchanged." Same
philosophy as tests/simulador-novos-presentation-test.py: 0 hardcoded
expected field values -- everything the DOM shows is compared against
what window.NX_COPARTICIPADO_ADAPTER.compute() + its own money/pct/iso
formatting functions say it should show, computed live in the SAME
page the real render() calls. This validates the CURRENT markup
against the CURRENT adapter on every run (not a frozen snapshot), so
it keeps guarding presentation-vs-business parity for any future Wave
that touches coparticipado.js/.css, not just this one.

Covers both "Visão Coparticipados" and "Visão Subsidiados", across a
representative subset of tests/fixtures/coparticipado-fixtures.json
(the default "ALL" combined scenario plus a few edge cases: a normal
match, a missing-taxa warning row, and a non-PAGA/FATURADA status) --
record count, record order, and every rendered field value (including
the Situação badge's text, which must equal r.situacaoB3 with 0 added
text from the badge markup itself).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8700/portal-next-v2/index.html#/coparticipado"

CP_COPART_HEADERS = ['Cliente', 'Vendedor', 'Loja', 'Modelo Base', 'Modelo Taxa', 'Valor Financiado', 'Rebate Total', 'Parte Brabus', 'Valor Rebate Total', 'Coparticipação', 'Situação', 'Data', 'Chassi']
CP_SUBS_HEADERS = ['Cliente', 'Vendedor', 'Loja', 'Departamento', 'Modelo', 'Valor Financiado', 'Retorno', 'SPF Extra', 'Situação', 'Data', 'Chassi']

CASES = ['ALL', 'coparticipado_valido', 'modelo_sem_taxa', 'situacao_faturada', 'subsidiado']


def expected_rows(page, fixture_id, view):
    """Compute the expected rendered row set live via the real adapter
    -- same functions render() itself calls -- independent of the DOM."""
    return page.evaluate(
        """
        ([fixtureId, view, coHeaders, suHeaders]) => {
          const A = window.NX_COPARTICIPADO_ADAPTER;
          const fd = window.__CP_TEST_FIXTURES__;
          const input = fixtureId === 'ALL'
            ? (() => {
                let vendorRows = [], taxasCopart = {}, b1Rows = [], b2Rows = [], b3Rows = [];
                const seen = {};
                fd.forEach(c => {
                  (c.vendorRows || []).forEach(v => { const k = v.NBS || v.Nome; if (seen[k]) return; seen[k] = true; vendorRows.push(v); });
                  Object.assign(taxasCopart, c.taxasCopart || {});
                  b1Rows = b1Rows.concat(c.b1Rows || []);
                  b2Rows = b2Rows.concat(c.b2Rows || []);
                  b3Rows = b3Rows.concat(c.b3Rows || []);
                });
                return { vendorRows, taxasCopart, b1Rows, b2Rows, b3Rows };
              })()
            : (() => { const c = fd.filter(x => x.id === fixtureId)[0];
                return { vendorRows: c.vendorRows, taxasCopart: c.taxasCopart, b1Rows: c.b1Rows, b2Rows: c.b2Rows, b3Rows: c.b3Rows }; })();
          const result = A.compute(input);
          const plano = view === 'SUBSIDIADO' ? 'SUBSIDIADO' : 'COPARTICIPADO';
          const rows = result.fins.filter(r => r.plano === plano);
          const headers = view === 'SUBSIDIADO' ? suHeaders : coHeaders;
          function fmtCopart(r) {
            const c = r.coparticipacaoDetalhe || A.calcCoparticipacaoDetalhe(r);
            return [
              r.cliente, r.vendedor, r.loja, r.modelo,
              c.modeloTabela ? c.modeloTabela : 'Não encontrado',
              A.money(r.valorFinanciado),
              c.ok ? A.pct(c.rebateTotal) : '—',
              c.ok ? A.pct(c.parteBrabus) : '—',
              c.ok ? A.money(c.valorRebateTotal) : '—',
              c.ok ? A.money(c.coparticipacao) : 'Modelo não encontrado',
              r.situacaoB3 || '', A.iso(r.data), r.chassi
            ];
          }
          function fmtSubs(r) {
            return [
              r.cliente, r.vendedor, r.loja, r.dept, r.modelo,
              A.money(r.valorFinanciado), A.money(r.retorno), A.money(r.receitaSPF),
              r.situacaoB3 || '', A.iso(r.data), r.chassi
            ];
          }
          return { headers, values: rows.map(view === 'SUBSIDIADO' ? fmtSubs : fmtCopart) };
        }
        """,
        [fixture_id, view, CP_COPART_HEADERS, CP_SUBS_HEADERS],
    )


def dom_rows(page):
    """Extract the ACTUAL rendered rows -- same DOM whether the CSS is
    currently painting it as a desktop table or a mobile card, since
    the transform is CSS-only (Gate 20/21): one <tr>/<td> markup, one
    read here covers both presentations. Excludes the single-cell
    "Nenhum ... encontrado" empty-state placeholder row (colspan'd,
    not a real record)."""
    return page.evaluate(
        """
        () => {
          const table = document.querySelector('#cpPanel table');
          if (!table) return [];
          return Array.from(table.querySelectorAll('tbody tr'))
            .filter(tr => tr.children.length > 1)
            .map(tr => Array.from(tr.children).map(td => td.textContent.trim()));
        }
        """
    )


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(500)

        # expose the raw fixture list once, mirroring how coparticipado.js
        # itself loads it, so expected_rows() can build any scenario
        # without re-fetching per case.
        page.evaluate(
            """
            () => fetch('tests/fixtures/coparticipado-fixtures.json').then(r => r.json()).then(d => { window.__CP_TEST_FIXTURES__ = d.cases; })
            """
        )
        page.wait_for_timeout(300)

        for fixture_id in CASES:
            page.select_option("#cpFixtureSelect", fixture_id)
            page.wait_for_timeout(200)

            for view, tab_id in (("COPARTICIPADO", "cpTabCopart"), ("SUBSIDIADO", "cpTabSubs")):
                page.click(f"#{tab_id}")
                page.wait_for_timeout(150)

                exp = expected_rows(page, fixture_id, view)
                actual = dom_rows(page)
                exp_values = exp["values"]

                name = f"{fixture_id}::{view}"
                if len(actual) != len(exp_values):
                    results.append((name, False, f"row count mismatch: dom={len(actual)} expected={len(exp_values)}"))
                    continue
                mismatch = None
                for i, (a_row, e_row) in enumerate(zip(actual, exp_values)):
                    if a_row != e_row:
                        mismatch = f"row {i}: dom={a_row} expected={e_row}"
                        break
                results.append((name, mismatch is None, mismatch))

        if errors:
            print("[FATAL] page errors:", errors)
            sys.exit(1)
        browser.close()

    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== Coparticipado Presentation Parity: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
