# Portal F&I V2 — Foundation (PORTAL-NEXT)

## THIS IS NOT PRODUCTION.

```
Product:           Portal F&I — Grupo Brabus
Generation:        V2
Design:            Red Precision
Environment:       LOCAL NEXT (NEXT_LOCAL)
Release Status:    DEVELOPMENT
Production:        NO
```

This is a strictly local, isolated, versioned foundation for a future
V2 of the real Portal (`portal-financiamento-brabus-secure`). It has:

- no remote (`git remote -v` returns nothing, by design)
- no deploy config, no GitHub Pages workflow, no production hostname
  anywhere in its code
- no business logic (no financial formula, no Score formula, no
  commission formula — see `tests/business-logic-scanner.py`)
- no real backend calls (0 Supabase, 0 Edge Functions, 0 OpenAI — see
  `assets/js/network-guard.js`)
- no migrated modules — every entry in `config/module-registry.json`
  is `NOT_MIGRATED`

**Foundation green does not mean**: Landing migrated, modules
migrated, V2 functional, Release Candidate, or Human Approved. It
means the container is safe to build inside of. See
`docs/MIGRATION-STATUS.md`.

## Before doing anything else

1. Read `docs/AUTHORITY.md` — who decides what (V1 = functional
   source, Design System 2.1 = visual source, the Red Precision
   Enforcement Skill = process enforcement).
2. Read `docs/SAFETY.md` — the hard rules (no push, no deploy, no
   production target).
3. Run `python config/pre-wave-check.py` before starting any Wave.
4. See `docs/DEVELOPMENT.md` for how to run this locally.

## Structure

```
portal-next-v2/
  index.html                shell entry point
  assets/css/shell.css        shell layout (tokens only — see AUTHORITY.md)
  assets/js/
    environment-guard.js         Gate 18 — asserts NEXT_LOCAL, refuses to
                                  render on a production-looking hostname
    network-guard.js               Gate 19 — flags any fetch/XHR to a real
                                  backend host
    auth-boundary.js                 Gate 17 — auth CONTRACT only, no login
    business-adapter-boundary.js       Gate 15 — business-adapter CONTRACT
                                      only, no formula
    router.js                          Gate 11 — hash-based router
    module-registry.js                   Gate 13 — loads config/module-
                                      registry.json
    design-trace.js                        Gate 32 — dev-only inspector panel
    shell.js                                 boot/orchestration
  config/
    module-registry.json          Gate 13/39 — module contract + manifest
    production-fingerprint.json     Gate 28 — V1 HEAD marker (no secrets)
    validate-token-authority.py       Gate 8/9 — token sync check
    v1-change-detection.py              Gate 29 — read-only drift check
    pre-wave-check.py                     Gate 27 — run before any Wave
  docs/
    ARCHITECTURE.md   DEVELOPMENT.md   MIGRATION-STATUS.md
    AUTHORITY.md      SAFETY.md        FOUNDATION-BASELINE.md
  tests/
    business-logic-scanner.py   contamination-scanner.py
    registry-test.py            reference-resolution-test.py
    foundation-regression.py    (runs all of the above)
    screenshots/                 (Gate 31 visual foundation evidence)
```
