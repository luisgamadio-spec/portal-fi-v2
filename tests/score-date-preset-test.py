#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score (Análise de Score Vendedores) -- local-calendar-safe date-preset
correction, sibling to FI-UX-1's own Gestão/Dashbi fix (tests/fi-ux-1-
date-preset-test.py), which explicitly left Score untouched at the time
("This is NOT the same defect as Score's own known UTC-boundary issue --
Score is untouched by this wave.").

ROOT CAUSE (confirmed by direct source read of assets/js/score.js, not
assumed): computePreset() constructs `start`/`end` as local-time Date
objects (via new Date(year, month, day) or the raw "now" object for
`end`), then formats them with `.toISOString().slice(0, 10)` -- a UTC
serialization of a local-time value. Score's OWN pre-existing todayIso()
(used only for the manual/custom date-range default) already used the
correct local-calendar pattern (getFullYear/getMonth/getDate, no UTC
roundtrip); computePreset() simply never reused it. Fix: a shared
localIso(d) helper (matching the exact pattern already proven in
coparticipado.js's localIso() (FC-2.4) and gestao.js/dashbi.js's own
FI-UX-1 fix), used by both todayIso() and computePreset().

This test suite reuses the EXACT technique already established and
proven in tests/fi-ux-1-date-preset-test.py: a fake, pinned window.Date
(fixed_date_script) for clock independence, and Playwright's own
`timezone_id` context option for real cross-timezone execution (not
merely reasoning about it) -- both required by this wave's own brief
(Gates 13/17/34).

SAFETY: 0 real network calls (RPC fully routed/mocked), 0 real Supabase
project touched, synthetic data only. Requires a static server for
PORTAL-FI-DESIGN-LAB/ on the project's canonical port 8080.
"""
import io
import json as _json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_score-real-provider-harness.html"
RPC_URL = "https://mock.invalid/rest/v1/rpc/operational_score_coparticipated_data"

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


def fixed_date_script(y, m, d, hh=10, mm=0):
    # Identical technique to tests/fi-ux-1-date-preset-test.py's own
    # fixed_date_script -- not reinvented.
    return """
        (function() {
            var FIXED = new Date(%d, %d, %d, %d, %d, 0);
            var OrigDate = Date;
            function FakeDate() {
                if (arguments.length === 0) return new OrigDate(FIXED.getTime());
                return new (Function.prototype.bind.apply(OrigDate, [null].concat(Array.prototype.slice.call(arguments))))();
            }
            FakeDate.prototype = OrigDate.prototype;
            FakeDate.now = function() { return FIXED.getTime(); };
            window.Date = FakeDate;
        })();
    """ % (y, m - 1, d, hh, mm)


def auth_mock_script(configured=True, token="mock-access-token-abc"):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: %s, getAccessToken: function () { return Promise.resolve(%s); } };
""" % ("true" if configured else "false", ("'" + token + "'") if token else "null")


EMPTY_PAYLOAD = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-01-01",
    "contains_client_identity": False, "contains_personal_documents": False, "contains_full_chassis": False,
    "sales": [], "finance": [], "rates": []
}


def mount(browser, date_script=None, timezone_id=None, capture=None):
    ctx = {"viewport": {"width": 1366, "height": 900}}
    if timezone_id:
        ctx["timezone_id"] = timezone_id
    page = browser.new_page(**ctx)
    page.add_init_script(auth_mock_script())
    if date_script:
        page.add_init_script(date_script)

    def handler(route):
        if capture is not None:
            capture["body"] = _json.loads(route.request.post_data or "{}")
        route.fulfill(status=200, content_type="application/json", body=_json.dumps(EMPTY_PAYLOAD))
    page.route(RPC_URL + "*", handler)
    page.goto(BASE)
    page.wait_for_function("!!window.NX_SCORE_PAGE", timeout=5000)
    page.evaluate("window.NX_SCORE_PAGE.render(document.getElementById('scOutlet'))")
    page.wait_for_timeout(200)
    return page


# (label, fixed today, expected currentMonth, expected lastMonth, expected last6-start, expected lastYear-start)
CASES = [
    ("CASE A 2026-09-05", (2026, 9, 5), ("2026-09-01", "2026-09-05"), ("2026-08-01", "2026-08-31"), "2026-04-01", "2025-09-05"),
    ("CASE B 2026-01-05", (2026, 1, 5), ("2026-01-01", "2026-01-05"), ("2025-12-01", "2025-12-31"), "2025-08-01", "2025-01-05"),
    ("CASE C 2026-03-01", (2026, 3, 1), ("2026-03-01", "2026-03-01"), ("2026-02-01", "2026-02-28"), "2025-10-01", "2025-03-01"),
    ("CASE D 2028-03-01 (leap)", (2028, 3, 1), ("2028-03-01", "2028-03-01"), ("2028-02-01", "2028-02-29"), "2027-10-01", "2027-03-01"),
    ("CASE E 2026-05-31", (2026, 5, 31), ("2026-05-01", "2026-05-31"), ("2026-04-01", "2026-04-30"), "2025-12-01", "2025-05-31"),
]


