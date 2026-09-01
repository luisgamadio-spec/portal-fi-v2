# Simulador Novos — Human UAT Refinement 08.3

Nomenclatura + Cronograma + Parcela Única — Coparticipado + Taxas Subsidiadas

Status: implemented, tested, screenshotted, documented, committed locally. **Not pushed. Not deployed. Pending human UAT.**

## 1. Human feedback addressed

Following the human-confirmed resolution of PORTAL-NEXT-08.2 (mode navigation, term/prazo distribution, balloon input width, balloon result clarity), a second round of UAT feedback identified 5 new issues on Simulador Novos. All 5 are addressed in this Wave. Zero changes were made to any engine, formula, coefficient, rate, rebate rule, campaign rule, entry rule, term set, special-payment math, Cash Conversion math, rounding, or validation logic — every change below is presentation-only, verified by an engine hash guard (see §6).

## 2. Change 1 — Label correction: "Plano Coparticipado"

The product previously labeled "Financiamento Campanha" is renamed, in every user-visible surface, to **"Plano Coparticipado"**. This is a presentation/label change only:

- `MODES` entry `label` changed from `'Financiamento Campanha'` to `'Plano Coparticipado'`.
- `MODE_DESC.campanha` updated to reference the new name.
- The internal mode `id` (`campanha`), the adapter function names (`calcularCampanha`, etc.), the fixture identifiers, and every other internal identifier are **unchanged** — renaming those was explicitly out of scope and unnecessary.

Verified: 0 occurrences of the string "Financiamento Campanha" anywhere in the rendered Novos UI (presentation test, §7).

## 3. Change 2 — Explicit special-payment schedules

Products with periodic or special payments (Semestral, Anual, Parcela Única, Semestral Triton/Outlander) previously required the user to infer which installment numbers carried a special payment (e.g. that "semestral" meant months 6, 12, 18…). A new reusable, presentation-only component — `scheduleBlockHtml()` — now renders a "Cronograma do plano" block under the result showing:

- **Prazo total** (financing term)
- **Periodicidade** (Semestral / Anual / Parcela única)
- The exact installment numbers carrying a special payment, as a row of non-interactive marker chips (e.g. `6 · 12 · 18 · 24 · 30 · 36`)

All 9 Novos engines were audited for applicability. Applied to:

| Mode | Source of the marker sequence |
|---|---|
| Periódico (Semestral) | `NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico(...).meses` |
| Periódico (Anual) | `NX_SIMULADOR_NOVOS_ADAPTER.calcularPeriodico(...).meses` |
| Parcela Única | `NX_SIMULADOR_NOVOS_ADAPTER.calcularParcelaUnica(...).plano.prazo` (single marker) |
| Semestral Triton/Outlander | `NX_SIMULADOR_SHARED.SEMESTRAL_TRITON_MESES` |

The component performs **no financial calculation** — it only formats numbers already returned by the frozen adapters. The sequence is never hardcoded in the UI layer; it is read live from the engine/config in every case. Markers are rendered as `<span role="listitem">` inside a `<div role="list">`, deliberately not `<button>`, so screen readers announce them as an informational list rather than implying interactivity.

Other Novos modes (Tradicional, financing without special payments) do not render this block — there is nothing to schedule.

## 4. Change 3 — Parcela Única: rate instead of coefficient

The internal financial coefficient is no longer shown to the user. In its place, the secondary metrics grid now shows **"Taxa da tabela"** — the authoritative rate for the applicable table, taken directly from `NX_SIMULADOR_NOVOS_ADAPTER.calcularParcelaUnica(...).taxa`.

This is not a derived value: the adapter's `taxa` field comes from the same source table as the coefficient but is not computed *from* the coefficient — it is an independent, authoritative field already returned by the frozen engine (confirmed by inspecting the extracted PORTAL-NEXT-08 engine source).

**Unit suffix**: no "a.m." / "a.a." suffix is appended, because the source does not prove the period. This is not a guess — production's own saved source (`portal-next-v2/../PORTAL-NEXT-08/.source/simulador-novos-origin-main.html`) labels this exact value (`id="uTaxa"`) as "Taxa da tabela" with a bare percentage and no period suffix. The V2 presentation matches production's own convention exactly, avoiding both an invented suffix and an unnecessary STOP for a business decision that production itself had already answered.

The coefficient remains available internally to the engine (unchanged, untouched) — it is simply not rendered in the UI.

## 5. Change 4 — Plano Coparticipado: financial emphasis

**Rebate Brabus** and **Valor Final de Venda** — the two figures the human flagged as needing more visual weight — are promoted out of the standard secondary metrics grid into a dedicated emphasis block (`.smEmphasisPair`), styled with the Red Precision system's existing financial-emphasis vocabulary: stronger typography weight/size and a subtle emphasized surface with a border accent (`.smEmphasisCard` / `.smEmphasisCardPrimary` for Valor Final de Venda, the more decisive figure). No new colors, no glow effects, no marketing banners were introduced. The underlying values are unchanged — this is purely a layout/typography promotion of two already-computed numbers.

