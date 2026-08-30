# Coparticipado Extraction Trace (Gate 58)

## Production source truth (Gate 3-4)

```
Production source files:     modules/coparticipado.html (portal-
                             financiamento-brabus-secure)
Production SHA (file blob):    f729c40aaec048f889693f9993af335e0c0526aa
                             (git rev-parse origin/main:modules/
                             coparticipado.html — PROVED byte-identical
                             to live production this Wave via direct
                             HTTPS fetch + git hash-object comparison,
                             same method as PORTAL-NEXT-03.1/04)
Repo commit (origin/main):       2f17eb2341c5cc14aa8710aa044103002ca572a9
                             (unchanged since Gate 0's baseline — no
                             rebaseline needed, re-checked end of Wave)
Local clone divergence:        CONFIRMED divergent (local blob
                             2cdb3e3... != origin/main blob above) —
                             everything below was read exclusively via
                             `git show origin/main:...`, never the
                             local clone.
Shared adapter file:            assets/js/score-coparticipated-secure-
                             adapter.js, blob 6f2c79b5737e993f02e731
                             da20c0bc7bb857130b (origin/main) — read
                             for completeness (Gate 4), NOT used this
                             Wave (0 backend, RPC-only file).
Critical function/constant names: EXCLUDED_SELLERS, MODELO_ALIAS_ERP,
                             classifyPlan, processFins, processSales,
                             matchB3/chooseB3/scoreB3/situacaoScoreB3/
                             closenessScoreB3, calcCoparticipacaoDetalhe,
                             findTaxaCopart, buildVendors, buildB3Index
                             (34 functions + 2 constants total, full
                             list below)
Extraction method:              two INDEPENDENT programmatic
                             extractions off the same source (Python,
                             paren/brace-balanced, string/template-
                             literal-aware scanning — not hand-
                             retyped): one assembled into the product
                             adapter (dependency order), one assembled
                             into the golden reference (alphabetical
                             order, separate script/wrapper) — see
                             docs/COPARTICIPADO-ENGINE-AUDIT.md and the
                             "Independent re-extraction" section below.
```
A future session can reproduce all of this independently:
`git show 2f17eb2341c5cc14aa8710aa044103002ca572a9:modules/coparticipado.html`
against `portal-financiamento-brabus-secure` — no dependency on this
conversation's memory.

## Function map (Gate 58)

All 34 functions below are byte-identical extractions (verified by
programmatic string-containment check both ways: adapter vs. an
independently re-pulled copy off source — 0 mismatches). None were
retyped, reformatted, or "cleaned up" (Gate 59).

| SOURCE | TARGET | Behavior change | Test | Parity |
|---|---|---|---|---|
| `classifyPlan(b3row)` | `coparticipado.adapter.js` → `.classifyPlan` | NONE | `tests/coparticipado-parity-test.py`, 22/22 fixtures | PASS |
| `processFins(rows,b3idx,sales)` | same file → `.processFins` | NONE | same | PASS |
| `processSales(rows)` | same file → `.processSales` | NONE | same | PASS |
| `matchB3/chooseB3/scoreB3/situacaoScoreB3/closenessScoreB3` | same file (internal, used by processFins) | NONE | same (priority_collision, duplicate_b3, date_boundary_tiebreak fixtures specifically exercise these) | PASS |
| `calcCoparticipacaoDetalhe(r)` | same file → `.calcCoparticipacaoDetalhe` | NONE | same (modelo_sem_taxa fixture exercises the `ok:false` path) | PASS |
| `findTaxaCopart(modelo)` | same file → `.findTaxaCopart` | NONE | same | PASS |
| `buildVendors(rows)` | same file → `.setVendors` | NONE | same | PASS |
| `buildB3Index(rows)` | same file → `.buildB3Index` | NONE | same | PASS |
| `isCoparticipadoValido/isTCcoparticipado/isSituacaoCoparticipadoValida` | same file (internal) | NONE | same (situacao_paga/situacao_faturada/situacao_invalida fixtures) | PASS |
| `rowHasExcluded(row)` + `EXCLUDED_SELLERS` | same file (internal + constant) | NONE — identical Set to the one Score/portal-app.js already use | same (vendedor_excluido fixture) | PASS |
| `getCol/getTC/getIF/planText/getSituacaoB3/normalizeText/normalizeClient/onlyDigits/asNumber/asRate/taxaKey/vendorFromRow/deptFin/deptVenda/familiaModelo/modeloPadrao/parseDate/valorFinB3` | same file (internal helpers, 17 functions) | NONE | same (exercised indirectly by every fixture) | PASS |
| `MODELO_ALIAS_ERP` | same file (constant) | NONE | same | PASS |
| `money(v)/num(v,d)/pct(v)/iso(d)/dateIn(r,start,end)/planBadge(p)` | same file → `.money/.num/.pct/.iso/.dateIn/.planBadge` | NONE — display/filter helpers, added Gate 20-27 for the real UI (table formatting, Loja/Departamento/date filters); byte-identical, same discipline as the classification engine | verified via real-browser Loja/Departamento/date filter interaction (docs/HUMAN-UAT-COPARTICIPADO.md script) | PASS (manual, no dedicated automated fixture — pure formatting, no classification/sort/total impact) |

## Independent re-extraction (Gate 13's "not hand-calculated" requirement)

