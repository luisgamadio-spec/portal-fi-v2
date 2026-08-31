# Frozen Module No-Horizontal-Scroll Inventory (PORTAL-NEXT-07.6, Gate 2)

Measured via real DOM (`document.documentElement.scrollWidth`/`clientWidth`
plus every `body *` descendant's own scrollWidth/clientWidth) in a real
Chromium session at 320/360/390/430/768/1366/1920, BEFORE any fix, using
each module's own richest/last fixture where a fixture selector exists.
Document-level passed at every viewport for all 4 modules even before any
fix — every real overflow here was component-level only, exactly the class
of bug the standing "measure children too" discipline exists to catch.

| MODULE | ROUTE | SURFACE | ELEMENT | SELECTOR | VIEWPORT | SCROLL W | CLIENT W | Δ | ROOT CAUSE | MATERIAL INFO | PROPOSED RECOMPOSITION | BUSINESS IMPACT | VISUAL IMPACT | RISK |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Landing | /landing | Mobile category nav | nav | `#landingNav.fNav` | 320-430 | up to 659 | 320-430 | 229-339 | `overflow-x:auto` (hidden scrollbar) on the mobile `.fNav` rule, items `flex-shrink:0` never wrap | Category labels (Gestão/Novos & Seminovos/Score & Salários/Brabus Intelligence/Auditoria) | `flex-wrap:wrap`, drop `overflow-x:auto` | 0 — pure nav | Nav becomes multi-line at mobile, unchanged at desktop | LOW |
| Landing | /landing | Module detail canvas | div | `.fCanvasInner` / `#landingModuleDetail` | ALL (incl. 1366/1920) | +18 flat | — | 18 (constant) | `.fModuleBlock{margin:0 -18px}` (intentional hover-bleed rectangle) | none — text never touches this 18px | NONE — already fully contained by the ancestor `.fCanvas{overflow:hidden}`; 0 visible/functional scrollbar at any viewport (proved by document-level scrollWidth passing everywhere) | 0 | 0 | SAFE (not remediated — false positive of child-only measurement, not a real defect) |
| Score | /score | Vendedor ranking table | table | `.scTableWrap` / `.scTable` | 320-430 | 460 | 286-396 | 64-174 | No `table-layout:fixed`; auto-layout sized every column to its widest un-wrapped content | #/Vendedor/Loja/Depto/Score/Financ. | `table-layout:fixed` + wrap 480-768px; full vertical stack ≤480px | 0 — presentation only | Desktop/tablet unchanged; mobile becomes stacked cards | LOW |
| Score | /score | Vendedor name | span | `.scNameText` | 320-430 | 118-120 | 116 | 2-4 (residual, past the ellipsis) | `overflow:hidden;text-overflow:ellipsis;white-space:nowrap` — truncating names AND still overflowing by a few px | Full vendedor name | Wrap instead of truncate | 0 | Long names now wrap to 2 lines instead of "…" | LOW |
| Coparticipado | /coparticipado | Coparticipados/Subsidiados record table | table | `.cpTableWrap` / `.cpTable` | 320 | 1747 | 286 | 1461 | Same auto-layout root cause, worst case: 13/11 real columns, all `white-space:nowrap` | Cliente/Vendedor/Loja/Modelo/Valor/Rebate/Parte/Coparticipação/Situação/Data/Chassi (13 cols) | `table-layout:fixed` + wrap text columns, `<colgroup>` floor-width + nowrap on atomic (money/%/date/chassi) columns; full vertical record ≤900px | 0 — presentation only | Desktop table shape kept; mobile becomes a full-field record card (no authorized primary/secondary split existed, so none invented) | MEDIUM (widest table in V2) |
| Coparticipado | /coparticipado | same table | table | `.cpTableWrap` | 1920 | 1747 | 1278 | 469 | Same — still overflowed at the largest required viewport, the most severe case flagged since PORTAL-NEXT-07.4's original audit | same | same fix as above | 0 | Table reflows within its container at every width up to 1920 | MEDIUM |
| Gestão | /gestao | Financiamentos por Loja | table | `.geTableWrap` | 320 | 1105 | 286 | 819 | Same auto-layout root cause; 10 columns ("Todos" vehicle branch) | Loja/Qtd/Novos/Seminovos/Fin. médio ×2/Parcela média ×2/Qtd Balão/Parcela média Balão | `table-layout:fixed` + wrap; full vertical stack ≤768px | 0 | Desktop (1366+) already fit and is unchanged | LOW |
| Gestão | /gestao | Pagos/Faturados/AG.Fat. por Unidade | table | `.geTableWrap` | 320 | 847 | 286 | 561 | Same | Unidade + 8 Pago/Faturado/AG.Fat./Total qtd+valor columns | same fix | 0 | same | LOW |
| Gestão | /gestao | ...por Banco | table | `.geTableWrap` | 320 | 834 | 286 | 548 | Same | Banco + same 8 columns | same fix | 0 | same | LOW |
| Gestão | /gestao | Planos por Loja/Depto (Novos, Seminovos ×2) | table | `.geTableWrap` | 320 | 500 / 790 (×2) | 286 | 214 / 504 | Same | Loja + Linear/Balão/Subsidiado/Reversão/Coparticipado/Total (Novos) or 3-type (Seminovos) | same fix | 0 | same | LOW |
| Gestão | /gestao | SPF EXTRA detail | table | `.geTableWrap` | 320 | 389 | 286 | 103 | Same | Loja/Departamento/SPF Total/Comissão Líquida 70% | same fix | 0 — value/formula untouched | same | LOW |
| Gestão | /gestao | Propostas Recusadas/Aprovadas por Loja (×2) | table | `.geTableWrap` | 320 | 790 (×2) | 286 | 504 | Same | Loja + Novos/Seminovos Qtd/Valor + Total CPFs/Valor Total/Valor Médio | same fix | 0 | same | LOW |

## Gate 4 — component scroll audit (CSS search classification)

Searched all 4 modules' CSS for `overflow-x`, `white-space:nowrap`,
`min-width`, `width:max-content`/`fit-content`, large fixed pixel widths,
table/grid width rules.

```
.fNav overflow-x:auto (landing.css)         ACTUAL OVERFLOW -> fixed (flex-wrap)
.pGlobalNav overflow-x:auto (landing.css)   SAFE -- defensive, never triggers at
                                             any measured viewport (few short
                                             icon buttons, fits at every width)
                                             -- left untouched, not a real bug
.scTableWrap overflow-x:auto (score.css)    ACTUAL OVERFLOW -> fixed
.cpTableWrap overflow-x:auto (coparticipado.css)  ACTUAL OVERFLOW (worst case
                                                    in V2) -> fixed
.geTableWrap overflow-x:auto (gestao.css)   ACTUAL OVERFLOW (8 tables) -> fixed
.scNameText text-overflow:ellipsis          ACTUAL OVERFLOW + information loss
  + white-space:nowrap (score.css)          (truncated names) -> fixed (wrap)
Every *Table th/td white-space:nowrap       ACTUAL OVERFLOW root cause (the
  (all 4 modules)                           table's own auto-layout sizing) ->
                                             fixed (table-layout:fixed + wrap)
```

All 4 `overflow-x:auto` wraps kept as a defensive safety net after the fix
(same convention Dashbi already established in PORTAL-NEXT-07.4) — none of
them are the PRIMARY mechanism preventing scroll any more; `table-layout:
fixed` + wrapping (+ vertical recomposition below each table's own
breakpoint) is what actually guarantees it now, verified by measurement,
not by the presence of `overflow-x:auto`.

No CSS declaration was blindly deleted — every changed rule is documented
in `FROZEN-MODULE-NO-SCROLL-REMEDIATION.md` with its specific before/after
and reasoning.