## 6. Change 5 — Taxas Subsidiadas: comparison card grid

The previous large vertical stack of comparison rows is replaced with a compact card grid (`.smSubsidiadaGrid`), grouped by taxa (`.smSubsidiadaGroup`), one card per prazo. Layout:

- Desktop: 3–4 cards per row
- Tablet: 2 cards per row
- Mobile: 1 card per row
- No horizontal carousel or scroll at any breakpoint

Each card preserves every material value the stacked layout showed: Taxa (badge in the card header, plus the taxa group heading), Prazo, Parcela, Rebate — custo comercial, Valor Final de Venda. The redundant "Simulado" text — previously shown identically on every row regardless of outcome — is removed; a pill now appears only when it conveys real information: the engine's own pre-existing `melhor` field (unchanged, not invented this Wave — traced back to production's own `montaDadosSubsidiadas()` ranking logic extracted in PORTAL-NEXT-08), or a genuine viability verdict once a minimum sale value is supplied. No new "MELHOR"/"RECOMENDADO" badge was invented.

The desktop input-rail width is reduced for this mode only (`.smGridStacked`, toggled additively via JS only when `currentMode === 'subsidiadas'`) so the result grid gets full width — the base `.smGrid` rule shared with Seminovos is untouched.

## 7. Tests

| Suite | Result |
|---|---|
| Simulador Novos UI-binding goldens | 43/43 |
| Simulador Novos presentation tests | 32/32 (16 from 08.2 + 16 new this Wave) |
| Campanha suite | 14/14 |
| Cross-product suite | 5/5 |
| Cash Conversion suite | PASS |
| Simulador Seminovos UI-binding goldens | 29/29 (unchanged — proof of zero Seminovos impact) |

New presentation tests this Wave verify, against live adapter calls (never hardcoded): the label rename and absence of the old label; the Semestral 36x and 24x schedules and the Anual 36x schedule against `calcularPeriodico(...).meses`; the Parcela Única single marker against `plano.prazo`; the absence of "Coeficiente" and presence of "Taxa da tabela" with the correct value and no unit suffix; the Triton/Outlander markers against `NX_SIMULADOR_SHARED.SEMESTRAL_TRITON_MESES`; the Coparticipado emphasis block structure; the Subsidiadas card count and a full data-parity cross-check of every card against `calcularSubsidiadas(...).rows`; and a check that each card renders exactly 3 metric rows (no duplication).

## 8. Engine and isolation guards

- **Engine hash guard**: sha256 of every Novos/Seminovos adapter, the Seminovos page, and every frozen Portal module (Score, Coparticipado, Gestão, Dashbi, Landing) captured before and after implementation — **0 diff**.
- **Seminovos preservation**: `assets/js/simulador-seminovos.js` and `assets/js/simuladores-shared.js` are byte-identical to their pre-Wave state — **0 diff**. Seminovos' own 29/29 UI-binding suite confirms unchanged behavior.
- **Responsive sweep**: 8 viewports × all 6 modes — 0 horizontal overflow.
- **Isolation baseline**: `git status --short` swept across every sibling worktree of `portal-financiamento-brabus-secure` — 0-line diff against the PORTAL-NEXT-08.2 baseline.
- **origin/main**: confirmed unchanged at `2f17eb2341c5cc14aa8710aa044103002ca572a9`.

## 9. Screenshots

All captured at a tall single-viewport `full_page=False` (avoids a known Playwright full-page compositing artifact with the shell's fixed dev badge), visually inspected before being accepted:

1. `01-desktop-semestral-36x-schedule.png` — Semestral 36x schedule block, markers `6 · 12 · 18 · 24 · 30 · 36`
2. `02-desktop-parcela-unica.png` — Parcela Única, coefficient absent, "Taxa da tabela" shown
3. `03-desktop-coparticipado-emphasis.png` — Rebate Brabus / Valor Final de Venda emphasis block
4. `04-desktop-subsidiadas-comparison.png` — comparison card grid, desktop
5. `05-mobile-subsidiadas.png` — comparison card grid, mobile (1 card/row)
6. `06-mobile-semestral-schedule.png` — schedule block, mobile

## 10. Scope discipline

- Simulador Seminovos was **not** redesigned this Wave.
- No engine, formula, coefficient, rate, rebate rule, or validation was changed.
- No other Portal module, auth flow, staging, or production system was touched.
- Production repositories (`portal-financiamento-brabus-secure`, `portal-financiamento-brabus`) remain untouched; `origin/main` unchanged.
- This Wave's commit is **local only** — no push, no deploy.

Human UAT on this Wave's 5 changes is required before any further simulator work proceeds.
