# Model Analysis — Restoration Matrix (PORTAL-NEXT-07.3, Gate 34-35)

| Production metric | V2 before | V2 after | Source function | Source field | Unit | Visible condition | Parity test | Status |
|---|---|---|---|---|---|---|---|---|
| Volume vendido (family) | absent | present | `familyMetricGridHtml` (sum of `modelRowsUnified`) | `volume` | count | Novos, Modelos mode | full-pipeline + new fixture | RESTORED |
| Financiamentos (family) | absent | present | same | `financiada` | count | same | same | RESTORED |
| Penetração (family) | absent | present | same | derived | % | same | same | RESTORED |
| Produção (family) | absent | present | same | `producao` | R$ | same | same | RESTORED |
| Receita (family) | absent | present | same | `receita` | R$ | same | same | RESTORED |
| Receita SPF (family) | absent | present | same | `receitaSPF` | R$ | same | same | RESTORED |
| Receita Total (family) | absent | present | same | `receitaTotal` | R$ | same | same | RESTORED |
| Ticket médio (family) | absent | present | same | derived | R$ | same | same | RESTORED |
| Média de retorno (family) | absent | present | `A.familyExtraMetrics` | `retornoMedio` | % | same | parity script + fixture | RESTORED |
| Prazo médio (family) | absent | present | `A.familyExtraMetrics` | `prazoMedio` | Nx | same | same | RESTORED |
| Média de parcela (family) | absent | present | `A.familyExtraMetrics` | `pmtMed` | R$ | same | same | RESTORED |
| Entrada média (family) | absent | present | `A.familyExtraMetrics` | `entradaMed` | R$ | same | Entrada parity unchanged | RESTORED |
| % Entrada médio (family) | absent | present | `A.familyExtraMetrics` | `entradaPct` | % | same | Entrada parity unchanged | RESTORED |
| Receita (per-model) | absent | present | `A.modelRowsUnified` (already had field) | `receita` | R$ | same | full-pipeline | RESTORED |
| Receita SPF (per-model) | absent | present | same | `receitaSPF` | R$ | same | full-pipeline | RESTORED |
| **Prazo Médio (per-model)** | absent | present | same | `prazoMedio` | Nx | same | new fixture (`model_analysis_parcelamento_completo`) | RESTORED |
| **Parcela Média (per-model)** | absent | present | same | `pmtMed` | R$ | same | same new fixture | RESTORED |
| Qtd Linear (per-model) | absent | present | same | `linearQtd` | count | same | same | RESTORED |
| Qtd Balão (per-model) | absent | present | same | `balaoQtd` | count | same | same | RESTORED |
| Qtd Reversão (per-model) | absent | present | same | `reversaoQtd` | count | same | same | RESTORED |
| **Valor Médio Balão / Balão Médio (per-model)** | absent | present | same | `balaoMed` | R$ | same | same | RESTORED |
| Penetração threshold styling | plain `pct()` | `.dbPenetracaoBaixa`/`.dbPenetracaoOk` (<40%) | inline in `dashbi.js` | `penetracao` | % + semantic class | per-model table | visual check | RESTORED |
| Resumo tipos de plano (family total, 5%) | absent | present | `A.planTotalRowsForFamily` (newly extracted) | — | count+% | Novos, Modelos mode | full-pipeline + parity script | RESTORED |
| Quantidade por tipo de plano / Modelo (5%) | counts only, no % | counts + % | `A.planRowsByModel` (already extracted, % now rendered) | — | count+% | same | full-pipeline | RESTORED |
| Quantidade por tipo de plano / Loja | absent | present | `A.planRowsByStoreForFamily` (already exported, now called) | — | count+% | same | full-pipeline | RESTORED |
| Detalhe Coparticipado/Subsidiado/Reversão | absent | present | `A.specialPlanDetailRows` (newly extracted) | — | text+R$ | same, table (with "Sem dados" fallback, not conditional in production) | full-pipeline + parity script | RESTORED |
| Inconsistências TRITON | absent | present | `A.inconsistenciaTritonRows` (newly extracted) | — | text | same, **conditional** — only rendered if non-empty (matches production exactly) | full-pipeline + parity script + `modelo_inconsistencia_triton` fixture (real non-empty case) | RESTORED |
| Entrada Qtd (per-model) | present (EXTRA_IN_V2) | present, unchanged | `A.modelRowsUnified` | `entradaQtd` | count | same | unchanged | MATCHED (kept, not production, disclosed) |
| Card+modal interaction shape | N/A (V2 never had it) | N/A — wide table + scroll used instead | — | — | — | — | — | NOT APPLICABLE (deliberate adaptation, see metric-contracts doc; **HUMAN REVIEW REQUIRED**) |

**Every production-visible material Model Analysis item now has an explicit final status. 0 BLOCKED, 0 silently DEFERRED.**
