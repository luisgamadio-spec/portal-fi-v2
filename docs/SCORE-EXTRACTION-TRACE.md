# Score Extraction Trace (Gate 46)

## Production source truth (Gate 45)

```
Production source files:     modules/score.html (portal-financiamento-
                             brabus-secure)
Production SHA (file blob):    cbaacb0b4c1cd50294984eaf5fdb59fe2917868d
                             (git rev-parse origin/main:modules/score.html
                             — PROVED byte-identical to live production
                             in PORTAL-NEXT-03.1 and re-confirmed this
                             Wave)
Repo commit (origin/main):       2f17eb2341c5cc14aa8710aa044103002ca572a9
Critical function names:            SCORE_WEIGHTS, MIX_PLANOS_UNIVERSO,
                             num, pct, calcScores
Golden fixture generation source:      PORTAL-FI-DESIGN-LAB/PORTAL-NEXT-04/
                             .source/reference-standalone.html — built
                             by mechanically extracting the 5 items
                             above directly from
                             `git show origin/main:modules/score.html`
                             (Python script, not hand-retyped — see
                             REPORT.md's PORTAL-NEXT-04 entry for the
                             exact extraction command)
```
A future session can reproduce all of this independently:
`git show 2f17eb2341c5cc14aa8710aa044103002ca572a9:modules/score.html`
against `portal-financiamento-brabus-secure` — no dependency on this
conversation's memory.

## Function map (Gate 46)

| SOURCE | TARGET | Behavior change | Test | Parity |
|---|---|---|---|---|
| `calcScores(sales,fins)` | `assets/js/adapters/score.adapter.js` → `window.NX_SCORE_ADAPTER.compute` | **NONE** — byte-identical (programmatically diffed, 2665/2665 chars match) | `tests/score-parity-test.py`, 12/12 golden fixtures | PASS |
| `SCORE_WEIGHTS` | same file, `_internal.SCORE_WEIGHTS` | NONE — byte-identical | same | PASS |
| `MIX_PLANOS_UNIVERSO` | same file, `_internal.MIX_PLANOS_UNIVERSO` | NONE — byte-identical | same | PASS |
| `num(v,d=0)` | same file, `_internal.num` | NONE — byte-identical | same | PASS |
| `pct(v)` | same file, `_internal.pct` | NONE — byte-identical | same | PASS |
| `isScoreSellerEligible(r)` | same file, local stub | **INTENTIONALLY NOT MIGRATED** — see below | N/A this Wave | N/A |

## Function intentionally NOT migrated

```
FUNCTION:          isScoreSellerEligible(r)
REASON:              depends on DATA.vendors, a backend-loaded vendor
                    registry (Supabase). This Wave has 0 backend calls
                    (Gate 8) and uses local fixtures only (Gate 25:
                    "implement only [filters] that can operate on
                    fixtures without backend").
SUBSTITUTION:          a local accept-all stub in score.adapter.js.
                    Fixtures are documented as pre-filtered/eligible
                    (tests/fixtures/score-fixtures.json's own note).
DOES THIS TOUCH         NO — the substitution changes what the
calcScores()?          pre-existing filter call resolves to; it does
                    not add, remove, or modify a single line inside
                    calcScores() itself (verified: 2665/2665 chars,
                    see table above).
FUTURE WORK:              when this module gets real backend
                    integration (a later, explicitly-scoped Wave per
                    PORTAL-NEXT-03.1's own Gate 29 guidance on
                    sequencing auth work), isScoreSellerEligible must
                    be extracted the same way — read from origin/main,
                    diffed, proved, not reconstructed.
```

## Second function intentionally NOT migrated (Gate 62)

```
FUNCTION:          openSellerDetails(vend, loja)  [production line 665]
WHAT IT DOES:         a SECOND, deeper drill-down than the criteria
                     breakdown — opens a modal listing every individual
                     sale/financing record for that seller (Cliente,
                     Modelo, Família, Valor Venda, Valor Financiado,
                     Plano, Prazo, Parcela, Balão, Retorno, SPF, Data,
                     Chassi columns), using money()/financiamentoCell
                     Balao()/financiamentoCellParcela() formatters.
REASON NOT MIGRATED:    two independent, sufficient reasons: (1) it
                     needs a per-TRANSACTION data model (cliente,
                     modelo, chassi, parcela, balão fields) far beyond
                     this Wave's aggregate sales[]/fins[] fixture
                     shape (docs/SCORE-ENGINE-AUDIT.md); (2)
                     financiamentoCellBalao/financiamentoCellParcela
                     are SIMULATOR-domain rendering functions —
                     migrating them would cross directly into "Balão"
                     display logic, which Gate 34 of this Wave's brief
                     explicitly forbids touching.
WHAT WAS MIGRATED       the FIRST-level drill-down — the score
INSTEAD:               criteria breakdown (scoreDetailsTitle/
                     scoreCriterion/scoreDetailGrid in production,
                     assets/js/score.js's .scDetail region in V2) —
                     genuinely self-contained Score logic, no
                     simulator overlap.
```
This is a real, disclosed scope boundary, not an oversight — Score V2
this Wave shows score + band-equivalent-absent + confidence +
breakdown + explanation (per design-system-2.1/references/score.md's
MUST list, band excepted — see docs/SCORE-ENGINE-AUDIT.md), not the
full per-sale audit trail production also happens to offer from the
same page.

## No-cleanup-drift confirmation (Gate 47)

The extraction was verified via direct string comparison against the
source (`docs/SCORE-ENGINE-AUDIT.md`'s method), not a manual
"transcribe and hope" copy. No formula was simplified, no variable
renamed, no weight adjusted, no rounding changed, no sort order
touched. The ONLY non-behavioral change anywhere in the extracted code
is the `isScoreSellerEligible` substitution documented above, which is
external to `calcScores()`, not internal to it.
