# Score Band — Mathematical & Business Discovery (PORTAL-NEXT-07.7A)

**STATUS: INVESTIGATION / RECOMMENDATION ONLY. NO THRESHOLD IS
HUMAN_APPROVED. NOTHING IN THIS DOCUMENT WAS IMPLEMENTED.** 0 lines of
HTML/CSS/JS/business logic changed this Wave — see the Gate 23 guard
results at the end.

## Gate 1 — Score engine location

```
FILE:      assets/js/adapters/score.adapter.js
FUNCTION:  calcScores(sales, fins)                          line 34
WEIGHTS:   SCORE_WEIGHTS (const)                             line 30
UNIVERSE:  MIX_PLANOS_UNIVERSO (const, 4 plan types)             line 31
ELIGIBILITY: isScoreSellerEligible(r) { return true; }               line 27
             (currently a no-op — every seller who appears in sales
             or fins is included, no filter is actually active)
```

Traced directly from source, not inferred.

## Gate 2 — Formula reconstruction

Per seller (grouped by `vendedor|loja|dept`), for department `dept`
(`Novos` or `Seminovos`), with weights `w = SCORE_WEIGHTS[dept]`:

```
Score = w.volume    × min(1, vendas / maxVenda[dept])
      + w.share      × min(1, share / 0.60) × confVendas
      + w.familias     × min(1, familias.size / 3)                [Novos only]
      + w.planos         × min(1, planosValidos.size / 4)            [Novos only]
      + w.spf              × min(1, spfRate) × confFin
      + w.retorno            × min(1, retorno / 0.08) × confFin

  share      = fin / vendas
  spfRate    = spfQtd / fin
  retorno    = (Σ retorno + Σ receitaSPF) / Σ valorFinanciado
  confVendas = min(1, vendas / 4)     — sample-size dampening
  confFin    = min(1, fin / 2)        — sample-size dampening
  maxVenda[dept] = max(1, highest `vendas` count among all sellers
                    of that dept IN THIS SAME COMPUTATION RUN)

  Score = round(max(0, min(1000, Score)))
```

Weights (from source, verified to sum to exactly 1000 in both depts):

```
NOVOS:      volume=250  share=230  familias=130  planos=130  spf=100  retorno=160   (Σ=1000)
SEMINOVOS:  volume=300  share=270                              spf=150  retorno=280   (Σ=1000)
```

Per-component reconstruction:

| Component | Business meaning | Source data | Contribution | Min | Max | Bounded |
|---|---|---|---|---|---|---|
| Volume de vendas | Sales activity relative to the TOP performer in this run | `sales` count | `w.volume × min(1, vendas/maxVenda)` | 0 | `w.volume` | YES, but **population-relative** (see Gate 3) |
| Penetração de financiamento | Share of sales converted to financing | `fin/vendas` | `w.share × min(1, share/0.6) × confVendas` | 0 | `w.share` | YES, absolute threshold 60% |
| Mix de famílias (Novos) | Breadth of vehicle families sold | distinct `familia` in sales | `w.familias × min(1, families/3)` | 0 | `w.familias` | YES, absolute threshold 3 |
| Mix de planos (Novos) | Breadth of financing plan types used | distinct `plano` in fins ∩ {LINEAR,BALÃO,COPARTICIPADO,SUBSIDIADO} | `w.planos × min(1, plans/4)` | 0 | `w.planos` | YES, absolute threshold 4 |
| SPF EXTRA | Attach rate of SPF Extra product | `spfQtd/fin` | `w.spf × min(1, rate) × confFin` | 0 | `w.spf` | YES, absolute threshold 100% |
| Retorno médio | Return (retorno+receitaSPF) as % of production | `(Σretorno+ΣreceitaSPF)/Σprodução` | `w.retorno × min(1, ret/0.08) × confFin` | 0 | `w.retorno` | YES, absolute threshold 8% |

## Gate 3 — Theoretical range

