# Dashbi Function Map (Gates 37, 124)

Production source: `git show origin/main:modules/analise-geral-grupo-secure-original-layout.html` (blob `f29546bc3718e6573ac069b66c8bcc02f227d600` — confirmed local clone DIVERGENT, origin/main == live production, Gate 4). 94 functions + 6 constants extracted byte-identical, verified by two independent extraction scripts (`assemble_dashbi_adapter.py` grouped-by-domain, `extract_dashbi_reference.py` alphabetical/separate wrapper) — 0 mismatches.

## Domain: primitives / formatting

norm/type helpers: `normalizeText`, `onlyDigits`, `asNumber`, `asMoneyNumber`, `asVehicleSaleValue`, `asDateValue`, `money`, `pct`, `num`, `normalizeClientName`, `clientNameVariants` — PURE EXTRACTION, NONE.

## Domain: plan text signals / column resolution

`planTextValue`, `isCoparticipadoValue`, `isSubsidiadoValue`, `isReversaoValue`, `isTCHeader`, `isIFHeader`, `hasAnyCol`, `findVal`, `getCol`, `getTCDevolvidaValue`, `getCodigoIFValue`, `hasTCPlanColumn`, `hasIFPlanColumn` — PURE EXTRACTION, NONE. Test: base03_alias_posicional.

## Domain: seller/store resolution

`sellerNameFromRow`, `rowContainsExcludedName`, `brabusIsoDateOnly`, `brabusDataOperacaoRow`, `brabusMudancaMatch`, `lojaEfetivaPorMudancaPortal`, `resolveLoja`, `isRevendaRecord`, `deptFromBase01`, `deptFromBase02`, `modeloPadrao`, `familyOfModel` — PURE EXTRACTION, NONE, except `lojaEfetivaPorMudancaPortal`'s backing data source (see Deferred below). Test: vendedor_excluido, vendedor_nao_localizado_bloqueia, modelo_eclipse_variantes, modelo_inconsistencia_triton.

## Domain: aggregation

`addAgg`, `rowsFromAgg` — PURE EXTRACTION, NONE. Test: multi_loja_vendedor.

## Domain: crossing / classification engine (the core)

`keyCliente`, `processBase01`, `processBase02`, `buildB03Index`, `scoreB03PlanRow`, `chooseBestB03Row`, `concatB03Candidates`, `aggregate`, `kpiMetricsFor`, `getReceitaSPF`, `getReceitaTotal` — PURE EXTRACTION, NONE. Test: all 24 fixtures (this is the pipeline every fixture exercises).

## Domain: plan flags

`isFinCoparticipado`, `isFinSubsidiado`, `isFinReversao`, `isFinBalao`, `isFinLinear`, `isPlanoSubsidiada`, `isPlanoReversao`, `isPlanoCoparticipada`, `isPlanoBalaoClassificado`, `planoKeyOperacao`, `planoPriority`, `planoCounts`, `getPlanoDestaque` — PURE EXTRACTION, NONE. Test: subsidiado, reversao, coparticipado, balao, priority_collision.

## Domain: Entrada / Model Analysis

`saleMatchKey`, `getSaleValorVenda`, `getFinValorVenda`, `buildSalesByChassiForEntry`, `buildSalesValueIndexForEntry`, `modelExtraMetrics`, `familyExtraMetrics`, `modelRowsUnified`, `planRowsByModel`, `planRowsByStoreForFamily` — PURE EXTRACTION, NONE. Test: entrada_elegivel, entrada_financiado_excede_tolerancia — see docs/DASHBI-MODEL-ANALYSIS-CONTRACT.md.

## Domain: local vendor mapping

`lookupNbsLocal`, `montarMapaVendedoresLocal`, `inferirTipoNovoSeminovo`, `criarIndiceVendasNovasPorChassi` — PURE EXTRACTION, NONE (given a synthetic vendorRows input — see VENDOR_MAP substitution below).

## Domain: Nova/historical format adapters