def run(playwright):
    browser = playwright.chromium.launch()
    try:
        # ================= A-E: month/leap/boundary matrix =================
        for label, (y, m, d), exp_current, exp_last, exp_last6_start, exp_lastyear_start in CASES:
            cap = {}
            page = mount(browser, date_script=fixed_date_script(y, m, d), capture=cap)

            page.click(".scPresetBtn[data-preset='currentMonth']")
            page.wait_for_timeout(150)
            got_current = (page.eval_on_selector("#scDateStart", "e=>e.value"), page.eval_on_selector("#scDateEnd", "e=>e.value"))
            check("Score %s: Mês atual == %s" % (label, exp_current), got_current == exp_current)
            check("Score %s: RPC (p_start/p_end) matches the displayed dates -- PROVIDER ARGUMENT PROOF" % label,
                  cap.get("body", {}).get("p_start") == got_current[0] and cap.get("body", {}).get("p_end") == got_current[1])

            page.click(".scPresetBtn[data-preset='lastMonth']")
            page.wait_for_timeout(150)
            got_last = (page.eval_on_selector("#scDateStart", "e=>e.value"), page.eval_on_selector("#scDateEnd", "e=>e.value"))
            check("Score %s: Mês anterior == %s" % (label, exp_last), got_last == exp_last)

            page.click(".scPresetBtn[data-preset='last6']")
            page.wait_for_timeout(150)
            got_last6 = (page.eval_on_selector("#scDateStart", "e=>e.value"), page.eval_on_selector("#scDateEnd", "e=>e.value"))
            check("Score %s: Últimos 6 meses start == %s, end == today" % (label, exp_last6_start), got_last6 == (exp_last6_start, exp_current[1]))

            page.click(".scPresetBtn[data-preset='lastYear']")
            page.wait_for_timeout(150)
            got_lastyear = (page.eval_on_selector("#scDateStart", "e=>e.value"), page.eval_on_selector("#scDateEnd", "e=>e.value"))
            check("Score %s: Último ano start == %s, end == today" % (label, exp_lastyear_start), got_lastyear == (exp_lastyear_start, exp_current[1]))
            page.close()

        # ================= CRITICAL BOUNDARY CASE F: UTC-3 (America/Sao_Paulo), 22:30 local =================
        # This is the SAME defect class already fixed in Gestão/Dashbi
        # (tests/fi-ux-1-date-preset-test.py CASE F). Under the CURRENT
        # (pre-fix) code, `end` stays the raw "now" Date object -- at
        # 22:30 local in UTC-3, .toISOString() shifts it to the NEXT
        # calendar day (2026-09-06), one day forward. Expected (fixed):
        # stays 2026-09-05.
        page = mount(browser, date_script=fixed_date_script(2026, 9, 5, hh=22, mm=30), timezone_id="America/Sao_Paulo")
        page.click(".scPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Score CASE F (UTC-3, America/Sao_Paulo, 22:30 local): Mês atual end stays 2026-09-05 (not shifted to 2026-09-06)",
              page.eval_on_selector("#scDateEnd", "e=>e.value") == "2026-09-05")
        page.close()

        # ================= CRITICAL BOUNDARY CASE G: UTC+14 (Pacific/Kiritimati), 00:30 local =================
        # `start` is constructed via new Date(Y, M, 1) at LOCAL midnight,
        # then .toISOString()'d -- in a positive-offset zone, local
        # midnight is BEHIND UTC by the offset, shifting the calendar day
        # BACKWARD (2026-05-31 instead of 2026-06-01) under the CURRENT
        # (pre-fix) code. Expected (fixed): stays 2026-06-01. This proves
        # the START side of the defect, not just the END side proven by
        # CASE F -- computePreset()'s bug affects EVERY branch (Gate 10).
        page = mount(browser, date_script=fixed_date_script(2026, 6, 1, hh=0, mm=30), timezone_id="Pacific/Kiritimati")
        page.click(".scPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Score CASE G (UTC+14, Pacific/Kiritimati, 00:30 local): Mês atual start stays 2026-06-01 (not shifted to 2026-05-31)",
              page.eval_on_selector("#scDateStart", "e=>e.value") == "2026-06-01")
        page.close()

        # ================= Manual/custom date-range path (Gate 27): untouched, must remain unchanged =================
        page = mount(browser, date_script=fixed_date_script(2026, 9, 5))
        page.click(".scPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Score: preset shows active state", page.eval_on_selector(".scPresetBtn[data-preset='currentMonth']", "e=>e.classList.contains('modSegItemActive')"))
        page.fill("#scDateStart", "2026-01-01")
        page.eval_on_selector("#scDateStart", "e => e.dispatchEvent(new Event('change'))")
        page.wait_for_timeout(150)
        check("Score: manual date edit clears the active preset state", not page.eval_on_selector(".scPresetBtn[data-preset='currentMonth']", "e=>e.classList.contains('modSegItemActive')"))
        check("Score: manual date value is respected (not overwritten back), proving the custom path is untouched by this fix", page.eval_on_selector("#scDateStart", "e=>e.value") == "2026-01-01")
        page.close()

        # ================= Manual default (todayIso(), Gate 27): still correct after the localIso() refactor =================
        page = mount(browser, date_script=fixed_date_script(2026, 9, 5, hh=23, mm=45))
        got_default_end = page.eval_on_selector("#scDateEnd", "e=>e.value")
        check("Score: default #scDateEnd (todayIso(), refactored to call localIso()) still correct at 23:45 local == 2026-09-05",
              got_default_end == "2026-09-05")
        page.close()

        browser.close()
    except Exception:
        browser.close()
        raise


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        run(p)
    failed = [r for r in results if not r[1]]
    print("\n%d passed, %d failed" % (len(results) - len(failed), len(failed)))
    if failed:
        print("FAILED:")
        for label, _ in failed:
            print(" -", label)
        sys.exit(1)
