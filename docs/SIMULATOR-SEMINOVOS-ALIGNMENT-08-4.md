# Simulador Seminovos — UX Alignment with Novos (PORTAL-NEXT-08.4)

Plus: Taxas Subsidiadas Rebate Percentage (Novos)

Status: implemented, tested, screenshotted, documented, committed locally. **Not pushed. Not deployed. Pending human UAT.**

## Part A — Novos: Taxas Subsidiadas Rebate %

### Gate 1 — denominator semantics (resolved without a business-decision STOP)

`calcularSubsidiadas()` (`assets/js/adapters/simulador-novos.adapter.js`) computes, per row:

```
rebateValor = financiado * row.rebate     // financiado = bem - entrada
```

`row.rebate` is an authoritative field taken directly from the frozen `tabelaRebates_FALLBACK` RATE_TABLE (e.g. `{"prazo":12,"taxa":0.0,"coef":0.09008,"rebate":0.1105}`) — it is not derived from anything else in the UI layer. The arithmetic conclusively proves the percentage's base is **financiado** (bem − entrada), not "valor do bem" as the brief's own conceptual example phrased it. Since the engine already exposes this exact percentage as an explicit field, the UI displays `row.rebate` as-is — no new derivation, no denominator invented.

### Gates 2-4 — presentation

Each Taxas Subsidiadas card's "Rebate — custo comercial" row now shows the percentage directly beneath the monetary value, in a right-aligned stack: smaller (10.5px vs. 14.5px), muted color, `pct2()` precision (matches the Portal's existing 2-decimal percentage convention, e.g. "11,05%"). Labeled "do valor financiado" (the correct, evidenced denominator). The comparison grid's 4/2/1 column layout is unaffected (verified at 1366px: still exactly 4 columns).

## Part B — Seminovos: navigation re-audit and UX alignment

### Gate 5/6 — applicability matrix (Novos 08.2/08.3 patterns → Seminovos)

| Pattern (Novos 08.2/08.3) | Seminovos applicability | Notes |
|---|---|---|
| Grouped-button mode nav (vs. `<select>`) | APPLICABLE | Ported as an independent copy — Seminovos' own smaller `MODES` list, `simulador-novos.js` untouched. |
| Balanced term grid | APPLICABLE (Tradicional only) | Linear/RATE_TABLE shows every term as a RESULT row, not an input selector — no term grid needed there. |
| Balloon input width/single R$ | ALREADY APPLIED | The `wireMoneyMask()`/`.smBalloonRow` fixes landed in the SHARED files during 08.2 and already covered Seminovos' balloon inputs. |
| Balloon payment-structure story | APPLICABLE | Ported as an independent copy over Seminovos' own `calcularTradicional()` output — 0 math reused from Novos (Seminovos' engine genuinely differs: vehicle-year table, 1.0 vs. 0.7 balloon-cap ratio). |
| Explicit special-payment schedule block | N/A | Its only Seminovos candidate (Semestral/Anual) is confirmed unreachable this Wave (see below) — nothing left to schedule. |
| Coefficient hidden / rate shown | ALREADY SATISFIED | Neither reachable Seminovos engine (Tradicional, RATE_TABLE) exposes a raw coefficient in its return value — both already return an authoritative `taxa`/`rate`. |
| Plano Coparticipado label + emphasis | N/A | Confirmed unreachable this Wave (see below) — not applicable. |
| Taxas Subsidiadas comparison grid | N/A | Seminovos' Subsidiadas engine is confirmed dead code (established in PORTAL-NEXT-08, unchanged this Wave). |

### Gate 6/21/22/25/34 — navigation re-audit (the significant finding this Wave)

Re-reading real production (`git show origin/main:modules/simulador-seminovos.html`) to build the matrix above surfaced a conflict between the current V2 build and actual production reachability. The main menu (`.premium-menu-grid-v2`) contains exactly 5 buttons, confirmed by direct markup inspection:

```
FINANCIAMENTO LINEAR    → openLinear            (reachable)
PLANO BALÃO              → openBalaoSafra        (reachable — Tradicional)
CALCULADORA DE TAXA      → openDescobridorTaxa   (reachable — Descobridor)
SIMULADOR DE ANTECIPAÇÃO → openAntecipacao       (reachable — Antecipação)
CASH CONVERSION           → openCashConversion   (reachable)
```