`brabusValorVendaBase01Nova`, `brabusValorFinanciadoBase02Nova`, `brabusDiagnosticarEntradaNova`, `adaptarBase01NovaLocal`, `adaptarBase02NovaLocal`, `enriquecerEntradaBase02Adaptada`, `filtrarDescricaoFinanciamentoBase02Nova` — PURE EXTRACTION, NONE. Test: nova_entrada_com_match, nova_entrada_sem_match, date_cutoff_misto.

## Domain: date / period

`toDateOnly`, `extractDateValue`, `dataLinhaManualLocal`, `parseDateNovaBaseBrabus`, `getDataNovaBase01`, `getDataNovaBase02`, `filtrarHistoricoManualLocal`, `filtrarNovoManualLocalBase01Adaptada`, `filtrarNovoManualLocalBase02Adaptada`, `getPeriodFromRows`, `isClosedMonthPeriod` — PURE EXTRACTION, NONE. Test: date_cutoff_misto, fechamento_mes_fechado.

## Constants

`ALLOWED_SALES`, `EXCLUDE_TX`, `DEV_TX`, `EXCLUDED_SELLERS`, `STORE_CODE_MAP`, `FAMILY_MODELS` — PURE EXTRACTION, byte-identical.

## Deliberate substitutions (documented, not silent)

```
VENDOR_MAP:    production ships ~100 real employee names -> real
              store names, hardcoded. V2's adapter starts it EMPTY.
              Every fixture supplies its own synthetic "Base de
              Vendedores" via setVendors() (mirroring
              montarMapaVendedoresLocal's own real AUGMENT behavior),
              so production's real names are never needed for parity
              -- they would only matter if a synthetic fixture name
              happened to collide with a real employee's name, which
              none do. NOT a PII exposure, NOT a functional gap.

lojaEfetivaPorMudancaPortal:    extracted byte-identical, but its
                              backing array (BRABUS_MUDANCAS_LOJA_
                              VENDEDORES) is never populated -- the
                              function that populates it
                              (carregarMudancasLojaVendedoresDashboard)
                              makes a LIVE SUPABASE REST FETCH, found
                              embedded directly in production's own
                              "MODO TESTE" orchestrator
                              (processarDashboardTesteManualLocal
                              awaits it at origin/main line 5912). 0
                              backend this Wave (Gate 31/114) --
                              V2's compute() omits that one line,
                              which deterministically reproduces
                              lojaEfetivaPorMudancaPortal's own
                              documented fallback (return the base
                              loja unchanged when no store-transfer
                              record exists), not an invented
                              simplification.
```

## Domain: DEFERRED (Gate 20-21, 137 — file I/O and live backend, 0 backend this Wave)

```
DEPENDENCY:    the live secure-API path (processar overridden by
              assets/js/analise-geral-grupo-secure-adapter.js's
              loadSecureDashboard, calling the operational_metrics
              RPC, wired to boot automatically on DOMContentLoaded)
SURFACE:              the module's DEFAULT/live data source
REASON:                  0 backend this Wave (Gate 31/95); ALSO: this
                       path only reshapes an ALREADY-aggregated,
                       ALREADY-classified backend payload
                       (metricsToLegacy()) -- there is no
                       classification/crossing logic to extract from
                       it, unlike the manual-test path's real engine.
FUTURE WAVE:              Auth/backend integration Wave (not
                        recommended yet this Wave either -- see
                        REPORT.md's Gate 153 analysis).

DEPENDENCY:    Excel/CSV file parsing (readWorkbook, readWorkbookSmart,
              workbookRowsFromLocalFile, and the online-URL auto-fetch
              path carregarBasesAutomaticamente)
SURFACE:              initial data load
REASON:                  0 file I/O this Wave (Gate 31); fixtures
                       supply already-shaped raw rows directly,
                       including the __COL_E/__COL_F/__HEADER_E/
                       __HEADER_F metadata readWorkbookSmart would
                       normally attach.
FUTURE WAVE:              same admin-tooling Wave as every prior
                        module's Excel-parsing deferral.

DEPENDENCY:    medal cards (renderRanking, addMedals, medalha,
              rankingHeroHtml, renderRankingCard, renderRankingGrid),
              CSV export (exportarResumoCSV), the multi-tab shell
              chrome (showTab)
SURFACE:              presentation only
REASON:                  V2 builds its own Red Precision presentation
                       from the extracted data, same precedent as
                       every prior module -- these are HTML-string
                       builders, not business logic.
FUTURE WAVE:              CSV export (exportarResumoCSV) is FC-2's target
                       (V1×V2 Feature Completeness Audit, GAP-004);
                       medal cards/showTab remain a presentation choice,
                       N/A.
```

