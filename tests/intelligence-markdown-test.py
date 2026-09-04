#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IA-V2-2-HUMAN-TEXT-UAT-01 HOTFIX-03/04 -- Assistant Markdown presentation.

Real OpenAI model replies came back with literal Markdown syntax
(**bold**, - lists, 1. lists) unrendered in the UI (HOTFIX-03). Then a
real reply that interleaved each numbered item with its own "- " detail
bullets came back numbered 1./1./1. instead of 1./2./3. (HOTFIX-04) --
every interruption of the numbered run (a blank line, a subordinate
bullet group) had started a brand new <ol>, and a native <ol> always
restarts its own numbering at 1.

This drives window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse()
directly (a narrow, safe Markdown-subset renderer -- Portal V2
presentation layer only, never touches conversation state or the
backend contract) and proves: the supported subset renders correctly,
ordered-list numbering stays continuous across subordinate bullet
groups while still splitting into a genuinely new list when real prose
intervenes, and a battery of XSS payloads (including inside list items)
survives only as inert escaped text -- HTML-escaping runs over the full
raw string BEFORE any Markdown transform, so no <, > character from
model output ever survives to be reinterpreted as a tag by the
transform's own (hardcoded-tag-only) regexes.

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
        # AUTH FOUNDATION generalized route-guard coverage to the whole
        # shell (Phase 2B) after this test was written -- without this,
        # a machine with a real .local.js override (Real Data
        # Integration Foundation's own ongoing arc) lands on SIGNED_OUT/
        # Login instead of AUTH_NOT_CONFIGURED, and the shell/#nxRoot
        # (with #baiConversation inside it) never mounts. This test's
        # own purpose (deterministic Markdown rendering) never depended
        # on auth; block the local override so it reaches the same
        # inert AUTH_NOT_CONFIGURED state it always relied on.
        page.route("**/intelligence-runtime-config.local.js", lambda route: route.abort())

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

        # HOTFIX-04 -- ordered-list numbering continuity.
        exact_human_structure = (
            "As 3 principais diferenças:\n\n"
            "1. Forma de pagamento\n"
            "- Linear: parcelas fixas.\n"
            "- Balão: parcelas menores + pagamento final.\n\n"
            "2. Valor das parcelas mensais\n"
            "- Linear: parcela mais alta.\n"
            "- Balão: parcela mais baixa.\n\n"
            "3. Compromisso no futuro\n"
            "- Linear: nenhum.\n"
            "- Balão: precisa quitar o balão.\n"
        )
        r = page.evaluate(
            """(text) => {
                const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse(text);
                const div = document.createElement('div');
                div.innerHTML = html;
                const ols = div.querySelectorAll('ol');
                return {
                    html: html,
                    olCount: ols.length,
                    liInFirstOl: ols.length ? ols[0].querySelectorAll(':scope > li').length : 0,
                    nestedUlCount: ols.length ? ols[0].querySelectorAll('ul').length : 0
                };
            }""",
            exact_human_structure,
        )
        check("ordered item + subordinate bullets: single continuous <ol>", r["olCount"] == 1)
        check("ordered item + subordinate bullets: 3 top-level <li>", r["liInFirstOl"] == 3)
        check("ordered item + subordinate bullets: 3 nested <ul>", r["nestedUlCount"] == 3)
        check(
            "ordered item + subordinate bullets: no leftover 'N. ' numeral prefix in item text",
            "1. Forma" not in r["html"] and "2. Valor" not in r["html"] and "3. Compromisso" not in r["html"],
        )

        r2 = page.evaluate(
            """() => {
                const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse('1. primeira opção\\n2. segunda opção\\n3. terceira opção');
                const div = document.createElement('div');
                div.innerHTML = html;
                const ols = div.querySelectorAll('ol');
                return { olCount: ols.length, liCount: ols.length ? ols[0].querySelectorAll('li').length : 0 };
            }"""
        )
        check("plain ordered 1/2/3: single <ol>", r2["olCount"] == 1)
        check("plain ordered 1/2/3: 3 <li>", r2["liCount"] == 3)

        multi_separate = (
            "1. Primeiro item\n2. Segundo item\n\n"
            "Um parágrafo normal no meio, sem relação com listas.\n\n"
            "1. Outro item\n2. Mais um item\n"
        )
        r3 = page.evaluate(
            """(text) => {
                const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse(text);
                const div = document.createElement('div');
                div.innerHTML = html;
                const ols = div.querySelectorAll('ol');
                return {
                    olCount: ols.length,
                    firstLi: ols.length > 0 ? ols[0].querySelectorAll('li').length : 0,
                    secondLi: ols.length > 1 ? ols[1].querySelectorAll('li').length : 0
                };
            }""",
            multi_separate,
        )
        check("multiple separate ordered lists: real prose splits into 2 <ol>", r3["olCount"] == 2)
        check("multiple separate ordered lists: first has 2 <li>", r3["firstLi"] == 2)
        check("multiple separate ordered lists: second has 2 <li>", r3["secondLi"] == 2)

        malicious_in_list = (
            "1. <script>alert(1)</script>\n"
            "- <img src=x onerror=alert(1)>\n\n"
            '2. <a href="javascript:alert(1)">click</a>\n'
        )
        r4 = page.evaluate(
            """(text) => {
                const html = window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse(text);
                const div = document.createElement('div');
                div.innerHTML = html;
                document.body.appendChild(div);
                const info = {
                    hasScriptTag: !!div.querySelector('script'),
                    hasImgTag: !!div.querySelector('img'),
                    hasAnchorTag: !!div.querySelector('a'),
                    hasOnErrorAttr: !!div.querySelector('[onerror]'),
                    hasJsHref: Array.from(div.querySelectorAll('[href]')).some(
                        e => (e.getAttribute('href') || '').toLowerCase().startsWith('javascript:')
                    )
                };
                div.remove();
                return info;
            }""",
            malicious_in_list,
        )
        check("malicious payload inside list item: no <script> element", not r4["hasScriptTag"])
        check("malicious payload inside list item: no live <img>/<a>", not (r4["hasImgTag"] or r4["hasAnchorTag"]))
        check("malicious payload inside list item: no live [onerror]", not r4["hasOnErrorAttr"])
        check("malicious payload inside list item: no live javascript: href", not r4["hasJsHref"])

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