Three features the pre-08.4 V2 build exposed as live modes are **not reachable** in production, confirmed by the identical evidentiary standard PORTAL-NEXT-08 already used for the two previously-known dead features (top-level Linear tab, Taxas Subsidiadas — see `docs/SIMULATOR-ENGINE-DISCOVERY-08.md` Gate 33):

- **Semestral/Anual** (`#periodico`): full real markup and calc wiring exist inside the reachable `#simulatorScreen`, but its `<div class="tabs">` contains exactly one button — `<button class="tab active" data-tab="tradicional">Balão Tradicional</button>` — no tab ever activates `#periodico`.
- **Financiamento Campanha/Coparticipado** (`#campaignScreen`): the screen exists (containing the same byte-identical iframe engine Novos uses), but `id="openFinanciamentoCampanha"` — its entry button — does not exist anywhere in the HTML. Same silent no-op guard pattern as the confirmed-dead features (`if(openCampaign) openCampaign.addEventListener(...)`).
- **Semestral Triton** (`#semestralCopartScreen`): same — `id="openSemestralCopart"` does not exist.

Checked for dynamic injection (`createElement`/`insertAdjacentHTML`) that could add these buttons at runtime — none exists. All three are genuinely unreachable.

**Human decision (this Wave):** match production exactly. All three removed from the Seminovos V2 page. `calcularPeriodico`/`calcularSemestralTriton` remain in `simulador-seminovos.adapter.js` untouched — same Gate 3 completeness treatment already established for `calcularLinear`/`calcularSubsidiadas` — but this page no longer calls them.

### Gate 7/34 — Financiamento group (human clarification)

```
FINANCIAMENTO
[ Tradicional (Balão) ]  [ Linear ]
```

Exactly 2 buttons, matching the human's explicit clarification. "Linear" is the reachable nested RATE_TABLE engine (`calcularLinearRateTable`) — the label was changed from the previous "Financiamento Seminovos" to match production's own "FINANCIAMENTO LINEAR" menu card; the internal mode `id` (`ratetable`) is unchanged.

### Gate 8/24/25 — Ferramentas group

```
FERRAMENTAS
[ Descobridor de Taxa ]  [ Antecipação de Parcelas ]  [ Cash Conversion ]
```

All three confirmed reachable via their own main-menu buttons. No empty "Campanhas" group is rendered — `modeGroups()` derives groups purely from what's present in `MODES`, so removing all Campanhas-group items removes the group entirely, satisfying Gate 25 without special-casing.

### Gates 9-17 — presentation ported

- **Mode nav** (Gate 9): grouped buttons, `role="group"`, `aria-current`, visible focus — independent copy in `simulador-seminovos.js`, reusing the already-shared `.smModeNav`/`.smModeBtn` CSS (added to the shared stylesheet in 08.2, never scoped to Novos).
- **Term grid** (Gate 10): `balancedColumns()`/`termGridFieldHtml()`/`wireTermGrid()` ported as an independent copy, applied to Tradicional's 7-term Prazo selector. Verified: 7 terms at 1366px → single row; at 390px → 5+2 balanced (no orphan).
- **50x preserved** (Gate 10 note): RATE_TABLE's 9 terms (12/18/24/30/36/42/48/50/60) render unchanged as result rows — confirmed live against the frozen engine, 0 mismatches.
- **Money inputs / balloon width** (Gates 11-12): already correct — the `wireMoneyMask()` and `.smBalloonRow` fixes are in the shared files (08.2) and applied to Seminovos automatically. Verified: single R$ prefix, value field (150px) wider than month field (92px).
- **Balloon result story** (Gate 13): ported as an independent copy of `balloonScheduleSummary()`/`renderBalloonStory()`, fed Seminovos' own `calcularTradicional()` output. Verified live: 36x term, balloon at month 36 of R$20.000 → "35x de R$3.105,55" + "Parcela 36 — R$23.105,55" (Seminovos' own rate, not Novos').
- **Intermediate/multiple balloons** (Gate 14): `balloonScheduleSummary()` is generic pure presentation over `(prazo, parcela, baloes)` — verified with dedicated presentation-test cases (single final, single intermediate, multiple).
- **Vehicle year** (Gate 15): untouched — `sAno` remains a visible, required field in the Tradicional form.
- **Linear composition/hierarchy** (Gates 16-17): unchanged from 08.1 (already primary-result-first: term grid, then financed-amount footnote) — already consistent with the Red Precision hierarchy principle, no material change needed.

### Gate 18 — periodic/special schedules

N/A this Wave. The only Seminovos candidate for a schedule block (Semestral/Anual) is confirmed unreachable (see Gate 6/21/22 above) — there is nothing left to schedule.

