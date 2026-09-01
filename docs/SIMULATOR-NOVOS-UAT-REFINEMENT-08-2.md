# Simulador Novos — Human UAT Refinement 01 (PORTAL-NEXT-08.2)

Scope: **Simulador Novos UI only.** Seminovos untouched except one
unavoidable one-line fix to a shared presentation bug (see "Seminovos
guard" below). 0 change to any extracted engine, formula, coefficient,
campaign rule, entry rule, term availability, balloon mathematics,
Cash Conversion mathematics, parsing semantics, or rounding — verified
by hash (Gate 45/46).

## Human feedback (4 confirmed issues)

1. Single large `<select>` mode navigation — rejected.
2. Term/prazo buttons: awkward distribution, isolated partial last row.
3. Balloon value input too narrow; currency clipped/malformed
   ("R$ R$ ..." visible in the human's screenshot).
4. Balloon result doesn't communicate the actual payment structure.

## Change 1 — Mode navigation

Replaced the `<select>` with a grouped-button nav (`modeNavHtml()`/
`wireModeNav()`, local to `simulador-novos.js`), preserving the
existing three-group semantic taxonomy already present in the old
`<optgroup>` structure: **Financiamento** (Tradicional, Semestral/
Anual, Parcela Única, Financiamento Linear), **Campanhas**
(Financiamento Campanha, Taxas Subsidiadas, Semestral Triton/
Outlander), **Ferramentas** (Descobridor de Taxa, Antecipação de
Parcelas, Cash Conversion). No product was renamed.

Visual: `.smModeNav` — three flex groups (`flex: 1 1 220px`, wrapping
naturally at narrow widths, no horizontal scroll), each with a
`.smModeGroupLabel` (mono, uppercase, matches `.kpiLabel`'s existing
grammar) and a `.smModeButtons` row. Inactive: `--color-surface-2`
background, `--color-hairline-strong` border, secondary text — "subtle
dark surface, restrained border" per the brief. Active:
`rgba(238,75,87,.14)` background + `--color-accent-primary` border +
`#ffecec` text — the same Red Precision selection treatment already
used by `.segmented button.active` elsewhere in this codebase, reused
rather than invented.

**Accessibility**: plain `<button>` elements (native Tab order, native
Enter/Space activation — verified live, no custom keydown handler
needed). Each group is `role="group"` with `aria-label`. The active
button carries `aria-current="true"`. Deliberately **not** ARIA tabs —
a full tabs pattern requires tabpanel association and arrow-key roving
tabindex that would need to be implemented correctly to avoid "faking"
the role; a labeled button group with `aria-current` is an honest,
simpler, equally operable pattern for "select one of several related
views."

## Change 2 — Term/prazo selector

Replaced `.segmented` (inline-flex + wrap, which could leave an
accidental "6+1"-style isolated last row) with a new `.smTermSelectGrid`
CSS Grid whose column count is computed in JS
(`balancedColumns(containerWidth, itemMinWidth, n)`), not hardcoded.

Algorithm: compute how many `itemMinWidth`-sized columns fit
(`cap`); if all `n` terms fit, use `n` (single row). Otherwise search
column counts from `cap` down to 2, returning the first that leaves
**no isolated single-item last row** (`n % c === 0 || n % c >= 2`); if
none is found going down (small prime-ish `n`), search upward from
`cap+1` to `n` for the same condition. Verified deterministically for
every term count actually used in this Wave's scope (1, 3, 7, 8 — see
presentation tests) — always avoids a remainder of exactly 1.

Wired via `ResizeObserver` (`wireTermGrid`) so the grid recomputes on
real container resize, not just at initial render — verified at 390px
(7 Tradicional terms → 5+2, no orphan) in addition to the 1366px
desktop case.

Value reading reuses the **existing, unmodified**
`UI.getSegmentedValue()`/active-button convention — only the layout
component is new, not the state model.

## Change 3 — Balloon input: root cause + fix

**Audited the actual rendered DOM before editing**, per the brief's
own instruction, rather than guessing. Root cause of "R$ R$": the
balloon value input's blur handler reformatted the raw input value
using `UI.brl()`, which returns the **full currency string including
"R$"** (`n.toLocaleString('pt-BR',{style:'currency',...})`) — but the
input is wrapped in `.inputAffix`, whose own `.prefix` span **already**
renders a separate "R$" glyph. Writing `"R$ 20.000,00"` into the raw
value while the prefix span shows its own "R$" produced the visible
duplication. This is a **presentation** bug — `parseBRL()`'s own
parsing semantics were never touched.

Fix: added `UI.brlDigits(n)` (digits-only Brazilian formatting, no
currency symbol) and pointed every `.inputAffix`-input blur handler at
it instead of `UI.brl()`. This is the **same bug pattern** that also
existed in `wireMoneyMask()` (the shared helper Linear mode's
`nBem`/`nEntrada` fields use) — fixed there too, at the root, rather
than only patching the one field the human's screenshot happened to
show.

Layout: `.smBalloonRow` changed from an equal `1fr 1fr auto` split to
`92px minmax(150px,1fr) auto` — month is a short 1–2 digit field,
value gets the space it actually needs for a realistic BRL balloon
amount, remove stays compact. Verified: value field renders wider than
month field (150px vs 92px, live-measured). Stacks to a single column
below 480px (unchanged breakpoint, still correct at every required
viewport — verified 320/390/430 with 0 overflow).

## Change 4 — Balloon result: payment-structure story

**Presentation-only.** `balloonScheduleSummary(prazo, parcela,
validBaloes)` (local to `simulador-novos.js`, exposed read-only on
`window.NX_SIMULADOR_NOVOS_PAGE` for deterministic testing, same
pattern as `NX_SCORE_PAGE.classifyScoreBand`) derives entirely from
values the frozen engine already computed (`r.parcela`) plus the
already-validated balloon list (validation — duplicate months, out-of-
range months, non-positive values — is 100% the engine's own,
unchanged):

```
specials      = each balloon {mes, total: parcela + valor}, sorted by mes
regularCount  = prazo - (number of unique balloon months)
```

`regularCount` is correct for every case because the engine's own
`BALAO_DUPLICADO` validation already guarantees every balloon month in
a *valid* result is unique — no double-subtraction risk.

**Human's exact acceptance example, reproduced live** (100.000/20.000/
36x/balão mês 36/R$20.000): engine `parcela = 2.994,92` (unrounded,
untouched) →UI shows **"35x de R$ 2.994,92"** then **"Parcela 36 —
R$ 22.994,92"** (`= 2.994,92 + 20.000,00`, exact arithmetic on the
engine's own float, no new rounding). Screenshot:
`docs/screenshots-08-2/03-desktop-final-balloon-result.png`.

