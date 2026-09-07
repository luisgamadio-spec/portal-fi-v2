# Human UAT Ledger — Painel Master

Official reconciliation of Human UAT evidence for the Painel Master (V2 admin
panel) capabilities, produced by Wave PM-6A.1 (2026-09-07), following the
technical/implementation reconciliation of Wave PM-6A (same date).

## Methodology

PM-6A found that most capability-level `*_HUMAN_APPROVED_LOCAL` labels
assumed as "known evidence" did not exist as persisted strings anywhere in
either repository, and correctly classified those as `HUMAN_EVIDENCE_NOT_
RECONCILED` rather than inventing approval. PM-6A.1 exists to close the gap
between that finding and reality: **absence of a persisted label proves only
a REGISTRY_GAP, not that the underlying Human UAT never happened.**

This ledger combines two evidence classes:

- **REPO_PERSISTED_EVIDENCE** — strings, commits, or prose already committed
  to either repository (e.g. `config/module-registry.json`'s existing
  `humanApprovalNote`/`migratedScope` text, git commit messages, CSS
  history comments).
- **CONVERSATION_HUMAN_UAT_HISTORY** — factual historical account supplied
  directly by the session coordinator in the PM-6A.1 brief, describing real
  UAT interactions that occurred in prior sessions/waves not otherwise
  persisted as a named label. Per that brief's explicit evidence rule
  (§2), this is treated as authoritative historical fact, not invented.

Where both classes corroborate the same event, provenance is recorded as
**BOTH**.

**Confidence** is assigned per Gate 22 of the brief: an event carrying an
explicit quoted Human sentence ("validado, bem melhor!", "Perfeito chat,
muito bom.", "tudo funcionou", "Testado e aprovado.", "Pendencia resolvida,
vamos ao próximo passo.", "Feito, vamos ao próximo.", "Validado.",
"Utilização validada.", "O PDF já estava funcionando...") = **HIGH**. An
event inferred only because the working sequence moved on, with no quoted
sentence = **MEDIUM at most** — never promoted to HIGH. No event in this
ledger is rated LOW; anything without sufficient evidence is left
`HUMAN_EVIDENCE_NOT_RECONCILED` rather than force-rated.

Status vocabulary (unchanged from PM-6A): `HUMAN_APPROVED_LOCAL` (real,
recorded approval, but against a local/dev/homologation environment, not
verified as a production-data event), `HUMAN_REJECTED` (historical, a real
UAT that failed), `HUMAN_PENDING_FIRST_REAL_EVENT` (structurally cannot be
tested until a real event occurs — e.g. a first real COMPLETE competência
closing — and is not penalized for that), `HUMAN_EVIDENCE_NOT_RECONCILED`
(no evidence located, technical work may still be solid). Per the brief's
Gate 29, `HUMAN_APPROVED` (unqualified, production-grade) is never used in
this ledger unless explicit evidence of a real-production event exists —
none was found or supplied this wave, so every approval below is `_LOCAL`.

**Denominator**: MASTER_REQUIRED_TOP_LEVEL_CAPABILITIES = 13 (unchanged
from PM-6A, independently corroborated by `config/module-registry.json`'s
own `MASTER_V2_TARGET_SURFACE_COUNT=13` and the 13-entry `SECTIONS` array
in `assets/js/shell-admin.js`). Implementation completeness: 13/13 (100%).
Technical homologation: 13/13 TECH_READY (1 carries a non-blocking,
documented 900px responsive debt — see Known Debts).

## Reconstructed Human Ledger — 13 capabilities

