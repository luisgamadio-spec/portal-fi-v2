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
