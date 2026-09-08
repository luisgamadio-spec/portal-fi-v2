# Change Proposal: Painel do Analista F&I — V1 → V2 Migration (PA-1)

**Change ID:** `PA-1`
**Change type:** New module migration (self-service queue-status
control) — not financial business logic, not a redesign of any frozen
module.
**Module:** `painel-analista-fi` (new route `/painel-analista-fi`).
**Authorization:** Go-Live audit discovery — a real, live V1 surface
(0% migrated) explicitly scoped for this wave.

## Status (2026-09-07)

- **Authority discovery:** COMPLETE.
- **Authority classification:** `ANALYST_PANEL_BACKEND_AUTHORITY_PROVEN`.
- **Permission classification:** `ANALYST_PANEL_PERMISSION_READY`.
- **SAFE_TO_IMPLEMENT:** YES.
- **Implementation:** COMPLETE (technical).
- **Target state:** `UAT_PENDING` (this repository's canonical
  equivalent of `TECH_READY_HUMAN_UAT_PENDING`). NOT `HUMAN_APPROVED`.

## V1 authority (read-only discovery, Secure repository)

Located in full in `assets/js/portal-app.js:1932-2043`
(`portal-financiamento-brabus-secure`, branch `hotfix/fandi-analista-
group-scope`, itself `origin/main` + 3 unrelated commits — confirmed
via `git log origin/main`, not assumed): `carregarMeuAnalistaFi()`,
`painelAnalistaMsg()`, `showPainelAnalistaFi()`,
`atualizarResumoPainelAnalistaFi()`, `alterarMeuStatusAnalistaFi()`.
This independently-rediscovered contract matches, field for field, a
pre-existing scoping note already present in `config/module-
registry.json`'s own `painel-analista-fi` entry (written during an
earlier AUTH FOUNDATION Phase 2A discovery pass) — strong corroboration
of both audits.

**Access control (V1):** two independent gates, both role-only, no
department/store scoping —
1. `portalAllowedModules()` includes `'painelAnalistaFi'` only for
   `tipo === 'MASTER'` or `tipo === 'ANALISTA'`.
2. `showPainelAnalistaFi()` re-checks the same condition before
   rendering.

**RPC contract (both confirmed live/ATIVA, `SECURITY DEFINER`, granted
to `authenticated`, in `supabase/baseline/MANIFEST.md` — Git=`C`,
meaning deployed directly to production, never committed to this
repo's migrations):**
- `operational_my_analyst_fi()` — read, 0 parameters. Identity resolved
  server-side from `auth.uid()`, never a client-supplied CPF. Returns
  `{row: {...}|null}`. V1 reads `row.status`, `row.atendimentos_hoje`,
  `row.ultimo_atendimento`, `row.ultimo_status_em`.
- `atualizar_meu_status_analista_fi(p_status text)` — write. Identity
  server-derived, same as above. Returns `{sucesso: boolean, mensagem:
  string}`.
- `chamar_analista_fi()` and `gestor_listar_analistas_fi()` also exist
  (confirmed live) but are **out of scope**: the first is the
  simulators' own "Falar com um analista" WhatsApp-lookup consumer (a
  different caller, different UI, not this analyst's own panel; no V2
  simulator currently exposes that button); the second backs the
  separate MASTER-only management console (`central-atendimento-fi`,
  already a distinct registry entry, not touched this wave).

**Table authority (read-only, confirmed against the real project this
wave):** `analistas_fi` exists, 11 real rows, columns confirmed:
`id, nome, whatsapp, teams_link, status, ativo, ordem_fila,
ultimo_atendimento, criado_em, online, atendimentos_hoje, ocupado,
cpf_normalizado, ultimo_status_em, observacao_status`. Every field the
V1 controller reads is present. Live distinct `status` values observed:
`ONLINE`, `OFFLINE`, `FÉRIAS` — `OCUPADO`/`ALMOÇO` are valid by backend
contract (the two write-RPC-accepting UI buttons already in production)
even though no analyst happened to hold those values at query time.

