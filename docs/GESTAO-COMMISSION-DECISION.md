# DECISION REQUIRED: COMMISSION BUSINESS AUTHORITY (Gate 22/86/155)

**Affected surface**: the "Comissão Líquida SPF EXTRA" KPI card and its breakdown table's "Comissão Líquida 70%" column, on the Gestão (Análise F&I do Grupo) screen. Nothing else in Gestão is affected — see `docs/COMMISSION-RULE-MAP.md` for the full investigation.

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

**PENDING HUMAN.**

Per Gate 86/155, this Wave does not recommend Option A or Option B — recommending "the newer/more sophisticated formula" or "the one that's currently in the file being migrated" are exactly the shortcuts this gate forbids without an independent, previously-approved business authority proving one is correct. Until a human decides, V2's "Comissão Líquida SPF EXTRA" card and column are rendered but explicitly marked **BLOCKED — HUMAN BUSINESS DECISION REQUIRED** in the UI (not computed and silently passed off as resolved parity, not left blank/fabricated with a placeholder number) — see `assets/js/gestao.js`.
