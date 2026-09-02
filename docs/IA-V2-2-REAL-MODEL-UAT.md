# Brabus Intelligence — Real-Model Automated UAT (IA-V2-2-REAL-MODEL-UAT-02)

Automated battery run against the REAL, unmodified `portal-ai-homolog`
source and the REAL OpenAI API (`gpt-5.6-luna`), through the same
authenticated `POST` contract the browser's `sendRealText()` uses.
Local mock Supabase Auth/RPC only (no real Supabase project exists
locally — see `docs/IA-V2-2-TEXT-INTEGRATION.md`). 26 real OpenAI
requests total. Full raw evidence (every request/response pair) is
kept locally, outside this repo, at the session's own scratch
directory — not committed, contains no secrets.

Scenario 1 (human-executed, HOTFIX-03/04 born from it) is not
repeated here — see the HOTFIX-03/04 reports.

## STRUCTURED BLOCK CONTRACT CORRECTION (IA-V2-2-STRUCTURED-BLOCK-FIX-01)

The "Critical finding" below (originally: `ranking`/`score_ranking`/
`score_breakdown`/`operations` render broken against real backend
data) is **fixed** as of `assets/js/brabus-intelligence.js`. Summary —
full per-type detail is unchanged in the section below, now describing
*history*, not current state:

- `renderRanking()` — reads `{position, name, ...metric-named fields}`;
  the `block.metric`-named field renders first, any other `sim_*`/
  `hist_*`/plain metric fields present render as additional columns;
  header labels come from a `RANKING_FIELD_META`/`RANKING_DIMENSION_LABELS`
  table in the adapter, mirroring the backend's own `METRIC_LABELS`/
  `DIMENSION_LABELS` constants (same keys, same Portuguese words) plus
  the additional identifiers this UAT observed — no raw `dimension`/
  `metric`/field-name string is ever shown to the user.
- `renderScoreRanking()` — reads `{rank, seller, store, department,
  score, classification, sales, financed}` directly.
- `renderScoreBreakdown()` — reads the block's own flat identity/summary
  fields (no `items` array exists in the real shape) plus
  `components:[{label,value,max}]`, rendered as a "value / max" line
  per component; `plan_mix` (a `{planName: count}` map) renders as a
  compact caption.
