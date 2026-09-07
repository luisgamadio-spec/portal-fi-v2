# Change Proposal: V2 Coparticipado Governed Rate Authority Correction

**Change ID:** `V2_COPART_GOVERNED_RATE_AUTHORITY_CORRECTION`
**Change type:** Financial data authority correction — **not** a visual
redesign, not a Design System change, not a formula change.
**Module:** Coparticipado (`assets/js/coparticipado.js` + adapters), frozen
at `migrationStatus: HUMAN_APPROVED` since PORTAL-NEXT-06.
**Authorization:** Explicit, narrowly-scoped Human authorization to reopen
the frozen module for this one correction (2026-09-07), satisfying the
freeze note's own "Design System Change Proposal + new human approval"
requirement (Skill's Human Approved Freeze rule). This document is that
proposal.

## Status (updated 2026-09-07, post-UAT)

- **Implementation:** COMPLETE — commit `9af543a`
  ("fix(v2): use governed copart rate authority").
- **Technical validation:** PASS — `V2_COPART_GOVERNED_RATE_AUTHORITY_TECHNICALLY_READY`
  (all tests in the "Tests" section below green; targeted governed-
  authority regression, 15-model parity, and stale-fallback-blocked
  reconfirmed green again immediately before refreeze).
- **Human UAT:** APPROVED. Human statement, verbatim: **"ok, validado."**
  — given after testing the V2 localhost build on commit `9af543a`.
  Classification: `V2_COPART_GOVERNED_RATE_AUTHORITY_HUMAN_APPROVED_LOCAL`.
- **Refreeze:** AUTHORIZED / COMPLETE. `config/module-registry.json`'s
  `coparticipado` entry is restored to `migrationStatus: HUMAN_APPROVED`
  (chronology preserved in that entry's own `humanApprovalNote`, not
  overwritten). The module is FROZEN again as of this status — any
  future functional change again requires a new Design System Change
  Proposal + new Human approval.
- **Debt NOT resolved by this correction** (unchanged, separate future
  work): `COPART_TEMPORAL_RATE_RESOLUTION_DEBT`,
  `V2_SIMULADOR_NOVOS_GOVERNED_RATE_PARITY_AUDIT_REQUIRED`.

## No Design System change

This change touches zero visual presentation. No component, token, layout,
color, typography, table structure, or responsive behavior is modified.
Every existing screenshot/UI-parity contract for Coparticipado remains
valid without re-verification of anything visual.

## The defect

An earlier read-only audit (portal-financiamento-brabus-secure, kept
strictly read-only, used here only as behavioral/contract reference — see
that repository's own Fase 1–3.J investigation trail for the full proof)
established that the real transport's Coparticipação/Rebate calculation
was reading its Modelo × Rebate Total × Parte Brabus rate table from the
wrong source:

- **Old authority (WRONG):** `operational_score_coparticipated_data`'s own
  `rates` field, backed by table `coparticipado_modelos_fi` — proven, by
  direct read-only inspection of that table in the Secure repository's own
  investigation, frozen and unmodified since **2026-06-30**, materially
  diverging from the actively-governed rate table for at least 3 of 15
  models (Outlander Signature: 20.5%/40% vs. governed 17.12%/48%; Outlander
  HPE-S: 18.5%/40% vs. governed ~19.23%/48%; Eclipse Cross Rush: a smaller
  ~0.2pp drift).
- **Governed authority (CORRECT):** `simulador_get_coparticipado`, the
  same actively-maintained, versioned ACTIVE managed batch that Simulador
  de Novos' own reference implementation is designed around.

V2's Coparticipado real-data pipeline (`coparticipado-real-provider.js` →
`coparticipado-real-view-model.js`) was extracted, deliberately and
correctly at the time, byte-identical to production's own pre-correction
behavior — inheriting this same defect by construction, not by a new V2
bug.

## The correction

1. New file `assets/js/adapters/coparticipado-governed-rates-provider.js`
   — a thin transport provider, matching every other real provider's
   pattern in this codebase exactly (`window.NX_AUTH.getAccessToken()` +
   `window.NX_INTELLIGENCE_CONFIG`, no independent Supabase client, no
   `service_role`, no new backend). Calls `simulador_get_coparticipado`
   (already deployed, already granted to `authenticated` sessions, no
   schema/migration/RPC change).
2. `coparticipado-real-view-model.js`: `buildRealResult(payload,
   governedPayload)` now builds `DATA.taxasCopart` from
   `governedPayload.linhas.matriz_modelos` instead of `payload.rates`.
   `payload.rates` remains in the operational payload's own contract
   (backend unchanged) but is never read for this purpose again.
   `sales`/`finance` mapping is completely untouched.
3. `coparticipado.js`: `loadReal()` now resolves the operational RPC and
   the governed-rates RPC via `Promise.all`, sharing one
   `AbortController`. A financial result is only ever published once
   **both** succeed. Either one failing (including a shared abort)
   surfaces the module's existing `errorStateHtml()` — no new UI state
   was introduced.
4. `index.html` / `tests/_coparticipado-real-provider-harness.html`: one
   new `<script src="...coparticipado-governed-rates-provider.js">` tag
   each, in the same load-order position as the sibling real provider.

The formula itself — `valorFinanciado × rebateTotal × parteBrabus`
(`calcCoparticipacaoDetalhe()` in `coparticipado.adapter.js`) — is
**untouched**, still byte-identical to its original extraction. Model
normalization (`taxaKey()`) is reused verbatim, not reimplemented.

## Fail-closed

If the governed rate authority fails for any reason (network, session,
`42501`, empty `matriz_modelos`, malformed response) while the operational
RPC succeeds, the module blocks with the existing error state — it never
falls back to `payload.rates`, never uses a fixture, never hardcodes a
rate. Proven by dedicated negative tests, including one where a valid
stale legacy rate is present in the operational payload at the same time
the governed call fails — the stale value is never rendered.

## Score

Score's own real pipeline (`score-real-provider.js` /
`score-real-view-model.js` / `score.adapter.js`) calls the same
`operational_score_coparticipated_data` RPC for `sales`/`finance`, but —
confirmed by direct source read, including that file's own documented
history of a briefly-added-then-removed rate lookup (FC-2/FC-2.2 → FC-2.3)
— never reads its `rates` field and never computes
`calcCoparticipacaoDetalhe()`/`taxasCopart` for scoring, ranking, or any
displayed value. Score's ranking/points algorithm (`calcScores()`) has
zero reference to rebate/taxasCopart anywhere. **No Score file is touched
by this change.**