### Gates 19-20 — coefficient/rate visibility

Audited both reachable engines: neither `calcularTradicional()` (`taxa: plano.taxa`) nor `calcularLinearRateTable()` (`rate` per term) exposes a raw coefficient to the UI — both already return an authoritative rate, unchanged from 08.1. Nothing to hide.

## Tests

| Suite | Result |
|---|---|
| Simulador Seminovos UI-binding goldens (rewritten scope) | 25/25 |
| Simulador Seminovos presentation tests (new) | 25/25 |
| Simulador Seminovos parity (engine-level, untouched) | 24/24 |
| Simulador Novos UI-binding goldens | 43/43 |
| Simulador Novos presentation tests | 36/36 (32 from 08.3 + 4 new Rebate % cases) |
| Campanha (shared engine) | 14/14 |
| Cross-product | 5/5 |
| Cash Conversion | 11/11 |

The Seminovos UI-binding suite's scope changed to match the reduced navigation: the Periodico (4 cases) and SemestralTriton (3 cases) sections were removed (those modes no longer exist in the page); `trad_with_balloon` now verifies the new balloon-story presentation instead of a plain "Parcela mensal" label; new Gate 22/25/34 assertions verify the dead/unreachable features are absent and the Financiamento group contains exactly 2 buttons.

## Engine and isolation guards

- **Engine hash guard**: sha256 of every adapter (Novos, Seminovos, shared, Cash Conversion, Campanha), `simulador-seminovos.adapter.js` included, plus every frozen Portal module (Score, Coparticipado, Gestão, Dashbi, Landing) — **0 diff**. `simulador-seminovos.adapter.js` itself is completely unchanged; only the PAGE (`simulador-seminovos.js`) and shared CSS were touched.
- **Responsive sweep**: 8 viewports (320/360/390/430/768/1024/1366/1920) × 5 modes — 0 horizontal overflow, 0 console errors.
- **Accessibility**: result region `aria-live="polite"`/`aria-atomic="true"` preserved; mode groups `role="group"` with `aria-label`; focus-visible outline confirmed on mode buttons; term-grid/schedule markers use the same non-interactive conventions already established.
- **Console/network**: 0 console errors across every test run and manual verification; 0 backend/production calls (FALLBACK tables only, per PORTAL-NEXT-08 architecture).

## Screenshots

`docs/screenshots-08-4/`, all captured at a tall single-viewport `full_page=False`, visually inspected before acceptance:

1. `01-novos-subsidiadas-rebate-pct-desktop.png` — Rebate % on every card, 4-column grid intact
2. `02-novos-subsidiadas-rebate-pct-mobile.png` — same, single column
3. `03-seminovos-nav-desktop.png` — Financiamento(2)/Ferramentas(3), no Campanhas group
4. `04-seminovos-tradicional-form-desktop.png` — balanced term grid, vehicle year field
5. `05-seminovos-balao-result-desktop.png` — "35x de R$3.105,55" + "Parcela 36" story, Seminovos' own values
6. `06-seminovos-linear-result-desktop.png` — all 9 terms incl. 50x
7. `07-seminovos-nav-mobile.png` — nav wraps naturally
8. `08-seminovos-balao-mobile.png` — balloon story stacked, readable
9. `09-seminovos-linear-mobile.png` — form stacks intentionally

Gate 38's visual question — "Does Seminovos look like the same premium product as Novos, while clearly containing a simpler/different financing offering?" — answered YES: same typography, spacing, button/field/term-grid/balloon-story conventions throughout, with a visibly smaller, simpler product structure (2 Financiamento items vs. Novos' 4).

## Scope discipline

- 0 change to any engine/formula/coefficient/rate/rebate/campaign rule/entry rule/term set/vehicle-year rule/RATE_TABLE semantics/special-payment formula/Cash Conversion math/rounding.
- `simulador-novos.adapter.js`, `simulador-seminovos.adapter.js`, `simulador-shared.adapter.js`, `cash-conversion.adapter.js`, `financiamento-campanha.adapter.js`: byte-identical (hash-verified).
- No other Portal module, auth flow, staging, or production system touched.
- `origin/main` unchanged (`2f17eb2341c5cc14aa8710aa044103002ca572a9`).
- Isolation sweep across sibling worktrees: 0-line diff against the PORTAL-NEXT-08.3 baseline.
- Local commit only — no push, no deploy.

Human UAT on both parts of this Wave is required before any further simulator work proceeds.
