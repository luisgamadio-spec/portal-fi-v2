# Dashbi Previous-Period Comparison Contract (FC-1/FC-1.1/FC-1.2, GAP-001)

## FC-1.2 fixes (Human UAT, 2026-09-05) — READ THIS FIRST

Human UAT on FC-1.1 found two defects; FC-1.1 was NOT approved.

**Defect B (data, the important one)**: "Vendas e Financiamentos por Loja"
showed the exact same store values regardless of the Grupo/Novos/Seminovos
selector. Root cause, confirmed by direct source read (and by a stash-based
before/after test run — the new test suite fails 9/11 checks against the
pre-fix code, passes 11/11 against the fix): `storeTableHtml(A, out, ...)`
always read `out.aggs`, computed ONCE by `compute()`/`buildRealOut()` over
the FULL, cross-department `sales`/`fins` arrays. `aggregate()` itself has
NO department parameter — `vendasLoja`/`finLoja`/`vendasVendDept`/
`finVendDept` accumulate whatever rows they're handed, with no `dept` check
(confirmed by direct source read of `dashbi.adapter.js`'s `aggregate()`).
This is UNLIKE `vendasModelo`/`finModelo`/`compModelo` (Model Analysis),
which hardcode `if (r.dept==='Novos')` INSIDE `aggregate()` itself — which
is exactly why Model Analysis was never affected by this defect, and why
Ranking (which already used the correctly department-filtered
`salesView`/`finsView`, not `out` directly) was never affected either.
Classification: **RENDER_USES_WRONG_DATASET**. Fix: `renderPanel()` now
re-aggregates from the SAME already-computed `salesView`/`finsView` per
`currentDeptView` (mirrors V1's own `agView = aggregate({sales,fins})`
pattern exactly) before calling `storeTableHtml`, for BOTH the current and
the previous period (Gate 12 — an unscoped previous period would have been
a subtler instance of the identical defect). No RPC/adapter/provider
change — `aggregate()` was already correct for whatever it's given; the
defect was entirely in which dataset `renderPanel()` handed it.

**Defect A (alignment)**: the current/previous+arrow model itself (approved
in FC-1.1) is unchanged. Only the geometry was fixed: a CSS Grid cell
(`.dbNumCompare`, `dashbi.css`) makes the previous number's digits land on
the exact same right edge as the current number, with the arrow in a
separate grid column that never shifts either number — proven pixel-exact
(not just class presence) in `tests/dashbi-fc12-alignment-test.py`. Applied
to `storeTableHtml`'s 5 primary columns and `modelCellHtml` (all 19 compared
Model Analysis columns); KPI cards are explicitly exempt (isolated blocks,
don't need forced right-alignment) and keep `previousValueHtml`'s simple
inline-flex line unchanged.

Verification: 26/26 golden + 36/36 real-provider + 16/16 comparison-parity
+ 27/27 FC-1.1 presentation/navigation all unchanged (business logic and
the dual-period engine untouched) + 24 new FC-1.2 checks (11 scope + 13
alignment geometry). `REAL_MASTER_RUNTIME_VALIDATION_UNAVAILABLE` — this
session had no live homolog login session to validate August 2026 data
directly; relied on the mocked real-transport harness and the golden
fixture's own multi-department, multi-store shape instead.

## FC-1.1 revision (Human UAT, 2026-09-05)

FC-1's percent-delta presentation ("▲ +12,4%", "Anterior: X") was **not
approved** by Human UAT. Current rule, implemented in FC-1.1:

```
CURRENT VALUE
PREVIOUS VALUE + DIRECTION ARROW   (▲ / ▼ / → / — )
```

No percent, no "Anterior:" label. `A.calcDelta` (the byte-identical `(c-p)/p`
extraction below) is **kept in the adapter, unused by the UI** — Gate 10 of
the FC-1.1 brief explicitly allows the percentage to remain internally
calculable, just not displayed. `deltaHtml` (FC-1's presentation function) was replaced by
`previousValueHtml` in `assets/js/dashbi.js`; `kpiCompareHtml` keeps its name
with a new body. This file is updated in place rather than superseded, since
the underlying dual-period engine (this file's own subject) is unchanged by
FC-1.1 — only the presentation layer changed.

Arrow semantics: `▲` current > previous, `▼` current < previous, `→` current
= previous (including `0 = 0`), `—` previous value itself unavailable
(distinct from previous = 0, which shows as a real "0 ▲/▼/→"). The arrow is
a plain numeric-comparison result now, not derived from `calcDelta` (which
existed specifically to guard percentage division-by-zero — irrelevant once
percentage isn't shown). Previous value uses the exact same formatter as
current (money/pct/num) at every call site. Accessibility: visually only the
previous value + arrow are shown; a visually-hidden `.srOnly` span carries
the equivalent context ("valor anterior X; valor atual aumentou/diminuiu/
permaneceu igual") for assistive tech.

**Also removed in FC-1.1** (information architecture, human decision,
unrelated to the comparison engine): the "Vendas e Financiamentos por
Vendedor" table in Visão Geral. `GENERAL_SELLER_TABLE → REMOVED_FROM_V2_
GENERAL_VIEW → REDUNDANT_WITH_RANKING` — the table existed in V2 since the
original Dashbi migration (PORTAL-NEXT-07) and was extended with comparison
support in FC-1; it was deliberately removed from the Visão Geral by explicit
human product decision this Wave, not because it "never existed". Ranking
(pre-existing, untouched) is the dedicated seller-performance surface going
forward. Capability-parity check against Ranking (this Wave's Gate 15):
`DETAIL_CAPABILITY_PRESERVED_BY_RANKING`, with one disclosed nuance —
Ranking shows the top 10 sellers by Receita Total, while the removed table
showed every seller sorted by Vendas qtd; the metric set itself (Vendas,
Financiamentos, Share, Produção Total, Receita Total, plus a Receita/Receita
SPF/Retorno detail group) is identical either way. `sellerTableHtml()` and
`SELLER_HEADERS` were deleted from `dashbi.js` (their only caller was the
removed heading); the underlying aggregate data
(`aggs.vendasVendDept`/`finVendDept`) is untouched in the frozen adapter.

Also relocated: the Visão Geral/Análise por Modelos/Ranking/Novos por Loja
subnav now renders in its own static shell slot (`#dbSubnav`, between the
module header and the filters — `pageShellHtml()`), not at the bottom of
`#dbPanel`'s own rebuilt content as in FC-1/PORTAL-NEXT-07.2 — it was
reachable only after scrolling past the KPIs/tables/Model Analysis. One
subnav instance only; the `.dbViewGroup` (Grupo/Novos/Seminovos) filter is
untouched and unmerged with it.

## FC-1 original (superseded presentation, engine unchanged) — history below

V1×V2 Feature Completeness Audit (2026-09-04) traced the human-reported
"missing comparativo com o mês anterior" to Dashbi specifically — Score and
Análise F&I do Grupo never had this capability, in V1 or in production. This
Wave (FC-1) restores it in V2's Dashbi, and only there.

## Source authority (byte-identical extraction)

```
FILE:    modules/analise-geral-grupo-secure-original-layout.html
        (portal-financiamento-brabus-secure)
LINES:      3112-3125 (period), 3151-3174 (delta/comparison)
FUNCTIONS:     lastDayOfMonth, sameDayPreviousMonth,
             getPreviousMonthComparablePeriod, calcDelta -- byte-identical,
             assets/js/adapters/dashbi.adapter.js
             formatDelta, comparisonBlock, valueWithDelta,
             metricCompareBlock -- presentation-only in V1 (HTML/CSS
             strings), reimplemented in assets/js/dashbi.js as
             deltaHtml/kpiCompareHtml using V2's own class vocabulary
             (Gate 18, FC-1 brief), same "V2 builds its own presentation"
             precedent as every prior Dashbi Wave.
```

## The semantic, precisely (Gate 6/7, FC-1 brief)

NOT "current calendar month vs. previous full calendar month". The previous
period is a **day-aligned equivalent period**: `sameDayPreviousMonth(d)`
subtracts one month from `d` and clamps the day to the target month's last
day if needed (e.g. Jan 31 -> Feb 28/29, never Mar 3). `getPreviousMonthComparablePeriod(start,end)`
applies this to `start` and `end` **independently** — for a multi-month custom
range this shifts each endpoint back by one month, not the whole span. See
`tests/dashbi-comparison-parity-test.py` (16 checks) for the exhaustive edge
matrix: January rollover, non-leap/leap February, 30-day-month clamp, partial
current month, closed full month, custom multi-month range, missing base.

## Delta formula (kept internally, FC-1.1: no longer displayed)

`calcDelta(current, previous) = (current - previous) / previous`, `null` when
`previous` is `0`/`null`/non-finite. This function is still exported on
`NX_DASHBI_ADAPTER` (unused by the UI since FC-1.1 — Gate 10 of that
revision's brief keeps it available for any future internal need) but no
longer drives the visible presentation, which since FC-1.1 shows the
previous value itself + a plain direction arrow instead (see the FC-1.1
section above). Up/down/flat is a pure math direction, not a performance
judgment (Gate 18, both waves) — every surface below is a generically
more-is-better metric, same uncontextualized coloring V1 itself used.

## Restored surfaces (mapped onto V2's actual UI, not V1's literal tables — Gate 15, disclosed adaptation)

V1 compared 4 surfaces: KPI cards, "Detalhe principal" (Loja|Dept combined
table), Share/Retorno cards, and Model Analysis. V2 never built a distinct
Loja|Dept "Detalhe principal" table or a separate Share/Retorno card grid —
its Loja/Vendedor detail lived in `storeTableHtml`/`sellerTableHtml` (the
Share metric folded in as one column, per PORTAL-NEXT-07.2's own "`overview`
stands in for production's default Share/Retorno tab" decision, made
independently of FC-1). FC-1 restored comparison onto both tables; FC-1.1
then removed `sellerTableHtml` from Visão Geral entirely (see the FC-1.1
section above) — its comparison support was removed along with it, not
adapted further (that Wave's own explicit instruction). Current surfaces:

| V1 surface | V1 metrics compared | V2 surface | V2 metrics compared |
|---|---|---|---|
| KPI cards do topo | Vendas, Financiamentos, Penetração, Receita, Receita SPF, Receita Total, Produção Total, Retorno médio | KPI grid + detail panel | same 8 |
| Detalhe principal (Loja\|Dept) | vendas, fin, penetração, receita, receitaSPF, receitaTotal, produção, retorno | `storeTableHtml` (por Loja) | same 8 (the Vendedor\|Dept half, `sellerTableHtml`, was removed in FC-1.1 — see above) |
| Share/Retorno cards | vendas, fin, penetração, receitaTotal, receita, receitaSPF, produção, retorno | (already merged into `storeTableHtml`/the former `sellerTableHtml` by V2's own prior design, not by FC-1) | — |
| Modelos (19 columns) | volume, financiada, penetração, produção, receita, receitaSPF, receitaTotal, ticket, retornoMédio, prazoMédio, pmtMed, entradaMed, entradaPct, linearQtd, balaoQtd, reversaoQtd, coparticipadoQtd, subsidiadoQtd, balaoMed | `modelPrimaryDetailTableHtml` + `familyMetricGridHtml` | same 19 |

**Not restored, matching V1exactly (no comparison there either)**: Painel
"Resultado da loja" quando uma loja é filtrada, Ranking, Novos por Loja —
V1 never compared these, so V2 doesn't either (would be an enhancement, not
a migration — out of this Wave's scope, Gate 16).

## Dual-period architecture (Gate 9-11, FC-1 brief)

`compute(fixture)` has a single-period signature — restoring comparison
needed a SECOND, independently-computed aggregate, not a UI-only change:

- **Fixture/demo mode**: `compute()` is period-agnostic (no date-range
  filtering inside it at all — a fixture already IS a period). The previous
  period is therefore an explicit second fixture pick ("Comparar com" select,
  defaulting to "Nenhuma"), not auto-derived from a date range. `A.compute()`
  called again, unchanged, against that second fixture's own raw rows —
  SAME_PIPELINE_DIFFERENT_PERIOD, no separate/simplified previous-period
  logic. Never auto-selected, so every existing golden-fixture-driven test/
  screenshot that doesn't touch this control is byte-unaffected.
- **Real transport**: `dashbi-real-provider.js`'s `loadDashbiRealWithComparison`
  computes the previous comparable period from the current `p_start`/`p_end`
  (local-calendar-date parsing/formatting throughout — Gate 8, never
  `toISOString()`, so the day never shifts across a UTC boundary the way
  Score's own known UTC-boundary defect does) and calls the SAME
  `loadDashbiReal()` twice — once per period, same two RPCs
  (`operational_metrics`, `operational_model_metrics`) both times.

## Failure mode (Gate 12)

Current period is primary. Previous-period fetch failing (real transport)
or being unset (fixture mode: no comparison fixture picked) renders the
current dashboard normally with comparison simply omitted — never a reason
to fail or alter the current period's own render. A blocked previous period
(missing-seller hard-stop) is treated the same way: "no comparison
available", not an error surfaced to the user.

## Verification

- `tests/dashbi-parity-test.py`: 26/26 (unchanged through both waves, golden business logic frozen — Gate 26).
- `tests/dashbi-real-provider-test.py`: 36/36 (FC-1: 33/33, including 2 dual-fetch checks + a capture-mechanics fix for the new 2-calls-per-RPC architecture; FC-1.1 added 3 more Gate-12 failure-mode checks). Untouched by FC-1.1's presentation change (this file exercises the transport layer, not the DOM).
- `tests/dashbi-comparison-parity-test.py`: 16/16 — calcDelta edge cases (still valid, the formula is unchanged, just unused by the UI), day-alignment matrix, scope-preservation, one real cross-fixture delta matching a hand-computed value exactly.
- `tests/dashbi-fc11-presentation-test.py` (new, FC-1.1): 27/27 — seller-table removal, current/previous+arrow presentation (no percent, no "Anterior:" label, only ▲▼→ glyphs), accessibility (`.srOnly` context, visually clipped), subnav single-instance/position/active-state/filter-persistence/Novos-por-Loja-availability, and 1024×768 + mobile responsive (0 horizontal overflow, subnav reachable without scrolling).

## Explicitly out of scope this Wave (Gates 29-33)

No global cross-module comparison framework (Score/Análise F&I never had this
capability — not added to either). No CSV/XLSX export (GAP-004, FC-2). No
Score drill-down (GAP-002, FC-4). Live MASTER/VENDEDOR homolog UAT — this
session had no live login session to exercise; classification is
`GAP001_DASHBI_PREVIOUS_PERIOD_TECHNICALLY_HOMOLOGATED_LOCAL`, same
evidentiary shape Dashbi Phase 2's own real-data-integration note already
uses for its own pending human checkpoint.
