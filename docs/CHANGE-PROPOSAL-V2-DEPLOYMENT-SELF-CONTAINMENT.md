# Change Proposal: V2 Self-Contained Deployable Unit + Pages Pipeline (GL-1B→GL-1G)

**Change ID:** `V2_SELF_CONTAINED_DEPLOYABLE_UNIT` / `V2_PRODUCTION_ARTIFACT_ALLOWLIST_PROVEN`
**Change type:** Deployment infrastructure preparation. No business logic,
no financial formula, no Score/Coparticipado/Simulator/Dashbi/Gestão/Painel
Master/Commissions/Intelligence logic touched.
**Authorization:** Human approved Strategy B (V2's own standalone repository
and GitHub Pages pipeline) in the prior Go-Live deployment architecture
reconciliation. This wave (GL-1B through GL-1G) implements the LOCAL
preparation gates only. GL-1H (Human go/no-go) and GL-1I (first real deploy)
remain separate, later, explicitly-authorized gates — **not requested and
not performed here**.

## Status

- **GL-1B (external dependency reconciliation):** COMPLETE.
  `EXTERNAL_RUNTIME_SIBLING_DEPENDENCIES = 0`, verified.
- **GL-1C (environment-guard contract):** COMPLETE. Redesigned from a
  blocklist to an explicit LOCAL_DEV / AUTHORIZED_PRODUCTION / UNKNOWN_HOST
  allowlist contract.
- **GL-1D (production config architecture):** COMPLETE.
  `intelligence-runtime-config.production.js` created, not yet loaded by
  `index.html` (see "Production config wiring" below).
- **GL-1E (artifact allowlist + Pages workflow):** COMPLETE.
  `.github/workflows/pages.yml` + `scripts/build-pages-artifact.sh` created.
- **GL-1F (local production-like smoke test):** COMPLETE. 27/27 PASS.
- **GL-1G (dry-run artifact audit):** COMPLETE. `UNEXPECTED_FILE_COUNT = 0`,
  zero forbidden content, zero credible secret pattern.
- **GL-1H / GL-1I:** NOT STARTED. No remote created, no push, no deploy.

## A note on a mid-wave collision, resolved cleanly

At preflight, `index.html` (one of this wave's required edit targets) had
active, uncommitted modifications from a parallel session (Painel do
Analista F&I, PA-1). Per this wave's own collision-safety instructions,
every OTHER gate (vendoring, guard rewrite, config creation, workflow,
local builder, smoke test) was completed first, entirely on files with no
overlap. The `index.html` edit was deliberately deferred. Partway through
this wave, the parallel session committed its own work
(`e739570`, "feat(v2): migrate analyst status panel"), leaving `index.html`
clean and stable. This wave then safely completed the deferred edit — no
file was ever touched while under concurrent modification, and the
parallel work is fully intact and unmodified by this wave.

## GL-1B — External dependency reconciliation

Four files were vendored byte-for-byte (SHA-256-verified) from sibling
directories of the parent `PORTAL-FI-DESIGN-LAB/` folder into V2's own
repository, plus the 8 font files one of them depends on. Full provenance,
dependency-graph findings, and the future synchronization policy are in
`docs/VENDORED-DESIGN-ASSETS-PROVENANCE.md`. Summary:

| Original | Vendored to |
|---|---|
| `../shared/fonts.css` (+ 8 `.woff2` files) | `assets/css/vendor/fonts.css` (+ `assets/css/vendor/fonts/`) |
| `../design-system-2/tokens.css` | `assets/css/vendor/design-tokens.css` |
| `../design-motion-lab-03/parametric-catalog.js` | `assets/js/vendor/parametric-catalog.js` |
| `../design-motion-lab-03/engine.js` | `assets/js/vendor/engine.js` |

`index.html` and `assets/css/shell.css`'s own doc comment were updated to
reference the vendored paths. Content is byte-identical to the originals —
no design decision was revisited, no value changed, no silent divergence.

**Finding, not fixed here:** `design-system-2/tokens.css` (now vendored as
`design-tokens.css`) contains Brabus-specific branding (a header comment
naming "BRABUS F&I DESIGN SYSTEM 2.0", a token literally commented
`/* Brand Red */`). This is exactly the kind of customer-specific content
the eventual generic-core/white-label goal will need to externalize —
flagged as future work, not addressed in this deployment-infrastructure
wave.

## GL-1C — Environment-guard contract redesign

`assets/js/environment-guard.js` was redesigned from a hardcoded hostname
BLOCKLIST (which could only ever say STOP, with no path to legitimately
authorize a real deployment) to an explicit ALLOWLIST contract:

- **LOCAL_DEV** — `localhost`/`127.0.0.1`. Always allowed.
- **AUTHORIZED_PRODUCTION** — hostname appears in the production config's
  own `authorizedHostnames` array. This can only ever come from that
  server-shipped file — never a client-editable query parameter or
  `localStorage` value.
- **UNKNOWN_HOST** — neither of the above. Fails closed, exactly as before,
  now reached via an allowlist miss instead of a blocklist hit.

Today, `authorizedHostnames` is an empty array in both the committed
default config and the new production config — **by design, per this
wave's own explicit instruction not to invent a final hostname.** Every
real host remains UNKNOWN_HOST (blocked) until a Human records the chosen
hostname there, a Go-Live Human checkpoint.

The authorization decision is computed inside the `DOMContentLoaded`
handler (not at top-level script execution), so it correctly sees
whatever `intelligence-runtime-config(.production).js` has loaded by then,
regardless of `environment-guard.js`'s own position in `index.html`'s
script order — no script reordering was required.

`window.NX_ENVIRONMENT.production` (a real existing consumer,
`dashbi.js:1087`, gates a dev-only diagnostic footer) is preserved,
now correctly tied to `name === 'AUTHORIZED_PRODUCTION'` rather than a mere
hostname-shape guess. Verified no regression via direct code inspection —
this consumer needed no change.

Three existing foundational docs (`README.md`, `docs/ARCHITECTURE.md`,
`docs/SAFETY.md`) described the OLD blocklist behavior and were corrected
with small, surgical edits — nothing else in those files was touched.

## GL-1D — Production config architecture

New file: `assets/js/intelligence-runtime-config.production.js`, modeled
directly on Secure's own `portal-runtime-config.production.js` (hand-
maintained, checked in, loaded via a plain relative `<script src>`, no
build-time substitution). Not yet loaded by `index.html` — see "Production
config wiring" below.

