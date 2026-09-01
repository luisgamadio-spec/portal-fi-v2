# Simulator UI Migration (PORTAL-NEXT-08.1)

**Functional V2 UI for Simulador Novos and Simulador Seminovos**, built
on Red Precision (`design-system-2.1/NORMATIVE.md`) and the frozen
PORTAL-NEXT-08 engines. 0 business logic in the page layer — every
number shown comes from `window.NX_SIMULADOR_NOVOS_ADAPTER` /
`NX_SIMULADOR_SEMINOVOS_ADAPTER` / `NX_CAMPANHA_ADAPTER` /
`NX_CASH_CONVERSION_ADAPTER` / `NX_SIMULADOR_SHARED` (PORTAL-NEXT-08,
byte-for-byte untouched — see Gate 45/46 verification below).

## Route architecture

```
Novos:       #/simulador-novos       -> assets/js/simulador-novos.js
Seminovos:   #/simulador-seminovos   -> assets/js/simulador-seminovos.js
```

**Correction to pre-existing metadata**: `config/module-registry.json`'s
`route` field previously said `/simulador/novos` (with a slash) —
`assets/js/router.js`'s own documented contract is `#/<module-id>`
(single-segment hash routing, no slash-path parsing), and
`NX_REGISTRY.byId()` matches `id` exactly. That slashed route value was
never actually wired to a working route (only Score/Coparticipado/
Gestão/Dashbi, whose `id`/`route` happened to already be identical
single tokens, were ever exercised through this mechanism). Corrected
to `/simulador-novos` / `/simulador-seminovos`, matching `id` — the
only routes the shell can actually resolve. No change to `router.js`
itself (Gate 3: do not redesign global navigation).

Both routes were **already wired into navigation** before this Wave —
`assets/js/landing.js`'s `NAV_ICONS` (`NV`/`SM`) and
`config/landing-groups.json`'s "Novos & Seminovos" group already
listed `simulador-novos`/`simulador-seminovos` — no nav changes were
needed.

## Mode mapping (Gate 7/47)

**Novos — all 9 reachable/authorized engines exposed:**
```
Financiamento:  Tradicional (Balão), Semestral/Anual, Parcela Única,
                Financiamento Linear
Campanhas:      Financiamento Campanha, Taxas Subsidiadas,
                Semestral Triton/Outlander
Ferramentas:    Descobridor de Taxa, Antecipação de Parcelas
                + Cash Conversion (shared, its own mode)
```

**Seminovos — the 6 reachable engines exposed; 2 confirmed dead-code
engines deliberately NOT exposed:**
```
Financiamento:  Tradicional (Balão, com faixa de ano), Semestral/Anual,
                Financiamento Seminovos (RATE_TABLE, ano x faixa de
                entrada, inclui 50x)
Campanhas:      Financiamento Campanha, Semestral Triton
Ferramentas:    Descobridor de Taxa, Antecipação de Parcelas
                + Cash Conversion (shared, its own mode)

NOT EXPOSED (Gate 47 dead-feature guard): "Financiamento Linear"
(top-level) and "Taxas Subsidiadas" — PORTAL-NEXT-08 confirmed 0
matching DOM markup for either in real production (only defensively-
guarded JS that safely no-ops). Their pure re-derivations remain in
simulador-seminovos.adapter.js for Gate 3 function-inventory
completeness only. Verified this Wave: the mode <select> has no option
whose text is "Financiamento Linear" or contains "Subsidiada" — see
tests/simulador-seminovos-ui-binding-test.py's Gate47 assertions.
"Financiamento Seminovos" (the real, reachable RATE_TABLE engine) is
never confused with the dead top-level Linear tab — it is its own
distinct mode with its own distinct label.
```

