# Simulator Engine Discovery + Extraction (PORTAL-NEXT-08)

**Scope: DISCOVERY + ENGINE EXTRACTION + PARITY HARNESS only.** No
simulator UI was migrated or redesigned. No formula was changed,
simplified, or "improved." Novos and Seminovos were investigated
independently — no assumption that Novos rules apply to Seminovos.

## Production authority

Per this Wave's explicit instruction, the local working-tree clone is
NOT trusted as authoritative — `origin/main` is. `modules/
simulador-novos.html` genuinely diverges from the local clone (a
"MITWEEK" seasonal campaign card/screen, presentation/navigation only,
0 calculation relevance — verified via `git diff`).
`modules/simulador-seminovos.html`'s apparent hash difference turned
out to be a line-ending artifact only (`git diff` shows 0 lines).

```
NOVOS Production Source:      git show origin/main:modules/simulador-novos.html
                              (2f17eb2341c5cc14aa8710aa044103002ca572a9)
SEMINOVOS Production Source:      git show origin/main:modules/simulador-seminovos.html
                                  (same SHA)
Saved locally (0 further
production connection made
this Wave):                          PORTAL-NEXT-08/.source/simulador-novos-origin-main.html (3195555 bytes)
                                     PORTAL-NEXT-08/.source/simulador-seminovos-origin-main.html (1372425 bytes)
                                     + shared assets/js/simulador-base-loader.js,
                                    cash-conversion.js, fi-atendimento.js
```

The large file sizes are entirely embedded base64 product-photo/logo
image data inside `<script>` blocks (25 base64 occurrences, several
~245KB lines, one 702KB line) — 0 calculation relevance.

## Reality check vs. the brief's assumed pipeline

