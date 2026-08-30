# Architecture (Gate 38)

## Shell

`index.html` + `assets/css/shell.css` + `assets/js/shell.js`. A
single-page shell: fixed global nav (landmark `<nav aria-label>`),
a content outlet (`<main id="nxContentOutlet" tabindex="-1">`), an
overlay root and a modal root (both empty by default, `display:none`
via `:empty`), a skip link as the very first focusable element, and a
small, non-obstructive dev badge (bottom-left) — never a giant banner.

No module's real UI exists yet. Every route renders a minimal
structural placeholder (name, title, migration status, a metadata
table) proving the routing/registry mechanism works, per Gate 10's
explicit instruction not to build a full visual mockup.

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