| # | Capability | Tech | Human (current) | Provenance | Confidence | Real-Event Status | Debt |
|---|---|---|---|---|---|---|---|
| 1 | Usuários | TECH_READY | **HUMAN_APPROVED_LOCAL** (parent promoted — see below) | BOTH | HIGH | n/a | No dedicated doc pre-PM-6A.1 (now closed by this doc) |
| 2 | Acessos aos Módulos | TECH_READY | **HUMAN_APPROVED_LOCAL** | BOTH | HIGH | n/a | 900px pre-existing render glitch (unrelated, non-blocking) |
| 3 | Pendências Cadastrais | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | HIGH | n/a | none |
| 4 | Auditoria | TECH_READY | **HUMAN_APPROVED_LOCAL** | BOTH | HIGH | n/a | own multi-width test suite spot-checks only 2 widths |
| 5 | Gestão de Bases | TECH_READY | **HUMAN_APPROVED_LOCAL** | BOTH | HIGH | n/a | approval tied to historical commit d647f96, not reconfirmed since |
| 6 | Gestão dos Simuladores | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM | n/a | inferred from dry-run success + sequence progression, no explicit quote |
| 7 | Configurações | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM | n/a | inferred from sequence progression, no explicit quote |
| 8 | Períodos de Comissão | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | HIGH | n/a | none |
| 9 | Férias/Ausências | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | HIGH | n/a | none |
| 10 | Mudança de Loja | TECH_READY | **HUMAN_APPROVED_LOCAL** (post-fix; historical HUMAN_REJECTED preserved) | BOTH | MEDIUM (final approval not quoted verbatim; the reject itself is HIGH/repo-persisted) | n/a | none remaining |
| 11 | Fechamento de Competência | TECH_READY | **MIXED**: UI/local flow = HUMAN_APPROVED_LOCAL (MEDIUM); real production close = separate dimension | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM | **HUMAN_PENDING_FIRST_REAL_EVENT** (real close) | expected, not penalized (Gate 37/59) |
| 12 | Histórico de Competências | TECH_READY | **MIXED** — see Subcapability Matrix (parent/Abrir + PDF/Print + Reabrir approved; RH/DP COMPLETE pending; RH/DP LEGACY export not reconciled) | BOTH | mixed, see below | **HUMAN_PENDING_FIRST_REAL_EVENT** (RHDP COMPLETE) | RHDP COMPLETE has 0 real exercised closings |
| 13 | Utilização dos Simuladores | TECH_READY | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | HIGH | n/a | none |

**Tally** (parents, buckets kept separate per Gate 48 — not blended):
- HUMAN_APPROVED_LOCAL (clean): **11/13**
- MIXED (approved dimension + a legitimately separate HUMAN_PENDING_FIRST_REAL_EVENT dimension, not rounded up): **2/13** (Fechamento de Competência, Histórico de Competências)
- HUMAN_EVIDENCE_NOT_RECONCILED (parent level): **0/13**
- No parent is rounded to 13/13 clean; the 2 MIXED rows are reported honestly, not forced into either bucket (Gate 49).

## Subcapability Matrix

### Histórico de Competências (4)

| Subcapability | Human (current) | Provenance | Confidence | Chronology |
|---|---|---|---|---|
| Abrir Competência | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM | Covered by the original Histórico approval (pre-RH/DP), no explicit quote supplied for this specific action |
| Exportar RH/DP — LEGACY_PARTIAL | **HUMAN_EVIDENCE_NOT_RECONCILED** | — | — | REJECTED (live-detail divergence, 414×410, PM-6B-H1) → architecture changed (PM-6D.1/6D.2/6D.3) → no new approval evidence supplied for the fixed legacy-reconstruction path specifically |
| Exportar RH/DP — COMPLETE | **HUMAN_PENDING_FIRST_REAL_EVENT** | — | — | Cannot be tested until a real COMPLETE closing exists (0 today); not promoted, per explicit brief instruction §17/§59 |
| PDF / Imprimir | **HUMAN_APPROVED_LOCAL** | CONVERSATION_HUMAN_UAT_HISTORY | HIGH | Human: "O PDF já estava funcionando..." (quoted during the RH/DP investigation) — approval provenance = CONVERSATION_HUMAN_UAT_HISTORY; post-approval code-path impact = **UNCHANGED_BY_PM6D** (confirmed technically by PM-6A: `historyPrintRhDp` untouched, PDF/Print regression tests unaffected across PM-6B→PM-6D.3) |
| Reabrir | **HUMAN_APPROVED_LOCAL** | BOTH | HIGH | REJECTED (action missing from list) → FIXED (commit `e8de698`, "fix(v2): show reopen action for real closing rows") → Human: "Validado." |

### Usuários (7)

All 7 (listagem, criação, edição, bloqueio, reativação, reenviar convite,
detalhe) were exercised per the brief's historical account: a homologation
user was created/edited/blocked/reactivated; resend passed; an adversarial
VENDEDOR→MASTER privilege-escalation attempt was correctly denied (a real
security-boundary UAT, not merely a happy-path click-through); the ficha/
detail modal passed (also independently REPO_PERSISTED_EVIDENCE — registry
line 54, PM-4B.4); the row-continuity visual adjustment was validated with
an explicit quote: "validado, bem melhor!"

| Subcapability | Human (current) | Provenance | Confidence |
|---|---|---|---|
| Listagem / row continuity | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | HIGH (explicit quote) |
| Criação | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM (exercised, no distinct quote) |
| Edição | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM |
| Bloqueio | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM |
| Reativação | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM |
| Reenviar convite | HUMAN_APPROVED_LOCAL | CONVERSATION_HUMAN_UAT_HISTORY | MEDIUM ("resend passou") |
| Detalhe | HUMAN_APPROVED_LOCAL | **BOTH** (registry line 54, PM-4B.4 + conversation history) | HIGH |

