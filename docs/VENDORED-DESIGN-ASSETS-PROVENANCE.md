# Vendored Design-System Assets — Provenance (GL-1B)

**Change ID:** `V2_SELF_CONTAINED_DEPLOYABLE_UNIT` (partial — see the Go-Live deployment
reconciliation report for full context; this document covers only GL-1B).

**Why this exists:** the prior deployment-architecture reconciliation found that
`index.html` referenced four runtime files living in sibling directories of the
parent `PORTAL-FI-DESIGN-LAB/` folder, outside this repository entirely
(`../shared/fonts.css`, `../design-system-2/tokens.css`,
`../design-motion-lab-03/parametric-catalog.js`, `../design-motion-lab-03/engine.js`).
A standalone V2 repository (Strategy B) cannot depend on files outside its own
tree. This document records the byte-identical vendoring of those four files
(plus the 8 font files `fonts.css` itself depends on) into V2's own repository,
so `EXTERNAL_RUNTIME_SIBLING_DEPENDENCIES` can eventually reach 0.

**Update — index.html now wired in**: at the time this vendoring was
performed, `index.html` was under active, uncommitted modification by a
parallel session (Painel do Analista F&I). This wave deliberately vendored
the files first and deferred editing `index.html` until that parallel work
committed, to avoid any risk of colliding with it. That commit
(`e739570`, "feat(v2): migrate analyst status panel") landed before this
wave finished, leaving `index.html` clean — the 4 references were then
updated in this same wave, in a separate, later commit. `EXTERNAL_RUNTIME_
SIBLING_DEPENDENCIES = 0`, verified by repository-wide search (see the
deployment reconciliation report for the exact verification command).

## Dependency graph (established before copying, per GL-1B)

- `shared/fonts.css` — self-contained `@font-face` declarations, referencing 8
  `.woff2` files via a path (`fonts/*.woff2`) relative to itself. No further
  dependencies. No Brabus-specific content. No secrets.
- `design-system-2/tokens.css` — pure CSS custom properties (`:root{...}`).
  Zero `url()`/`@import`/further file dependencies. **Contains Brabus-specific
  branding** (header comment "BRABUS F&I DESIGN SYSTEM 2.0", a token literally
  named `--p-red-2` commented `/* Brand Red */`). Flagged for the future
  white-label/generic-core goal — not blocking for this wave, vendored as-is
  per the "no silent divergence" rule.
- `design-motion-lab-03/parametric-catalog.js` — defines `window.MOTION_CATALOG`
  and `window.MOTION_ENGINE_HELPERS`. No file dependencies; only standard
  browser globals (`Math`, `window`).
- `design-motion-lab-03/engine.js` — depends on `window.MOTION_CATALOG` being
  already defined (must load AFTER `parametric-catalog.js`, matching the
  existing script order) and on 2 CSS custom properties (`--brand-red`,
  `--accent-primary`) being already defined by `tokens.css`. Uses only
  standard browser APIs (`ResizeObserver`, `IntersectionObserver`,
  `requestAnimationFrame`, `matchMedia`). No further file dependencies.

No secrets, tokens, or environment-specific values were found in any of the 4
files. Total dependency closure: 4 source files + 8 font files, ~253KB.

## Provenance table

