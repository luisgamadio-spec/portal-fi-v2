# Dashbi Analytical Hierarchy Inventory (PORTAL-NEXT-07.5, Gate 1)

Human authority: PRIMARY = Vendas, Financiamentos, Share, Produção Total, Receita
Total (wherever semantically present). SECONDARY (explicit): Receita SPF, Retorno
Médio. Applies only where the metric genuinely exists in that surface's business
contract — nothing invented to force visual symmetry.

## Visão Geral — KPI grid (`render()`'s `dbKpiGridPrimary`)

```
SURFACE:              Overview primary KPI cards (Grupo/Novos/Seminovos)
BUSINESS UNIVERSE:        kpiMetricsFor(out, currentDeptView) — already extracted
VENDAS:                       EXISTS (kpi.vendas)
FINANCIAMENTOS:                  EXISTS (kpi.fins)
SHARE:                               EXISTS (kpi.share) — BEFORE: buried as a hint
                                    string under the Financiamentos card, not its
                                    own primary value
PRODUÇÃO TOTAL:                        EXISTS (kpi.producao) — already its own
                                       card
RECEITA TOTAL:                            EXISTS (kpi.receitaTotal) — BEFORE: the
                                          card's BIG number was kpi.receita
                                          (Receita EXCLUDING SPF), with Receita
                                          Total only in the hint text
CURRENT PRIMARY:                              Vendas, Financiamentos, Produção,
                                              Receita (not Total), Retorno
CURRENT DETAIL:                                  none (no expansion mechanism on
                                                 the KPI grid at all)
REQUIRED CHANGE:                                    make Share its own primary
                                                    card; swap the Receita card's
                                                    big number to Receita Total;
                                                    add a KPI-level "+ Detalhes"
                                                    for Receita (base)/Receita
                                                    SPF/Retorno Médio (secondary)
```

## Vendas e Financiamentos por Loja (`storeTableHtml`)

```
SURFACE:              Store analysis (always-on, "Visão Geral" base content)
BUSINESS UNIVERSE:        A_.vendasLoja / A_.finLoja (aggregate(), already extracted)
VENDAS:                       EXISTS (v.qtd)
FINANCIAMENTOS:                  EXISTS (f.qtd)
SHARE:                               EXISTS (derived f.qtd/v.qtd — same formula
                                    already used everywhere else in Dashbi)
PRODUÇÃO TOTAL:                        EXISTS (f.producao) — BEFORE: in + Detalhes
RECEITA TOTAL:                            EXISTS (f.receitaTotal, on the same
                                          aggregation object) — BEFORE: only plain
                                          "Receita" (excl. SPF) was in + Detalhes,
                                          Receita Total wasn't shown anywhere
CURRENT PRIMARY:                              Loja, Vendas, Financiamentos, Share
CURRENT DETAIL:                                  Produção, Receita (excl. SPF)
REQUIRED CHANGE:                                    promote Produção (Total) and
                                                    Receita Total to primary;
                                                    detail keeps Receita (base),
                                                    adds Receita SPF and Retorno
                                                    (derived, same formula as
                                                    Ranking/Model Analysis)
```

## Vendas e Financiamentos por Vendedor (`sellerTableHtml`)

```
SURFACE:              Seller analysis (always-on)
BUSINESS UNIVERSE:        A_.vendasVendDept / A_.finVendDept
VENDAS:                       EXISTS
FINANCIAMENTOS:                  EXISTS
SHARE:                               EXISTS (derived)
PRODUÇÃO TOTAL:                        EXISTS (f.producao) — BEFORE: in + Detalhes
RECEITA TOTAL:                            EXISTS (f.receitaTotal, same
                                          aggregation object as store) — BEFORE:
                                          not shown anywhere at all (not even
                                          plain Receita)
CURRENT PRIMARY:                              Vendedor, Vendas, Financiamentos,
                                              Share
CURRENT DETAIL:                                  Depto, Produção
REQUIRED CHANGE:                                    promote Produção Total,
                                                    Receita Total to primary;
                                                    detail keeps Depto, adds
                                                    Receita, Receita SPF, Retorno
```

