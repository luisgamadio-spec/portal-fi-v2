# Score Band — Normative Contract (PORTAL-NEXT-07.7B)

**Status: HUMAN-APPROVED business rule.** Resolves the Design System
score-band conflict documented in `design-system-2.1/references/
score.md` and investigated in `docs/SCORE-BAND-DISCOVERY-07-7A.md`
(preserved as-is — this document does not rewrite that investigation;
it records that its recommended Option 1 was subsequently selected by
explicit human product decision).

## The contract

```
Score:        numeric, 0-1000 (unchanged — assets/js/adapters/
              score.adapter.js's calcScores(), 0 diff this Wave)
Score Band:   an ABSOLUTE classification of the final valid Score.
              Fixed thresholds. Independent of seller population,
              period, department, store, ranking position, or sample
              distribution — a Score of 900 is ELITE regardless of who
              else is being ranked alongside it.

CRÍTICO             0–299
DESENVOLVIMENTO     300–549
PERFORMANCE         550–749
ALTA PERFORMANCE    750–899
ELITE               900–1000
```

Implemented as the single authoritative classifier
`classifyScoreBand(score)` in `assets/js/score.js` (Gate 2 — exactly
one classifier; both the desktop table and mobile card renderers call
it, no threshold logic duplicated anywhere else). Exposed read-only as
`window.NX_SCORE_PAGE.classifyScoreBand` for deterministic testing
(`tests/score-band-test.py`).

## Pipeline (architectural boundary, not to be blurred)

```
existing Score engine (calcScores, unchanged)
        ↓
final numeric Score, 0-1000
        ↓
absolute Score Band classifier (NEW, presentation layer, score.js)
        ↓
executive presentation (desktop table + mobile card)
```

**Important, carried forward from the 07.7A investigation**: the Score
engine's own largest single component (Volume, 250-300/1000 weight) is
normalized against the current computation's own top performer
(`maxVenda`) — a real population-relative element inside an otherwise
mostly-absolute formula. This Wave did **not** change that formula (0
diff to `score.adapter.js`, verified by hash). The Band classifier
itself operates purely on the already-computed final number and is
100% absolute by construction — but a given seller's underlying Score
(and therefore their Band) can still shift between periods purely from
other sellers' Volume changing, exactly as documented in 07.7A's Gate
3. This is a property of the existing engine, not the new Band layer.

## Business semantics

```
CRÍTICO           Performance materially below expected operating level.
DESENVOLVIMENTO   Performance exists, but important dimensions remain
                  below the desired operating level.
PERFORMANCE       Healthy/expected operating performance.
ALTA PERFORMANCE  Consistently above expected operating performance.
ELITE             Exceptional performance at the highest intended
                  Score range.
```

## Known, disclosed limitations (not fixed this Wave, by design)

- **No tenure/newness signal.** `calcScores()` has no way to
  distinguish a brand-new seller with 1-2 transactions from a genuine
  underperformer — both can land in CRÍTICO. Documented in
  `docs/SCORE-BAND-DISCOVERY-07-7A.md` Gate 18; not addressed here, as
  fixing it would require a separate business decision (e.g., a tenure
  exemption) outside this Wave's scope.
- **NaN defect, registered, not fixed.** A financing record missing
  `receitaSPF` produces `calcScores()`'s `score = NaN` (root cause:
  `o.retorno += f.retorno + f.receitaSPF` has no `|| 0` fallback,
  unlike the adjacent `spfQtd` accumulator which does — see 07.7A Gate
  19). The Band classifier's own invalid-input contract (below) keeps
  this from silently becoming a false performance judgment, but the
  underlying NaN production itself remains a live, disclosed defect —
  **not fixed as part of 07.7B**, per this Wave's explicit instruction
  not to bundle a business/functional correction into the Band Wave.

## Invalid Score contract

