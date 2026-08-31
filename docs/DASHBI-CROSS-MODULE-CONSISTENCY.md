# Dashbi Cross-Module Consistency (Gates 6, 36, 46, 106-109, 128-129)

## Gate 6 — Dashbi vs. Análise F&I functional domain comparison

| Rule | Dashbi | Análise F&I (Gestão) | Same/Different |
|---|---|---|---|
| Plan classification priority | SUBSIDIADO>REVERSÃO>COPARTICIPADO>BALÃO>LINEAR | SUBSIDIADO>REVERSÃO>COPARTICIPADO>BALÃO>LINEAR | **SAME** — both source comments explicitly cross-reference each other ("igual a planTypeFromFields() do módulo Análise F&I do Grupo" appears verbatim in Dashbi's own source) |
| Data architecture | 3-base crossing (Base01×02×03, fuzzy match by name/CPF/variants) | 1 worksheet, grouped-row inheritance | **DIFFERENT** — genuinely different real architectures, not unified |
| EXCLUDED_SELLERS | same 9 names | not present in Gestão (different exclusion mechanism: EXCLUDE_MODALIDADE) | **DIFFERENT MECHANISM**, but the 9-name Set itself is shared with Score/Coparticipado |
| Historical/Nova date-cutoff format split | YES (2026-06-01) | NO (not present in Gestão) | **NOT PRESENT** in Gestão — Dashbi-specific |
| Model Analysis / Entrada metrics | YES, Novos-only | NOT PRESENT (confirmed absent, docs/GESTAO-KPI-CONTRACT.md) | **NOT PRESENT** in Gestão |
| FECHAMENTO | YES (isClosedMonthPeriod) | NOT PRESENT (confirmed absent, docs/GESTAO-KPI-CONTRACT.md) | **NOT PRESENT** in Gestão |
| Share threshold semantic color | YES (40%, `pctPenetracao`) | NOT PRESENT | **NOT PRESENT** in Gestão |

**Safe shared functions**: none were literally shared/reused as code — each module has its OWN independently-extracted copy of `modeloPadrao`, plan classification, `EXCLUDED_SELLERS`, etc. Consistency was PROVED per-Wave by independent extraction + fixture comparison, never assumed and never refactored into a shared library this Wave (Gate 39: "establish a safe future architecture, not perform an uncontrolled rewrite").

## Gate 46, 106, 128 — Plan priority cross-module proof

A synthetic dataset with a record satisfying SUBSIDIADO + COPARTICIPADO + BALÃO signals simultaneously was run through all 3 modules' own extracted classification engines (each module's own `priority_collision` golden fixture):

```
DASHBI:                    SUBSIDIADO (tests/fixtures/dashbi-fixtures.json,
                          case priority_collision — verified via
                          tests/dashbi-parity-test.py)
ANÁLISE F&I (Gestão):         SUBSIDIADO (tests/fixtures/gestao-fixtures.json,
                             case priority_collision)
COPARTICIPADO:                  SUBSIDIADO (tests/fixtures/coparticipado-
                              fixtures.json, case priority_collision)
SAME BUSINESS UNIVERSE:            YES — all three implement the identical
                                 documented priority rule (confirmed by
                                 source comments cross-referencing each
                                 other, not just coincidental agreement)
EXPECTED EQUALITY:                    YES
RESULT:                                  MATCH — 0 unexplained difference
```

## Gate 46 (continued) — a real, disclosed, NOT-unified difference: B3/B03 tiebreak rule

```
COPARTICIPADO's chooseB3:    ties broken by MOST RECENT contract date
                            (explicit date comparison in the sort)
DASHBI's chooseBestB03Row:      ties broken by ARRAY ORDER (JS
                               Array.sort is stable per spec; no date
                               comparison exists in scoreB03PlanRow or
                               chooseBestB03Row)
SAME BUSINESS UNIVERSE:               NO — different real production
                                    files, independently authored,
                                    genuinely different tiebreak
                                    mechanisms
EXPECTED EQUALITY:                       NO
RESULT:                                     Preserved as a documented
                                          difference (Gate 14: "if
                                          different, preserve
                                          difference and document
                                          why") — NOT normalized to
                                          match Coparticipado's rule.
```

## Gate 107, 109, 129 — KPI-level (NOT) cross-module equality

Vendas/Financiamentos/Produção/Receita/Share equality between Dashbi and Gestão was **NOT tested and is NOT claimed** — the two modules read from different real data universes (Dashbi: Base01×02×03; Gestão: a single FANDI operational extract) with different real column contracts and different real business scopes. Requiring numeric equality between two modules that consume genuinely different source data would be a **false equality** (Gate 80's own warning) — this was recognized and avoided, not overlooked.

## Gate 108 — Grupo = Novos + Seminovos?

Within Dashbi itself, `kpiMetricsFor(results, 'Grupo')` filters nothing (`deptView === "Grupo" ? results.sales : ...`), while `'Novos'`/`'Seminovos'` filter `r.dept===deptView`. Since every real record has exactly one `dept` value (`Novos` or `Seminovos`, resolved by `deptFromBase01`/`deptFromBase02`, never both/neither), **Grupo does reconcile as Novos+Seminovos by construction** for this module — verified via the `multi_loja_vendedor` fixture (Grupo vendas=4 = Novos vendas=3 + Seminovos vendas=1). This is a proved relationship, not an assumed one (Gate 27/108's own caution against presuming it).
