# Dashbi Model Analysis Contract (Gates 15-19, 47-56, 81)

Model Analysis is explicitly flagged in this Wave's brief as the highest-risk functional region (historical failure mode: `entradasLength = 0` with no traceable reason). This document is the evidence that it is NOT opaque in V2.

## Scope (Gate 16, proved not presumed)

```
NOVOS ONLY:    aggregate()'s own model-keyed maps (vendasModelo,
              finModelo, compModelo) only add a record `if (r.dept ===
              "Novos")` — confirmed by direct source read, both for
              sales AND financing sides. Seminovos records never enter
              any model-keyed aggregation. Golden fixture:
              seminovos_fora_model_analysis.
FAMILY GROUPING:    FAMILY_MODELS (extracted byte-identical constant):
                  OUTLANDER: [OUTLANDER HPE-S, OUTLANDER SIGNATURE]
                  ECLIPSE CROSS: [RUSH, HPE, HPE-S 4X2, HPE-S 4X4,
                                  HPE-S BLACK, TARMAC]
                  TRITON: [GL, GLS, HPE, HPE-S, KATANA, SAVANA,
                           TARMAC, TERRA]
                  NOTE: plain "OUTLANDER" (no trim suffix) is NOT in
                  FAMILY_MODELS' own OUTLANDER list — modelRowsUnified
                  still shows it (it unions FAMILY_MODELS with every
                  REAL model found in sales data for that family), but
                  planRowsByModel/planRowsByStoreForFamily (which
                  iterate ONLY over FAMILY_MODELS) do NOT show it. This
                  is a real, faithfully-reproduced production quirk,
                  not a bug — confirmed via the golden fixtures and
                  visible in the V2 UI itself.
```

## Model normalization (Gate 17, extracted byte-identical: `modeloPadrao`)

Same general shape as Coparticipado's/Gestão's own `modeloPadrao`, but this is **Dashbi's own, independently extracted copy** — not assumed identical (Gate 13's own instruction). Explicit pre-cleanup rules for TRITON TERRA/TARMAC and ECLIPSE CROSS TARMAC (to avoid the generic cleanup regex stripping "TARMAC"-relevant tokens before the family check runs), then family-specific suffix detection. **`"INCONSISTÊNCIA TRITON"`** is the real, literal return value for an unrecognized Triton sub-variant — not an error, not corrected, not silently mapped to a nearest match. Golden fixture: `modelo_inconsistencia_triton`.

## Entrada calculation contract (Gate 51, the historically risky part)

```
FUNCTION:           modelExtraMetrics(results, modelo) — origin/main
                   lines 3877-3912
FOR EACH financing record (Novos, that model):
  1. chassi = fin.chassi (or origem's own Chassi/Chassi Resumido/etc.)
  2. sale = salesByChassi[chassi] (built by buildSalesByChassiForEntry,
     Novos-only, requires the SALE's own valorVenda > 0)
  3. valorVenda = fin.valorVenda || getFinValorVenda(origem) ||
     (sale ? sale.valorVenda : 0)
     — getFinValorVenda itself checks VALOR_VENDA_NOVO FIRST (set by
     the Nova adapter when a chassi match succeeded), then falls back
     through 8 more historical column-name aliases.
  4. financiado = fin.producao || asNumber(getCol(origem,
     ["VALOR_FINANCIADO","Valor Financiado"]))
  5. ELIGIBILITY GUARD (the critical gate):
       valorVenda > 0 && financiado > 0 && financiado <= valorVenda * 1.15
     If this fails, the record contributes NOTHING to Entrada — no
     error, no NaN, just correctly excluded. Golden fixtures:
     entrada_financiado_excede_tolerancia (financiado > 1.15x, verified
     entradaQtd=0 for the affected model), entrada_elegivel (passes).
  6. entradaInformada = asNumber(getCol(origem, ["ENTRADA_NOVO",
     "Entrada","VALOR_ENTRADA","Valor Entrada"])) — if > 0, USE THIS
     (the Nova adapter's own pre-computed value takes priority).
  7. entrada = entradaInformada > 0 ? entradaInformada :
     Math.max(0, valorVenda - financiado)  [fallback: computed]
DENOMINATOR/AGGREGATION (per model):
  entradaQtd = count of eligible records
  entradaTotal = sum(entrada)
  valorVendaTotal = sum(valorVenda) [only over eligible records]
  entradaMed = entradaQtd ? entradaTotal/entradaQtd : 0
  entradaPct = valorVendaTotal ? entradaTotal/valorVendaTotal : 0
    — NOTE: this is a TOTAL-over-TOTAL ratio, NOT the average of each
    record's own individual pct. A real, non-obvious aggregation
    choice, preserved exactly (not "simplified" to an average).
FAMILY-LEVEL (familyExtraMetrics): entradaMed/entradaPct are summed
  across the family's model rows the same way (entradaTotal/
  valorVendaTotal totals, not weighted averages of already-averaged
  per-model figures) — prazoMedio/pmtMed ARE weighted by `financiada`,
  entradaMed/entradaPct are NOT reweighted (they're already correct
  totals-of-totals by construction). Preserved exactly.
```

