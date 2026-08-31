# Score — receitaSPF Non-Finite Defect: Root Cause & Correction (PORTAL-NEXT-07.7C)

**Status: FIXED.** Resolves the pre-existing defect discovered (not
fixed) in `docs/SCORE-BAND-DISCOVERY-07-7A.md` Gate 19 and intentionally
left untouched in PORTAL-NEXT-07.7B.

## The original defect

```
Symptom:     calcScores() can return score = NaN for a real seller row.
Trigger:     a fins[] record whose receitaSPF is missing (property
             absent / undefined) reaching calcScores() (assets/js/
             adapters/score.adapter.js's byte-identical extraction of
             production's calcScores()).
Reproduced:  tests/fixtures/score-fixtures.json's "missing_optional_data"
             case, and tests/score-spf-defect-test.py's "BEFORE" check
             (runs the untouched reference at PORTAL-NEXT-04/.source/
             reference-standalone.html directly — score comes back NaN).
```

## Root cause (Gate 9)

Inside `calcScores()`'s `fins.forEach(...)`:

```js
o.retorno += f.retorno + f.receitaSPF;   // no fallback
o.spf     += f.receitaSPF;               // no fallback
o.spfQtd  += f.spfQtd || 0;              // HAS a fallback
```

`f.retorno` (a number) `+` `f.receitaSPF` (`undefined`) evaluates to
`NaN` in JavaScript — `f.receitaSPF` is the first non-finite operand.
`o.retorno` accumulates to `NaN` from that point on (`NaN + anything =
NaN`), `ret = o.retorno / o.producao` becomes `NaN`, the "Retorno
médio" breakdown item becomes `NaN`, and `score += NaN` poisons the
running total for every subsequent `addBreak()` call — the final
`Math.round(Math.max(0, Math.min(1000, score)))` is `NaN` regardless of
how well the seller did on every other criterion.

The adjacent `spfQtd` accumulator already had a `|| 0` fallback for
exactly this kind of optional/absent SPF-derived field — the two
`retorno`/`spf` lines lacking one is best read as an asymmetry/oversight
in the original code, not a deliberate design choice (see business
evidence below).

## Business meaning of receitaSPF (Gate 5) — evidence, not inference

`receitaSPF` is the summed value of a financing proposal's "SPF EXTRA"
line items. Traced to its construction in **two independent,
byte-identical copies of production's own `processFins()`**:

- `PORTAL-NEXT-04/.source/score-origin-main.html` (a locally-saved copy
  of `git show origin/main:modules/score.html`, i.e. live production —
  read locally, no production connection made this Wave, Gate 6/36)
- `portal-next-v2/assets/js/adapters/coparticipado.adapter.js`'s own
  byte-identical extraction of the same function

Both build it identically:

```js
const receitaSPF = g.spfRows.reduce(
  (s, r) => s + asNumber(getCol(r, ['Valor Serviço','Retorno Bruto','Retorno  Liquido'])),
  0   // <-- numeric seed
);
```

`Array.prototype.reduce` with a numeric seed **always returns a
number** — when a financing proposal has zero "SPF EXTRA" rows (which
is the normal case: most financed sales carry no SPF product), this
still evaluates to exactly `0`, never `undefined`. **Production's real
data pipeline cannot structurally produce a fins[] record with
`receitaSPF` missing.** A fixture/adapter-boundary input that omits it
is therefore not evidence of a legitimate "unknown SPF revenue"
business state — it is an input that does not yet conform to
production's own guaranteed contract.

Corroborating evidence:
- `tests/fixtures/score-fixtures.json`'s own `missing_optional_data`
  case description (written when the fixture set was authored, before
  this defect was discovered): *"Financing record missing plano
  (undefined) and receitaSPF/spfQtd (absent keys) -- must not throw,
  must be treated as falsy/0."* — the project's own prior, independent
  statement of intent already pointed at zero semantics.
- The sibling `spfQtd += f.spfQtd || 0` accumulator in the same
  function already treats a missing/falsy SPF-derived field as `0`.

**Conclusion (Gate 10/11): missing receitaSPF = ZERO SPF revenue.
Evidence is conclusive, not ambiguous.** No human decision required;
implementation proceeded per Gate 11's "Case A" branch.

## Correction (Gates 14/15/28)

`calcScores()` itself is **not modified** — it remains the byte-identical
extraction the file's own header comment (Gate 47, established in an
earlier Wave) forbids touching. The correction sits at the adapter's
input boundary, in `assets/js/adapters/score.adapter.js`:

