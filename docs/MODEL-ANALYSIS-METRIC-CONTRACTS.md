# Model Analysis — Metric Contracts (PORTAL-NEXT-07.3, Gates 9-11, 36-42, 46-48)

Every contract below traced to production's own executable code (`rowsFromAgg`,
`aggregate`, `processBase02`), not assumed from the metric's name.

## Parcela Média (production label: "Média Parcela" / "Média de parcela") — Gate 9, 36, 40

```
MEANS:        average PMT (installment PAYMENT VALUE, in R$) per
             financing contract — NOT the number of installments.
NUMERATOR:      pmtSum = sum of fin.pmt across eligible fins records
              for the model/family (Novos only).
DENOMINATOR:       pmtQtd = COUNT of fins records where fin.pmt > 0.
ELIGIBLE POPULATION:  only records with pmt > 0 -- a record with pmt=0
                    (no Base03 match, or Base03 didn't carry a PMT
                    value) is excluded from BOTH numerator and
                    denominator, not treated as a R$0 data point.
ZERO/NULL:              if pmtQtd is 0 (no eligible record),
                       result is 0 -- distinguishable in the UI by
                       showing "R$ 0" only when the model genuinely
                       has 0 eligible contracts, same convention as
                       every other averaged metric in this module.
ROUNDING:                    money() -- floor toward zero, 0 decimals
                           (Dashbi's own money(), NOT Coparticipado/
                           Gestão's rounding convention -- already
                           documented as a real per-module difference
                           in docs/DASHBI-KPI-CONTRACT.md).
SOURCE FIELD:                    fin.pmt, itself sourced from Base03
                                "Op Fin - PMT (R$)" / "PMT" /
                                "Valor Parcela" (processBase02, line
                                3352) -- 0 if no Base03 match.
FORMULA LOCATION:                    rowsFromAgg (origin/main lines
                                    3193-3203) -- pmtMed = pmtQtd ?
                                    pmtSum/pmtQtd : 0.
```

## Prazo Médio (this IS "Média de Parcelas" — Gate 10, 37, 41)

**Production does not have two separate metrics for "average installment count."**
Confirmed by reading every metric box/column in `renderModelos()`: there is exactly
one such metric, internally named `parcelasMed`, labeled "Prazo Médio" wherever it
appears (family miniGrid and per-model table alike), formatted as `${num(v,1)}x`
(one decimal + "x" suffix, e.g. "24,0x") — i.e. an average **count** of
installments, displayed as a multiplier, which is exactly what "Média de Parcelas"
would mean. There is no second, differently-labeled metric for this concept anywhere
in the file. Gates 10/37's warning not to confuse "Quantidade média de parcelas"
with "Parcela média em R$" is already resolved structurally: those are two different
internal fields (`parcelasMed` vs `pmtMed`) with two different labels ("Prazo Médio"
vs "Média Parcela") — production never conflates them, and neither does this
restoration.

```
MEANS:        average number of installments (contract term) per
             financing contract.
NUMERATOR:      parcelasSum = sum of fin.parcelas across eligible
              records.
DENOMINATOR:       parcelasQtd = COUNT of records where
                  fin.parcelas > 0.
ELIGIBLE POPULATION:  only records with parcelas > 0 (same exclusion
                    rule as Parcela Média -- no Base03 match means
                    excluded, not zero).
ROUNDING:                    num(v, 1) -- 1 decimal place, "x" suffix
                           appended by the caller, not by num()
                           itself.
SOURCE FIELD:                    fin.parcelas, sourced from Base03
                                "Op Fin - Quantidade Parcelas" /
                                "Quantidade Parcelas" / "Parcelas".
FORMULA LOCATION:                    rowsFromAgg -- parcelasMed =
                                    parcelasQtd ?
                                    parcelasSum/parcelasQtd : 0.
```

## Balão Médio (production label: "Valor Médio Balão") — Gate 11, 38, 42

