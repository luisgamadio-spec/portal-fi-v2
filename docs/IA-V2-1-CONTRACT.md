# Brabus Intelligence — V2 Module Contract (IA-V2-1)

Fixture-driven module shell, contract adapter, and structured-block
renderer for the Brabus F&I Intelligence module inside Portal V2.
**Zero real backend, zero real auth, zero network calls, zero Voice,
zero Realtime this Wave.** For the full integration architecture
decision this Wave implements, see the (separately delivered)
IA-V2-PLAN-01 report; this document covers only what actually shipped.

## Module route

Real, working route: **`#/brabus-intelligence`** (the module registry
`id`). The registry's own `route` field (`/intelligence`) is
descriptive metadata only — it is never read by the router or shell;
every module in this app is actually addressed by its registry `id`
(confirmed true for all 9 other modules too), not by that field. This
is a pre-existing repo characteristic, not something this Wave
introduced or changed.

Page controller: `assets/js/brabus-intelligence.js`
(`window.NX_BRABUS_INTELLIGENCE_PAGE`, `render(outlet)`). Shell wiring:
`assets/js/shell.js`'s `MODULE_PAGES` map.

## Fixture-only boundary

`assets/js/adapters/brabus-intelligence.adapter.js`'s
`resolveFixtureScenario(message)` stands in for a real `fetch()` to
`portal-ai-homolog`. It is the **only** function IA-V2-2 will need to
replace — the page controller and renderer already speak the exact
response shape a real call would return, and never change.

