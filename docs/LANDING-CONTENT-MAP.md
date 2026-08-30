# Landing Content Map (Gates 0, 5, 6, 39)

## Gate 0 — Rebaseline Review finding (bigger than PORTAL-NEXT-02 flagged)

`git ls-remote origin refs/heads/main` still returns `2f17eb2...` — no
new drift since PORTAL-NEXT-02. But investigating further this phase
(to satisfy Gate 6's read-only V1 content discovery) surfaced a
**larger fact than PORTAL-NEXT-02 disclosed**: `gh api .../commits/
53d7197...` returns `404 No commit found`. The local clone's `main`
and GitHub's real `main` are not "a few commits apart" — they are
**divergent histories**. The local HEAD commit was made directly on
the local checkout (reflog: `main@{0}: commit: ...`) and was
apparently never pushed; meanwhile the real remote accumulated 100+
commits including a differently-hashed version of that same logical
change (`2dc12ed9`, same message, different SHA/timestamp).

**Practical consequence acknowledged, not fixed**: PORTAL-NEXT-01's
architecture audit was performed against the local clone, which was
never the literally-deployed code. It was evidently *close* (same
recent feature, same day), but this is a materially bigger gap than
"stale by a few commits." **Recommend a dedicated future rebaseline
phase** to re-audit V1 against the real remote properly — not
performed here, out of this Wave's scope (Landing/Shell only).

**Does it affect Landing / Shell / Navigation / Auth for THIS Wave?**
```
Landing:      NO — structure comes exclusively from the frozen
              Approved Reference (design-system-2.1), never from V1,
              per this phase's own Gate 8. Unaffected by any V1 drift.
Shell:          NO structurally — V2's shell is independent new code.
Navigation:       Only in the sense that real V1 module NAMES/grouping
              used for Landing content (below) were sourced from the
              REAL remote content (fetched read-only via `gh api
              repos/.../contents/index.html?ref=main`), not the stale
              local clone — this produced MORE accurate content than
              PORTAL-NEXT-01's own module inventory in some cases
              (e.g. "Gestão" is not a real V1 display title; the real
              one is "Análise F&I do Grupo").
Auth:             NOT independently re-verified this phase (out of
              scope — Landing has no auth surface; Gate 41 requires
              Landing to work with 0 backend calls anyway).
```
No pull/fetch/merge/checkout/reset/rebase was performed on the local
V1 clone. All of the above came from `git ls-remote` (ref lookup only)
and `gh api` (HTTPS content/commit reads) — see the commands recorded
in `REPORT.md`'s PORTAL-NEXT-03 entry.

## Gate 2 — Approved Reference resolved via the normative registry

`design-system-2.1/design-system.normative.json` →
`approvedReferences[id=module-landing]`, `status: APPROVED`,
`sourcePath: design-system-2.1/references/baselines/module-landing-
approved/index.html`. This is the ONLY structural source used — not
`REPORT.md`, not conversation memory, not `facelift-prototype-01`'s
current (possibly since-edited) state.

## Gate 3-4 — Fresh render + real DOM measurement

Rendered fresh this phase at all 4 required viewports (screenshots:
`tests/screenshots/landing-wave/source-fresh-*.png`; raw measurements:
`source-measurements.json`, `source-detail-measurements.json`,
`source-nav-content.json` in the same folder). Key real numbers (not
estimated):
```
fShell:            x=64 (right of global nav), width=1302 @1366 viewport
fNav width:          546.8px = 42.0% of fShell width
fNav padding:          70px 0 70px 56px
nav item gap:             4px; each item ~69.7px tall; 6 items @1366
nav item label font:        45px / weight 300 (desktop max, matches
                          clamp(27px,3.5vw,45px))
canvas (module block)         padding: 21px 18px
globalNav:                       64px wide, full height, brandMark
                          "B" (28x28 box, red border)
globalNav module shortcuts:         2-letter uppercase mono codes
                          (PF/GE/NV/SM/SI/SC/SL/AI/AU)
mobile (390/430):                      globalNav becomes a 52px-tall
                          horizontal bar; fNav width=100%, height
                          ~69px; nav item label font: 17px
```

## Gate 5 — 6 real category slots in the reference, real content mapped

The reference's own 6 nav categories (verbatim labels) and block count:
```
Gestão                 -> 1 block ("Gestão / Análise Geral")
Novos & Seminovos          -> 2 blocks ("Novos", "Seminovos")
Simuladores                  -> 1 block ("Simuladores")
Score & Salários                -> 2 blocks ("Score de Vendedores",
                              "Salários & Comissões")
Brabus Intelligence                -> 1 block
Auditoria                            -> 1 block ("Auditoria / Relatórios")
```
Max observed blocks-per-category in the approved grammar: **2**.

V2's real 10-module registry mapped onto this grammar (5 of the 6
category slots used; real V1 names preserved where they exist):

