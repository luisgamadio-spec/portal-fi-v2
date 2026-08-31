# Gestão KPI Contract (Gate 13, 135)

Every KPI below is transcribed from `render()` (origin/main lines 2310-2455) exactly as production computes and labels it — nothing inferred from a label alone (Gate 13's own rule). **Gestão has no Vendas/Financiamentos/Share/Penetração/Receita/Ticket Médio/Retorno Médio KPIs, no charts, no FECHAMENTO, no Model Analysis, no Seller Analysis, and no export** — confirmed by direct source read (0 matches for any of these concepts anywhere in the 2477-line file). This is real architecture, not an oversight or a migration gap; each is reported N/A below rather than invented.

## Produção Paga / Produção Faturada / Produção Ag. Faturamento (4 cards)

```
SOURCE:       prodSummary(operacional, status) for each of PAGA/FATURADA/
             AG. FATURAMENTO
FORMULA:        qtd = count of operational rows with that exact status
             valor = sum(valorFinanciado) for that status
             + Novos/Seminovos split (qtd + valor) unless a vehicle
             filter narrows to one department, in which case the card
             shows only that department's total (productionCard()'s
             `isFiltered` branch)
DENOMINATOR:      N/A (a count/sum, not a ratio)
FILTER SCOPE:       period + store + vehicle (applied upstream, to `operacional`)
ROUNDING:            money(): pt-BR currency, 0 decimal places
                  (maximumFractionDigits:0)
DISPLAY UNIT:          BRL currency + integer count
GOLDEN TEST:             tests/fixtures/gestao-fixtures.json:
                       status_ag_faturamento_variantes (spelling-variant
                       normalization), multi_store_bank
```

## Produção Total (4th card)

```
SOURCE:       prodTotalSummary(operacional)
FORMULA:        same shape as above, but status ∈ {PAGA, FATURADA, AG.
             FATURAMENTO} combined — i.e. exactly the OPERACIONAL set.
             Historical note (source comment, lines 2209-2213): this
             invariant was NOT always true — an earlier version silently
             dropped AG. FATURAMENTO from this specific card, diverging
             from every other indicator. Current production has already
             fixed this; V2 reproduces the CURRENT (fixed) behavior.
GOLDEN TEST:     status_ag_faturamento_variantes
```

## Valor de Produção Total (executive KPI)

```
SOURCE:       = prodTotalSummary(operacional).valor (same value as the
             "Produção Total" card's valor)
DISPLAY HINT:      "Paga + Faturada • {tipo}" -- NOTE: this hint text is
                 IMPRECISE in production itself (it omits AG.
                 FATURAMENTO, which the underlying value DOES include
                 per the fix above) -- a real, observable production
                 quirk. Gate 64 (No Cleanup Drift) forbids silently
                 "fixing" this hint text during migration; V2 reproduces
                 the same hint text verbatim, not a corrected one.
```

## Valor Total de Propostas Perdidas (executive KPI)

```
SOURCE:       sum(cpf.recusadas.map(r => r.valor))
MEANING:        total of the SINGLE largest financed value found per
             CPF counted as a net refusal (buildCpfAnalysis) -- NOT a
             sum of every refused row; each CPF contributes once, at
             its own max observed value.
DENOMINATOR:      N/A
GOLDEN TEST:        cpf_recusa_liquida, cpf_recusa_anulada_cancelada
```

## Valor de Propostas em Aberto (executive KPI)

```
SOURCE:       sum(cpf.aprovadas.map(r => r.valor)) -- same "one CPF,
             max value" rule as above, for CPFs whose final valid
             status is in STATUS_APROVADAS_VALIDAS and that have NOT
             yet reached an operational status.
GOLDEN TEST:        cpf_aprovada_valida, cpf_aprovada_mas_ja_operacional
```

## Classificação dos Planos (5 cards: SUBSIDIADO/REVERSÃO/COPARTICIPADO/BALÃO/LINEAR)

```
SOURCE:       buildPlanAnalysis(baseOperacionalContexto) -- note this
             uses the CONTEXTO population (includes auxiliary opcional
             rows), not the narrower `operacional` used by the
             Produção cards.
FORMULA:        one classified proposal (deduped by proposalKey, highest-
             priority signal across all its rows wins) per plan type;
             qtd = proposal count, valor = sum of each proposal's own
             (max-observed) valorFinanciado.
DENOMINATOR:      N/A
GOLDEN TEST:        subsidiado_codigo_if, reversao_codigo_if,
                  coparticipado_tc_devolvida, balao_pmt,
                  priority_collision, multi_row_proposal_plan_signal
```

## Planos por Loja e Departamento (2 tables: Novos / Seminovos)

```
SOURCE:       buildPlanStoreDeptAnalysis(baseOperacionalContexto)
FORMULA:        per loja, counts of each plan type among that store's
             proposals, split by department.
CRITICAL SCOPE NOTE: Novos tracks LINEAR/BALÃO/SUBSIDIADO/REVERSÃO/
             COPARTICIPADO (5 types); Seminovos tracks ONLY LINEAR/
             BALÃO/REVERSÃO (3 types) -- SUBSIDIADO and COPARTICIPADO
             are NOT counted into any Seminovos column, even if a
             Seminovos proposal is itself classified as one of those
             two types elsewhere (it still counts toward Seminovos
             `total`, just not a named column). Confirmed real
             production behavior (both the aggregation function's own
             field set AND the render() table headers agree), not
             invented and not "fixed" to add the missing columns.
GOLDEN TEST:        seminovos_plan_scope
```

## SPF EXTRA — Total (KPI card)

```
SOURCE:       buildSpfExtraAnalysis(baseOperacionalContexto).total
FORMULA:        sum of Opcional - Valor (R$) across every auxiliary row
             whose Opcional - Nome contains "SPF EXTRA", deduplicated
             by proposal+value, grouped by loja+departamento.
STATUS:                  ordinary PASS — not commission-dependent (the
                        raw value, before any multiplier).
GOLDEN TEST:                spf_extra_commission
```

## SPF EXTRA — Comissão Líquida (KPI card + table column)

```
SOURCE:       buildSpfExtraAnalysis(...).comissao / detalhes[].comissao
FORMULA:        valor * 0.70 (hardcoded literal — see docs/COMMISSION-
             RULE-MAP.md)
STATUS:                  BLOCKED — HUMAN BUSINESS DECISION REQUIRED
                        (Gate 21/87/155; docs/GESTAO-COMMISSION-
                        DECISION.md). Extracted byte-identical (same
                        as everything else) but NOT reported as
                        resolved functional parity in the final
                        delivery matrix, and rendered in V2 with an
                        explicit blocked-state label, not a silent
                        number.
GOLDEN TEST (extraction verified,        spf_extra_commission (proves
parity confirmed, decision NOT):         the extraction matches
                                        production's own 0.70 math
                                        exactly; does not resolve
                                        whether 0.70 is the right
                                        business rule going forward)
```

## Support KPIs (Visão / Tipo de veículo / Período analisado / Total geral / Parcela média / Operações com balão)

```
SOURCE:       inline in render() -- Visão/Tipo/Período simply echo the
             active filter state; "Total geral (3 status)" = operacional.
             length; "Parcela média (PMT)" = avg(operacional.map(pmt))
             (avg() ignores zero values in its denominator, matching
             production exactly); "Operações com balão" = count + avg
             of rows with balao > 0.
DENOMINATOR (PMT avg):  count of NON-ZERO pmt values among operational
                       rows (avg()'s own filter, not a naive mean over
                       all rows)
GOLDEN TEST:               valores_zero (proves avg() correctly
                          excludes zero from its own denominator, no
                          NaN/Infinity)
```

## Financiamentos por Loja / Bank tables / Status-by-store / Status-by-bank / CPF Recusadas / CPF Aprovadas tables

All structured, non-KPI-card outputs of `buildStore`/`buildBankOperational`/`buildStatusByStore`/`buildStatusByBank`/`buildCpfAnalysis` respectively — see docs/GESTAO-FUNCTION-MAP.md for the extraction trace; column-level formulas match this contract's entries above (avg financed/PMT per department, sum per status, CPF-level max-value-per-CPF rule).

## N/A — confirmed absent, not migrated (Gate 13's own discipline: report reality, not the generic template)

Vendas (as distinct from Produção) · Financiamentos (as a separate KPI from Produção) · Share / Penetração · Receita · Ticket Médio · Retorno Médio · Model Analysis (Análise por Modelo) · Seller Analysis (Análise por Vendedor) · FECHAMENTO · any chart/graph · export.
