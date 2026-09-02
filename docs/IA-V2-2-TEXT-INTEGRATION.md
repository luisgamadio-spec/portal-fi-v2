# Brabus Intelligence — Real TEXT Integration (IA-V2-2)

Real transport added alongside (never replacing) IA-V2-1's fixture
mode. **UAT classification: `DETERMINISTIC_MODEL_BOUNDARY_E2E`** — no
real, paid OpenAI traffic is used anywhere this phase (no safe local
homolog OpenAI credentials were available). Everything downstream of
"which tool got called with which arguments" — auth, CORS, the
security gate, the financial engine, `dispatchTool`, structured-block
builders, the V2 renderer — is 100% real, unmodified source under
test, evaluated via real HTTP over a genuine cross-origin browser
request.

## Architecture

```
Portal V2 UI (approved IA-V2-1 presentation, unchanged)
      │
      ├─ FIXTURE mode (default, unchanged from IA-V2-1)
      │
      └─ REAL_TEXT mode ──► assets/js/auth-boundary.js (real Supabase Auth)
                       │
                       ├─► mock Supabase Auth/REST/RPC (local homolog stand-in
                       │    for a real Supabase project — none available locally)
                       │
                       └─► assets/js/adapters/…adapter.js sendRealText()
                                  │  (genuine cross-origin fetch, real CORS)
                                  ▼
                           portal-ai-homolog (REAL, unmodified source,
                           read directly from the Intelligence authority
                           repository — never copied)
                                  │
                                  ├─► same mock Supabase (its own MASTER
                                  │    gate + financial-tool RPC lookups)
                                  └─► mock OpenAI (DETERMINISTIC_MODEL_BOUNDARY —
                                       see tests/intelligence-v2-text/README.md)
```

Portal V2 is served on **`http://localhost:8080`** for this — not this
repo's usual `:8700` test port — because that origin is *already* in
`portal-ai-homolog`'s own `ALLOWED_ORIGINS` CORS allowlist. Confirmed
live, both directions, before writing a single line of integration
code (Gate 10):

| Origin sent | Real backend's `Access-Control-Allow-Origin` response |
|---|---|
| `http://localhost:8080` | `http://localhost:8080` (allowed) |
| `http://localhost:8700` | *(empty — rejected)* |

