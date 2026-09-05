# Dashbi Previous-Period Comparison Contract (FC-1, GAP-001)

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

## Delta formula

`calcDelta(current, previous) = (current - previous) / previous`, `null` when
`previous` is `0`/`null`/non-finite (rendered as "— sem base anterior", never
a divide-by-zero). Up/down/flat coloring is a pure math direction, not a
performance judgment (Gate 18) — every surface below is a generically
more-is-better metric, same uncontextualized coloring V1 itself used.

## Restored surfaces (mapped onto V2's actual UI, not V1's literal tables — Gate 15, disclosed adaptation)

V1 compared 4 surfaces: KPI cards, "Detalhe principal" (Loja|Dept combined
table), Share/Retorno cards, and Model Analysis. V2 never built a distinct
Loja|Dept "Detalhe principal" table or a separate Share/Retorno card grid —
its Loja/Vendedor detail already lives in `storeTableHtml`/`sellerTableHtml`
(the Share metric folded in as one column, per PORTAL-NEXT-07.2's own
"`overview` stands in for production's default Share/Retorno tab" decision,
made independently of FC-1). Comparison is therefore restored onto V2's
actual 3 surfaces, covering the same underlying metric set V1 compared:

| V1 surface | V1 metrics compared | V2 surface | V2 metrics compared |
|---|---|---|---|
| KPI cards do topo | Vendas, Financiamentos, Penetração, Receita, Receita SPF, Receita Total, Produção Total, Retorno médio | KPI grid + detail panel | same 8 |
| Detalhe principal (Loja\|Dept) | vendas, fin, penetração, receita, receitaSPF, receitaTotal, produção, retorno | `storeTableHtml` (por Loja) + `sellerTableHtml` (por Vendedor\|Dept) | same 8, split across the two tables V2 already ships |
| Share/Retorno cards | vendas, fin, penetração, receitaTotal, receita, receitaSPF, produção, retorno | (already merged into the two tables above by V2's own prior design, not by FC-1) | — |
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

- `tests/dashbi-parity-test.py`: 26/26 (unchanged, golden business logic frozen — Gate 26).
- `tests/dashbi-real-provider-test.py`: 33/33 (26 pre-existing + 2 new FC-1 dual-fetch checks; one pre-existing check's capture mechanics needed updating for the new 2-calls-per-RPC architecture, documented in the test file itself).
- `tests/dashbi-comparison-parity-test.py` (new): 16/16 — calcDelta edge cases, day-alignment matrix, scope-preservation (identical current/previous fixture -> every delta flat), and one real, non-degenerate cross-fixture delta matching a hand-computed value exactly.

## Explicitly out of scope this Wave (Gates 29-33)

No global cross-module comparison framework (Score/Análise F&I never had this
capability — not added to either). No CSV/XLSX export (GAP-004, FC-2). No
Score drill-down (GAP-002, FC-4). Live MASTER/VENDEDOR homolog UAT — this
session had no live login session to exercise; classification is
`GAP001_DASHBI_PREVIOUS_PERIOD_TECHNICALLY_HOMOLOGATED_LOCAL`, same
evidentiary shape Dashbi Phase 2's own real-data-integration note already
uses for its own pending human checkpoint.
