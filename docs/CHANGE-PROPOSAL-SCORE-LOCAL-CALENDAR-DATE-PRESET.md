# Change Proposal: Score Local-Calendar Date Preset Correction

**Change ID:** `SCORE_LOCAL_CALENDAR_DATE_PRESET_FIX`
**Change type:** Date-serialization bug fix — **not** a visual redesign,
not a Design System change, not a Score formula/weight/threshold/band
change, not a drill-down feature (see the immediately preceding wave's
own `SCORE_DRILLDOWN_ALREADY_CLOSED` finding, which remains untouched and
unrelated).
**Module:** Score (Análise de Score Vendedores) — `assets/js/score.js`,
frozen at `migrationStatus: HUMAN_APPROVED` (Real Data Integration Phase
2C's own human UAT, reconciled Painel Master V2 Phase 3B).
**Authorization:** This correction addresses a defect already disclosed
in the repository's own record as known debt (see "The defect" below) —
not a new capability request. Per the Skill's Human Approved Freeze
rule, reopening still requires a Design System Change Proposal + new
Human approval; this document is that proposal, and `migrationStatus`
is moved to `UAT_PENDING` alongside it (see "Registry" below).

## Status (updated 2026-09-07)

- **Implementation:** COMPLETE.
- **Technical validation:** PASS — `SCORE_LOCAL_CALENDAR_FIX_TECH_READY_HUMAN_UAT_PENDING`
  (RED proven empirically before the fix, GREEN after; full existing
  Score regression suite reconfirmed green; see "Tests" below).
- **Human UAT:** PENDING. Not yet requested/performed. Refreeze criteria
  below.
- **Refreeze:** NOT YET AUTHORIZED. `config/module-registry.json`'s
  `score` entry stays `UAT_PENDING` until the Human explicitly confirms
  the local build (see "Human UAT required" below); this technical wave
  does not self-promote back to `HUMAN_APPROVED`.

## No Design System change

This change touches zero visual presentation. No component, token,
layout, color, typography, table structure, ranking order, band logic,
or responsive behavior is modified. Every existing screenshot/UI-parity
contract for Score remains valid without re-verification of anything
visual. `NO_LAYOUT_CHANGE` — confirmed: the diff touches only date-math
functions inside `assets/js/score.js` (no `.css` file, no new DOM
structure, no new class name).

## The defect

Confirmed by direct source read (not assumed) and already recorded as
known debt in this repository before this wave, in two independent
places:
- `tests/fi-ux-1-date-preset-test.py`'s own docstring: *"This is NOT the
  same defect as Score's own known UTC-boundary issue — Score is
  untouched by this wave."*
- The immediately preceding Score drill-down reconciliation wave's own
  final report (`SCORE_DRILLDOWN_ALREADY_CLOSED`), which independently
  re-confirmed the same debt at `assets/js/score.js:76` while
  investigating an unrelated question.

`computePreset(preset)` (the function backing the "Mês atual"/"Mês
anterior"/"Últimos 6 meses"/"Último ano" quick-period buttons) builds
`start`/`end` as **local-time** `Date` objects — `new Date(year, month,
day)` (local midnight) for `start`, and the raw "now" object for `end`
in 3 of 4 branches — then serializes both via `.toISOString().slice(0,
10)`. `.toISOString()` expresses a moment in **UTC**, not local
calendar time; for a host whose timezone offset is non-zero and whose
constructed instant sits close enough to a day boundary, this shifts
the reported calendar date by one day, in either direction depending on
the offset's sign:

- **UTC-3 (e.g., America/Sao_Paulo), late evening:** the `end` branches'
  raw "now" Date, taken close to local midnight, is exported ONE DAY
  FORWARD once converted to UTC.
- **UTC+14 (e.g., Pacific/Kiritimati), just after local midnight:** the
  `start` branches' locally-constructed midnight Date is exported ONE
  DAY BACKWARD once converted to UTC.

Score's OWN pre-existing `todayIso()` (used only for the manual/custom
date-range field's default value) already used the CORRECT pattern —
reading `getFullYear()/getMonth()/getDate()` directly, with no UTC
round-trip at all — proving the correct pattern was already present in
this exact file; `computePreset()` simply never reused it.

This is the same defect CLASS already fixed for Gestão (`gestao.js`) and
Dashbi (`dashbi.js`) during FI-UX-1, each via an independently-duplicated
`localIso(d)` helper (a small, deliberately-not-shared pattern, per that
fix's own rationale: *"a small duplicated fix is safer here than a new
shared-utility layer that would also have to avoid touching Score"*) —
originally established in `coparticipado.js`'s own `localIso()` (FC-2.4).
Score is the last of the four analytical modules to receive it.

## The correction

1. `assets/js/score.js`: added `function localIso(d) { return
   d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') +
   '-' + String(d.getDate()).padStart(2, '0'); }` — byte-identical
   construction to `coparticipado.js`/`gestao.js`/`dashbi.js`'s own
   `localIso()`.
2. `todayIso()` refactored to `return localIso(new Date());` — same
   observable behavior (it was already correct), now sharing the one
   helper instead of duplicating the formatting logic a second time
   inside the same file.
3. `computePreset(preset)`'s return statement changed from
   `{ start: start.toISOString().slice(0, 10), end: end.toISOString().
   slice(0, 10) }` to `{ start: localIso(start), end: localIso(end) }`.
   No other line in this function changed — the date-MATH (which month/
   day each preset resolves to) is byte-identical; only the final
   serialization step changed.

Nothing else in `score.js` was touched. `score.adapter.js` (`calcScores()`
and everything else the Skill's Freeze rule protects) is untouched —
confirmed via `git diff`, and reconfirmed by the parity suite below
staying green with the SAME 12 golden fixtures.

## Score engine/formula — untouched

`calcScores()`, `SCORE_WEIGHTS`, `MIX_PLANOS_UNIVERSO`, the score band
classifier, and the ranking sort are byte-identical before and after
this change (confirmed: 0 diff outside `score.js`'s date functions).
Given the same `p_start`/`p_end` values, the Score engine's result is
provably unchanged — this wave only affects WHICH `p_start`/`p_end`
values a preset button produces near timezone boundaries, never how
those values are used downstream.

## Registry

`config/module-registry.json`'s `score` entry: `migrationStatus` moved
`HUMAN_APPROVED` → `UAT_PENDING`, scoped explicitly to this one
correction (`SCORE_LOCAL_CALENDAR_DATE_PRESET_FIX`) via a new sentence
appended to its existing `humanApprovalNote` — the full prior approval
chronology (Score Band Business Rule/Visual/Responsive, Real Data
Integration Phase 2A/2B/2C) is preserved verbatim, not erased.

## Tests

- `tests/score-date-preset-test.py` (new, 31 checks): the same A–E
  month/leap-year/boundary matrix technique already proven in
  `tests/fi-ux-1-date-preset-test.py`, plus the two critical
  cross-timezone boundary cases (CASE F: America/Sao_Paulo, UTC-3, late
  evening; CASE G: Pacific/Kiritimati, UTC+14, just after midnight),
  plus a provider-argument proof (the RPC's real `p_start`/`p_end` match
  the displayed dates for every case), plus a manual/custom
  date-range-path regression (untouched, confirmed unaffected), plus a
  regression on `todayIso()`'s own refactor. RED proven empirically
  before the fix (CASE F and CASE G failed exactly as predicted, all
  other 29 checks already passed against the unfixed code — proving the
  defect is real but narrowly confined to timezone-boundary conditions,
  not a general date-math error); GREEN after.
- `tests/score-real-contract-test.py`, `tests/score-parity-test.py`,
  `tests/score-band-test.py`, `tests/score-spf-defect-test.py`,
  `tests/score-family-mapping-test.py`, `tests/score-period-filter-test.py`,
  `tests/registry-test.py`: reconfirmed green (exact counts in the wave's
  own final report).
- `tests/fi-ux-1-date-preset-test.py`: reconfirmed green, unmodified in
  its own assertions — its docstring received one small addendum noting
  Score was fixed later, in this dedicated file, preserving rather than
  rewriting its original "Score is untouched by this wave" statement.

## Risks

- **Low.** The fix is a pure serialization change (how an already-
  correct in-memory Date is turned into a string), reusing an
  already-proven pattern from 3 sibling modules. No backend change, no
  new RPC parameter, no new permission.
- The defect only manifests for a narrow window near local-midnight in
  timezones offset from UTC by roughly ±3 hours or more at the relevant
  time of day — most day-to-day usage in a typical business timezone at
  typical business hours was never affected, which is consistent with
  this debt having gone unnoticed until explicitly investigated.

## Rollback strategy

Rollback means reverting this change's V2 commit (`git revert`), not
reintroducing `.toISOString()` for calendar-date serialization anywhere
in `score.js`.

## Human UAT required

Refreeze criteria: the Human opens the V2 localhost build, exercises
all 4 quick-period buttons ("Mês atual", "Mês anterior", "Últimos 6
meses", "Último ano"), and confirms the displayed start/end dates match
today's real local calendar date (exact expected values computed and
provided in the wave's own final report, since they depend on the real
date UAT is performed on) — plus confirms no other visual/behavioral
change is present. Only after that confirmation may a separate, narrow
registry action restore `migrationStatus: HUMAN_APPROVED`.