## The Nova-format Entrada pipeline (Gate 20-21, 41-42, real risk confirmed)

```
STEP 1:    criarIndiceVendasNovasPorChassi(b1Nova) — indexes the
          ADAPTED Base01-Nova rows (post adaptarBase01NovaLocal) by
          chassi.
STEP 2:      brabusDiagnosticarEntradaNova(rawB2NovaRows, indice) —
            runs BEFORE enrichment, against the RAW (pre-adapter) Base02-
            Nova rows, counting totalFinanciamentos (rows whose
            Descrição Serviço contains "POR PLANO-FINANCIAMENTO"),
            chassisLocalizados (found in the index), chassisNaoLocalizados
            (not found, up to 20 examples captured with chassi/cliente/
            loja for diagnosis). calculoAplicado = chassisLocalizados > 0
            — a REAL FIX already in production (comment: "a divergência
            em outros chassis não pode zerar operações válidas") — the
            calculation applies per-located-operation, an all-or-nothing
            abort is NOT reintroduced.
STEP 3:        enriquecerEntradaBase02Adaptada(adaptedB2Nova, indice) —
              for each ADAPTED row, looks up the same chassi in the
              same index, computes valorVenda (via
              brabusValorVendaBase01Nova on the matched sale) and
              valorFinanciado (via brabusValorFinanciadoBase02Nova),
              sets ENTRADA_NOVO = max(0, valorVenda-valorFinanciado)
              (0 if no match), PERCENTUAL_ENTRADA_NOVO accordingly.
GOLDEN FIXTURES:    nova_entrada_com_match (chassi found — ENTRADA_NOVO
                  computed correctly, verified 200000-150000=50000),
                  nova_entrada_sem_match (chassi NOT found — diagnostic
                  shows exactly which chassi/cliente/loja failed to
                  match, chassisNaoLocalizados=1, calculoAplicado=
                  false, ENTRADA_NOVO=0 — never an opaque zero).
```

## Model Analysis KPI columns (as displayed, Gate 47-50)

Vendas (volume), Financiamentos (financiada), Penetração (fin/vendas), Produção, Receita Total, Ticket (produção/financiamentos), Retorno Médio, Prazo Médio, PMT Médio, Entrada Qtd, Entrada Média, Entrada % — ALL present in the V2 UI's Model Analysis table (Gate 81: never hidden for visual simplicity).

## Plan mix by model (`planRowsByModel`) and by store (`planRowsByStoreForFamily`)

Counts + percentages of Linear/Balão/Coparticipado/Subsidiado/Reversão among that model's (or that store's, for the family) financing records — using the SAME `isFinLinear`/`isFinBalao`/`isFinCoparticipado`/`isFinSubsidiado`/`isFinReversao` classification flags as everywhere else in the module (no separate classification logic for this view).