**Intermediate balloon** (36x, balão único mês 24): "34x"→ no, 35x de
R$X (regularCount=36-1=35) + "Parcela 24" special row — the brief's
own warning ("do not display 35x regular + parcela 24 as if additive")
is addressed by a standing footnote on every balloon result: *"Total
de parcelas do plano: {prazo}. Os meses com balão substituem o valor
da parcela regular naquele mês por um valor especial (parcela +
balão) — não são parcelas adicionais."* — present regardless of
final/intermediate/multiple, so the "replaces, not adds" relationship
is always stated, not just implied by the math.

**Multiple balloons** (36x, meses 12 e 24): "34x de R$2.777,25"
(regularCount=36-2) + two special rows (Parcela 12, Parcela 24), each
correctly computed from its own balloon amount. Verified live
(`docs/screenshots-08-2` — see presentation test suite for the
deterministic version of this same case).

**No balloon**: `calcTradicional()` explicitly branches — 0 balloons
renders the original "Parcela mensal" hero unchanged (Gate: "do not
force balloon-style presentation onto modes that do not use
balloons").

Supporting metrics (Entrada/Taxa aplicada/Limite de balão) remain,
demoted to the existing `secondaryGrid` below the new story — no
material information removed.

## Seminovos guard

**0 diff** to `simulador-seminovos.js` except the one unavoidable
line: the identical `UI.brl()`→`.inputAffix` duplication bug existed
in Seminovos' own balloon-row blur handler (copy-pasted from the same
original pattern) — fixed with the same one-line `UI.brlDigits()`
swap, verified live (`R$ 12.000,00`, single prefix). Confirmed via
`git diff`: exactly 1 line changed, nothing else. Seminovos'
`tests/simulador-seminovos-ui-binding-test.py` (29/29, unchanged
count) proves every other Seminovos behavior is byte-for-byte
unaffected. No Change-1/2/4 component (mode nav, term grid, balloon
story) was applied to Seminovos this Wave — it still uses its
original `<select>`/`.segmented`/"Parcela mensal"-only presentation,
exactly as PORTAL-NEXT-08.1 left it.

