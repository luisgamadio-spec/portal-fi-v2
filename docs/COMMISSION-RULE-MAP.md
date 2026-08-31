# Commission Rule Map (Gate 20)

Every commission-related rule reachable from Gestão (`modules/analise-fi-grupo.html`, origin/main), located by direct source read — not retyped from memory.

## Rule A — `buildSpfExtraAnalysis()` hardcoded 0.70 (inside Gestão itself)

```
SOURCE FILE:        modules/analise-fi-grupo.html (origin/main, blob
                    d52cc9ada7fd1a373d84ff6ea894d85ffc58ad0d — confirmed
                    byte-identical local clone == origin/main == live
                    production, Gate 4)
FUNCTION/LINEAGE:      buildSpfExtraAnalysis(rows), lines 2135-2168
FORMULA:                 g.comissao = g.valor * 0.70   (per loja+departamento
                        bucket, line 2159)
                        return {...,comissao:total*0.70}   (grand total, line 2167)
                        0.70 is a LITERAL, not read from any config table.
USED BY GESTÃO:            YES — feeds exactly ONE card ("Comissão Líquida
                          SPF EXTRA", hint text "70% sobre o total SPF
                          EXTRA", render() lines 2407-2413) and one
                          breakdown table column ("Comissão Líquida 70%").
USED BY SALÁRIOS:              NOT INVESTIGATED — Salários/Comissões is out
                              of scope this Wave (Gate 118); not migrated,
                              not read for this map beyond confirming it is
                              a separate, untouched module.
OUTPUT AFFECTED:                  "Total SPF EXTRA" and "Comissão Líquida
                                SPF EXTRA" KPI cards, and the per-loja/
                                departamento SPF Extra breakdown table.
                                Nothing else in Gestão reads buildSpfExtra
                                Analysis's output (confirmed: grepped
                                every call site).
```

## Rule B — `commissionCalc()` multi-tier, config-driven (in `assets/js/portal-app.js`)

```
SOURCE FILE:        assets/js/portal-app.js (origin/main, blob
                    16f1d41d597af6ef12c6c14d4453579b6bdf7ef3 — LOCAL
                    CLONE IS DIVERGENT for this file (local blob
                    386249d...), read exclusively from origin/main;
                    confirmed origin/main == live production via direct
                    HTTPS fetch + git hash-object, Gate 4)
FUNCTION/LINEAGE:      commissionCalc(status, m, cls), lines 111-131 +
                      commissionSummaryFromBlocks/managerCommissionSummary
FORMULA:                 spfLiquido = (m.spf||0) * (cfgNum('spf_liquido_
                        percentual') / 100)   -- CONFIG-DRIVEN, fetched
                        from master_portal_config via RPC (cfgNum reads
                        MASTER_SECURITY_STATE.data, itself populated by
                        carregarParametrosPortal()'s
                        master_get_portal_config RPC — not a literal).
                        rentTotal = (m.retorno||0) + spfLiquido
                        faixa = role/share/return-tier lookup (also
                        config-driven: gerente_faixa_share_alto/baixo,
                        analista_faixa_share_alto/baixo, vendedor_faixa_*
                        — 6+ distinct config keys, none hardcoded)
                        comissaoPrincipal = rentTotal * faixa
                        comissaoTotal = comissaoPrincipal + comissaoSpf
USED BY GESTÃO:            NO — Gestão (analise-fi-grupo.html) never
                          calls commissionCalc, never loads portal-app.js,
                          never references cfgNum/MASTER_SECURITY_STATE.
                          Confirmed by grep: 0 occurrences of
                          "commissionCalc" in analise-fi-grupo.html.
USED BY SALÁRIOS:              YES (per module-registry.json's pre-
                              existing "salarios-comissoes" entry,
                              functionalSource: portal-app.js:
                              commissionCalc) — NOT investigated further,
                              out of scope (Gate 118).
USED IN PRODUCTION:               PROVED — this is the live commission
                                 engine used by the MASTER/Analista/
                                 Gerente/Vendedor commission views inside
                                 portal-app.js's own UI (Painel Master
                                 and related commission screens), confirmed
                                 by direct source read of its call sites
                                 (commissionSummaryFromBlocks,
                                 managerCommissionSummary, and the HTML-
                                 building functions around lines 1060-1550
                                 that render it).
```