`tests/fixtures/_coparticipado-reference.js` is NOT a copy of
`coparticipado.adapter.js`. It was built by a second script
(`extract_reference.py`, scratchpad) using its own paren/brace-
balancing implementation, its own function ordering (alphabetical,
not the adapter's dependency order), and its own wrapper/global name
(`window.NX_COPARTICIPADO_REFERENCE` vs. `window.NX_COPARTICIPADO_
ADAPTER`). `tests/coparticipado-parity-test.py` loads BOTH in separate
Playwright pages, runs all 22 fixtures through the reference to
produce goldens (saved fresh to `tests/fixtures/coparticipado-golden-
output.json` every run — never hand-edited), then runs the same
fixtures through the adapter and diffs. 22/22 exact match.

Sanity spot-check against the documented rules (not just "both sides
agree", which could mask a shared extraction bug): `priority_collision`
resolves to `SUBSIDIADO` (not BALÃO or COPARTICIPADO, proving the
priority order), `duplicate_b3` resolves to the `PAGA` candidate over
the `CANCELADO` one, `modelo_sem_taxa` returns `coparticipacaoDetalhe.
ok===false` with the exact production message, `coparticipado_valido`'s
computed `coparticipacao` value matches `valorFinanciado × rebateTotal
× parteBrabus` arithmetic by hand (R$150.000 × 5% × 50% = R$3.750) —
see docs/COPARTICIPADO-ENGINE-AUDIT.md.

## Functions/features intentionally NOT migrated (Gate 57/62)

```
FEATURE:               "Diagnóstico" tab (renderVendorAlerts,
                      collectUnknownVendors, isVendorRegisteredName,
                      isVendorKnownAnyType)
WHAT IT DOES:            flags sellers appearing in Base01/02/03 who
                      are not registered (or registered under a
                      different TIPO) in the vendor registry —a data-
                      quality/admin diagnostic, not a financial
                      classification.
REASON NOT MIGRATED:       needs the REAL vendor registry (backend-
                      loaded in production); this Wave is 0 backend,
                      fixture-only (Gate 8/25). Orthogonal to the
                      classification/crossing/exclusion/priority/
                      filter/sort surface this Wave scopes.
FUTURE WORK:              whichever Wave adds real backend/vendor-
                      registry integration.

FEATURE:               export to Excel (exportarCoparticipados,
                      exportarSubsidiados)
WHAT IT DOES:            downloads a formatted .xlsx of the current
                      filtered view via xlsx-js-style.
REASON NOT MIGRATED:       DEFERRED DEPENDENCY — needs a real file-
                      download flow and the xlsx-js-style library;
                      same 0-file-I/O boundary already established for
                      the Base01/02/03 raw Excel parsing deferral (see
                      docs/COPARTICIPADO-ENGINE-AUDIT.md's "Deferred"
                      section).
FUTURE WORK:              same admin-tooling Wave as the raw Excel
                      parsing deferral.

FEATURE:               openSellerDetails/openScoreDetails/toggleScore
                      Details/renderScore/scoreDetailHtml/financing
                      DetailsHtml + the embedded stale calcScores()/
                      SCORE_WEIGHTS/PLAN_WEIGHT inside coparticipado.
                      html itself, plus the #novos/#score sections and
                      their CSS (.sellerScoreGrid/.scoreCircle/etc.)
WHAT IT DOES (in the    a SEPARATE, OLDER, VESTIGIAL "Score dos
file, but not live):    Vendedores" feature, once apparently shown in
                      this same page (CSS comment "V1.05 — Visual
                      premium Score dos Vendedores").
REASON NOT MIGRATED:       CONFIRMED DEAD CODE — verified by reading
                      the real page markup (Gate 3-4): the only tabs
                      wired into `<div class="tabs" id="tabs">` are
                      'copart' (Coparticipados/Subsidiados) and
                      'diagnostico'. There is no tab or route that
                      ever shows `#novos` or `#score`; `renderNovos()`
                      is a literal no-op (`el.innerHTML=''`). No user
                      of production today can reach this code through
                      the UI. Not migrated, same finding pattern as
                      Score's own stale-code discovery (PORTAL-NEXT-04,
                      docs/SCORE-ENGINE-AUDIT.md Gate 11) — this
                      module also contains its own older, unrelated
                      calcScores() implementation (PLAN_WEIGHT-based,
                      not the confidence-dampened version already
                      extracted for the real Score module) which was
                      correctly identified and left untouched.
FUTURE WORK:              none anticipated — if this code is truly
                      dead in production, the correct future action is
                      likely deletion at the source, not migration; not
                      this Wave's decision to make.

FEATURE:               row-level drill-down / detail modal for
                      Coparticipados or Subsidiados table rows
WHAT PRODUCTION HAS:       NOTHING — verified by direct source read.
                      Neither `renderCopa` nor `renderSubsidiados`
                      attaches any click handler or modal trigger to
                      its `<tr>` elements.
REASON NOT MIGRATED:       NOT APPLICABLE, not a scope cut. The row
                      already is the finest real granularity (one
                      financing operation per row, with client/model/
                      values/situação/date/chassi all visible inline).
                      Inventing a drill-down modal here would be
                      exactly the kind of new business/UX surface
                      Gate 59 forbids.
```

## No-cleanup-drift confirmation (Gate 59)

The extraction was verified via direct string comparison against the
source (docs/COPARTICIPADO-ENGINE-AUDIT.md's method — the same
discipline as Score's), cross-checked a second time by an entirely
independent extraction script/ordering/wrapper (`_coparticipado-
reference.js`) landing on byte-identical function bodies. No formula
was simplified, no variable renamed, no scoring weight adjusted, no
rounding changed, no priority order touched, no filter predicate
altered. The two intentional additions beyond the 34 classification
functions — the `money/num/pct/iso/dateIn/planBadge` display/filter
helpers — are likewise byte-identical extractions from the same
source, not new formatting rules (Gate 60: raw/display separation
holds — none of these six functions is called anywhere inside the
classification/crossing/priority pipeline itself).
