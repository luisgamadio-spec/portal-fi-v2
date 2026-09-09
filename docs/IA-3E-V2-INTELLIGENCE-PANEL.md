# Brabus Intelligence — V2 Persistent Panel (IA-3E)

Status: **local implementation, MASTER-only presentation, no real
activation.** `mode` stays whatever the environment's own runtime
config already sets (default `fixture` everywhere except a developer's
own gitignored `.local.js`) — this Wave changes nothing about when the
real backend is called, only what the Text experience looks like and
how its own client state is organized.

## 1. What this Wave found (read before assuming a blank slate)

Two prior waves already exist and are untouched by this one:

- **IA-V2-1** (`docs/IA-V2-1-CONTRACT.md`) — the routed, full-page
  module at `#/brabus-intelligence`
  (`assets/js/brabus-intelligence.js` + its adapter), fixture-driven,
  Human visual-UAT'd.
- **IA-V2-2** (`docs/IA-V2-2-TEXT-INTEGRATION.md`,
  `docs/IA-V2-2-REAL-MODEL-UAT.md`) — the same page's real transport
  (`real_text` mode), proven against the real, unmodified backend and,
  separately, against the real OpenAI API (26 calls, 0 discrepancies,
  `REAL_MODEL_E2E`). A server-authoritative kill switch
  (`ia_texto_habilitada`, `IA-V2-3B`) already gates every request.

**IA-3E does not replace or fork either of these.** The routed page,
its adapter, its 6 structured-block renderers, its Markdown-safety
renderer, and its fixture library are all reused **unmodified** —
`assets/js/intelligence/intelligence-panel.js` calls the exact same
`window.NX_BRABUS_INTELLIGENCE_ADAPTER` and reuses the exact same
`window.NX_BRABUS_INTELLIGENCE_PAGE.renderAssistantProse`/
`renderStructuredBlock` the routed page already exposed for its own
tests. Zero rendering/transport logic was reimplemented.

## 2. What IA-3E actually adds

The brief's own Section 12/62 ask for something the routed, per-route
page structurally cannot be: a persistent, cross-module "operating
intelligence layer," not a destination you navigate to and away from.
Three new files, mounted once by `shell.js`'s `boot()` into
`#nxOverlayRoot` (already existed, already sits outside
`#nxContentOutlet`'s per-route rewrite — the correct mount point, not
invented this Wave):

- `intelligence-state.js` — the explicit TEXT state machine (`CLOSED`,
  `OPEN_IDLE`, `COMPOSING`, `SENDING`, `THINKING`, `STREAMING`,
  `COMPLETE`, `ERROR`, `DISABLED`, `SESSION_EXPIRED`, `FORBIDDEN`) plus
  an inert VOICE-ready enum, and the conversation array itself — living
  in its own module-level closure so it survives route navigation
  (this is the entire mechanism behind conversation persistence; no
  database, no localStorage).
- `intelligence-context.js` — the `CLIENT_CONTEXT_HINTS` provider.
  `setRoute()` is called by `shell.js` on every navigation, for every
  route, without touching any individual (frozen) module's own source.
  `publish()` is a voluntary, allow-listed API nothing in this
  codebase calls yet (see §4 below for why).
- `intelligence-panel.js` — the launcher + drawer UI: MASTER-only
  visibility (real DOM removal, not CSS), the send/apply flow rewired
  onto the explicit state machine, open/close, the context chip.

## 3. Why a floating drawer, not a redesigned route

Desktop: a right-side drawer with **no backdrop** — the nav sidebar
and the module underneath stay fully interactive, so "navigate to
another module while the panel is open" is literally true, not a
visual illusion. Mobile (≤768px): near-full-screen with a backdrop,
matching Section 14's "do not squeeze module + chat side-by-side."
Both reuse `.baiBubble`/`.baiMessage*`/`.baiStructuredRegion`/
`.baiComposer*` from the existing `intelligence.css` — only the
wrapper/chrome classes (`.baiPanel*`, `.baiLauncher*`) are new.

**The routed `#/brabus-intelligence` page is left reachable and
unchanged** (direct links, bookmarks, the existing 6 test suites all
still pass unmodified — §7). The persistent launcher suppresses itself
specifically on that route (`isVisibleNow()`'s route check) — found
necessary live during this Wave's own regression pass: an early build
stacked the launcher on top of the routed page too, which both reads
as a redundant second Intelligence surface and collided with
`intelligence-visual-qa-test.py`'s `.baiComposer` selector (two
elements sharing that content class, by design, for visual
consistency). Fixed by suppressing the launcher whenever
`NX_INTELLIGENCE_CONTEXT`'s own `route` is `brabus-intelligence` — a
route-driven rule (also re-evaluated on context change, not only on
auth change), so it covers a direct hash navigation, not only a
launcher click.

## 4. Context envelope: why it is NOT sent over the wire this Wave

Read directly from source this Wave, not assumed:
`supabase/functions/portal-ai-homolog/index.ts`'s own body-parsing
comment states it plainly — **"só lê message/conversation, nunca
user_id/perfil/loja/departamento vindos do cliente."** The real
backend destructures exactly `message` and `conversation` from the
request body; any third field would be silently ignored, never
enforced, by design (the backend never trusts anything else the client
sends).

