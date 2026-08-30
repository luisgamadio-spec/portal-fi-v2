# Score Engine Audit (Gate 4) — read from the correct authority

## Critical Gate 3 finding, before anything else

`modules/score.html` is **NOT** one of the files proved byte-identical
between local clone and remote/production in PORTAL-NEXT-03.1 — re-hashed
fresh this Wave and confirmed **still divergent**:
```
local main:    c8156797dabffd4ee7aef0559b784fc89b1c4dbb
origin/main:   cbaacb0b4c1cd50294984eaf5fdb59fe2917868d  (== live production)
```
Per Gate 3's explicit instruction, **the local clone was NOT used as
authority**. Everything below is read from `git show origin/main:
modules/score.html` (saved at `PORTAL-FI-DESIGN-LAB/PORTAL-NEXT-04/
.source/score-origin-main.html` for this Wave's own reference — not
committed to V2).

## What actually changed vs. PORTAL-NEXT-01's original description

PORTAL-NEXT-01's architecture audit (based on the local clone) is now
**stale** for this specific function. Real differences found via
direct diff (`git diff main origin/main -- modules/score.html`):

1. **`SCORE_WEIGHTS` redistributed** (both departments still sum to
   1000, but per-criterion weights changed):
   ```
                Novos (old→new)         Seminovos (old→new)
   volume:      150 → 250               200 → 300
   share:       250 → 230               300 → 270
   familias:    150 → 130               (n/a)
   planos:      200 → 130               (n/a)
   spf:         100 → 100                200 → 150
   retorno:     150 → 160                300 → 280
   ```

2. **A confidence/sample-size dampening mechanism was ADDED** — did
   NOT exist in the version PORTAL-NEXT-01 audited:
   ```js
   const confVendas = Math.min(1, o.vendas/4);
   const confFin = Math.min(1, o.fin/2);
   ```
   Applied as a multiplier on 3 of the criteria: "Penetração de
   financiamento" (×confVendas), "SPF EXTRA" (×confFin), "Retorno
   médio" (×confFin). A seller with fewer than 4 sales or 2
   financings gets those specific criteria's points scaled down
   proportionally — this IS "confidence" in the sense Gate 24 asks
   about, and it DOES exist in production. **Preserved exactly, not
   invented, not renamed.**

