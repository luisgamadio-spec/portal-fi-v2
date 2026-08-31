# Model Analysis — No-Scroll Design (PORTAL-NEXT-07.4)

## Problem

PORTAL-NEXT-07.3's completeness restoration produced an 18-column grouped table
that required horizontal scrolling at **every** viewport, including 1920×1080
(1855px content in a 1324px container). Human UAT rejected this presentation
outright, superseding the earlier "wide table + scroll" decision from 07.3 (which
had itself been flagged HUMAN REVIEW REQUIRED for exactly this reason).

## Solution shape

**Primary comparison row + inline "+ Detalhes" expansion**, per production
interaction evidence (Gate 9-10): production's own current UI already shows a
reduced default (Volume/Financiada/Penetração) with the rest behind a
"Ver Detalhes" control — this Wave keeps that *shape* (reduced default + one-click
full detail) but changes the *mechanism* from a modal to an **inline, vertical
expansion directly below the row**, per explicit human preference, and allows
**multiple rows expanded simultaneously** (production's modal is necessarily
one-at-a-time; the human explicitly wants side-by-side comparison of 2+ expanded
models).

## Primary column tiers

- **Always primary** (every viewport): Modelo, Volume, Financiamentos, Penetração.
- **Desktop-enhanced primary** (≥768px, CSS `.dbDesktopCol`): + Produção, Receita
  Total, Ticket Médio, Retorno Médio.