| Field | Value in this file |
|---|---|
| `mode` | `'fixture'` — Intelligence Text/Voice stays inert, per this wave's explicit instruction not to activate it |
| `supabaseUrl` / `supabasePublishableKey` | The SAME real, already-public values Secure's own tracked production config already ships today — reused, not invented, per Gate 18 |
| `turnstileSiteKey` | The SAME real, already-public Cloudflare Turnstile site key Secure already ships — reused, not invented |
| `textEndpoint` | `null` — Intelligence backend not deployed, unrelated to this wave |
| `authorizedHostnames` | `[]` — deliberately empty; the final V2 hostname has not been chosen |

`intelligence-runtime-config.js` (the committed default) gained the same
new `authorizedHostnames` field, defaulting to `[]` — safe on every host.
`intelligence-runtime-config.example.js` received a short comment noting
the field doesn't apply to local overrides. No secret of any kind — no
OpenAI key, no service-role key, no private token — was placed in any of
these files; this was verified structurally (see "Security scan" below),
not merely asserted.

**Production config wiring — deliberately NOT done this wave.** The new
production file is not referenced by `index.html`. Wiring it in (behind an
environment check, never unconditionally) is exactly the kind of decision
that should happen at GL-1H (Human go/no-go) once a real hostname is
chosen — populating it prematurely would risk the production config
silently becoming live before that checkpoint.

## GL-1E — Production artifact allowlist + Pages workflow

New file: `scripts/build-pages-artifact.sh` — a single, deterministic,
POSITIVE allowlist script, callable identically by the real workflow and
by local testing (so "what deploys" and "what was smoke-tested" can never
silently drift apart). New file: `.github/workflows/pages.yml`, modeled
directly on Secure's own proven `pages.yml` (same 3 standard GitHub Pages
actions), calling this script.

**Committing this workflow does not deploy anything.** This repository has
no git remote (confirmed, unchanged by this wave) — a workflow with no
remote behind it cannot trigger, cannot run, cannot publish.

Allowlist included: `index.html`, `assets/` (recursive, **excluding**
`*.local.js` — see the bug fix below), `config/module-registry.json`,
`config/landing-groups.json`, and the top-level `*.json` files under
`tests/fixtures/` (not the `.html`/`.js` files alongside them, not the rest
of `tests/`).

