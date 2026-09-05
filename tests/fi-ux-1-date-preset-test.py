#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FI-UX-1 (Human-reported defect B) -- deterministic date-preset tests for
Gestão (Análise F&I do Grupo, gestao.js) and Dashbi (Análise Geral do
Grupo, dashbi.js).

ROOT CAUSE (confirmed by direct source read + git blame, not assumed):
both applyPresetAndRender() functions read `var today = new Date(2026, 7,
30)` UNCONDITIONALLY -- a fixed reference date introduced at each
module's own original fixture-only migration (7808b6b for Gestão,
df67013 for Dashbi), before real-data transport existed, never branched
when real transport was added later. "Mês atual" therefore always
resolved to 01/08->30/08 in REAL mode too, regardless of the genuine
current date. Fix: `today = isRealTransport() ? new Date() : <the same
fixed reference date>` -- fixture mode's own deterministic behavior is
UNCHANGED (explicitly tested below), only real mode now uses the genuine
local date. A NEW localIso() in each file (small, independently
duplicated, matching the FC-2.4 precedent) replaces `.toISOString()` for
formatting, avoiding the separate (already-known, NOT fixed here) UTC
calendar-shift class of defect.

This is NOT the same defect as Score's own known UTC-boundary issue --
Score is untouched by this wave.

Requires: a static server for PORTAL-FI-DESIGN-LAB/ on port 8080.
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

GESTAO_BASE = "http://127.0.0.1:8080/portal-next-v2/tests/fixtures/_gestao-real-provider-harness.html"
GESTAO_RPC = "https://mock.invalid/rest/v1/rpc/operational_fandi_dashboard"
DASHBI_BASE = "http://127.0.0.1:8080/portal-next-v2/tests/_dashbi-real-provider-harness.html"
DASHBI_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_metrics"
DASHBI_MODEL_METRICS_URL = "https://mock.invalid/rest/v1/rpc/operational_model_metrics"

results = []


def check(label, cond):
    results.append((label, bool(cond)))
    print(("PASS" if cond else "FAIL") + " - " + label)


def fixed_date_script(y, m, d, hh=10, mm=0):
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


def gestao_auth_script(configured):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: %s, getAccessToken: function () { return Promise.resolve('mock-access-token-abc'); } };
window.NX_AUTH_CORE = { getContext: function () { return {isMaster:true,perfil:'MASTER',loja:null}; }, reportSessionExpired: function () {} };
""" % ("true" if configured else "false")


def dashbi_auth_script(configured):
    return """