```
MEANS:        average balloon PAYMENT VALUE (R$), among ONLY the
             contracts that actually have a balloon (balaoValor > 0)
             -- NOT averaged across all financing contracts in the
             model, and NOT the balloon PMT's relation to the
             regular PMT.
NUMERATOR:      balaoValorSum = sum of fin.balaoValor across records
              where balaoValor > 0.
DENOMINATOR:       balaoValorQtd = COUNT of records where
                  balaoValor > 0.
MULTIPLE BALLOONS:    the data model has exactly one balaoValor field
                    per financing contract (one Base03-matched row
                    per contract, via chooseBestB03Row's own
                    single-best-candidate selection) -- there is no
                    "multiple balloons per contract" concept in
                    production; each contract contributes at most one
                    balaoValor to the sum.
ZERO/NULL:              contracts with balaoValor = 0 (Linear, or
                       Balão flag never set) are correctly EXCLUDED
                       from both sum and count -- they do not drag
                       the average toward zero. If balaoValorQtd is
                       0 (no balloon contracts for that model), result
                       is 0.
ROUNDING:                    money().
SOURCE FIELD:                    fin.balaoValor, sourced from Base03
                                "Op Fin - Balão PMT (R$)" / "Balão
                                PMT" / "Balao PMT" -- 0 if no Base03
                                match. The SAME field also drives the
                                BALÃO plan-classification flag
                                (isFinBalao: balaoValor > 0) --
                                Balão Médio's population is therefore
                                EXACTLY the set of contracts already
                                classified as BALÃO elsewhere in this
                                module, not a separately-defined
                                population.
FORMULA LOCATION:                    rowsFromAgg -- balaoMed =
                                    balaoValorQtd ?
                                    balaoValorSum/balaoValorQtd : 0.
```

## Qtd Linear / Qtd Balão / Qtd Reversão — Gate 12, 13, 39

Counts, not derived from a different population than the plan-classification
tables elsewhere in this module. `compModelo`'s `linearQtd`/`balaoQtd` (used by the
per-model table) are populated in `aggregate()` via `isFinLinear(r)?1:0` /
`isFinBalao(r)?1:0` — the exact same classifier functions `planRowsByModel` uses for
its own Linear/Balão counts, scoped to the same `dept==="Novos"` + model filter.
These are the same number computed two different ways (one via `aggregate()`+`rowsFromAgg`,
one via a direct `.filter().length`) — confirmed identical by construction, not by
assumption; the completeness restoration golden fixtures below assert this equality.
`reversaoQtd` at the model-table level is computed inline in `modelRowsUnified`
itself (`.filter(r=>r.dept==="Novos" && r.modelo===model && isFinReversao(r)).length`)
— same classifier again.

## Presentation decision: no card+modal reproduction (Gate 23-26, 49-51)

Production's own current UI (`renderModelIndicatorsCards`/`openModelDetailModal`)
shows only 3 of the 18 per-model fields by default (Volume/Financiada/Penetração)
and hides the other 15 behind a "Ver Detalhes" modal per model — its own source
comment explains this was a deliberate response to the same "18 columns don't fit"
problem this Wave's Gate 24 anticipates. **V2 does not reproduce the card+modal
shape.** Reason: the actual Design System authority for dense data in this whole
engagement, `design-system-2.1/references/data-table.md`, states plainly "Table
remains table — MUST NOT auto-convert rows into cards" — a rule already followed by
every prior module (Score/Coparticipado/Gestão/Dashbi's own store/seller/Ranking/
Novos-por-Loja tables). Converting the per-model data to cards would contradict that
standing rule for the sake of matching production's own (different, disclosed)
choice. Instead: a single wide table, sticky first column (`Modelo`), horizontal
scroll (`.dbTableWrap`, same pattern already used everywhere in Dashbi), grouped
column headers (Volume/Financeiro/Parcelamento/Planos — presentational grouping
only, no new business category, per Gate 50) — same completeness (all 18 fields, 0
removed) with a materially different, already-approved interaction shape. This is a
disclosed, deliberate adaptation, not an oversight — flagged per Gate 49's "IF ORDER
CHANGES... HUMAN REVIEW: REQUIRED" provision, applied here to the presentation-shape
decision as well: **HUMAN REVIEW REQUIRED** on whether this table-vs-card choice
matches expectations, alongside the metric semantics themselves.

