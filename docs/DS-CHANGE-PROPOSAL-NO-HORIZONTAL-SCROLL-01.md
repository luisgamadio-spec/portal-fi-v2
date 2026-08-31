# Design System Change Proposal — No Horizontal Scroll (01)

**STATUS: HUMAN DIRECTIVE / PENDING FORMAL DESIGN SYSTEM INTEGRATION.**

Not a self-authorized rewrite of `design-system-2.1`'s normative files — this
document records an explicit human product directive given during PORTAL-NEXT-07.4,
pending the human's own decision on whether/how to fold it into the formal Design
System.

## Directive (verbatim intent)

User-facing Portal V2 surfaces MUST NOT require horizontal scrolling to access
material information.

## Scope

Global, all current and future V2 modules.

## What this does NOT mean

- Force every field into the viewport simultaneously.
- Tiny unreadable typography, extreme column compression, overlapping content, or
  multi-line numeric values caused by lack of width.
- Removing material metrics or permanently hiding production information.
- Concealing overflow with CSS (`overflow-x: hidden`, hidden scrollbars, etc.) while
  the information remains inaccessible — explicitly prohibited as a fake fix.

## Design principle

Prefer, in this order: responsive recomposition → progressive disclosure →
structured detail → priority hierarchy → vertical expansion, over horizontal
scrolling.

## Relationship to the existing `data-table.md` Approved Reference

`data-table.md` states "Table remains table — MUST NOT auto-convert rows into
cards" — that rule stands and was followed this Wave (the Model Analysis
recomposition is still a real `<table>`, not a card grid). What this new directive
adds/supersedes is the *implicit* allowance of horizontal scroll as a mobile
fallback for wide tables — `data-table.md` never explicitly endorsed horizontal
scroll, but every prior module (Score/Coparticipado/Gestão/Dashbi's own earlier
tables) used `overflow-x: auto` as the de facto solution. This directive makes
explicit that horizontal scroll is no longer acceptable for material information,
while the "stay a table" rule is unchanged.

## Applied this Wave

Dashbi (UAT_PENDING, not frozen) — recomposed. See
`docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md` and
`docs/MODEL-ANALYSIS-PRIMARY-DETAIL-MAP.md`.

## Not applied this Wave (frozen conflicts, reported not fixed)

Landing, Score, Coparticipado, Análise F&I (Gestão) — all HUMAN_APPROVED/FROZEN,
all found to have at least one component-level horizontal-scroll dependency (see
`docs/V2-HORIZONTAL-SCROLL-AUDIT.md`). None were modified. Recommended: a
dedicated **V2 No-Horizontal-Scroll Remediation Wave**, explicitly authorized by
the human, after Dashbi's own human UAT concludes — not bundled into an
unrelated Wave, and not assumed to require the same solution for every module
(Coparticipado's own severity — scrolling even at 1920px — likely needs the same
primary+detail pattern used here for Model Analysis; Landing's `.fNav` may turn out
to be a different, lower-priority case since it's navigation chrome, not
analytical data).

## Future migrations

From this directive forward, every future V2 module migration (Novos, Seminovos,
Simuladores, Salários/Comissões, Brabus Intelligence, Admin/Auditoria) must prove
0 page-level horizontal overflow and 0 material-information dependency on
horizontal scrolling, at all 6 required viewports, before human UAT — the same
gate now applied to Dashbi.
