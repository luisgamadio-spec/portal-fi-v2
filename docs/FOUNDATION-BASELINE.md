# Foundation Baseline (Gate 37)

Registered once, after Foundation went green. Future Waves start from
this known base — see `config/pre-wave-check.py` and
`config/v1-change-detection.py` for how to confirm nothing has moved
since.

```
Foundation created:                2026-08-30
Design System authority version:     design-system-2.1 (status CANDIDATE,
                                    directionStatus HUMAN_APPROVED)
Skill version:                        design-system-skill-01
                                    (Red Precision Enforcement,
                                    v1.0-candidate, HUMAN STATUS PENDING)
Production (V1) fingerprint:            2f17eb2341c5cc14aa8710aa044103002ca572a9
                                       (realRemoteMainHead — see
                                       config/production-fingerprint.json
                                       for the full disclosure of why
                                       this differs from the local
                                       clone's HEAD)
Environment:                              NEXT_LOCAL
```

No remote tag was created (none is mandatory this phase, per Gate 37's
own instruction) — this document plus the local git log inside
`portal-next-v2/` (see `git log` — first commit message references
this same baseline) is the addressable marker for now.

## First-Wave Readiness (Gate 40)

```
Landing Approved Reference resolves:    YES (tests/reference-resolution-test.py)
Router ready:                             YES (hash routing verified in a real
                                         browser: nav click, reload-preserves-
                                         route, cold deep link all work)
Tokens ready:                               YES (direct link to design-system-2/
                                         tokens.css, validated against
                                         design-system-2.1's normative JSON,
                                         0 divergence)
Motion runtime ready:                         YES, loadable, OFF by default
                                         (window.NX_MOTION.parametricReactive:
                                         available=true, enabled=false)
Context Beam hook ready:                        YES, stub exists
                                         (window.NX_CONTEXT_BEAM.fire — a
                                         documented no-op, not fired by any
                                         placeholder)
Responsive foundation ready:                      YES (0 horizontal overflow
                                         at 360x800/390x844/430x932/
                                         768x1024/1366x768/1920x1080,
                                         verified in a real browser)
Visual comparison harness ready:                    YES (mechanism only —
                                         tests/visual-comparison-harness.py
                                         renders + captures source reference
                                         and V2 result side by side; does
                                         NOT claim any parity verdict, since
                                         nothing is migrated)
Production fingerprint available:                     YES (config/
                                         production-fingerprint.json)
Skill active:                                           YES (SKILL.md read
                                         and followed throughout this phase;
                                         not modified, not promoted to FINAL)
```

**PORTAL-NEXT-03 (Shell + Approved Landing Migration): READY.**

No critical item is NO. This does not authorize starting PORTAL-NEXT-03
— that remains a separate, explicit human decision (Gate 40's own
instruction: "não executar a Wave").