3. **"Mix de planos" methodology changed** from a weighted-average
   "plan quality" score (`PLAN_WEIGHT`, now REMOVED — source comment:
   *"nao ha mais PLAN_WEIGHT. REVERSAO fica fora do universo de
   diversidade"*) to a **distinct-category diversity count**:
   ```js
   const planosValidos = new Set([...o.plans].filter(p => MIX_PLANOS_UNIVERSO.has(p)));
   addBreak('Mix de planos (diversidade)', w.planos*Math.min(1, planosValidos.size/MIX_PLANOS_UNIVERSO.size), ...)
   ```
   where `MIX_PLANOS_UNIVERSO = new Set(['LINEAR','BALÃO','COPARTICIPADO','SUBSIDIADO'])`
   (4 categories; `REVERSAO` plan type explicitly excluded from this
   universe). The label itself changed too — "Mix de planos vendidos"
   → "Mix de planos (diversidade)" — production's own commit already
   disclosed the semantic change in its own UI text; V2 preserves that
   disclosure, doesn't hide it.

4. Internal-only, non-behavioral cleanup: `get(v,d)` → `get(v)` (the
   unused `d` param was dropped); `plans:{}}` (weighted accumulator)
   → `plans:new Set(), planCounts:{}` (two structures supporting the
   new diversity + "most common plan" logic). No output-affecting
   change beyond what's already listed above.

## Complete mapping (Gate 4 requirement)

```
INPUTS:           sales[] {vendedor, loja, dept, familia},
                  fins[] {vendedor, loja, dept, valorFinanciado,
                  retorno, receitaSPF, spfQtd, plano}
ELIGIBILITY:        isScoreSellerEligible(r) -- filters by a backend
                  vendor registry (DATA.vendors, requires Supabase).
                  NOT extracted this Wave (Gate 25: only filters that
                  work on local fixtures, zero backend). See
                  "Decomposition decision" below.
NORMALIZATION:        none beyond the eligibility filter -- calcScores
                  itself does no name/text normalization.
WEIGHTS:                SCORE_WEIGHTS (Novos/Seminovos), see above.
                  Per-criterion max points = the weight itself.
GROUPING KEY:             `${vendedor}|${loja}|${dept}` -- same
                  seller in a different loja/dept is a DIFFERENT row.
PEER-RELATIVE VOLUME:       maxVenda = max(vendas) among ALL sellers
                  IN THE SAME calcScores() call, split by dept. Volume
                  score = min(1, own vendas / maxVenda for that dept).
                  This means scores are relative to the peer group
                  passed in, not an absolute scale -- a fixture with a
                  different peer set will legitimately produce
                  different Volume scores for the "same" seller. This
                  is production behavior, not a bug to fix.
THRESHOLDS (ratio caps, all min(1, x/y) patterns):
                  share/0.6 (financing-penetration reference is 60%),
                  familias.size/3 (3 total families exist),
                  planosValidos.size/4 (4-category universe),
                  spfRate (no cap divisor, raw min(1,spfRate)),
                  ret/0.08 (8% return reference).
CONFIDENCE:               confVendas=min(1,vendas/4), confFin=min(1,fin/2)
                  -- see above, applied multiplicatively.
ROUNDING:                   each breakdown item's `points` rounded
                  individually (Math.round) for display; the total
                  `score` is computed from UNROUNDED points, THEN
                  clamped [0,1000] and rounded ONCE
                  (Math.round(Math.max(0,Math.min(1000,score)))).
                  These can differ by up to a few points from summing
                  the already-rounded breakdown items -- production's
                  own behavior, not a V2 rounding bug.
BAND:                         NONE EXISTS in production. No discrete
                  ALTO/BOM/BAIXO classification anywhere in
                  calcScores() or its render path. See "Conflict with
                  Design System 2.1" below -- NOT invented this Wave.
SORTING:                        .sort((a,b) => b.score-a.score ||
                  b.fin-a.fin) -- descending score, ties broken by
                  descending financing count. Preserved exactly.
```

## Decomposition decision (Gate 5)

`calcScores()` itself calls `isScoreSellerEligible` as its first two
lines (filtering `sales`/`fins`). That eligibility check depends on
`DATA.vendors`, populated from a backend registry — unavailable this
Wave (Gate 8: 0 backend calls). **Decision**: `calcScores()`'s own
body is extracted **byte-identical**, unmodified; a local
`isScoreSellerEligible` shim in V2's adapter module returns `true`
unconditionally, with an explicit comment that eligibility filtering
is NOT implemented this Wave — fixtures are assumed pre-filtered
(every fixture record already represents an eligible seller). This is
the smallest possible substitution that keeps the actual scoring
algorithm 100% untouched — see `assets/js/adapters/score.adapter.js`.

## Conflict with Design System 2.1 (Gate 2, not resolved by this phase)

`design-system-2.1/references/score.md` states **MUST**: "Score value,
**band (ALTO/BOM/BAIXO)**, confidence, component breakdown (meters,
not gamified), explanation." Real production Score has **no band
concept at all** — confirmed by reading the actual authoritative
source, not inferred from UI labels (Gate 4's own instruction). The
reference's band requirement was approved against `facelift-
prototype-01`'s fictional demo data (its own file already discloses:
*"Full breakdown... currently exists for one demo seller only — a
prototype data-generation limitation"*), before this rebaseline
established what real production Score actually computes.

**This Wave does NOT invent a band.** Inventing threshold cutoffs
(e.g. "score>700 = ALTO") to satisfy the reference would be
fabricating new business logic — a direct violation of this Wave's
own "DO NOT REDESIGN THE SCORE LOGIC" principle and of Gate 24 ("do
not invent confidence [or, by clear extension, a classification] if
absent"). **Classified as a genuine Normative/Functional conflict
requiring a Design System Change Proposal in a future phase** — not
decided here. Confidence (the real "amostra" mechanism) and breakdown
(meters) ARE preserved faithfully — see `docs/SCORE-VISUAL-AUTHORITY.md`.
This is why Gate 44 requires `NORMATIVE COMPLIANCE` to be reported
SEPARATELY from `FUNCTIONAL PARITY` — they diverge here, honestly.
