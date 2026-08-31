# Model Analysis — Redundant Plan Tables Removal (PORTAL-NEXT-07.5.1)

Human decision: remove 4 user-facing analytical sections from Análise
por Modelos ("Resumo tipos de plano", "Quantidade por tipo de plano /
Modelo", "Quantidade por tipo de plano / Loja", "Detalhe Coparticipado /
Subsidiado / Reversão") — visual pollution / duplicated information, now
that the approved per-model `+ Detalhes` already exposes plan counts.
Presentation-only; no business function touched.

## Gate 1 — render paths located (before any edit)

All 4 were rendered inside `modelAnalysisHtml()` (`assets/js/dashbi.js`),
via the shared `planPctTableHtml()`/`planPctBodyRow()`/
`planPctPrimaryHeaders()` renderers (sections 1-3) and a hand-rolled
`expandableTableHtml()` call (section 4):

```
SECTION                                    FUNCTION/CALL SITE                          DATA SOURCE                          REUSED ELSEWHERE?
Resumo tipos de plano                      planPctTableHtml('planTotal', ...)          A.planTotalRowsForFamily()           NO — only this call site
Quantidade por tipo de plano / Modelo      planPctTableHtml('planModel', ...)          A.planRowsByModel() -> planRows      YES — planRows also feeds the
                                                                                                                              planByModelo merge that sets
                                                                                                                              subsidiadoQtd/coparticipadoQtd
                                                                                                                              on modelRows, consumed by the
                                                                                                                              APPROVED + Detalhes Planos group
Quantidade por tipo de plano / Loja        planPctTableHtml('planStore', ...)          A.planRowsByStoreForFamily()         NO — only this call site
Detalhe Coparticipado/Subsidiado/Reversão  expandableTableHtml(...) + specialBody       A.specialPlanDetailRows()            NO — only this call site
```

**Critical finding acted on**: `planRows` (from `A.planRowsByModel()`)
is REUSED by the approved `+ Detalhes` Planos group — removing section
2's *rendering* did NOT remove `planRows` itself, the `planByModelo`
merge, or the `planRowsByModel()` adapter function. Only the
`planPctTableHtml('planModel', ...)` call and its `<h3>` were deleted.

## Gates 2-5 — what was actually removed

- The 4 `<h3 class="dbSubHeading">...</h3>` + table render calls inside
  `modelAnalysisHtml()`'s return statement.
- The 3 now-unused local variables that fed ONLY those calls:
  `planTotalRows`, `planStoreRows`, `specialRows` (+ `specialNs`/
  `specialBody`, the hand-rolled row builder for section 4).
- The 3 rendering helper functions left with 0 remaining callers after
  the above: `planPctTableHtml()`, `planPctBodyRow()`,
  `planPctPrimaryHeaders()` — dead presentation code, not business
  logic (their own comment block, PORTAL-NEXT-07.4's no-scroll fix for
  these specific tables, was removed with them since it no longer
  describes anything live).

**Untouched, per Gate 1's finding above**: `planRows`/
`A.planRowsByModel()`, the `planByModelo` merge, `A.planTotalRowsForFamily()`,
`A.planRowsByStoreForFamily()`, `A.specialPlanDetailRows()` (all 3
adapter functions still exist, still exported, still callable — simply
no longer called by any V2 renderer) — no business calculation,
classifier, or aggregation was deleted. "Inconsistências TRITON" (not
in the removal list) was left completely untouched, including its
position immediately after the model table.

## Gate 8 — information retention audit

| METRIC | REMOVED SECTION | REMAINING LOCATION | STATUS |
|---|---|---|---|
| Financiamentos (nível Família) | Resumo tipos de plano | `familyMetricGridHtml`'s "Financiamentos" box (already existed, same population) | AVAILABLE |
| Linear/Balão/Coparticipado/Subsidiado/Reversão — contagem E % (nível Família) | Resumo tipos de plano | Nenhuma — apenas somável manualmente a partir das contagens por modelo em `+ Detalhes` | REVIEW |
| Financiamentos (por Modelo) | Qtd. por tipo de plano / Modelo | Já era a própria coluna primária "Financiamentos" do modelo | AVAILABLE |
| Qtd Linear/Balão/Reversão/Subsidiado/Coparticipado (por Modelo) | Qtd. por tipo de plano / Modelo | Grupo Planos do `+ Detalhes` aprovado (mesmas 5 categorias, mesma fonte `planRowsByModel`) | AVAILABLE (INTENTIONALLY REMOVED DUPLICATE) |
| % Linear/Balão/Coparticipado/Subsidiado/Reversão (por Modelo) | Qtd. por tipo de plano / Modelo | Nenhuma — `+ Detalhes` mostra quantidade, não percentual | REVIEW |
| Financiamentos/Linear/Balão/Coparticipado/Subsidiado/Reversão — contagem E % (por Loja) | Qtd. por tipo de plano / Loja | Nenhuma — Análise por Modelos é organizada por Modelo, não por Loja; a tabela "Vendas e Financiamentos por Loja" é Grupo-wide, não filtrada por família/Novos, e não quebra por tipo de plano | REVIEW |
| Detalhe por registro (Cliente/Produção/Receita) dos financiamentos Coparticipado/Subsidiado/Reversão | Detalhe Coparticipado/Subsidiado/Reversão | Nenhuma — `+ Detalhes` mostra apenas quantidade agregada por modelo, não o drill-down por registro/cliente | REVIEW |

Reportado integralmente, sem converter nenhum REVIEW em AVAILABLE. Por
instrução humana explícita ("Do not add new UI merely to preserve
redundant information. The human explicitly wants these four
analytical blocks removed"), nenhuma dessas lacunas foi preenchida com
nova interface — a remoção foi executada como pedida, com este audit
como registro do que efetivamente deixou de ser visível.

## Verification

```
tests/dashbi-parity-test.py:       26/26 PASS (0 business change)
tests/foundation-regression.py:    10/10 PASS
Rendered UI occurrences (Playwright, real browser):
  "Resumo tipos de plano":                          0
  "Quantidade por tipo de plano / Modelo":              0
  "Quantidade por tipo de plano / Loja":                    0
  "Detalhe Coparticipado / Subsidiado / Reversão":              0
  "Inconsistências TRITON" (must remain):                          present
Model Analysis regression (fixture model_analysis_parcelamento_completo):
  model selector / vehicle images / primary metrics / + Detalhes /
  multiple-open / Financeiro / Retorno / Parcelamento / Entrada / Planos
  (Subsidiado/Coparticipado/Reversão/Balão/Linear quantities):    all PASS
No horizontal scroll (360/390/430/768/1366/1920, doc+component):  PASS
Console/page errors:                                                0
Network calls:                                                          0
```