**Self-caught bug, fixed before use:** the script's first draft did a
blanket `cp -r assets/.`, which — when run against a real developer's own
working tree during local testing — pulled in the gitignored,
never-committed `intelligence-runtime-config.local.js`. A real CI checkout
would never have this problem (git never materializes an ignored,
uncommitted file), but relying on that distinction would have made the
LOCAL smoke test unreliable as a proof of what actually ships. Fixed by
explicitly excluding `*.local.js` in the copy step itself — verified fixed
via a direct re-check (0 matches for `*local*` in the rebuilt artifact).

**Fixture policy (Gate 20/21):** the committed default config has real
transport unconfigured (`supabaseUrl: null` in the default file, and the
new production file is not yet wired in) — so, as things stand today, a
real deploy of exactly what's committed would run every module in fixture
mode, needing `tests/fixtures/*.json`. Once a production config is wired
in at GL-1H, every module using `isRealTransport()` switches to real
transport automatically, and this fixture dependency disappears on its
own — this is not a separate migration to plan for later, it is an
automatic consequence of the existing `isRealTransport()` check already
in every real-data module.

## GL-1F — Local production-like smoke test

Artifact assembled via the script above into a temporary directory outside
the repository, served with a plain local HTTP server (not the whole
working tree — only the assembled artifact), driven with Playwright.
**27/27 checks PASS**, including:

- Environment guard correctly classifies `127.0.0.1` as `LOCAL_DEV` and
  allows rendering.
- A synthetic unauthorized-hostname check confirms the `UNKNOWN_HOST`
  fail-closed contract holds under the current empty `authorizedHostnames`
  (structural verification of the classification logic; a full live
  render-block against a genuinely different real hostname would need
  DNS-level test infrastructure beyond this wave's scope).
- `config/module-registry.json` and `config/landing-groups.json` both
  fetch with HTTP 200.
- All 4 vendored design-system assets serve correctly.
- Zero remaining `../shared/`, `../design-system-2/`, or
  `../design-motion-lab-03/` references anywhere in the served page —
  `EXTERNAL_RUNTIME_SIBLING_DEPENDENCIES = 0`, proven, not merely claimed.
- 7 representative routes (Score, Coparticipado, Gestão, Dashbi, Simulador
  Novos, Simulador Seminovos, Painel Master shell) each navigate with zero
  console errors.
- Zero horizontal overflow at 1366/1024/900/480px.
- Exactly 1 network request fails (`intelligence-runtime-config.local.js`,
  404) — correctly classified `EXPECTED_INERT_FEATURE` (proof the
  gitignored-file exclusion works), not `BROKEN_PRODUCTION_ARTIFACT`.

## GL-1G — Dry-run artifact audit

118 files in the assembled artifact. Every forbidden-content category
checked explicitly, all 0 matches: `tests/*.py`, harness/bridge HTML,
`screenshots/`, `docs/`, `README`, `.git`, `.gitignore`, `*local.js`,
migrations, `.env*`. Sensitive-string scan (OpenAI-key shape, service-role
references, PEM private key headers, JWT-shaped tokens): 2 matches, both
confirmed false positives — code comments explicitly documenting the
*absence* of service-role usage, not key material. No `UNEXPECTED_FILE`
category was needed — every file present maps cleanly to
`REQUIRED_RUNTIME`, `PUBLIC_CONFIG`, or `VENDORED_RUNTIME_DEPENDENCY`.
Base-path check: zero absolute-root (`/`-leading) paths in the assembled
`index.html` — portable to any future subpath.

## Regression — existing test suites

`tests/registry-test.py`: PASS, unaffected.

`tests/foundation-regression.py`: **FAIL, pre-existing, not caused by this
wave.** Its "No business logic (Gate 16)" check — an early-Foundation-
phase rule that no real Supabase host string or business-logic pattern may
appear ANYWHERE in the repo — flags 5 patterns. **4 of the 5 already
existed before this wave touched anything**: a real Supabase host string
already present in the developer's own pre-existing local override file
(`intelligence-runtime-config.local.js`, never created or modified by this
wave), a commission-engine function name in `master-competence-closing-
engine.js` (from an earlier Painel Master wave), and 2 references in
pre-existing untracked test-bridge/reference files. The 5th match is this
wave's own new `intelligence-runtime-config.production.js`, and its
Supabase host string is exactly what Gate 15 of this wave's own brief
required — not a defect. This test's own "zero backend anywhere" premise
was already obsolete before this wave, given the many real-data modules
(Score, Coparticipado, Gestão, Dashbi, Painel Master, Painel do Analista)
this project has since built; it was not fixed here (out of this wave's
scope — no production business-logic file was touched), and is recorded
as a debt below.

## Security scan summary

- No committed secret found anywhere in the assembled artifact (Gate 32).
- `authorizedHostnames` cannot be set by a client — it only ever comes from
  a server-shipped static file, never a query parameter or `localStorage`.
- No OpenAI key, no service-role key, no private Cloudflare secret, no JWT
  signing secret was placed in any file this wave touched or created.
- Intelligence Text/Voice remain fully inert in every config this wave
  shipped.

## Debts / open items (not resolved this wave)

- `tests/foundation-regression.py`'s "No business logic (Gate 16)" check
  is stale relative to the project's current real-data state (4 of 5
  pre-existing failures). Not fixed here — recommend a small, separate,
  explicitly-scoped hygiene wave.
