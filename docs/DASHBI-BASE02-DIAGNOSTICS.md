# Dashbi Base02 Discard Diagnostics (Gates 8-9, 40, 125)

Dev-only diagnostics (never shown in the final product experience — Gate 40/98) proving that valid financing rows are not silently discarded.

## processBase02's own discard categories (Gate 8-9)

```
rowContainsExcludedName(row):   discarded entirely (EXCLUDED_SELLERS
                               match anywhere in the row's own values)
isRevendaRecord(row):              discarded entirely (seller ===
                                 "JAIR BARBOSA", OR loja contains
                                 "REVENDA")
isFin check fails
(financiado!==1 AND !desc.includes         discarded — not treated as
("FINANCIAMENTO") AND valorFin<=0        a financing row at all
AND receita<=0):
valorFin <= 0
(even when isFin was true):                 discarded — `if(!isFin ||
                                          valorFin<=0) return;`
```
V2's `compute()` result exposes `results.excluded` (from `processBase01`'s own excluded list — chassi groups whose last relevant transaction wasn't in ALLOWED_SALES) and `results.semMatch` (Base02 rows that found no Base03 match, tracked by client name) — both extracted byte-identical, both available for dev inspection, never shown in the base product UI.

## Entrada-specific diagnostic (Nova format only — Gate 9, 40, 125)

```
brabusDiagnosticarEntradaNova(rawB2NovaRows, indiceVendasNovas)
returns:
  totalFinanciamentos    — rows whose Descrição Serviço contains "POR
                          PLANO-FINANCIAMENTO"
  chassisLocalizados        — of those, how many matched a Base01-Nova
                            sale by chassi
  chassisNaoLocalizados        — how many did not
  taxaSucesso                     — chassisLocalizados / totalFinanciamentos
  naoLocalizados                     — up to 20 examples {chassi,
                                    cliente, loja} for the ones that
                                    failed to match
  calculoAplicado                       — chassisLocalizados > 0 (per-
                                        record, NOT all-or-nothing —
                                        see DASHBI-MODEL-ANALYSIS-
                                        CONTRACT.md)
```
This diagnostic is exposed by V2's `compute()` as `results.entradaDiagnostic` and rendered in a dedicated "Diagnóstico (dev only)" section of the V2 UI, clearly separated from and below the real product content — satisfying Gate 40's "dev tooling only" requirement without adding debug counters to the actual KPI cards/tables.

## Golden fixture evidence (Gate 9, 41-42, 125)

| Fixture | Proves |
|---|---|
| `linear_sem_b3` | a financing record with no Base03 match still enters `fins` (matched:false, plano LINEAR) — not discarded |
| `vendedor_excluido` | EXCLUDED_SELLERS discard verified end-to-end |
| `vendedor_nao_localizado_bloqueia` | the hard-stop guard (not a silent partial discard — full abort with the exact missing seller named) |
| `valores_zero` | financiado<=0 correctly discards the row (not a false-positive inclusion) |
| `nova_entrada_com_match` / `nova_entrada_sem_match` | the Nova-format Entrada pipeline's own discard/match tracking, both outcomes, both traceable |
| `date_cutoff_misto` | historical vs. Nova rows both survive their respective pipelines and get concatenated — no row silently dropped at the date boundary |

24/24 golden fixtures pass exact parity against an independently re-extracted reference (`tests/dashbi-parity-test.py`) — see `docs/DASHBI-FUNCTION-MAP.md`.
