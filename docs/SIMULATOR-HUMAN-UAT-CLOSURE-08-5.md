# Simulator Human UAT Closure (PORTAL-NEXT-08.5)

Status: **CLOSED.** Documentation-only Wave — 0 implementation change (hash-verified).

## 1. Approval authority (Gate 1)

The sole authority for this closure is the human's own explicit statement:

> "Fechamos os simuladores."

This is not inferred from automated test results, screenshots, or "technically green" reports — those are necessary but insufficient preconditions, never a substitute for human judgment (the same standing rule applied to every other module in this engagement — Landing, Coparticipado, Gestão, Dashbi).

This closes the UAT cycle that ran:

- **PORTAL-NEXT-08** — engine discovery + extraction + parity harness (9 Novos engines, 6 reachable + 2 dead Seminovos engines).
- **PORTAL-NEXT-08.1** — native V2 functional UI built on the frozen engines.
- **PORTAL-NEXT-08.2** — Novos UAT Refinement 01 (mode nav, term grid, balloon input width, balloon payment-structure story).
- **PORTAL-NEXT-08.3** — Novos UAT Refinement 02 (Plano Coparticipado label, explicit special-payment schedules, Parcela Única rate, Coparticipado emphasis, Taxas Subsidiadas comparison grid).
- **PORTAL-NEXT-08.4** — Novos Rebate %, Seminovos navigation re-audit and UX alignment with Novos' approved patterns.

## 2. Final status matrix (Gate 2/3)

```
SIMULATOR ENGINE                          PARITY_VERIFIED / FROZEN   (unchanged designation)

SIMULADOR NOVOS — Business/Functional     HUMAN_APPROVED / FROZEN
SIMULADOR NOVOS — UI                      HUMAN_APPROVED / FROZEN
SIMULADOR NOVOS — Responsive              HUMAN_APPROVED / FROZEN

SIMULADOR SEMINOVOS — Business/Functional HUMAN_APPROVED / FROZEN
SIMULADOR SEMINOVOS — UI                  HUMAN_APPROVED / FROZEN
SIMULADOR SEMINOVOS — Responsive          HUMAN_APPROVED / FROZEN
```

**Gate 3 — engine status is not casually rewritten.** The extracted mathematical engines (`simulador-novos.adapter.js`, `simulador-seminovos.adapter.js`, `simulador-shared.adapter.js`, `financiamento-campanha.adapter.js`, `cash-conversion.adapter.js`) keep their own, separate `PARITY_VERIFIED/FROZEN` designation, established in PORTAL-NEXT-08 and unchanged since (byte-identical through every subsequent Wave — see §7). Human approval this Wave applies to the migrated functional/UI/responsive experience built on top of those engines, not to a re-verification of the engines' own mathematical parity. These are two distinct claims and are recorded separately in `config/module-registry.json` (`migrationStatus` for the UI/business dimensions vs. `engineExtractionNote`'s own "ENGINE STATUS" line).

## 3. Novos — approved final contract (Gate 4)

High-level summary; full implementation detail lives in the Wave docs referenced below.

- **Navigation**: visible button-based mode nav (`.smModeNav`/`.smModeBtn`, `role="group"`/`aria-current`), replacing the originally-built `<select>` — human-rejected in 08.2 UAT.
- **Semantic groups**: Financiamento (Tradicional/Balão, Semestral/Anual, Parcela Única, Financiamento Linear), Campanhas (Plano Coparticipado, Taxas Subsidiadas, Semestral Triton/Outlander), Ferramentas (Descobridor de Taxa, Antecipação de Parcelas, Cash Conversion).
- **Term selector**: balanced-column grid (`balancedColumns()`), no isolated single-item last row at any width.
- **Tradicional/Balão**: payment-plan storytelling ("35x de R$X" + "Parcela 36 — R$Y") instead of a raw table, derived entirely from the frozen engine's own `parcela` + validated balloon list.
- **Explicit special-payment schedules**: Semestral/Anual, Parcela Única, and Semestral Triton/Outlander show prazo total, periodicidade, and the exact installment numbers carrying a special payment — derived live from the engine, never hardcoded.
- **Parcela Única**: internal coefficient hidden; the engine's own authoritative `taxa` field shown instead ("Taxa da tabela"), evidenced against production's own labeling convention, no invented unit suffix.
- **Plano Coparticipado**: visible product label (renamed from "Financiamento Campanha"); Rebate Brabus and Valor Final de Venda promoted to a financial-emphasis block.
- **Taxas Subsidiadas**: comparison-grid presentation (replacing a stacked-row layout), 4/2/1 responsive column structure, each card showing Parcela, Rebate — custo comercial (with its Rebate % as quiet secondary text, denominator = `financiado`, not `bem` — see §6), and Valor Final de Venda.
- **Cash Conversion**: preserved unchanged as its own mode, shared engine.
- **Responsive**: 0 horizontal scroll requirement, verified at 8 viewports.