**Parent promotion decision (§26 of the brief):** since all 7 subcapabilities
were genuinely exercised (not merely implied), the **Usuários parent is
promoted to HUMAN_APPROVED_LOCAL**, superseding PM-6A's narrower
"detail-modal-only" reading. This is not an invention — PM-6A's own finding
was correct given only repo-persisted evidence; this wave adds the
conversation-supplied historical account for the other 6 actions, which
PM-6A's brief did not have access to.

## Historical Reject → Fix → Approve Chronologies (preserved explicitly)

1. **Mudança de Loja**: HUMAN_REJECTED (horizontal overflow/overlap — repo-
   persisted evidence: `assets/css/shell-admin.css:531-579`, comment
   `MASTER_STORE_CHANGE_HUMAN_UAT_FAILED_HORIZONTAL_OVERFLOW`) → FIXED
   (scrollbar + overlap corrected) → HUMAN_APPROVED_LOCAL (post-fix
   acceptance, conversation-supplied, no verbatim quote given).
2. **Reabrir**: HUMAN_REJECTED (reopen action missing from the closings
   list) → FIXED (commit `e8de698`) → HUMAN_APPROVED_LOCAL (Human:
   "Validado.").
3. **RH/DP Export**: HUMAN_REJECTED (live-detail divergence between the
   frozen commission snapshot and current operational detail, 414×410
   vendidas — PM-6B-H1) → architecture changed (PM-6D.1 schema foundation →
   PM-6D.2 atomic freeze-on-close → PM-6D.3 frontend consumption) →
   COMPLETE closings = HUMAN_PENDING_FIRST_REAL_EVENT (0 real COMPLETE
   closings exist; not artificially forced). LEGACY_PARTIAL closings keep
   their pre-existing fail-closed live-reconstruction behavior, unchanged,
   and remain HUMAN_EVIDENCE_NOT_RECONCILED for lack of a specific new
   approval of that exact (fixed) path.
4. **Pendências Cadastrais**: HUMAN_REJECTED (first presentation had
   horizontal overflow) → FIXED → HUMAN_APPROVED_LOCAL (Human: "Perfeito
   chat, muito bom.").

## Pending-First-Real-Event Items (not penalized, not forced)

- **Fechamento de Competência — real production close**: 0 real closings
  ever executed by any wave of this engagement. UI/local flow is human-
  approved; the real mutation itself has never been human-witnessed.
- **Histórico de Competências — Exportar RH/DP, COMPLETE closings**: 0 real
  COMPLETE closings exist (`historical_detail_status='COMPLETE'`). The
  frozen-snapshot architecture (PM-6D.1/6D.2/6D.3) is fully implemented and
  technically proven (73/73 tests, live-independence proven, reimport-
  golden proven) but cannot receive a real Human UAT until the first real
  COMPLETE closing occurs naturally. No real closing was created to force
  this — per explicit brief instruction (§17/§59), this is not attempted.

## Known Debts (unchanged from PM-6A, not resolved this wave)

- `AUTH_RH_SCOPE_CONTRADICTION` — dormant contradiction between
  `portal_modulos_permitidos()` (grants RH the `comissoes` module) and
  `operational_current_scope()` (has no RH branch, raises 42501). Inert
  today because `configuracoes.permissoes_modulos_dinamicas = false`. Not
  resolved this wave (Gate 51 — explicitly out of scope).
- `MASTER_ACESSOS_900PX_PREEXISTING_RENDER_GLITCH` — Acessos aos Módulos'
  9-column matrix collapses at exactly 900px, pre-existing, documented,
  `[INFO, not blocking]`. Not resolved this wave (Gate 52).
- `PUBLIC_DEFAULT_TABLE_ACL_SECURITY_DEBT` — inherited from PM-6D.1, not
  re-verified this wave.
- Two V2 status-ledger documents (`config/module-registry.json` vs
  `docs/MIGRATION-STATUS.md`) were out of sync prior to this wave for
  Painel Master specifically — corrected by this wave (see below), not a
  remaining debt after this commit.

## Real-Write Classification — unchanged by this wave

Per Gate 50 of the brief, Human UI/local UAT approval and real production
write-mutation proof are different dimensions and this wave does not alter
any Real-Write classification established by PM-6A. All V2-frontend-layer
capabilities remain `SIMULATED_WRITE_PROVEN` or `READ_ONLY_PROVEN` (mocked
Playwright RPC-route fixtures); only the Authority-repo RH/DP freeze
mechanics (PM-6D.2) carry `REAL_WRITE_PROVEN` status, via real BEGIN...
ROLLBACK-tested transactions prior to a real, permanent apply. A capability
being `HUMAN_APPROVED_LOCAL` here does NOT imply `REAL_WRITE_PROVEN`.

## Date of reconciliation

2026-09-07 (Wave PM-6A.1, same day as PM-6A).
