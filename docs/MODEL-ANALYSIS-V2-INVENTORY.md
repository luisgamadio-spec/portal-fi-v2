# Model Analysis — V2 Inventory BEFORE PORTAL-NEXT-07.3 (Gate 4)

Rebuilt from a fresh read of `assets/js/dashbi.js`'s `modelAnalysisHtml()` (as it
stood at commit `343c10f`, end of PORTAL-NEXT-07.2) — not from memory of what was
intended.

## Family-level miniGrid

**Absent entirely.** V2 never built a family-level aggregate block — no Volume
vendido/Financiamentos/Penetração/Produção/Receita/Receita SPF/Receita Total/Ticket
médio/Média de retorno/Prazo médio/Média de parcela/Entrada média/%Entrada médio at
the family (all-models-in-family) level. Only Plano Destaque exists at that level
(via `planClassificationHtml`, itself covering all 5 plan types, not the family
miniGrid's single "🏆 Plano Destaque" badge).

## Per-model table ("Indicadores por Modelo" table, `.dbModelSection`'s first `tableHtml`)

| # | Column (V2) | Source | Note |
|---|---|---|---|
| 1 | Modelo | `r.Modelo` | matches production |
| 2 | Vendas | `r.volume` | matches production's "Volume / Qtd Vendida" (renamed label) |
| 3 | Financiamentos | `r.financiada` | matches production's "Financiamento / Qtd Financiada" (renamed label) |
| 4 | Penetração | `A.pct(r.penetracao)` | plain `pct()`, **not** production's `pctPenetracao` threshold formatter |
| 5 | Produção | `A.money(r.producao)` | matches "Produção / Valor Produzido" (renamed label) |
| 6 | Receita Total | `A.money(r.receitaTotal)` | matches, but Receita/Receita SPF individually **absent** |
| 7 | Ticket | `A.money(r.ticket)` | matches "Ticket Médio Financiado" (shortened label) |
| 8 | Retorno Médio | `A.pct(r.retornoMedio)` | matches "Média Retorno" |
| 9 | Entrada Qtd | `r.entradaQtd` | **not** a production column at this table (EXTRA_IN_V2) |
| 10 | Entrada Média | `A.money(r.entradaMed)` | matches |
| 11 | Entrada % | `A.pct(r.entradaPct)` | matches "% Entrada" |

**Absent from this table**: Receita, Receita SPF (shown combined as Receita Total only), Prazo Médio, Média Parcela, Qtd Linear, Qtd Balão, Qtd Reversão, Valor Médio Balão — 7 of production's 18 fields.

## Plan mix table ("Mix de Planos por Modelo")

| # | Column (V2) | Note |
|---|---|---|
| 1 | Modelo | matches |
| 2 | Financiamentos | matches |
| 3 | Linear | matches (count only) |
| 4 | Balão | matches (count only) |
| 5 | Coparticipado | matches (count only) |
| 6 | Subsidiado | matches (count only) |
| 7 | Reversão | matches (count only) |

**Absent**: all 5 percentage columns (Linear %/Balão %/Coparticipado %/Subsidiado %/Reversão %). This one V2 table is a partial analog of production's "Quantidade por tipo de plano / Modelo" (E) — production's "Resumo tipos de plano" family total (D), "Quantidade por tipo de plano / Loja" (F), and "Detalhe COPARTICIPADO/SUBSIDIADO/REVERSÃO" (G) have **no V2 analog at all**.

## Missing entire sections

- Inconsistências TRITON (conditional table) — absent.
- Resumo tipos de plano (family total row) — absent.
- Quantidade por tipo de plano / Loja — absent.
- Detalhe COPARTICIPADO / SUBSIDIADO / REVERSÃO — absent.

## Vehicle selector

Present, unchanged since PORTAL-NEXT-07.1 (`vehicleSelectorHtml()`) — out of scope for this Wave (Gate 61 regression-only).

## Business logic already extracted and available, unused

`modelRowsUnified` (adapter) already returns `receita`, `receitaSPF`, `parcelasMed`, `pmtMed`, `linearQtd`, `balaoQtd`, `reversaoQtd`, `balaoMed` on every row — confirmed by direct read of `assets/js/adapters/dashbi.adapter.js` lines 962-1001 — **V2's UI simply never rendered them**. `familyExtraMetrics` and `planRowsByStoreForFamily` are exported from the adapter's public API but never called from `dashbi.js`. This means most of the restoration in this Wave is a presentation gap, not a missing-extraction gap — see `docs/MODEL-ANALYSIS-PRODUCTION-VS-V2.md`.
