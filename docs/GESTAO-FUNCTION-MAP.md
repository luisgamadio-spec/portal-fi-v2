# Gestão Function Map (Gate 129, 134)

Production source: `git show origin/main:modules/analise-fi-grupo.html` (blob `d52cc9ada7fd1a373d84ff6ea894d85ffc58ad0d` — confirmed byte-identical local clone == origin/main == live production, Gate 4). 38 functions + 5 constants extracted byte-identical, verified by two independent extraction scripts (`assemble_gestao_adapter.py` dependency-ordered, `extract_gestao_reference.py` alphabetically-ordered/separate wrapper) landing on identical function bodies — 0 mismatches.

## Domain: primitives / formatting

| Function | Target | Method | Test | Behavior change |
|---|---|---|---|---|
| norm, upper, onlyDigits, cleanTextKey | gestao.adapter.js | PURE EXTRACTION | indirect (every fixture) | NONE |
| money, num, html | gestao.adapter.js | PURE EXTRACTION | manual UI verification | NONE |

## Domain: row normalization

| Function | Target | Method | Test | Behavior change |
|---|---|---|---|---|
| findCol | gestao.adapter.js | PURE EXTRACTION | indirect | NONE |
| normalizeRows | gestao.adapter.js | PURE EXTRACTION | all 26 fixtures | NONE |
| parseNumber, excelDateToJS | gestao.adapter.js | PURE EXTRACTION | valores_zero, valores_grandes | NONE |
| statusNorm | gestao.adapter.js | PURE EXTRACTION | status_ag_faturamento_variantes | NONE |
| tipoVeiculo, lojaCurta | gestao.adapter.js | PURE EXTRACTION | multi_store_bank | NONE |
| isExcludedModalidade, isFandiModalidade | gestao.adapter.js | PURE EXTRACTION | modalidade_excluida, modalidade_nao_fandi | NONE |

## Domain: plan classification

| Function | Target | Method | Test | Behavior change |
|---|---|---|---|---|
| planTypeFromFields | gestao.adapter.js | PURE EXTRACTION | subsidiado/reversao/coparticipado/balao/priority_collision | NONE |
| planPriority, proposalKey | gestao.adapter.js | PURE EXTRACTION | priority_collision, multi_row_proposal_plan_signal | NONE |
| planProposalsFromRows, buildPlanAnalysis, buildPlanStoreDeptAnalysis | gestao.adapter.js | PURE EXTRACTION | all plan fixtures + seminovos_plan_scope | NONE |

## Domain: filters

| Function | Target | Method | Test | Behavior change |
|---|---|---|---|---|
| inPeriod | gestao.adapter.js | PURE EXTRACTION | date_boundary | NONE |
| storeMatches, normalizeStoreName | gestao.adapter.js | PURE EXTRACTION | store_filter_scope | NONE |
| vehicleMatches | gestao.adapter.js | PURE EXTRACTION | vehicle_filter_scope | NONE |
| applyPeriodPreset (date math only) | gestao.adapter.js `computePeriodPreset` | ADAPTED (pure date arithmetic lifted out of a DOM-coupled function — see adapter file header) | manual UI verification (period preset buttons) | NONE to the arithmetic itself; the DOM read/write wrapper is not reproduced |

## Domain: aggregation