**Zero CORS modification was made or needed.** This is the one
finding from IA-V2-PLAN-01/IA-V2-1 ("V2's origin isn't in the
allowlist yet") resolved simply by choosing an already-allowed origin
for local testing, not by touching the Intelligence authority.

## Auth

`assets/js/auth-boundary.js` is no longer a stub — it's a real
implementation of the *exact same contract* the Foundation-phase stub
declared (same method names: `signIn`, `getSession`,
`onAuthStateChange`, `resolveAuthorizedProfile`, `signOut`, plus
`getAccessToken`), reusing V1's real flow verbatim:
`supabaseClient.auth.signInWithPassword({email, password})` and RPC
`usuario_logado_fi()` for role resolution — **never** a client-side
role claim. It only activates when
`NX_INTELLIGENCE_CONFIG.mode === 'real_text'` and both
`supabaseUrl`/`supabasePublishableKey` are configured; otherwise it
still throws the same `NOT_IMPLEMENTED`-shaped error the stub always
did (Gate 8 containment — see below).

**Server remains sovereign.** The client never decides "this person is
MASTER" — it only obtains a session and attempts the TEXT call; the
real backend's own DB-verified gate returns 401 (no/invalid session)
or 403 (authenticated, non-MASTER), and the UI reacts to *that*, not
to any local role guess.

No login **form** exists yet — Shell-wide login UI migration is
explicitly out of scope for IA-V2-2 (Gate 36). This phase's tests
bootstrap a session by calling `NX_AUTH.signIn()` directly (a real
method, just not yet wired to a visible form), exactly matching what a
future login page will eventually call.

## Feature containment (Gate 8)

Committed defaults (`assets/js/intelligence-runtime-config.js`):
`mode: 'fixture'`, `supabaseUrl: null`, `supabasePublishableKey: null`,
`textEndpoint: null` — safe on every host, including a
production-looking one. `assets/js/environment-guard.js`'s own
`NX_ENVIRONMENT.production` flag independently confirms this is never
a production build regardless.

Real transport requires `assets/js/intelligence-runtime-config.local.js`
— **gitignored**, never committed, loaded only when
`location.hostname` is `localhost`/`127.0.0.1` (the exact same
convention the Secure repo already uses for its own
`portal-runtime-config.local.js`). Without that file on a given
machine, `NX_INTELLIGENCE_CONFIG.mode` stays `'fixture'` and the
module behaves exactly as IA-V2-1 shipped it. This is containment by
configuration absence, not by hiding a button — the underlying code
path simply isn't reachable without the file.

## Contract (recovered from source, Gate 3)

**Endpoint**: `POST {textEndpoint}` (in production, this is
`{SUPABASE_URL}/functions/v1/portal-ai-homolog` — see "Local topology
note" below for why this harness splits that into two local origins).

**Headers**: `Content-Type: application/json`, `apikey: <publishable
key>`, `Authorization: Bearer <session.access_token>`.

**Request**: `{ message: string, conversation: [{role, content}] }` —
last 8 prior turns only (unchanged from IA-V2-1 — confirmed compatible
with the real backend, which itself slices to the same window
server-side).

**Response**: `{ reply, blocks, request_id, scenario_reset }` —
`_homolog_debug` (homolog-only field) is present in the real payload
but stripped by `normalizeResponse()` before it ever reaches
presentation, confirmed live (no leak in any screenshot or DOM dump).

**Errors**: 401 → "Sessão expirada — entre novamente."; 403 → "Este
recurso não está disponível para o seu perfil."; anything else → "Não
foi possível concluir a análise agora. Tente novamente." — same
Portuguese copy IA-V2-1 already used for fixture errors, now proven
against real backend status codes too.

### Local topology note

Production would naturally serve Auth/REST/Functions from one Supabase
project origin. This local harness has no real Supabase project to
unify them under, so it uses **two** local mock origins instead: a
mock Auth/REST/RPC server (`:8790`) and the real, unmodified
`portal-ai-homolog` process (`:8801`), both configured independently
in `intelligence-runtime-config.local.js`. This split does **not**
weaken the CORS evidence above — the browser still calls the real
function's real origin directly, cross-origin, exercising its actual
unmodified CORS check for real; it just isn't proxied through
anything that could paper over a real rejection.

## Financial tools — real backend, evidence tier per tool

Every tool below was exercised **live**, through the real UI, over a
real cross-origin call, against the real, unmodified engine — not a
fixture. Values shown are the actual computed output.

| Tool | Evidence | Sample result |
|---|---|---|
| TEXT basic (`consultar_resultado`) | REAL_HOMOLOG_HTTP_VERIFIED | real metrics block |
| Linear (Novos) | REAL_HOMOLOG_HTTP_VERIFIED | R$4.010,97 (120k/30k/36x) |
| Linear (Seminovos) | REAL_HOMOLOG_HTTP_VERIFIED | dispatched + rendered |
| Balão | REAL_HOMOLOG_HTTP_VERIFIED | combined ranking+metrics blocks |
| Coparticipado | REAL_HOMOLOG_HTTP_VERIFIED | L200 Triton block rendered |
| Subsidiado | REAL_HOMOLOG_HTTP_VERIFIED | real ranking table |
| Semestral/Anual | REAL_HOMOLOG_HTTP_VERIFIED | dispatched, real backend authority for feasibility |
| Taxa Implícita | REAL_HOMOLOG_HTTP_VERIFIED | NET 2,6% / CET 2,9% (real bisection solver) |
| Antecipação (explicit date) | REAL_HOMOLOG_HTTP_VERIFIED | real date passthrough |
| Antecipação (default date) | REAL_HOMOLOG_HTTP_VERIFIED | real today+30d default, DD/MM/YYYY |
| Cash Conversion (official) | REAL_HOMOLOG_HTTP_VERIFIED | real 1,12%→1,1% engine computation |
| Cash Conversion (custom-rate request) | REAL_HOMOLOG_HTTP_VERIFIED | real backend guardrail holds 1,1% regardless |
| Multi-turn | REAL_HOMOLOG_HTTP_VERIFIED | 2nd real call succeeds, context sent, no duplicate blocks |
| Novo Cliente / `scenario_reset` | REAL_HOMOLOG_HTTP_VERIFIED | real splice + reset confirmation |
| Negative/ineligible truth | REAL_HOMOLOG_HTTP_VERIFIED | real 50% floor rejection, no fabricated payment |
| **Score** | REAL_HOMOLOG_HTTP_VERIFIED *dispatch/calculation*, **RUNTIME_DATA_DEPENDENT** for real-world trust | real `calcScores()` ran on a 2-row synthetic fixture — mechanically correct, but too thin a sample to represent real seller performance |
| **Histórico** | REAL_HOMOLOG_HTTP_VERIFIED *dispatch*, **RUNTIME_DATA_DEPENDENT** for real-world trust | the real tool's own `sample_quality: "INSUFICIENTE"` safeguard fired correctly on the same thin fixture — proof the real logic ran, not that the sample was adequate |

Score and Histórico both call the same RPC
(`operational_score_coparticipated_data`). A 2-row synthetic fixture
was added specifically so both tools have *something* real to compute
over rather than silently returning empty — this proves the real
dispatch and calculation paths work, but is explicitly **not** claimed
as evidence the tools are ready for real production data volumes;
that requires a real database, out of scope for local homologation.

**Frontend financial recalculation: NONE** anywhere in this phase —
`tests/business-logic-scanner.py` still finds 0 unauthorized patterns
across the whole V2 tree, including the new auth/transport code.

## Security matrix

| Case | Result | Evidence |
|---|---|---|
| No session | 401, safe UX | REAL_HOMOLOG_HTTP_VERIFIED |
| Invalid/garbage token | 401 | REAL_HOMOLOG_HTTP_VERIFIED |
| Authenticated, non-MASTER | 403 | REAL_HOMOLOG_HTTP_VERIFIED |
| Authenticated, MASTER | request reaches the real engine | REAL_HOMOLOG_HTTP_VERIFIED |

All four verified via a genuine HTTP round trip against the real,
unmodified backend (not a structural regex proof, not a mocked
transport layer standing in for the backend itself — only its
Supabase/OpenAI *external* boundaries are mocked).

## Network / secrets

- Fixture mode: 0 network calls (unchanged from IA-V2-1).
- Real mode: exactly 3 allowed targets — `127.0.0.1:8790` (mock
  Supabase), `127.0.0.1:8801` (real backend), plus the page's own
  origin. 0 unexpected targets across the full 38-scenario run.
- Browser **never** calls OpenAI directly — confirmed 0 direct
  `api.openai.com` requests from the browser in every run (only the
  server-side Deno process talks to it, and that's redirected to the
  mock via `fetch-patch.ts`, invisible to the browser entirely).
- 0 secret patterns (`sk-…`, `service_role`, a raw JWT shape) found in
  rendered page source across the full scenario set.

## Visual (Gate 46 freeze respected)

The approved IA-V2-1 clean initial state, structured-block
presentation, error states, and Nova conversa behavior are **all
pixel-for-pixel unchanged** in real_text mode — only the fixture
banner/selector are absent (Gate 34/35). Verified at 1920/1366/1024/768
desktop and 430/390 mobile, 0 horizontal overflow at every breakpoint.
No welcome card, no example-question grid, no suggested-prompt cards,
no "Nenhuma pergunta ainda" reintroduced anywhere.

## Known limitations

- **Score/Histórico**: `RUNTIME_DATA_DEPENDENT` — real dispatch and
  calculation proven, real-world data adequacy not (no real database
  available locally; would need a genuine homolog Supabase project).
- **Real OpenAI orchestration**: `HUMAN_RUNTIME_PENDING` — this
  phase's evidence is `DETERMINISTIC_MODEL_BOUNDARY_E2E`, not
  `REAL_MODEL_E2E`. See `docs/IA-V2-2-HUMAN-TEXT-UAT.md`.
- **Balão placement optimization**: unchanged, still an explicit
  `OPEN_PRODUCT_DECISION`, not a defect (carried forward from
  IA-V2-PLAN-01/IA-UAT-02).
- **Login UI**: no visible sign-in form exists in Portal V2 yet
  (Shell-wide auth migration, explicitly out of scope this phase per
  Gate 36) — this phase's tests call `NX_AUTH.signIn()` programmatically.
- **Voice/Realtime**: untouched, not started, no placeholders added
  (Gate 45).

## Test suite

- `tests/intelligence-v2-text-test.py` — 38 checks against the real
  backend (see table above), 21 screenshots at
  `tests/screenshots/ia-v2-2/`.
- `tests/intelligence-v2-text/` — the harness itself (mock backend +
  Deno bootstrap), see its own `README.md`.
- IA-V2-1's fixture-mode suites (`intelligence-contract-test.py`,
  `intelligence-presentation-parity-test.py`,
  `intelligence-browser-test.py`, `intelligence-visual-qa-test.py`,
  `intelligence-visual-fix-01-test.py`) all re-run unchanged and green
  with the local real-mode config *removed* (both modes cannot be
  tested simultaneously on the same machine, since the local override
  activates on any localhost origin — a real developer would not run
  both at once either).
