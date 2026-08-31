# Dashbi Primary/Detail Map (PORTAL-NEXT-07.5, post-implementation)

Companion to `DASHBI-ANALYTICAL-HIERARCHY-INVENTORY.md` (the before-state
audit). This is the after-state contract every surface now follows.

## Overview KPI grid

```
PRIMARY (5 cards, always visible, no + Detalhes):
  Vendas · Financiamentos · Share (emphasis) · Produção Total ·
  Receita Total (emphasis)
SECONDARY (behind one KPI-level "+ Detalhes" toggle):
  Receita (base, excl. SPF) · Receita SPF · Retorno Médio
```

## Vendas e Financiamentos por Loja / por Vendedor

```
PRIMARY: Identidade · Vendas · Financiamentos · Share (emphasis) ·
         Produção Total · Receita Total
SECONDARY (+ Detalhes): Depto (Vendedor only) · Receita (base) ·
         Receita SPF · Retorno
```

## Ranking (Vendedores / Lojas / Departamentos)

```
PRIMARY: # · Nome · Vendas · Financiamentos · Share (Penetração, emphasis) ·
         Produção Total · Receita Total
SECONDARY (+ Detalhes): Receita (base) · Receita SPF · Retorno
SORT: unchanged — Receita Total desc (rankingFromViews untouched)
```

## Novos por Loja

```
PRIMARY: Loja · Vendidos · Financiados · Share (derived, emphasis) ·
         Plano Destaque
SECONDARY (+ Detalhes): Balão · % Balão · Subsidiada · Coparticipada ·
         Reversão · Linear
NOT APPLICABLE: Produção Total / Receita Total — buildNovosLojaRows has no
         production-value field for this business question (plan-mix per
         loja for Novos); not fabricated, per Gate 39.
```

## Department analysis

No distinct V2 surface exists (only Ranking's own "Departamentos"
dimension, updated above). Not invented this Wave.

## Model Analysis

Frozen (Gate 32). Not reopened. Spot-checked via Playwright this Wave
(fixture `model_analysis_parcelamento_completo`): "Entrada Qtd" still
absent, all 5 plan Qtd categories still present, no horizontal scroll —
matches the 07.4.1 state exactly.

## Share visual emphasis

Reuses the already-approved `penetracaoCellHtml()`/`.dbPenetracaoBaixa`/
`.dbPenetracaoOk` pattern (Model Analysis, 07.3) for every table cell —
same threshold, same classes, 0 new logic. The KPI-grid Share card adds a
left border stripe (green/orange matching the threshold) plus a text
caption ("Dentro da meta" / "Abaixo da meta (40%)") so the signal is not
color-only there.

THRESHOLD: v < 0.40 → baixa (critical/orange) · else → ok (success/green).
Reconfirmed this Wave against `docs/DASHBI-KPI-CONTRACT.md` (source:
`pctPenetracao`, origin/main lines 2788-2794) — not assumed from memory.

## Receita Total visual emphasis

New this Wave. See `DS-CHANGE-PROPOSAL-RECEITA-TOTAL-EMPHASIS-01.md` for
the token-authority gap and the provisional treatment: a top border
stripe + bold `--color-info` value, applied only to the KPI-grid card
(table cells stay plain-formatted money, consistent with every other
non-emphasized metric — "not a rainbow" per Gate 18).

## Responsive strategy

`.dbTableStackable` (opt-in, store/seller/Ranking/Novos-por-Loja only —
Model Analysis's own tables untouched) recomposes each row into a
vertical label/value stack at <=480px instead of shrinking columns or
moving a primary metric behind + Detalhes. Verified via Playwright at
360/390/430/768/1366/1920, document- and component-level
(`.dbTableWrap` scrollWidth vs clientWidth), with a detail row expanded
at every viewport (worst case) — 0 problems.
