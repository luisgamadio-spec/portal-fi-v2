# Architecture (Gate 38)

## Shell

`index.html` + `assets/css/shell.css` (dev-tooling chrome only) +
`assets/css/landing.css` (persistent app chrome, transplanted from the
Approved Reference — see PORTAL-NEXT-03) + `assets/js/shell.js`. The
persistent chrome is `.pShell > .pGlobalNav + .pMain(.pTopBar,
.ctxBeam, #nxContentOutlet.pContent)` — exact class names from
`design-system-2.1/references/baselines/module-landing-approved/`, not
reinvented. A skip link is the first focusable element; overlay/modal
roots are empty by default.

**Landing** (`#/landing`, the default route) has a real, transplanted
UI — see the dedicated section below. Every OTHER route still renders
the Foundation-era minimal structural placeholder (name, title,
migration status, a metadata table, honest `NOT_MIGRATED` label) — per
Gate 10/40, no functionality is simulated for unmigrated modules.

## Landing (PORTAL-NEXT-03)

`assets/js/landing.js` + `assets/css/landing.css` +
`config/landing-groups.json`. Method: TRANSPLANT + CONTROLLED
ADAPTATION (Skill Gate 8) — structure/interaction model copied
verbatim from the reference's `pages.js`/`app.js` (category selection
via hover/focus/click, module block click navigates, Context Beam
fires only on an actual context change, respects
`prefers-reduced-motion`), tokens from `design-system-2/tokens.css`,
motion from the shared `design-motion-lab-03/engine.js` (linked
directly, not reimplemented), content from V2's real module registry.
Full mapping rationale: `docs/LANDING-CONTENT-MAP.md`. Full test
evidence: `tests/landing-composition-regression.py`,
`tests/anti-ai-audit.md`, `REPORT.md`'s PORTAL-NEXT-03 entry.

## Router

`assets/js/router.js` — hash-based (`#/<module-id>`). Deep links work
(a cold load with a hash resolves immediately via `resolveInitial()`);
reload preserves the route (the hash is part of the URL, not in-memory
state). No production routes exist — this only proves the mechanism.

## Module Registry

`config/module-registry.json`, loaded by `assets/js/module-registry.js`.
One entry per real V1 module found during PORTAL-NEXT-01's audit (10
entries: Landing, Portal Shell/MASTER Admin, Score, Coparticipado,
Gestão, Dashbi, Simulador Novos, Simulador Seminovos,
Salários/Comissões, Brabus Intelligence). Every entry starts
`NOT_MIGRATED`. See `docs/MIGRATION-STATUS.md` for the status enum.

## Module Contract (Gate 12)

Every registry entry satisfies this shape:
```
id, route, title, density, authRequirement, designPattern,
entryPoint, businessSource, functionalSource, approvedReference,
migrationWave, risk, migrationStatus, notes
```
A future Wave should never invent a different shape per module — this
is the one contract all of them share.

## Business Adapter Boundary

`assets/js/business-adapter-boundary.js` — a contract stub
(`compute(input) -> plain output, no DOM access`) so V2's UI layer
never needs to know V1's DOM contracts or RPC names directly. Empty
registry this phase (`NX_BUSINESS_ADAPTERS.registry = {}`) — populated
one module at a time, only when that module's Wave actually extracts
its logic (never speculatively).

## Auth Boundary

`assets/js/auth-boundary.js` — a contract stub for `signIn`,
`getSession`, `onAuthStateChange`, `resolveAuthorizedProfile`,
`signOut`. Every method throws `NOT_IMPLEMENTED`. A future Wave wires
this to V1's exact Supabase Auth flow — no parallel auth is ever
created (`PORTAL-NEXT-01/SHADOW-UAT-PLAN.md` Gate 21).

## Guards

`environment-guard.js` (Gate 18) declares `NEXT_LOCAL` and refuses to
render if the hostname ever looks like production. `network-guard.js`
(Gate 19) wraps `fetch`/`XMLHttpRequest` to flag (never silently
allow-and-ignore) any request to a known real-backend host.

## Design Trace (dev tooling)

`assets/js/design-trace.js` + the `#nxDesignTrace` panel — shows the
current route's registry metadata. Toggled by a small "trace" button
in the dev badge. Explicitly separated from the product experience —
see Gate 33's contamination scanner, which also confirms this is not
an import of facelift-prototype-01's own Lab tooling.

## Test Architecture

Static, scriptable checks live in `tests/*.py` (business logic
absence, contamination, registry structure, token authority, reference
resolution) and run together via `tests/foundation-regression.py`.
Browser-only concerns (routing in a live DOM, responsive layout across
6 breakpoints, keyboard/focus order, reduced-motion behavior, network
capture) were verified manually via Playwright this phase — see
`REPORT.md`'s PORTAL-NEXT-02 entry for the exact results and
`docs/DEVELOPMENT.md` for how to re-run them.