The brief assumed a single reconstructable pipeline ("model selection
→ campaign/condition lookup → sale value → entry value → financed
amount → term → coefficient → financial additions → installment").
Real production contains **9 independent calculation engines in
Novos** and **6 reachable + 2 confirmed-dead in Seminovos** — each
with its own rate table, entry-validation rule, and term set. This
was flagged to the human before extraction began (full-scope
extraction was explicitly requested and delivered).

## Gate 3 — Function inventory summary

Full function-by-function inventories (name, line range, purpose,
PURE/DOM-COUPLED, category) were produced for both simulators and are
preserved as this Wave's working record; the essential facts are
captured in the per-engine sections below and in the adapter files'
own header comments (each cites its exact source line ranges).

## Gate 2/22/49 — Dependency graph & shared-vs-independent classification

```
assets/js/simulador-base-loader.js    SB_LOADER.carregar/travarSubmodulo/
                                      linhasValidas — bridges to
                                     window.parent.simuladorGetBase(rpcName),
                                    byte-identical, used by both simulators'
                                   carregarBaseX() loaders. NOT extracted
                                  (0 backend this Wave, Gate 21) — every
                                 adapter uses the FALLBACK table exactly.
assets/js/cash-conversion.js          Pure, byte-identical, shared by both —
                                      extracted verbatim as
                                     cash-conversion.adapter.js.
assets/js/fi-atendimento.js               WhatsApp-to-analyst integration —
                                          not a calculation engine, not
                                         extracted.
Financiamento Campanha/Coparticipado
(base64 iframe, both simulators)          Confirmed BYTE-IDENTICAL (calc()/
                                          coefFor()/selectedModel(), PRAZOS,
                                         TX_COEF, MODELS all diff-identical
                                        except var/const and one telemetry
                                       line) — extracted ONCE as
                                      financiamento-campanha.adapter.js,
                                     shared by both.
Semestral Triton/Outlander campaign       FATOR_SEMESTRAL_TRITON=
                                          1.1045534653178353 and MESES=
                                         [6,12,18,24] confirmed shared
                                        (simulador-shared.adapter.js).
                                       Rebate data (rebateTotal/hpeShare/
                                      brabusShare per model) also
                                     identical. BUT the final formula
                                    genuinely differs (see below) — kept
                                   as two separate functions.
Shared pure helpers                        parseBRL, taxaInterna,
(simulador-shared.adapter.js)             baseInterna, faixaLinear,
                                          coefLinear, baseCalculoLinear,
                                         taxaPricePorIteracao, pct2,
                                        parsePctInput, formatPctInputValue,
                                       fmtDateBR, addMonths, diffMonthsAhead
                                      — all confirmed byte-identical via
                                     direct diff.
Antecipação (formula + table)              Confirmed byte-identical
                                           (source comment even says so:
                                          "Base COMPARTILHADA com o
                                         Simulador Seminovos") — kept as
                                        two independently-tested local
                                       copies rather than merged, to avoid
                                      touching the already-verified Novos
                                     adapter under this Wave's time
                                    constraints (documented, not hidden).
Descobridor de Taxa (formula)              Confirmed byte-identical (same
                                           CAD/REG/IOF_DISCOVER constants)
                                          — same "kept separate, documented"
                                         treatment as Antecipação.
Financiamento Linear (top-level table)     tabelaLinear/prazosLinear data
                                           values are identical between
                                          Novos and Seminovos — but
                                         Seminovos' copy is UNREACHABLE
                                        dead code (see below), so merging
                                       it has no product value.
Tradicional (Balão)                        Formula helpers shared
                                           (taxaInterna/baseInterna), but
                                          table VALUES and even table
                                         SHAPE differ: Novos has no
                                        vehicle-year dimension at all;
                                       Seminovos requires one
                                      (faixaAnoTrad). Genuinely
                                     independent engines.
Semestral/Anual (Periódico)                Formula identical, table values
                                           differ (48x taxa: 0.019 Novos vs
                                          0.0183 Seminovos). Independent.
Taxas Subsidiadas                          Formula identical, rebate% table
                                           values differ. In Novos, reachable
                                          and tested. In Seminovos, DEAD
                                         CODE (see below).
"Financiamento Seminovos" RATE_TABLE       Seminovos-exclusive — no Novos
                                           equivalent at all (year x
                                          entry-band lookup, its own
                                         pmt()/calcIOF() formula, 2.5%
                                        "seguro proteção" surcharge Novos'
                                       engines never apply).
Parcela Única                              Novos-exclusive — no Seminovos
                                           equivalent at all.
```

## Gate 33 — Confirmed dead code in Seminovos (not ambiguous — verified)

Two entire features exist in Seminovos' JavaScript (functions, event
wiring, even hundreds of lines of dedicated CSS) with **zero matching
markup anywhere in the production file**:

1. **Top-level "Financiamento Linear" tab** (`calcLinear()`,
   `tabelaLinear`, `prazosLinear`) — every DOM read/write inside it is
   defensively guarded (`if($(id))`/`if(!$('lResultados')) return;`),
   so it silently no-ops. The real, reachable "Linear" experience is
   exclusively the nested `#linearSeminovosFrame` RATE_TABLE iframe.
2. **"Taxas Subsidiadas"** (`calcSubsidiadas()`,
   `montaDadosSubsidiadas()`, the `openSubsidiadas` nav button,
   `showSubsidiadas()`) — `id="subsidizedScreen"` does not exist as an
   actual HTML element anywhere (only as a CSS selector target and in
   guarded JS, `document.getElementById('subsidizedScreen')` safely
   returning `null`). Clicking the nav button would close the menu and
   open nothing.

Both are kept in `simulador-seminovos.adapter.js` for Gate 3's
function-inventory completeness (and because their formulas/tables are
independently interesting/correct), but are **excluded from this
Wave's Gate 39 engine-parity requirement** — there is no reachable
production DOM path to verify them against. This is a verified fact
(direct absence-of-markup check), not an assumption.

## Gate 6/7 — Novos vs Seminovos comparison matrix