- `design-system-2/tokens.css` (now vendored) contains Brabus-specific
  branding, relevant to the future white-label/generic-core goal. Not
  addressed here.
- The Turnstile site key's hostname binding lives in Cloudflare's own
  dashboard, external to both repos — must be checked/updated once a real
  V2 hostname is chosen (Go-Live Human checkpoint), independent of any
  code in either repository.
- Production config wiring into `index.html` remains deliberately
  undone, pending GL-1H.

## Files changed

Production: `index.html`, `assets/css/shell.css` (comment only),
`assets/js/environment-guard.js`, `assets/js/intelligence-runtime-
config.js`, `assets/js/intelligence-runtime-config.example.js`.
New: `assets/js/intelligence-runtime-config.production.js`,
`assets/css/vendor/` (13 files), `assets/js/vendor/` (2 files),
`.github/workflows/pages.yml`, `scripts/build-pages-artifact.sh`,
`docs/VENDORED-DESIGN-ASSETS-PROVENANCE.md`, this document.
Docs (small, surgical corrections only): `README.md`,
`docs/ARCHITECTURE.md`, `docs/SAFETY.md`.

No business logic, no financial formula, no Score/Coparticipado/
Simulator/Dashbi/Gestão/Painel Master/Commissions/Intelligence logic file
was touched.

## GL-1H → GL-1K addendum (Go-Live external homologation)

- **GL-1H (pre-gate):** COMPLETE. `GL1H_READY_FOR_EXTERNAL_HOMOLOGATION_CREATION`.
  No external action performed; identified the environment-guard
  hostname-authorization and Turnstile host-binding items as the two
  remaining prerequisites.
- **GL-1I (repository creation):** `luisgamadio-spec/portal-fi-v2`
  created PRIVATE, `origin` connected, `main` pushed
  (`ec12de6970e26281d4e66aea666c64211dc7516a`). Pages enablement failed:
  `PRIVATE_PAGES_PLAN_RESTRICTION` (proven via GitHub API 422).
- **GL-1I.1 (public exposure):** Full-history public-exposure audit (122
  commits) found 0 real secrets, 0 customer PII. Repository changed
  PRIVATE → PUBLIC (Human-authorized). Pages enabled and deployed
  successfully. `REAL_HOMOLOGATION_URL =
  https://luisgamadio-spec.github.io/portal-fi-v2/`, proven directly
  from GitHub's own Pages API. Environment Guard correctly blocked the
  new hostname (`UNKNOWN_HOST`) — expected, proven working as designed.
- **GL-1J (hostname authorization):** Commit `dca34bdadc7dad1c1c3adbc9e043eb53af5093cd`
  authorized exactly `luisgamadio-spec.github.io` in
  `intelligence-runtime-config.production.js`'s `authorizedHostnames`
  and wired it into `index.html` behind an exact-match host-conditional
  loader. Deployed and live-verified: `NX_ENVIRONMENT.name ===
  'AUTHORIZED_PRODUCTION'`, Landing/Login publicly reachable, STOP
  screen gone. Turnstile hostname-binding left unverified (no
  Cloudflare tooling available this wave, no login performed) —
  classified `TURNSTILE_HOST_BINDING_HUMAN_ACTION_REQUIRED`.