0 network calls are made by any Intelligence interaction —
proven live in `tests/intelligence-browser-test.py`. (A single
pre-existing, route-independent `fetch(null)` call — confirmed also
present on the already-shipped `#/score` route with the identical
timing, unrelated to this Wave — is excluded from that count; see the
test's own comment for how it was isolated and confirmed pre-existing.)

## Request contract

```js
{
  message: string,
  conversation: [{role, content}]   // last 8 prior turns only
}
```

Structured `blocks` are never resent (mirrors the real frontend's own
`baiSend`, which intentionally strips them before resending history).

## Response contract

```js
{
  reply: string,
  blocks: Block[] | null,   // one of 6 types, see below
  request_id: string | null,
  scenario_reset: boolean
}
```

`_homolog_debug` (present on the real homolog-only response) is
stripped by `normalizeResponse` and never reaches presentation. A
block whose `type` isn't one of the 6 recognized values is silently
dropped, matching the real backend's own defense-in-depth discipline
(a malformed block never breaks the reply text).

## The 6 structured block types

Recovered from the real `portal-ai-homolog` source's own
`buildBlockFromToolResult` dispatch table — every one of the 12 real
tools composes its output from only these 6 shapes, never a
per-tool-specific one:

| Type | Shape | V2 renderer |
|---|---|---|
| `metrics` | `{title, period_label, items:[{key,label,value,format}]}` | `.modPanelResult` + KPI grid |
| `comparison` | `{title, a:{label,period_label,items}, b:{...}, deltas}` | side-by-side panels |
| `ranking` | `{title, dimension, metric, items}` | `.modTable` |
| `operations` | `{title, items}` | analytical list |
| `score_breakdown` | `{title, period_label, items}` | KPI grid (never calls `score.adapter.js`) |
| `score_ranking` | `{title, items}` | `.modTable` |

`renderStructuredBlock(block)` in `assets/js/brabus-intelligence.js`
dispatches on `block.type` — presentation only, see "Forbidden" below.

## Format contract — the one regression this exists to prevent

`formatValue(value, format)` ports `baiFormatValue`'s exact behavior:

- **`percent` values are already percentage points** (e.g. Cash
  Conversion's official rate arrives as `1.12`, meaning "1.12%") —
  this formatter never multiplies or divides by 100. This is the
  **opposite** convention from this repo's own `NX_SIM_UI.pct1/pct2`
  helpers (which format a raw fraction from V2's local calculators and
  DO multiply by 100) — the two must never be used interchangeably.
- `currency`: pt-BR BRL, values ≥ R$1M compact to "R$ X mi" with the
  full value in a tooltip (`title`).
- `date`: `YYYY-MM-DD → DD/MM/YYYY`; anything else → `—`.
- `int`: plain pt-BR grouped integer.
- `text` (this Wave's own addition, not present in the real
  `baiFormatValue` — needed for the Operations block's free-text item
  values, not independently re-verified against the real backend's
  exact operations field shape): renders the string verbatim.
- `null`/`undefined`/non-finite → `—`, never `NaN`/`undefined`/`[object Object]`.

## Conversation state

Lives entirely in `brabus-intelligence.js`'s own closure, **reset on
every `render()` call** — matching every other V2 module's lifecycle
(none preserves state across a route re-entry). Persistence
(`localStorage`/`sessionStorage`) is deliberately **not** implemented —
that would be a new product decision this Wave does not make.

## Novo Cliente / Nova conversa

Two distinct mechanisms, both ported:

1. **"Nova conversa" button** — pure client-side, clears the
   conversation array, no backend involvement.
2. **`scenario_reset: true` in a response** (the fixture's
   `scenario-reset` scenario simulates the model calling
   `iniciar_novo_cliente`) — the conversation is pruned back to just
   the triggering user turn before the reply is appended, exactly
   mirroring the real frontend's own reset splice.

## Errors

| Status | Message shown |
|---|---|
| 401 | Sessão expirada — entre novamente. |
| 403 | Este recurso não está disponível para o seu perfil. |
| upstream/unknown | Não foi possível concluir a análise agora. Tente novamente. |

No stack trace, ever — verified live (`tests/intelligence-browser-test.py`).

## Source-of-truth boundary

`tests/business-logic-scanner.py` forbids `CASH_CONVERSION_APPLICATION_RATE`,
`BALAO_MAX_COUNT`, a `SYSTEM_PROMPT` constant, and a `TOOLS` registry
array **everywhere in V2, with no scoped exception — including inside
this module's own adapter/page files.** Every fixture value in the
adapter is a plain data literal, never derived from a formula
(`tests/intelligence-presentation-parity-test.py` also asserts the
renderer source contains no `Math.pow`/`Math.round`).

## Test suite

- `tests/intelligence-contract-test.py` — adapter contract (request
  shape, history-8, blocks-not-resent, response normalization, all 6
  block types, format functions, all 17 fixture scenarios).
- `tests/intelligence-presentation-parity-test.py` — payload → adapter
  → renderer value preservation for every block type, including the
  two named regression-sensitive cases (Cash Conversion 1.12%,
  Antecipação's assumed date).
- `tests/intelligence-browser-test.py` — real browser: module
  registration, full conversation flow through the actual UI, 0
  network calls, responsive (7 breakpoints), accessibility smoke,
  Landing/other-module regression, screenshots
  (`tests/screenshots/ia-v2-1/`).

The first two are wired into `tests/foundation-regression.py`; the
browser test is run separately, matching this repo's existing
convention (real-browser concerns are not re-implemented as a static
DOM simulation — see `foundation-regression.py`'s own header comment).

## IA-V2-2 prerequisites (recorded, not solved here)

- Real V2 auth — `assets/js/auth-boundary.js` (`NX_AUTH`) is currently
  a contract-only stub; every method throws. Must reuse V1's real
  Supabase Auth flow, never invent a parallel one.
- CORS allowlist update on the 3 real Edge Functions
  (`portal-ai-homolog`/`portal-voice-homolog`/`portal-realtime-homolog`)
  for V2's eventual real origin.
- A feature-containment/kill-switch equivalent for V2 (the real
  backend's `aiAssistantEnabled`/`IA-PROD-CONTAINMENT-01` pattern has
  no V2-side counterpart yet).
- Histórico's RPC-backed data needs live-runtime validation before
  being trusted in production (only structurally verified upstream).

Voice Orb variant and the CSP `media-src` prerequisite remain open but
only block the later Voice Wave (IA-V2-4), not IA-V2-2.