`classifyScoreBand(score)` returns `null` — never a band object — for
any `score` that is not a finite JavaScript number: `NaN`, `Infinity`,
`-Infinity`, `null`, `undefined`, or negative (the engine's own clamp
already prevents negative scores in practice; guarded defensively
anyway). `null` never renders any band text or color — the row simply
shows no band, not an invented "unclassified" 6th category. Verified
by `tests/score-band-test.py`, including the REAL `missing_optional_
data` fixture that actually produces `NaN` through the live engine (not
a synthetic `NaN` literal only).

## Visual treatment

- **Hierarchy** (both desktop and mobile): numeric Score first, Band
  label second, the already-approved visual score bar third — matching
  `docs/SCORE-BAND-DISCOVERY-07-7A.md` Gate 6/21's validated mockup.
- **Bar**: unchanged. Still a single `--color-accent-primary` fill, no
  quality-coded color, no 5-segment redesign (Gate 13) — the Band is an
  additive interpretation layer above the bar, not a recoloring of it.
- **Colors**: reuses existing Design System semantic tokens
  (`design-system-2/tokens.css`) rather than inventing new hues (Gate
  12). Only 4 status tokens exist for 5 bands, so a naive 1:1 mapping
  doesn't work cleanly:
  ```
  CRÍTICO            --color-critical
  DESENVOLVIMENTO    --color-warning
  PERFORMANCE        --color-text-secondary (deliberately neutral —
                     the "meets expectations" baseline band doesn't
                    need emphasis in either direction)
  ALTA PERFORMANCE   --color-success
  ELITE              --color-success, reused — distinguished from ALTA
                     PERFORMANCE by weight + a subtle border, not a
                    new hue (the same "position/weight, not just
                   color" principle already used for Dashbi's Share/
                  Receita Total emphasis, PORTAL-NEXT-07.5)
  ```
- **Not color-only** (Gate 14): the textual label is authoritative and
  always rendered; color is a supplementary emphasis, never the sole
  signal.
- **No legend/tooltip added this Wave.** Gate 16 framed a compact
  legend as optional ("if an appropriate location exists... MAY be
  added"), not mandatory. Considered and deliberately not built: the
  five band labels are self-explanatory Portuguese words even without
  an attached numeric legend, and no existing tooltip/help affordance
  exists on this page to hook into without building new UI — the more
  conservative, restrained choice given Gate 11/16's explicit caution
  against clutter and against inventing new instructional UI beyond
  what's necessary.

## Verification

```
tests/score-parity-test.py:          PASS — 12/12 (0 numeric diff)
tests/score-band-test.py (new):          PASS — 24/24 (10 boundary +
                                         6 invalid-input + 7 representative
                                        real-fixture + 1 real-NaN-fixture
                                       case)
No-horizontal-scroll (320-1920):              PASS, all 7 viewports
Long labels (ALTA PERFORMANCE,
DESENVOLVIMENTO) at 320px:                        wrap by word if needed,
                                                  0 character-stacking
                                                 (verified, not assumed)
Keyboard + visible focus (mobile card):               PASS
Desktop fidelity (1366/1920):                              PASS — band is
                                                            additive inside
                                                           the existing
                                                          Score cell, 0
                                                         new column, 0
                                                        row-count change
score.adapter.js hash:                                          unchanged
Other modules (Landing/Coparticipado/
Gestão/Dashbi) diff:                                                0
```

## Status (Gate 34)

```
Score Business/Functional:    UAT_PENDING            (unchanged)
Score Responsive:                 HUMAN_APPROVED / FROZEN   (granted
                                  this Wave, via this brief's own
                                 explicit Gate 34 instruction — not a
                                claim that an earlier, separate
                               approval message existed)
Score Band Business Rule:            HUMAN_APPROVED           (this
                                     document — the threshold model
                                    itself, Option 1)
Score Band Visual:                       UAT_PENDING              (the
                                         concrete implementation above
                                        awaits a human look before
                                       being called done)
```

The Score module as a whole is **not** marked frozen — only the
responsive presentation (07.6.4's dual-renderer) and the Band's
business-rule numbers are approved; the Band's visual execution and
the module's overall business/functional status remain open.