- `renderOperations()` — renders **cards, not a table** (the backend
  source's own comment: "cards com referência mascarada, nunca uma
  tabela — mobile-first"), reading whichever fields are present per
  item across both real variants (Coparticipado/Subsidiado operations
  vs. Histórico similar-operations).

`metrics` and `comparison` — already correctly contracted — are
unchanged. The IA-V2-1 fixture data in
`assets/js/adapters/brabus-intelligence.adapter.js` (balão/subsidiado
ranking, score, historico-operations, score-ranking scenarios) was
also corrected to the same real shapes — it had been authored against
the same wrong assumption, so fixture mode was silently demonstrating
the same defect fixture-only tests could never have caught.

**Real E2E re-confirmation** (1 real OpenAI call, Subsidiado, same
prompt as Scenario 5): the live model→tool→block round trip was
repeated and the resulting real block rendered through the corrected
code — table now shows "Condição / Parcela / Financiado / Entrada"
headers and real R$ 1.920,00 / R$ 1.530,00 values, zero raw field
names. `REAL_STRUCTURED_BLOCK_E2E: PASS`.

New deterministic coverage: `tests/intelligence-structured-block-test.py`
(52/52 — the real captured Scenario 5 payload plus synthetic,
source-shaped fixtures for every producer variant, an XSS battery
targeting these 4 renderers specifically, and non-regression checks
for `metrics`/`comparison`).

## Legend

- **REAL_MODEL_E2E** — real Portal contract → real backend → real OpenAI.
- **DETERMINISTIC_ENGINE** — the tool's own JSON result, from the same
  authoritative call (not a separate calculation — there is only one
  engine, so the tool's own output *is* the deterministic truth to
  check the model's prose against).
- **DATA_DEPENDENT** — correct dispatch/logic proven; real-world data
  adequacy not claimed (no production database available locally).
- **LOCAL_MOCK_DATA_LIMITATION** — the real engine correctly returned
  "no data for this exact combination" because this session's local
  fixture tables are a small subset of the real production tables —
  not a product defect.

## Scenario matrix

| # | Scenario | Prompt (final turn) | Tool | Prose ⇄ Tool Result | Guardrail | Verdict |
|---|---|---|---|---|---|---|
| 2 | Linear | "...R$ 120.000, R$ 30.000 entrada, 36 meses" | `simular_financiamento` (LINEAR) | Exact match (R$ 4.010,97, 25%, R$ 90.000) | n/a | REAL_MODEL_E2E ✅ |
| 3 | Balão | "...R$ 150.000, balão R$ 40.000, entrada R$ 30.000, 36 meses" + "É NOVOS" (clarification) | `simular_financiamento` (BALAO) | Exact match (R$ 4.364,99/mês, balão R$ 40.000 no mês 36, total R$ 44.364,99) | Model asked for department instead of guessing — correct | REAL_MODEL_E2E ✅ |
| 4 | Coparticipado | "...L200 Triton, R$ 200.000, entrada R$ 120.000, 24 meses" + 2 clarification turns | `simular_financiamento` (COPARTICIPADO) | Exact match (R$ 3.747,96/mês, rebate R$ 4.000, venda líquida R$ 198.000) | Model correctly refused to guess a trim (system prompt rule "nunca escolha um modelo por conta própria"); self-corrected from the tool's own error listing once | REAL_MODEL_E2E ✅ |
| 5 | Subsidiado | "...bem R$ 90.000, entrada R$ 50.000" | `simular_financiamento` (TAXAS_SUBSIDIADAS) | Exact match (24x R$1.920/0,49%, 36x R$1.530/0,99%) | n/a | REAL_MODEL_E2E ✅ (structured block PRESENTATION DEFECT — see below) |
| 6 | Semestral/Anual | "...R$ 150.000, entrada R$ 40.000, 36 meses, NOVOS" | `simular_financiamento` (SEMESTRAL_ANUAL) | Exact match (R$ 30.850,43 × 6, meses 6/12/18/24/30/36) — first attempt correctly reported "no rule for this term" against the *original*, sparser local fixture | n/a | REAL_MODEL_E2E ✅ (after 1 harness fixture-data addition — see Environment Notes) |
| 7 | Taxa Implícita | "R$ 100.000 em 36x de R$ 4.485,75" | `calcular_taxa_financiamento` | Exact match (NET 2,58%, CET 2,86%, anual 35,73%) | Model explicitly disclaimed this isn't a commercial-table match | REAL_MODEL_E2E ✅ |
| 8 | Antecipação | "saldo R$ 50.000, sem data" + prazo/parcela/data de hoje | `simular_antecipacao` | Exact match (1ª parcela 02/10/2026 assumida, desconto R$ 7.311,60/11,28%, quitação R$ 57.488,40) | Correct default-date semantics; no "—" defect | REAL_MODEL_E2E ✅ |
| 9 | Cash Conversion | "à vista R$ 50.000 ou financiar 12 meses" + "considerar 1,5% ao mês?" | `simular_financiamento` (rate-challenge: no tool call) | Linear leg returned `payment: null` both attempts (LOCAL_MOCK_DATA_LIMITATION — see notes); rate-guardrail leg has no numeric tool result to check | **Rate immutability confirmed twice, unambiguously**: model refused the 1,5% substitution both times, citing the fixed 1,12% a.m. rule, and did not compute an alternate figure | Guardrail: REAL_MODEL_E2E ✅ · Full numeric comparison: NOT_OBTAINED (parameter choice, not a defect) |
| 10 | Multi-turn | "...R$ 90.000/R$20.000/36m" → "E em 48 meses?" → "compara com Balão R$25.000" | `simular_financiamento` × 3 calls across 3 turns | Exact match every turn (R$3.132,53 → R$2.812,08 → Linear R$2.812,08 vs Balão R$2.302,02+R$25.000@mês48) | Context correctly reused vehicle_value/down_payment across all 3 turns without being repeated; 2 structured blocks on turn 3, no duplication | REAL_MODEL_E2E ✅ |
| 11 | Novo Cliente | "...R$80.000/R$15.000/24m" → "Agora é outro cliente. Esquece esse cenário." | `simular_financiamento` then `iniciar_novo_cliente` | `scenario_reset: true` returned by the real backend; turn 1's `payment: null` correctly reported as "not returned, not estimating" (LOCAL_MOCK_DATA_LIMITATION) | Reset genuinely fires server-side, not a frontend-only illusion | REAL_MODEL_E2E ✅ |
| 12 | Negative/Guardrail | "...bem R$ 90.000, entrada R$ 20.000" + "Sim, é NOVOS" | `simular_financiamento` (TAXAS_SUBSIDIADAS) | `valid: false`, `message: "entrada mínima... 50%"` — prose matches exactly, no fabricated alternative | Clean rejection, no bypass attempt | REAL_MODEL_E2E ✅ |
| 13 | Score | "score do vendedor Ana Paula Ribeiro" | `consultar_score_vendedores` | Tool itself returned `{"error": "Não há competências cadastradas no Portal."}` — model relayed this honestly, invented no score | n/a | Dispatch: REAL_MODEL_E2E ✅ · Trust: DATA_DEPENDENT (this mock lacks a "competências" dataset the real tool also needs, beyond the sales/finance rows added in IA-V2-2) |
| 14 | Histórico | "histórico dos últimos 90 dias" | `analisar_historico_financiamento` | Exact match (`sample_size:2`, `sample_quality:"INSUFICIENTE"`, R$ 308.000,00 total, 100% penetração) — `sample_quality` safeguard correctly respected in prose | n/a | Dispatch: REAL_MODEL_E2E ✅ · Trust: DATA_DEPENDENT (synthetic 2-row fixture, same as IA-V2-2) |

## Financial engine parity

All numeric values that appeared in assistant prose were checked
against the same request/response's own `_homolog_debug.calls[].result`
(the tool's own authoritative JSON — there is no separate "engine" to
independently query, since the tool call *is* the engine call).
**Zero discrepancies found** across all 26 real calls: every currency,
percentage, date, and count in prose traces exactly to a field in the
tool's own result. No frontend recalculation anywhere (grep-verified,
same as prior phases).

One prose imprecision (not a fabricated **value**, a fabricated
**framing**): Scenario 14 said "prazo mais comum: 36 meses" from a
2-row sample where 36 and 48 months each occur once (a tie, not a
mode) — `HUMAN_REVIEW_RECOMMENDED`, low severity, doesn't change any
number shown.

## Internal leakage

Scanned all 26 reply texts for tool names, `_homolog_debug`,
`request_id`, Supabase/OpenAI internals, engine function names, model
identifiers: **zero matches**. Full list checked in
`real_uat_evidence.json` (local, not committed).

## Critical finding — structured-block field-contract mismatch (PRESENTATION)

While inspecting Scenario 5's real `ranking` block, its `items` use
`{position, name, sim_payment, sim_financed, sim_down_payment}` —
**not** the `{label, value, format}` shape
`assets/js/brabus-intelligence.js`'s `renderRanking()` expects. Traced
this across the real source (`grep 'type: "ranking"'` /
`'"score_ranking"'` / `'"score_breakdown"'` / `'"operations"'`,
8+ call sites) and confirmed it is systemic, not a one-off:

| Block type | Real field shape | Renderer expects | Status |
|---|---|---|---|
| `metrics` | `{label, value, format}` | same | ✅ matches |
| `comparison` | `a`/`b`.`items[]` = `{label, value, format}` | same | ✅ matches |
| `ranking` | `{dimension, metric, items[]:{position, name, <metric>}}` | `{label, value, format}` per item, `block.dimension`/`block.metric` as raw header text | ❌ **broken** |
| `score_ranking` | `items[]:{rank, seller, store, department, score, classification, sales, financed}` | `{label, value, format}` per item | ❌ **broken** |
| `score_breakdown` | flat top-level fields + `components[]:{label, value, max}}`, no `items` | `block.items` (doesn't exist) | ❌ **broken — renders empty** |
| `operations` | `items[]:{reference, date, store, department, model, financed_value, ...}` | `{label, value, format}` per item | ❌ **broken** |

Empirically confirmed by feeding Scenario 5's real captured block
straight through `window.NX_BRABUS_INTELLIGENCE_PAGE.renderStructuredBlock()`
(bypassing transport, so this is pure presentation-layer proof): the
table renders with literal `rate_term` / `sim_payment` as column
headers and every row's label blank, value `—`.

This was never caught before because IA-V2-1's fixture data was
authored to match the *renderer's own assumption* (uniform
label/value/format) rather than cross-checked field-by-field against
each block builder in source — `metrics` and `comparison` happen to
genuinely be label/value/format in the real backend, so those passed
by coincidence; `ranking`, `score_ranking`, `score_breakdown`, and
`operations` did not.

**Classification: PRESENTATION / STRUCTURED_BLOCK_CONTRACT_MISMATCH.**
Confirmed NOT touching the financial engine, business rules, or
security — purely how Portal V2 reads fields off an already-correct
backend response. Not fixed in this session: it affects 4 of 6 block
types across ~8 call sites and needs its own contract rediscovery per
type, which is out of scope for a "narrow, deterministic" inline fix
per this gate's own rules. Recommended as its own dedicated phase
before any human checkpoint that would surface `ranking`,
`score_ranking`, `score_breakdown`, or `operations` (Subsidiado,
Coparticipado multi-term/compare, Score, Score-ranking, Operações
Especiais, Histórico distribution modes). Scenarios that only ever
render `metrics`/`comparison` (Linear, Balão single, Coparticipado
single-term, Antecipação, Taxa Implícita, Histórico summary) are
unaffected.

## Environment notes (harness-only, not production)

- `tests/intelligence-v2-text/mock-backend.mjs` (tracked, already
  committed from IA-V2-2) was extended with two small fixture
  additions to unblock legitimate scenario coverage: a second
  Coparticipado model row (`"L200 TRITON HPE-S"`, since the model
  correctly refused the bare family name and my original mock had
  only that one generic row) and three `SEMESTRAL_ANUAL` rows (my
  mock previously had none at all for that product). The mock backend
  process was restarted to pick these up — `:8801` (real OpenAI) and
  `:8080` were never touched. **Left uncommitted** — this is a
  test-fixture-data change, not a presentation-defect fix, so it
  doesn't fit this gate's 0-or-1-commit rule for defect fixes; the
  human can commit it separately if useful for future local UAT runs.
- Two combinations (`Linear NOVOS, R$80.000, 18,75% down, 24m` and
  `Linear NOVOS, R$50.000, 0% down, 12m`) returned `payment: null`
  from the real engine — this local mock's Linear rate table is a
  small subset of the real production table; the model correctly
  reported "not returned, not estimating" rather than inventing a
  number, which is itself good evidence of the anti-hallucination
  guardrail holding even under a data gap.