## Tests

```
tests/simulador-novos-presentation-test.py (NEW):        16/16
  - balloonScheduleSummary: no balloon / single final / single
    intermediate / multiple balloons / exact special-month math
  - balancedColumns: ample width (all fit), narrow width (no orphan,
    7 and 8 terms), 3-term and 1-term trivial cases
  - live DOM: single R$ prefix (no duplication), value field wider
    than month field, term-grid button counts (7 Tradicional / 3
    Periódico), no orphan row at 390px

tests/simulador-novos-ui-binding-test.py (updated):        43/43
  - select_mode() now clicks .smModeBtn instead of a <select>
  - trad_with_balloon case re-asserted against the new story
    presentation (regular count text + special-row total), not the
    old "Parcela mensal" label
tests/simulador-seminovos-ui-binding-test.py (unchanged):        29/29
tests/simulador-{novos,seminovos}-parity-test.py:                    40/40 + 24/24
tests/simulador-campanha-parity-test.py:                                 14/14
tests/cash-conversion-parity-test.py:                                        11/11
tests/simulador-cross-product-test.py:                                          5/5
Score/Coparticipado/Gestão/Dashbi/Landing/registry/scanner:                          all PASS
```

## Engine hash guard

```
simulador-shared.adapter.js / simulador-novos.adapter.js /
simulador-seminovos.adapter.js / financiamento-campanha.adapter.js /
cash-conversion.adapter.js:                     0 diff (byte-identical)
score/coparticipado/gestao/dashbi adapters+pages+score.css:    0 diff
```

## Responsive

Swept 320/360/390/430/768/1024/1366/1920 with the mode nav, term
selector, balloon input, and balloon result all active simultaneously
(fill bem/entrada, add a balloon, calculate) — 0 horizontal scroll at
every viewport, both before and after the balloon calculation.

## Screenshots

`docs/screenshots-08-2/`: `01-desktop-mode-nav.png`,
`02-desktop-term-selector.png`, `03-desktop-final-balloon-result.png`
(the human's exact acceptance example), `04-mobile-mode-nav.png`,
`05-mobile-balloon-input-result.png`. All captured and visually
inspected before declaring green (one early full-page capture showed
a compositing artifact from the shell's `position:fixed` dev badge
duplicating mid-page in a tall stitched screenshot — confirmed via a
single tall-viewport re-capture that this was a Playwright full-page
screenshot artifact, not a real rendering bug, and re-captured the
deliverable screenshots accordingly).

## Status

```
Simulator Engine:      PARITY_VERIFIED / FROZEN (0 diff this Wave)
Novos UI:                   MIGRATED / UAT_PENDING
Novos Business:                   PARITY_VERIFIED / HUMAN_UAT_PENDING
Novos Responsive:                       TECHNICALLY_GREEN / HUMAN_UAT_PENDING
```
Not marked `HUMAN_APPROVED` — this is UAT Refinement 01, not final
approval. `config/module-registry.json`'s `migrationStatus` for both
simulator modules is unchanged from PORTAL-NEXT-08.1
(`VISUAL_PARITY_PENDING`) — this Wave's own scope was UI refinement
within an already-`VISUAL_PARITY_PENDING` module, not a status
transition.
