# Change Proposal: Simulador Novos Governed Authority Migration

**Change ID:** `V2_SIMULADOR_NOVOS_GOVERNED_AUTHORITY_MIGRATION`
**Change type:** Financial data authority correction — **not** a visual
redesign, not a Design System change, not a formula change.
**Module:** Simulador Novos, "Plano Coparticipado" campaign mode only
(`assets/js/simulador-novos.js` + `assets/js/adapters/financiamento-
campanha.adapter.js`), frozen at `migrationStatus: HUMAN_APPROVED` since
PORTAL-NEXT-08.5.
**Authorization:** A dedicated, multi-wave, read-only authority-
reconciliation investigation (opened as debt
`V2_SIMULADOR_NOVOS_GOVERNED_RATE_PARITY_AUDIT_REQUIRED` during the
Coparticipado governed-rate correction) proved the module's local
financial authority is stale and that both blockers to migration
(governed coefficient authority existence; real-user RPC authorization)
are resolved. This document is the freeze-reopening Change Proposal
required by that investigation's own conclusion (`SAFE_TO_IMPLEMENT =
YES`).

## Status (2026-09-07)

- **Previous state:** `HUMAN_APPROVED` / `FROZEN` (PORTAL-NEXT-08.5).
- **Reopen reason:** `STALE_HARDCODED_FINANCIAL_AUTHORITY_VS_ACTIVE_
  GOVERNED_AUTHORITY`.
- **Authority reconciliation:** `V2_SIMULADOR_NOVOS_PREIMPLEMENTATION_
  AUTHORITY_RESOLVED` (`SAFE_TO_IMPLEMENT = YES`), established across the
  prior investigation waves — see "Prior evidence" below.
- **Implementation:** COMPLETE this wave.
- **Target state during this wave:** `UAT_PENDING`. This document does
  **not** claim Human approval.

## Prior evidence (read-only investigation, not repeated here)

- **Blocker A (governed coefficient authority):** `TX_COEF_GOVERNED_
  AUTHORITY_FOUND`. A dedicated governed table
  (`simulador_coparticipado_coeficiente_linhas`, batch family
  `COEFICIENTES_COPARTICIPADO`) exists, is actively maintained (ACTIVE
  batch imported 2026-08-25, i.e. *after* the model matrix's own last
  update), and is a strict superset of the local hardcoded `TX_COEF` (all
  40 shared keys byte-identical, plus 4 governed-only keys). Coverage
  proven: 39/39 required unique `(prazo, taxa)` keys, 90/90 governed
  model×term rows.
- **Blocker B (real-user RPC authorization):** `V2_SIMULADOR_NOVOS_
  GOVERNED_RPC_AUTH_COMPATIBLE`. A real authenticated VENDEDOR/NOVOS
  Portal V2 browser session (the highest-risk legitimate day-to-day user
  class for this module) successfully called `simulador_get_
  coparticipado()` through the exact production code path
  (`coparticipado-governed-rates-provider.js`), runtime-proving
  `matriz_modelos` (90 rows / 15 models / 6 terms) and `tx_coef` (44
  rows) both present and non-empty.
- **The defect:** `financiamento-campanha.adapter.js`'s hardcoded
  `MODELS`/`TX_COEF` are a byte-identical freeze of the original Secure
  embedded mini-app (proven via the file's own header comment and via a
  fresh read-only comparison against the governed table's own
  `BOOTSTRAP_HARDCODED_ATUAL` batch) that never received the business's
  subsequent real corrections. Numeric result: 14/15 models exact on
  rebate/hpe/brabus (1 divergent: **ECLIPSE CROSS RUSH**, 7.81% hardcoded
  vs. 8.01% governed); 15/90 taxa cells divergent across 10/15 models
  (always local = governed + 0.0010, one cell +0.0020), including
  **TRITON TARMAC** at prazo 18 (local 0.0039 vs. governed 0.0029,
  governed coefficient 0.0627685 — absent from the local `TX_COEF` before
  this fix).

## The correction

1. **`assets/js/adapters/financiamento-campanha.adapter.js`** —
   **additive only**. `calcularCampanha(params)` accepts two new optional
   parameters, `modelOverride` (a model object shaped like a `MODELS[]`
   entry) and `coefLookup` (a `(prazo, taxa) -> coeficiente|null`
   function). When omitted, behavior is byte-identical to before —
   `PRAZOS`/`TX_COEF`/`MODELS`/the formula are **untouched**, and
   `tests/simulador-campanha-parity-test.py` (14/14, comparing the
   adapter against the real decoded DOM-coupled origin mini-app) passes
   unchanged, proving this. This file is loaded globally by `index.html`
   but — verified this wave by grep — **`simulador-seminovos.js` has zero
   references to `NX_CAMPANHA_ADAPTER`/`'campanha'` anywhere**, so this
   change has **zero Seminovos blast radius**.
2. **`assets/js/simulador-novos.js`** — new governed-authority state
   machine local to this file (`campState`: `IDLE`/`LOADING`/`READY`/
   `ERROR`; `campAuthority`: normalized `{modelsByName, modelNames,
   coefLookup}`), built from `simulador_get_coparticipado()`'s real
   response by reusing `coparticipado-governed-rates-provider.js`
   **directly, unmodified** — the exact same file, exact same function,
   Coparticipado's own frozen module already calls. This is a pure,
   stateless, side-effect-free read; calling it a second time from a
   different page does not affect Coparticipado's behavior in any way
   (confirmed: `tests/coparticipado-governed-rate-authority-test.py`,
   23/23, unchanged).
   - Loaded **lazily**, once, the first time the user enters "Plano
     Coparticipado" mode — not at page load, not per model/term, not
     polled. Cached in `campAuthority` for the rest of the page session
     (a full reload re-fetches; this mirrors the "current ACTIVE batch"
     semantics already used elsewhere, not a live/per-second feed).
   - The model `<select>` is now populated exclusively from
     `campAuthority.modelNames` (the governed set), never from
     `CAMP._internal.MODELS`.
   - `calcCampanha()` always injects `modelOverride`/`coefLookup` from
     `campAuthority` into `CAMP.compute()`. There is no code path left
     that reads the adapter's own internal `MODELS`/`TX_COEF` for a real
     calculation.
3. **Fail-closed, structurally, not by convention:** the Calcular button
   is only ever rendered when `campState === 'READY'`. On `LOADING` a
   neutral "Carregando condições vigentes do simulador..." message shows
   (no form). On `ERROR` a Portuguese message — "Não foi possível
   carregar as condições vigentes do simulador. Tente novamente." — shows
   with a **Retry** button that re-invokes the same load. No RPC name,
   database detail, Supabase internal, token, or stack trace is ever
   exposed to the user. There is **no** code path back to the stale
   embedded `MODELS`/`TX_COEF` for a real user calculation — this was
   verified by dedicated tests (see below), not merely asserted.
4. **Race protection:** an in-flight promise guard prevents duplicate
   concurrent governed-authority requests; every async continuation
   re-checks `currentMode === 'campanha'` before re-rendering, so a user
   who switches mode away mid-load never has a stale render silently
   applied to the wrong panel.
5. **Registry:** `config/module-registry.json`'s `simulador-novos` entry
   moved from `HUMAN_APPROVED` to `UAT_PENDING`, with a new
   `governedAuthorityMigrationNote` field recording this change without
   erasing or rewriting the existing `humanApprovalNote` (PORTAL-NEXT-08.5
   chronology preserved in full).

## What was explicitly NOT done

- **`PRAZOS`, the acréscimo constants (0.0411/0.0622), and the campaign
  formula itself** (`entryPct`/`minValue`/`financed`/`payment`/
  `rebateTotal`/`rebateBrabus`/`rebateHpe`/`finalSale`) — untouched.
  Input authority and calculation formula are kept strictly separate, per
  the investigation's own explicit instruction.
- **The 8 non-campaign Novos engines** (Tradicional, Periódico, Parcela
  Única, Linear, Subsidiadas, Semestral Triton/Outlander, Descobridor de
  Taxa, Antecipação) — zero code touched; confirmed unaffected by a
  dedicated regression case (Linear renders correctly with the new
  provider variable declared but never invoked for that mode).
- **Cash Conversion** (`assets/js/adapters/cash-conversion.adapter.js`) —
  confirmed, again this wave, to take a 100% user-entered
  `taxaAplicacao` with zero coupling to `MODELS`/`TX_COEF`; not modified.
- **Simulador Seminovos** — zero files touched; zero blast radius proven
  by direct grep (zero references to the campanha adapter in its own
  page script).
- **Coparticipado** — zero files touched; `coparticipado-governed-rates-
  provider.js` was reused exactly as-is, not edited; full regression
  green (23/23).
- **Any backend/DB object** — the migration consumes an already-deployed,
  already-granted RPC; 0 migrations, 0 schema changes, 0 permission
  changes, 0 new RPCs.

## Tests

- **`tests/simulador-novos-governed-authority-test.py` (new, 21/21):**
  governed-authority success + 15/15/90/90/39/39 coverage; the `<select>`
  sourced from governed data, not hardcoded `MODELS`; three golden cases
  computed independently from the frozen governed fixture (never
  hand-typed) — **ECLIPSE CROSS RUSH** (rebate + taxa divergence),
  **TRITON TARMAC** (previously-missing local coefficient key), and
  **OUTLANDER SIGNATURE** (control); empty `matriz_modelos`/`tx_coef`,
  permission-denied (`42501`), network failure, and session-expired —
  all fail closed with **no Calcular button** and **no fallback value**;
  Retry recovers to `READY`; governed authority is loaded exactly once
  per page session (cached across mode re-entry); the Linear engine
  (a non-campaign control) renders unaffected.
- **RED-before-fix was proven empirically**, not just reasoned about: the
  two implementation files were temporarily reverted via a scoped `git
  stash` (leaving unrelated dirty work untouched), the new test was run
  against that reverted code, and it failed for the correct reason (the
  pre-fix code has no governed-authority state machine at all — no
  `getCampState`, no gating, the Calcular button always present against
  the stale hardcoded matrix). The stash was restored and the suite
  re-confirmed green (21/21).
- **Governed fixture:** `tests/fixtures/simulador-novos-governed-
  campanha-contract.json` — a frozen, read-only snapshot of both
  governed batches (`matriz_modelos` batch `c4ec1f49-…`, `tx_coef` batch
  `150bf52c-…`), captured fresh this wave via the same read-only
  service-role technique already used and approved for every prior
  Coparticipado/Simulador Novos audit wave. **Not a runtime authority** —
  the real V2 module always calls the live RPC.
- **`tests/simulador-campanha-parity-test.py` (14/14, unchanged):** proves
  the additive adapter change did not alter default (no-override)
  behavior.
- **`tests/coparticipado-governed-rate-authority-test.py` (23/23,
  unchanged):** proves zero Coparticipado behavior change.
- **`tests/cash-conversion-parity-test.py` (11/11, unchanged):** proves
  Cash Conversion unaffected.
- **`tests/registry-test.py` (unchanged, green):** its own
  `EXPECTED_STATUS` allowlist already accepts `UAT_PENDING` for
  `simulador-novos`.
- **Pre-existing, unrelated failure noted (not caused by this change, not
  fixed by this change):** `tests/simulador-novos-ui-binding-test.py` and
  `tests/simulador-novos-presentation-test.py` (both port-8700,
  full-router-driven) time out/crash waiting for `.smModeBtn` — confirmed
  **identically reproducible against the pre-fix (stashed) code**, so
  this is a pre-existing local environment condition, not a regression
  introduced by this wave.

## Risks

- **Low.** The governed data path reuses an already-deployed,
  already-granted RPC and an already-proven provider file, unmodified.
  The only new runtime dependency for this one mode is one additional
  network round-trip on first entry into "Plano Coparticipado" per page
  session — cached thereafter.
- The stricter fail-closed gating means a transient governed-RPC hiccup
  blocks only the "Plano Coparticipado" mode (not the other 9 engines) —
  accepted, mirroring the same trade-off already Human-approved for
  Coparticipado.
- `DIRETOR_SEMINOVOS` remains `DIRETOR_SEMINOVOS_RUNTIME_NOT_TESTED` on
  the same `coparticipadoPortal` permission dimension VENDEDOR/NOVOS was
  proven compatible on — not a blocker (per the prior wave's explicit
  instruction), but the fail-closed error state is exactly the correct
  behavior if that profile is ever genuinely denied.

## Rollback strategy

Rollback means **reverting this change's V2 commit** (`git revert`), not
introducing a runtime fallback to the local hardcoded `MODELS`/`TX_COEF`.
A silent stale fallback must never be reintroduced as an emergency
mechanism — if the governed authority is temporarily unavailable, the
module should show its existing blocked/error/Retry state, exactly as
the fail-closed tests already verify.

## Human UAT visual finding (2026-09-07) — `HUMAN_UAT_VISUAL_DEFECT_FOUND`

While performing the UAT below, the Human found a **visual** defect
unrelated to the financial authority migration: the installment result
grid's internal dividers rendered broken/inconsistent around specific
cells ("erro na linha entre 24x e 36x"; also reported in Financiamento
Linear at "24x e 30x"; also reported, independently, in **Simulador
Seminovos**' own Linear grid). This is **not** a rejection of the
governed-authority migration — the Human's own screenshots otherwise
confirmed the intended calculations and rendering; the financial
regression suite (governed-authority, campanha parity, Coparticipado,
Cash Conversion) remained green throughout.

**Root cause (proven by rendered DOM geometry, not guessed):**
`.smTermGrid` (the shared installment RESULT grid, `simuladores-
shared.js`'s `UI.termGrid`, used by both Simulador Novos and Simulador
Seminovos) painted its dividers as the container's own background
showing through 1px CSS Grid gaps, with `grid-template-columns:
repeat(auto-fill, minmax(110px, 1fr))`. `auto-fill` computes a column
count from container width alone, with no awareness of the actual item
count — whenever the item count wasn't an exact multiple of that column
count, the wrapped last row still allocated every computed track
(`auto-fill` never collapses unfilled trailing tracks), leaving a
visible untinted void from the last real cell to the grid's right edge
— read as a broken/dangling divider exactly at the row-wrap boundary.
The exact cell pair the Human saw ("24x/36x", "24x/30x") depends on
their own window width, which determined where the grid happened to
wrap — reproduced and measured directly at 1366/1024/900/480px.

**Fix (additive, shared, non-financial):** a new `UI.balancedColumnsExact()`
+ `UI.wireTermResultGrid()` pair in `simuladores-shared.js` computes a
column count that is an **exact divisor** of the item count (not merely
"avoid a lone leftover," which the pre-existing `balancedColumns()` for
the unrelated `.smTermSelectGrid` term-picker already did and was
correctly left untouched) — guaranteeing every row is always completely
filled, at any container width. `.smTermGrid`'s CSS now reads
`--term-grid-cols` (set by the new function) instead of `auto-fill`.
`simulador-novos.js` (`calcCampanha`, `calcLinear`) and `simulador-
seminovos.js` (`calcRateTable`) each gained one call to a small local
`wireResultTermGrid()` wrapper right after rendering their term grid —
no CSS selector, formula, business logic, or financial value was
touched in either page file.

**New permanent regression:** `tests/simulator-installment-grid-
geometry-test.py` (85/85) — DOM/geometry assertions (not screenshots)
across all three real grid sizes (Coparticipado 6 cells, Novos Linear 8
cells, Seminovos Linear 9 cells) and four viewport widths
(1366/1024/900/480px): every row's last cell reaches the grid's own
right edge, adjacent cells are separated by exactly the CSS gap, all
rows within a grid have equal item counts, and both page-level and
grid-wrapper horizontal overflow stay within 1px tolerance (never via
`overflow-x:auto`/`hidden`). RED-before-fix proven empirically via a
scoped `git stash` of the CSS/JS files (67/85, with the exact predicted
failure modes); stash restored and 85/85 reconfirmed.

**Seminovos governance impact:** `simulador-seminovos.js` (a production
file of the `HUMAN_APPROVED`/`FROZEN` Seminovos module) required one
additive line change to wire the shared fix into its own Linear/
RATE_TABLE grid, since the same shared `.smTermGrid`/`UI.termGrid`
component is genuinely used by both simulators and the Human
independently reported the identical defect there. `config/module-
registry.json`'s `simulador-seminovos` entry moved `HUMAN_APPROVED` →
`UAT_PENDING` with a new `installmentGridVisualFixNote` field (existing
notes preserved); `tests/simulador-seminovos-parity-test.py` (24/24,
all 9 LinearRateTable golden values byte-for-byte unchanged) proves
zero financial/business-logic regression from this narrowly-scoped
visual correction.

## Human UAT required (original financial migration, not yet satisfied)

Refreeze criteria: the Human re-tests the V2 localhost build at
`http://127.0.0.1:8080/portal-next-v2/` and confirms, at minimum:

A. **ECLIPSE CROSS RUSH** — sale R$200.000,00 / entry R$120.000,00: the
   rebate/taxa values now reflect the governed authority (higher rebate
   cost, and the 12x/18x installments now resolve instead of any prior
   discrepancy).
B. **TRITON TARMAC** — same sale/entry: the 18x installment resolves
   using the previously-missing governed coefficient.
C. **OUTLANDER SIGNATURE** — same sale/entry, as a control case.
D. One normal non-campaign calculation (e.g. Tradicional) — unchanged.
E. A Seminovos smoke test — unchanged, unaffected.
F. The authority-unavailable state, if it can be safely reproduced
   locally (e.g. via a temporary network block) without touching
   production/backend — confirms the Portuguese message and Retry action,
   never a stale value.

No visual regression expected; no horizontal scrollbar
(`PORTAL_V2_ZERO_HORIZONTAL_SCROLL_GLOBAL_RULE` untouched). Only after
this UAT and an explicit Human approval statement may a separate, narrow
registry action restore `HUMAN_APPROVED`/`FROZEN`.