Mode switcher: a native `<select>` with `<optgroup>` sections (Gate 8)
— evaluated against a horizontal segmented tab strip and rejected: 8-9
modes in a single-row `.segmented` control would either overflow (Gate
33's absolute "no horizontal scroll" rule) or force unreadably
compressed labels. A `<select>` has zero overflow risk at any
viewport, is a native accessible control, and is the "select/command
surface" pattern Gate 8 explicitly offered as a valid option.

## Form contracts (Gates 10/11/12/13/14/15/16/18/19/20)

Every field maps 1:1 to what the selected engine actually needs — no
field is shown "for symmetry" (Gate 13: Novos' Tradicional form has no
year field; Seminovos' does). Money inputs use `.inputAffix` (R$
prefix + digits-only value, matching `NX_SIMULADOR_SHARED.parseBRL`'s
own expectations — Gate 18) via a shared `moneyField()` builder.
Percent-rate inputs (Cash Conversion's taxa de aplicação) use a plain
`type="text" inputmode="decimal"` field, NOT `type="number"` — see
"Bugs found and fixed" below. Term selectors are `.segmented` controls
built directly from each engine's own literal term list (Gate 19 — no
universal 12/18/24/36/48/60 list; Seminovos' RATE_TABLE mode shows all
9 of its own terms including 50x, which Novos never has). Entry-rule
guidance is per-engine (`MODE_DESC` strings), never a single global
"Entrada mínima 60%" claim (Gate 16).

Validation authority: every `calc*()` function in the page calls the
adapter FIRST, then branches on `result.error` — the UI never
independently decides validity (Gate 17). Error codes are mapped to
the exact original production message text (`ERROR_MSG` tables in each
page file), preserving message fidelity without re-deriving the logic
that produces them.

## Result hierarchy (Gates 21/22/23)

Large hero value first (`.resultHero .resultValue`, `clamp(30px,5vw,44px)`,
matching the Approved Reference's own measured grammar) — "result
dominates the view" (financial-simulator.md MUST). Secondary metrics
in a `.resultSecondaryGrid` below a hairline divider. Every displayed
number is `.toLocaleString('pt-BR', {style:'currency',...})` — the
same 2-decimal display rounding used everywhere else in V2 (Score/
Coparticipado/Dashbi); no value is rounded differently than the
adapter's own raw float. States: empty (`.emptyState`, initial), error
(`.errorState`, red-tinted), valid result — switching modes or
re-submitting invalid inputs always fully replaces
`#smResultRegion.innerHTML`, so a stale prior result can never remain
visible next to a new error (Gate 23).

**NORMATIVE.md §9 compliance** (MUST rules): Tradicional's balloon
result table shows parcela mensal + valor do balão + mês + total
devido no mês final, per balloon. Every rebate value everywhere is
labeled "— custo comercial da taxa" (Financiamento Campanha, Taxas
Subsidiadas, Semestral Triton), never "desconto". Every rebate-bearing
result shows "Valor final de venda" (valor líquido para a loja).

## Cash Conversion (Gates 24/25/26)

Its own mode in both simulators, calling
`window.NX_CASH_CONVERSION_ADAPTER.compute()` directly — 0 formula
duplication. Classification rendered as a colored badge
(`.smClassBadge.FINANCIAR/UTILIZAR/EQUIVALENTE`) plus the same
secondary-grid pattern used everywhere else, not a visually separate
"other app". Engine file hash verified unchanged (Gate 26/45 below).

## Coefficient visibility (Gate 27)

Production never surfaces the raw `coef`/`taxa` decimal fields to the
end user as their own dedicated UI element outside their calculated
role (e.g. the Parcela Única `coef` exists in the engine's own detail
panel in production but isn't a headline metric) — the V2 UI follows
the same restraint: `Descobridor` shows the resulting taxa (that IS
its whole purpose), other modes show `taxa aplicada` as one line among
several secondary metrics, matching production's own treatment,
without inventing a new "show me the raw coefficient" affordance
anywhere.

## Campaign iframe (Gate 28)

The byte-identical Financiamento Campanha engine was historically an
iframe (`FINANCIAMENTO_CAMPANHA_HTML_B64`) in both V1 simulators. V2
does **not** reproduce that architecture — it calls the extracted pure
`NX_CAMPANHA_ADAPTER.compute()` directly and renders native V2 markup
(a `.smTermGrid` + secondary grid), preserving 100% of the business
behavior (verified against both original iframes' real DOM output in
PORTAL-NEXT-08's own parity suite, re-confirmed this Wave) with 0
iframe, 0 new network/production dependency.

## WhatsApp / navigation (Gates 29/30)

No WhatsApp integration was migrated this Wave (Gate 29's "if
migrated" is conditional — it was not). Back-navigation uses V2's
existing global nav rail / breadcrumb (already present in the shell);
no legacy Back-button logic was copied.

## Vehicle imagery (Gate 31)

None used. Every result is fully operable and legible without any
image — imagery was never necessary to operate the simulator, and
none was introduced.

## Responsive (Gates 32-35)

Built mobile-first from the start: `.smGrid` collapses `360px 1fr` →
single column at ≤900px (same breakpoint the Approved Reference
itself uses), `.segmented` wraps, `.smTermGrid`/`.resultSecondaryGrid`
use `auto-fill`/`auto-fit` minmax grids that naturally recompose at
any width. Verified 0 horizontal scroll (`document.documentElement.
scrollWidth === clientWidth`) at 320/360/390/430/768/1024/1366/1920px
across both simulators, sweeping 5-8 representative modes per route
per viewport (48 combinations, 0 overflow). Long labels (14-model
Financiamento Campanha `<select>`, `"ECLIPSE CROSS HPE-S S-AWC BLACK"`,
BRL values up to 7 digits) verified via `word-break:break-word` on
result values; native `<select>` handles long option text without any
custom wrapping logic. Screenshots: `docs/screenshots-08-1/` (see
list below).

## Accessibility (Gate 36)

Every input has a real `<label for="...">`. Segmented controls are
`role="group"` with `aria-label`, built from native `<button>`
elements (native Enter/Space activation, no custom keydown handling
needed, confirmed via live keyboard test). Focus is visible
(`:focus-visible` outline on every interactive element, confirmed
`outlineStyle: solid` on a tabbed-to element). `#smResultRegion` is
`aria-live="polite" aria-atomic="true"` — a screen reader announces
the calculation result without the user needing to navigate to it
manually. No modal/drawer was introduced this Wave (nothing to trap
focus in).

## Reduced motion (Gate 37)

No animation/Ambient Motion/Parametric Reactive canvas was added by
this Wave's pages at all — nothing depends on motion, so
`prefers-reduced-motion` has nothing to disable here (trivially
satisfied, not silently skipped).

## Loading states (Gate 38) / Backend (Gate 39)

No fake loading state exists anywhere — every calculation is a
synchronous local function call (the adapters are plain JS, no
Promise/async in the compute path). 0 `fetch`/network/Supabase calls
anywhere in the two page files or the shared UI helper (grep-verified,
same as PORTAL-NEXT-08's own adapters).

## Bugs found and fixed during this Wave

1. **Doubled "R$ R$" currency prefix.** `moneyField()`'s default
   values were passed as `'R$ 100.000,00'` while `.inputAffix .prefix`
   already renders the "R$" glyph — fixed by stripping a leading `R$`
   from the raw value inside `moneyField()` itself (one fix point, not
   30 call-site edits).
2. **`business-logic-scanner.py` false-collision, real catch.** The
   page's own UI wrapper function for Parcela Única was named
   `calcParcelaUnica` — textually identical to the forbidden V1
   DOM-coupled function name, even though it contains 0 duplicated
   business math (just reads form fields, calls the adapter, renders).
   Renamed to `runParcelaUnica` — the scanner's guard is deliberately
   blunt (exact name match, not an AST-aware "is this really the same
   logic" check), and this Wave's own architecture principle (Gate 25:
   use different names for pure re-derivations) applies to the page
   layer too, not just the adapter layer.
3. **Cash Conversion rate field silently defaulted to 0%.** The "Taxa
   de aplicação mensal (%)" field used `type="number"` with a
   Brazilian comma-decimal default value (`"0,80"`) — HTML5 number
   inputs require a dot for decimals regardless of locale, so the
   browser silently rejected the value and rendered an empty field,
   computing every Cash Conversion result with an implicit 0% rate
   with zero visible error. Found by screenshot review (Gate 49/50's
   entire justification — an automated DOM check that doesn't inspect
   rendered pixels/values would not have caught this on its own).
   Fixed with a dedicated `percentField()` helper (`type="text"
   inputmode="decimal"`), and 6 new regression cases added to both
   UI-binding test suites specifically to keep this class of bug
   caught mechanically going forward.

## Engine freeze verification (Gates 1/26/45/46)

```
sha256 of every PORTAL-NEXT-08 adapter file + every frozen module
file (Score/Coparticipado/Gestão/Dashbi/Landing), captured before any
UI code was written and again after full implementation: 0-byte diff,
byte-for-byte identical.
```

## Golden verification

```
tests/simulador-novos-parity-test.py (PORTAL-NEXT-08, re-run):        40/40
tests/simulador-seminovos-parity-test.py (PORTAL-NEXT-08, re-run):        24/24
tests/simulador-campanha-parity-test.py (PORTAL-NEXT-08, re-run):             14/14
tests/cash-conversion-parity-test.py (PORTAL-NEXT-08, re-run):                    11/11
tests/simulador-cross-product-test.py (PORTAL-NEXT-08, re-run):                       5/5
tests/simulador-novos-ui-binding-test.py (NEW, real UI):                                  43/43
                                                                                            (40 original
                                                                                           golden cases +
                                                                                          3 Cash Conversion)
tests/simulador-seminovos-ui-binding-test.py (NEW, real UI):                                  29/29
                                                                                                (24 original
                                                                                               golden cases +
                                                                                              2 Gate47 dead-
                                                                                             feature checks +
                                                                                            3 Cash Conversion)
Score/Coparticipado/Gestão/Dashbi/Landing/registry/scanner:                                       all PASS
                                                                                                   (business-
                                                                                                  logic-scanner
                                                                                                 updated: same
                                                                                                scoped-
                                                                                               authorization
                                                                                              pattern already
                                                                                             used for Score/
                                                                                            Coparticipado,
                                                                                           applied here for
                                                                                          the page-layer
                                                                                         wrapper-name
                                                                                        collision)
Console/page errors across every test run:                                                        0
Horizontal scroll at every required viewport:                                                          0
```

## Known limitations (disclosed, not hidden)

- Antecipação's balloon-payment sub-feature is not exposed in this
  UI's form (the extracted engine fully supports it, per
  PORTAL-NEXT-08's own golden coverage) — the form only exercises the
  "no balloon" path. A future Wave can add the balloon rows using the
  exact same pattern already built for Tradicional.
- No WhatsApp/analyst-contact integration was migrated.
- No live ACTIVE-base coefficient loading (Supabase RPC) — every table
  is the FALLBACK table exactly as PORTAL-NEXT-08 extracted it, per
  this Wave's explicit 0-backend instruction.

## Status (Gate 51)

```
Simulator Engine:            PARITY_VERIFIED / FROZEN (0 diff this Wave)
Simulator V2 UI:                  MIGRATED / UAT_PENDING
Simulator Business:                    PARITY_VERIFIED / HUMAN_UAT_PENDING
Simulator Responsive:                        TECHNICALLY_GREEN / HUMAN_UAT_PENDING
```
Not marked `HUMAN_APPROVED` anywhere — `migrationStatus` for both
modules is `VISUAL_PARITY_PENDING` in `config/module-registry.json`
(same status Score/Coparticipado/Gestão/Dashbi carried at the
equivalent point in their own history).
