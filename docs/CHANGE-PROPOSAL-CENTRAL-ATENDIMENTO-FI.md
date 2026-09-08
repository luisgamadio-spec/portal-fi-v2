# Central de Atendimento F&I — Migration Wave CA-1

**Change ID:** `CENTRAL_ATENDIMENTO_FI_V2_MIGRATION` (module id `central-atendimento-fi`,
registry entry already existed as `NOT_MIGRATED` from AUTH FOUNDATION Phase 2A's
discovery pass — this Wave proves the backend authority live and implements it).

**Date:** 2026-09-07 (CA-1) → 2026-09-08 (CA-1A/CA-1B). **Author:** this session.
**Status:** **HUMAN_APPROVED — FROZEN** (chronology below; see §9).

## 1. Why this exists

AUTH FOUNDATION Phase 2A found a real, live, currently-used V1 surface —
Central de Atendimento F&I, the MASTER-only management counterpart to Painel do
Analista F&I — that had a registry placeholder but no V2 implementation
(`entryPoint: "NOT YET CREATED in V2"`). This Wave (CA-1) was scoped to: (1)
reconstruct the real V1 operational contract from source, (2) prove the RPC/database
authority live and read-only against the real project, (3) prove the auth model,
(4) determine the relationship to the already-migrated Painel do Analista F&I, (5)
implement only if a strict `SAFE_TO_IMPLEMENT` gate held, (6) run regressions, (7)
stop before any Human approval claim.

## 2. V1 authority — frontend (source read, `portal-financiamento-brabus-secure`)

Self-contained IIFE in `index.html:1620-1753` (module id `centralAtendimentoFi`),
gated by `isMaster()` at the entry point AND independently re-checked inside each of
its 3 sub-renders (defense in depth). Three views:

- **Dashboard** (`centralRenderDashboard`) — KPI cards, a "Fila atual" panel (the
  analyst roster, NOT a request backlog — see §3), a "Últimos atendimentos" panel,
  and actions (Atualizar / Encerrar Expediente / Gerenciar Analistas / Ver Histórico).
- **Gestão de Analistas** (`centralRenderAnalistas`) — CRUD form (Nome, CPF,
  WhatsApp, Teams link, Ordem da fila, Ativo) + roster table with per-row actions
  (Editar, Ativar/Inativar, Status, Mover ⬆/⬇).
- **Histórico** (`centralRenderHistorico`) — read-only, client-side-filterable
  (Loja/Vendedor), Excel-exportable attendance log.

**Critical structural finding, confirmed both by source read and live data (§3):**
V1 has **no chamado/ticket lifecycle** exposed to any UI. "Fila" means the analyst
roster's own display/rotation order (`ordem_fila`), not a queue of pending customer
requests. There is no claim/assign/complete/cancel action anywhere in this codebase.
"Falar com um analista" (the simulator button, `assets/js/fi-atendimento.js:21-49` →
`portalCallAnalystFi()` → RPC `chamar_analista_fi()`) is a synchronous "connect me
now" call that opens a WhatsApp deep link to whichever analyst gets picked — not a
persisted, trackable request object the UI ever revisits.

## 3. V1 authority — live database (read-only, this Wave)

Proven via `BEGIN...ROLLBACK`-wrapped queries against the Supabase Management API
(`https://api.supabase.com/v1/projects/yacqlelpzchcotgngwbh/database/query`), the
same guaranteed-zero-permanent-write methodology used by prior Waves (e.g. PM-6D.4).
Zero writes; every statement rolled back.

### Tables (4, not 1 — a real finding beyond what the frontend alone reveals)

