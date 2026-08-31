# Responsive Test Evidence — PORTAL-NEXT-07.6.1 (Gates 7-11, 18)

REAL BROWSER TEST results (Playwright/Chromium, live interaction) for
the 4 items PORTAL-NEXT-07.6 disclosed as not literally exercised. Every
result below was produced by actually running the check in a real page,
not inferred from CSS/JS source. Screenshots in the session scratchpad
(`screenshots-07-6-1/`) back every FAIL/PASS.

## Method note — 200% zoom

No Playwright API fires a literal browser Ctrl-+ zoom event. The
standard technique used to reproduce its LAYOUT effect: halve the
viewport (683×450 instead of 1366×900) — at 200% zoom every CSS pixel
occupies 2 physical pixels, so half as many CSS pixels fit in the same
physical window, which a halved viewport reproduces exactly for layout
purposes. Documented here rather than silently presented as identical
to a literal zoom event.

## Gate 7 — 200% zoom (REAL BROWSER TEST)

```
Landing:         FAIL (see note below — not a new defect)
Score:               PASS — docOverflow=0, worstComponentOverflow=0
Coparticipado:           PASS — docOverflow=0, worstComponentOverflow=0
Gestão:                      PASS — docOverflow=0, worstComponentOverflow=0
```

## Gate 8 — Orientation, 390×844 portrait / 844×390 landscape (REAL BROWSER TEST)

```
Landing:         FAIL both orientations (same note)
Score:               PASS both — docOverflow=0, worstComponentOverflow=0
Coparticipado:           PASS both
Gestão:                      PASS both
```

## Gate 9 — Continuous resize, 320→1920px in 40px steps, both directions, no reload (REAL BROWSER TEST)

```
Landing:         FAIL at all 82 steps (same note, constant not growing)
Score:               PASS — 0/82 problem steps
Coparticipado:           PASS — 0/82 problem steps
Gestão:                      PASS — 0/82 problem steps
```
No stuck responsive state, duplicated UI, disappearing content, or
transient-then-persistent overflow was found in Score/Coparticipado/
Gestão across the full live sweep (not just discrete breakpoints).

## Landing's Gate 7-9 result — reported honestly, not converted to PASS, not "fixed" reflexively

Every single Gate 7/8/9 measurement for Landing shows the exact same
signature: `docOverflow=0` (0 real page-level scroll, every time) and
`worstComponentOverflow=18` at selector `DIV.fCanvasInner`. This is the
identical, already-documented finding from PORTAL-NEXT-07.6's own
inventory (`docs/FROZEN-MODULE-NO-SCROLL-INVENTORY.md`): a constant
18px child-scrollWidth delta caused by `.fModuleBlock{margin:0 -18px}`
(an intentional hover-highlight bleed rectangle), fully contained by
the ancestor `.fCanvas{overflow:hidden}` — confirmed again here at
every zoom/orientation/resize step: `docOverflow=0` in 100% of the 94
Landing measurements this Wave (4 zoom + 8 orientation + 82 resize)
means it produces 0 visible or functional scrollbar under any of these
harsher test conditions either.

**MODULE**: Landing
**ROUTE**: /landing
**TEST**: 200% zoom, portrait/landscape, continuous resize
**VIEWPORT/ZOOM/ORIENTATION**: all tested conditions
**EXACT FAILURE**: `.fCanvasInner`/`#landingModuleDetail` scrollWidth
exceeds clientWidth by a constant 18px
**ROOT CAUSE**: `.fModuleBlock{margin:0 -18px}`, an intentional
hover-bleed rectangle
**AFFECTED SELECTOR**: `.fCanvasInner`, `#landingModuleDetail`
**MATERIAL INFORMATION AFFECTED**: no — text never reaches this 18px,
confirmed by screenshot at every condition tested
**MINIMUM PROPOSED FIX**: none proposed — fixing it would mean shrinking
an intentional, already-approved hover-bleed visual with 0 user-facing
benefit (0 visible scrollbar exists to remove)
**BUSINESS IMPACT**: none
**DESIGN IMPACT**: none (not touched)

Not re-classified as PASS — recorded as FAIL against the strict
"0 elements with scrollWidth>clientWidth" measurement, with the
functional read (0 visible/functional scroll at any of the 94
conditions tested) stated separately and explicitly, per Gate 82's own
rule not to convert a real measurement into an unqualified PASS.

## Gates 10-11 — Keyboard + visible focus (REAL BROWSER TEST)

```
Landing:         PASS — .fNavItem reachable, visible focus outline
                  present, Enter activates the category (detail content
                  changed)
Score:               PASS — table row reachable (tabindex=0, role=button),
                      visible focus outline present, Enter opens the
                      detail panel (hidden attribute removed)
Coparticipado:           PASS — view-switch tab button reachable, visible
                          focus outline present, Enter activates the tab
                          (cpTabActive class applied); the Loja filter
                          select is reachable in the same tab sequence
Gestão:                      PASS — filter select reachable, visible
                              focus outline present
```

All four: `getComputedStyle(document.activeElement)` confirmed a real
`outline-style`/`outline-width` on the focused element (not merely
present in CSS source — the actual computed style after focus), and the
relevant action (category switch / detail open / tab switch) was
confirmed to have actually happened by reading the DOM after `Enter`,
not assumed from the click handler's existence.

## Summary

```
Gate 7 (200% zoom):          Landing FAIL (non-material, documented) /
                              Score, Coparticipado, Gestão PASS
Gate 8 (orientation):            Landing FAIL (same) / others PASS
Gate 9 (continuous resize):          Landing FAIL (same) / others PASS
Gates 10-11 (keyboard/focus):            PASS — all 4 modules
```

No test failure found here was material or within a scope requiring a
fix (Landing's is the same pre-existing, already-accepted, non-visible
bleed; nothing else failed) — per Gate 12, no presentation code was
changed this Wave.
