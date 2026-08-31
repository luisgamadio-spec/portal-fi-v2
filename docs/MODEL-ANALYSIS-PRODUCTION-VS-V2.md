# Model Analysis — Production × V2 Column Diff (PORTAL-NEXT-07.3, Gate 5)

## Family-level miniGrid (14 items)

| Production item | V2 item (before) | Status | Functional source | Action |
|---|---|---|---|---|
| Volume vendido | — | MISSING_IN_V2 | `A.modelRowsUnified` rows, summed | RESTORE |
| Financiamentos | — | MISSING_IN_V2 | same | RESTORE |
| Penetração | — | MISSING_IN_V2 | derived | RESTORE |
| Produção | — | MISSING_IN_V2 | same | RESTORE |
| Receita | — | MISSING_IN_V2 | same | RESTORE |
| Receita SPF | — | MISSING_IN_V2 | same | RESTORE |
| Receita Total | — | MISSING_IN_V2 | same | RESTORE |
| Ticket médio | — | MISSING_IN_V2 | derived | RESTORE |
| Média de retorno | — | MISSING_IN_V2 | `A.familyExtraMetrics` (already exported, unused) | RESTORE |
| Prazo médio | — | MISSING_IN_V2 | `A.familyExtraMetrics` | RESTORE |
| Média de parcela | — | MISSING_IN_V2 | `A.familyExtraMetrics` | RESTORE |
| Entrada média | — | MISSING_IN_V2 | `A.familyExtraMetrics` | RESTORE |
| % Entrada médio | — | MISSING_IN_V2 | `A.familyExtraMetrics` | RESTORE |
| 🏆 Plano Destaque | Classificação dos Planos (5-card grid) | SEMANTIC_MISMATCH (both real, not a conflict) | already migrated | KEEP BOTH — production's family miniGrid box is a single "most-common plan" badge; V2's 07.1 Plan Classification block (5 cards with counts) is the SAME underlying `getPlanoDestaque`/`planoCounts` data already migrated and human-approved-by-UAT in 07.1 — not replaced, both stay |

## Per-model table (18 fields)

| Production item | V2 item (before) | Status | Functional source | Action |
|---|---|---|---|---|
| Modelo | Modelo | MATCH | — | keep |
| Volume / Qtd Vendida | Vendas | RENAMED (label only) | `r.volume` | keep V2 label (shorter, consistent with V2's KPI naming elsewhere) |
| Financiamento / Qtd Financiada | Financiamentos | RENAMED (label only) | `r.financiada` | keep V2 label |
| Penetração | Penetração | FORMAT_DIFFERENCE | plain `pct()` vs. production's `pctPenetracao` (< 40% flagged) | keep V2's own low-Penetração semantic token already used elsewhere in Dashbi (`.dbPenetracaoBaixa`), applied here too — same underlying threshold, no new business rule |
| Produção / Valor Produzido | Produção | RENAMED (label only) | `r.producao` | keep |
| Receita | — | MISSING_IN_V2 | `r.receita` (already on row) | RESTORE |
| Receita SPF | — | MISSING_IN_V2 | `r.receitaSPF` (already on row) | RESTORE |
| Receita Total | Receita Total | MATCH | `r.receitaTotal` | keep |
| Ticket Médio Financiado | Ticket | RENAMED (label only) | `r.ticket` | keep V2 label |
| Média Retorno | Retorno Médio | RENAMED (label only) | `r.retornoMedio` | keep V2 label |
| Prazo Médio | — | MISSING_IN_V2 | `r.prazoMedio` (already on row) | RESTORE |
| Média Parcela | — | MISSING_IN_V2 — **this is "Parcela Média"** | `r.pmtMed` (already on row) | RESTORE |
| Entrada Média | Entrada Média | MATCH | `r.entradaMed` | keep |
| % Entrada | Entrada % | RENAMED (label only) | `r.entradaPct` | keep V2 label |
| Qtd Linear | — | MISSING_IN_V2 | `r.linearQtd` (already on row) | RESTORE |
| Qtd Balão | — | MISSING_IN_V2 | `r.balaoQtd` (already on row) | RESTORE |
| Qtd Reversão | — | MISSING_IN_V2 | `r.reversaoQtd` (already on row) | RESTORE |
| Valor Médio Balão | — | MISSING_IN_V2 — **this is "Balão Médio"** | `r.balaoMed` (already on row) | RESTORE |
| (none) | Entrada Qtd | EXTRA_IN_V2 | `r.entradaQtd` | keep — real data, already correct, useful alongside Entrada Média/% |

## Plan tables

| Production item | V2 item (before) | Status | Functional source | Action |
|---|---|---|---|---|
| Resumo tipos de plano (family total, 1 row, 12 cols incl. 5 %) | — | MISSING_IN_V2 | `planTotalRowsForFamily` (not extracted) | EXTRACT + RESTORE |
| Quantidade por tipo de plano / Modelo (12 cols incl. 5 %) | Mix de Planos por Modelo (7 cols, no %) | MISSING_IN_V2 (partial — counts present, percentages absent) | `A.planRowsByModel` (already extracted) | RESTORE the 5 missing % columns onto the existing table |
| Quantidade por tipo de plano / Loja | — | MISSING_IN_V2 | `A.planRowsByStoreForFamily` (already exported, unused) | RESTORE |
| Detalhe COPARTICIPADO/SUBSIDIADO/REVERSÃO | — | MISSING_IN_V2 | `specialPlanDetailRows` (not extracted) | EXTRACT + RESTORE |
| Inconsistências TRITON (conditional) | — | MISSING_IN_V2 | `inconsistenciaTritonRows` (not extracted) | EXTRACT + RESTORE |

## Complete missing list (Gate 6)

1. Family-level miniGrid — entire section (14 metrics), all MATERIAL.
2. Receita, Receita SPF — per-model table, MATERIAL (Receita Total alone hides the SPF split already shown everywhere else in Dashbi).
3. Prazo Médio — per-model table, MATERIAL (installment-count average — see contracts doc; this **is** what "Média de Parcelas" means in production, not a second metric).
4. **Média Parcela ("Parcela Média")** — per-model table, MATERIAL. User-named example.
5. Qtd Linear, Qtd Balão, Qtd Reversão — per-model table, MATERIAL.
6. **Valor Médio Balão ("Balão Médio")** — per-model table, MATERIAL. User-named example.
7. Resumo tipos de plano (family total + 5 %) — MATERIAL.
8. 5 percentage columns on Quantidade por tipo de plano / Modelo — MATERIAL.
9. Quantidade por tipo de plano / Loja — MATERIAL.
10. Detalhe COPARTICIPADO/SUBSIDIADO/REVERSÃO — SECONDARY (drill-down detail, real and production-visible, still restored per Gate 17 — materiality does not authorize omission).
11. Inconsistências TRITON — DIAGNOSTIC (conditional data-quality surface, real, restored — same rule).

**Material missing after user's 2 named examples were excluded from the count: 9 further items** (family miniGrid counts as 1 section covering 13 numeric metrics) — confirms the brief's own warning that Balão Médio/Parcela Média were not the complete scope.