```js
// byte-identical extraction of production's own asNumber() (also
// present, byte-identical, in coparticipado.adapter.js)
function asNumber(v){ ... }

function normalizeFinInput(f) {
  return Object.assign({}, f, { receitaSPF: asNumber(f.receitaSPF) });
}

function compute(sales, fins) {
  return calcScores(sales, (fins || []).map(normalizeFinInput));
}
```

`asNumber()` is not a new rule invented for this fix — it is
production's own canonical numeric parser, the same function production
itself uses inside `processFins()` to build `receitaSPF` in the first
place. Reusing it here means the V2 adapter boundary now enforces the
exact guarantee production's real pipeline already provides, rather
than inventing a parallel `|| 0` convention (Gate 14's explicit
preference for one normalization point over scattered defensive
fallbacks).

Scope is deliberately narrow (Gate 28): only `receitaSPF` is
normalized. `retorno`, `valorFinanciado`, `spfQtd`, and every other
field are untouched — no broad/global coercion was introduced.

## Missing-value matrix (Gate 3/19) — `tests/score-spf-defect-test.py`

| Input | Normalized to |
|---|---|
| property absent | 0 |
| `undefined` | 0 |
| `null` | 0 |
| `''` | 0 |
| `'   '` (whitespace) | 0 |
| `0` | 0 (preserved, not miscoerced — Gate 13) |
| `'0'` | 0 |
| `1234.56` | 1234.56 (unchanged) |
| `'1.234,56'` (BRL string) | 1234.56 |
| `NaN` | 0 |
| `Infinity` / `-Infinity` | 0 |
| non-numeric text | 0 |

All 13 cases verified live via `window.NX_SCORE_ADAPTER._internal.normalizeFinInput()`.

## Before / after

```
Fixture:            missing_optional_data ("JJJ DADOS FALTANTES")
Before:              score = NaN, retorno = NaN, spf = NaN,
                     Score Band = none (classifyScoreBand(NaN) -> null)
After:                score = 431, retorno = 800, spf = 0,
                     Score Band = DESENVOLVIMENTO (300-549)
Math (after):            Volume 250 + Penetração 58 + Mix famílias 43 +
                         Mix planos 0 + SPF EXTRA 0 + Retorno médio 80
                        = 431 (retorno médio hits its 8% reference
                       exactly: 800/10000 = 0.08, capped confFin=0.5
                      for 1/2 financings -> 160*1*0.5=80)
```

Band comes from the real `classifyScoreBand(431)` call, not a manual
assignment (Gate 26).

## Regression scope

- The other 11 score fixtures: numerically **unchanged** — each already
  carries a valid, finite `receitaSPF`, so `normalizeFinInput()` is a
  no-op for them (`asNumber()` returns an already-finite number
  unchanged). Verified by `tests/score-parity-test.py`: 11/12 exact
  byte-match against the untouched production reference.
- `missing_optional_data` now **intentionally diverges** from that same
  raw reference (which still returns `NaN` — it is the byte-identical,
  unmodified `calcScores()`, deliberately never touched). This one
  mismatch in `score-parity-test.py`'s output **is the fix working
  as intended**, not a regression — see that test file's own docstring,
  which describes it as a fidelity check against raw production math,
  not a business-correctness check.
- `tests/score-band-test.py`'s former "real NaN fixture -> None" case
  was updated to assert the new, correct end-to-end behavior (real
  score, real band, both computed live) — the classifier's own
  invalid-input contract (`NaN`/`Infinity`/`-Infinity`/`null`/
  `undefined`/`-1` -> `null`) is unchanged and still separately covered
  by 6 dedicated synthetic cases.

## Known, unchanged limitations

- The "no tenure signal" limitation from 07.7A remains, untouched.
- No other field's missing-value handling was audited or changed in
  this Wave — only the specific, evidenced `receitaSPF` defect.

## Verification

```
tests/score-parity-test.py:               11/12 (missing_optional_data
                                          intentionally diverges from
                                         raw production reference — see
                                        above)
tests/score-band-test.py:                     24/24
tests/score-spf-defect-test.py (new):             16/16 (before/after +
                                                  13-case matrix + Gate
                                                 13 zero-preservation)
Score range after fix:                                0 <= score <= 1000,
                                                       finite -- PASS
Other modules diff:                                       0
score.adapter.js calcScores() line:                           byte-for-
                                                              byte
                                                             unchanged
                                                            (only
                                                           additions
                                                          before/after
                                                         it — verified
                                                        via git diff)
Console errors (live page,
both fixtures affected/unaffected):                                0
Responsive (390px, both renderers):                                    no
                                                                        horizontal
                                                                       scroll,
                                                                      no
                                                                     clipping
```