**Status set (exact, preserved verbatim — never translated/invented):**
`ONLINE`, `OCUPADO`, `ALMOÇO`, `FÉRIAS`, `OFFLINE`.

## Auth Foundation compatibility

`painelAnalistaFi` is registered in the backend's `modulos_portal`
catalog with `configuravel = false` — it deliberately does **not**
participate in the dynamic `permissoes_modulos` perfil×departamento
matrix (confirmed by direct migration read: zero `permissoes_modulos`
rows exist for this module id). Access is governed exclusively by the
simple role check described above.

V2 already had a purpose-built `authMode` constant for exactly this
case — `ANALISTA_OR_MASTER` — implemented in `assets/js/auth-core.js`'s
`isModuleAuthorized()` **before this wave** (`case 'ANALISTA_OR_MASTER':
return context.isMaster === true || context.perfil === 'ANALISTA';`).
**Zero new authentication/authorization code was required.** The
existing registry entry already declared this `authMode`; this wave
only had to build the module behind it.

## Implementation

1. **`assets/js/adapters/painel-analista-fi-real-provider.js`** (new) —
   thin transport, identical pattern to `gestao-real-provider.js`/
   `coparticipado-governed-rates-provider.js`: reuses `window.NX_AUTH`/
   `window.NX_INTELLIGENCE_CONFIG`, no independent Supabase client, no
   service_role. Exposes `loadMeuAnalista()` and
   `atualizarMeuStatus(status)`.
2. **`assets/js/painel-analista-fi.js`** (new) — page controller/view.
   State machine: `LOADING → READY | NOT_LINKED | ERROR`, plus a
   `saving` flag disabling the status buttons mid-write. **Non-
   optimistic**, matching V1: after a successful write, the page
   re-fetches the authoritative record rather than assuming the write
   applied as requested. **Fail-closed**: the 5 status buttons only
   exist in the `READY` state; any load failure shows a Portuguese
   message with a Retry action, never a silent/fake/cached status. A
   missing analyst record (`NOT_LINKED`) shows a clean message that
   does **not** leak the internal table name (`analistas_fi`) to the
   end user, unlike V1's own literal text — the one deliberate, minimal
   wording improvement made this wave, not a behavior change.
3. **`assets/css/painel-analista-fi.css`** (new) — built on
   `design-system-2/tokens.css`, following the same per-module
   stylesheet convention as `simuladores.css`/`coparticipado.css`/
   `score.css`. Status communicated via text + icon, never color alone
   (current-status pill always shows the word; each button pairs an
   emoji with a bold label, same as V1). Status buttons and summary
   cards use `auto-fit` responsive grids (comfortable ≥44px tap targets
   confirmed at 480px) — no forced desktop table, no horizontal scroll
   at any tested width.
4. **`index.html`** — one new `<link>` + two new `<script>` tags, in
   the same load-order position as the sibling Simulador Novos/
   Seminovos entries.
5. **`assets/js/shell.js`** — one additive line in the existing
   `MODULE_PAGES` route-dispatch map (`'painel-analista-fi':
   'NX_PAINEL_ANALISTA_FI_PAGE'`), following the established convention
   exactly. No existing route entry touched.