**Bounded: YES**, exactly **[0, 1000]** — not by the outer
`Math.max(0, Math.min(1000, score))` clamp (which is mathematically
redundant, since no component can individually exceed its own weight
and weights sum to exactly 1000 in both departments) but by
construction of the formula itself.

**Critical nuance, not to be glossed over**: the "Volume de vendas"
component — the single largest weight in both departments (250/1000
Novos, 300/1000 Seminovos) — is normalized against `maxVenda[dept]`,
which is **derived from the same population being scored in that
specific `calcScores()` call**, not a fixed absolute sales target. By
construction, the seller(s) with the most `vendas` in any given
computation always receive full volume credit, regardless of their
absolute count. This means:

- The formula is **not purely absolute**. A seller's score can shift
  even if their own numbers never change, if the composition of the
  scored population changes (e.g., the prior top performer leaves the
  dataset, or a new even-higher performer is added).
- Every other component (5 of 6) uses a genuine fixed absolute business
  threshold embedded in the source (60% share, 3 families, 4 plan
  types, 100% SPF rate, 8% retorno).
- A true 1000 requires simultaneously: being at/above the population's
  own max `vendas`, `vendas>=4` (for full `confVendas`), `fin>=2` (for
  full `confFin`), `share>=60%`, (Novos) 3+ distinct families and all 4
  plan types used, 100% SPF attach rate, and `retorno>=8%`. Observed
  directly in the fixture sample (Gate 4): two sellers reach exactly
  1000.

## Gate 4 — Practical (observed) range

Computed by executing the real `window.NX_SCORE_ADAPTER.compute()` —
not reconstructed by hand — across all 12 approved golden fixtures (23
seller-score entries total).

**One entry produced `score = NaN`** (see Gate 19) — excluded from the
statistics below and reported separately, not silently dropped.

```
n (valid) = 22
min    = 71
max    = 1000
mean   = 551.7
median = 533.0
stdev  = 291.9  (population stdev)

P10 = 121.0    P50 = 533.0
P20 = 341.0    P60 = 610.0
P25 = 362.8    P75 = 795.2
P40 = 416.0    P80 = 874.2
               P90 = 966.7
               P95 = 998.4
```

All 22 sorted values: `71, 106, 106, 256, 337, 357, 380, 380, 380, 470,
513, 553, 583, 628, 628, 772, 803, 892, 955, 968, 1000, 1000`

**Sample size is small (n=22) and NOT statistically representative of
the real Brabus seller population** — stated explicitly per Gate 4's
own instruction, not glossed over. See Gate 6.

## Gate 5 — Distribution

Buckets sized to the actual observed range (not a preset 0-200 grid):

```
0–99:      1 seller   ( 4.5%)   — AAA BAIXO PERF (vendas=1, fin=0)
100–199:   2 sellers  ( 9.1%)   — both fin=0, low vendas
200–299:   1 seller   ( 4.5%)
300–399:   4 sellers  (18.2%)   — cluster: all fin=0, "sells but never
                                  converts" ceiling (see Gate 7)
400–499:   2 sellers  ( 9.1%)
500–599:   3 sellers  (13.6%)
600–699:   2 sellers  ( 9.1%)
700–799:   1 seller   ( 4.5%)
800–899:   2 sellers  ( 9.1%)
900–999:   2 sellers  ( 9.1%)
1000:      2 sellers  ( 9.1%)   — hit the exact theoretical ceiling
```

