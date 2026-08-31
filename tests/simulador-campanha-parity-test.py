#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gates 22/26/27/49 — Financiamento Campanha/Coparticipado engine parity
(PORTAL-NEXT-08).

Drives BOTH the decoded Novos and decoded Seminovos base64 campaign
iframes (saved locally, byte-diff-confirmed identical this Wave except
var/const and an unrelated telemetry hook -- see
docs/SIMULATOR-ENGINE-DISCOVERY-08.md Gate 22/49) and compares each
against V2's pure re-derivation
(assets/js/adapters/financiamento-campanha.adapter.js).

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

NOVOS_URL = "http://localhost:8700/PORTAL-NEXT-08/.source/novos-campanha-iframe-decoded.html"
SEMINOVOS_URL = "http://localhost:8700/PORTAL-NEXT-08/.source/seminovos-campanha-iframe-decoded.html"
ADAPTER = "C:/Projetos/PORTAL-FI-DESIGN-LAB/portal-next-v2/assets/js/adapters/financiamento-campanha.adapter.js"

CENT = 0.01


def brl_to_float(s):
    if s is None or s.strip() in ("", "—", "-"):
        return None
    m = re.search(r"-?[\d.]+,\d+", s)
    return float(m.group(0).replace(".", "").replace(",", "")) / 100 if m else None


def close(a, b, eps=CENT):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < eps


CASES = [
    {"id": "eclipse_at_min_60pct", "model": "ECLIPSE CROSS HPE-S S-AWC", "sale": 200000, "entry": 120000},
    {"id": "eclipse_above_min", "model": "ECLIPSE CROSS HPE-S S-AWC", "sale": 200000, "entry": 150000},
    {"id": "eclipse_below_min_invalid", "model": "ECLIPSE CROSS HPE-S S-AWC", "sale": 200000, "entry": 100000},
    {"id": "triton_hpe", "model": "TRITON HPE", "sale": 180000, "entry": 108000},
    {"id": "outlander_signature", "model": "OUTLANDER SIGNATURE", "sale": 320000, "entry": 192000},
    {"id": "zero_entry", "model": "TRITON GLS AT", "sale": 150000, "entry": 0},
    {"id": "large_value", "model": "ECLIPSE CROSS HPE-S S-AWC BLACK", "sale": 900000, "entry": 540000},
]


def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        adapter = browser.new_page()
        adapter.goto("about:blank")
        adapter.add_script_tag(path=ADAPTER)

        for label, url in [("Novos-iframe", NOVOS_URL), ("Seminovos-iframe", SEMINOVOS_URL)]:
            page = browser.new_page()
            page.goto(url)
            page.wait_for_timeout(200)
            for c in CASES:
                page.evaluate(
                    """(c) => {
                        document.getElementById('model').value = c.model;
                        document.getElementById('saleValue').value = fmtBRL.format(c.sale);
                        document.getElementById('entryValue').value = fmtBRL.format(c.entry);
                        calc();
                    }""",
                    c,
                )
                prod_final = brl_to_float(page.evaluate("document.getElementById('finalSale').textContent"))
                prod_financed = brl_to_float(page.evaluate("document.getElementById('financedValue').textContent"))
                prod_terms = page.evaluate(
                    "[...document.querySelectorAll('#terms .payment')].map(e => e.textContent)"
                )
                prod_payments = [brl_to_float(x) for x in prod_terms]

                r = adapter.evaluate(
                    "(c) => NX_CAMPANHA_ADAPTER.compute({model: c.model, saleValue: c.sale, entryValue: c.entry})",
                    c,
                )
                adapter_payments = [t["payment"] for t in r["terms"]]

                # calc()'s own `financed` is genuinely 0 (not null) when invalid --
                # the '—' is purely a *display* choice (valid?fmtBRL.format(financed):'—'),
                # so a blank prod display legitimately corresponds to a real
                # financed=0 in both the original and the adapter, not a mismatch.
                financed_ok = close(prod_financed, r.get("financed")) or (prod_financed is None and r.get("financed") == 0)

                ok = (
                    close(prod_final, r.get("finalSale"))
                    and financed_ok
                    and len(prod_payments) == len(adapter_payments)
                    and all(close(a, b) for a, b in zip(prod_payments, adapter_payments))
                )
                results.append((f"{label}/{c['id']}", ok, prod_final, r.get("finalSale")))
            page.close()

        adapter.close()
        browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    for name, ok, pv, av in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  prod={pv!r} adapter={av!r}")
    print(f"\n=== Financiamento Campanha Parity: {passed}/{len(results)} ===")
    print("RESULT:", "PASS" if passed == len(results) else "FAIL")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