Full detail: `docs/SIMULATOR-UI-MIGRATION-08-1.md`, `docs/SIMULATOR-NOVOS-UAT-REFINEMENT-08-2.md` (referenced by 08.3's own doc), `docs/SIMULATOR-NOVOS-UAT-REFINEMENT-08-3.md`, `docs/SIMULATOR-SEMINOVOS-ALIGNMENT-08-4.md` (Part A).

## 4. Seminovos — approved final contract (Gate 5)

```
FINANCIAMENTO
[ Tradicional (Balão) ]  [ Linear ]

FERRAMENTAS
[ Descobridor de Taxa ]  [ Antecipação de Parcelas ]  [ Cash Conversion ]
```

Only these two products belong in the Seminovos Financiamento group (explicit human clarification, PORTAL-NEXT-08.4). "Linear" is the reachable nested RATE_TABLE engine, labeled to match production's own "FINANCIAMENTO LINEAR" menu card (internal mode id unchanged from `ratetable`). The three Ferramentas tools are preserved per their confirmed production reachability, unchanged since PORTAL-NEXT-08.1.

Presentation ported from Novos' approved patterns as independent copies (0 Novos file touched, 0 Seminovos math reused by Novos or vice versa): grouped mode nav, balanced term grid (Tradicional's 7 terms), and the balloon payment-structure story (fed by Seminovos' own `calcularTradicional()` output).

Full detail: `docs/SIMULATOR-SEMINOVOS-ALIGNMENT-08-4.md` (Part B).

## 5. Seminovos non-reachable features — explicit production-parity decision, not accidental omission (Gate 6)

The following are **not exposed** in the approved Seminovos V2, by deliberate decision, not oversight:

- **Semestral / Anual**
- **Financiamento Campanha / Coparticipado**
- **Semestral Triton**

All three were exposed in the V2 build through PORTAL-NEXT-08.1–08.3. PORTAL-NEXT-08.4's Gate 5 applicability-matrix audit re-read real production (`git show origin/main:modules/simulador-seminovos.html`) and found all three genuinely unreachable — 0 real click path — by the identical evidentiary standard already used for the two previously-confirmed dead features (top-level Linear tab, Taxas Subsidiadas):

- Semestral/Anual's `#periodico` panel has full real markup, but its parent screen's only tab button targets `data-tab="tradicional"` — no tab ever activates it.
- Campanha/Coparticipado's `#campaignScreen` and Semestral Triton's `#semestralCopartScreen` both exist as real screens, but their entry buttons (`id="openFinanciamentoCampanha"`, `id="openSemestralCopart"`) do not exist anywhere in production's HTML.

This was reported to the human as HUMAN DECISION REQUIRED (the conflict PORTAL-NEXT-08.4's own brief anticipated at its Gate 21). The human's decision — recorded in this closure — was to **match production exactly**: all three removed from the Seminovos V2 UI. `calcularPeriodico()`/`calcularSemestralTriton()` remain in `simulador-seminovos.adapter.js`, untouched, for function-inventory completeness (same treatment already given to `calcularLinear()`/`calcularSubsidiadas()`); the page simply no longer calls them.

## 6. Dead-feature distinction preserved (Gate 7)

Two separate concepts, never collapsed into one:

- **The reachable Seminovos "Linear" experience** = the nested RATE_TABLE engine (`calcularLinearRateTable()`), year × entry-band lookup, its own PMT/IOF formula, includes the authoritative 50x term. This IS exposed in the approved V2, labeled "Linear".
- **The separate, confirmed-dead legacy top-level "Financiamento Linear" tab** (`calcularLinear()`, `tabelaLinear`) — 0 matching production DOM markup (`#lValorBem`/`#lEntrada`/`#lResultados` do not exist), only defensively-guarded JS that silently no-ops. This is NOT exposed and was never exposed in any V2 Wave.

The approved V2 retains only the reachable engine; the dead legacy feature stays unexposed.

## 7. Business differences preserved — UI consistency ≠ engine identity (Gate 8)

Novos and Seminovos do **not** share one common financing formula. UI-level presentation consistency (mode nav, term-grid, balloon story visual grammar) is deliberate and approved; the underlying calculations remain genuinely independent, per `docs/SIMULATOR-ENGINE-DISCOVERY-08.md`'s Gate 6/7/49 comparison matrix:

- Seminovos' Tradicional/Balão carries a **vehicle-year dimension** (`faixaAnoTrad`) Novos has no concept of at all; table shape, values, and the balloon-cap ratio (1.0 vs. 0.7) genuinely differ.
- Seminovos' RATE_TABLE ("Linear") engine has **no Novos equivalent whatsoever** — different lookup dimension (year × entry band, not model), its own fee structure (a 2.5% "seguro proteção" surcharge Novos never applies), and the authoritative 50x term Novos never offers.
- Semestral Triton's *presentation* is shared (both consume `FATOR_SEMESTRAL_TRITON`/`MESES` from `simulador-shared.adapter.js`), but the final `valorFinalVenda` formula genuinely differs: Novos computes `bem − rebateBrabus` (Brabus' share only, with a per-model `entradaMinima` override); Seminovos computes `bem − rebateTotal` (the full Brabus+HPE rebate, flat 60% entry, no override).

## 8. Rebate percentage contract (Gate 9)

Preserved verbatim from PORTAL-NEXT-08.4, no recalculation this Wave:

```
Rebate % (Novos Taxas Subsidiadas) = row.rebate   (authoritative engine field)
Denominator                        = financiado = bem − entrada
```

Proven, not assumed: `calcularSubsidiadas()` computes `rebateValor = financiado * row.rebate` — the engine's own `tabelaRebates_FALLBACK` RATE_TABLE stores `rebate` as an independent, authoritative field, not derived from `coef` or any other value. The denominator is conclusively `financiado` (bem − entrada), **not** "valor do bem" (the total vehicle value) — that phrasing appeared only in the brief's own illustrative conceptual example, not in engine semantics.

## 9. What FROZEN means (Gate 10)

After this closure, no future Wave may change, as a side effect of unrelated work:

- Simulator business logic (any engine/formula/coefficient/rate/rebate/campaign rule/entry rule/term set/vehicle-year rule/RATE_TABLE semantics/special-payment formula/Cash Conversion math/rounding).
- Simulator UI composition (navigation, mode grouping, labels, form/result layout).
- Simulator responsive behavior.
- Simulator financial presentation (hierarchy, emphasis, schedule/story components).

Any further functional or visual Simulator change requires **explicit new human authorization** — a Design System Change Proposal + approval, the same Freeze rule already governing Landing, Coparticipado, Gestão, and Dashbi.

**Named future exception**: a planned, separately-authorized **Visual Polish / Motion** transversal Wave may later touch Simulator *presentation* only, when explicitly authorized at that time. That future Wave must preserve business rules, financial outputs, and the approved information hierarchy/UX structure documented in §3/§4 above. No motion work is implemented by this Wave.

## 10. Engine and implementation hash freeze (Gate 11)

Hashes captured before any documentation change in this Wave, for:

```
assets/js/adapters/cash-conversion.adapter.js
assets/js/adapters/coparticipado.adapter.js
assets/js/adapters/dashbi.adapter.js
assets/js/adapters/financiamento-campanha.adapter.js
assets/js/adapters/gestao.adapter.js
assets/js/adapters/score.adapter.js
assets/js/adapters/simulador-novos.adapter.js
assets/js/adapters/simulador-seminovos.adapter.js
assets/js/adapters/simulador-shared.adapter.js
assets/js/business-adapter-boundary.js
assets/js/simuladores-shared.js
assets/js/simulador-novos.js
assets/js/simulador-seminovos.js
assets/css/simuladores.css
assets/js/coparticipado.js
assets/js/score.js
assets/js/gestao.js
assets/js/dashbi.js
assets/js/landing.js
```

This Wave touched **0** implementation files (JS/CSS) — only documentation (`docs/`, `config/module-registry.json`, `REPORT.md`) and this closure record. Re-hashed after all documentation changes: **0 diff** across every file above.

```
Simulator implementation diff:  0
Engine diff:                    0
```

## 11. Regression (Gate 12)

Run against the frozen implementation, not modified to force a pass:

```
Novos UI Goldens:              43/43
Novos Presentation:            36/36
Seminovos UI Goldens:          25/25
Seminovos Presentation:        25/25
Novos Engine Parity:           40/40
Seminovos Engine Parity:       24/24
Campanha/Coparticipado Parity: 14/14
Cross-product:                  5/5
Cash Conversion:               11/11
```

All counts match this Wave's own brief expectations exactly — no test was edited to reach these numbers.

## 12. Other frozen modules (Gate 13)

```
Landing:         0 diff
Score:           0 diff
Coparticipado:   0 diff
Gestão:          0 diff
Dashbi:          0 diff
```

## 13. Registry and status reconciliation (Gate 14/15/18)

`config/module-registry.json`: `simulador-novos` and `simulador-seminovos` entries' `migrationStatus` updated `VISUAL_PARITY_PENDING` → `HUMAN_APPROVED`; a new `humanApprovalNote` field added to each recording the approval authority, the 3-dimension breakdown, the distinct engine-status designation, and the FROZEN rule (same convention already used for Landing/Coparticipado/Gestão/Dashbi). No other module's status touched.

`docs/MIGRATION-STATUS.md`: current-status summary table updated for both Simulator rows; the "Standing blockers carried forward" Simulador bullet reclassified from open blocker to RESOLVED/CLOSED; a new `## PORTAL-NEXT-08.5 addendum` section appended. Every prior Wave's addendum (03 through 07.7C) preserved verbatim — no historical UAT_PENDING state was rewritten.

Status-consistency sweep (Gate 18): searched every current, non-Wave-specific doc referencing "simulador" (`docs/ARCHITECTURE.md`, `docs/LANDING-CONTENT-MAP.md`, `config/landing-groups.json`, `docs/DS-CHANGE-PROPOSAL-NO-HORIZONTAL-SCROLL-01.md`, `docs/COPARTICIPADO-ENGINE-AUDIT.md`) — none contain a conflicting current-authoritative status string (all are structural/routing references, not status claims). No changes needed there.

## 14. Next module discovery (Gate 19 — discovery only, nothing implemented)

Per the now-reconciled `config/module-registry.json`:

```
shell-admin           Portal Shell / MASTER Admin Panel   NOT_MIGRATED   risk HIGH
salarios-comissoes    Salários / Comissões                NOT_MIGRATED   risk MEDIUM
brabus-intelligence   Brabus F&I Intelligence (AI+Voice)   NOT_MIGRATED   risk HIGH — UNSCHEDULABLE
                                                                          (3 named blockers open)
```

Also noted for completeness, not `NOT_MIGRATED`: `score` remains `UAT_PENDING` for Business/Functional only (its Design System score-band conflict, open since PORTAL-NEXT-04, unresolved); its Responsive/Score Band Business Rule/Score Band Visual dimensions are already separately `HUMAN_APPROVED/FROZEN`.

No module was selected, scoped, or implemented this Wave. PORTAL-NEXT-09 was not started.

## 15. Production isolation (Gate 20)

```
Production repo:      UNTOUCHED
origin/main:           UNCHANGED (2f17eb2341c5cc14aa8710aa044103002ca572a9)
V2 remote:              NONE
Push:                    NO
Deploy:                   NO
Backend calls:              0
Production calls:            0
```

Sibling-worktree isolation sweep: 0-line diff against the PORTAL-NEXT-08.4 baseline.