| Table | Rows (live) | Purpose |
|---|---|---|
| `analistas_fi` | 11 | The roster. `id, nome, whatsapp, teams_link, status (default 'DISPONIVEL'), ativo, ordem_fila, ultimo_atendimento, criado_em, online, atendimentos_hoje, ocupado, cpf_normalizado, ultimo_status_em, observacao_status`. |
| `atendimentos_fi` | 109 | `id, analista_id, nome_analista, canal (default 'WHATSAPP'), origem (default 'SIMULADOR_FI'), status (default 'ABERTO'), criado_em`. |
| `historico_atendimentos_fi` | 102 | The rich log Central's own Histórico tab reads: `id, criado_em, origem, canal, cpf_vendedor, nome_vendedor, loja_vendedor, analista_id, cpf_analista, nome_analista, status_atendimento (default 'ABERTO'), iniciado_em, finalizado_em, observacao`. |
| `fila_atendimento` | 1 | `id, analista_atual, ultima_atualizacao, observacao` — a singleton pointer shape. **Confirmed fully orphaned: referenced by none of the 9 F&I RPCs, read or write.** Not used by this Wave's implementation. |

**Real, live-data fact, documented not concealed:** every single row in both
`atendimentos_fi` (109/109) and `historico_atendimentos_fi` (102/102) is
permanently `status='ABERTO'` (`finalizado_em` null in all 102 `historico_
atendimentos_fi` rows). No RPC anywhere transitions this status — the schema
clearly intends an ABERTO→finalizado lifecycle (column names, defaults) but V1
never shipped the closing step. Central's Histórico tab renders this reality
as-is (a "Status" column that will read "ABERTO" for every real row today), not
fabricated as "closed" or hidden.

### Access model

All 4 tables have RLS **enabled**. Only **one** policy exists in total
(`analistas_select_authenticated` on `analistas_fi`, `SELECT` for `authenticated`
where `ativo = true`) — and even that is moot in practice, because
`information_schema.table_privileges` confirms **zero direct GRANTs** to
`authenticated`/`anon` on any of the 4 tables. Access is **100% RPC-mediated** —
matching the access posture this Wave's implementation relies on exclusively (no
direct table read/write anywhere in the V2 code).

### RPCs (9 total, all read live via `pg_get_functiondef` — full bodies captured, not inferred)