**PORTAL-NEXT-07.1 correction**: `rankingFromViews` (the actual Ranking business
logic — grouping, aggregation, sort) was wrongly bucketed under this deferral in
PORTAL-NEXT-07 — it was never read in full during that Wave's audit, only its line
number was recorded. It has since been extracted byte-identical and is no longer
deferred; see `docs/RANKING-FUNCTION-MAP.md`. Likewise `buildNovosLojaRows` was not
discovered at all in PORTAL-NEXT-07 (Novos por Loja was missed entirely, not
deliberately deferred); see `docs/NOVOS-POR-LOJA-FUNCTION-MAP.md`. 96 functions
extracted as of this Wave (94 + `rankingFromViews` + `buildNovosLojaRows`), still 0
mismatches against an independently re-extracted reference.

**FC-1 (GAP-001) correction**: `calcDelta`/`formatDelta`/`comparisonBlock`/
`metricCompareBlock`/`getPreviousMonthComparablePeriod`/`sameDayPreviousMonth` were
bucketed above as "presentation only" through PORTAL-NEXT-07 -- the V1×V2 Feature
Completeness Audit (2026-09-04) found that framing incomplete, not wrong about
`formatDelta`/`comparisonBlock`/`metricCompareBlock` (genuinely HTML-string
builders, DUAL_PERIOD_DATA_ORCHESTRATION_REQUIRED does not apply to those three) but
incomplete about the other three: `calcDelta` is pure math with documented edge-case
behavior (previous=0/null/non-finite -> null), and the previous-comparable-period
functions require a SECOND, independently-computed aggregate the pre-FC-1 adapter's
`compute(fixture)` had no way to produce (single-period signature, no second
"previous period" parameter) -- restoring the comparison is dual-period data
orchestration (SAME_PIPELINE_DIFFERENT_PERIOD: `compute()` called twice, once per
period), not a UI-only change. FC-1 extracted `calcDelta`/`getPreviousMonthComparablePeriod`/
`sameDayPreviousMonth` byte-identical into dashbi.adapter.js (business-logic layer,
`_internal`-adjacent exports) and added dual-period fetch orchestration to
dashbi-real-provider.js (`loadDashbiRealWithComparison`) and dashbi.js (fixture mode:
a second, explicitly-picked comparison fixture; real mode: the previous comparable
period fetched via the same RPCs). `formatDelta`/`comparisonBlock`/`metricCompareBlock`
stay presentation-only, reimplemented in dashbi.js as `deltaHtml`/`kpiCompareHtml`
using V2's own class vocabulary (Gate 18, FC-1 brief) -- consistent with every other
module's "V2 builds its own presentation from the extracted data" precedent. See
`docs/DASHBI-COMPARISON-CONTRACT.md` for the restored surface set and edge-case
matrix.

## Functional diff audit (Gate 124)

0 unintentional business differences. Every extracted function's output was verified byte-for-byte against an independently re-extracted reference across all 25 fixtures (24 from PORTAL-NEXT-07 + 1 new tie fixture from PORTAL-NEXT-07.1). The two documented substitutions above (VENDOR_MAP, the live-fetch omission) are I/O-boundary/PII decisions, not business-rule differences — neither changes what any of the 96 extracted functions themselves compute for a given input.
