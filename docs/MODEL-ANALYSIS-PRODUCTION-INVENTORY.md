# Model Analysis — Production Inventory (PORTAL-NEXT-07.3, Gate 3)

Rebuilt from a fresh read of `PORTAL-NEXT-07/.source/dashbi-origin-main.html` (==
`origin/main` SHA `2f17eb2341c5cc14aa8710aa044103002ca572a9`, re-confirmed unchanged
this Wave) — `renderModelos()` (lines 3999-4164) and every function it calls, not
from memory or the earlier 07.1 inventory.

## Render path (Gate 2)

`renderModelos(results)` — origin/main lines 3999-4164. Called from `render()`
(unconditional param) and `showTab('modelos', ...)`. Builds, in order: `planDiagnosticsHtml()`
(Base03 missing-column warning, conditional) → family header + vehicle selector →
**family-level "miniGrid"** (14 metric boxes) → **per-model indicators** (18-field
data contract, rendered as **cards + "Ver Detalhes" modal**, not a plain table —
see Control Type below) → **Inconsistências TRITON** table (conditional) →
**Resumo tipos de plano** (family total) → **Quantidade por tipo de plano / Modelo**
→ **Quantidade por tipo de plano / Loja** → **Detalhe COPARTICIPADO/SUBSIDIADO/REVERSÃO**.

**Control type — Model Analysis cards, real finding**: production's own source
comment (line 3052-3055) states this table was deliberately changed from an
18-column plain table to **compact cards (Volume/Financiada/Penetração only) + a
"Ver Detalhes" modal showing the other 15 fields** — `renderModelIndicatorsCards`/
`openModelDetailModal`, lines 3070-3100 — specifically because no legible font fits
18 numbered columns without horizontal scroll, even at 1920px. This is production's
own real, current solution to the same width problem this Wave's own Gate 24
describes. **V2 does not reproduce the card+modal shape** — see
`docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md`'s "Presentation decision" section for why
(the actual Design System authority, `data-table.md`, explicitly forbids
cardification: "Table remains table — MUST NOT auto-convert rows into cards").

## A) Family-level miniGrid (14 items, origin/main lines 4071-4086, exact order)

| # | Label (exact) | Field | Format | Source |
|---|---|---|---|---|
| 1 | Volume vendido | `totals.volume` | count | `rows.reduce(...volume)` |
| 2 | Financiamentos | `totals.financiada` | count | `rows.reduce(...financiada)` |
| 3 | Penetração | `pen` | % | `totals.volume ? totals.financiada/totals.volume : 0` |
| 4 | Produção | `totals.producao` | R$ | `rows.reduce(...producao)` |
| 5 | Receita | `totals.receita` | R$ | `rows.reduce(...receita)` |
| 6 | Receita SPF | `totals.receitaSPF` | R$ | `rows.reduce(...receitaSPF)` |
| 7 | Receita Total | `totals.receitaTotal` | R$ | `rows.reduce(...receitaTotal)` |
| 8 | Ticket médio | `ticket` | R$ | `totals.financiada ? totals.producao/totals.financiada : 0` |
| 9 | Média de retorno | `extraFam.retornoMedio` | % | `familyExtraMetrics()` |
| 10 | Prazo médio | `extraFam.prazoMedio` | `Nx` (1 decimal + "x") | `familyExtraMetrics()` |
| 11 | Média de parcela | `extraFam.pmtMed` | R$ | `familyExtraMetrics()` |
| 12 | Entrada média | `extraFam.entradaMed` | R$ | `familyExtraMetrics()` |
| 13 | % Entrada médio | `extraFam.entradaPct` | % | `familyExtraMetrics()` |
| 14 | 🏆 Plano Destaque | `getPlanoDestaque(modelPlanResults)` | badge | already migrated (07.1/07.2, Novos-only, nested in Model Analysis) |

Every box (2-13) that has a `prevX` argument also renders a `metricCompareBlock` (month-over-month delta) — **not migrated** (comparison-to-previous-period deltas are an established, documented deferral since PORTAL-NEXT-07, presentation-layer, out of scope here).

**No "Valor Médio Balão" at the family level** — confirmed absent from the miniGrid; it only appears per-model (item below). Not an omission to fix; production itself doesn't show it here.

## B) Per-model indicators — 18-field data contract (origin/main lines 4088-4107, exact order)

| # | Key | Label (exact) | Format |
|---|---|---|---|
| 1 | `Modelo` | Modelo | text (card title / not a "field" in the modal) |
| 2 | `volume` | Volume / Qtd Vendida | count |
| 3 | `financiada` | Financiamento / Qtd Financiada | count |
| 4 | `penetracao` | Penetração | % (via `pctPenetracao` — real threshold formatter, <40% flagged) |
| 5 | `producao` | Produção / Valor Produzido | R$ |
| 6 | `receita` | Receita | R$ |
| 7 | `receitaSPF` | Receita SPF | R$ |
| 8 | `receitaTotal` | Receita Total | R$ |
| 9 | `ticket` | Ticket Médio Financiado | R$ |
| 10 | `retornoMedio` | Média Retorno | % |
| 11 | `prazoMedio` | Prazo Médio | `Nx` (1 decimal) |
| 12 | `pmtMed` | Média Parcela | R$ |
| 13 | `entradaMed` | Entrada Média | R$ |
| 14 | `entradaPct` | % Entrada | % |
| 15 | `linearQtd` | Qtd Linear | count |
| 16 | `balaoQtd` | Qtd Balão | count |
| 17 | `reversaoQtd` | Qtd Reversão | count |
| 18 | `balaoMed` | Valor Médio Balão | R$ |