| RPC | Kind | Identity/authz | Grants (`authenticated`) |
|---|---|---|---|
| `gestor_listar_analistas_fi()` | read | `auth.uid()`→`usuarios.perfil='MASTER'`, else 0 rows | ✅ |
| `gestor_listar_historico_atendimentos_fi()` | read (LIMIT 300, newest first) | same MASTER check | ✅ |
| `gestor_salvar_analista_fi(...)` | write (upsert roster row) | same MASTER check | ✅ |
| `gestor_alterar_status_analista_fi(id, status)` | write (force any analyst's status) | same MASTER check + status enum validation | ✅ |
| `gestor_encerrar_expediente_fi()` | write (bulk OFFLINE) | same MASTER check | ✅ |
| `chamar_analista_fi()` | write (picks + inserts request rows) | none (any authenticated user) — **out of scope, see §6** | ✅ |
| `atualizar_meu_status_analista_fi(status)` | write (self only) | `auth.uid()`→own `usuarios` row, perfil in (ANALISTA, MASTER) | ✅ (Painel do Analista's own RPC) |
| `atualizar_status_analista_fi(cpf, status)` | write | **none at all** — no `auth.uid()` resolution in the body | ❌ not granted to `authenticated` or `anon` — confirmed dead/unreachable via `has_function_privilege`, matches its `MANIFEST.md` classification `INTERNA` |
| `operational_my_analyst_fi()` | read (self) | `auth.uid()`→own row | ✅ (Painel do Analista's own RPC) |

Every client-reachable RPC resolves identity server-side via `auth.uid()`, never a
client-supplied identity, matching this codebase's established house style
(confirmed by direct body read, not assumed by convention this time).

### Known, documented, non-blocking debts found during this proof

- **`chamar_analista_fi` concurrency race (V1 pre-existing, out of scope):** its
  analyst-selection `SELECT ... LIMIT 1` has no `FOR UPDATE`/atomic-claim guard.
  Two simultaneous "Falar com um analista" clicks could select the same analyst
  before either write commits. This is real and confirmed by the SQL body, but
  **Central never calls `chamar_analista_fi`** — it is the simulators' RPC, a
  different caller, already out of this Wave's scope by the brief's own
  instruction not to touch simulator integration. Documented for completeness,
  not fixed (a fix would require a DB migration — explicitly forbidden without a
  separate, explicit authorization).
- **Queue-reorder (⬆/⬇) is not atomic** — two sequential `gestor_salvar_analista_fi`
  calls swap `ordem_fila`. This faithfully mirrors V1's own already-live behavior
  (a MASTER-only, non-safety-critical display-order reshuffle), not a new risk
  introduced by V2.
- **`ordem_fila` is dual-purpose**: manual roster display order (Central's own
  ⬆/⬇) AND the round-robin fairness pointer `chamar_analista_fi` bumps to
  `MAX(ordem_fila)+1` after every call. A MASTER manually reordering the queue can
  therefore affect round-robin fairness — an existing V1 design property, not
  altered here.

## 4. Relationship to Painel do Analista F&I

Both surfaces read/write the same `analistas_fi` table but have a disjoint write
surface: Painel do Analista (`painel-analista-fi.js`, `HUMAN_APPROVED`, commit
`ec12de6`) writes only the caller's own row via `atualizar_meu_status_analista_fi`
(self-service, `ANALISTA_OR_MASTER`). Central writes **any** row via the `gestor_*`
RPCs (`MASTER_ONLY`). Kept as two separate registry entries per the pre-existing
Decision H3 (different role gates, different write scope), as this Wave's own brief
required — no merge attempted.

## 5. SAFE_TO_IMPLEMENT gate — result: TRUE

- ✅ Every RPC this implementation needs already exists, live, correctly
  MASTER-gated server-side. **Zero DB writes, zero migrations, zero RLS/permission
  changes required or made.**
- ✅ `authMode: MASTER_ONLY` already existed in `auth-core.js`'s
  `isModuleAuthorized()` (used by `shell-admin`) — reused as-is, 0 new auth code.
- ✅ No financial/business calculation logic touched (admin/queue-management only).
- ✅ No overlap with Painel do Analista, Score, Coparticipado, Simuladores, or
  their frozen business logic.
- ✅ Persistent sidebar `NAV_GROUPS` (`assets/js/landing.js`) left untouched — same
  pre-existing, documented, non-blocking gap Painel do Analista already carries
  (`ANALYST_PANEL_PERSISTENT_SIDEBAR_NAV_GAP`); Central is reachable via the
  Landing page (`config/landing-groups.json`'s "Atendimento F&I" group), same as
  its sibling.
- ✅ `config/module-registry.json`/`tests/registry-test.py` (PA-1C's own concurrent
  governance work) were re-verified clean (`git diff` empty, HEAD `ec12de6`) both
  before discovery began and immediately before this Wave's own registry edit — no
  collision occurred; **`PARALLEL_FILE_COLLISION_DETECTED` was never triggered.**
- ✅ "Falar com um analista" / simulator integration investigated (§3) but **not
  touched** — out of scope per the brief.

## 6. V2 implementation

New files, following the exact architectural pattern already established by
`painel-analista-fi.js`/`painel-analista-fi-real-provider.js` (thin transport +
non-optimistic state machine, re-fetch after every write, fail closed on any RPC
error):

- `assets/js/adapters/central-atendimento-fi-real-provider.js` —
  `NX_CENTRAL_ATENDIMENTO_FI_REAL_PROVIDER`, wraps the 5 `gestor_*` RPCs. No
  business logic, no formatting.
- `assets/js/central-atendimento-fi.js` — `NX_CENTRAL_ATENDIMENTO_FI_PAGE`, the
  3-tab controller (Dashboard/Gestão de Analistas/Histórico).
- `assets/css/central-atendimento-fi.css` — module-system.css primitives + a
  genuinely separate mobile-card renderer (not a CSS-only table transform), same
  proven pattern Score's own human UAT eventually forced (PORTAL-NEXT-07.6.4).
- Wiring: `index.html` (1 `<link>` + 2 `<script>` tags, additive, placed
  immediately after Painel do Analista's own), `assets/js/shell.js`
  (`MODULE_PAGES['central-atendimento-fi'] = 'NX_CENTRAL_ATENDIMENTO_FI_PAGE'`,
  additive), `config/landing-groups.json` ("Atendimento F&I" group now lists both
  siblings, additive), `config/module-registry.json` (existing entry's
  `entryPoint`/`migrationStatus`/`migrationWave` updated, `migrationCA1Note` added
  — no other module's entry touched).

**Encerrar Expediente** (a bulk, destructive action) uses an in-page confirm panel
(`.caConfirm`, Confirmar/Cancelar), never a native `confirm()`/`alert()` — matching
this codebase's own established convention (`shell-admin.js`'s `pendingConfirm`
pattern), not V1's own (unknown/unverified) confirmation behavior.

**KPI formula disclosure:** the discovery pass captured V1's exact "Disponíveis"
formula (`ativo!==false && status==='ONLINE' && online===true && ocupado===false`,
`index.html:1731`) and "Último atendimento" source (`hist[0]?.criado_em`) verbatim.
The other 6 dashboard KPIs (Online/Ocupados/Almoço/Offline+Férias/Atendimentos
hoje/Analistas ativos) are straightforward, clearly-labeled counts/sums over the
same confirmed real fields — **reconstructed, not verbatim-copied V1 code**, since
V1's own exact dashboard aggregation source for these secondary counts was not
captured this Wave. Nothing here is fabricated business logic; every value is a
plain count of an already-real, already-proven field.

**Focus-preservation fix applied proactively:** the Histórico tab's Loja/Vendedor
filter inputs debounce the *re-render* itself (200ms), not just the filtering —
the same fix already proven in this codebase for the identical defect class
(`shell-admin.js`'s `suBuscaDebounce`/"Pesquisar usuário..." field) — so continuous
typing never triggers a DOM replace that would silently steal focus/caret position.

**A real bug found and fixed during this Wave's own testing (not shipped):** the
first draft of `central-atendimento-fi.css` declared `.caCardList { display: flex;
... }` *after* the `.caMobileOnly` media-query block in source order — at equal
specificity, the later unconditional rule silently won the cascade for the
`display` property at every viewport width (the same "[hidden] loses to an
explicit display" class of bug already documented in `shell.css`), causing the
desktop table and the mobile card renderer to render simultaneously instead of
exactly one at a time. Caught by this Wave's own zero-horizontal-scroll test suite
(§7, not by inspection), fixed by moving `display:flex` into the media query
itself on `.caMobileOnly`, and re-verified.

## 7. Test results (this Wave)

All new suites are non-mutating (routed/mocked fetches only, 0 real Supabase
project touched, 0 credentials anywhere):

| Suite | Result |
|---|---|
| `tests/central-atendimento-fi-test.py` (new — module's own contract, isolated harness) | **64/64 PASS** |
| `tests/central-atendimento-fi-route-test.py` (new — real shell/router/auth-core integration) | **10/10 PASS** |
| `tests/registry-test.py` | PASS |
| `tests/auth-catalog-drift-test.py` | 40/40 PASS |
| `tests/painel-analista-fi-test.py` (sibling regression) | 30/30 PASS |
| `tests/painel-analista-fi-landing-visibility-test.py` (regression, landing-groups.json touched) | 8/8 PASS |
| `tests/master-admin-route-test.py` (regression) | 18/18 PASS |
| `tests/foundation-regression.py` | 11/12 static checks — the 1 failure (Gate 16, 5 findings) is **pre-existing**, confirmed unrelated to any file this Wave touched (2 config files, 1 unrelated commission-engine file, 2 unrelated test-bridge files — none of the 5 flagged lines are in a file this Wave created or edited) |
| `tests/auth-foundation-test.py` | 1 pre-existing failure (`#pUserLogoutBtn` timeout), **confirmed via `git stash` A/B comparison** to reproduce identically against clean HEAD `ec12de6` with 0 CA-1 changes applied — not a regression introduced by this Wave |

Manual browser verification (real shell, real MASTER/VENDEDOR/ANALISTA/signed-out
flows, screenshots taken and visually inspected — `tests/screenshots/ca-1/`):
Dashboard, Gestão de Analistas (desktop + 480px mobile card view), status-change
modal, and Histórico all render correctly with the real V2 design language, 0
console errors. One pre-existing, unrelated cosmetic note: the global
`.nxDevBadge` (fixed-position, dev-only, defined in `shell.css`, present on every
page) can visually overlap page content at the bottom-left corner on long-scrolling
pages — not specific to Central, not introduced by this Wave, not fixed here
(out of scope: a global shell affordance, not this module's own file).

## 8. Human UAT plan (not yet executed)

Focused on the real MASTER workflow, not a mechanical RPC checklist:

1. Open Central de Atendimento F&I as a real MASTER account; confirm the Dashboard
   KPIs match the real roster/history state.
2. Cadastrar a new analyst (Nome/CPF/WhatsApp/Ordem); confirm it appears in the
   roster and (separately, out of this UAT's scope) that a real "Falar com um
   analista" click can reach them once ONLINE.
3. Change an analyst's status via the Status modal; confirm it's reflected
   immediately and matches what Painel do Analista shows for that same analyst.
4. Reorder the queue (⬆/⬇); confirm the display order updates.
5. Encerrar Expediente; confirm the in-page confirm panel, then confirm every
   active analyst is now OFFLINE.
6. Open Histórico, filter by a real Loja/Vendedor, export to Excel, confirm the
   file opens and matches the filtered rows.
7. Confirm a VENDEDOR/ANALISTA account cannot reach `#/central-atendimento-fi`.

**Target state if this UAT is approved:** `CENTRAL_FI_V2_TECH_READY_HUMAN_UAT_
PENDING` → `HUMAN_APPROVED` (with a verbatim quote recorded, same discipline as
every other module in this registry). No approval is claimed by this document.

> **Superseded by §9 below** — the plan above (written at CA-1 completion) included
> mutation steps (Cadastrar, Status change, queue reorder, Encerrar Expediente).
> CA-1A found no safe, reversible, already-established homologation analyst row in
> the real database and narrowed the actually-executed plan to READ-ONLY + EXPORT
> only. This original plan is preserved here as historical record, not deleted —
> §9 records what was actually run and approved.

## 9. Chronology — CA-1A (commit) and CA-1B (Human approval + freeze)

**CA-1A (2026-09-08) — technical freeze + safe UAT preparation.** The CA-1
implementation was reviewed hunk-by-hunk on every shared file touched (`index.html`,
`assets/js/shell.js`, `config/landing-groups.json`, `config/module-registry.json`,
`tests/registry-test.py`) and confirmed in-scope, then committed in one atomic,
explicitly-staged commit: **`a0e7b9b`**, `feat(v2): migrate F&I service center`.
Focused tests held at 64/64 (`central-atendimento-fi-test.py`) and 10/10
(`central-atendimento-fi-route-test.py`) both pre- and post-commit, with zero
regression on every sibling suite (`registry-test.py`, `auth-catalog-drift-test.py`
40/40, `painel-analista-fi-test.py` 30/30, `painel-analista-fi-landing-visibility-
test.py` 8/8, `master-admin-route-test.py` 18/18). Unrelated dirty/untracked work
was preserved byte-identically throughout (no `git add -A`/`clean`/`reset` used).

A dedicated, read-only, live query against the real `analistas_fi` table (11 real
rows) found no test-like CPF pattern and no HOMOLOG/TESTE-named row; the one
pre-existing dedicated homolog identity already in this codebase (a Phase 3A.2
`usuarios`-table account, synthetic CPF) was cross-checked against `analistas_fi`
and confirmed unrelated (zero match). **Classification:
`NO_SAFE_MUTATION_TARGET_PROVEN`.** No homologation row was created. The Human UAT
plan was therefore narrowed, for this approval only, to READ-ONLY + EXPORT actions —
mutation paths remain technically covered by the automated evidence above, not by
Human UAT.

The local gitignored `assets/js/intelligence-runtime-config.local.js` had its
`turnstileSiteKey` temporarily restored (the same established public value already
used for prior local Human UAT waves, not a new value, not a secret) so a real
MASTER could log in locally. No tracked/production config, Cloudflare, Supabase, or
GitHub Pages configuration was touched.

**CA-1B (2026-09-08) — Human approval + final refreeze.** The Human performed the
narrowed READ-ONLY + EXPORT UAT and responded, verbatim: **"validado"**. Scope
actually exercised: real MASTER login, Landing visibility (Atendimento F&I → Central
de Atendimento F&I), opening the module, Dashboard visual/coherence review, Gestão
de Analistas visual/readability review (no analyst created or mutated), Histórico
rendering + a real history filter + Excel export, and a responsive/narrow-layout
qualitative check. `config/module-registry.json`'s `central-atendimento-fi` entry
was promoted `UAT_PENDING` → **`HUMAN_APPROVED`**, with `migrationCA1ANote` and
`humanApprovalNote` fields recording this chronology in full (see that file for the
verbatim registry text — not duplicated here to avoid drift between the two
documents). **FROZEN as of this status**: any future functional change requires a
new Change Proposal + new Human approval, same Freeze rule already applied to every
other approved module in this registry.

The local `turnstileSiteKey` was returned to `null` immediately after this approval
was recorded (§10) — the temporary CA-1A activation is closed.

## 10. Local Turnstile cleanup (CA-1B)

`assets/js/intelligence-runtime-config.local.js` (confirmed gitignored, confirmed
untracked, confirmed local-only) had `turnstileSiteKey` returned from its CA-1A
temporary value back to `null`, restoring the pre-CA-1A inert baseline. No tracked
file, no `intelligence-runtime-config.production.js`, no `.example.js`, no
Cloudflare/Supabase/GitHub Pages configuration was touched by this cleanup.

## 11. Final debt ledger (carried forward, none resolved by CA-1B)

| ID | Priority | Description |
|---|---|---|
| `CENTRAL_CHAMAR_ANALISTA_CONCURRENCY_RACE` | P2 | V1 pre-existing, simulator-side race in `chamar_analista_fi`; requires a separate backend migration, out of scope |
| `CENTRAL_QUEUE_REORDER_NON_ATOMIC` | P3 | Faithfully mirrors V1's own already-live behavior |
| `ANALYST_PANEL_PERSISTENT_SIDEBAR_NAV_GAP` | P2 | Shared with Painel do Analista; Landing remains the approved discovery path |
| `CENTRAL_SECONDARY_KPI_RECONSTRUCTED` | P3 | 6 of 8 dashboard KPIs are reconstructed counts, not verbatim-captured V1 aggregation code |
| `NX_DEV_BADGE_LONG_SCROLL_OVERLAP` | P3 | Pre-existing global shell cosmetic issue, unrelated to this module |
| `ABERTO_FOREVER_ATTENDANCE_DATA_FACT` | P3 (info only) | Real V1 historical records never close; rendered as-is |

None of these were fixed opportunistically during CA-1B — this was a governance-only
refreeze wave.