| Concept | Novos | Seminovos | Same? |
|---|---|---|---|
| Model/vehicle selection | Only in the shared Campanha iframe (exact-string match, `MODELS.find(m=>m.name===...)`, no normalization) and Semestral Triton (object-key lookup, no normalization) | Same Campanha iframe; Tradicional/RATE_TABLE key by **vehicle year band**, not model name | PARTIALLY |
| Vehicle value | `bem` (sale value) | `bem`/`valor` (sale value) | IDENTICAL concept |
| Entry / minimum entry | Varies by engine: 10% (Tradicional), dynamic-per-term (Periódico), 50% (Subsidiadas), 60% fixed campaign models, 0% floor (Linear) | Same shape, same numeric floors for the engines that exist in both (Tradicional 10%, Subsidiadas 50% — though Subsidiadas is dead code here) | Formula same, data same where both reachable |
| Financed amount | `Math.max(0, bem-entrada)`, everywhere | Same everywhere | IDENTICAL |
| Terms | 12/24/30/36/40/42/48 (Trad), 24/36/48 (Periódico), 25 fixed (Parcela Única), 12/18/24/30/36/42/48/60 (Linear), 1-60 free (Descobridor/Antecipação/Cash Conv), 12/15/18/24/30/36/48/60 (Subsidiadas), 6/12/18/24 (Semestral Triton), 12/18/24/36/48/60 (Campanha) | 12/24/30/36/40/42/48 (Trad), 24/36/48 (Periódico), 12/18/24/30/36/42/48/50/60 (RATE_TABLE — has 50x, Novos never does), 1-60 free (Descobridor/Antecipação), 6/12/18/24 (Semestral Triton), 12/18/24/36/48/60 (Campanha) | PARTIALLY — no universal term set |
| Rates/coefficients | Hardcoded FALLBACK tables, ACTIVE-loadable via SB_LOADER (ana Wave doesn't reproduce ACTIVE) | Same pattern for Tradicional/Antecipação/RATE_TABLE; Periódico/Linear/Subsidiadas/Semestral Triton are 100% hardcoded, no loader at all — a REAL, verified difference even within Seminovos itself | PARTIALLY |
| Fees baked into base | ADICIONAL 6.2305%+CAD 980+REG 339.67, IOF 3.21516% (Trad/Periódico); CAD 980+REG 339.67, IOF 0.38%+0.0082%/dia (Linear); FEES {cadastro 970, avaliação 699, registro 400}+seguro 2.5%+IOF (RATE_TABLE, Seminovos-only) | Same as Novos for Trad/Periódico/top-level-Linear (dead code); RATE_TABLE fees are Seminovos-exclusive, no Novos equivalent | PARTIALLY |
| Campaign rules | Shared Campanha iframe: 60% min entry (all current models), 4.11%/6.22% fee bracket by term ≤/>24 | Identical (byte-diff confirmed) | IDENTICAL |
| Installment formula | Price-system `saldo/fator` (Trad/Periódico); `baseCalculo*coefLinear` (Linear); flat `fin*coef` (Parcela Única/Subsidiadas); `pmt()` closed-form (RATE_TABLE, Seminovos); `financiado*FATOR/4` (Semestral Triton) | Same formulas where the same engine exists in both | Formula identical per engine; engines differ |
| Rounding | None mid-pipeline; only `Intl`/`toLocaleString` at display time (2 decimals) | Same | IDENTICAL |
| Validation/error states | Guard-clause + inline message, never `alert()` for calc errors, never throws | Same pattern | IDENTICAL |
| Cash Conversion | Independent tool, own 4 inputs, shared engine | Same, verified byte-identical | IDENTICAL |
| Result presentation deps | 1:1 DOM ids per engine, no shared component | Same pattern (different ids) | Structurally identical, not literally shared |

## Gate 49 — Can Novos and Seminovos share a common core engine?

**PARTIALLY.** The following are proven, evidence-based, safe to
share (and already implemented that way):

- The pure math helpers (`parseBRL`, `taxaInterna`, `baseInterna`,
  `faixaLinear`, `coefLinear`, `baseCalculoLinear`,
  `taxaPricePorIteracao`, `pct2`, `parsePctInput`,
  `formatPctInputValue`, `fmtDateBR`, `addMonths`, `diffMonthsAhead`) —
  `simulador-shared.adapter.js`.
- The Financiamento Campanha/Coparticipado engine (formula AND data,
  fully byte-identical) — `financiamento-campanha.adapter.js`.
- Cash Conversion (already a single shared production file) —
  `cash-conversion.adapter.js`.
- Two Semestral Triton/Outlander literal constants
  (`FATOR_SEMESTRAL_TRITON`, `MESES`) — in
  `simulador-shared.adapter.js`; the surrounding orchestration and the
  final `valorFinalVenda` formula are **not** shared (see below).

**NOT shareable — kept independent, with evidence:**

- Tradicional/Balão: different table shape (Seminovos adds a vehicle
  year-band key Novos has no concept of), different values, different
  `max` balloon-cap ratio (1.0 vs 0.7).
- Semestral/Anual: same formula, different rate values at 48x.
- Semestral Triton "final formula": **Novos** computes
  `valorFinalVenda = bem - rebateBrabus` (only Brabus' share of the
  rebate) **and** supports a per-model `entradaMinima` override
  (default 60%, e.g. Outlander at 70% via ACTIVE data); **Seminovos**
  computes `valorFinalVenda = bem - rebateTotal` (the full rebate,
  both Brabus+HPE shares) and hardcodes a flat 60% for every model,
  with no override mechanism at all. This was caught by directly
  diffing the two `renderStc()` bodies, not by assuming similarity —
  a genuine, real business difference that would have been silently
  destroyed by naive unification.
- "Financiamento Seminovos" RATE_TABLE engine has no Novos equivalent
  whatsoever (different lookup dimension — vehicle year × entry band,
  not model — different fee structure, a 2.5% "seguro proteção"
  surcharge no Novos engine applies).
- Parcela Única (Novos-only) and the reachable Taxas Subsidiadas
  (Novos-only, since Seminovos' copy is dead code) have no counterpart
  to compare against at all.

**Some additionally-identical-but-not-yet-merged pieces**, documented
honestly rather than silently duplicated: Antecipação (formula +
table), Descobridor de Taxa (formula), and the top-level Linear table
values are all byte-identical between the two files, but were kept as
independently-tested local copies in each simulator's own adapter
file rather than merged into the shared file, specifically to avoid
touching the already-verified Novos adapter under this Wave's time
constraints. A future Wave could merge these with no loss of
correctness — not done here because it wasn't necessary for parity,
only for code deduplication (Gate 22 explicitly: "Do not refactor yet
solely for cleanliness").

## Gate 9/13/14 — Rounding & money parsing

No engine applies mid-pipeline rounding to a currency value; every
`parcela`/`financiado`/etc. is carried as a full-precision float and
only rounded implicitly by `Intl.NumberFormat`/`toLocaleString` at
display time (2 decimals). The one exception: Cash Conversion's
`classificarResultado()` rounds to whole cents (`Math.round(x*100)`)
**only for the FINANCIAR/UTILIZAR/EQUIVALENTE comparison**, never for
the displayed figures themselves.

`parseBRL(s)` (shared, byte-identical): strips everything except
digits/comma/minus, strips thousands-separator dots, swaps decimal
comma for a dot, `Number(...)||0`. Blank/invalid input always becomes
`0`, never `NaN`/throws. The Campanha iframe uses a **different**
digit-only `cents()` parser (divides raw digits by 100, typical
input-masking style) — confirmed NOT the same algorithm as `parseBRL`,
though both are correct for their own UI's masking behavior.

## Gate 15/25 — Extraction architecture

```
assets/js/adapters/simulador-shared.adapter.js       shared pure helpers
                                                      + 2 shared constants
assets/js/adapters/cash-conversion.adapter.js            byte-identical
                                                          extraction
assets/js/adapters/financiamento-campanha.adapter.js          pure
                                                               re-derivation,
                                                              shared by
                                                             both sims
assets/js/adapters/simulador-novos.adapter.js                     9 pure
                                                                   engine
                                                                  functions
assets/js/adapters/simulador-seminovos.adapter.js                     8
                                                                       pure
                                                                      engine
                                                                     functions
                                                                    (2 dead-
                                                                   code, not
                                                                  parity-
                                                                 tested)
```

Every calculation function in production reads/writes DOM directly —
there is no pre-existing separation between math and DOM (Blocker #5,
confirmed again this Wave). Each adapter function is therefore a
**pure re-derivation** (Gate 25: no `document`/`window` dependency),
not a byte-identical copy — verified for behavioral fidelity (Gate 26)
against the real, unmodified, DOM-coupled originals, driven live in a
real browser against the saved `origin/main` HTML (Gate 27), with 0
network calls (loading each file as a top-level page structurally
forces `window.parent===window`, which makes `SB_LOADER` throw
immediately inside every `carregarBaseX()`, guaranteeing the
FALLBACK-only path with no mocking required).

## Gate 28/29 — Golden coverage

```
tests/simulador-novos-parity-test.py          40/40 (8 engines: Tradicional,
                                              Periódico, Parcela Única,
                                             Linear, Descobridor, Subsidiadas,
                                            Antecipação, Semestral Triton)
tests/simulador-seminovos-parity-test.py          24/24 (6 reachable engines:
                                                  Tradicional, Periódico,
                                                 LinearRateTable, Descobridor,
                                                Antecipação, Semestral Triton)
tests/simulador-campanha-parity-test.py               14/14 (shared engine,
                                                       driven against BOTH
                                                      simulators' own decoded
                                                     iframe copies independently)
tests/cash-conversion-parity-test.py                      11/11
tests/simulador-cross-product-test.py                        5/5 (Gate 30)
                                                              TOTAL: 94/94
```

Coverage per engine includes (per Gate 29): minimum valid entry,
exactly below/at/above minimum, small and large sale values, every
supported term where feasible, decimal/currency parsing, zero/blank/
invalid input, boundary values, and — for Cash Conversion — a
rounding-sensitive `EQUIVALENTE` case constructed to land exactly on
the cent-comparison boundary.

## Gate 39/40 — Numeric precision

All comparisons distinguish exact currency equality (parsed BRL string
vs. computed float, cent-level epsilon 0.005–0.02 depending on the
formatter's own rounding) from formatting equality — no case hides a
real mismatch behind a broad epsilon; every epsilon used is justified
by the display formatter's own precision (2 decimals for currency, 2
decimals for percentages).

## Gate 20 — Global state made explicit

Every mutable module-scope variable found in production (selected
model/term, cached ACTIVE-vs-FALLBACK tables, last antecipação result,
Cash Conversion state, various one-shot "base carregada" guards) is
now an explicit function **input** in the corresponding adapter
function — nothing is read from ambient global state.

## Gate 21/35/36 — Security / isolation

0 backend calls, 0 production calls made during this Wave's discovery
or testing (all reads were of locally-saved files; all test execution
ran against those local files or the local V2 adapters). Production
`modules/simulador-novos.html`/`modules/simulador-seminovos.html`: 0
diff (read-only references, never written to). Isolation baseline:
0-line diff across sibling worktrees.

## What was NOT done this Wave

- No Simulator UI was built or migrated.
- No formula was changed, simplified, or unified beyond what evidence
  proved was already identical in production.
- ACTIVE-base coefficient loading (Supabase RPC) was not reproduced —
  every table is the FALLBACK table exactly as it appears in source.
- The two confirmed-dead Seminovos engines (top-level Linear,
  Subsidiadas) were not "fixed" or removed — only documented.