| Original path (relative to `PORTAL-FI-DESIGN-LAB/`) | Original SHA-256 | Vendored path (relative to `portal-next-v2/`) | Byte-identical |
|---|---|---|---|
| `shared/fonts.css` | `fe06be3b632413006866437910dec8ac0fc720eba304cf5e003177bc8c2a6273`* | `assets/css/vendor/fonts.css` | YES |
| `design-system-2/tokens.css` | `55bfed53ff4883da8e00e416ecc743068da20ca3cb5fc248d24e6151177c9b13`* | `assets/css/vendor/design-tokens.css` | YES |
| `design-motion-lab-03/parametric-catalog.js` | `0c0b1353658b7860318f8f77c752e653f641f1f00d100a729b1781300d735d5b`* | `assets/js/vendor/parametric-catalog.js` | YES |
| `design-motion-lab-03/engine.js` | `47aee884ab9972f6d340981ac7af806e7d274af9f20ce6307aec7ffca2d44b8b`* | `assets/js/vendor/engine.js` | YES |
| `shared/fonts/archivo-var.woff2` | `8f704806dbedeaaeca334b11ec348bc3ac3a439d6431544b3afb54f534ee4967`* | `assets/css/vendor/fonts/archivo-var.woff2` | YES |
| `shared/fonts/ibm-plex-mono-400.woff2` | `08949f728dc52d528e69b1667d15c89a5686a4ee9a296ff90983985f99c380f7`* | `assets/css/vendor/fonts/ibm-plex-mono-400.woff2` | YES |
| `shared/fonts/ibm-plex-mono-500.woff2` | `01d285447409c8a588692162439a038b8cbd7871309ee20267b0d2d91c6e8e22`* | `assets/css/vendor/fonts/ibm-plex-mono-500.woff2` | YES |
| `shared/fonts/ibm-plex-mono-600.woff2` | `0d1f0b8d0722224e32e9f28261bdc86c79115be73444ae5eceb73976a1bcdf83`* | `assets/css/vendor/fonts/ibm-plex-mono-600.woff2` | YES |
| `shared/fonts/ibm-plex-sans-var.woff2` | `e2291e842cf5af167122a22881a740c7f2dda7716f1e8cd76680264f4a859470`* | `assets/css/vendor/fonts/ibm-plex-sans-var.woff2` | YES |
| `shared/fonts/instrument-sans-var.woff2` | `2ee17598a98d8a59e4df8152d015bec9ab8e4d5672cc0ab42bef806b568e3971`* | `assets/css/vendor/fonts/instrument-sans-var.woff2` | YES |
| `shared/fonts/red-hat-display-var.woff2` | `f7a7830b81e351f89b91f0201de71c8d937e25df5a3e31ecca9b4ee877abedb7`* | `assets/css/vendor/fonts/red-hat-display-var.woff2` | YES |
| `shared/fonts/red-hat-text-var.woff2` | `59826f39dcb265c6aa94d978cc0941a083df5acc7f447324ecf6f58ad19d6b7c`* | `assets/css/vendor/fonts/red-hat-text-var.woff2` | YES |

\* SHA-256 of the ORIGINAL file at time of vendoring (2026-09-07), captured via `sha256sum`.
Byte-identity of every pair was independently re-verified by comparing source and
vendored hashes directly (not merely trusting the copy operation) — all 12 matched.

`fonts.css` and `design-tokens.css` were copied byte-for-byte, including their
relative `url()` references — `fonts.css`'s own `url('fonts/instrument-sans-var.woff2')`-
style references continue to resolve correctly because the font files were vendored
into the matching relative subdirectory (`assets/css/vendor/fonts/`), preserving the
exact directory-shape the original CSS expects. No line of any vendored file was
modified.

## Reason for vendoring

Portal V2 is targeting its own, standalone deployment (Strategy B — see the
Go-Live deployment architecture reconciliation report). A deployable unit
cannot depend on files living outside its own repository. These four files
(plus their own font dependency) are the entirety of that external
dependency — everything else V2 needs already lives inside this repo.

## Future synchronization policy

These are vendored **snapshots**, not a live symlink or build-time fetch. If
the source design-lab files (`shared/fonts.css`, `design-system-2/tokens.css`,
`design-motion-lab-03/{parametric-catalog,engine}.js`) are ever updated with a
deliberate, human-approved design change, the vendored copies in this repo
must be updated by the same provenance process: re-copy, re-hash, update this
table, and re-run the design-system regression check (Section "Regression —
Design System" of the deployment reconciliation report). Do not let the two
copies silently drift — this table's hashes are the audit trail for detecting
drift, not a promise of automatic sync.

## Completion

`index.html` now references:
- `assets/css/vendor/fonts.css` (was `../shared/fonts.css`)
- `assets/css/vendor/design-tokens.css` (was `../design-system-2/tokens.css`)
- `assets/js/vendor/parametric-catalog.js` (was `../design-motion-lab-03/parametric-catalog.js`)
- `assets/js/vendor/engine.js` (was `../design-motion-lab-03/engine.js`)

Re-verified via a repository-wide search for `../shared/`, `../design-system-2/`,
and `../design-motion-lab-03/`: no production file (`index.html`, anything
under `assets/`) references them anymore. The only remaining references are
in dev-only test harness files under `tests/` (which run directly against
the developer's own checkout, where the sibling directories genuinely exist
on disk, and are never part of any deploy artifact) and documentation —
neither is in scope for this self-containment goal.