Source function: `modelRowsUnified(results, family)` — origin/main lines 3678-3701-ish (re-confirmed unchanged), **already extracted byte-identical in V2's adapter since PORTAL-NEXT-07** and **already computes every one of these 18 fields** (verified by direct read of `assets/js/adapters/dashbi.adapter.js` lines 962-1001). V2's UI (`dashbi.js`) currently renders only 11 of the 18 (see V2 inventory doc) — this is a **presentation gap, not a missing extraction**.

Note: `Entrada Qtd` is **not** a production column at this table — it's derived/available on the row object but not one of the 18 displayed fields. V2's current table shows it; flagged as EXTRA_IN_V2 in the diff doc (kept — it's real data, already correct, not invented).

## C) Inconsistências TRITON (conditional — only rendered if non-empty)

Columns: `Base`, `Cliente`, `Modelo original`, `Vendedor`. Source: `inconsistenciaTritonRows(results)` (origin/main lines 3930-3936) — **not yet extracted in V2**.

## D) Resumo tipos de plano (family total, 1 row)

Columns: Família, Financiamentos, Linear, Linear %, Balão, Balão %, Coparticipado, Coparticipado %, Subsidiado, Subsidiado %, Reversão, Reversão %. Source: `planTotalRowsForFamily(results, family)` (origin/main lines 3851-3874) — **not yet extracted in V2**.

## E) Quantidade por tipo de plano / Modelo

Same 12 columns as D, one row per model. Source: `planRowsByModel(results, family)` — **already extracted** in V2 (confirmed byte-identical), but V2's UI currently renders only 7 of the 12 columns (no percentage columns).

## F) Quantidade por tipo de plano / Loja

Same 12 columns as D, one row per loja. Source: `planRowsByStoreForFamily(results, family)` — **already extracted** in V2's adapter (confirmed exported), but **never called/rendered anywhere in V2's UI** — entire table missing from V2.

## G) Detalhe COPARTICIPADO / SUBSIDIADO / REVERSÃO

Columns: Loja, Modelo, Plano, Cliente, Produção, Receita — one row per financing record classified as COPARTICIPADO and/or SUBSIDIADO and/or REVERSÃO (label is a `" + "`-joined combination when a record matches more than one flag simultaneously — real, confirmed by direct read, not assumed impossible). Source: `specialPlanDetailRows(results, family)` (origin/main lines 3787-3801) — **not yet extracted in V2**, entire table missing.

## Base03 field dependencies (Gate 8)

| Semantic field | Source column (alias order) | Null handling | Eligibility | Aggregation |
|---|---|---|---|---|
| `parcelas` (Quantidade Parcelas) | `Op Fin - Quantidade Parcelas` / `Quantidade Parcelas` / `Parcelas` | 0 if no B03 match (`comp` null) | `parcelasQtd` denominator only counts records where `parcelas > 0` | sum/count → average (`parcelasMed`) |
| `pmt` (PMT / valor da parcela) | `Op Fin - PMT (R$)` / `PMT` / `Valor Parcela` | 0 if no B03 match | `pmtQtd` denominator only counts records where `pmt > 0` | sum/count → average (`pmtMed`) |
| `balaoValor` (Balão PMT) | `Op Fin - Balão PMT (R$)` / `Balão PMT` / `Balao PMT` | 0 if no B03 match | `balaoValorQtd` denominator only counts records where `balaoValor > 0` | sum/count → average (`balaoMed`) |
| `tcDevolvida` (TC Devolvida) | via `getTCDevolvidaValue` | already extracted, classification input | n/a | n/a |
| `codigoIF` (Código IF) | via `getCodigoIFValue` | already extracted, classification input | n/a | n/a |

All three (`parcelas`/`pmt`/`balaoValor`) are attached to every `fins` record inside
`processBase02` (origin/main lines 3340-3357, **already extracted byte-identical in
V2** — confirmed unchanged since PORTAL-NEXT-07). The averaging (`parcelasMed`/
`pmtMed`/`balaoMed`) happens in `rowsFromAgg` (origin/main lines 3193-3203, **already
extracted byte-identical in V2**, confirmed line-for-line).

## Metric semantics proved (Gates 9-11)

See `docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md` for the full numerator/denominator/
population/rounding contract of Parcela Média, Prazo Médio (= "Média de Parcelas" —
production does NOT have two separate metrics here, see that doc), and Balão Médio.

## Sorting (Gate 59)

`modelRowsUnified` sorts by `volume` desc, then `Modelo` alphabetically — no
production UI control to re-sort by another column. Not reproduced as sortable in
V2 (matches production; not invented).

## Column order (Gate 16, 49)

The 18-field order above is production's own literal array order — this is the
order V2 restores, not a V2 preference (see the metric-contracts doc for the one
disclosed adaptation: grouping headers, not reordering).
