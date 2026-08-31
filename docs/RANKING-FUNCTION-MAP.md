# Ranking Function Map (PORTAL-NEXT-07.1, Gate 3-6)

## What "Ranking" actually is in production

Not assumed — read directly from `dashbi-origin-main.html` lines 4452-4658. It is a
**single surface with 3 sub-rankings** (Vendedores, Lojas, Departamentos), all sorted
by the same metric, all scoped to the currently-selected `currentDeptView`
(Grupo/Novos/Seminovos) but **never gated by it** — i.e. the Ranking tab itself is
visible in all 3 views (see `DASHBI-PRODUCTION-SURFACE-INVENTORY.md`).

## Business logic (extracted byte-identical)

`rankingFromViews(salesView, finsView, tipo)` — origin/main lines 4459-4493.

- `tipo === "vendedor"`: groups by `"${vendedor} | ${dept} | ${loja}"` (loja resolved
  via `r.loja || VENDOR_MAP[normalizeText(r.vendedor)] || "NÃO LOCALIZADO"`).
- `tipo === "loja"`: groups by `r.loja || "NÃO LOCALIZADO"`.
- `tipo === "dept"`: groups by `r.dept || "NÃO INFORMADO"`.
- Aggregates `vendas` (count from `salesView`), `fin`/`receita`/`receitaSPF`/
  `receitaTotal`/`producao` (from `finsView`), then derives `penetracao` (fin/vendas)
  and `retorno`/`retornoTotal` (receitaTotal/producao).
- **Sort**: descending by `receitaTotal` (falls back to `receita` if absent) —
  `(b.receitaTotal||b.receita||0) - (a.receitaTotal||a.receita||0)`. Ties keep
  insertion order (JS `Array.sort` is stable) — locked in by the new
  `ranking_empate_receita_total` golden fixture.
- Production's `renderRanking()` then `.slice(0,10)` each of the 3 lists — V2
  reproduces the same Top-10 cutoff.

Not extracted (confirmed presentation-only by direct read): `medalha` (emoji position
label), `addMedals` (adds the emoji label to each row), `rankingHeroHtml`,
`renderRankingCard`, `renderRankingGrid`, `renderRanking` (HTML string builders). V2
builds its own Red Precision table instead of production's medal/hero-card layout —
same precedent as every other module (Ranking is a plain numbered table: `#`, Nome,
Vendas, Financiamentos, Penetração, Receita Total, Produção, Retorno — no medals, no
podium, no gradient hero).

## Parity verification

`rankingFromViews` was added to both `assets/js/adapters/dashbi.adapter.js` (product
adapter) and `tests/fixtures/_dashbi-reference.js` (independent reference,
alphabetically re-inserted, same dual-extraction discipline as the other 94
functions) — 0 mismatches across all 24 pre-existing fixtures × 3 dept-views × 3
`tipo`s, plus the new tie fixture. See `tests/dashbi-parity-test.py` (full-pipeline,
25/25) and the ranking/novosLoja-specific parity script run this Wave (23 testable
fixtures + 1 correctly-blocked + 1 new tie fixture = 24/24).

## Golden fixtures exercising Ranking

Every existing fixture exercises it (it runs off the same `sales`/`fins` as the core
pipeline); scenarios explicitly covered: multi-store/multi-seller
(`multi_loja_vendedor`), zero (`valores_zero`, `empty`), large values
(`valores_grandes`), long name (`nome_longo`), Seminovos-only
(`seminovos_fora_model_analysis`), filtered/closed period
(`fechamento_mes_fechado`), and the new **tie** scenario
(`ranking_empate_receita_total` — 2 lojas/vendedores with identical Receita Total,
locking in the stable-sort tie-break behavior).
