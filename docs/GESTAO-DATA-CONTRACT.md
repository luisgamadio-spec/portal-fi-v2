# Gestão Data Contract (Gate 6-11, 136)

## Real architecture (Gate 3, proved not presumed)

Unlike Coparticipado (which crosses 3 separate bases — vendas/financiamentos/contratos FANDI), Gestão (`modules/analise-fi-grupo.html`) consumes **ONE single worksheet** — a flat FANDI operational extract (`../data/Base 03.xlsx` in production, or a live secure RPC in `FANDI_SECURE_MODE`, not used this Wave). There is no Base01×Base02×Base03 crossing here — it does not apply to this module, and is not force-fitted into this report.

## Row shape and the grouped-row inheritance mechanic

The raw worksheet uses real Excel export conventions where **auxiliary rows** (carrying an "Opcional" field — SPF Extra, TC Devolvida, Código IF) appear directly below a proposal's main row, sharing its proposal but with blank context/financial cells. `normalizeRows()` (byte-identical, extracted) reconstructs full records by:

- **Inheriting context fields** (proposal code, client, CPF, store, department, modalidade, status, bank, dates) forward from the last row that had them.
- **NEVER inheriting financial fields** (valorFinanciado, PMT, balão, valor balão) — each must come from its own row, specifically to prevent an auxiliary row from being double-counted as a second financing.
- Tagging inherited-only ("auxiliary") rows with `__isAuxOptional: true` and a `__proposalKey` linking them back to their proposal.

## Columns used (real header names, `findCol()`'s own candidate lists — origin/main lines 1467-1486)

| Canonical field | Real header candidates (first match wins) |
|---|---|
| opCodigo | Op - Código / Op Código / Código / Codigo / Proposta / Nº Proposta / Numero Proposta |
| cliente | Cli - Nome / Cliente / Nome |
| cpf | Cli - CPF/CNPJ / CPF/CNPJ / CPF / CNPJ |
| loja | Inst - Ponto de Venda / Ponto de Venda / Loja / Revenda |
| departamento | Inst - Departamento / Departamento / Novo Seminovo / Novos Seminovos |
| modalidade | Op - Modalidade / Modalidade / Tipo Modalidade |
| status | Op - Situação / Situação / Status |
| banco | Op Fin - Banco / Banco / Financeira |
| valorFinanciado | Op Fin - Financiado (R$) / Financiado (R$) / Financiado / Valor Financiado / ... |
| pmt | Op Fin - PMT (R$) / PMT / Parcela / Valor Parcela |
| balao | Op Fin - Balão PMT (R$) / Balão PMT / Balao PMT |
| valorBalao | Op Fin - Valor Balão (R$) / Valor Balão (R$) / ... |
| dataFaturamento | Op - Data Faturamento / Data Faturamento / Op - Data Contrato / Data Contrato |
| dataPagamento | Op Fin - Data Pagamento Contrato / ... / Op - Data Inclusão / Data Inclusão |
| opcionalNome | Opcional - Nome: / Opcional - Nome / Opcional Nome / Nome Opcional / Opcional |
| opcionalValor | Opcional - Valor (R$) / Opcional Valor / ... / Valor SPF / SPF EXTRA |
| tcDevolvida | Tabela - TC Devolvida (R$) / TC Devolvida (R$) / TC Devolvida / ... |
| codigoIF | Tabela - Código IF / Tabela - Codigo IF / Código IF / Codigo IF / Cod IF |

## Row-level filter (applied at the end of `normalizeRows()`)

A normalized row survives only if: `isFandiModalidade(modalidade)` (`Op - Modalidade` cleans to exactly `FANDI`) AND NOT `isExcludedModalidade(modalidade)` (excludes `FINANCEIRA EXT.`, `À VISTA`/`A VISTA`, `CONSÓRCIO`/`CONSORCIO`, or anything containing `TOTAL`) AND the status does not contain `TOTAL` (drops Excel subtotal/summary rows) AND the row carries at least one of status/cpf/valorFinanciado/opcionalNome/opcionalValor/tcDevolvida/codigoIF (drops fully-blank rows).

## Normalization

- `statusNorm()`: maps raw status text to one of `AG. FATURAMENTO / FATURADA / PAGA / APROVADA / ASSINADA / TRANSITO / ENC. A VISTA / ENCERRADA / RECUSADA / ENC. RECUS. / PRÉ-RECUSA / CANCELADA` (or passes through uppercased if none match) — handles known spelling variants (e.g. "AGUARD. FATU." and "AG FATURAMENTO" both normalize to "AG. FATURAMENTO").
- `lojaCurta()`: strips a "MITSUBISHI | " prefix, expands known abbreviations (A. FRANCO → ANÁLIA FRANCO, NAÇÕES/NACOES → NAÇÕES UNIDAS, GASTÃO/GASTAO → GASTÃO VIDIGAL).
- `tipoVeiculo()`: NOVO or "VENDAS DIRETA"/"VENDA DIRETA" → Novos; SEMINOV* → Seminovos; else "Não informado".
- `parseNumber()`: pt-BR-aware numeric parsing (comma = decimal, dot = thousands separator, with a heuristic for ambiguous single-dot cases).
- `cleanTextKey()`: uppercase + NFD accent-strip, used for all text-signal comparisons (plan classification, modalidade checks).