- Below 768px these 4 columns are hidden from the primary row (Gate 24: "may
  reduce the primary visible metric set on mobile ONLY IF all remaining metrics
  are immediately available through + Detalhes") — they are *also* always present
  in the detail panel's "Financeiro"/"Retorno" groups, so mobile users lose
  nothing, just reach them via one click instead of seeing them inline.

## Detail groups (presentational only, 0 new business category)

Reused production's own family-miniGrid grouping concept, not invented fresh:

- **Financeiro**: Produção, Receita, Receita SPF, Receita Total, Ticket Médio.
- **Retorno**: Retorno Médio.
- **Parcelamento**: Prazo Médio, Parcela Média.
- **Entrada**: Entrada Qtd, Entrada Média, Entrada %.
- **Planos**: Qtd Linear, Qtd Balão, Qtd Reversão, Balão Médio.

Every group label maps to one or more of production's own 18 fields 1:1 — no
formula, population, denominator, or inclusion rule changed. See
`docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md` (unchanged since 07.3) for the exact
semantics, and `docs/MODEL-ANALYSIS-PRIMARY-DETAIL-MAP.md` for the complete
per-metric final-location mapping.

## Interaction contract

- `+ Detalhes` / `− Detalhes` — real `<button>`, `aria-expanded`, `aria-controls`
  pointing to a real `<tr id="...">` detail row (Gate 17-18, verified).
- Multiple rows may be expanded simultaneously (Gate 15) — no accordion
  single-open constraint; no technical/accessibility blocker was found that would
  require overriding this explicit human preference.
- Toggling calls the same `render()` pipeline as every other Dashbi interaction
  (family switch, view switch, mode switch) — consistent with the codebase's
  existing pattern, not a new mechanism.
- Expansion state (`expandedKeys`) is a module-level JS object, namespaced per
  table (`modelIndicators`, `storeTable`, `sellerTable`, `ranking-vendedor`,
  `ranking-loja`, `ranking-dept`, `novosLoja`, `planTotal`, `planModel`,
  `planStore`) — a row's key is its identity (Modelo/Loja/Vendedor|Dept/etc.).
- **Reset on family switch** (Gate 16/44): `resetExpanded('modelIndicators')` runs
  on every `.dbVehicleCard` click — the safe default the brief itself prescribed,
  since a different family means an entirely different set of model rows/keys;
  persisting stale keys across families risked orphaned detail rows.
- **Persists across period/fixture/view changes** (Gate 45): nothing resets
  `expandedKeys` on those triggers — `render()` rebuilds the table from fresh
  `results`, and any row whose key is still marked expanded gets its detail rebuilt
  with the current filtered data, so an open row never shows stale values.

## Applied to every Dashbi table that needed it, not just Model Analysis

Same shared component (`expandableRow`/`detailToggleHtml`/`detailRowHtml` in
`assets/js/dashbi.js`), reused for:

- Store/Seller tables (Visão Geral) — primary: identity + Vendas/Financiamentos/
  Share; detail: Depto (seller only) + Produção/Receita.
- Ranking (×3: Vendedores/Lojas/Departamentos) — primary: #/Nome/Vendas/
  Financiamentos/Receita Total; detail: Penetração/Produção/Retorno.
- Novos por Loja — primary: Loja/Vendidos/Financiados/Plano Destaque; detail:
  Balão/%Balão/Subsidiada/Coparticipada/Reversão/Linear.
- Model Analysis's 3 plan-mix tables (Resumo/Modelo/Loja) — primary: label/
  Financiamentos/Linear/Balão; detail: all 5 percentage pairs + Coparticipado/
  Subsidiado/Reversão counts.

None of these tables' underlying business logic, sorting, or golden-fixture
contracts changed — confirmed via `git diff` showing 0 lines changed in
`dashbi.adapter.js`, `_dashbi-reference.js`, or `dashbi-fixtures.json` this Wave.

## A real bug self-caught during verification (Gate 96 disclosure)

The first working version passed every *document-level* `scrollWidth` check
(Gate 3's literal assertion) but still had a **hidden component-level horizontal
scrollbar**: `.dbTableWrap`'s own `overflow-x: auto` was silently absorbing
overflow from the table growing past its container whenever a detail row was
open — invisible to a page-level check, but a real horizontal-scroll dependency
by the letter of the directive (Gate 2 explicitly lists `overflow-x:auto`
causing horizontal scroll as something to search for). Found by directly
comparing `.dbTableWrap`'s `scrollWidth` vs `clientWidth`, not by trusting the
document-level number alone. Root cause: `.dbDetailPanel`'s wrapping layout
reported a min-content width wide enough to grow the whole `<table>` under its
default `auto` layout (this is how HTML tables size themselves — from the
widest cell's content, across every row, including a colspan'd detail row).
Fixed with `table-layout: fixed` on every `.dbTableExpandable`/
`.dbTableWrapText` table, which decouples column widths from any single row's
content. Two further residuals surfaced only after that fix (both similarly
self-caught, not reported by any single-viewport spot-check): long header
labels ("FINANCIAMENTOS") and the toggle button's own text not fitting their
newly-fixed column widths, each independently bleeding a few px of ink overflow
into the same hidden scrollbar. Both fixed by allowing text to wrap
(`overflow-wrap`/`word-break`) instead of forcing a single line, plus a
guaranteed fixed-pixel width for the toggle column and a floor share for the
identity column so real values (vendor names, "OUTLANDER SIGNATURE") don't
wrap character-by-character either. Final verification checks BOTH
document-level and every `.dbTableWrap`'s own `scrollWidth` vs `clientWidth`,
with every detail panel open simultaneously (the worst case) — this is the
check that would have caught the original bug and didn't exist until this was
found, so it's now the standing verification method for this component.

## Verification

Automated sweep, checking BOTH document-level `scrollWidth` AND every
`.dbTableWrap`'s own component-level `scrollWidth` vs `clientWidth` (the check
that catches the hidden-scrollbar class of bug above): 48/48 view×mode×viewport
combinations (8 scenarios × 6 viewports) pass with 0 overflow at either level,
tested with every visible detail panel open simultaneously (the worst-case
width). Full 26-fixture × 3-family sweep at 360px (the narrowest required
viewport) with every visible detail toggle opened: 0 overflow at either level,
0 console errors.
