# Authority (Gate 38)

```
V1 (portal-financiamento-brabus-secure)  = FUNCTIONAL SOURCE
Design System 2.1                          = VISUAL SOURCE
Red Precision Enforcement Skill (v1.0-candidate) = ENFORCEMENT
```

## V1 = Functional Source

Every business rule, financial formula, permission check, and data
scope V2 will ever need already exists, tested and running, in
`portal-financiamento-brabus-secure`. V2 does not invent or "improve"
any of it. See `config/module-registry.json`'s `functionalSource`
field for where each module's real logic currently lives, and
`assets/js/business-adapter-boundary.js` for the contract a future
adapter must satisfy to reuse it verbatim.

**This phase ported zero business logic.** See
`tests/business-logic-scanner.py`.

## Design System 2.1 = Visual Source

`design-system-2.1/` (inside this same Lab) is the design authority.
V2 does **not** duplicate it — `index.html` links
`../design-system-2/tokens.css` directly (the exact same executable
token file the Human Approved Executable Landing Reference itself
links to), `../shared/fonts.css` for IBM Plex Sans/Mono, and (as of
PORTAL-NEXT-03) `../design-motion-lab-03/parametric-catalog.js` +
`engine.js` for the Parametric Reactive motion runtime — the same
shared, approved implementation the Landing reference itself uses,
not a reimplementation. No hex value, token name, or motion parameter
is retyped anywhere in V2. See `config/validate-token-authority.py`.

**Open item, not solved this phase**: these are relative-path
references into the Lab, which will not survive V2 being promoted to
a standalone remote repo. A future phase must decide how tokens/fonts
travel with V2 when that happens (vendor them, publish them as a
versioned artifact, or graduate the whole Design System out of the
Lab) — see `PORTAL-NEXT-01/V1-V2-ARCHITECTURE.md` Gate 24 for the
same open question already flagged for the Skill itself.

## Red Precision Enforcement Skill = Enforcement

`design-system-skill-01/SKILL.md` (v1.0-candidate) governs how any
future UI work in V2 must be done — Authority Order, Visual Source of
Truth Rule, density/motion rules, anti-AI rules, the 8-phase workflow,
etc. This phase read it in full and followed it; it was not modified,
and it was not promoted to FINAL (still CANDIDATE, HUMAN STATUS
PENDING — see the Skill's own `VERSION.md`).

## Precedence (unchanged from design-system-2.1/design-system.normative.json)

```
1. explicit human decision
2. HUMAN APPROVED visual implementation (executable reference)
3. Design System 2.0 APPROVED
4. homologated Labs
5. PROVISIONAL
6. UNRESOLVED (STOP-ESCALATE)
```