| Function | Target | Method | Test | Behavior change |
|---|---|---|---|---|
| avg, sum, groupBy | gestao.adapter.js | PURE EXTRACTION | valores_zero (avg's zero-exclusion) | NONE |
| buildStore, buildBankOperational | gestao.adapter.js | PURE EXTRACTION | multi_store_bank, banco_ausente | NONE |
| buildStatusByStore, buildStatusByBank | gestao.adapter.js | PURE EXTRACTION | multi_store_bank | NONE |
| buildCpfAnalysis | gestao.adapter.js | PURE EXTRACTION | cpf_recusa_liquida, cpf_recusa_anulada_cancelada, cpf_aprovada_valida, cpf_aprovada_mas_ja_operacional | NONE |
| buildSpfExtraAnalysis | gestao.adapter.js | PURE EXTRACTION | spf_extra_commission | NONE (extraction) — see COMMISSION-RULE-MAP.md for the business-decision status of its OUTPUT |
| prodSummary, prodTotalSummary | gestao.adapter.js | PURE EXTRACTION | status_ag_faturamento_variantes | NONE |

## Constants

| Constant | Target | Method |
|---|---|---|
| EXCLUDE_MODALIDADE, OPERACIONAL, STATUS_RECUSA_LIQUIDA, STATUS_APROVACAO_HISTORICA, STATUS_APROVADAS_VALIDAS | gestao.adapter.js | PURE EXTRACTION, byte-identical |
| RECUSAS | NOT extracted — confirmed dead/unused in source (grepped: declared, never referenced elsewhere) | N/A |

## Domain: presentation (NOT extracted — V2 builds its own Red Precision presentation layer from the extracted data, same precedent as Score/Coparticipado)

`tbl`, `row`, `kpi`, `planCard`, `spfRows`, `planClass`, `productionCard`, `dynamicStoreTable`, `dynamicBankTable`, `cpfRowsDynamic`, `planStoreDeptRows`, `render` — HTML-string builders. Their OUTPUT CONTRACT (exact columns, labels, hint text) is preserved per docs/GESTAO-KPI-CONTRACT.md; their implementation is not reused.

## Domain: DEFERRED (Gate 137 — file I/O and live backend, out of scope, 0 backend this Wave)

`rowsFromWorksheet`, `detectCsvDelimiter`, `parseCsvRows`, `rowsFromCsvText`, `loadWorkbookFromCsvText`, `loadWorkbookFromXlsxArrayBuffer`, `loadOnlineWorkbook`, `autoFillDates` — Excel/CSV file parsing.
`processSecureFandi`, `fandiAdaptSecureResponse`, `fandiStatusPivot`, `fandiProposalOutcomes`, `fandiPlansByStore`, `fandiSyntheticOperational`, `fandiApiDate`, `fandiSafeError`, `fandiNumber` — the live secure-API (`operational_fandi_dashboard` RPC) path. Read for completeness (Gate 4), never called this Wave.
`selectedStore`, `selectedVehicle`, `setVehicleFilter`, `syncPeriodButtons`, `dateInputValue` — thin DOM-reading wrappers around the pure predicates above; V2's own UI layer reimplements the equivalent DOM interaction, not these specific functions.

| DEPENDENCY | SURFACE | REASON | FUTURE WAVE | UAT IMPACT |
|---|---|---|---|---|
| Excel/CSV file parsing | initial data load | I/O boundary, 0 file I/O this Wave (Gate 31) | admin-tooling Wave (same boundary as Coparticipado's Base01/02/03 parsing deferral) | fixtures supply already-parsed rows; UAT reviewer selects a fixture from a dev-only selector instead of uploading a file |
| Secure FANDI RPC (`operational_fandi_dashboard`) | live data refresh | 0 backend this Wave (Gate 31/95) | Auth/backend integration Wave (not yet recommended — see REPORT.md's Gate 150 analysis) | UAT reviewer sees local fixtures only, clearly labeled "DADOS DE TESTE (NEXT_LOCAL)" |
| "Diagnóstico"-style data-quality alerts | N/A — Gestão itself has none (only Coparticipado had this) | — | — | — |

## Functional diff audit (Gate 129)

0 unintentional business differences found. The ONE intentional, disclosed non-parity is the "Comissão Líquida SPF EXTRA" surface — extracted byte-identical (so its OUTPUT for a given input is provably identical to production) but explicitly marked BLOCKED in the UI pending a human business decision on which of the two real commission mechanisms (Rule A/B, see COMMISSION-RULE-MAP.md) should govern going forward. This is a decision-pending status, not a code behavior difference.
