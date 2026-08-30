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
| Landing | **UAT_PENDING** (PORTAL-NEXT-03 — see `docs/HUMAN-UAT-LANDING.md`) | 1 |
| Portal Shell / MASTER Admin | NOT_MIGRATED | 0 |
| Score | NOT_MIGRATED | 2 |
| Coparticipado | NOT_MIGRATED | 3 |
| Gestão | NOT_MIGRATED | 4 |
| Dashbi | NOT_MIGRATED | 5 |
| Simulador Novos | NOT_MIGRATED | 6 |
| Simulador Seminovos | NOT_MIGRATED | 6 |
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
canvas, still reachable via the router).

## Standing blockers carried forward (not resolved this phase)

- Gestão / Salários-Comissões: commission-rule discrepancy
  (`PORTAL-NEXT-01.1/BLOCKER-CLASSIFICATION.md` Blocker #6) — RC
  BLOCKER, must close before either can claim functional parity.
- Simulador Novos / Seminovos: DOM-coupled loan-math extraction
  (Blocker #5) — RC BLOCKER, Wave 6 must start with the extraction
  sub-project before any UI work.
- Brabus Intelligence: Voice Orb variant still PROVISIONAL/HUMAN
  SELECTION PENDING; a separately-tracked V1 issue (the AI kill-switch)
  — see `REPORT.md`'s PORTAL-NEXT-02 entry for this phase's discovery
  that it appears to have been resolved in production since PORTAL-
  NEXT-01.1, not independently re-verified this phase.