## Department analysis — NOT A DISTINCT V2 SURFACE

```
Production has vendasDept/finDept aggregations (already extracted, unused by any
dedicated V2 UI table). V2 never built a standalone department-level table in any
prior Wave — department-level reading is only available via Ranking's own
"Departamentos" dimension (a Top-10-by-Receita-Total ranking, a different business
question than a full department breakdown). Per Gate 60's own instruction not to
invent surfaces, no new department table was created this Wave — Ranking's
Departamentos dimension is updated per the Ranking rules below, and that is this
Wave's complete department-level change.
```

## Ranking (`rankingRowHtml`/`rankingTableHtml`, 3 dimensions: Vendedores/Lojas/Departamentos)

```
SURFACE:              Ranking (Top 10, all 3 dept views)
BUSINESS UNIVERSE:        rankingFromViews(salesView, finsView, tipo) — already
                        extracted
VENDAS:                       EXISTS (r.vendas)
FINANCIAMENTOS:                  EXISTS (r.fin)
SHARE:                               EXISTS (r.penetracao, same field name/formula
                                    as Model Analysis's Penetração) — BEFORE: in
                                    + Detalhes
PRODUÇÃO TOTAL:                        EXISTS (r.producao) — BEFORE: in + Detalhes
RECEITA TOTAL:                            EXISTS (r.receitaTotal) — already
                                          primary (it's the sort key — Gate 7's own
                                          "never hide Ranking Receita Total" is
                                          already satisfied structurally)
CURRENT PRIMARY:                              #, Nome, Vendas, Financiamentos,
                                              Receita Total
CURRENT DETAIL:                                  Penetração, Produção, Retorno
REQUIRED CHANGE:                                    promote Penetração(Share) and
                                                    Produção to primary; detail
                                                    keeps Retorno, adds Receita
                                                    (base)/Receita SPF (already on
                                                    the row, unused) for
                                                    cross-surface consistency
SORT:                                                    unchanged — Receita Total
                                                         desc, stable tie-break
                                                         (rankingFromViews itself
                                                         untouched)
```

## Novos por Loja (`novosLojaHtml`)

```
SURFACE:              Novos por Loja (Novos-only)
BUSINESS UNIVERSE:        buildNovosLojaRows(out) — already extracted, byte-
                        identical since PORTAL-NEXT-07.1. A genuinely different
                        business question (plan-mix breakdown per loja for Novos),
                        not a financial summary.
VENDAS:                       EXISTS as "Vendidos" (same concept, production's own
                             label for this specific table)
FINANCIAMENTOS:                  EXISTS as "Financiados"
SHARE:                               EXISTS (derived Financiados/Vendidos — same
                                    formula pattern as store/seller, not a new
                                    extraction)
PRODUÇÃO TOTAL:                        NOT APPLICABLE — buildNovosLojaRows does
                                       not compute a production/financing-value
                                       field at all; fabricating one here would
                                       violate Gate 39's own "do not invent" rule
RECEITA TOTAL:                            NOT APPLICABLE — same reason
CURRENT PRIMARY:                              Loja, Vendidos, Financiados, Plano
                                              Destaque
CURRENT DETAIL:                                  Balão, % Balão, Subsidiada,
                                                 Coparticipada, Reversão, Linear
REQUIRED CHANGE:                                    add derived Share to primary
                                                    (Vendidos/Financiados ratio,
                                                    consistent with every other
                                                    surface); Produção/Receita
                                                    Total NOT added — not present
                                                    in this business universe;
                                                    plan-mix breakdown stays in
                                                    detail (already correctly
                                                    secondary, Gate 40)
```

## Model Analysis — FROZEN, not touched (Gate 32)

Human-finalized presentation from PORTAL-NEXT-07.4/07.4.1. Not reopened this Wave.
Verified via regression only (goldens, no-scroll assertions) — see final report.
