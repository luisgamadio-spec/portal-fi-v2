#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-2-HUMAN-TEXT-UAT-01 HOTFIX-03 -- Assistant Markdown presentation.

Real OpenAI model replies came back with literal Markdown syntax
(**bold**, - lists, 1. lists) unrendered in the UI. This drives
window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse() directly (a
narrow, safe Markdown-subset renderer -- Portal V2 presentation layer
only, never touches conversation state or the backend contract) and
proves both: the supported subset renders correctly, and a battery of
XSS payloads survives only as inert escaped text -- HTML-escaping runs
over the full raw string BEFORE any Markdown transform, so no <, >
character from model output ever survives to be reinterpreted as a
tag by the transform's own (hardcoded-tag-only) regexes.

Requires: `python -m http.server 8700` running from PORTAL-FI-DESIGN-LAB/.
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://localhost:8700/portal-next-v2/index.html"
results = []


def check(label, cond):
    results.append((label, bool(cond)))


CASES = {
    "bold": "**Financiamento Linear:** texto normal.",
    "list": "**Quando faz sentido:**\n- situação um\n- situação dois",
    "olist": "1. primeira opção\n2. segunda opção",
    "italic": "Texto com *ênfase*.",
    "script": "<script>alert(1)</script>",
    "img_onerror": "<img src=x onerror=alert(1)>",
    "a_js_href": '<a href="javascript:alert(1)">x</a>',
}


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        page.goto(BASE + "#/brabus-intelligence")
        page.wait_for_timeout(400)

        check(
            "renderAssistantProse exposed for tests",
            page.evaluate("typeof window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse === 'function'"),
        )

        for label, text in CASES.items():
            result = page.evaluate(
                """(text) => {
                    const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse(text);
                    const div = document.createElement('div');
                    div.innerHTML = html;
                    document.body.appendChild(div);
                    const info = {
                        html: html,
                        hasScriptTag: !!div.querySelector('script'),
                        hasImgTag: !!div.querySelector('img'),
                        hasAnchorTag: !!div.querySelector('a'),
                        hasAnyOnErrorAttr: !!div.querySelector('[onerror]'),
                        hasJsHref: Array.from(div.querySelectorAll('[href]')).some(
                            e => (e.getAttribute('href') || '').toLowerCase().startsWith('javascript:')
                        ),
                        textContent: div.textContent
                    };
                    div.remove();
                    return info;
                }""",
                text,
            )
            check(f"{label}: no <script> element materialized", not result["hasScriptTag"])
            check(f"{label}: no live <img>/<a> element created", not (result["hasImgTag"] or result["hasAnchorTag"]))
            check(f"{label}: no live [onerror] attribute in DOM", not result["hasAnyOnErrorAttr"])
            check(f"{label}: no live javascript: href", not result["hasJsHref"])

            if label == "bold":
                check("bold: <strong> present, no raw **", "<strong>" in result["html"] and "**" not in result["html"])
            if label == "list":
                check("list: <ul><li> present", "<ul>" in result["html"] and "<li>" in result["html"])
            if label == "olist":
                check("olist: <ol><li> present", "<ol>" in result["html"] and "<li>" in result["html"])
            if label == "italic":
                check("italic: <em> present", "<em>" in result["html"] and "ênfase" in result["textContent"])
            if label in ("script", "img_onerror", "a_js_href"):
                check(f"{label}: payload survives only as inert visible text", text in result["textContent"])

        check("no alert() dialogs fired by any payload", len(dialogs) == 0)

        block_html = page.evaluate(
            """() => window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock({
                type: 'metrics', title: 'T', items: [{label: 'L', value: 1, format: 'currency'}]
            })"""
        )
        check("structured block renderer untouched by this hotfix", "baiMetricsGrid" in block_html)

        long_md = (
            "**Financiamento Linear:** parcelas mensais regulares.\n\n"
            "**Quando faz sentido:**\n- situação um\n- situação dois\n\n"
            "1. primeiro\n2. segundo\n\nTexto com *ênfase* e `código`."
        )
        for w, h in [(1366, 768), (768, 1024), (430, 932), (390, 844)]:
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate(
                """(text) => {
                    const el = document.getElementById('baiConversation');
                    const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse(text);
                    el.innerHTML = '<div class="baiMessage baiMessageAssistant">'
                        + '<div class="baiBubble baiBubbleMd">' + html + '</div></div>';
                }""",
                long_md,
            )
            page.wait_for_timeout(150)
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"{w}x{h}: no horizontal overflow with rendered Markdown", not overflow)

        browser.close()

    passed = sum(1 for _, c in results if c)
    total = len(results)
    for label, cond in results:
        print(("[PASS] " if cond else "[FAIL] ") + label)
    print(f"\n=== Brabus Intelligence Markdown Presentation Test: {passed}/{total} ===")
    print("RESULT:", "PASS" if passed == total else "FAIL")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