Given that, `intelligence-context.js`'s envelope is deliberately
**presentation-only** this Wave: it drives the panel's own context
chip (a human-visible "Contexto: Score · Barra Funda" line) so a human
can *see* what the model isn't automatically told and phrase their own
question accordingly — it is never merged into `createRequest`'s
payload, never read by `sendRealText`. This is a disclosed, deliberate
scope boundary, not a silent no-op: wiring context into the actual
conversation (e.g. as a natural-language preamble the model would
read like any other turn) is a real, separate product decision with
its own tone/length/multi-turn-repetition tradeoffs, better made in a
dedicated future wave coordinated with the backend's own owners than
invented unilaterally here. Section 25's "reconstruct the actual
contract, do not invent it" argued directly against fabricating a new
accepted field the backend does not read.

`publish()` is allow-listed (`activeSection`/`periodStart`/
`periodEnd`/`store`/`department`/`seller`/`model` only) specifically
so a future module integration — or a future wire-format decision —
can never smuggle an authority-shaped field (`perfil`, `isMaster`,
...) through it, even by accident; proven by test (an injected
`perfil` key is silently dropped, §7).

## 5. MASTER-only presentation — real removal, not CSS

`isVisibleNow()` reads only `window.NX_AUTH_CORE`'s own existing,
server-derived, `Object.freeze`'d Auth Context — the same one
`shell.js`'s route guard and `landing.js`'s nav rendering already use,
never localStorage/DOM/a URL param. Non-visible means
`#baiLauncherRoot` does not exist in the document at all
(`element.remove()`, not `display:none`) — proven by test for all 7
real profiles plus `SIGNED_OUT`/`SESSION_EXPIRED`
(§7). `AUTH_NOT_CONFIGURED` (no real Supabase Auth wired on a given
host — this worktree's own current default) is treated as visible,
mirroring `auth-core.js`'s own existing `SEPARATE_AUTHORITY`
convention for every other module.

This is intentionally **stricter** than the routed page's own existing
`SEPARATE_AUTHORITY` authMode (any authenticated user may still
navigate to `#/brabus-intelligence` directly, unchanged — the backend
alone gates it there via 401/403). The persistent launcher applies the
brief's own explicit, new instruction ("do not expose active
Intelligence UI to non-MASTER profiles") without touching that
existing, Human-approved routed-page convention.

## 6. Explicit state machine — mapping to a non-streaming contract

The real backend returns one JSON body, never token deltas.
`SENDING` and `THINKING` are both real, distinct states (SENDING:
request being dispatched; THINKING: awaiting the response) even though
today's contract makes the visible transition between them
synchronous/instant — `STREAMING` exists in the enum and is never
entered by anything in this codebase, so a real future streaming
contract would not require inventing a new state later. `DISABLED`
(503)/`SESSION_EXPIRED` (401)/`FORBIDDEN` (403) are **sticky**:
composer stays disabled, no automatic retry ever, the only way out is
a deliberate human action (`Nova conversa`, or a fresh, independent
send attempt). `ERROR` (429/502/network) is **transient**: the
composer re-enables immediately, so a human can manually retry, per
Section 41's explicit distinction.

## 7. Evidence

- **New**: `tests/intelligence-panel-test.py`, 70/70 — MASTER-only
  matrix (9 rows), text E2E, context updates + navigation persistence
  + no frozen-module regression (Score), routed-page non-duplication,
  503/401/403/429/malformed, long-content containment, 4-breakpoint ×
  2-route responsive/zero-scroll proof (16 checks).
- **Re-run unmodified, zero regression**: `intelligence-browser-test.py`
  (51/51), `intelligence-contract-test.py` (62/62),
  `intelligence-markdown-test.py` (55/55),
  `intelligence-presentation-parity-test.py` (23/23),
  `intelligence-structured-block-test.py` (52/52),
  `intelligence-visual-fix-01-test.py` (49/49) — 292/292 total, run
  against this exact worktree via a temporary directory junction (not
  committed) so their own hardcoded serving path resolved correctly;
  their own screenshot regeneration was discarded (`git restore`)
  before committing, not left as accidental diff noise.
- **`business-logic-scanner.py`**: pre-existing 3 findings, all in
  files this Wave never touched (`git diff --stat` empty for each) —
  not a regression, disclosed as carried/pre-existing.
- **Not run this Wave** (out of scope — no file either depends on):
  `intelligence-kill-switch-test.py` and `intelligence-v2-text-test.py`
  need the external `ia-reconciliation-v2-local` source + a working
  Deno bootstrap; `intelligence-visual-qa-test.py`'s own
  `[data-route='brabus-intelligence']` assertion was found to already
  fail identically on a clean sibling worktree with **zero** IA-3E
  changes present (`portal-next-v2-rh4a`, verified side-by-side this
  Wave) — a pre-existing stale expectation, not something this Wave
  introduced or is positioned to fix.

## 8. Carried debts (unchanged by this Wave)

`CURRENT_SUPABASE_OPENAI_KEY_ENVIRONMENT_BINDING_UNPROVEN`,
`MASTER_RUNTIME_503_ORIGINAL_INCIDENT_INSUFFICIENT_EVIDENCE`,
`HOMOLOG_PLATFORM_VERIFY_JWT_HARDENING_PENDING`,
`RH_OPERATIONAL_SCOPE_SECURE_LINEAGE_NOT_RECONCILED`,
`HISTORICO_AI_PERMISSION_MAPPING_INFERRED` — none touched, none
resolved, none silently marked closed by this Wave.
