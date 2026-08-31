# V2 Global Horizontal-Scroll Audit (PORTAL-NEXT-07.4, Gate 2)

Measured with `document.scrollWidth`/`clientWidth` (document-level) and a scan of
every element with `overflow-x: auto|scroll` whose `scrollWidth > clientWidth`
(component-level), at all 6 required viewports: 360×800, 390×844, 430×932,
768×1024, 1366×768, 1920×1080.

## Landing (HUMAN_APPROVED / FROZEN)

| Viewport | Doc overflow | Component scroll | Cause |
|---|---|---|---|
| 360-430 | No | Yes — `.fNav` (mobile category nav strip), scrollWidth 659 vs 326-396 | Horizontal nav strip, not an analytical/tabular surface |
| 768-1920 | No | No | — |

**STATUS: FROZEN CONFLICT.** `.fNav` is a navigation affordance (menu categories), not material analytical data — but it does require a horizontal gesture to reach some categories on narrow phones. Not modified this Wave (HUMAN_APPROVED/FROZEN). Recommend evaluating in a future remediation Wave whether this specific case (navigation chrome, not data) should be exempted from the directive or recomposed.

## Score (HUMAN_APPROVED / FROZEN)

| Viewport | Doc overflow | Component scroll | Cause |
|---|---|---|---|
| 360-430 | No | Yes — `.scTableWrap`, scrollWidth 457 vs 326-396 | Score ranking table, real material data |
| 768-1920 | No | No | — |

**STATUS: FROZEN CONFLICT.** Material information (score ranking table) requires horizontal scroll at 360-430px. Not modified this Wave. **Future remediation required.**

## Coparticipado (HUMAN_APPROVED / FROZEN)

| Viewport | Doc overflow | Component scroll | Cause |
|---|---|---|---|
| 360-1920 (ALL) | No | Yes — `.cpTableWrap`, scrollWidth 1886 vs 326-1278 | Wide Coparticipados/Subsidiados table, real material data |

**STATUS: FROZEN CONFLICT — most severe of the 4 frozen modules.** Requires horizontal scroll at every viewport including 1920px. Not modified this Wave. **Future remediation required**, likely a primary+detail recomposition similar to this Wave's Model Analysis work.

## Análise F&I / Gestão (HUMAN_APPROVED / FROZEN)

| Viewport | Doc overflow | Component scroll | Cause |
|---|---|---|---|
| 360-430 | No | Yes — up to 7 different `.geTableWrap` tables, scrollWidths 398-1162 vs 326-396 | Multiple KPI/breakdown tables |
| 768 | No | Yes — 5 tables still scroll at this width | Same tables, narrower gap |
| 1366-1920 | No | No | — |

**STATUS: FROZEN CONFLICT.** Multiple tables require horizontal scroll up to 768px. Not modified this Wave. **Future remediation required.**

## Dashbi (UAT_PENDING — in scope this Wave)

### Before PORTAL-NEXT-07.4

| Surface | Worst overflow | Viewports affected |
|---|---|---|
| Store/Seller tables (Visão Geral) | 814 vs 326 (2.5×) | ≤430px |
| Ranking (Vendedores table) | 742 vs 326 | ≤768px |
| Novos por Loja | 853 vs 326 | ≤768px |
| Model Analysis wide table (18 cols) | 1855 vs 292 (6.4×) | **ALL 6 viewports, including 1920px** |
| Model Analysis plan tables (×3) | up to 1132 vs 292 | ≤768px |

### After PORTAL-NEXT-07.4

All Dashbi tables recomposed with the shared "primary row + inline + Detalhes" component (see `docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md`). First pass only checked document-level `scrollWidth` and missed a hidden component-level scrollbar (`.dbTableWrap`'s own `overflow-x:auto` silently absorbing table growth when a detail row was open) — self-caught and fixed (`docs/MODEL-ANALYSIS-NO-SCROLL-DESIGN.md`'s "A real bug self-caught during verification" section has the full trace). Final verification checks BOTH levels: **48/48** view/mode × viewport combinations pass with 0 overflow at either level, including with every detail panel open (worst-case width). Full 26-fixture × 3-family sweep at 360px (narrowest required viewport) with all details expanded: 0 overflow at either level, 0 console errors.

**STATUS: PASS.** Dashbi is now fully compliant with the global no-horizontal-scroll directive.

## Summary

```
Landing:          FROZEN CONFLICT (nav strip, not analytical data — lower priority)
Score:            FROZEN CONFLICT (material data)
Coparticipado:    FROZEN CONFLICT (material data, most severe — scrolls even at 1920px)
Análise F&I:      FROZEN CONFLICT (material data)
Dashbi:           PASS (recomposed this Wave)
```

**FULL V2 COMPLIANCE: PARTIAL** — Dashbi is compliant; 4 frozen modules are not, and were deliberately NOT modified per explicit instruction (no unauthorized changes to HUMAN_APPROVED/FROZEN surfaces). See `docs/DS-CHANGE-PROPOSAL-NO-HORIZONTAL-SCROLL-01.md` for the formal directive record and recommended next step (a dedicated remediation Wave, only after Dashbi's own human approval and explicit authorization).
