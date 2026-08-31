# Dashbi KPI Contract (Gates 25-30, 57-60)

## Core KPIs (Grupo/Novos/Seminovos) — `kpiMetricsFor(results, deptView)`

```
Vendas:               salesView.length (salesView = all sales, or
                     filtered to r.dept===deptView for Novos/Seminovos)
Financiamentos:            finsView.length (same view logic)
Share:                        vendas ? fins/vendas : 0  (a ratio 0-1,
                            displayed via pct())
Produção:                        sum(finsView.map(producao))
Receita:                            sum(finsView.map(receita))  —
                                  EXCLUDES SPF
Receita SPF:                           getReceitaSPF(finsView) =
                                     sum(receitaSPF)
Receita Total:                            receita + receitaSPF
Retorno:                                     producao ? receitaTotal/
                                           producao : 0  (a ratio,
                                           displayed via pct())
```
No separate "Ticket Médio" at the Grupo/Novos/Seminovos level (confirmed absent from `kpiMetricsFor` by direct source read) — Ticket exists only at the per-model level (`modelRowsUnified`'s own `ticket: fin ? producao/fin : 0`). Not invented here to fill a gap.

## Classificação dos Planos

Same 5-way classification as every other module (`planoKeyOperacao` on each `fins` record), counted via `planoCounts`. No denominator (raw counts), same priority-collision proof as Coparticipado/Gestão (see `docs/DASHBI-CROSS-MODULE-CONSISTENCY.md`).

## Share threshold — real, current business rule (Gate 91-92)

```
FUNCTION:    pctPenetracao(v) (origin/main lines 2788-2794)
THRESHOLD:      v < 0.40 -> "penetracao-baixa" (semantic: low), else
              "penetracao-ok"
SCOPE:               applies to any Share/Penetração value rendered
                   through this helper in production — a genuine,
                   current business rule, not stale CSS (confirmed by
                   reading the function itself, which computes the
                   comparison at call time from the raw ratio, not a
                   hardcoded class name).
V2:                     reproduced as a plain data threshold (v<0.40),
                      exposed for the UI to apply its own semantic
                      token (--color-critical/--color-success) rather
                      than reusing the literal inline <span> HTML —
                      same "extract the business rule, not the legacy
                      markup" discipline as every other Wave.
```

## Store / Seller tables

`aggs.vendasLoja`/`finLoja` (by loja) and `aggs.vendasVendDept`/`finVendDept` (by `"vendedor | dept"` composite key) — real production aggregation keys, extracted via `addAgg`/`aggregate` byte-identical. Sort: by `qtd` (sales count) descending, matching production's own `sortQtd` convention.

## Model Analysis KPIs

See `docs/DASHBI-MODEL-ANALYSIS-CONTRACT.md` for the full contract (volume, financiada, penetração, produção, receita, ticket, retorno médio, prazo médio, PMT médio, Entrada/Entrada Média/Entrada %).

## FECHAMENTO (Gate 32, 66 — present here, unlike Gestão)

```
isClosedMonthPeriod(period):    true only if the filtered period spans
                               EXACTLY one full calendar month (day 1
                               through the month's real last day).
isSelectedClosedMonth():           only checked when currentPeriodFilter.
                                 mode is 'custom' or 'lastMonth' — the
                                 quick-preset 'currentMonth'/'last6'/
                                 'lastYear' never show FECHAMENTO even
                                 if they happen to span a closed month
                                 (a real, non-obvious scope restriction,
                                 preserved exactly). Golden fixture:
                                 fechamento_mes_fechado.
```

## Rounding / raw-display separation (Gate 59-60, 85-87)

```
money(v):    Math.floor(v) if v>=0, Math.ceil(v) if v<0 -- i.e.
            TRUNCATES toward zero before formatting with 0 decimal
            places. This is DIFFERENT from Gestão's/Coparticipado's
            own money() (which uses toLocaleString's own ROUNDING at
            0 decimals) -- a genuine, real, per-module difference,
            confirmed by direct source read of each file, not
            assumed identical. Preserved exactly, not unified.
pct(v):          (v*100).toLocaleString('pt-BR', {1 decimal}) + '%' --
               same shape as every other module's pct().
Formatter never touches the raw stored value -- money()/pct() are
pure presentation functions called only at render time; sorting/
classification/aggregation all operate on the raw numbers.
```

## Period filter (Gate 31, 61-65)

```
PRESETS:    currentMonth, lastMonth, last6, lastYear -- 4 presets,
           SAME SET as Coparticipado (Mês atual/Mês anterior/Últimos
           6 meses/Último ano), NOT Gestão's 3-preset set (no
           "Último ano" there) -- verified per-module, not presumed
           shared.
BOUNDARIES:      inclusive both ends (withinCurrentPeriod: d >= start
                && d <= end).
```

## Percentage unit audit (Gate 28-29, 85)

Every percentage in this module (Share, Penetração, Entrada %, Retorno) is stored as a raw fraction (0-1) and multiplied by 100 exactly once, at the `pct()` formatting boundary — confirmed by reading every ratio's own computation (e.g. `vendas ? fins/vendas : 0`, never pre-multiplied). No double-scaling, no missing scaling — verified across all 24 golden fixtures (any such bug would have surfaced as a parity mismatch against the independent reference, since the reference re-implements the same formulas from source independently).