```
"Gestão"                 -> Análise Geral do Grupo (dashbi)
                            + Análise F&I do Grupo (gestao)
                          [matches V1's own real "📊 Gestão" grouping,
                          emoji stripped per the Skill's own emoji-ui
                          anti-pattern rule — TEST-30 in the Skill's
                          adversarial suite]

"Novos & Seminovos"        -> Simulador de Novos (simulador-novos)
                            + Simulador de Seminovos (simulador-seminovos)
                          [reference's OWN category name already
                          matches these 2 real module titles closely]

"Score & Salários"           -> Análise de Score Vendedores (score)
                              + Salários & Comissões (salarios-comissoes)
                          [near-verbatim match to the reference's own
                          block text]

"Brabus Intelligence"          -> Brabus F&I Intelligence (brabus-intelligence)

"Auditoria"                       -> Painel Master / Auditoria (shell-admin)
                          [shell-admin is broader than just the
                          Auditoria tab, but "Auditoria" is real V1
                          category language and shell-admin's real
                          scope includes it, per PORTAL-NEXT-01.1's
                          finding that Auditoria is a tab inside the
                          admin panel, not a separate page]
```

**Unused reference category**: "Simuladores" — the reference's own
fictional content here ("Simulação interativa de propostas") is
redundant with "Novos & Seminovos" once real content is substituted
(V1 has no separate simulator-only module distinct from Simulador de
Novos/Seminovos). Deliberately not populated, not silently dropped —
documented here as the disclosed reason.

**Content that does NOT fit this Wave's grammar (Gate 39 escape
valve, used at minimum scope)**: **Coparticipado**. V1's real grouping
pairs it with Score under "Gestão de Incentivos" (see below), but that
would either invent a 7th category not present in the frozen reference
(forbidden by Gate 38 — the reference cannot be altered) or push a
category to 3 blocks, exceeding the observed 1-2 max the approved
grammar actually uses anywhere. Rather than silently forcing it in or
inventing a new category, **Coparticipado is not represented as a
distinct Landing canvas entry this Wave.** It remains a real,
routable, `NOT_MIGRATED` entry in `config/module-registry.json` and
is reachable via the shell's persistent global nav — this is a
disclosed content-fit decision, not data loss. A future Wave/Design
System Change Proposal should resolve this properly (e.g., approving
a 7th category or a 3-block category) rather than this phase deciding
it unilaterally.

```
V1's real grouping, for reference (not used to override the frozen
Approved Reference's own category set, only informed the assignment
above where compatible):
  📊 Gestão            -> Análise Geral do Grupo, Análise F&I do Grupo
  💰 Gestão de Incentivos -> Coparticipados/Subsidiados, Análise de Score Vendedores
  🚗 Simuladores         -> Simulador de Novos, Simulador de Seminovos
  🎧 Atendimento F&I       -> Central de Atendimento F&I (not in V2's
                            registry — discovered this phase, not
                            previously catalogued in PORTAL-NEXT-01;
                            flagged for a future module-inventory
                            update, not added to Landing this Wave
                            without its own registry entry first)
```

**Must-not-show list respected**: no "Disponível"/"GE-01"-style debug
codes, no "1 módulo nesta categoria" counters, no LAB labels appear in
the Landing's real content — verified in `tests/anti-ai-audit.md`.

## Gate 42 — Logo / brand asset

Real institutional logo extracted read-only from V1's live `main`
(`gh api repos/.../contents/index.html?ref=main`, the `<img
class="headerLogo">` inline PNG) — Mitsubishi three-diamond mark +
wordmark, white-on-transparent, designed for a dark ground (matches
Portal's canvas). Saved to `assets/images/brabus-logo.png`. **Not
recreated, not redesigned, no proportion change, no glow, no
recoloring.** The Approved Reference's own `brandMark` treatment
(28×28 red-bordered monogram box, currently showing "B") is a
DIFFERENT, smaller, structural element (part of the global nav rail's
own design) — both are used as-is, in their own respective places, per
their own authorities (reference for the structural monogram, V1 for
the real institutional logo — see `index.html`'s header treatment for
exactly where each appears).
