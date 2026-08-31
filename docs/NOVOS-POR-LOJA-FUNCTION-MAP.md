# Novos por Loja Function Map (PORTAL-NEXT-07.1, Gate 7-10)

## What it is in production

Read directly from `dashbi-origin-main.html` lines 4726-4805. A per-loja breakdown of
**Novos-only** vehicles: units sold, units financed, and financed-unit plan mix
(Balão/Subsidiada/Coparticipada/Reversão/Linear + a "Plano Destaque" per loja), plus a
`TOTAL GERAL` row. **Novos-only is a real, double-confirmed production business rule**,
not a presentation choice:

1. Its tab (`#novosLojaTab`) shares the `modelosTab` CSS class with the Análise por
   Modelos tab (line 2160) — both hidden/shown together by
   `updateModelosTabVisibility()` (line 3651-3652:
   `novosLojaTab.style.display = currentDeptView==='Novos'?'flex':'none'`).
2. `renderNovosLojaAnalysis()` itself also self-guards independently (line 4773:
   `if(currentDeptView !== "Novos"){ el.innerHTML=""; return; }`).

## Business logic (extracted byte-identical)

`buildNovosLojaRows(results)` — origin/main lines 4726-4758.

- Filters `results.sales`/`results.fins` to `dept === "Novos"` only.
- Groups by `loja` (`"NÃO LOCALIZADO"` fallback), counts `Vendidos` (from sales) and
  `Financiados` + plan-type buckets (from fins, via the SAME `isPlanoSubsidiada` /
  `isPlanoReversao` / `isPlanoCoparticipada` / `isPlanoBalaoClassificado` classifiers
  already extracted in PORTAL-NEXT-07 — priority SUBSIDIADO > REVERSÃO > COPARTICIPADO
  > BALÃO > LINEAR, same as everywhere else in this module).
- Sort: `Vendidos` desc, then `Financiados` desc, then `Loja` alphabetically.
- `BalaoPct = Balao/Financiados`; `PlanoDestaque = getPlanoDestaque(rowFinRegistros)`
  (same "most-common, priority-broken-tie" rule as the family-level Plano Destaque).
- Appends a `TOTAL GERAL` row (sum of all lojas, same `PlanoDestaque` rule applied to
  the pooled registros).

Not extracted (confirmed presentation-only by direct read):
`refreshNovosLojaIfActive` (tab-visibility plumbing), `renderNovosLojaAnalysis` (HTML
string builder + the Novos-only DOM guard, reproduced in V2 as a JS-side
`currentDeptView === 'Novos'` render gate instead). V2 builds its own Red Precision
table — reuses the same numeric-header/value-axis contract as every other Dashbi
table (`headerRow`/`.dbNumCol`), with the `TOTAL GERAL` row bolded via `.dbTotalRow`
(border-top + font-weight, no color-only signal).

## Parity verification

`buildNovosLojaRows` added to both the product adapter and the independent reference
(alphabetically, between `buildB03Index` and `buildSalesByChassiForEntry`) — 0
mismatches across all 24 pre-existing fixtures (internal `_regs` field stripped before
comparison, since it is a working array reused by the destaque calculation, not part
of the rendered contract) plus the new tie fixture. 24/24 (1 fixture correctly
excluded: `vendedor_nao_localizado_bloqueia` is the missing-seller hard-stop case,
which never reaches `buildNovosLojaRows` in production either — `compute()` returns
`{blocked:true}` before `aggregate()`/any per-view builder runs).
