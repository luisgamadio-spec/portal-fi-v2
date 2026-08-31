# Model Analysis — Primary / Detail Completeness Map (PORTAL-NEXT-07.4, updated 07.4.1)

Authority: `docs/MODEL-ANALYSIS-PRODUCTION-INVENTORY.md` (PORTAL-NEXT-07.3, not
re-audited from memory this Wave — same production evidence, only the V2
presentation shape changed).

**PORTAL-NEXT-07.4.1 update**: human UAT approved the primary+detail experience
itself, with two presentation corrections — "Entrada Qtd" removed (it was never a
production metric, only an internal denominator, item 18 below); Qtd Subsidiado/Qtd
Coparticipado added to the Planos group (real counts, sourced from the
already-extracted `planRowsByModel`, matched by Modelo — see
`docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md`'s new section for the full trace and
reconciliation proof). Table below updated accordingly.

## Family-level (14 items) — unchanged location, `.dbFamilyMetricGrid`

All 14 boxes (Volume vendido, Financiamentos, Penetração, Produção, Receita,
Receita SPF, Receita Total, Ticket médio, Média de retorno, Prazo médio, Média de
parcela, Entrada média, % Entrada médio, 🏆 Plano Destaque) render exactly as in
07.3 — this grid was never wide enough to require horizontal scroll, so it was not
touched this Wave.

## Per-model (18 items) — final location

| # | Production metric | Final location |
|---|---|---|
| 1 | Volume / Qtd Vendida | VISIBLE_IN_PRIMARY_ROW (all viewports) |
| 2 | Financiamento / Qtd Financiada | VISIBLE_IN_PRIMARY_ROW (all viewports) |
| 3 | Penetração | VISIBLE_IN_PRIMARY_ROW (all viewports) |
| 4 | Produção / Valor Produzido | VISIBLE_IN_PRIMARY_ROW (≥768px) + VISIBLE_IN_INLINE_DETAIL (all viewports) |
| 5 | Receita | VISIBLE_IN_INLINE_DETAIL |
| 6 | Receita SPF | VISIBLE_IN_INLINE_DETAIL |
| 7 | Receita Total | VISIBLE_IN_PRIMARY_ROW (≥768px) + VISIBLE_IN_INLINE_DETAIL |
| 8 | Ticket Médio Financiado | VISIBLE_IN_PRIMARY_ROW (≥768px) + VISIBLE_IN_INLINE_DETAIL |
| 9 | Média Retorno | VISIBLE_IN_PRIMARY_ROW (≥768px) + VISIBLE_IN_INLINE_DETAIL |
| 10 | Prazo Médio | VISIBLE_IN_INLINE_DETAIL (Parcelamento group) |
| 11 | Média Parcela | VISIBLE_IN_INLINE_DETAIL (Parcelamento group) |
| 12 | Entrada Média | VISIBLE_IN_INLINE_DETAIL (Entrada group) |
| 13 | % Entrada | VISIBLE_IN_INLINE_DETAIL (Entrada group) |
| 14 | Qtd Linear | VISIBLE_IN_INLINE_DETAIL (Planos group) |
| 15 | Qtd Balão | VISIBLE_IN_INLINE_DETAIL (Planos group) |
| 16 | Qtd Reversão | VISIBLE_IN_INLINE_DETAIL (Planos group) |
| 17 | Valor Médio Balão | VISIBLE_IN_INLINE_DETAIL (Planos group) |
| 18 | (Entrada Qtd — EXTRA_IN_V2, not a production column) | **REMOVED FROM UI (07.4.1)** — still computed internally, feeds Entrada Média/% exactly as before, just not rendered |
| 19 | (Qtd Subsidiado — not in `modelRowsUnified`'s own row shape, but on the same `compModelo` aggregation with the same population/classifiers) | **ADDED (07.4.1)** — VISIBLE_IN_INLINE_DETAIL (Planos group), sourced from `planRowsByModel` matched by Modelo |
| 20 | (Qtd Coparticipado — same as above) | **ADDED (07.4.1)** — VISIBLE_IN_INLINE_DETAIL (Planos group), sourced from `planRowsByModel` matched by Modelo |

**Primary row (always visible, all viewports)**: Modelo, Volume, Financiamentos,
Penetração — 1 click maximum to every other metric via `+ Detalhes`.

**Primary row (desktop, ≥768px)**: adds Produção, Receita Total, Ticket Médio,
Retorno Médio — 8 data columns total, still comfortably a single non-scrolling
table row at 768px+.

**Parcelamento discoverability (Gate 38)**: Prazo Médio and Parcela Média are both
in the *first* detail group after `+ Detalhes` (Parcelamento) — one click, no
nested interaction.

**Entrada discoverability (Gate 39)**: Entrada Média/% are together in their own
detail group — one click. Entrada Qtd is not displayed (07.4.1, see above).

**Planos group order (07.4.1)**: Qtd Subsidiado, Qtd Reversão, Qtd Coparticipado,
Qtd Balão, Qtd Linear, Balão Médio — follows the official classification priority
(SUBSIDIADO>REVERSÃO>COPARTICIPADO>BALÃO>LINEAR) per explicit human preference,
not production's own field order (which never listed Subsidiado/Coparticipado at
this level at all).

## Plan tables (already existing semantic subtables — unchanged mapping)

- Resumo tipos de plano (family total) — VISIBLE_IN_EXISTING_SEMANTIC_SUBTABLE,
  now itself primary(label/Financiamentos/Linear/Balão) + detail (5 % pairs +
  Coparticipado/Subsidiado/Reversão).
- Quantidade por tipo de plano / Modelo — same pattern.
- Quantidade por tipo de plano / Loja — same pattern.
- Detalhe Coparticipado/Subsidiado/Reversão — VISIBLE_IN_SPECIAL_DETAIL_TABLE,
  unchanged (6 columns, only overflowed at 360px by a small margin — resolved as
  a side effect of the shared numeric-alignment/padding pass, verified 0 overflow
  in the full 26-fixture sweep).
- Inconsistências TRITON — VISIBLE_IN_CONDITIONAL_INCONSISTENCY_TABLE, unchanged
  (4 columns, never needed scroll).

## Completeness equation (Gate 72)

PRIMARY (4-8 cols, all viewports) + INLINE DETAIL (14 more per-model fields, one
click) + EXISTING SEMANTIC SUBTABLES (plan/special/inconsistency, unchanged
mapping) = **100% of the 07.3 material Model Analysis inventory.**

```
UNMAPPED MATERIAL ITEMS: 0
INACCESSIBLE MATERIAL ITEMS: 0
```

No metric is counted twice for completeness purposes — Produção/Receita Total/
Ticket Médio/Retorno Médio appear in BOTH the desktop primary row and the detail
panel (intentional redundancy for mobile completeness, documented in
`docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md`), but this is one metric with two
presentation locations, not two metrics.
