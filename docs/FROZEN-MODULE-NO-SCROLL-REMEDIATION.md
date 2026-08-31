# Frozen Module No-Horizontal-Scroll Remediation Manifest (PORTAL-NEXT-07.6, Gate 66)

Every change this Wave, why it's the minimum required, and its parity
proof. Companion to `FROZEN-MODULE-NO-SCROLL-INVENTORY.md` (before-state)
and `FROZEN-MODULE-RESPONSIVE-INFORMATION-PARITY.md` (per-field parity).

## Landing — `assets/css/landing.css`

**Surface**: mobile category nav (`.fNav` at ≤768px).
**Root cause**: `overflow-x:auto` on the nav row, items `flex-shrink:0` —
a hidden horizontal scrollbar carrying the 5 category labels sideways.
**Solution**: `flex-wrap:wrap` (replaces `overflow-x:auto`); gap adjusted
to `10px 24px` for a sane 2-axis wrap.
**Why minimal**: same `.fNavItem` markup, same click handlers, same
active-state styling — only the container's wrap behavior changed.
**Information/business parity**: 100% — all 5 labels always visible,
0 JS touched.
**Desktop fidelity**: 0 change — the mobile-only media query rule was the
only edit; `landing-composition-regression.py`'s own 1366/1920 checks
(fNav width proportion, canvas region, nav-not-compressed) still pass
byte-for-byte (0.0pp drift).
**Mobile result**: nav reflows onto 2-3 lines at 320-768px, 0 horizontal
scroll, `landing-composition-regression.py`'s own 390/430 "no horizontal
overflow" checks pass.

**Not remediated (classified SAFE, not a defect)**: `.fCanvasInner`/
`#landingModuleDetail`'s constant 18px child-scrollWidth delta, present
at every viewport including 1366/1920. Traced to `.fModuleBlock{margin:0
-18px}` — an intentional hover-highlight bleed rectangle, already fully
contained by the ancestor `.fCanvas{overflow:hidden}`. Produces 0 visible
or functional scrollbar at any viewport (proved, not assumed: document-
level `scrollWidth<=clientWidth` passes at every one of the 7 measured
widths). Left untouched — "fixing" it would mean shrinking the intentional
hover-bleed design, a cosmetic change with 0 user-facing benefit.

## Score — `assets/css/score.css`, `assets/js/score.js`

**Surface**: vendedor ranking table (`.scTableWrap`/`.scTable`).
**Root cause**: no `table-layout:fixed` — auto-layout sized every column
to its widest un-wrapped content (measured: 460px content in a 286-396px
container at 320-430px). Compounded by `.scNameText`'s
`text-overflow:ellipsis` truncating vendor names while still overflowing
by 2-4px past the ellipsis.
**Solution**:
- `.scTable{table-layout:fixed}` + headers/cells `white-space:normal;
  overflow-wrap:break-word` (was `nowrap`).
- `.scNameText`: removed `overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap`, replaced with `overflow-wrap:break-word;
  white-space:normal` — names wrap instead of truncating.
- `data-th` attributes added to every `<td>` (score.js) driving a new
  `@media(max-width:480px)` vertical-stack recomposition (thead hidden,
  each `<tr>` becomes a flex row of labeled blocks) — same technique
  already proven on Dashbi's tables, not invented fresh.
**Why minimal**: 0 change to `renderTable()`'s row-building logic beyond
adding `data-th`; 0 change to the click-to-detail interaction, the score
meter, or `calcScores()`'s own extracted formula.
**Score business parity**: 12/12 golden fixtures pass unchanged
(`tests/score-parity-test.py`) — score values, ordering, and the score
bar's fill/meaning were never touched (Score's own frozen band conflict
remains unresolved, per Gate 16 — not invented here either).
**Desktop fidelity**: table shape, columns, and sticky-name-column
behavior unchanged at 768px+ (0 overflowing elements measured).
**Mobile result**: 320-430px stack into labeled record blocks; 0
horizontal scroll; long name fixture (`long_name`) verified wrapping
correctly, not truncating.

## Coparticipado — `assets/css/coparticipado.css`, `assets/js/coparticipado.js`

**Surface**: Coparticipados (13 cols) and Subsidiados (11 cols) record
tables — the widest tables in V2, and the most severe pre-existing case
(still 469px of overflow at 1920px, flagged since PORTAL-NEXT-07.4's own
audit).
**Root cause**: same auto-layout sizing, at a scale no other module's
table reaches (1747px of un-wrapped content).
**Solution**:
- `.cpTable{table-layout:fixed}` + general wrap on text columns.
- A `<colgroup>` (`cpColGroup()`, new small JS helper) gives 8-9 "atomic"
  columns (Valor Financiado, Rebate Total, Parte Brabus, Valor Rebate
  Total, Coparticipação, Retorno, SPF Extra, Data, Chassi) explicit floor
  widths, and `.cpNumCol`/`.cpAtomic{white-space:nowrap}` keeps those
  values on one line — this two-part fix exists specifically because the
  first attempt (uniform wrap, no floor) let currency/chassi values
  split mid-token ("R$ 155.00" + "0" on the next line, "CHS000002" +
  "5") — caught by re-screenshotting after the first pass, not assumed
  safe.
