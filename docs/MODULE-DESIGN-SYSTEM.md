# Red Precision Module Design System (Wave 3A)

Shared module-level primitives for Portal V2, defined in
`assets/css/module-system.css`, loaded after `shell.css`/`landing.css`
and before any per-module stylesheet. **Foundation, not a mass
migration** — most modules still use their own `db*`/`ge*`/`sc*`/`cp*`
classes; only Análise Geral do Grupo (Dashbi) consumes the shared
classes so far, as the representative proof (see "Representative
migration" below).

Every primitive here is **extracted** from a pattern already proven
and human-approved somewhere in the app (Dashbi/Gestão's page header,
field, KPI card, table grammar; Simuladores' `.btn`/`.segmented`/
`.emptyState` family) — nothing was invented fresh. Where a module's
own class already does the same job, it is untouched; these shared
classes exist so a future module Wave has one vocabulary to reach for.

## Tokens

`module-system.css` §1 defines semantic-role custom properties
(`--mod-space-*`, `--mod-title-size`, `--mod-surface-*`, `--mod-accent`,
`--mod-success/-warning/-info/-critical`, ...) that are **aliases**
onto the existing global tokens in `design-system-2/tokens.css` — no
new primitive value was introduced. Reach for `--mod-*` in shared
primitives; reach for the global token directly in module-local CSS,
same as today.

## Page header

```html
<div class="modPageHeader">
  <div class="modHeaderMain">
    <h1 class="modTitle">Título do módulo</h1>
    <p class="modSubtitle">Descrição de uma linha.</p>
  </div>
  <div class="modHeaderActions"><!-- optional right-side action --></div>
</div>
```
Optional `.modEyebrow` (small uppercase accent tag) can precede
`.modTitle` inside `.modHeaderMain`. `.modSectionTitle` is the shared
`h2`-equivalent for in-page section headings.

## Filters

```html
<div class="modFilters">
  <div class="modField"><label>Loja</label><select>...</select></div>
  <div class="modField"><label for="x">Data inicial</label><input id="x" type="date"></div>
</div>
```
Wraps naturally (`flex-wrap`) at any width; `.modField` gets a
narrower `min-width` at ≤768px. Does not include the segmented/preset
buttons themselves — those are a separate component (below).

## Buttons

`.modBtn` + one modifier (`.modBtnPrimary`/`.modBtnSecondary`/
`.modBtnGhost`/`.modBtnDanger`), optionally `.modBtnSm`. `.modBtnPrimary`
is a byte-for-byte extraction of Simuladores' already-approved
`.btn-primary` (background `--color-accent-primary`, text `#1a0506`) —
reuses that decision rather than making a second one. Never use
`--color-brand-red` for an interactive button; the token file itself
reserves that hue for institutional/brand presence, not state.

## Segmented controls vs. tabs

Two related but semantically different components (a segmented
control is a **filter**; a tab is a **navigation-like single-active-
region switcher** — keep them conceptually distinct even though their
visual language is related):
- `.modSegmentedGroup` > `.modSegItem` (+ `.modSegItemActive`) — e.g.
  Todos/Novos/Seminovos.
- `.modTabGroup` > `.modTab` (+ `.modTabActive`, underline indicator)
  — e.g. a Grupo/Modelos/Ranking switcher.

Both extract the `canvas`-background/`text-primary`-foreground active
recipe already used by Dashbi/Gestão/Coparticipado (`.dbBtnActive`/
`.gePresetActive`/`.cpTabActive`). **Not** the recipe Simuladores uses
(`rgba(238,75,87,.14)` + `#ffecec`) — that is a deliberately different,
untouched, already-approved family; do not merge the two without a
human decision.

## KPI cards

`.modKpiGrid` > `.modKpiCard` (+ `.modKpiLabel`/`.modKpiValue`/
`.modKpiHint`). Three tiers: base (24px value), `.modKpiCardExec`
(20px), `.modKpiCardSecondary` (15px, tighter padding). Semantic
modifiers `.modKpiCardSuccess`/`-Warning`/`-Critical` (left border +
value color) and `.modKpiCardInfo` (top border + bold value) —
position/weight distinguish them from each other and from a plain
card, never color alone.

## Tables

`.modTableWrap` (local `overflow-x:auto`) > `.modTable` with
`.modNumCol`/`.modCurrencyCol`/`.modPercentCol` (right-aligned,
tabular-nums), `.modActionCol`, `.modStatusCell`, sticky first column.
**This Wave covers desktop/tablet only** — mobile transformation stays
module-owned; the inventory found three genuinely different, all
legitimate, existing strategies (Dashbi/Score's separate mobile-card
renderer; Gestão's `data-th` + flex-wrap at 768px; Coparticipado's
same technique at 900px with `table-layout` switched to `auto`) — do
not force one onto another module without evidence it's actually
better for that module's content shape.

## Panels

`.modPanel` (spacing only) / `.modPanelBordered` (bordered box) /
`.modPanelForm` + `.modPanelResult` (Simuladores' `.smFormCard`/
`.smResultCard` treatment, extracted for reuse by a future two-panel
module).

## States

`.modEmptyState` / `.modErrorState` / `.modInfoState` (+ `.modStateTitle`)
and `.modLoadingState` (+ `.modLoadingDot`, static — no animation, per
this Wave's motion deferral) — extracted from Simuladores' already-
approved `.emptyState`/`.errorState`.

## Fixture/dev-data banner

`.modFixtureBanner` (+ `.modFixtureLabel`, optional `<select>`) unifies
the 4 existing near-identical banners (`.dbFixtureBar`/`.scFixtureBar`/
`.cpFixtureBar`/`.geFixtureBar` — the inventory found Gestão's has no
select and different copy; the shared version supports both with/
without a selector). Diagnostic-only, visually subordinate — same
design family as the Shell's own `.nxDevBadge`, never its exact
markup.

## Representative migration — Análise Geral do Grupo

Migrated to the shared system: page header, fixture banner, filter
field wrappers, and the top-tier KPI grid (Vendas/Financiamentos/
Share/Produção Total/Receita Total — `kpiPrimary()`/
`kpiShareCardHtml()`/`kpiReceitaTotalCardHtml()` in `dashbi.js`).
Verified pixel-equivalent to the pre-migration render (screenshot
comparison) — 0 visual regression, 0 business-logic change (Dashbi's
own 26/26 parity suite, which validates calculations not markup,
unaffected).

**Deliberately NOT migrated this Wave** (present, correct, untouched):
segmented-control buttons (`.dbBtn`/`.dbViewBtn`/`.dbPresetBtn`/
`.dbModeGroup` — JS event handlers target these exact class names via
`classList.toggle`; renaming requires updating every call site
consistently, deferred to a lower-risk future Wave rather than risking
an incomplete rename in a 2000+ line file), plan/entrada/family-metric
card variants, the table foundation itself (still `.dbTable`), Model
Analysis, Ranking, Novos por Loja, and the mobile card renderer.
Old `.dbHeader`/`.dbFixtureBar`/`.dbFilters`/`.dbField`/
`.dbKpiGridPrimary`/`.dbKpiCardPrimary`/`.dbKpiCardShare`/
`.dbKpiCardReceitaTotal` rules remain in `dashbi.css`, marked as
confirmed-dead (0 remaining reference, verified via grep), not
deleted — same discipline as other Waves' retired code.

## Deferred (explicitly, per the Wave 3A brief)

- **Coparticipados**: the responsive per-record card is known to be
  excessively tall at tablet widths. Future direction: a multi-column
  information grid at tablet, selectively grouped single-column at
  narrow mobile. Not implemented this Wave.
- **Score**: no redesign, no artificial fixture population. Score's
  own module Wave will decide whether/how it adopts the shared system
  (its band/badge system is the richest of the 6 modules and may
  warrant its own `.modBadge*` extension later).
- **Simuladores**: business-interface UX untouched. Their `.btn`/
  `.segmented`/`.emptyState` family is the *source* the shared button
  and state primitives were extracted from — already compatible in
  spirit, not touched structurally.

## Responsive contract

Primitives validated at 1920/1366/1024/768/430/390px via the
representative module — 0 horizontal scroll at every width (verified,
not assumed). The Shell's own breakpoint architecture (drawer at
≤1279px, see `docs/` from Wave 2B) is unchanged.

## Second migration — Análise F&I do Grupo (Wave 3B)

Migrated to the shared system: page header, fixture banner, filter
field wrappers, all KPI grids (production status, financial value,
SPF Extra, and every "Indicadores"/support KPI group), and the table
foundation (`Planos por Loja e Departamento`, `Financiamentos por
Loja`, both status-by tables, both proposal-outcome tables — 7 tables
total). Verified via a captured before/after data snapshot (28 KPI
values, 5 plan-classification cards, 8 tables' full text) — byte-
identical, 0 business-logic change.

**Deliberately NOT migrated**: the 5-way plan classification cards
(`.gePlanCard`/`.planSubsidiado`/etc.) — business-critical, already
correct, distinct semantics the shared system's 4 generic modifiers
don't map onto 1:1; segmented-control buttons (`.gePresetBtn`/
`.geVehicleBtn`) — same JS-coupling reason as Dashbi's deferred
`.dbBtn` family in Wave 3A.

Two genuinely reusable rules this migration surfaced, not covered by
Wave 3A's single-module proof:

- **Financial semantic KPI accents**: an Exec-tier `.modKpiCard` can
  take an existing semantic modifier (`.modKpiCardWarning`,
  `.modKpiCardInfo`, ...) to distinguish cautionary/informational
  metrics from a neutral total — reuses existing tokens, never invents
  a new color. Applied to "Propostas Perdidas" (warning) and "Propostas
  em Aberto" (info) alongside a plain "Valor de Produção Total".
- **Wide analytical tables need a module-level override on
  `.modTable`**: the shared table foundation's default is
  `white-space: nowrap` (fine for narrower tables), but a table with
  many columns (F&I's widest has 10) needs `table-layout: fixed` +
  wrapping to hold 0 horizontal scroll — re-declare those two
  properties scoped under the module's own page class (e.g. `.gePage
  .modTable { table-layout: fixed; }`), and retarget any existing
  `<=768px` data-th mobile override from the module's old table class
  to `.modTable`/`.modTableWrap`. Don't assume the shared default fits
  every column count — measure.

## Third migration — Gestão de Coparticipados & Subsidiados (Wave 3C)

Migrated to the shared system: page header, fixture banner (with
selector, same as Dashbi/F&I), filter field wrappers, the
Coparticipados/Subsidiados view switcher (the first real consumer of
`.modTabGroup`/`.modTab` — a genuine single-active-region switch, not a
filter), Subsidiados' 3-stat summary (`.modKpiGrid` +
`.modKpiCardSecondary`), and the table foundation for both of this
module's tables (13 and 11 columns — the widest in V2). Verified via a
DOM-level presentation-parity test
(`tests/coparticipado-presentation-parity-test.py`) that derives
expected values live from `window.NX_COPARTICIPADO_ADAPTER.compute()`
and compares every rendered field, across 5 fixture scenarios × 2
views — 0 hardcoded expected value, 0 business-logic touched.

**Deliberately NOT migrated**: the section heading (`.cpPanel h2`) —
already pixel-identical to `.modSectionTitle`'s type values, but kept
local because only one heading renders per view here (no top-gap
needed, unlike Gestão's many stacked sections).

**New this Wave**: `.modBadgeNeutral` — a badge-shaped chip with no
color semantic, for a status/reference value that has no authoritative
good/bad mapping (Coparticipado's raw backend "Situação" string).
Reuses the same shape as `.modBadgeSuccess`/`-Warning`/`-Critical`/
`-Info` without inventing a color meaning that isn't there.

**Responsive record composition** (the objective-B refinement,
authorized specifically for this module): below 900px, a wide
analytical table recomposes into a grouped card instead of one flat
column of label/value pairs — primary identity (first field) full-width
and bold with its label hidden, a status badge on its own line, then
metadata/financial/reference bands each on their own visual line
(divider = `border-top` + `margin-top` on the band's first cell),
still in the table's original DOM/reading order (no `order`-based
visual reordering — WCAG meaningful-sequence: a screen reader's
reading order must still match what's visually grouped). One concrete
financial "headline" field (this module's `Coparticipação`) may take a
small mobile-only weight/size bump — only when the module truly has a
single decisive output value; don't invent one where several fields
are peers (Subsidiados has none).

**Two real bugs found and fixed while building this, both proven with
this Wave's own regression matrix, worth remembering for the next
wide-table mobile migration**:
- A `<tr>` restyled to `display:grid` (not `display:flex`) inside a
  `table-layout:auto` table, with a `<colgroup>` still present in the
  DOM, made Chromium size the `<table>` by the colgroup's pixel widths
  regardless of the grid content — 647px of overflow at a 430px
  viewport. Fix: explicitly hide `colgroup`/`col` at that breakpoint
  (or don't use `display:grid` for this transform; `display:flex` with
  explicit `flex-basis` percentages doesn't hit this).
- A cell carrying a numeric-column class (`.modNumCol`, which sets
  `white-space:nowrap`) can still be showing a non-numeric fallback
  message (a "not found" warning) instead of a real value — the nowrap
  forces that message to overflow its column. `white-space` is
  inherited per-element, so overriding it directly on the fallback's
  own span (not the cell) fixes it without touching the numeric case.

## Sixth migration — Simulador de Seminovos (Wave 3F) — SIMULATOR FAMILY CONCLUSION

Migrated the same two elements Wave 3E migrated for Novos — page
header (`.modPageHeader`/`.modTitle`/`.modSubtitle`) and the form/result
panels (`.modPanelForm`/`.modPanelResult`) — closing out the simulator
family. Unlike Novos, Seminovos has no `.smGridStacked`-equivalent mode
(no Subsidiadas comparison grid), so its form region drops
`.smFormCard` entirely rather than keeping it as a redundant safety
class; Novos still needs to keep that one.

**Net effect on the old shared rules**: `.smHeader` and `.smResultCard`
are now fully superseded — 0 remaining reference in either simulator
file. `.smFormCard` stays active, but only because Novos' own
Subsidiadas-mode override (`.smGridStacked .smFormCard`) still targets
it by name; nothing else needs it anymore.

**The Transactional Module Contract required 0 changes to survive a
second, structurally different consumer.** Confirms it as generalized,
not Novos-shaped: mode-nav grouped by category (Seminovos has 2 groups
and 5 modes vs. Novos' 3 groups and 10 — the contract doesn't care) →
one form region with every input and the primary CTA together → a
result region beside the form at ≥900px, stacked below it under 900px
→ one dominant value with a quieter secondary grid. No new shared
primitive was needed (Gate 27 expected zero, delivered zero).

**Confirmed still genuinely module-specific, not merely deferred**:
`window.NX_SIM_UI` (fields/buttons/states/result blocks — shared
infrastructure, still untouched by either simulator's migration), the
grouped mode-nav and balloon payment-structure story (independently
duplicated in both files, proven safe to leave alone twice now), and
the features that exist in only one simulator — Seminovos has no
Campanhas group, no Subsidiadas grid, no Semestral Triton, no
"Parcela Única"; it has its own vehicle-year field (`Ano do veículo`)
and its own Linear rate-table engine that Novos has no equivalent of.
None of that was copied in either direction — shared UI language,
independent business capability, exactly as this Wave's brief required.

**Simulator-family migration is now complete**: both Novos and
Seminovos speak the same Red Precision transactional visual language
(header, panels, mode-nav, field, button, and result grammar) while
keeping 100% independent financial engines, field sets, and mode
lists.

## Fourth migration — Análise de Score Vendedores (Wave 3D)

Migrated to the shared system: page header, fixture banner. A shared
`.modEmptyState` was also added for the (currently untested-by-fixture)
zero-record case, matching the same pattern other modules already use.

**Deliberately NOT migrated** — this module has more already-approved,
bespoke UI than any other migrated so far, and none of it was touched:
the score band classifier/labels (`.scBand` + 5 variants — human-
approved normative colors, PORTAL-NEXT-07.7B), the score meter
(`.scMeterTrack`/`.scMeterFill` — transplanted byte-for-byte from an
Approved Executable Reference), the dual-renderer responsive strategy
(`renderDesktopTable()`/`renderMobileCards()`, both fed by the same
computed rows — a *different*, equally valid pattern from Coparticipado's
CSS-only table-to-card transform, chosen after human UAT rejected the
CSS-transform approach specifically for this module three times), and
the detail/breakdown drill-down panel (`.scDetail`/`.scCriterion` — no
shared parallel exists; its heading isn't a pixel match for
`.modSectionTitle`, unlike Gestão/Coparticipado's headings).

## Fifth migration — Simulador de Novos (Wave 3E) — TRANSACTIONAL MODULE CONTRACT

The first migrated module that isn't an analytical dataset — it's a
financial WORKFLOW (input → condition → calculate → result), and the
migration scope was governed by one hard architectural constraint that
didn't exist for any analytical module:

**`assets/js/simuladores-shared.js`'s `window.NX_SIM_UI` helper (the
`.field`/`.input`/`.select`/`.inputAffix`/`.segmented`/`.btn*`/
`.kpiLabel`/`.emptyState`/`.errorState`/`.resultHero`/
`.resultSecondaryGrid` markup builders) is consumed by BOTH Simulador
de Novos and Simulador de Seminovos.** Changing anything it emits
changes both simulators at once — and Seminovos is explicitly frozen
this Wave. So is every Novos-owned class name that Seminovos'
*separate* `render()` also happens to reuse (`.smHeader`,
`.smModeNav`/`.smModeBtn`, `.smGrid`/`.smFormCard`/`.smResultCard`,
`.smPlanRegular`/`.smPlanSpecial` balloon story, `.smClassBadge`,
`.smTable`, `.smFootnote` — verified one by one against
`simulador-seminovos.js` before touching anything, not assumed).

**What was actually safe to migrate**: only where Novos' own `render()`
emits a class Seminovos' *own*, textually separate `render()` also
happens to use, swapping Novos' copy to a shared primitive is safe
*only if the old CSS rule is left fully intact* (Seminovos still reads
it). Migrated: the page header (`.modPageHeader`/`.modTitle`/
`.modSubtitle` — pixel-identical to `.smHeader`'s own values) and the
form/result panels (`.modPanelForm`/`.modPanelResult` — these were
*already* extracted from `.smFormCard`/`.smResultCard` in Wave 3A and
had never had a real consumer until now; pixel-identical, confirmed
before switching). The form region keeps `.smFormCard` as a second,
redundant class alongside `.modPanelForm`, because a `.smGridStacked
.smFormCard` descendant rule (Subsidiadas mode) still targets it by
name — dropping it would have silently broken that rule for Novos
while leaving the (harmless, identical) shared class doing nothing.

**Deliberately NOT migrated — genuinely already correct, not
avoidable-only-by-caution**: everything the shared `NX_SIM_UI` helper
renders (money/percent/date/segmented fields, buttons, the empty/error
states, the result hero and secondary grid) is untouchable by
construction (shared with Seminovos) — but it's also *already* the
literal source `.modBtn`/`.modField`/`.modEmptyState`/`.modErrorState`
were extracted from in Wave 3A, so it already reads as the same
product without a single class changing. The mode-nav (grouped by
Financiamento/Campanhas/Ferramentas), the balloon payment-structure
story, the schedule block, the Subsidiadas comparison card grid, and
the Cash Conversion classification badge are all Novos-specific
transactional compositions with no existing shared-system parallel —
left as-is, already restrained and Red-Precision-compliant (no medals,
no gradients, no marketing cards) per their own PORTAL-NEXT-08.2/.3/.4
UAT history.

**Transactional flow contract** (already satisfied by the existing
implementation, not newly built this Wave — recorded here because it's
the pattern a Seminovos migration, or any future transactional module,
should reproduce): mode-nav grouped by category → one form region
containing every input AND the primary CTA together (input and action
are never separated into different panels) → a separate result region
beside the form at ≥900px, stacked below it at <900px → the principal
output (the installment, or the classification for tools like Cash
Conversion) gets the largest single typographic treatment on the page,
everything else renders in a quieter secondary grid beneath it. No
change was needed to reach this — the module already had it.
shared `.modTable`'s own first-child sticky rule assumes the first
column is the one worth pinning while scrolling. Score's table leads
with a narrow rank column (`#`) but deliberately keeps the *second*
column (seller name) sticky instead. Migrating it naively would have
produced two competing `position:sticky; left:0` columns. Fix: cancel
the shared rule on the actual first column
(`.scPage .modTable td:first-child { position: static; background: none; }`)
and keep the module's own sticky rule on its real anchor column. Check
which column a migrating module actually wants pinned before assuming
it's the first one.