**Superseded by PORTAL-NEXT-07.4**: the wide-table-with-horizontal-scroll decision
above was rejected by human UAT and replaced with a primary-row + inline
"+ Detalhes" pattern — see `docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md` for the current
authority. This section is kept for its historical reasoning (why cards were
rejected; that reasoning still holds), not as a description of the current UI shape.

## Qtd Subsidiado / Qtd Coparticipado at the model level (PORTAL-NEXT-07.4.1)

Human UAT on the 07.4 primary+detail experience asked for these two counts inside
the per-model Planos detail group, alongside the already-present Qtd Linear/Qtd
Balão/Qtd Reversão. Traced before adding anything (Gates 0-7 of that Wave):

```
SOURCE:        aggregate()'s own compVals object (already extracted
              byte-identical since PORTAL-NEXT-07) computes
              coparticipadoQtd/subsidiadoQtd on the SAME compModelo
              aggregation as linearQtd/balaoQtd -- same population
              (dept==="Novos", same model), same mutually-exclusive
              classifiers (isFinSubsidiado/isFinCoparticipado/
              isFinBalao/isFinLinear/isFinReversao).
WHY NOT ALREADY THERE:    production's own modelRowsUnified (byte-
                        identical, unchanged) simply doesn't pick
                        those two fields out into the row object it
                        returns -- confirmed by direct source read,
                        not an extraction gap. This is a real,
                        disclosed production omission at that
                        specific call site, not a V2 mistake.
V2 SOURCE:                    NOT a new extraction. Read from
                             planRowsByModel(results, currentFamily)
                             -- already extracted, already called one
                             section below in the same page, matched
                             to the model-indicators row by Modelo.
                             A model absent from planRowsByModel (not
                             in FAMILY_MODELS' static list) shows 0
                             for both, the same way it already has no
                             row at all in "Quantidade por tipo de
                             plano / Modelo".
RECONCILIATION PROVED:               golden fixture
                                    model_analysis_parcelamento_completo
                                    extended with 1 real Subsidiado
                                    contract (OUTLANDER HPE-S) and 1
                                    real Coparticipado contract
                                    (OUTLANDER SIGNATURE). Confirmed
                                    in a real browser: OUTLANDER
                                    HPE-S Financiamentos=4, Subsidiado
                                    1 + Reversão 0 + Coparticipado 0 +
                                    Balão 0 + Linear 3 = 4. OUTLANDER
                                    SIGNATURE Financiamentos=2,
                                    Subsidiado 0 + Reversão 0 +
                                    Coparticipado 1 + Balão 1 +
                                    Linear 0 = 2. 0 double counting in
                                    either direction.
ORDER:                                    Subsidiado, Reversão,
                                        Coparticipado, Balão, Linear,
                                        Balão Médio -- official
                                        classification priority, per
                                        explicit human preference,
                                        not production's own (absent)
                                        field order.
```

## Entrada Qtd removed from the UI (PORTAL-NEXT-07.4.1)

Confirmed (again, same conclusion as 07.3's own audit): `entradaQtd` was never a
production-visible metric — it is `modelExtraMetrics`'s internal count of
Entrada-eligible financing records, the denominator `entradaMed` divides by. Human
UAT asked for it to not be shown. Removed from `MODEL_TABLE_COLUMNS` (a
presentation-only array) — the field itself is untouched on the row object and
still feeds `entradaMed`/`entradaPct` exactly as before (both re-verified unchanged
via the 26/26 golden-fixture re-run).
