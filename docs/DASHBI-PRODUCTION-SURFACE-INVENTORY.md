# Dashbi Production Surface Inventory (PORTAL-NEXT-07.1, Gate 2/59)

Rebuilt fresh from `PORTAL-NEXT-07/.source/dashbi-origin-main.html` (== `origin/main`
SHA `2f17eb2341c5cc14aa8710aa044103002ca572a9`, re-confirmed unchanged this Wave), not
carried over from PORTAL-NEXT-07's own audit notes. Every row below was verified by
reading the actual function body / DOM markup, not inferred from a name.

| Surface | Real production view(s) | Source function(s) | Trigger | V2 status |
|---|---|---|---|---|
| Grupo/Novos/Seminovos KPIs | all 3 | `kpiMetricsFor` | always | MIGRATED (PORTAL-NEXT-07) |
| Classificação dos Planos ("Plano Destaque" box) | **Novos only** — lives inside `renderModelos`, line 4085 (`planoDestaqueFamiliaAtualHtml`) | `getPlanoDestaque`, `planoCounts` | `#modelos` render | MIGRATED, now correctly Novos-only (this Wave, Gate 11-14) |
| Análise por Modelos (indicators, plan-mix tables, vehicle selector) | **Novos only** — `#modelosTab`/`#modelos`, gated by `updateModelosTabVisibility()` (line 3633: `modelosTab.style.display = currentDeptView==='Novos'?'flex':'none'`) | `modelRowsUnified`, `planRowsByModel`, `planRowsByStoreForFamily`, etc. | `#modelos` render | MIGRATED, now correctly Novos-only (this Wave) |
| Vehicle images (OUTLANDER/ECLIPSE CROSS/TRITON) | inside Análise por Modelos, Novos only | `VEHICLE_IMAGES` const, line 2651 (3 base64 PNGs, 2048×935/2048×935/1080×521) | `renderModelos` | RESTORED this Wave — real assets traced to `origin/main`, resized to 280px (see Gate 15-21 below) |
| Vendas/Financiamentos por Loja, por Vendedor | Grupo/Novos/Seminovos (all 3, scoped by `currentDeptView` inside `render()`) | `rowsFromAgg`, `aggregate` | `#visao`/`#vendas`/`#fin`/`#b03` render | MIGRATED (PORTAL-NEXT-07) — unchanged this Wave |
| Share / Retorno por loja e departamento | Grupo/Novos/Seminovos | `consolidateShareByStoreForGrupo`, `renderSharePerformanceGrid` | `#share` render | MIGRATED (PORTAL-NEXT-07) — unchanged this Wave |
| **Ranking** (Top 10 Vendedores/Lojas/Departamentos por Receita Total) | **all 3 views** — `#rankingTab` has NO `modelosTab` class (line 2159), `renderRanking()` is called unconditionally inside `render()` (line 4930), never gated by `currentDeptView` | `rankingFromViews`, `medalha` (presentation only) | `#ranking` render + tab click | **RESTORED this Wave** (Gate 3-6) |
| **Novos por Loja** | **Novos only** — `#novosLojaTab` shares the `modelosTab` class (line 2160), same visibility gate as Análise por Modelos; `renderNovosLojaAnalysis` also self-guards (`if(currentDeptView!=='Novos'){el.innerHTML='';return;}`, line 4773) — double-confirmed | `buildNovosLojaRows` | `#novosLoja` render + tab click | **RESTORED this Wave** (Gate 7-10) |
| FECHAMENTO badge | view-independent (attached to `document.body`, not gated by `currentDeptView`) | `fechamentoBadgeHtml`, `isClosedMonthPeriod` | `render()` | MIGRATED (PORTAL-NEXT-07); this Wave moved its V2 placement from the (now Novos-only) Plan Classification heading to the always-visible KPI area, matching production's own view-independent placement |
| Qualidade do cruzamento / vendedores sem loja / clientes sem match | all 3 (uses full `r.sales`/`r.fins`, not view-filtered) | inline in `render()` | `#alertas` render | MIGRATED (PORTAL-NEXT-07) as "Diagnóstico (dev only)" — unchanged this Wave |
| CSV export | all 3 | `exportarResumoCSV` | button | DEFERRED (file I/O, documented since PORTAL-NEXT-07) |
| Live secure-API path (`operational_metrics` RPC) | all 3 (production default) | `loadSecureDashboard` | boot | DEFERRED (0 backend, documented since PORTAL-NEXT-07) |
| Excel/CSV upload | manual-mode entry point | `workbookRowsFromFile` | button | DEFERRED (0 file I/O, documented since PORTAL-NEXT-07) |

## Reconciliation (Gate 23, 59)

Comparing this fresh inventory against PORTAL-NEXT-07's migrated set: the only
previously-undiscovered MATERIAL surfaces are Ranking, Novos por Loja, and the vehicle
images — exactly the 4 human-reported issues (Plan Classification/Model Analysis
visibility being the other 2, which were a scoping bug in V2, not a missing-surface
bug — production itself already gates them Novos-only). No other unexplained material
surface was found. CSV export, the live secure-API path, and Excel upload remain
correctly DEFERRED for the same reasons as PORTAL-NEXT-07 — no change to that status
this Wave.
