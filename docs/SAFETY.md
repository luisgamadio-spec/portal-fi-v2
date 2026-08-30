# Safety (Gate 38)

## THIS IS NOT PRODUCTION.

```
Environment:    NEXT_LOCAL
Production:     NO
```

## Hard rules

```
NO PUSH        — this repo has zero remotes configured, on purpose.
                 Do not add one without an explicit human decision to
                 promote V2 beyond local development.
NO DEPLOY       — no GitHub Pages workflow, no Netlify/Vercel config,
                 no deploy script of any kind exists in this tree.
NO PRODUCTION    — no production hostname appears anywhere as a deploy
TARGET             target. assets/js/environment-guard.js actively
                 refuses to render if it ever detects one at runtime.
```

## Before starting any Wave

Run `python config/pre-wave-check.py`. It reports (does not
auto-block): V2 root, git branch/HEAD, remotes, environment, expected
network targets, Design System authority path, Skill authority path,
the recorded production fingerprint, and — critically — the REAL V1
repo's current branch (must be `main`; anything else is a context
error).

## Why the "no branch protection on main" fact matters here

`portal-financiamento-brabus-secure`'s `main` has **no branch
protection** (confirmed via GitHub API in PORTAL-NEXT-01.1) — any push
reaches production immediately, with zero required review. This
Foundation was built with that fact treated as load-bearing, not
academic:

- V2 lives in its own independent local git repository, not a
  worktree of V1's repo (a worktree still shares V1's remote
  configuration — a fresh `git init` with zero remotes removes even
  the possibility of an accidental `git push` reaching production).
- Every guard in this Foundation (`environment-guard.js`,
  `network-guard.js`, the business/auth boundary stubs) is designed to
  fail loud, not silently succeed, if context is ever ambiguous.
- **Gate 35's rule**: if repo/branch/remote/production-branch context
  is ever ambiguous before a local V2 commit, STOP. Do not guess.

## Rebaseline Review (Gate 29)

This Foundation's own `config/v1-change-detection.py` discovered,
during this phase, that `origin/main`'s real tip had moved since
PORTAL-NEXT-01/01.1 audited it (local clone was stale). This did NOT
block Foundation work — see `config/production-fingerprint.json` for
the full, disclosed finding and `REPORT.md`'s PORTAL-NEXT-02 entry.
**Lesson encoded here**: always trust `config/v1-change-detection.py`'s
live check over any previously-recorded document, including this one.

## What this phase did NOT do

- No commit/push/merge to any real repository.
- No V1 file read, write, or diff beyond what PORTAL-NEXT-01/01.1
  already audited (this phase used `git ls-remote` + `gh api`, both
  read-only, to check the drift above — no `git fetch`, no `git pull`,
  no local V1 working-tree change).
- No module migrated, no business logic ported, no real backend called.
