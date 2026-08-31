# DS Change Proposal — Receita Total Emphasis

**Status: HUMAN DIRECTIVE / PENDING FORMAL DS INTEGRATION**
(same pattern as `DS-CHANGE-PROPOSAL-NO-HORIZONTAL-SCROLL-01.md` and
`DS-CHANGE-PROPOSAL-SCORE-BAND-01.md` — a Wave-scoped human directive
documented here rather than silently written into the normative token
file, which this Wave does not touch.)

## Gap

PORTAL-NEXT-07.5 requires Receita Total to get a "distinct attention
treatment, different from Share, financial/value-emphasis character" —
explicitly NOT a status semantic (`--color-success`/`--color-critical`/
`--color-warning`), since revenue being large isn't "success" and Brand
Red isn't "this number is important." Searched
`design-system-2/tokens.css` (the real token authority, confirmed via
`portal-next-v2/index.html`'s own `<link>` order — distinct from
`design-system-2.1`, which only holds `references/*.md` docs) and
`design-system-2.1/references/*` for an existing "financial value
emphasis" token or approved pattern. None exists.

## Options considered

- **`--color-accent-primary`** (`#ee4b57`, red): the token file's own
  comment marks this "functional: state, selection, interactive
  emphasis, focus" — it's already load-bearing for interactive states
  elsewhere on this exact page (vehicle-card selection, focus rings,
  mode-tab active indicator). Reusing it for a *static, non-interactive*
  value would blur that meaning and risks reading as "this number is
  clickable" or, given its proximity to `--color-brand-red`, as
  "critical." Rejected.
- **`--color-info`** (`#6fa8c9`, blue): a distinct semantic hue, not part
  of the success/warning/critical status family, not the interactive
  accent, no existing usage on this page competing for the same meaning
  (only used for `.dbPlanCard.planBalao`'s left-stripe, a different
  surface and different data). Reads as "informational/value," which
  matches "financial/value-emphasis character" better than any status
  color would. **Selected**, provisionally.

## Provisional treatment (this Wave only)

Applied ONLY to the Overview KPI grid's Receita Total card (the single
most prominent primary surface) — table cells showing Receita Total
elsewhere (Loja/Vendedor/Ranking) stay plain-formatted money, matching
every other non-emphasized metric on those tables (Gate 18: "must not
become rainbow analytics").

```css
.dbKpiCardReceitaTotal { border-top-width: 3px; border-top-color: var(--color-info); }
.dbKpiCardReceitaTotal .dbV { color: var(--color-info); font-weight: 700; }
```

Distinguishing device from Share's own emphasis (also required to be
distinguishable at a glance, not by color alone): Share uses a LEFT
border stripe + a success/critical hue that changes with the data +
a text caption; Receita Total uses a TOP border stripe + a fixed
info hue + bold weight. Position, hue family, and weight all differ —
not color alone in either case.

## Contrast

`#6fa8c9` on `--color-canvas` (`#0a0a0a`): relative luminance 0.3562 vs
0.0030 → contrast ratio ≈ 7.66:1 — passes WCAG AA (4.5:1) and AAA (7:1)
for normal text. Computed via the WCAG relative-luminance formula, not
assumed or reused from a prior measurement.

## Disposition

This is a Wave-scoped provisional reuse of an existing semantic token in
a new role, not a new primitive. Formal DS integration (a dedicated
`--color-value-emphasis` token, or an explicit "financial emphasis"
usage note added to `--color-info`'s own definition) is deferred to a
future Design System phase with human authorization — this file is the
record of that gap until then.
