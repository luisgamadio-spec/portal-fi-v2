# Score Visual Authority (Gates 9, 43-44)

## Authority resolution (Gate 2/9)

```
Score normative pattern:   design-system-2.1/references/score.md
Reference status:              APPROVED (but NO executable Approved
                             Reference file exists for Score — the
                             reference doc is text-only, unlike
                             Landing's frozen HTML snapshot)
```
Per Gate 43: **no executable source exists**, so this Wave does NOT
fabricate a visual-parity claim. Reported as **NORMATIVE COMPLIANCE**
(does the implementation follow the text rules), not **VISUAL
PARITY** (no image/DOM to compare against) — see Gate 44 below.

## Normative compliance, MUST-by-MUST

```
MUST NOT speedometer/generic gauge/trophy/medal/podium/emoji:  PASS
  (grep-verified 0 occurrences in assets/css/score.css,
  assets/js/score.js)
MUST show Score value:                                            PASS
  (.scDetailTotal, "Total: N / 1000")
MUST show band (ALTO/BOM/BAIXO):                                     FAIL
  — see docs/SCORE-ENGINE-AUDIT.md's dedicated section. Real
  production has NO band concept. Inventing thresholds to satisfy
  this MUST would fabricate business logic this Wave's own principle
  forbids ("DO NOT REDESIGN THE SCORE LOGIC"). Classified as a
  genuine Design System / production-truth conflict requiring a
  Change Proposal, NOT resolved by this phase either by inventing a
  band or by silently dropping the requirement without disclosure.
MUST show confidence:                                                PASS
  — the REAL per-criterion "amostra" mechanism (confVendas/confFin
  dampening), disclosed in the UI exactly as production discloses it
  ("Amostra: X — pontuação proporcional à amostra até atingir
  confiança plena"), not a fabricated global confidence badge.
MUST show component breakdown (meters, not gamified):                  PASS
  — .scMeter (thin hairline bar, width=pct), not a radial/circular
  gauge or gamified progress ring.
MUST show explanation:                                                    PASS
  — each criterion's `detail` text (real production strings, e.g.
  "4 financiado(s) / 4 venda(s) (100,0%)").
Status must never depend on color alone:                                   PASS
  — every state (score, points, detail) is conveyed in text; the
  meter fill color is decorative reinforcement, not the sole signal.
```

## Anti-AI audit (Gate 37)

| Pattern | Result |
|---|---|
| Card Grid Syndrome | PASS — table, not cards |
| Pills Everywhere | PASS — 0 pills |
| Gradient Decoration | PASS — 0 gradients |
| Glow Futurism | PASS — 0 box-shadow glow |
| Giant KPI Grid | PASS — no KPI tiles at all |
| Rainbow Metrics | PASS — single accent color (--color-accent-primary) throughout meters, no per-band color-coding (consistent with no band existing) |
| Fake HUD | PASS |
| Speedometer/Gauge | PASS — explicit MUST NOT honored |
| Card Inside Card | PASS — detail region is a flat section, not a nested card |
| Motion Everywhere | PASS — 0 motion on Score (HIGH density table, motion OFF per Gate 11/56) |
| Generic SaaS | PASS — real labels, no generic "Performance Intelligence"-style renaming (Gate 57) |

## Semantic copy (Gate 57)

All labels are production's own real strings, read directly from
`origin/main:modules/score.html`, not invented: "Análise de Score
Vendedores" (page title), "Volume de vendas", "Penetração de
financiamento", "Mix de famílias vendidas", "Mix de planos
(diversidade)", "SPF EXTRA", "Retorno médio". No marketing rename
("Performance Intelligence", "Dealer Power Score", etc.) was
introduced.

## Numeric typography (Gate 58)

IBM Plex Mono (`var(--font-mono)`) used for: score/rank/financing-count
columns (`.scNumCol`, `.scRankCol`), criterion points
(`.scCriterionPoints`), detail total (`.scDetailTotal`). NOT used for
explanatory text (`.scCriterionMeta`, `.scAmostraNote`, headings) —
those stay on `var(--font-ui)`, per Gate 58's "não usar mono
indiscriminadamente".

## Filter/sort visuals (Gates 59-60)

No filters implemented this Wave (production's Score filters were not
mapped/ported — out of scope, see docs/SCORE-EXTRACTION-TRACE.md).
Table order = `calcScores()`'s own sort (score desc, fin desc) —
**not** interactively re-sortable by column this Wave, because
`data-table.md`'s Sortable Column visual indicator is explicitly
**UNRESOLVED** and this Wave does not invent one locally.