## Simulador de Novos

Out of scope for this correction. A related but separate finding (not
fixed here): V2's Simulador de Novos does not currently call
`simulador_get_coparticipado` at all — it uses a fully hardcoded `MODELS`
array in `financiamento-campanha.adapter.js`. Registered as debt:
`V2_SIMULADOR_NOVOS_GOVERNED_RATE_PARITY_AUDIT_REQUIRED`.

## Tests

- `tests/coparticipado-governed-rate-authority-test.py` (new, 23
  assertions): golden R$114.990/R$146.000, negative test against the old
  20.5%/40% result, 15-model source+financial parity and 6-term
  invariance against a frozen contract fixture
  (`tests/fixtures/coparticipado-governed-rates-contract.json` — a
  regression snapshot, never a runtime authority), and 6 fail-closed
  scenarios (governed failure with stale legacy rate available, empty
  governed response, malformed governed response, governed `42501`,
  governed network failure, governed `401`).
- `tests/coparticipado-real-provider-test.py` (34/34, updated): every
  real-transport scenario now also routes the governed endpoint; check 13
  (rebate formula) now sources its expected values through the governed
  contract shape instead of the legacy percent-style `rates` shape,
  preserving its original expected numbers.
- `tests/coparticipado-fc24-test.py` (60/60, updated) and
  `tests/coparticipado-gap003-export-test.py` (55/55, updated): both use
  a shared `mount_real()` real-transport helper that now also routes the
  governed endpoint by default.
- `tests/coparticipado-parity-test.py` (22/22) and
  `tests/coparticipado-presentation-parity-test.py` (10/10): fixture-mode
  only, untouched code path, unaffected — reconfirmed green.
- `tests/score-real-contract-test.py` (37/37): reconfirmed green, proving
  zero Score impact.
- `tests/registry-test.py`: reconfirmed green (its own `EXPECTED_STATUS`
  allowlist for `coparticipado` already included `UAT_PENDING`).

**RED-before-fix was proven empirically**, not just reasoned about: the
implementation files were temporarily reverted via `git stash` (scoped to
exactly those files, leaving unrelated dirty work untouched), the new
governed-authority test suite was run against that reverted code, and it
failed exactly as expected (a test waiting for the fail-closed error state
timed out, because the unfixed code never calls the governed endpoint at
all and therefore never blocks). The stash was then restored and the full
suite re-confirmed green.

Pre-existing, unrelated failure noted (not caused by this change, not
fixed by this change): `tests/score-presentation-parity-test.py` times out
waiting for `#scFixtureSelect` in fixture mode, a code path this change
never touches — confirmed by re-running it with zero Score files modified
by this wave.

## Risks

- **Low.** The new code path reuses an already-deployed, already-granted
  RPC and an already-established provider pattern; no backend change, no
  new permission, no schema change.
- The only behavioral risk is the stricter `Promise.all` gating: a
  transient governed-RPC hiccup now blocks the whole panel (including
  `sales`/`finance`, which used to render independently of rate
  availability). This is a deliberate, brief-mandated trade-off (Gate 19:
  "must not publish a financial result until BOTH... resolve") — accepted
  because the alternative (partial data with unavailable/incorrect rates)
  is worse for a financial-reconciliation tool.
- Temporal rate resolution (rate vigency by operation date, as opposed to
  "whatever is ACTIVE right now") remains unresolved — `COPART_TEMPORAL_
  RATE_RESOLUTION_DEBT`, unchanged by this correction, not invented here
  either.

## Rollback strategy

Rollback means **reverting this change's V2 commit** (`git revert`), not
introducing a runtime fallback to legacy rates. A silent stale-rate
fallback must never be reintroduced as an emergency mechanism — if the
governed authority needs to be temporarily unavailable, the module should
correctly show its existing blocked/error state, exactly as the
fail-closed tests already verify.

## Human UAT required (historical — since satisfied, see Status above)

At the time this change was implemented, it did **not** self-register
`HUMAN_APPROVED`. Interim registry state was `UAT_PENDING` (see
`config/module-registry.json`). Refreeze criteria: Human re-tests the V2
localhost build, confirms the Outlander Signature golden (R$114.990 →
~17,1% / 48,0% / ~R$19.691 / ~R$9.451), no visual regression, no
horizontal scrollbar, Subsidiado still renders normally — then, and only
then, a separate narrow registry action may restore `HUMAN_APPROVED`/
FROZEN.

**This criteria was met.** The Human tested the V2 localhost build on
commit `9af543a` and responded **"ok, validado."** The registry's
`coparticipado` entry was restored to `HUMAN_APPROVED`/FROZEN on this
basis (see the "Status" section at the top of this document, and
`config/module-registry.json`'s own `humanApprovalNote` chronology,
which preserves every step from the original PORTAL-NEXT-06 approval
through this refreeze without erasing any of it).
