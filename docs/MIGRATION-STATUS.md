# Migration Status (Gate 14, 38)

## Status enum

```
NOT_MIGRATED     — default state, nothing done yet.
IN_PROGRESS       — a Wave has started work on this module.
PARITY_PENDING     — implementation exists, FUNCTIONAL/data parity
                    not yet verified (see PORTAL-NEXT-01/
                    FUNCTIONAL-PARITY-PLAN.md).
VISUAL_PARITY_PENDING — implementation exists, VISUAL comparison
                    against an Approved Reference not yet passed (see
                    PORTAL-NEXT-01/VISUAL-PARITY-PLAN.md and, for the
                    concrete method, PORTAL-NEXT-03's
                    tests/landing-composition-regression.py).
UAT_PENDING          — parity (functional and/or visual, as
                    applicable to that module) verified, awaiting
                    human UAT.
HUMAN_APPROVED         — a human has approved this module's V2 result.
FROZEN                   — approved and locked; any further change
                          requires a Design System Change Proposal +
                          new human approval (Skill's Human Approved
                          Freeze rule).
```

**HUMAN_APPROVED is not the same thing as functional parity.**
Functional/visual parity is a technical verification step; HUMAN_
APPROVED is a separate, human judgment call that can only follow
parity, never substitute for it (Skill's Human Approval Gate).

## Current status — all modules

| Module | Status | Wave |
|---|---|---|
| Landing | BUSINESS **HUMAN_APPROVED** (PORTAL-NEXT-04, Gate 1) · RESPONSIVE **UAT_PENDING** (PORTAL-NEXT-07.6, see `docs/HUMAN-UAT-RESPONSIVE-REMEDIATION.md`) | 1 |
| Portal Shell / MASTER Admin | NOT_MIGRATED | 0 |
| Score | BUSINESS **UAT_PENDING** (PORTAL-NEXT-04 — see `docs/HUMAN-UAT-SCORE.md`; **eligible for final closure** per PORTAL-NEXT-07.7C Gate 34, subject to human confirmation of `docs/SCORE-RECEITA-SPF-NONFINITE-07-7C.md` — not self-promoted) · RESPONSIVE **HUMAN_APPROVED/FROZEN** (granted PORTAL-NEXT-07.7B, reaffirmed PORTAL-NEXT-07.7C) · SCORE BAND BUSINESS RULE **HUMAN_APPROVED/FROZEN** (PORTAL-NEXT-07.7B, Option 1 from `docs/SCORE-BAND-DISCOVERY-07-7A.md`, reaffirmed PORTAL-NEXT-07.7C) · SCORE BAND VISUAL **HUMAN_APPROVED/FROZEN** (granted PORTAL-NEXT-07.7C, per human visual UAT of PORTAL-NEXT-07.7B) · RECEITA SPF NON-FINITE DEFECT **FIXED** (PORTAL-NEXT-07.7C — see `docs/SCORE-RECEITA-SPF-NONFINITE-07-7C.md`) | 2 |
| Coparticipado | BUSINESS **HUMAN_APPROVED** (PORTAL-NEXT-06, Gate 1) · RESPONSIVE **UAT_PENDING** (PORTAL-NEXT-07.6) | 3 |
| Gestão | BUSINESS **HUMAN_APPROVED** (PORTAL-NEXT-07, Gate 1) · RESPONSIVE **UAT_PENDING** (PORTAL-NEXT-07.6) | 4 |
| Dashbi ("Análise Geral do Grupo" — a DIFFERENT, larger sibling file, not to be confused with Gestão) | BUSINESS **HUMAN_APPROVED** (reconciled PORTAL-NEXT-07.6.1, cc3a296) · RESPONSIVE **UAT_PENDING** (PORTAL-NEXT-07.6.2 found and fixed a real readability defect in the same narrow-width presentation 07.6.1 had reconciled as approved — see the PORTAL-NEXT-07.6.2 addendum below, `docs/HUMAN-UAT-RESPONSIVE-REMEDIATION.md`) | 5 |
| Simulador Novos | NOT_MIGRATED (UI) — ENGINE **PARITY_VERIFIED** (PORTAL-NEXT-08: 9 engines extracted, 40/40 parity — see `docs/SIMULATOR-ENGINE-DISCOVERY-08.md`) · BUSINESS UAT PENDING | 6 |
| Simulador Seminovos | NOT_MIGRATED (UI) — ENGINE **PARITY_VERIFIED** (PORTAL-NEXT-08: 6 reachable engines extracted, 24/24 parity + 2 confirmed dead-code engines documented — see `docs/SIMULATOR-ENGINE-DISCOVERY-08.md`) · BUSINESS UAT PENDING | 6 |
| Salários/Comissões | NOT_MIGRATED | 4 |
| Brabus Intelligence | NOT_MIGRATED | 7 |

Full detail (density, auth, functional source, approved reference,
risk, notes) in `config/module-registry.json` — this table is a
summary, not a second source of truth for that data.

## PORTAL-NEXT-03 addendum

Landing moved `NOT_MIGRATED` → `UAT_PENDING` this Wave (technical:
PASS — 20/20 structural/visual comparison checks; human: pending, see
`docs/HUMAN-UAT-LANDING.md`). Every other module is untouched. See
`docs/LANDING-CONTENT-MAP.md` for exactly how V2's real modules were
mapped onto the Approved Reference's category grammar, and what did
NOT fit this Wave (Coparticipado — deliberately not on the Landing
canvas, still reachable via the router). **Superseded PORTAL-NEXT-05**:
now that Coparticipado is a real migrated route, it was placed into
the existing `Gestão` category — see the PORTAL-NEXT-05 addendum below.

## PORTAL-NEXT-04 addendum

Score moved `NOT_MIGRATED` → `UAT_PENDING` (technical: PASS — 12/12
golden-fixture parity, see `docs/SCORE-ENGINE-AUDIT.md` and
`docs/SCORE-EXTRACTION-TRACE.md`; human: pending, see
`docs/HUMAN-UAT-SCORE.md`). Landing's `migrationStatus` updated to
`HUMAN_APPROVED` per Gate 1 (metadata-only — Landing's implementation
files remain byte-identical, re-verified this Wave). Every other
module untouched.

**Real, load-bearing finding this Wave**: `modules/score.html` was
itself proved divergent between the local clone and `origin/main` (==
production) — the local clone's `calcScores()` is NOT what production
runs. Score was correctly re-extracted from `origin/main`, not the
local clone. See `docs/SCORE-ENGINE-AUDIT.md` for the full diff
(redistributed weights, a new sample-size confidence-dampening
mechanism, a changed plan-mix methodology).

**Genuine Design System conflict, not resolved this Wave**:
`design-system-2.1/references/score.md` requires a band
(ALTO/BOM/BAIXO) that does not exist anywhere in real production Score
logic. Not invented — flagged as needing a future Design System Change
Proposal. See `docs/SCORE-ENGINE-AUDIT.md`.

## PORTAL-NEXT-05 addendum

Coparticipado moved `NOT_MIGRATED` → `UAT_PENDING` (technical: PASS —
22/22 golden-fixture parity, goldens generated by executing an
independently re-extracted reference copy in a real browser, see
`docs/COPARTICIPADO-ENGINE-AUDIT.md` and `docs/COPARTICIPADO-
EXTRACTION-TRACE.md`; human: pending, see `docs/HUMAN-UAT-
COPARTICIPADO.md`). Landing/Score re-verified byte-identical
(implementation files unchanged; `landing-groups.json` intentionally
updated to place Coparticipado into the existing `Gestão` category,
Gate 28 — no new category invented). Every other module untouched.

**Real, load-bearing finding this Wave**: same pattern as Score —
`modules/coparticipado.html` was itself proved divergent between the
local clone and `origin/main` (== production). Coparticipado was
correctly re-extracted from `origin/main`, not the local clone. 34
functions + 2 constants (classification/crossing/exclusion/priority
engine) plus 6 display/filter helpers (money/num/pct/iso/dateIn/
planBadge) extracted byte-identical — see `docs/COPARTICIPADO-ENGINE-
AUDIT.md`.

**Scope findings, not resolved/not needed this Wave**: the
"Diagnóstico" tab (vendor-registry alerts) and Excel export are
DEFERRED DEPENDENCIES (need real backend/file I/O — see extraction
trace). The row-level drill-down some other modules have is NOT
APPLICABLE here — production's own Coparticipados/Subsidiados tables
have no per-row detail modal, and none was invented to fill that gap.
A block of embedded, older Score-related code inside coparticipado.html
itself (`renderScore`, `openScoreDetails`, its own stale `calcScores`)
was confirmed DEAD CODE (unreachable from any real tab in production)
and correctly left untouched, same finding pattern as Score's own
stale-code discovery.

## PORTAL-NEXT-06 addendum

Coparticipado moved `UAT_PENDING` → `HUMAN_APPROVED` (PORTAL-NEXT-06
Gate 1 — human decision recorded in this Wave's CONTEXT section,
metadata-only update, implementation files re-verified byte-identical
before/after). Gestão (Análise F&I do Grupo) moved `NOT_MIGRATED` →
`UAT_PENDING` (technical: PASS for 37/38 extracted functions and every
KPI/table except one commission-dependent surface — 26/26 golden
fixtures, see `docs/GESTAO-ENGINE-AUDIT.md`/`GESTAO-FUNCTION-MAP.md`;
human: pending, see `docs/HUMAN-UAT-GESTAO.md`). Landing/Score/
Coparticipado re-verified byte-identical. Every other module untouched.

**Real, load-bearing finding this Wave**: "Gestão" in production is a
MENU CATEGORY (`grupo:'📊 Gestão'`), not a single module — it groups two
sibling screens, "Análise F&I do Grupo" (`gestao`, migrated this Wave)
and "Análise Geral do Grupo" (`dashbi`, a different and much larger
file, Wave 5, untouched). Unlike Score/Coparticipado, `analise-fi-
grupo.html` is NOT divergent between the local clone and `origin/main`
— all three (local/origin/live) are byte-identical for this file (the
divergence this Wave found instead was in `portal-app.js` and
`index.html`, both read from `origin/main` per standing discipline).

**RC BLOCKER #6 re-scoped, not resolved this Wave**: the original "flat
70% vs. multi-tier commissionCalc()" framing (PORTAL-NEXT-01.1) is real
but narrower than it read — only ONE Gestão KPI card + one table column
("Comissão Líquida SPF EXTRA") is affected; every other Gestão surface
is unaffected. Formalized as `docs/COMMISSION-RULE-MAP.md` +
`docs/GESTAO-COMMISSION-DECISION.md`, STATUS: PENDING HUMAN at the time.

## PORTAL-NEXT-06.1 addendum

Human UAT feedback on PORTAL-NEXT-06 requested two adjustments before
final approval: (1) table header/value alignment across Gestão, (2) the
SPF commission decision. Both resolved this Wave, Gestão remains
`UAT_PENDING` (not auto-promoted):

- **Commission decision — RESOLVED**: `docs/GESTAO-COMMISSION-DECISION.md`
  moved PENDING HUMAN → HUMAN DECIDED. Authority: "Comissão Líquida SPF
  EXTRA = Total SPF EXTRA × 70%", fixed, non-configurable, scoped to
  this one metric only — not generalized to other commissions, Salários/
  Comissões untouched. No new formula introduced (the pre-existing
  byte-identical extraction is what's now authorized). Rounding audited
  with 4 new golden fixtures (R$0/R$100/R$1.000/R$12.345,67 — the
  formula itself never rounds, only `money()`'s display formatting
  does, per raw/display separation).
- **Table alignment — FIXED**: a real bug (numeric column headers
  left-aligned while their values were right-aligned, so they didn't
  share an axis) found in human UAT, root-caused (missing `.geNumCol`
  on `<th>` elements) and fixed via one shared `headerRow()` alignment
  contract applied to every Gestão table — not per-cell offsets.
  Verified 0px header/value axis diff across all 8 tables. Score/
  Coparticipado's own tables share the same underlying pattern but were
  deliberately NOT touched (no proven need there, out of this Wave's
  scope per explicit instruction).

30/30 golden fixtures pass (26 from PORTAL-NEXT-06 + 4 new SPF-rounding
cases). Landing/Score/Coparticipado re-verified byte-identical.

## PORTAL-NEXT-07 addendum

Gestão (Análise F&I do Grupo) moved `UAT_PENDING` → `HUMAN_APPROVED`
(Gate 1 — human decision recorded in this Wave's CONTEXT section,
metadata-only, implementation files re-verified byte-identical).
Dashbi (Análise Geral do Grupo) moved `NOT_MIGRATED` → `UAT_PENDING`
(technical: PASS — 24/24 golden fixtures, see `docs/DASHBI-FUNCTION-
MAP.md`/`DASHBI-DATA-CONTRACT.md`/`DASHBI-MODEL-ANALYSIS-CONTRACT.md`/
`DASHBI-BASE02-DIAGNOSTICS.md`/`DASHBI-BASE03-SCHEMA.md`/`DASHBI-
CROSS-MODULE-CONSISTENCY.md`; human: pending, see `docs/HUMAN-UAT-
DASHBI.md`). Landing/Score/Coparticipado/Gestão re-verified byte-
identical. Every other module untouched.

**Real, load-bearing finding this Wave**: "Gestão" is confirmed as a
menu CATEGORY containing two independent sibling screens — this Wave
migrated the second one, "Análise Geral do Grupo" (dashbi,
`analise-geral-grupo-secure-original-layout.html`, 6010 lines, the
largest module migrated so far: 94 functions extracted, vs. Gestão's
38 and Coparticipado's 40). Unlike Gestão, this file IS divergent
between the local clone and `origin/main` (like Score/Coparticipado).

**Historically-cited risks, re-audited from current production
authority, not presumed still accurate**: a hard 2026-06-01 date-
cutoff splits "historical" and "Nova" (new) Base01/Base02 formats,
each with its own adapter, both streams concatenated (not chosen
exclusively); Base03 supports a positional column E/F alias fallback
for "anonymized" exports; Model Analysis's Entrada/Entrada Média/
Entrada % has a real eligibility guard (`financiado <= valorVenda ×
1.15`) and a traceable diagnostic (`chassisLocalizados`/
`chassisNaoLocalizados`) instead of an opaque zero — all confirmed
present in current production, extracted byte-identical, and covered
by dedicated golden fixtures (`base03_alias_posicional`,
`nova_entrada_com_match`, `nova_entrada_sem_match`,
`entrada_financiado_excede_tolerancia`).

**A real hard-stop validation gate, faithfully reproduced**: if any
resolved seller has no known store, production aborts rendering
entirely rather than showing a partial/wrong result
(`vendedor_nao_localizado_bloqueia` fixture) — V2's `compute()`
returns `{blocked:true}` in that case, and the UI shows an explicit
notice, never a silently-wrong partial dashboard.

**Cross-module plan-priority consistency proved a third time**:
Dashbi's own source comments explicitly cross-reference Análise F&I's
classification rule ("igual a planTypeFromFields() do módulo Análise
F&I do Grupo") — independently confirmed via a shared priority-
collision fixture run through all three modules' own extracted
engines (Dashbi/Gestão/Coparticipado), 0 unexplained difference. One
real, disclosed, NOT-unified difference was found and preserved: B3/
B03 candidate tiebreak — Coparticipado breaks ties by most-recent
contract date, Dashbi breaks ties by array order (no date comparison
exists in its own scoring function) — see `docs/DASHBI-CROSS-MODULE-
CONSISTENCY.md`.

## PORTAL-NEXT-07.1 addendum

Dashbi stays `UAT_PENDING` (never auto-promoted) — this Wave addressed the 4 issues
raised in PORTAL-NEXT-07's human UAT, technical status re-verified GREEN (25/25
golden fixtures incl. 1 new Ranking tie-break fixture; 0 console/page errors and 0
external network calls across a full 25-fixture × 3-view sweep; 0 page-level
horizontal overflow at 360/390/430; Landing/Score/Coparticipado/Gestão re-verified
byte-identical). See `docs/HUMAN-UAT-DASHBI.md` for the updated UAT script and
`docs/DASHBI-PRODUCTION-SURFACE-INVENTORY.md` for the from-scratch surface audit
this Wave was built on.

**Root cause, not just symptom, for all 4 issues**: PORTAL-NEXT-07's own production
audit was incomplete — it extracted the classification/aggregation/Entrada engine it
had identified, but never built an exhaustive inventory of every user-facing
production surface before wiring the V2 UI. Concretely: (1-2) Plan Classification and
Model Analysis were shown in all 3 views because V2 never added a visibility gate,
not because production shows them everywhere — direct source read this Wave
(`updateModelosTabVisibility`, origin/main lines 3633-3652) confirms production
itself hides both outside Novos; V2 now matches. (3) Vehicle images were never
searched for during PORTAL-NEXT-07's business-logic-focused audit — found this Wave
at origin/main line 2651 (`VEHICLE_IMAGES`, 3 real base64 product photos), decoded,
visually verified as genuine, and resized into a new compact selector — see
`docs/DASHBI-VEHICLE-ASSETS.md`. (4) Ranking and Novos por Loja's *rendering*
functions were correctly identified as presentation-only in PORTAL-NEXT-07, but their
underlying *business logic* (`rankingFromViews`, `buildNovosLojaRows`) was never read
in full and got miscategorized as deferred along with the rendering — both are now
extracted byte-identical; see `docs/RANKING-FUNCTION-MAP.md` and
`docs/NOVOS-POR-LOJA-FUNCTION-MAP.md`.

**A real, production-confirmed visibility asymmetry, not assumed**: Ranking is
visible in all 3 department views (its tab carries no Novos-only gating class in
production), while Novos por Loja is Novos-only (shares the same gating class as
Análise por Modelos, and independently self-guards in its own render function) —
both behaviors verified by direct source read, not inferred from the human's wording,
and reproduced exactly.

**A real, pre-existing bug found and fixed as a side effect of this Wave's mobile
testing, not present in PORTAL-NEXT-07's own claimed responsive pass**: the "Diagnóstico
(dev only)" footer's `JSON.stringify(sourceInfo)` dump renders as one unbroken string
with no spaces, which was silently making the entire Dashbi page horizontally
scrollable at 360/390/430 — on the Grupo view too, unrelated to any of this Wave's
additions. Fixed with a single `overflow-wrap: anywhere` rule scoped to that one
diagnostic span; 0 business-logic change.

## PORTAL-NEXT-07.2 addendum

Dashbi stays `UAT_PENDING` (never auto-promoted). PORTAL-NEXT-07.1's human UAT
confirmed the restored content (Análise por Modelos/Ranking/Novos por Loja/vehicle
imagery) was itself correct, but flagged that these 3 surfaces must not stay
expanded simultaneously — the previous Portal exposed them one at a time. This Wave
adds selective analytical navigation: a compact 4-option control (Visão Geral /
Análise por Modelos / Ranking / Novos por Loja), exactly one active at a time,
availability per department view matching production's own `updateModelosTabVisibility`
gating (already established in 07.1, reused here rather than re-derived).

**Production authority, not assumed**: production's `showTab()` (origin/main lines
4944-4961) already implements a single-active-region switcher — exactly one of
`share`/`modelos`/`ranking`/`novosLoja` gets `display:block`, the rest
`display:none`. V2's new mode switcher reproduces this behavior, not a newly
invented interaction pattern. No dedicated Design System tabs/segmented-nav
component exists (checked `design-system-2.1/references/`), so the existing
`.dbBtn` segmented-control grammar (already used on this same page for
Visão/Período) was the correct authority to extend, per this Wave's own instruction
not to blindly implement literal tabs when another approved component applies.

**A real production inconsistency found and closed, not reproduced**: production's
fallback-on-view-change is asymmetric — `updateModelosTabVisibility()` explicitly
falls back to the Share tab when Análise por Modelos becomes unavailable (leaving
Novos), but has no equivalent branch for Novos por Loja. Traced this to Novos por
Loja apparently being added in a later UX iteration (its own `UX-Grupo-3.x` source
comments postdate the Modelos-fallback code) without extending that same fallback.
Left as-is in production this would mean switching Novos+Novos-por-Loja→Seminovos
leaves no analytical content visible at all — V2 applies the same deterministic
Visão-Geral fallback uniformly to both cases instead, per this Wave's explicit "no
blank page, no stale content" requirement.

**Plan Classification re-placed within Model Analysis, not a separate block**:
confirmed by direct source read that production's `planoDestaqueFamiliaAtualHtml`
call is literally emitted inside `renderModelos()`'s own `innerHTML` assignment —
not a sibling section. V2's 07.1 implementation had it as a separate always-shown-
in-Novos block; this Wave nests it inside the Análise por Modelos mode instead,
matching production's real DOM structure.

**0 change to any already-approved content**: `dashbi.adapter.js` and every fixture
file are byte-identical to PORTAL-NEXT-07.1 (confirmed via `git diff`, 0 lines) —
this Wave touched only `dashbi.js`/`dashbi.css` (presentation). 25/25 golden
fixtures pass unchanged. Landing/Score/Coparticipado/Gestão re-verified byte-
identical. 0 console/network errors across the full visibility matrix, 0 page-level
horizontal overflow at all 6 required breakpoints (360/390/430/768/1366/1920).

## PORTAL-NEXT-07.3 addendum

Dashbi stays `UAT_PENDING`. Human UAT on PORTAL-NEXT-07.2's selective navigation
flagged that Análise por Modelos was missing columns/metrics present in current
production (named examples: Balão Médio, Parcela Média — explicitly flagged as not
the complete scope). This Wave performed a from-scratch production × V2 audit
before touching any code (`docs/MODEL-ANALYSIS-PRODUCTION-INVENTORY.md`,
`docs/MODEL-ANALYSIS-V2-INVENTORY.md`, `docs/MODEL-ANALYSIS-PRODUCTION-VS-V2.md`)
and restored every material item found missing (`docs/MODEL-ANALYSIS-RESTORATION-
MATRIX.md`): 14 family-level metric boxes (entirely absent), 8 per-model fields
(Receita/Receita SPF split, Prazo Médio, Parcela Média, Qtd Linear/Balão/Reversão,
Balão Médio), 4 more plan-breakdown tables (family total, per-loja breakdown,
special-plan detail, conditional TRITON-inconsistency table).

**Most of the restoration was a presentation gap, not a missing-extraction gap**:
`modelRowsUnified`/`familyExtraMetrics`/`planRowsByStoreForFamily` — all already
extracted byte-identical since PORTAL-NEXT-07 — already computed nearly every
missing field; V2's UI simply never rendered it. Only 3 functions needed fresh
extraction (`planTotalRowsForFamily`, `specialPlanDetailRows`,
`inconsistenciaTritonRows`) — 99 functions total, 0 mismatches against an
independently re-extracted reference.

**Metric semantics proved before restoring, not assumed** (`docs/MODEL-ANALYSIS-
METRIC-CONTRACTS.md`): "Parcela Média" = average PMT value in R$ (eligible
population: records with pmt>0, excluded not zeroed otherwise); "Prazo Médio" *is*
the average-installment-count metric — production has exactly one such metric, not
two separately-labeled ones as a plausible reading of the brief might suggest;
"Balão Médio" = average balloon value among only balloon contracts (same population
as the BALÃO plan-classification flag), not averaged across all financings. A new
golden fixture (`model_analysis_parcelamento_completo`) proves this with real
non-zero PMT/installment-count/balloon values across 2 real SKUs plus one record
with no Base03 match, confirming the exclusion (not zero-inclusion) averaging rule.

**Deliberate, disclosed presentation choice — flagged for human review**:
production's own current UI shows only 3 of the 18 per-model fields by default
(cards) with the rest behind a "Ver Detalhes" modal — its own source comment
explains this was production's real response to the same "18 columns too wide"
problem. V2 does **not** reproduce the card+modal shape: `data-table.md` (the
actual Design System authority for dense data throughout this whole engagement)
forbids cardifying tabular data. Restored instead as one wide table (grouped
headers, sticky Modelo column, horizontal scroll) — same completeness, a
different, already-approved interaction shape. Human review requested specifically
on this choice, separately from the metric semantics.

**0 change** to Ranking, Novos por Loja, the vehicle selector, selective navigation,
or any already-parity-proven metric — confirmed via `git diff` showing only
additions to `dashbi.adapter.js` (0 deletions to existing functions). 26/26 golden
fixtures (25 + 1 new). Landing/Score/Coparticipado/Gestão re-verified byte-
identical. 0 console/network errors across a full 26-fixture × 3-family sweep, 0
page-level horizontal overflow at all 6 required breakpoints.

## PORTAL-NEXT-07.4 addendum

Dashbi stays `UAT_PENDING`. Two independent items this Wave:

**Cache incident closed, no hotfix**: the human's earlier report that Análise por
Modelos "wasn't opening" (after PORTAL-NEXT-07.3) was retested after a hard
refresh and confirmed working — stale cached `dashbi.js`/`dashbi.css`, not a code
regression (already exhaustively verified in the prior exchange: 0 changes to the
click-handling code path between 07.2 and 07.3). No PORTAL-NEXT-07.3.1 hotfix was
implemented, per explicit instruction not to modify working navigation code to fix
an unproven bug.

**New global human directive — no horizontal scrolling for material information**:
superseding 07.3's own wide-table decision, which itself required horizontal
scroll at every viewport including 1920px. Full audit
(`docs/V2-HORIZONTAL-SCROLL-AUDIT.md`) found this affected every Dashbi table wide
enough to need one (store/seller, Ranking, Novos por Loja, Model Analysis's wide
table and 3 plan tables) plus, separately, at least one surface in **every**
HUMAN_APPROVED/FROZEN module (Landing's mobile nav strip, Score's ranking table,
Coparticipado's table — the most severe, scrolling even at 1920px — and multiple
Gestão tables up to 768px). Frozen modules were **not modified** — reported as
`FROZEN CONFLICT`, pending a dedicated remediation Wave the human must explicitly
authorize after Dashbi's own approval (`docs/DS-CHANGE-PROPOSAL-NO-HORIZONTAL-
SCROLL-01.md`).

**Dashbi recomposed**: every table replaced with a shared "primary row + inline
`+ Detalhes`" component (`docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md`) — a compact,
genuinely tabular comparison row plus a one-click vertical expansion for
everything else, multiple rows expandable simultaneously per explicit human
preference. Not a card grid (would violate `data-table.md`'s "table stays table"
rule); not a modal (production's own current pattern, explicitly rejected in favor
of inline vertical disclosure). Full completeness re-verified against the frozen
07.3 production inventory (`docs/MODEL-ANALYSIS-PRIMARY-DETAIL-MAP.md`): 0
unmapped, 0 inaccessible material items.

**0 business-logic change**: `git diff` shows 0 lines changed in
`dashbi.adapter.js`, `_dashbi-reference.js`, or `dashbi-fixtures.json` — this Wave
touched only `dashbi.js`/`dashbi.css` (presentation). 26/26 golden fixtures
unchanged. Landing/Score/Coparticipado/Gestão re-verified byte-identical
(untouched, per the frozen-conflict reporting rule). Automated sweep: 48/48
view×mode×viewport combinations pass with 0 horizontal overflow (detail panels
open, worst case); full 26-fixture × 3-family sweep at 390px with every detail
expanded: 0 overflow, 0 console errors.

## PORTAL-NEXT-07.4.1 addendum

Dashbi stays `UAT_PENDING`. Human UAT **strongly approved** the 07.4 primary +
inline "+ Detalhes" experience, with two narrow presentation corrections inside
the expanded model detail: "Entrada Qtd" removed (never a production metric,
only the internal denominator `entradaMed` divides by — still computed, just not
shown); Qtd Subsidiado and Qtd Coparticipado added to the Planos group, next to
the already-present Qtd Linear/Qtd Balão/Qtd Reversão.

Traced before adding anything: `aggregate()`'s own `compVals` (already extracted
byte-identical) computes `subsidiadoQtd`/`coparticipadoQtd` on the same
`compModelo` aggregation, same population, same mutually-exclusive classifiers as
`linearQtd`/`balaoQtd` — production's own `modelRowsUnified` just never surfaced
those two fields into its row shape. Sourced from `planRowsByModel` (already
extracted, already on-page one section below), matched by Modelo — no new
business-logic extraction. Reconciliation proved with a real golden fixture
(extended with 1 real Subsidiado and 1 real Coparticipado contract):
Subsidiado+Reversão+Coparticipado+Balão+Linear sums exactly to Financiamentos for
both tested models, 0 double counting. Order follows the official classification
priority (SUBSIDIADO>REVERSÃO>COPARTICIPADO>BALÃO>LINEAR), per explicit human
preference. See `docs/MODEL-ANALYSIS-METRIC-CONTRACTS.md`.

0 business-logic change (`dashbi.adapter.js`/`_dashbi-reference.js`: 0 diff —
only `dashbi.js` presentation and `dashbi-fixtures.json` changed). 26/26 golden
fixtures pass. 0 horizontal overflow reintroduced (re-verified at both document
and component level, full 8-scenario × 6-viewport sweep plus 26-fixture ×
3-family sweep). Landing/Score/Coparticipado/Gestão byte-identical.

## PORTAL-NEXT-07.5 addendum

Dashbi stays `UAT_PENDING`. New human product authority this Wave: 5
PRIMARY metrics (Vendas, Financiamentos, Share, Produção Total, Receita
Total) must be immediately visible wherever they semantically exist,
with 0 +Detalhes/modal/extra navigation needed to reach them; Receita
SPF and Retorno Médio may stay secondary. Named example of the prior
violation: the Loja table showed Produção/Receita Total only behind
`+ Detalhes`.

**Full surface audit before any code change**
(`docs/DASHBI-ANALYTICAL-HIERARCHY-INVENTORY.md`): confirmed Produção/
Receita Total already existed as computed, unrendered fields on
`finLoja`/`finVendDept`/ranking rows (a presentation gap, not an
extraction gap — the same recurring pattern as every prior Wave in this
sequence). Confirmed no distinct "department analysis" V2 surface
exists (only Ranking's own Departamentos dimension) — not invented.
Confirmed Novos por Loja's business universe (`buildNovosLojaRows`) has
no production/financing-value field at all — Produção Total/Receita
Total correctly reported NOT APPLICABLE there rather than fabricated;
only a derived Share (Financiados/Vendidos, same ratio pattern used
everywhere else) was added to its primary row.

**Promoted to primary** (`docs/DASHBI-PRIMARY-DETAIL-MAP.md` is the
full after-state contract): Overview KPI grid (Share and Receita Total
become their own cards instead of hint text under Financiamentos/
Receita); Loja and Vendedor tables (Produção Total, Receita Total);
Ranking's 3 dimensions (Share/Penetração, Produção Total — Receita
Total was already primary, being the sort key); Novos por Loja (derived
Share). Retorno Médio moved out of the KPI grid's primary row into a
new KPI-level `+ Detalhes` toggle alongside Receita (base)/Receita SPF
— the KPI grid never had a detail mechanism before this Wave.

**Share emphasis**: reused the already-approved `penetracaoCellHtml()`/
`.dbPenetracaoBaixa`/`.dbPenetracaoOk` pattern (Model Analysis, 07.3) —
same threshold, same classes, 0 new logic, applied consistently across
every table gaining a Share column. Threshold re-confirmed against
current production authority this Wave (not assumed from memory):
v<0.40 → baixa, per `docs/DASHBI-KPI-CONTRACT.md`
(`pctPenetracao`, origin/main lines 2788-2794).

**Receita Total emphasis — new token usage, documented, not invented
silently**: no exact "financial value emphasis" token exists in
`design-system-2/tokens.css` (the real token authority, confirmed via
`index.html`'s own `<link>` order). `--color-accent-primary` was
rejected (already load-bearing for interactive/selection state
elsewhere on this same page); `--color-info` was selected as a
provisional, documented reuse — see
`docs/DS-CHANGE-PROPOSAL-RECEITA-TOTAL-EMPHASIS-01.md`, including a
computed contrast ratio (≈7.66:1 against `--color-canvas`, WCAG AAA).
Share and Receita Total are distinguishable from each other and from
plain KPI cards by position (left vs. top border stripe) and hue family
(status vs. info), not color alone; applied ONLY to the KPI-grid cards
(the most prominent surface) — table cells keep plain-formatted values,
per the explicit "not a rainbow" instruction.

**Responsive strategy — a genuinely new component, not a shrink**: the
existing `.dbDesktopCol` hide-and-duplicate-in-detail pattern (Model
Analysis, 07.4) does not satisfy this Wave's rule (all 5 primary metrics
outside `+ Detalhes` at every viewport, mobile included), so a new
opt-in `.dbTableStackable` modifier recomposes each row into a vertical
label/value stack at <=480px instead, applied only to
store/seller/Ranking/Novos-por-Loja (Model Analysis's own tables
untouched, Gate 32). A real bug was caught and fixed during this Wave's
own verification: the first CSS draft let stacked metric cells shrink to
near-zero width, combining with the pre-existing
`word-break:break-word` rule to wrap every character onto its own
line — fixed with an explicit `min-width:108px` per stacked cell, then
re-verified clean via screenshot.

**0 business-logic change**: `dashbi.adapter.js`/`_dashbi-reference.js`/
`dashbi-fixtures.json` — 0 diff. 26/26 golden fixtures pass unchanged.
Model Analysis spot-checked via Playwright (fixture
`model_analysis_parcelamento_completo`): "Entrada Qtd" still absent, all
5 plan Qtd categories still present, 0 horizontal overflow — matches
07.4.1 exactly, not reopened. Full no-horizontal-scroll matrix
(document- and component-level `.dbTableWrap` scrollWidth check, a
detail row expanded at every viewport as the worst case) re-verified
clean at all 6 required viewports (360/390/430/768/1366/1920). 0
console/page errors, 0 network calls. Landing/Score/Coparticipado/
Gestão untouched (not re-read this Wave beyond the existing automated
parity suites, which stayed green). Isolation baseline
(`.baseline-portalnext075-after.txt`) shows 0-line diff against
`.baseline-portalnext0741-after.txt` across all ~30 sibling worktrees;
`origin/main` SHA re-confirmed unchanged
(`2f17eb2341c5cc14aa8710aa044103002ca572a9`).

## PORTAL-NEXT-07.5.1 addendum

Dashbi stays `UAT_PENDING`. One final human-directed presentation
adjustment before UAT: removed 4 redundant Análise por Modelos
sections — "Resumo tipos de plano", "Quantidade por tipo de plano /
Modelo", "Quantidade por tipo de plano / Loja", "Detalhe Coparticipado
/ Subsidiado / Reversão" — per explicit human decision that they now
duplicate what the approved per-model `+ Detalhes` (07.4/07.4.1)
already shows. Presentation-only; Model Analysis's own compact table
and `+ Detalhes` (family/model selector, primary metrics, Financeiro/
Retorno/Parcelamento/Entrada/Planos groups, multiple-open behavior)
untouched. See `docs/MODEL-ANALYSIS-REDUNDANT-SECTIONS-REMOVAL.md`.

**Reuse traced before deleting anything (Gate 1)**: `planRows` (from
`A.planRowsByModel()`) feeds BOTH the removed "Quantidade por tipo de
plano / Modelo" table AND the approved `+ Detalhes` Planos group's
`subsidiadoQtd`/`coparticipadoQtd` merge — only the redundant
*rendering* call was removed, `planRows`/`planRowsByModel()`/the merge
itself stay. The other 3 removed sections' data sources
(`planTotalRowsForFamily`, `planRowsByStoreForFamily`,
`specialPlanDetailRows`) had no other caller — their adapter functions
remain intact (unused by any V2 renderer now, still exported, 0
business logic deleted). 3 now-fully-dead V2 rendering helpers
(`planPctTableHtml`/`planPctBodyRow`/`planPctPrimaryHeaders`, 0
remaining callers) were removed along with their call sites.

**Information-retention audit, reported honestly, not converted to
false PASS**: family-level plan-type percentages, per-model plan-type
percentages, per-loja plan-type breakdown, and per-record
Cliente/Produção/Receita drill-down for Coparticipado/Subsidiado/
Reversão financings are genuinely no longer shown anywhere (marked
REVIEW, not AVAILABLE) — only the raw per-model plan quantities
survive, via the already-approved `+ Detalhes` Planos group. Per
explicit human instruction, no replacement UI was added to preserve
these — full table in
`docs/MODEL-ANALYSIS-REDUNDANT-SECTIONS-REMOVAL.md`.

**0 business-logic change**: `dashbi.adapter.js`/`_dashbi-reference.js`/
`dashbi-fixtures.json` — 0 diff. 26/26 golden fixtures pass unchanged.
Verified in a real browser: all 4 removed section headings — 0
occurrences in rendered Análise por Modelos; "Inconsistências TRITON"
(not in the removal list) untouched; the family's Planos `+ Detalhes`
group still shows all 5 quantities, reconciling exactly to the family
totals; multiple rows still expand simultaneously; no orphan headings,
empty shells, or blank gaps where the 4 sections used to be — the
section ends naturally right after the model table. No-horizontal-
scroll re-verified clean at all 6 required viewports (document- and
component-level, a detail row expanded). Other Dashbi surfaces (Visão
Geral KPI grid, Ranking) spot-checked unchanged. 0 console/page errors,
0 network calls. Isolation baseline
(`.baseline-portalnext0751-after.txt`) 0-line diff against
`.baseline-portalnext075-after.txt`; `origin/main` SHA re-confirmed
unchanged (`2f17eb2341c5cc14aa8710aa044103002ca572a9`).

## PORTAL-NEXT-07.5.2 addendum

Dashbi stays `UAT_PENDING`. Human decision: Ranking's "Departamentos"
dimension removed from the rendered UI — "not required in the final
analytical experience," presentation simplification. Ranking now
contains exactly Vendedores and Lojas.

**Reuse checked before removing (Gate 1)**: `A.rankingFromViews()` is
shared by all 3 kinds (`vendedor`/`loja`/`dept`) — the function itself
stays, called with `'vendedor'`/`'loja'` as before. Only the `depts`
variable (`rankingFromViews(..., 'dept')`) and its
`rankingTableHtml(A, 'Departamentos', depts, 'dept')` render call were
removed from `rankingHtml()`. The underlying `vendasDept`/`finDept`
department aggregation in `aggregate()` was already unused by any other
V2 surface before this change (confirmed in
`docs/DASHBI-ANALYTICAL-HIERARCHY-INVENTORY.md`, PORTAL-NEXT-07.5) and
remains fully intact in the adapter — 0 business logic deleted.

**0 business-logic change**: `dashbi.adapter.js`/`_dashbi-reference.js`/
`dashbi-fixtures.json` — 0 diff. 26/26 golden fixtures unchanged
(`dashbi-parity-test.py` only exercises `NX_DASHBI_ADAPTER.compute()`,
which never called `rankingFromViews()` at all — this presentation-only
removal could not affect it). Verified in a real browser: Ranking shows
exactly 2 sections (Vendedores, Lojas), both with their full primary
5-metric header row and working `+ Detalhes` (multiple rows open
simultaneously, same as before), the section ends naturally after the
Lojas table with no blank gap or orphan heading where Departamentos
used to be. Model Analysis (07.5.1's removed sections stay removed),
Overview KPI grid, and Novos por Loja spot-checked unchanged.
No-horizontal-scroll re-verified clean at all 6 required viewports,
document- and component-level, a detail row expanded (worst case). 0
console/page errors, 0 network calls. Isolation baseline
(`.baseline-portalnext0752-after.txt`) 0-line diff against
`.baseline-portalnext0751-after.txt`; `origin/main` SHA re-confirmed
unchanged (`2f17eb2341c5cc14aa8710aa044103002ca572a9`).

## PORTAL-NEXT-07.6 addendum

Dedicated responsive remediation Wave for Landing/Score/Coparticipado/
Gestão — eliminating the horizontal-scroll dependencies each module's
own prior audit (07.4) had flagged but deliberately not touched at the
time (they were already approved and out of scope then). Dashbi
explicitly not modified this Wave (only regression-verified — 26/26
goldens, byte-identical `dashbi.js`/`dashbi.css`/`dashbi.adapter.js`
hashes before/after).

**Premise discrepancy, flagged rather than silently accepted**: this
Wave's own brief stated Score and Dashbi were already `HUMAN_APPROVED /
FROZEN`. `config/module-registry.json`'s actual `migrationStatus` shows
both as `UAT_PENDING` — Score has been `UAT_PENDING` since PORTAL-NEXT-04
(its own Design System band conflict, `docs/SCORE-ENGINE-AUDIT.md`, was
never resolved), and Dashbi has been `UAT_PENDING` since PORTAL-NEXT-07.5.2
(no human approval message was received in between). Reported here
per this whole engagement's standing "do not convert UNKNOWN into PASS"
discipline — not corrected unilaterally, not treated as blocking the
requested technical work either (the remediation itself is valid
regardless of exact approval status, and Dashbi was left untouched
exactly as instructed either way).

**Full audit before any fix (Gate 2)**: `docs/FROZEN-MODULE-NO-SCROLL-
INVENTORY.md` — real DOM measurement (not CSS inference) found every
module's own `*TableWrap` table overflowing via the same root cause
(no `table-layout:fixed`, so auto-layout sized every column to its
widest un-wrapped content): Landing's mobile category nav (up to 339px
over via a literal `overflow-x:auto`), Score's ranking table (up to
174px) plus a name-truncation bug, Gestão's 8 tables (up to 819px), and
Coparticipado's Coparticipados/Subsidiados tables — the most severe
case in V2, still 469px over even at 1920px.

**Recomposition, not hiding (Gate 66)**: every fix follows the same
already-proven recipe (`table-layout:fixed` + wrap, `data-th`-driven
vertical stacking below each table's own natural breakpoint — 480px for
Score, 768px for Gestão, 900px for Coparticipado's unusually wide
13-column record). Coparticipado additionally needed a `<colgroup>`
floor-width + `nowrap` protection for its atomic (currency/percentage/
date/chassi) columns — a real character-collapse bug ("R$ 155.00" +
"0" on the next line) was caught by re-screenshotting after the first
wrap-only attempt and fixed before being reported clean, not assumed
safe. No column, table, or field was hidden or moved behind a new
`+ Detalhes`; Coparticipado's mobile view is a full vertical record
(every field), since no authorized primary/secondary hierarchy exists
for it (unlike Dashbi's own human-directed KPI hierarchy) and none was
invented.

**0 business-logic change**: Score 12/12, Coparticipado 22/22, Gestão
30/30 golden fixtures pass unchanged (including all 4 SPF-rounding
fixtures — Comissão Líquida SPF EXTRA = 70%, untouched); Landing's own
`landing-composition-regression.py` (20/20) shows 0.0pp drift on every
desktop (1366/1920) structural check. Full field-by-field parity in
`docs/FROZEN-MODULE-RESPONSIVE-INFORMATION-PARITY.md` — material
information loss: 0. Isolation baseline
(`.baseline-portalnext076-after.txt`) 0-line diff against
`.baseline-portalnext0752-after.txt`; `origin/main` SHA re-confirmed
unchanged (`2f17eb2341c5cc14aa8710aa044103002ca572a9`).

**Honestly scoped, not exhaustively automated**: keyboard/focus/touch-
target behavior was verified by code-diff audit (no interactive/focus
code was touched in any of the 7 changed files), not by live automated
re-testing; 200% zoom, continuous resize, and device orientation were
not independently exercised as literal browser interactions this Wave —
see `docs/FROZEN-MODULE-NO-SCROLL-REMEDIATION.md`'s closing section for
exactly what was and wasn't tested.

## PORTAL-NEXT-07.6.1 addendum

Not a design/remediation Wave — two reconciliation actions only, no
visual or business change.

**Dashbi status reconciled**: PORTAL-NEXT-07.5.2 (commit `cc3a296`) had
reported 26/26 goldens, 0 business diff, Ranking = Vendedores + Lojas,
Model Analysis unchanged, no-horizontal-scroll PASS. The human then
explicitly responded "Aprovado." — a fact this session's own record
never captured, so it stayed `UAT_PENDING` through PORTAL-NEXT-07.6
(which correctly flagged the staleness rather than silently trusting its
own brief's assumption that Dashbi was already approved). Corrected now:
Dashbi is `HUMAN_APPROVED / FROZEN` for both business and responsive —
this is a reconciliation of an already-issued approval, not a new one;
`dashbi.js`/`dashbi.css`/`dashbi.adapter.js` were not touched (re-hashed,
0 diff) and PORTAL-NEXT-07.6.1 did not re-review Dashbi's business
logic. See `config/module-registry.json`'s own `humanApprovalNote` on
the `dashbi` entry for the full record.

**Score explicitly NOT promoted**: no equivalent approval record exists
for Score. It stays `UAT_PENDING` for both business and responsive — its
own Design System score-band conflict (`docs/SCORE-ENGINE-AUDIT.md`)
remains unresolved and was not touched this Wave. Successful responsive
testing (below) does not change Score's business status — that boundary
was explicit in this Wave's own brief and is respected here.

**Literal responsive/accessibility tests executed** (previously
disclosed as code-audit-only in PORTAL-NEXT-07.6): 200% zoom, portrait/
landscape orientation, continuous resize sweep, and live keyboard/focus
interaction — for Landing, Score, Coparticipado, and Gestão. Full
results, method, and evidence in
`docs/FROZEN-MODULE-NO-SCROLL-REMEDIATION.md`'s updated test-evidence
section (each entry now labeled CODE AUDIT / AUTOMATED TEST / REAL
BROWSER TEST, so the two categories are never conflated again) and
`docs/RESPONSIVE-TEST-EVIDENCE-07-6-1.md`.

**0 business/visual change**: no test failure was found requiring a
fix, so no presentation code was touched this Wave. Score/Coparticipado/
Gestão/Dashbi golden suites re-run fresh and unchanged. Responsive
status for Landing/Score/Coparticipado/Gestão remains `UAT_PENDING` —
technical testing passing does not substitute for human visual approval
(Gate 19 of this Wave's own brief).

## PORTAL-NEXT-07.6.2 addendum

Human visual UAT rejected PORTAL-NEXT-07.6's responsive solution for
Score and Dashbi: not horizontal scroll, but readability — desktop
tables compressed into narrow widths until headers/values wrapped
badly ("FINANCIAMENTOS breaking almost character-by-character", Share/
Produção Total/Receita Total breaking vertically, currency values
splitting across many lines). Landing/Coparticipado/Gestão were not
targets and were not touched.

**Root cause actually found, not just patched**: the previous <=480px
stacking CSS used a generic flex-wrap of every `data-th` cell, packing
however many fit per row — inherently non-deterministic under real
content lengths. Worse, reproducing the exact human-reported symptom
(character-by-character collapse) traced to a genuine bug:
`.dbTableExpandable{table-layout:fixed}` (set since PORTAL-NEXT-07.4)
stayed active on Dashbi's `<table>` even with primary rows flexed —
with a `+ Detalhes` row open (a colspan'd `<tr>` the fixed layout still
accounts for), the fixed column-width algorithm squeezed every primary
cell to a few px, reproduced directly (identity/currency cells
collapsed to ~17px, paired metrics to ~7.5px) and fixed with
`table-layout:auto` inside the media query — the exact same class of
fix PORTAL-NEXT-07.6 had already needed for Coparticipado's
`<colgroup>`, not applied to Dashbi's own stacking block at the time
because the interaction wasn't tested with a detail row open at narrow
width until this Wave.

**Redesigned as an explicit, deterministic record** (not generic
flex-wrap): every field defaults to the full row width, one per line;
only Vendas+Financiamentos (Dashbi) — both always a short integer,
never a currency/percentage string — share a row, per explicit human
spec. Score: identity (Vendedor) gets full-width bold emphasis, Score
gets its own bordered/emphasized block with the approved score bar
intact, every other field (#, Loja, Depto, Financ.) gets its own
full-width row. No new bands/colors/thresholds/score semantics
introduced (Gate 5) — the score-band Design System conflict remains
unresolved, untouched.

**Verified, not assumed**: re-tested the exact failure condition (long
name + `+ Detalhes` open + 320-430px) that reproduced the bug pre-fix —
clean after. 0 overflowing components and 0 narrow-cell readability
findings at 320/360/390/430/768/1366/1920 for both Score and Dashbi
(one pre-existing, out-of-scope, non-material finding noted: the
dev-only `.dbFixtureBar` diagnostic bar overflows by 2px at 320px only,
0 document-level scroll, not touched — it existed before this Wave and
isn't part of the approved user-facing experience). Score 12/12,
Dashbi 26/26, Coparticipado 22/22, Gestão 30/30, Landing 20/20 — all
unchanged. `dashbi.js`/`dashbi.adapter.js`/`score.adapter.js` byte-
identical (0 diff) — only `dashbi.css`/`score.css` changed, 0 JS
touched. Keyboard/focus re-verified on the new stacked markup (real
browser test): `+ Detalhes`/row-click both remain keyboard-reachable
with visible focus.

**Status unchanged by this Wave**: Score stays `BUSINESS UAT_PENDING /
RESPONSIVE UAT_PENDING` — successful readability work doesn't promote
business status, the score-band conflict is untouched. Dashbi stays
`BUSINESS HUMAN_APPROVED/FROZEN` — only its narrow-width presentation
was reopened, its business logic was never touched (byte-identical);
`RESPONSIVE` reverts to `UAT_PENDING` for Dashbi specifically (the
07.6.1 reconciliation covered Dashbi's *already-validated* zero-scroll
state — this Wave found and fixed a real readability defect in that
same surface, so a fresh human visual pass is warranted before
re-closing it).

## PORTAL-NEXT-07.6.3 addendum

Human visual UAT rejected PORTAL-NEXT-07.6.2 a second time with the
same symptoms the 07.6.2 fix targeted, via screenshots taken after
commit `b4fe4f6`. Before touching code again, verified what was
actually being served: found **14 zombie `python -m http.server 8700`
processes** accumulated across this multi-day session (7 of them
simultaneously LISTENING on the same port — Windows honors
`http.server`'s `allow_reuse_address=True` for concurrent binds), all
killed, replaced with exactly one clean instance, served-file hashes
confirmed byte-identical to the working tree. No `Cache-Control` header
is ever sent by this server — the likely actual explanation, and the
same root cause already confirmed once before in this engagement
(PORTAL-NEXT-07.3.1): a normal browser reload can serve stale CSS from
before a fix landed, where a genuine hard refresh would not. Full
writeup: `docs/RESPONSIVE-STALE-SERVE-INVESTIGATION-07-6-3.md`.

**0 code change this Wave** — re-verified the already-committed
PORTAL-NEXT-07.6.2 implementation against the real served routes (not
fixture HTML, not only scrollWidth): computed-style proof that no
legacy table geometry constrains the narrow-width records
(`table-layout:auto`/`display:block`, full-width flex-basis, no
min/max-width floor), plus an exhaustive sweep — all 12 Score fixtures
× 5 viewports, all 3 Dashbi views × 5 viewports × closed/detail-open
states, Ranking and Novos por Loja at narrow width with detail open —
0 problems found anywhere. Score 12/12, Dashbi 26/26, Coparticipado
22/22, Gestão 30/30, Landing 20/20 all unchanged; working tree clean
(no file diff, so no new commit — the environmental fix isn't a
git-tracked change). Isolation baseline
(`.baseline-portalnext0763-after.txt`) 0-line diff;
`origin/main` SHA unchanged.

Score/Dashbi RESPONSIVE status remains `UAT_PENDING` pending a fresh
human visual pass against the now-clean, single-server environment
with a genuine hard refresh.

## PORTAL-NEXT-07.6.4 addendum

**Human UAT history, recorded honestly, not rewritten as PASS**:

```
PORTAL-NEXT-07.6.2:  TECHNICALLY GREEN — HUMAN RESPONSIVE UAT REJECTED
                     (compressed/unreadable narrow-width tables)
PORTAL-NEXT-07.6.3:  TECHNICALLY GREEN — HUMAN RESPONSIVE UAT REJECTED
                     AGAIN, after the human performed the requested
                     clean-server/hard-refresh/incognito validation —
                     ruling out cache as the explanation
PORTAL-NEXT-07.6.4:  strategy changed (this addendum)
```

**Strategy change**: after two rejections of "transform the desktop
`<table>` into a mobile layout via CSS" (07.6, 07.6.2) — the second
proven correct by every computed-style/DOM check available, and still
rejected — this Wave stopped trying to prove that approach should work
and replaced it instead. Score and every Dashbi table sharing the
`expandableRow`/`expandableTableHtml` component (store, seller,
Ranking, Novos por Loja — all showed the identical underlying pattern,
so the fix was extended to all of them, matching Gate 3D's explicit
allowance) now render through **two independent, non-table renderers**
fed by the same already-computed row data:

- `renderDesktopTable()`/`.dbDesktopOnly` — the pre-existing, unchanged
  `<table>`, visible at 768px+.
- `renderMobileCards()`/`dbMobileCard()`/`.dbMobileOnly` — new plain
  `<div>`-based cards (no `table`/`thead`/`tr`/`td`/`th`/`colgroup`
  anywhere in this markup), visible at <=767px.

Exactly one is `display:block`, the other `display:none` — never both
occupying layout at once. Proven by computed style, not assumed: at
390px, `.scTable` computes to `display:block` at all (Score's own
`<table>` stops being a table at that breakpoint since its wrapper is
hidden and only the sibling card list renders); Dashbi's desktop table
wrap computes `display:none`, its card list `display:block`, 0 visible
`<table>` elements, >0 visible cards — measured directly via
`getComputedStyle`/`offsetParent`, not inferred.

**0 business duplication**: the mobile renderer receives the exact same
`v`/`f`/`share`/`r` objects the desktop renderer already computed in
the same function call — verified by direct comparison (a representative
desktop row's cell text vs. the matching mobile card's field values,
identical for every field, both derived from one shared object, not
recalculated).

**Detail toggle state, shared correctly**: both renderers' `+ Detalhes`
button reference the same `ns`/`key` toggle state (so opening one and
resizing keeps it open in the other), but each gets its own DOM id
(`idSuffix` parameter added to `detailDomId()`/`detailToggleHtml()`/
`kpiDetailPanelHtml()`, optional and omitted by every pre-existing call
site — Model Analysis's own usage is byte-identical to before) so the
two renderers' detail panels never collide as duplicate ids while both
exist in the DOM.

**A real bug found and fixed during this Wave's own verification, not
assumed safe**: the Score mobile card's score-bar row used `width:100%`
on the meter track without releasing the base rule's `flex-shrink:0`,
which overflowed by up to 52px with the `large_values` fixture at
320px (a wide 4-digit score number pushed the non-shrinking bar past
the container) — caught by the exhaustive fixture sweep, not by the
single fixture used for screenshots, fixed with `flex:1 1 0;
min-width:0`.

**0 business-logic change**: `dashbi.adapter.js`/`score.adapter.js`
byte-identical (0 diff); Score 12/12, Dashbi 26/26 (Ranking =
Vendedores + Lojas, Departamentos absent, Model Analysis's 07.5.1
removed sections still absent, Entrada Qtd still absent — all
re-verified), Coparticipado 22/22, Gestão 30/30, Landing 20/20 all
unchanged. Isolation baseline 0-line diff; `origin/main` SHA unchanged.

**Score/Dashbi status unchanged by this Wave**: Score stays `UAT_PENDING`
(business and responsive) — no promotion, score-band conflict
untouched. Dashbi business stays `HUMAN_APPROVED/FROZEN` (unaffected —
only presentation reopened); responsive stays `UAT_PENDING` pending a
fresh human visual pass on this specific, structurally different
mobile-card presentation.

## PORTAL-NEXT-07.7B addendum

Implements the human-approved Score Band model discovered/recommended
in PORTAL-NEXT-07.7A (that investigation document is preserved as-is,
not rewritten — this addendum records that its Option 1 was
subsequently selected). Full contract: `docs/SCORE-BAND-NORMATIVE-
07-7B.md`.

**Design System conflict resolved**: `design-system-2.1/references/
score.md`'s old ALTO/BOM/BAIXO requirement (never numerically defined
normatively — the only concrete thresholds ever existed in the
facelift prototype's own throwaway mock data, on an incompatible
~0-100 scale) is superseded by the new 5-band CRÍTICO/DESENVOLVIMENTO/
PERFORMANCE/ALTA PERFORMANCE/ELITE model, absolute thresholds 0-299/
300-549/550-749/750-899/900-1000 on the real 0-1000 engine scale.

**Architecture**: one authoritative classifier
(`classifyScoreBand()`, `assets/js/score.js`), consumed identically by
both the desktop table and the mobile card (PORTAL-NEXT-07.6.4's
dual-renderer, untouched architecturally) — 0 duplicated threshold
logic. Operates purely on the already-computed final Score; the
underlying engine (`score.adapter.js`) has 0 diff, hash-verified
unchanged. Invalid/non-finite Score (the NaN defect documented in
07.7A) returns no band at all — verified against the real fixture that
actually produces it, not just a synthetic NaN literal.

**Colors**: reuses existing semantic tokens (critical/warning/
success), with PERFORMANCE deliberately left neutral and ELITE
distinguished from ALTA PERFORMANCE by weight/border rather than a new
hue — no arbitrary rainbow invented, 4 tokens honestly don't map 1:1
to 5 bands and that gap is documented, not hidden.

**0 business-logic change to the Score engine itself**: 12/12 golden
fixtures unchanged. New `tests/score-band-test.py` (24/24): all 10
required boundary values, 6 invalid-input cases (NaN/Infinity/
-Infinity/null/undefined/negative), 7 representative real fixture
scores, and the real NaN-producing fixture. No-horizontal-scroll
re-verified at all 7 viewports; long band labels (ALTA PERFORMANCE,
DESENVOLVIMENTO) confirmed wrapping by word only, even at 320px.
Desktop fidelity preserved — the band is additive inside the existing
Score cell, 0 new table column, 0 row-count change. Other modules
(Landing/Coparticipado/Gestão/Dashbi): 0 diff.

**Status**: Score Business/Functional stays `UAT_PENDING`. Score
Responsive is set to `HUMAN_APPROVED/FROZEN` this Wave (per this
brief's own explicit Gate 34 instruction — not a claim that a separate
prior approval message existed). Score Band Business Rule (the
threshold numbers themselves) is `HUMAN_APPROVED`. Score Band Visual
(this concrete implementation) stays `UAT_PENDING` pending a human
look — the module as a whole is not marked frozen.

## PORTAL-NEXT-07.7C addendum

The human confirmed PORTAL-NEXT-07.7B's visual UAT (Score Band Business
Rule, Score Band Visual, and Score Responsive all promoted to
`HUMAN_APPROVED/FROZEN` by the brief's own explicit statement — the
same "brief-as-approval-channel" pattern as PORTAL-NEXT-07.6.1's
"Aprovado." and PORTAL-NEXT-07.7B's own Gate 34). This Wave then fixed
the pre-existing `receitaSPF`-driven `NaN` Score defect that
PORTAL-NEXT-07.7A discovered and PORTAL-NEXT-07.7B intentionally left
untouched.

**Root cause**: `calcScores()`'s `o.retorno += f.retorno +
f.receitaSPF` has no fallback for a missing `receitaSPF`, unlike the
adjacent `spfQtd += f.spfQtd || 0`. Traced conclusively (not assumed)
to production's own `processFins()` (read from a locally-saved
`origin/main` copy, `PORTAL-NEXT-04/.source/score-origin-main.html` —
zero live production connection) building `receitaSPF` via
`.reduce((s,r)=>...,0)` — a numeric-seeded reduce that can never itself
produce `undefined`, meaning real production data can never trigger
this path. Missing `receitaSPF` at the adapter boundary is therefore
conclusively a "no SPF revenue" (zero) case, not an "unknown" one.

**Fix**: a normalization boundary in `assets/js/adapters/
score.adapter.js`, using production's own byte-identical `asNumber()`
parser, applied to `fins[].receitaSPF` **before** the still-untouched
`calcScores()` is called — `calcScores()`'s own extracted lines remain
byte-for-byte unmodified (verified via `git diff`), preserving the
"no cleanup drift" rule established for this file. Full missing-value
matrix (13 cases, including `0` correctly preserved, not miscoerced)
verified live via the adapter's own exported `normalizeFinInput()`.

**Regression**: `tests/score-parity-test.py`: 11/12 exact byte-match
against the untouched production reference — the 1 intentional
divergence (`missing_optional_data`) is the fix itself (that fixture
now returns a real, finite score where the unmodified reference still
returns `NaN`, by design — see `docs/SCORE-RECEITA-SPF-NONFINITE-
07-7C.md`). `tests/score-band-test.py`: 24/24 (one assertion updated to
reflect the fixture's corrected, finite result — the classifier's own
invalid-input contract is unchanged and separately covered). New
`tests/score-spf-defect-test.py`: 16/16 (live before/after proof + the
full missing-value matrix + a dedicated Gate-13 zero-preservation
check). Other modules (Landing/Coparticipado/Gestão/Dashbi): 0 diff.
Score formula weights/thresholds: unchanged.

**Status**: Score Band Business Rule, Score Band Visual, and Score
Responsive: all `HUMAN_APPROVED/FROZEN`. Score Business/Functional
remains `UAT_PENDING` as its own separate, older status (open since
PORTAL-NEXT-04, unrelated to Band/Responsive/this defect) — marked
**eligible for final closure** per this Wave's own Gate 34 wording, but
not self-promoted to `HUMAN_APPROVED` here; that remains a human
decision.

## Standing blockers carried forward (not resolved this phase)

- Gestão: commission-rule discrepancy (`PORTAL-NEXT-01.1/BLOCKER-
  CLASSIFICATION.md` Blocker #6) — RESOLVED for its actual (surface-
  scoped) extent as of PORTAL-NEXT-06.1: `docs/GESTAO-COMMISSION-
  DECISION.md`, STATUS: HUMAN DECIDED (70% fixed, non-configurable,
  scoped to "Comissão Líquida SPF EXTRA" only). The broader Blocker #6
  framing (a possible discrepancy reaching Salários/Comissões'
  `commissionCalc()`) is NOT closed — only Gestão's own surface is.
- Salários/Comissões: same underlying `commissionCalc()` engine (Rule
  B from `docs/COMMISSION-RULE-MAP.md`) — not investigated beyond
  confirming it exists and is unaffected by the Gestão decision above
  (explicitly not generalized to it); module itself remains untouched.
- Simulador Novos / Seminovos: DOM-coupled loan-math extraction
  (Blocker #5) — the extraction sub-project itself was executed in
  PORTAL-NEXT-08 (engines extracted + parity-verified, see that Wave's
  addendum below and `docs/SIMULATOR-ENGINE-DISCOVERY-08.md`). Blocker
  #5 is therefore satisfied for its own stated scope ("a dedicated
  extraction sub-project... verifies cent-accurate output equivalence,
  which has not been attempted yet" — now attempted and green). UI
  migration itself is explicitly NOT done — `migrationStatus` for both
  modules stays `NOT_MIGRATED`.
- Brabus Intelligence: Voice Orb variant still PROVISIONAL/HUMAN
  SELECTION PENDING; a separately-tracked V1 issue (the AI kill-switch)
  — appears resolved in production since PORTAL-NEXT-01.1 (see
  PORTAL-NEXT-02's REPORT.md entry), not independently re-verified.
  Not touched this Wave (Gate 33).
- Score: band (ALTO/BOM/BAIXO) Design System conflict — see addendum
  above. isScoreSellerEligible() and openSellerDetails() intentionally
  not migrated — see `docs/SCORE-EXTRACTION-TRACE.md`.