## Exclusions (Gate 11, extracted not retyped)

```js
const EXCLUDE_MODALIDADE = ["FINANCEIRA EXT.", "À VISTA", "A VISTA", "CONSÓRCIO", "CONSORCIO"];
```
Applied via `isExcludedModalidade()`, plus a blanket `.includes("TOTAL")` catch. This is a DIFFERENT exclusion mechanism than Coparticipado/Score's `EXCLUDED_SELLERS` name-based exclusion — Gestão has no seller-name exclusion list at all (confirmed: no `EXCLUDED_SELLERS`-equivalent constant anywhere in analise-fi-grupo.html).

## Plan classification (Gate 12) — cross-checked against Coparticipado V2

```js
function planTypeFromFields(opcionalNome, balao, tcDevolvida, codigoIF, valorBalao){
  // 1) Código IF = 999 ou SUBSIDIADO => SUBSIDIADO
  // 2) Código IF = 777 ou REVERSÃO => REVERSÃO
  // 3) TC Devolvida = 1 ou COPARTICIPADO => COPARTICIPADO
  // 4) PMT Balão > 0 ou Valor Balão > 0 => BALÃO
  // 5) Demais propostas => LINEAR
}
```
**Same priority order as Coparticipado V2's `classifyPlan()`**: SUBSIDIADO > REVERSÃO > COPARTICIPADO > BALÃO > LINEAR — independently implemented in a second real production file, not shared code, giving genuine cross-module business-rule consistency evidence (Gate 83; also directly proved in this Wave's own `priority_collision` fixture, which resolves to SUBSIDIADO under both files' rules). Proposal-level resolution differs from Coparticipado's B3-fuzzy-matching: `buildPlanAnalysis()`/`planProposalsFromRows()` instead take the HIGHEST-PRIORITY signal found across every row sharing a `proposalKey()` (main row + any auxiliary rows), via `planPriority()`.

## Status buckets (Gate 19 relevant)

```
OPERACIONAL             = PAGA, FATURADA, AG. FATURAMENTO (+ spelling variants)
STATUS_RECUSA_LIQUIDA   = RECUSADA, ENC. RECUS., PRÉ-RECUSA
STATUS_APROVACAO_HISTORICA = APROVADA, ENCERRADA, CANCELADA, ASSINADA, TRANSITO,
                          ENC. A VISTA, FATURADA, PAGA, AG. FATURAMENTO (+ variants)
STATUS_APROVADAS_VALIDAS = APROVADA, ENCERRADA, CANCELADA, ASSINADA, TRANSITO, ENC. A VISTA
RECUSAS                 = declared, CONFIRMED UNUSED (dead constant — grepped, 0 other
                          references in the file) — not migrated, not a business rule
                          in effect today.
```
CPF-level "recusa líquida" rule: a CPF counts as a net refusal only if its LAST-registered status is in `STATUS_RECUSA_LIQUIDA` (implicitly requiring no later approval-type status ever superseded it, since the "last" status by date/row-order wins). CANCELADA/ASSINADA/TRANSITO/ENC. A VISTA are explicitly treated as approvals that nullify a refusal (source comment, lines 1161-1166).

## Date semantics

`inPeriod(row, start, end)`: a row is in-period if EITHER `dataFaturamento` OR `dataPagamento` falls within `[start, end]`, inclusive on both ends. Period presets (Gate 17): `CURRENT_MONTH`, `PREVIOUS_MONTH`, `LAST_6_MONTHS` (no "last year", no "clear" button — different preset set than Coparticipado's 4-preset UI, confirmed by direct source read, not presumed identical).

## Deferred (not this Wave's data-loading path)

```
DEFERRED DEPENDENCY:  raw Excel/CSV worksheet parsing (rowsFromWorksheet,
                     parseCsvRows, loadWorkbookFrom*, loadOnlineWorkbook,
                     autoFillDates) and the live secure-API path
                     (processSecureFandi, fandiAdaptSecureResponse,
                     fandiStatusPivot, fandiProposalOutcomes,
                     fandiPlansByStore, fandiSyntheticOperational) --
                     both are I/O-boundary concerns (file parsing /
                     RPC calls), not part of the classification/
                     aggregation engine. Fixtures supply already-shaped
                     raw row objects (real column names) directly to
                     the byte-identical normalizeRows(), consistent
                     with 0 backend / 0 file I/O this Wave (Gate 31).
FUTURE WAVE:           whichever Wave adds real backend integration.
```