- `@media(max-width:900px)`: full vertical record recomposition (every
  field shown, `data-th`-driven) — NOT a primary/secondary split. No
  authorized hierarchy exists for this audit-style record (unlike
  Dashbi's human-directed KPI hierarchy), so per the explicit "prefer
  vertical recomposition over hiding information" instruction, every
  field stays visible rather than inventing one. `table-layout:auto` is
  re-applied inside this same media query — the `<colgroup>` floor
  widths would otherwise force the `<table>`'s own rendered width past
  its container even with rows flexed (a real regression caught during
  this Wave's own verification and fixed before being reported clean).
**Why minimal**: 0 change to `calcCoparticipacaoDetalhe()`, `dateIn()`,
classification, or filter logic; the `<colgroup>`/`cpAtomic` additions
are pure width/wrap hints, not new business rules.
**Coparticipado business parity**: 22/22 golden fixtures pass unchanged
(`tests/coparticipado-parity-test.py`), including the `modelo_sem_taxa`
warning-state fixture and `nome_longo`'s long-name stress case.
**Desktop fidelity**: real HTML table preserved at every width up to
1920px — 0 redesign into cards on desktop (that would have been a STOP
condition per Gate 74; table-layout:fixed + wrap was sufficient, verified
by measurement, so no STOP was needed).
**Mobile result**: ≤900px becomes a full vertical record card (all 13/11
fields, atomic values still nowrap-protected); 0 horizontal scroll from
320-1920px, verified with the `nome_longo` fixture (a name wrapping
across 3 lines) as the worst case.

## Gestão — `assets/css/gestao.css`, `assets/js/gestao.js`

**Surface**: 8 distinct tables (Financiamentos por Loja; Pagos/Faturados/
AG.Fat. por Unidade and por Banco; Planos por Loja/Departamento ×2;
SPF EXTRA detail; Propostas Recusadas/Aprovadas ×2) — up to 10 columns
each, overflowing up to 819px at 320px, clean by 1366px.
**Root cause**: same auto-layout sizing across every `geTableWrap` table.
**Solution**:
- `row(cells, headers)` extended to accept an optional `headers` array
  and stamp `data-th` per cell (every call site updated to pass its own
  in-scope `headers` variable); the 2 hand-rolled tables
  (`planStoreDeptTableHtml`, the SPF detail row) got `data-th` added
  directly.
- `.geTable{table-layout:fixed}` + wrap (was `nowrap` on both th and td).
- `@media(max-width:768px)`: vertical-stack recomposition, same
  `data-th`-driven technique as Score/Dashbi.
**Why minimal**: `row()`'s existing plain-string call signature is
unchanged for any caller that doesn't pass `headers` (none exist here,
but the parameter is optional by design, matching the same
non-breaking-extension pattern used for Dashbi's `expandableRow()` in
PORTAL-NEXT-07.5); 0 change to `compute()`, filters, or the SPF 70%
formula.
**Gestão business parity**: 30/30 golden fixtures pass unchanged
(`tests/gestao-parity-test.py`), including all 4 SPF-rounding fixtures
(`spf_zero`/`spf_100`/`spf_1000`/`spf_12345_67`) — **Comissão Líquida SPF
EXTRA = Total SPF EXTRA × 70%, unchanged, not touched**.
**Desktop fidelity**: 0 overflow at 1366/1920 before OR after (already
clean there) — the fix only changes behavior at ≤768px.
**Mobile result**: 320-768px all 8 tables stack into labeled records; 0
horizontal scroll.

## Verification summary (all 4 modules, fresh final run)

```
Overflow audit (real DOM, 320/360/390/430/768/1366/1920,
richest/last fixture per module):      0 overflowing elements
                                        (Landing's 2 residual = SAFE,
                                        contained bleed, not scroll)
tests/score-parity-test.py:                PASS — 12/12
tests/coparticipado-parity-test.py:            PASS — 22/22
tests/gestao-parity-test.py:                       PASS — 30/30
tests/landing-composition-regression.py:               PASS — 20/20
                                                       (0.0pp desktop
                                                       drift at 1366/1920)
tests/dashbi-parity-test.py:                              PASS — 26/26
                                                          (Dashbi untouched)
tests/foundation-regression.py:                              PASS — 10/10
tests/registry-test.py:                                          PASS
Dashbi file hashes (dashbi.js/.css/.adapter.js):                     0 diff
Score/Coparticipado/Gestão adapter file hashes:                        0 diff
Isolation baseline (.baseline-portalnext076-after.txt vs.
.baseline-portalnext0752-after.txt, ~30 sibling worktrees):               0-line diff
origin/main SHA:                                                              2f17eb2341c5cc14aa8710aa044103002ca572a9
                                                                              (unchanged)
Console/page errors across all 4 routes:                                          0
Network calls (supabase/api/openai):                                                  0
```

## Honestly scoped, not exhaustively automated this Wave

Keyboard/focus/touch-target behavior for Score's clickable rows and
every module's filters/buttons was **not** independently re-tested live
this Wave — verified instead by code-diff audit: no `:focus-visible`,
`tabindex`, `aria-*`, or interactive JS handler was touched in any of the
7 changed files (only `table-layout`, `white-space`/`overflow-wrap`,
`flex-wrap`, a `<colgroup>`, and `data-th` attributes were added/changed).
200% zoom, continuous resize, and device orientation were not
independently exercised as literal browser interactions this Wave;
confidence instead comes from the same 7-viewport measurement passing
cleanly, which is the direct proxy for "does the layout have a hard
breakpoint that could snap or overflow under zoom/resize" — flagged here
rather than silently claimed as PASS, per Gate 82's own honesty rule.
