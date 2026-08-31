# Dashbi Base03 Schema Resolution (Gates 10-11, 43-44, 126)

## Real column names and aliases (Gate 10, extracted not retyped)

| Semantic field | Resolution order |
|---|---|
| Cliente (crossing key) | `Cli - Nome` / `Cliente` / `Nome Cliente` / `CLIENTE` / `Nome/Razão Social` / `Razão Social` |
| CPF/CNPJ (crossing key) | `Cli - CPF/CNPJ` / `CPF` / `CPF/CNPJ` / `CNPJ` / `CPF CNPJ` / `Documento` |
| TC Devolvida | named columns, THEN positional `__COL_E` fallback (see below) |
| Código IF | named columns, THEN positional `__COL_F` fallback (see below) |
| Balão PMT | `Op Fin - Balão PMT (R$)` / `Balão PMT` / `Balao PMT` |
| PMT | `Op Fin - PMT (R$)` / `PMT` / `Valor Parcela` |
| Quantidade Parcelas | `Op Fin - Quantidade Parcelas` / `Quantidade Parcelas` / `Parcelas` |
| Financiado | `Op Fin - Financiado (R$)` / `Financiado` |

**No `Op - Modalidade` filter** — `buildB03Index` indexes every row unconditionally. Confirmed real difference from Coparticipado's `buildB3Index`, which filters to `Modalidade === 'FANDI'` — not presumed identical, verified by direct source read of both files.

## Positional alias fallback for "anonymized" exports (Gate 43-44, the historically-cited risk)

```js
function getTCDevolvidaValue(row){
  const named = getCol(row,["Tabela - TC Devolvida (R$)","Tabela - TC Devolvida","TC Devolvida","Tabela TC Devolvida"]);
  if(named !== "" && named !== null && named !== undefined) return named;
  if(isTCHeader(row.__HEADER_E) || isCoparticipadoValue(row.__COL_E)) return row.__COL_E;
  return "";
}
function getCodigoIFValue(row){
  const named = getCol(row,["Tabela - Código IF","Tabela - Codigo IF","Codigo IF","Código IF","Tabela Codigo IF"]);
  if(named !== "" && named !== null && named !== undefined) return named;
  if(isIFHeader(row.__HEADER_F) || isSubsidiadoValue(row.__COL_F) || isReversaoValue(row.__COL_F)) return row.__COL_F;
  return "";
}
```
Both extracted byte-identical. `__COL_E`/`__COL_F`/`__HEADER_E`/`__HEADER_F` are populated by production's own `readWorkbookSmart()` Excel reader (columns 5 and 6, 0-indexed 4 and 5) when a Base03 export has been "anonymized" — the real column exists at that fixed position but without (or with an unrecognized) header text. Since Excel parsing is deferred this Wave, fixtures that need to exercise this path set these four properties directly on the raw Base03 row object.

## Alias resolution matrix (Gate 44) — tested by golden fixture

| Scenario | Fixture | Result |
|---|---|---|
| Canonical named column present | `subsidiado`, `reversao`, `coparticipado`, `balao` | PASS — resolved via `getCol`'s exact-then-contains alias search |
| Missing named columns, positional fallback (`__COL_F`) | `base03_alias_posicional` | PASS — resolves SUBSIDIADO via the positional path, verified against the independent reference |
| No match at all (no Base03 row for the client) | `linear_sem_b3` | PASS — `matched:false`, `planoClassificado` defaults to LINEAR, no error, no guessed substitute column |
| Duplicate/ambiguous candidates (two Base03 rows for one client) | `duplicate_b3` | PASS — `scoreB03PlanRow` scoring picks the higher-priority candidate (SUBSIDIADO signal, score 100) over a lower-scoring residual match |

## What V2 does NOT do (Gate 43)

When a semantically required field is genuinely absent (no named column, no positional signal), the row is classified LINEAR by the same default production itself falls back to — **no substitute column is guessed**, and no new "missing schema" error UI was invented beyond what `getCol`'s own empty-string return already produces. This preserves inclusion/classification semantics exactly; it does not add presentation on top of them.
