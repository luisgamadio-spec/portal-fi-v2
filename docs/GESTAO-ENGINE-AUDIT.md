# Gestão Engine Audit (Gates 5-19) — index

This Wave's audit findings for Gestão (Análise F&I do Grupo) are split across three focused documents rather than one long one, per Gates 134-136's explicit request for separate Function/KPI/Data contracts:

- **`docs/GESTAO-DATA-CONTRACT.md`** — real architecture (single-worksheet, not a Base01×02×03 crossing), grouped-row context-inheritance mechanic, real column names, normalization, exclusions, plan classification priority (cross-checked against Coparticipado V2), status buckets, date semantics, deferred dependencies (Gates 3, 5-12, 136).
- **`docs/GESTAO-KPI-CONTRACT.md`** — every KPI card and table's real formula/denominator/filter-scope/rounding, transcribed from `render()` (not inferred from labels), plus the confirmed-absent concepts (Vendas/Share/Receita/Ticket Médio/Model Analysis/Seller Analysis/FECHAMENTO/charts/export) (Gates 13-19, 135).
- **`docs/GESTAO-FUNCTION-MAP.md`** — the full extraction trace, 38 functions + 5 constants, dependency domains, deferred functions (Gate 129, 134, 137).
- **`docs/COMMISSION-RULE-MAP.md`** + **`docs/GESTAO-COMMISSION-DECISION.md`** — the commission blocker investigation and human-decision artifact (Gates 20-22, 86).

## Gate 3-4 — where the experience really lives, and the correct source

```
"Gestão" IS A MENU CATEGORY in production (grupo:'📊 Gestão'), not a
single module — proved by direct read of origin/main:index.html's
addOrUpdateModule() calls, not presumed:
  {id:'dashbi', grupo:'📊 Gestão', title:'ANÁLISE GERAL DO GRUPO', ...}
  {id:'gestao', grupo:'📊 Gestão', title:'ANÁLISE F&I DO GRUPO', ...}
This Wave migrates 'gestao' (modules/analise-fi-grupo.html, 2477
lines) — chosen over 'dashbi' (analise-geral-grupo-secure-original-
layout.html, a different and much larger file) based on convergent
evidence: (1) MIGRATION-WAVES.md's own Wave 4=Gestão/Wave 5=Dashbi
sequencing, where Dashbi explicitly depends on Wave 4; (2) this Wave's
entire commission-blocker apparatus (Gates 20-22 etc.) matches EXACTLY
the RC BLOCKER #6 already on file for module-registry.json's 'gestao'
entry (the hardcoded 70% at analise-fi-grupo.html line ~2159); (3)
PORTAL-NEXT-05's own "Next Eligible Phase" recommendation named this
same file explicitly.

Local vs. remote (Gate 4, proved not presumed):
  modules/analise-fi-grupo.html:  local == origin/main == live
    production, blob d52cc9ada7fd1a373d84ff6ea894d85ffc58ad0d — the
    ONE file this Wave read that was NOT divergent (unlike Score/
    Coparticipado's source files, and unlike portal-app.js/index.html,
    which WERE divergent and were read exclusively from origin/main).
```

## Gate 20 finding, summarized (full detail in COMMISSION-RULE-MAP.md)

Commission impact on Gestão: **SURFACE-SCOPED**, not GLOBAL. One KPI card ("Comissão Líquida SPF EXTRA") and one table column are affected; everything else (Produção, Classificação dos Planos, Planos por Loja/Departamento, Store/Bank/Status/CPF analysis) is unaffected and reaches ordinary functional parity.
