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

## Human UAT required (not yet satisfied)

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
