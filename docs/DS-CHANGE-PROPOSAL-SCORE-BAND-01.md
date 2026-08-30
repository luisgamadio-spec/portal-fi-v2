# Design System Change Proposal — SCORE-BAND-01

```
STATUS:                   HUMAN REVIEW REQUIRED
RULE:                        design-system-2.1/references/score.md,
                            "MUST": Score value, band (ALTO/BOM/BAIXO),
                            confidence, component breakdown (meters,
                            not gamified), explanation.
CURRENT AUTHORITY:              design-system-2.1/references/score.md
                            (status APPROVED), approved in
                            DESIGN-SYSTEM-LAB-01.
```

## Conflict

The normative rule requires a discrete **band** classification
(ALTO/BOM/BAIXO). Real production `calcScores()` (`origin/main:
modules/score.html`, proved == live production, PORTAL-NEXT-03.1) has
**no band concept anywhere** — it computes a continuous 0-1000 point
total with no threshold-based categorical classification. This was
confirmed by reading the actual function body (`docs/SCORE-ENGINE-
AUDIT.md`), not inferred from any UI.

**Separately**, this Lab's own earlier work (DESIGN-SYSTEM-LAB-01 →
`design-system-2/components.js` → `facelift-prototype-01` →
`design-system-2.1`'s own frozen `module-landing-approved` reference)
DID build a band-aware visual component for Score — a linear meter
(`.rankScoreBar`/`.fill`) whose fill color is derived from `faixa`
(ALTO→success, BOM→info, BAIXO→critical). That component's own demo
data (`window.DS_DATA.sellers`) invented a `faixa` field for its
fictional sellers — it was never validated against real production
data, because at the time no one had read `calcScores()` from the real
authoritative source.

## Why this wasn't invented away

This phase's own governing principle: **"VISUALIZATION MAY REPRESENT
BUSINESS TRUTH. VISUALIZATION MUST NOT CREATE NEW BUSINESS TRUTH."**
Assigning a threshold (e.g. "score > 700 = ALTO") to satisfy the
normative rule would be inventing a business classification that does
not exist in production — indistinguishable, from the business's
perspective, from silently changing what Score means.

## Proposal

Amend `design-system-2.1/references/score.md` to recognize **two**
normative variants, selected by whether the underlying business logic
actually has a band:

```
VARIANT A — Score with Business Band
  Used when the functional source genuinely computes a band.
  MUST show: score, band, confidence, breakdown (meters), explanation.

VARIANT B — Continuous Score  (NEW)
  Used when the functional source has no band (Score's real case,
  today).
  MUST show: numeric score, linear meter (proportional to the real
  scale, single non-band-derived color), confidence when the business
  logic has one, breakdown (meters, not gamified), explanation.
  MUST NOT invent a categorical band, threshold, or color-coded
  quality tier not present in the functional source.
```

## What this Wave actually did, pending the decision above

`assets/js/score.js`/`assets/css/score.css` implement **Variant B** as
described — this is a live preview of what the amendment would
formalize, not a unilateral edit to `design-system-2.1/` itself (that
file was **not** touched — see the isolation section of `REPORT.md`'s
PORTAL-NEXT-04.1 entry). The linear meter's STRUCTURE (80×4px track,
3px radius, single fill) is transplanted verbatim from the frozen,
Human Approved `module-landing-approved` reference. The ONE adaptation
is the fill color: `--color-accent-primary` (single, consistent),
**not** the reference's own `faixa`-derived success/info/critical
scheme, since production has no `faixa`.

## Impact if approved

- `score.md` gains a documented escape hatch for continuous (non-band)
  scoring surfaces — relevant beyond just this module if any future
  module has the same "normative pattern assumes more structure than
  the real business logic has" shape.
- No other Approved Reference or component is affected.

## Human decision required

Approve Variant B as written / amend it / reject it (and if rejected,
Score's meter would need to become band-based some other way, which
this phase declines to invent). **PENDING.**