## The actual relationship between Rule A and Rule B

They are **not two competing formulas for the same output.** Rule B's `spfLiquido` calculation is structurally the SAME CONCEPT as Rule A (a percentage applied to SPF revenue) — both currently evaluate to 70% in practice — but:

- Rule A hardcodes `0.70` as a literal inside Gestão's own local aggregation function, used ONLY for Gestão's own "Comissão Líquida SPF EXTRA" card.
- Rule B reads the equivalent percentage from `master_portal_config`'s `spf_liquido_percentual` key at runtime, as ONE ingredient inside a much larger multi-tier commission formula (`rentTotal × faixa`) that ALSO depends on role class, share thresholds, and return thresholds — none of which Gestão's card reproduces or even references.

**The real discrepancy**: if a MASTER admin ever changes `spf_liquido_percentual` away from 70 via the Master Config panel, Gestão's "Comissão Líquida SPF EXTRA" card would silently continue showing the OLD hardcoded 70% — diverging from what `commissionCalc()` (the real, live-adjustable commission engine) would compute for the same input. Today, with the config presumably still at 70, the two happen to agree numerically; this is a **latent** divergence, not a currently-observed one — production evidence: the value 70 was found in the Gestão hint text itself ("70% sobre o total SPF EXTRA"), consistent with the config's presumed-current value, but the two code paths are NOT the same formula and WILL diverge silently the moment the config changes.

## Gate 21 — Commission Decision Gate

```
GESTÃO DOES NOT DEPEND ON RULE B AT ALL — the RC BLOCKER (originally
documented in module-registry.json's "gestao" entry from the PORTAL-
NEXT-01 audit) is REAL but SCOPED NARROWER than that entry's own
wording suggested ("flat 70% ... vs. portal-app.js's multi-tier
commissionCalc()" reads as if the two compete for the SAME output;
they do not — only Rule A's single hardcoded literal is in tension
with Rule B's equivalent config parameter, and only for the one
"Comissão Líquida SPF EXTRA" surface).

COMMISSION IMPACT ON GESTÃO: SURFACE-SCOPED
  Affected: "Comissão Líquida SPF EXTRA" KPI card + its breakdown
  table's "Comissão Líquida 70%" column (2 of Gestão's ~30 rendered
  data surfaces).
  NOT affected: Produção (Paga/Faturada/Ag.Faturamento/Total),
  Classificação dos Planos, Planos por Loja e Departamento, Store
  analysis, Bank analysis, Status-by-store/bank, CPF Recusadas/
  Aprovadas analysis, "Total SPF EXTRA" (the raw value, before the
  0.70 multiplier, is unaffected — only the commission-derived figure
  is).

HUMAN DECISION REQUIRED: YES, for the "Comissão Líquida SPF EXTRA"
surface specifically — should V2 (a) keep the literal 0.70 (byte-
identical to what Gestão shows today, but latently divergent from the
live-configurable Rule B if that config ever changes), or (b) make the
percentage config-driven, matching Rule B's mechanism? This Wave does
NOT choose — see docs/GESTAO-COMMISSION-DECISION.md.

DECISION PER GATE 21: SURFACE-SCOPED, NOT GLOBAL — the Wave continues.
The "Comissão Líquida SPF EXTRA" card/column is migrated using Rule A's
own literal (byte-identical extraction, same as everything else in this
adapter — Gate 64/No Cleanup Drift forbids silently switching it to
config-driven behavior that doesn't exist in Gestão's own source), and
is explicitly labeled in the UI and in this report as reflecting a
literal, non-config-driven percentage — NOT presented as a resolved or
human-approved business decision. "Total SPF EXTRA" (raw) is unaffected
and reported as ordinary PASS.
```
