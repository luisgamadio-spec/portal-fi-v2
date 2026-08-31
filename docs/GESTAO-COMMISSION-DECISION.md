# COMMISSION BUSINESS AUTHORITY — DECIDED (PORTAL-NEXT-06.1 Gate 2)

```
STATUS:        HUMAN DECIDED (PORTAL-NEXT-06.1, human UAT feedback on
              PORTAL-NEXT-06)
AUTHORITY:        SPF EXTRA × 70%
SCOPE:               Gestão (Análise F&I do Grupo) / Comissão Líquida
                  SPF EXTRA — this metric specifically, nowhere else.
CONFIGURABLE:           NO — fixed and rigid for this metric. Do not
                      replace with spf_liquido_percentual or any other
                      configurable parameter used by another module.
```

**Affected surface**: the "Comissão Líquida SPF EXTRA" KPI card and its breakdown table's "Comissão Líquida 70%" column, on the Gestão (Análise F&I do Grupo) screen. Nothing else in Gestão is affected — see `docs/COMMISSION-RULE-MAP.md` for the full investigation.

The two options below are kept as a historical record of the investigation that led to this decision — **Option A is now the authoritative rule for this metric**; Option B is preserved as evidence that a second, configurable mechanism genuinely exists elsewhere (Salários/Comissões' `commissionCalc()`), not as a governing rule for Gestão's SPF Extra commission. Do not delete this record when reading it as "resolved" — it documents why Option B does NOT apply here, which matters if this decision is ever revisited.

## Option A

```
RULE:                a literal 70% (0.70), hardcoded inside Gestão's
                    own buildSpfExtraAnalysis() function.
FORMULA:               comissao = valorSpfExtra * 0.70
WHERE CURRENTLY USED:      modules/analise-fi-grupo.html (origin/main,
                          lines 2159/2167) — this is what production
                          shows TODAY, right now, on this exact card.
SYNTHETIC EXAMPLE RESULT:      Total SPF EXTRA = R$ 10.000,00 ->
                              Comissão Líquida SPF EXTRA = R$ 7.000,00
                              (tests/fixtures/gestao-fixtures.json,
                              case "spf_extra_commission" — verified via
                              the golden parity harness,
                              tests/gestao-parity-test.py)
```

## Option B

```
RULE:                spf_liquido_percentual, a live business parameter
                    read from master_portal_config (Master Config
                    panel), currently believed to equal 70 but changeable
                    by a MASTER at any time without a code deploy.
FORMULA:               comissao = valorSpfExtra * (cfgNum('spf_liquido_
                      percentual') / 100)
WHERE CURRENTLY USED:      assets/js/portal-app.js:commissionCalc()
                          (origin/main, lines 111-131), as one input to
                          the real, live, multi-tier seller/analyst/
                          manager commission engine — used by Comissões/
                          Salários screens, NOT by Gestão.
SYNTHETIC EXAMPLE RESULT:      Cannot be computed from a Gestão-only
                              fixture — this formula needs the full
                              commissionCalc() context (role class,
                              share, retorno, faixa tier), which Gestão's
                              own data model does not carry. If the
                              config value stayed at 70, the SPF-portion
                              of the result would numerically match
                              Option A's R$ 7.000,00; if an admin
                              changes the config, it would diverge, and
                              Gestão's card (if left on Option A) would
                              NOT reflect that change.
```

## Difference

Both options currently produce the same number (70%) for the one card in question, because Gestão's hardcoded literal happens to match the SPF percentage `commissionCalc()` reads from a config table today. They are not the same MECHANISM: Option A is frozen at 70% until someone edits Gestão's source code; Option B tracks whatever a MASTER sets in the live Config panel. **If the config value ever changes, the two will silently disagree** — and there is no way for this Wave to know, from a static/local-fixture inspection, whether that config parameter has already drifted from 70 in the real live database, since 0 backend calls are made this Wave (Gate 31).

## Gestão surfaces affected

"Comissão Líquida SPF EXTRA" KPI card; "Comissão Líquida 70%" column in the SPF Extra breakdown table. Two data points out of Gestão's full surface. "Total SPF EXTRA" (the raw, pre-multiplier value) is NOT affected and is migrated as ordinary functional parity.

## Salários/Comissões surfaces affected

Not investigated (Salários/Comissões module itself is out of scope this Wave, Gate 118) — noted only because `commissionCalc()`, Option B's real engine, lives there. No Salários/Comissões UI is touched or claimed migrated by this decision.

## Decision

**HUMAN DECIDED (PORTAL-NEXT-06.1): Option A.**

`Comissão Líquida SPF EXTRA = Total SPF EXTRA × 70%`, fixed and rigid, not configurable, for this metric specifically. The human explicitly confirmed the synthetic example already in this document (R$ 10.000,00 → R$ 7.000,00) as authoritative and instructed that 70% must **not** be generalized to other commissions, and that Salários/Comissões must **not** be altered based on this decision — Option B's `spf_liquido_percentual` mechanism remains real and unaffected, it simply does not govern this metric.

V2's "Comissão Líquida SPF EXTRA" card and column are no longer marked BLOCKED — the existing byte-identical `valor * 0.70` computation (already present in `assets/js/adapters/gestao.adapter.js`'s `buildSpfExtraAnalysis`, unchanged) is now reported as ordinary functional parity. No second formula was introduced — the literal 70% logic already extracted from production is the one now authorized to compute and display this metric (Gate 3's own "não criar segunda fórmula" instruction).

## Rounding audit (PORTAL-NEXT-06.1 Gate 4)

The formula itself (`comissao = valor * 0.70`) never rounds — rounding happens only at display time, in `money()`'s `toLocaleString('pt-BR', {maximumFractionDigits:0})`, which is a pure formatting concern (Gate 106: raw/display separation — the formatter never feeds back into the stored/compared value). Verified against 5 fixtures (`tests/fixtures/gestao-fixtures.json`, `tests/gestao-parity-test.py`, all PASS):

| SPF Extra (raw) | Comissão (raw, unrounded) | Comissão (displayed, `money()`) |
|---|---|---|
| R$ 0,00 | 0 (row excluded — production requires value > 0) | R$ 0,00 |
| R$ 100,00 | 70 | R$ 70 |
| R$ 1.000,00 | 700 | R$ 700 |
| R$ 10.000,00 | 7.000 | R$ 7.000 |
| R$ 12.345,67 | 8.641,969 | R$ 8.642 |