6. **`config/landing-groups.json`** — one new group, `"Atendimento
   F&I"` (V1's own group label, for continuity), containing exactly
   `painel-analista-fi`. No existing group modified.
7. **`config/module-registry.json`** — the pre-existing scaffolded
   entry's `entryPoint`/`migrationWave`/`migrationStatus` filled in with
   the real implementation, plus a new `migrationPA1Note` field
   recording this wave's evidence. The entry's own prior discovery
   `notes` field preserved verbatim. `central-atendimento-fi` (the
   separate MASTER-only management counterpart) was **not** touched.

## What was explicitly NOT done

- No department/store scoping was added — V1 has none, and none was
  invented.
- No call-center analytics, dashboard, CRM, chat, or ticketing feature
  was added — this is the same self-service status control V1 has,
  nothing more.
- No backend/database change — 0 migrations, 0 schema changes, 0
  permission-matrix rows added, 0 RPCs created or modified.
- `chamar_analista_fi` (simulators' consumer RPC) was **not** wired
  into any V2 simulator this wave — explicitly out of scope, a separate
  concern with a separate caller.
- Score, Coparticipado, Simulador Novos, Simulador Seminovos, Dashbi/
  Gestão financial logic, Cash Conversion, commission formulas — none
  touched.
- No real production status mutation was performed to test this — every
  test routes a mocked RPC response at the network layer; 0 real network
  calls, 0 real Supabase project touched by the test suite.

## Tests

- **`tests/painel-analista-fi-test.py`** (new, 30/30): `READY` state
  with all 5 exact V1 status values/accents preserved; current-status
  pill communicates status by text (not color alone); accented status
  (`FÉRIAS`) round-trips correctly; `NOT_LINKED` state with no internal
  table name leaked and no status buttons rendered; network failure,
  `42501` permission-denied, and session-expired (no access token) all
  fail closed — `ERROR` state, Retry present, **zero** status buttons
  rendered (no fallback/fake status ever shown); Retry recovers to
  `READY`; a successful status change re-fetches the authoritative
  record (non-optimistic, 2 reads observed) and shows the server's own
  success message; a server-reported failure (`sucesso: false`) surfaces
  the server's own message verbatim and does **not** silently change
  the displayed status; an RPC transport failure on write shows an
  error message, never silence; zero horizontal overflow and ≥44px
  tappable status buttons confirmed at 1366/1024/900/480px.
- **RED-before-fix proven empirically**: the two new implementation
  files were temporarily moved aside (a brand-new module has no prior
  "broken" version to `git stash` back to), the test suite was run
  against their absence, and it failed for the correct reason — the
  harness times out waiting for `window.NX_PAINEL_ANALISTA_FI_PAGE`,
  which never gets defined. Files restored and 30/30 reconfirmed.
- **`tests/registry-test.py`** (reconfirmed green): its
  `EXPECTED_STATUS` allowlist gained one new entry,
  `"painel-analista-fi": {"NOT_MIGRATED", "UAT_PENDING"}`, following the
  exact same documented precedent already used for every other module
  that has ever changed status in this file (Score, Coparticipado,
  Gestão, Dashbi, the simulators, shell-admin) — not an ad hoc
  exception.
- **`tests/auth-catalog-drift-test.py`** (reconfirmed green, 40/40):
  already contained dedicated checks for `painel-analista-fi`'s
  `ANALISTA_OR_MASTER` authMode and its `permissionId` resolving to a
  known backend catalog entry — both passed without any change to that
  test file, confirming the registry entry is well-formed by a
  pre-existing, independent check.
- **`tests/foundation-regression.py`**: one pre-existing, unrelated
  failure noted (not caused by this wave): `business-logic-scanner.py`
  flags 4 items, none of which reference `painel-analista-fi` or any
  file this wave touched (a gitignored local config, a commission
  engine file, an unrelated test harness, and a V1 reference file) —
  confirmed identical before and after this wave's changes.

## Parallel work safety

A concurrent session (GL-1, expected read-only) added new untracked
paths (`assets/css/vendor/`, `assets/js/vendor/`, `docs/VENDORED-
DESIGN-ASSETS-PROVENANCE.md`) during this wave. None of them overlap
with any file this wave modified or created — confirmed by direct
`git status` inspection before finalizing. No collision.

## Risks

- **Low.** No new backend surface, no new permission, reuses an
  already-implemented auth mode and an already-established provider
  pattern.
- `atualizar_meu_status_analista_fi`'s exact server-side validation
  logic (which `p_status` values it accepts) could not be read directly
  (the function body is DB-only, not committed to any migration) — the
  5-value contract is established by V1's own UI offering exactly these
  5 write options in production today, which is the strongest available
  evidence, but not a literal read of the function's own `CHECK`/`IF`
  logic. If the backend ever rejects one of these 5 exact strings, the
  module already fails closed (server-reported `sucesso: false` message
  shown verbatim, status never silently changed) — no masking risk.

## PA-1A — local Turnstile login blocker (2026-09-07)

Human's first UAT attempt was blocked before reaching the module by a
local-only login failure ("Não foi possível validar a verificação de
segurança"). Root cause: the gitignored local runtime config
(`assets/js/intelligence-runtime-config.local.js`) had
`turnstileSiteKey: null`, so Login never rendered the real Cloudflare
widget/token, and the real Supabase project rejected the captcha-less
sign-in — the same historical pattern already fixed twice in earlier
V2 waves. Fixed by restoring the already-documented, already-public
site key value in that same gitignored file. Zero tracked files
changed, zero commit for that fix (purely local/gitignored).

## PA-1B — Landing visibility defect (2026-09-07)

After PA-1A's login fix, the Human successfully logged in as ANALISTA
and reached Landing — but the "Atendimento F&I" group / "Painel do
Analista F&I" tile was not visible.

**Root cause, proven, not assumed:** a rigorous reproduction of the
real authentication flow (mocked Supabase client injected before any
V2 script runs, via the exact same technique already established in
`tests/auth-foundation-test.py` — not a naive `window.NX_AUTH`
override, which `auth-boundary.js`'s own real client construction
clobbers) with a genuinely authenticated ANALISTA session proved that
`landing.js`/`module-registry.js`/`auth-core.js`'s authorization logic
was **already 100% correct** — "Atendimento F&I" rendered, "Painel do
Analista F&I" rendered as an authorized, clickable link, exactly as
intended. **This ruled out every authorization-logic hypothesis**
(ANALISTA_OR_MASTER unsupported at the Landing layer, module-ID
normalization mismatch, dynamic-permission false filter, invalid group
config, UAT_PENDING visibility policy, runtime context normalization
error).

The remaining, best-supported explanation: `config/landing-groups.json`
and `config/module-registry.json` were fetched with a plain `fetch()`
call, no cache directive, no `Cache-Control` header from the local
static server (only `Last-Modified`) — across a single long Human
browser session spanning this entire day's multiple Waves, a
heuristically-cached stale response (predating PA-1's own commit,
which is what structurally added the "Atendimento F&I" group) can be
served silently, with no error, indefinitely, until a hard refresh.
This is the same general class of caching bug already encountered and
fixed once before in this project's history (a different, unrelated
sub-resource, fixed with a versioned cache-buster at the time).

**Fix (narrow, 2 files, no auth/authorization-logic change):**
`assets/js/landing.js`'s `loadGroups()` and `assets/js/module-
registry.js`'s `load()` now pass `{ cache: 'no-store' }` to their
respective `fetch()` calls — forcing a real network read every load.
Both files are metadata-only, small, and already fetched once per
page load; the cost is negligible. No change to any authorization
predicate, no change to `config/landing-groups.json`/`config/module-
registry.json`'s own content, no change to any other module's
visibility.

**Note on RED-before-fix:** a caching-class defect cannot be
demonstrated RED in a fresh Playwright browser context by construction
(a fresh context has no pre-existing stale cache to reproduce against)
— this is disclosed explicitly rather than fabricating a synthetic RED
result. The new permanent test (`tests/painel-analista-fi-landing-
visibility-test.py`, 8/8) instead proves the full ANALISTA/MASTER/
VENDEDOR profile × route/Landing-visibility matrix is correct, both
before and after this fix, guarding the actual authorization logic
against any future regression even though this specific incident's
true cause was the caching gap, not that logic.

## Human UAT required (not yet satisfied)

Refreeze/approval criteria: the Human logs in locally as an ANALISTA or
MASTER homolog user, opens Painel do Analista F&I, and confirms:

A. Current status loads and displays correctly (text + icon).
B. Each of the 5 status buttons (Online/Ocupado/Almoço/Férias/Offline)
   successfully changes status and the panel refreshes to show it.
C. The three summary cards (atendimentos hoje / último atendimento /
   última atualização de status) show sensible values.
D. No horizontal scrollbar at any window width, including a narrow/
   mobile width.
E. The module tile appears under a new "Atendimento F&I" section on the
   Landing page, visible to ANALISTA/MASTER accounts only.

Only after this UAT and an explicit Human approval statement may a
separate, narrow registry action restore `HUMAN_APPROVED`.