window.NX_INTELLIGENCE_CONFIG = { mode: 'fixture', supabaseUrl: 'https://mock.invalid', supabasePublishableKey: 'mock-anon-key', textEndpoint: null };
window.NX_AUTH = { isAuthConfigured: %s, getAccessToken: function () { return Promise.resolve('mock-access-token-abc'); } };
""" % ("true" if configured else "false")


GESTAO_EMPTY_PAYLOAD = {
    "scope": {}, "period": {}, "filters": {}, "source": {},
    "summary": {"operational_quantity": 0, "total_financed": 0},
    "stores": [], "banks": [], "status_by_store": [], "status_by_bank": [],
    "plans": [], "plans_by_store_department": [], "spf_extra": [], "proposal_outcomes": []
}
DASHBI_EMPTY_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "eligibility_rule": "ACTIVE_VENDEDOR_ONLY", "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}
DASHBI_EMPTY_MODEL_METRICS = {
    "scope": {"profile": "MASTER", "is_master": True}, "period_start": "2026-01-01", "period_end": "2026-09-03",
    "contains_personal_documents": False, "contains_client_identity": False, "contains_chassis": False,
    "entry_rule": "SUM_ENTRY_DIV_VALID_OPERATIONS", "entry_percent_rule": "SUM_ENTRY_DIV_SUM_SALE_VALUE",
    "plan_priority_rule": "SUBSIDIADO_REVERSAO_COPARTICIPADO_BALAO_LINEAR",
    "rows": []
}


def mount_gestao_real(browser, date_script=None, timezone_id=None, capture=None):
    ctx = {"viewport": {"width": 1366, "height": 900}}
    if timezone_id:
        ctx["timezone_id"] = timezone_id
    page = browser.new_page(**ctx)
    page.add_init_script(gestao_auth_script(True))
    if date_script:
        page.add_init_script(date_script)

    def handler(route):
        if capture is not None:
            capture["body"] = json.loads(route.request.post_data or "{}")
        route.fulfill(status=200, content_type="application/json", body=json.dumps(GESTAO_EMPTY_PAYLOAD))
    page.route(GESTAO_RPC + "*", handler)
    page.goto(GESTAO_BASE)
    page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
    page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
    page.wait_for_timeout(200)
    return page


def mount_gestao_fixture(browser):
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(gestao_auth_script(False))
    page.goto(GESTAO_BASE)
    page.wait_for_function("!!window.NX_GESTAO_PAGE", timeout=5000)
    page.evaluate("window.NX_GESTAO_PAGE.render(document.getElementById('geOutlet'))")
    page.wait_for_timeout(200)
    return page


def mount_dashbi_real(browser, date_script=None, timezone_id=None, capture=None):
    ctx = {"viewport": {"width": 1366, "height": 900}}
    if timezone_id:
        ctx["timezone_id"] = timezone_id
    page = browser.new_page(**ctx)
    page.add_init_script(dashbi_auth_script(True))
    if date_script:
        page.add_init_script(date_script)

    def metrics_handler(route):
        # loadDashbiRealWithComparison() fires TWO requests (current period
        # + previous period, FC-1's comparison engine) against this SAME
        # endpoint, in a non-deterministic order -- capture every body seen
        # rather than the last one, so the assertion can confirm the
        # CURRENT-period request (matching the displayed dates) was among
        # them, regardless of which one the mock happened to see last.
        if capture is not None:
            capture.setdefault("metrics_bodies", []).append(json.loads(route.request.post_data or "{}"))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(DASHBI_EMPTY_METRICS))

    def model_handler(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(DASHBI_EMPTY_MODEL_METRICS))
    page.route(DASHBI_METRICS_URL + "*", metrics_handler)
    page.route(DASHBI_MODEL_METRICS_URL + "*", model_handler)
    page.goto(DASHBI_BASE)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")
    page.wait_for_timeout(200)
    return page


def mount_dashbi_fixture(browser):
    import os
    fixtures_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "dashbi-fixtures.json")
    with open(fixtures_path, encoding="utf-8") as f:
        body = f.read()
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.add_init_script(dashbi_auth_script(False))
    page.route("**/dashbi-fixtures.json", lambda route: route.fulfill(status=200, content_type="application/json", body=body))
    page.goto(DASHBI_BASE)
    page.wait_for_function("!!window.NX_DASHBI_PAGE", timeout=5000)
    page.evaluate("window.NX_DASHBI_PAGE.render(document.getElementById('dbOutlet'))")
    page.wait_for_timeout(200)
    return page


# (label, fixed today, expected currentMonth, expected lastMonth, expected last6-start)
CASES = [
    ("CASE A 2026-09-05", (2026, 9, 5), ("2026-09-01", "2026-09-05"), ("2026-08-01", "2026-08-31"), "2026-04-01"),
    ("CASE B 2026-01-05", (2026, 1, 5), ("2026-01-01", "2026-01-05"), ("2025-12-01", "2025-12-31"), "2025-08-01"),
    ("CASE C 2026-03-01", (2026, 3, 1), ("2026-03-01", "2026-03-01"), ("2026-02-01", "2026-02-28"), "2025-10-01"),
    ("CASE D 2028-03-01 (leap)", (2028, 3, 1), ("2028-03-01", "2028-03-01"), ("2028-02-01", "2028-02-29"), "2027-10-01"),
    ("CASE E 2026-05-31", (2026, 5, 31), ("2026-05-01", "2026-05-31"), ("2026-04-01", "2026-04-30"), "2025-12-01"),
]


def run(playwright):
    browser = playwright.chromium.launch()
    try:
        # ================= GESTÃO (Análise F&I do Grupo) =================
        for label, (y, m, d), exp_current, exp_last, exp_last6_start in CASES:
            cap = {}
            page = mount_gestao_real(browser, date_script=fixed_date_script(y, m, d), capture=cap)
            page.click(".gePresetBtn[data-preset='CURRENT_MONTH']")
            page.wait_for_timeout(150)
            got_current = (page.eval_on_selector("#geDateStart", "e=>e.value"), page.eval_on_selector("#geDateEnd", "e=>e.value"))
            check("Gestão %s: Mês atual == %s" % (label, exp_current), got_current == exp_current)
            check("Gestão %s: RPC receives same p_start/p_end as displayed" % label,
                  cap.get("body", {}).get("p_start") == got_current[0] and cap.get("body", {}).get("p_end") == got_current[1])

            page.click(".gePresetBtn[data-preset='PREVIOUS_MONTH']")
            page.wait_for_timeout(150)
            got_last = (page.eval_on_selector("#geDateStart", "e=>e.value"), page.eval_on_selector("#geDateEnd", "e=>e.value"))
            check("Gestão %s: Mês anterior == %s" % (label, exp_last), got_last == exp_last)

            page.click(".gePresetBtn[data-preset='LAST_6_MONTHS']")
            page.wait_for_timeout(150)
            got_last6_start = page.eval_on_selector("#geDateStart", "e=>e.value")
            got_last6_end = page.eval_on_selector("#geDateEnd", "e=>e.value")
            check("Gestão %s: Últimos 6 meses start == %s, end == today" % (label, exp_last6_start),
                  got_last6_start == exp_last6_start and got_last6_end == exp_current[1])
            page.close()

        # ================= DASHBI (Análise Geral do Grupo) =================
        for label, (y, m, d), exp_current, exp_last, exp_last6_start in CASES:
            cap = {}
            page = mount_dashbi_real(browser, date_script=fixed_date_script(y, m, d), capture=cap)
            page.click(".dbPresetBtn[data-preset='currentMonth']")
            page.wait_for_timeout(150)
            got_current = (page.eval_on_selector("#dbDateStart", "e=>e.value"), page.eval_on_selector("#dbDateEnd", "e=>e.value"))
            check("Dashbi %s: Mês atual == %s" % (label, exp_current), got_current == exp_current)
            check("Dashbi %s: RPC receives same p_start/p_end as displayed" % label,
                  any(b.get("p_start") == got_current[0] and b.get("p_end") == got_current[1] for b in cap.get("metrics_bodies", [])))

            page.click(".dbPresetBtn[data-preset='lastMonth']")
            page.wait_for_timeout(150)
            got_last = (page.eval_on_selector("#dbDateStart", "e=>e.value"), page.eval_on_selector("#dbDateEnd", "e=>e.value"))
            check("Dashbi %s: Mês anterior == %s" % (label, exp_last), got_last == exp_last)

            page.click(".dbPresetBtn[data-preset='last6']")
            page.wait_for_timeout(150)
            got_last6_start = page.eval_on_selector("#dbDateStart", "e=>e.value")
            got_last6_end = page.eval_on_selector("#dbDateEnd", "e=>e.value")
            check("Dashbi %s: Últimos 6 meses start == %s, end == today" % (label, exp_last6_start),
                  got_last6_start == exp_last6_start and got_last6_end == exp_current[1])
            page.close()

        # ================= Timezone boundary (Case F/G) =================
        # UTC-3 boundary: local clock after 21:00 in America/Sao_Paulo must
        # not shift the calendar day forward via UTC conversion.
        cap = {}
        page = mount_gestao_real(browser, date_script=fixed_date_script(2026, 9, 5, hh=22, mm=30), timezone_id="America/Sao_Paulo", capture=cap)
        page.click(".gePresetBtn[data-preset='CURRENT_MONTH']")
        page.wait_for_timeout(150)
        check("Gestão CASE F (UTC-3, 22:30 local): Mês atual end stays 2026-09-05", page.eval_on_selector("#geDateEnd", "e=>e.value") == "2026-09-05")
        page.close()

        page = mount_dashbi_real(browser, date_script=fixed_date_script(2026, 9, 5, hh=22, mm=30), timezone_id="America/Sao_Paulo")
        page.click(".dbPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Dashbi CASE F (UTC-3, 22:30 local): Mês atual end stays 2026-09-05", page.eval_on_selector("#dbDateEnd", "e=>e.value") == "2026-09-05")
        page.close()

        # UTC+14 boundary: local clock just after midnight must not shift
        # the calendar day BACKWARD via UTC conversion.
        page = mount_gestao_real(browser, date_script=fixed_date_script(2026, 6, 1, hh=0, mm=30), timezone_id="Pacific/Kiritimati")
        page.click(".gePresetBtn[data-preset='CURRENT_MONTH']")
        page.wait_for_timeout(150)
        check("Gestão CASE G (UTC+14, 00:30 local): Mês atual start stays 2026-06-01", page.eval_on_selector("#geDateStart", "e=>e.value") == "2026-06-01")
        page.close()

        page = mount_dashbi_real(browser, date_script=fixed_date_script(2026, 6, 1, hh=0, mm=30), timezone_id="Pacific/Kiritimati")
        page.click(".dbPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Dashbi CASE G (UTC+14, 00:30 local): Mês atual start stays 2026-06-01", page.eval_on_selector("#dbDateStart", "e=>e.value") == "2026-06-01")
        page.close()

        # ================= Fixture-mode regression (Gate 30/32): unchanged =================
        page = mount_gestao_fixture(browser)
        page.click(".gePresetBtn[data-preset='CURRENT_MONTH']")
        page.wait_for_timeout(150)
        check("Gestão FIXTURE mode unchanged (still the deterministic 2026-08-01..2026-08-30 reference)",
              (page.eval_on_selector("#geDateStart", "e=>e.value"), page.eval_on_selector("#geDateEnd", "e=>e.value")) == ("2026-08-01", "2026-08-30"))
        page.close()

        page = mount_dashbi_fixture(browser)
        page.click(".dbPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Dashbi FIXTURE mode unchanged (still the deterministic 2026-08-01..2026-08-30 reference)",
              (page.eval_on_selector("#dbDateStart", "e=>e.value"), page.eval_on_selector("#dbDateEnd", "e=>e.value")) == ("2026-08-01", "2026-08-30"))
        page.close()

        # ================= Manual date edit + active-state behavior (Gates 13/14/24) =================
        page = mount_gestao_real(browser, date_script=fixed_date_script(2026, 9, 5))
        page.click(".gePresetBtn[data-preset='CURRENT_MONTH']")
        page.wait_for_timeout(150)
        check("Gestão: preset shows active state", page.eval_on_selector(".gePresetBtn[data-preset='CURRENT_MONTH']", "e=>e.classList.contains('gePresetActive')"))
        page.fill("#geDateStart", "2026-01-01")
        page.eval_on_selector("#geDateStart", "e => e.dispatchEvent(new Event('change'))")
        page.wait_for_timeout(150)
        check("Gestão: manual date edit clears the active preset state", not page.eval_on_selector(".gePresetBtn[data-preset='CURRENT_MONTH']", "e=>e.classList.contains('gePresetActive')"))
        check("Gestão: manual date value is respected (not overwritten back)", page.eval_on_selector("#geDateStart", "e=>e.value") == "2026-01-01")
        page.close()

        page = mount_dashbi_real(browser, date_script=fixed_date_script(2026, 9, 5))
        page.click(".dbPresetBtn[data-preset='currentMonth']")
        page.wait_for_timeout(150)
        check("Dashbi: preset shows active state", page.eval_on_selector(".dbPresetBtn[data-preset='currentMonth']", "e=>e.classList.contains('dbBtnActive')"))
        page.fill("#dbDateStart", "2026-01-01")
        page.eval_on_selector("#dbDateStart", "e => e.dispatchEvent(new Event('change'))")
        page.wait_for_timeout(150)
        check("Dashbi: manual date edit clears the active preset state", not page.eval_on_selector(".dbPresetBtn[data-preset='currentMonth']", "e=>e.classList.contains('dbBtnActive')"))
        check("Dashbi: manual date value is respected (not overwritten back)", page.eval_on_selector("#dbDateStart", "e=>e.value") == "2026-01-01")
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