- **GL-1K (Human published-login approval + network-guard fix):**

  **Human evidence (authoritative, verbatim):** after opening the real
  published URL and visually confirming the Turnstile widget ("Portal FI
  Brabus") already listed `luisgamadio-spec.github.io` alongside its
  established hosts, the Human performed the first real published
  MASTER login and responded exactly:

  > "validado"

  Classification: `REAL_HOMOLOGATION_LOGIN_HUMAN_APPROVED`,
  `TURNSTILE_HOMOLOGATION_HOST_BINDING_HUMAN_PROVEN`. No further
  Cloudflare mutation required.

  **Network-guard fix:** GL-1J's own live check had already surfaced a
  false positive — `assets/js/network-guard.js` listed
  `luisgamadio-spec.github.io` in `REAL_BACKEND_HOST_PATTERNS`, so
  same-origin static requests (e.g. `config/module-registry.json`)
  resolved against that hostname and were misclassified as real-backend
  calls. Reproduced (RED), fixed at the semantic level — same-origin
  requests are now excluded before any hostname-pattern check runs, so
  this cannot recur for any future hosting origin — and the now-redundant
  hostname entry removed. 6/6 new focused regression assertions pass;
  the existing GL-1J hostname contract (13/13) and `registry-test.py`
  remain green. Commit deployed and live-verified: 0 flagged same-origin
  requests, real-backend protection (Supabase, `api.openai.com`,
  `brabus.blistiq.com.br`) unchanged.

  CA-1 (Central de Atendimento F&I, `a0e7b9b`/`e6ab438`,
  `CENTRAL_FI_HUMAN_APPROVED_REFROZEN` locally) remained intentionally
  excluded from this deployment lineage as of GL-1K — GL-1K did not
  synchronize it. GL-1L (below) is the later wave that performed that
  reconciliation.

- **GL-1L (controlled lineage reconciliation):** Merge commit
  `69d2318e9d0e78e24805b59cf61fcd9bffd7d776` (parents `5598f7a`, `e6ab438`)
  reconciled the Human-approved, frozen Central de Atendimento F&I
  lineage into this deployment lineage. Merge-base proven
  (`ec12de6`); the two lineages overlapped in exactly one file
  (`index.html`, three non-adjacent regions) and merged with zero manual
  conflict resolution. Full-tree diff against both parents proved no
  content was lost on either side. Every required regression suite
  passed at its exact expected baseline (Central 64/64 + 10/10, registry
  PASS, auth-catalog 40/40, Painel do Analista 30/30 + 8/8,
  master-admin-route 18/18, GL-1J hostname 13/13, GL-1K network-guard
  6/6, landing composition 20/20), plus zero horizontal scroll on
  Landing/Central Dashboard/Gestão/Histórico. Deployed and live-verified:
  `AUTHORIZED_PRODUCTION`, network-guard clean, Intelligence inert, 0
  console errors. Closed with `PUBLISHED_CENTRAL_TRANSPORT_SMOKE_PENDING`
  — the Human was asked to perform one small published transport smoke
  (real MASTER login, confirm Central visible on Landing, open Central
  Dashboard, confirm normal render) before that status could close.

- **GL-1M (integrated homologation transport-smoke refreeze,
  governance-only, no runtime change):** the Human performed exactly the
  requested published transport smoke and responded verbatim:

  > "validado"

  Scope of this evidence: real MASTER published login on
  `https://luisgamadio-spec.github.io/portal-fi-v2/`; confirmed "Central
  de Atendimento F&I" visible on Landing; opened Central Dashboard;
  confirmed normal render. **No mutation performed. No export performed.
  No functional Central re-UAT performed** — Central's own functional
  approval remains the CA-1B evidence recorded above, unchanged.

  Classification: `PUBLISHED_CENTRAL_TRANSPORT_SMOKE_HUMAN_APPROVED` —
  closes GL-1L's `PUBLISHED_CENTRAL_TRANSPORT_SMOKE_PENDING`. Integrated
  deployed commit at the time of this evidence:
  `69d2318e9d0e78e24805b59cf61fcd9bffd7d776`. `CENTRAL_FI_HUMAN_APPROVED`,
  `CENTRAL_FI_HUMAN_APPROVED_REFROZEN`, and `CENTRAL_FI_FROZEN` are
  unchanged and preserved — this wave records deployment/transport
  evidence only, not a new functional decision. No runtime, Auth,
  deployment-infrastructure, or business-logic file was touched by this
  wave; `config/module-registry.json` was left unmodified (Gate 12) since
  it already correctly records Central's functional `HUMAN_APPROVED`
  status and this wave's evidence is deployment-level, not functional.