**Notable clustering**: three sellers (RRR REF ALTO, DDD REF PERF, TTT
REF PERF) all score exactly **380**, despite having different `vendas`
counts (6, 5, 4) — because all three have `fin=0`. With 0 financings,
`share`/`spf`/`retorno` (490/1000 of Novos' total weight) are all
necessarily 0, and 380 = full `volume` (250, being the run's own
max-vendas performer or close) + full `familias` (130, if 3+ families
sold) — a hard ceiling for "generates sales activity but converts
nothing," independent of how much volume they generate above the
minimum needed to lead the pack. This is a real, load-bearing insight
for where a DESENVOLVIMENTO/PERFORMANCE boundary should sit (see Gate
13/15).

**No negative scores are possible** (every component is
non-negative by construction, outer clamp floors at 0). **Two exact
1000s** exist in the sample — both from fixtures specifically engineered
to prove the ceiling is reachable (`very_low`'s BBB TOPO PERF,
`very_high`'s EEE MELHOR PERF), not organic data.

## Gate 6 — Historical/real data availability

Searched only local, already-authorized project artifacts (no
production/Supabase access attempted):

```
tests/fixtures/score-fixtures.json    → FIXTURE (12 synthetic,
                                        engineer-authored cases, each
                                        built to exercise one specific
                                        formula edge case — tie_case,
                                        sorting_case, confidence_boundary,
                                        zero_values, missing_optional_data,
                                        large_values, long_name — NOT
                                        organic seller behavior)
tests/fixtures/score-golden-output.json → derived from the same
                                          fixtures (golden output, not
                                          an independent data source)
facelift-prototype-01/mock-data.js      → SAMPLE, but on a completely
                                          different, incompatible,
                                          hand-authored 0-100-ish scale
                                          (see Gate 9) — not usable as
                                          evidence for the real 0-1000
                                          engine's distribution
```

**No HISTORICAL SNAPSHOT or REAL LOCAL EXPORT of actual seller Score
data exists anywhere in this authorized local environment.**
Classification: **FIXTURE only.** The n=22 sample in Gate 4/5 must not
be treated as representative of the real Brabus seller population —
it is a curated edge-case test set, useful for proving the formula's
mechanics but not for calibrating population-level thresholds.

## Gate 7 — Component sensitivity

Traced from the actual implementation, not estimated:

- **+1 financing from 0**: the single largest sensitivity event in the
  formula. Instantly unlocks non-zero `share`, `spfRate`, and `retorno`
  (worth up to 490/1000 combined weight for Novos, 700/1000 for
  Seminovos) and moves `confFin` from 0 to 0.5. Going from 0→1
  financing is disproportionately more impactful than any single later
  increment.
- **+1 financing from 1→2**: completes `confFin` to 1.0 (full
  confidence unlocked on SPF/retorno) — the second-largest single step.
  Beyond `fin=2`, further financings only help via changing the
  `spfRate`/`retorno` ratios themselves, with diminishing marginal
  effect.
- **Share (penetração), 1 percentage point**: linear impact up to 60%
  share (`min(1, share/0.6)`), then flat — a point of share matters
  strictly more below the 60% threshold than above it, where the
  component is already saturated.
- **Retorno, 1 percentage point**: linear up to 8% (`min(1, ret/0.08)`),
  then flat — same saturation pattern.
- **Production/revenue value themselves are NOT direct score inputs.**
  `producao`/`valorFinanciado` only enter as the DENOMINATOR of the
  `retorno` ratio — a seller with high production but proportionally
  low return sees no volume-based credit for the production amount
  itself. There is no separate "production total" or "revenue total"
  component in the Score formula (unlike Dashbi's own primary-metric
  hierarchy) — worth flagging since a naive reader might assume larger
  deals score higher; they don't, independent of return rate.
- **Step functions**: `confVendas`/`confFin` are linear ramps (not true
  step functions) from 0 to 1, but they act as de facto soft gates —
  a seller below the sample-size floor (vendas<4 or fin<2) has EVERY
  confidence-scaled component proportionally suppressed, compounding
  across `share` and `retorno` simultaneously.
- **No caps below 1000 exist beyond each component's own weight** — no
  artificial global ceiling below the natural 1000 sum.

## Gate 8 — Existing semantic thresholds

The engine already embeds 5 genuine business thresholds (all found by
direct source read, none invented this Wave):

```
Penetração de financiamento:   60% share      → full credit
Mix de famílias (Novos):        3 families      → full credit
Mix de planos (Novos):           4/4 plan types    → full credit
SPF EXTRA:                        100% attach rate    → full credit
Retorno médio:                     8% return-on-production → full credit
Sample-size floor (share/retorno):    vendas>=4, fin>=2 → full confidence
```

These ARE a defensible basis for band thresholds, in the sense that
they define what "100% credit" means per dimension — but they say
nothing directly about what TOTAL summed score should count as
CRÍTICO/DESENVOLVIMENTO/PERFORMANCE/ALTA PERFORMANCE/ELITE. No new
thresholds were invented to bridge that gap in this document — Gate 13
proposes candidates built FROM these existing thresholds' implications
(e.g., the observed 380 "converts nothing" ceiling, Gate 5), not from
new arbitrary numbers.

## Gate 9 — Existing score-band history

**Normative Design System reference** (`design-system-2.1/references/
score.md`, Status: **APPROVED**, source: `facelift-prototype-01/
index.html#score`):

```
MUST:  "Score value, band (ALTO/BOM/BAIXO), confidence, component
       breakdown (meters, not gamified), explanation. Status must
       never depend on color alone."
```

This is a **3-band model (ALTO/BOM/BAIXO)**, different from the
human's new 5-band product direction. Key findings:

- **No numeric thresholds are defined in the normative reference
  itself.** The MUST rule only requires that *a* band concept exists
  visually — it never specifies where the boundaries sit.
- **Thresholds AND colors WERE defined, but only in the prototype's
  own throwaway mock data**, never promoted into the normative
  reference: `facelift-prototype-01/mock-data.js` line 73:
  `faixa: s.score >= 80 ? 'ALTO' : (s.score >= 55 ? 'BOM' : 'BAIXO')`,
  with colors `pages.js`: ALTO→`--color-success`, BOM→`--color-info`,
  BAIXO→`--color-critical`.
- **Critical scale mismatch, not to be missed**: the prototype's mock
  scores are hand-authored fictional values on an unrelated ~0–100
  scale (`score: 91`, `79`, `38`, `74`...) — invented for visual design
  purposes **before the real `calcScores()` engine was ever extracted
  from production**. The 80/55 thresholds have **zero mathematical
  relationship** to the real engine's 0–1000 scale. Naively reapplying
  80/55 to real scores would misclassify almost every seller as BAIXO
  (since real scores range up to 1000, 80 is a tiny fraction of that).
  This is exactly why PORTAL-NEXT-04's own audit (`docs/SCORE-ENGINE-
  AUDIT.md`) flagged the ALTO/BOM/BAIXO band as an unresolved Design
  System conflict rather than implementing it as-is — confirmed here
  as the correct call, not merely inherited caution.
- **Why it remained unresolved**: no business-defensible numeric
  threshold was ever derived from the REAL formula for ANY band model
  — 3-band or 5-band. This Wave is the first attempt to do that
  derivation from the actual engine rather than the prototype's mock.

## Gate 10 — Three models evaluated

**Model A — Absolute fixed bands** (score X always means the same
classification regardless of period/population).
*Advantages*: maximally interpretable to executives; stable meaning
over time; directly defensible ("PERFORMANCE means retorno>=8% AND
share trending toward 60%..."). *Risks*: 5/6 components are already
absolute, but the `volume` component's `maxVenda` normalization is
population-relative (Gate 3) — a pure absolute-band promise is not
100% true to the underlying number, though the effect is usually small
in a stable-sized team. *Stability*: high, since only the volume
component can drift. *Defensibility*: high, given 5 of 6 formula
inputs already use absolute business thresholds.

**Model B — Relative/percentile bands** (classification depends on the
current seller distribution).
*Advantages*: guarantees a spread across bands every period; simple to
compute. *Risks*: directly contradicts the human's own stated product
preference (Gate 11) — a seller could become "ELITE" purely because
peers underperformed, with zero change in their own numbers; also
unstable under population change (a strong team makes everyone look
"average," a weak team makes mediocre performers look "elite").
*Interpretability*: low for absolute performance meaning, since the
same number means different things period to period. *Fairness*: poor
for the "fixed interpretable meaning" goal.

**Model C — Hybrid** (fixed thresholds informed by empirical
distribution and business targets).
*Advantages*: keeps the interpretability of Model A while calibrating
where boundaries sit using the formula's own embedded thresholds and
observed clustering (e.g., the real 380 "converts nothing" ceiling
found in Gate 5) rather than picking round numbers blind.
*Risks*: requires periodic recalibration if the underlying formula or
population changes materially — a governance cost, not a math cost.
*Stability*: high, same as Model A, since thresholds are still fixed
once set; only their initial calibration used distribution evidence.

## Gate 11 — Product preference applied, not forced

The stated preference (fixed, interpretable meaning; a seller should
not become ELITE merely because everyone else underperformed) points
toward **Model A or Model C**. Given 5 of 6 formula components already
carry real absolute business thresholds, and the one relative
component (volume) is a modest share of total weight (250-300/1000),
**Model C (Hybrid)** is recommended: absolute score thresholds, but
calibrated using the real formula's own embedded meaning and the
observed 380-ceiling finding — not blind round numbers, and not
peer-relative.

## Gate 12 — Five bands, business meaning validated against the engine

| Band | Hypothesis (from brief) | Validated against engine |
|---|---|---|
| CRÍTICO | Materially below expected operating level | Consistent with: `fin=0` sellers (0 conversion) OR very low activity (vendas<2). Formula supports this: a 0-fin seller cannot exceed the ~380 volume+familias ceiling, and a seller with near-0 activity scores near 0 by construction. |
| DESENVOLVIMENTO | Some performance, important dimensions below target | Consistent with: sellers converting SOME financings but missing multiple absolute thresholds (share<60%, no plan-mix diversity, retorno<8%) — the observed 400-600 range in Gate 5 clusters here. |
| PERFORMANCE | Healthy/expected operating performance | Consistent with: meeting most but not all absolute thresholds, `fin>=2` (full confidence), share trending toward 60% — observed ~600-800 range. |
| ALTA PERFORMANCE | Consistently above expected | Consistent with: meeting nearly all absolute thresholds simultaneously — observed ~800-950 range. |
| ELITE | Exceptional, highest intended standard | Consistent with: meeting essentially every absolute threshold at once (60% share, full plan/family mix, 100% SPF, 8%+ retorno) AND leading or near-leading in volume — by construction genuinely rare (Gate 17). |

These hypotheses hold up against the formula's actual mechanics — not
contradicted by anything found in Gates 1-9.

## Gate 13 — Threshold candidates (NOT implemented)

All three options are absolute (Model C/Hybrid), 0-1000 scale, informed
by the embedded thresholds (Gate 8) and the observed 380-ceiling and
percentile evidence (Gates 4-5) — not blind round numbers, and
explicitly NOT derived from the incompatible prototype 80/55 scale
(Gate 9).

**OPTION 1 — Conservative** (wider CRÍTICO/DESENVOLVIMENTO bands, ELITE
reserved for very rare cases):
```
CRÍTICO:           0–299
DESENVOLVIMENTO:   300–549
PERFORMANCE:       550–749
ALTA PERFORMANCE:  750–899
ELITE:             900–1000
```

**OPTION 2 — Balanced / Recommended**:
```
CRÍTICO:           0–249
DESENVOLVIMENTO:   250–449
PERFORMANCE:       450–699
ALTA PERFORMANCE:  700–874
ELITE:             875–1000
```

**OPTION 3 — Selective Elite** (same lower bands as Option 2, ELITE
held to a materially higher bar):
```
CRÍTICO:           0–249
DESENVOLVIMENTO:   250–449
PERFORMANCE:       450–699
ALTA PERFORMANCE:  700–924
ELITE:             925–1000
```

## Gate 14 — Classification simulation (real fixture sample, n=22)

```
                    OPTION 1              OPTION 2              OPTION 3
Band                Count  %              Count  %              Count  %
CRÍTICO             1      4.5%           2      9.1%           2      9.1%
DESENVOLVIMENTO     6      27.3%          5      22.7%           5      22.7%
PERFORMANCE         9      40.9%          7      31.8%           7      31.8%
ALTA PERFORMANCE    4      18.2%          6      27.3%           4      18.2%
ELITE               2      9.1%           2      9.1%            4      18.2%
```

Representative sellers near boundaries (all names already used by
existing Score fixtures, per Gate 14's own allowance):

```
Score 380 (RRR REF ALTO / DDD REF PERF / TTT REF PERF, all fin=0):
  Option 1: DESENVOLVIMENTO (just above 300 floor)
  Option 2: PERFORMANCE (just above 250 floor) — arguably too generous
            for a 0-conversion seller, see Gate 15
  Option 3: same as Option 2

Score 470 (P3 RANK TERCEIRO):
  All 3 options: DESENVOLVIMENTO (Opt 1) / PERFORMANCE (Opt 2/3) —
  boundary-sensitive, sits right at Option 1's 449/550 gap

Score 892 (SSS ALTO2 PERF):
  Option 1: ALTA PERFORMANCE   Option 2: ALTA PERFORMANCE
  Option 3: ALTA PERFORMANCE (below 925 Elite bar)

Score 955 (GGG QUATRO VENDAS):
  Option 1: ELITE (>=900)   Option 2: ELITE (>=875)
  Option 3: ALTA PERFORMANCE (below 925) — illustrates how Option 3
  deliberately makes Elite harder to reach
```

**Flagged finding**: the 380-score "sells but converts nothing" cluster
lands in PERFORMANCE under Options 2/3 — arguably contradicts the
CRÍTICO/DESENVOLVIMENTO hypothesis validated in Gate 12 (a seller who
never converts a single financing reading as "healthy performance" is
questionable). Option 1's 300/549 split keeps this cluster in
DESENVOLVIMENTO instead, which reads as more defensible. This tension
is reported, not resolved — a human threshold decision, not a
mathematical one.

## Gate 15 — Boundary analysis

- **Why the CRÍTICO/DESENVOLVIMENTO boundary matters most**: this is
  where the 0-conversion sellers sit (Gate 5's 380 cluster). The
  boundary choice directly determines whether "generates leads but
  never closes" reads as CRÍTICO, DESENVOLVIMENTO, or (under Option
  2/3) even PERFORMANCE — a real business-meaning decision, not a
  statistically convenient one.
- **DESENVOLVIMENTO/PERFORMANCE boundary**: no single formula
  threshold maps directly here since it's a SUM of several ratios: the
  boundary is necessarily a judgment call about "how many of the 5
  absolute sub-thresholds must be met" rather than one clean
  mathematical line. Flagged as inherently a business decision, not
  purely derivable.
- **ALTA PERFORMANCE/ELITE boundary**: has the clearest mathematical
  grounding of the four boundaries — it's the region where a seller
  must be hitting nearly every embedded absolute threshold at once
  (Gate 12), which is a genuinely rare, compounding condition by
  construction (Gate 17).
- **Month-to-month oscillation risk**: real, structurally. Because
  `confVendas`/`confFin` ramp linearly and several ratio thresholds
  (60% share, 8% retorno) are meaningful percentages that can swing on
  small absolute changes for low-volume sellers, a seller near a
  boundary with only 4-5 sales/2-3 financings in a period could
  plausibly cross a band boundary from one low-volume month to the
  next purely from normal variance, not a real performance change. Not
  quantified with real data (see Gate 16) — flagged as a genuine risk
  worth testing against real historical data before finalizing.

## Gate 16 — Stability

**INSUFFICIENT EVIDENCE FOR TEMPORAL STABILITY ANALYSIS.** No
historical/multi-period real dataset exists locally (Gate 6) to
measure actual month-to-month band-switching frequency. The
theoretical oscillation risk described in Gate 15 is a structural
inference from the formula's mechanics, not a measured rate — stated
as such, not fabricated as a number.

## Gate 17 — Elite scarcity

ELITE is NOT defined as "top N%" under any of the 3 options — all use
fixed absolute score floors (875-925 depending on option). Under the
n=22 fixture sample, ELITE captures 9.1-18.2% depending on option — but
this sample is heavily biased toward edge cases specifically engineered
to hit the ceiling (Gate 6), so this percentage is **not a reliable
estimate of real-population ELITE scarcity**. What IS defensible: by
construction (Gate 3), reaching 875+ requires simultaneously clearing
5-6 compounding absolute thresholds (60%+ share, full family/plan mix
where applicable, 100% SPF attach, 8%+ retorno, sufficient volume) —
structurally rare regardless of the exact cutoff chosen, since each
individual threshold alone is already demanding and they must ALL be
met together. Option 3's 925 floor pushes this further by explicitly
excluding scores in the 875-924 range (which under the sample still
includes at least one seller, SSS ALTO2 PERF at 892, who meets most but
not literally every threshold).

## Gate 18 — Critical semantics risk

**Real risk confirmed, not hypothetical**: a brand-new seller with
`vendas=1, fin=0` (fixture `very_low`'s AAA BAIXO PERF) scores **71** —
solidly CRÍTICO under every option. This is NOT unfair per se (the
formula has no tenure/newness adjustment at all — `isScoreSellerEligible`
is a no-op, Gate 1), but it means CRÍTICO will structurally capture:
- Genuinely underperforming established sellers (the intended target).
- **Brand-new sellers with only 1-2 transactions**, indistinguishable
  by the formula from a poor performer, since there is no
  tenure/ramp-up signal anywhere in `calcScores()`.
- Low-volume Seminovos-only or single-department sellers, if their
  absolute activity count is simply small.

This is a real, disclosed risk: **the current formula cannot
distinguish "new" from "underperforming."** Flagged per Gate 18's own
instruction — not fixed this Wave, since fixing it would require a
business decision (e.g., a tenure exemption) outside this
investigation's scope.

## Gate 19 — Zero/no-data distinction

**Real defect found, not assumed safe**: the `missing_optional_data`
fixture (a financing record missing `receitaSPF`/`spfQtd` keys
entirely — its own fixture description says "must be treated as
falsy/0") produces **`score = NaN`**, not 0 and not a clean fallback.
Root cause traced precisely: `o.spfQtd += f.spfQtd || 0` correctly
defaults the field, but the adjacent accumulator `o.retorno += f.retorno
+ f.receitaSPF` has **no equivalent `|| 0` fallback for
`f.receitaSPF`** — `undefined` in that addition produces `NaN`, which
permanently poisons the running `o.retorno` total, then `ret`, then the
`retorno` score component, then the final summed `score`.

This is very likely a **pre-existing production defect**, not a V2
extraction error — `calcScores()` was extracted byte-identical from
`origin/main` (docs/SCORE-ENGINE-AUDIT.md), and the existing 12/12
parity test suite does not catch it because `JSON.stringify(NaN)`
serializes to `null` in JavaScript — both the independently re-extracted
reference and the V2 adapter reproduce the identical `NaN→null`
behavior, so the parity comparison matches (proving byte-identical
extraction, not correctness).

**Currently, `Score=0` (true floor), `no activity` (absent from output
entirely — a seller with 0 sales AND 0 financings never appears in
`calcScores()`'s return array at all), and `missing/malformed optional
data` (NaN, a silent corruption) are three different, NOT cleanly
distinguished states.** This materially affects any future CRÍTICO
definition: a NaN score cannot be compared against any numeric
threshold in JavaScript (`NaN < anything` is always `false`), so a
naive future band-classification `if/else if` chain would likely leave
such a seller unclassified or fall through to an unintended default —
a concrete implementation risk to flag for whoever builds the band
feature, not fixed here per this Wave's explicit "investigation only,
zero implementation changes" boundary.

## Gate 20 — Language review

```
CRÍTICO             — clear, direct, but can read as harsh/demotivating
                      in a performance-management/HR context if shown
                      to the seller themselves (vs. management-only
                      viewing) — flag for human consideration of
                      audience before finalizing copy.
DESENVOLVIMENTO      — clear, professional, appropriately neutral/
                       constructive tone. No concerns.
PERFORMANCE          — clear as a mid-tier label, though it's also the
                        generic term for the whole discipline being
                       measured ("Análise de Score Vendedores... Ranking
                      de performance F&I") — mild ambiguity risk
                     (a band literally named the same as the page's own
                    subtitle), not a hard problem.
ALTA PERFORMANCE       — clear, professional, executive-appropriate.
ELITE                    — clear, strong executive tone; some
                          organizations read "Elite" as excluding/
                         elitist language in HR contexts — worth a
                        one-line human gut-check, not a strong
                       objection.
```

No alternative label is proposed as materially better — the set is
coherent and professional as given. The two soft flags above (CRÍTICO's
possible harshness if seller-facing, PERFORMANCE's mild self-referential
overlap) are noted for the human's awareness, not acted on.

## Gate 21 — Future visual direction (described, not built)

```
SCORE
742
ALTA PERFORMANCE
[approved score bar — unchanged fill/track from the current
 implementation, positioned per the existing score value/1000]
```

Hierarchy: (1) the raw numeric score remains primary and immediately
visible — unchanged from today; (2) the band label reads as the
second-most prominent element, directly beneath/beside the number; (3)
the already-approved visual bar keeps its current role as a positional
indicator, not redesigned. No new CSS was written or even sketched
beyond this textual description, per Gate 21's own instruction.

## Gate 22 — Color caution

The current Score bar (`.scMeterFill`) uses a single
`--color-accent-primary` fill, deliberately NOT band-derived — Score's
own file comments (score.css) explicitly document this as a prior Wave
decision ("não codificar qualidade do vendedor por cor se produção não
possui essa semântica"). The Design System's semantic tokens
(`--color-success`/`--color-warning`/`--color-critical`/`--color-info`,
`design-system-2/tokens.css`) exist and were used by the PROTOTYPE's
own mock 3-band coloring (Gate 9), but that mapping was never validated
against the real 5-band/1000-scale model and is not recommended for
reuse without a dedicated future color decision. **No color was chosen
or implemented in this Wave** — flagged as a distinct, separate future
decision per Gate 22's own instruction.

## Gate 23-25 — Guards

```
Score HTML/CSS/JS diff:        0 (verified via git status/diff below)
Score formula diff:                0
Score fixtures diff:                   0
Dashbi/Landing/Coparticipado/Gestão diff:  0
Production:                                    UNTOUCHED
Backend calls:                                     0
```

## Recommendation summary

- **Method**: Model C (Hybrid) — absolute thresholds calibrated from
  the formula's own embedded meaning and observed clustering, not
  peer-relative.
- **Recommended option**: **Option 1 (Conservative)** over the
  nominally-labeled "Option 2 — Balanced," specifically because Gate
  14/15's simulation shows Option 2/3's 250 CRÍTICO/DESENVOLVIMENTO
  floor pulls the real "0-conversion, sells but never closes" cluster
  (score 380) up into PERFORMANCE — contradicting Gate 12's own
  validated business meaning for that band. Option 1's wider 300/549
  split keeps that cluster in DESENVOLVIMENTO, which better matches
  the intended semantics. This is a recommendation for the human to
  weigh, not a decision made on their behalf.
- **Elite**: Option 1's 900 floor (not Option 3's 925) is recommended
  as the starting point — already structurally rare (Gate 17) without
  needing the more aggressive Option 3 cutoff; Option 3 remains
  available if the human wants ELITE to be rarer still.
- **Before finalizing**: address Gate 18 (new-vs-underperforming
  conflation) and Gate 19 (NaN defect) as separate, explicit human
  decisions — neither blocks choosing a threshold model, but both will
  affect real-world classification quality once implemented.
