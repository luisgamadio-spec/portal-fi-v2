# IA-V2-2 real TEXT integration harness

Drives the REAL, unmodified `portal-ai-homolog` source (read directly
from the Intelligence authority repository, never copied) against the
already-approved Portal V2 UI. Only the Supabase and OpenAI network
boundaries are mocked — see `docs/IA-V2-2-TEXT-INTEGRATION.md` for the
full architecture and why Portal V2 must be served from
`http://localhost:8080` specifically for this (the real function's own
CORS allowlist already includes that origin — no CORS change needed).

## Running it

Four processes, each in its own terminal/background job:

```bash
# 1. Mock Supabase Auth/REST/RPC
node tests/intelligence-v2-text/mock-backend.mjs 8790

# 2. Real portal-ai-homolog (unmodified source, read from the Intelligence repo)
cd tests/intelligence-v2-text/deno
V2_TEXT_PORT=8801 V2_MOCK_BASE=http://127.0.0.1:8790 \
SUPABASE_URL=http://127.0.0.1:8790 SUPABASE_ANON_KEY=v2-anon-key \
SUPABASE_SERVICE_ROLE_KEY=v2-service-key OPENAI_API_KEY=v2-dummy-key \
  npx --yes deno run --allow-net --allow-env --allow-read --import-map=import_map.json bootstrap-text.ts

# 3. Portal V2 itself, on port 8080 specifically (not this repo's usual 8700)
cd ../../..   # back to PORTAL-FI-DESIGN-LAB/
python -m http.server 8080

# 4. Point the frontend at the mock/real backend for this machine
cp portal-next-v2/assets/js/intelligence-runtime-config.example.js \
   portal-next-v2/assets/js/intelligence-runtime-config.local.js
```

Then open `http://localhost:8080/portal-next-v2/index.html#/brabus-intelligence`.

## UAT classification

`DETERMINISTIC_MODEL_BOUNDARY_E2E` — no real, paid OpenAI traffic is
used (no safe local homolog credentials available this phase). The
mock "model" only ever decides which tool to call for a known test
prompt and narrates the real tool's own JSON result back — it never
computes a financial number. Everything downstream (financial engine,
`dispatchTool`, structured-block builders, security gate, CORS) is
100% real, unmodified source under test.

## Files

- `mock-backend.mjs` — Node HTTP server: mocks Supabase Auth/REST/RPC
  (for both the browser's own auth calls and the real backend's
  internal RPC/security-gate calls) and OpenAI (`/openai/*`, reached
  via the fetch patch below).
- `deno/fetch-patch.ts` — monkey-patches `fetch` so the real source's
  OpenAI calls redirect to the mock, without touching the source.
- `deno/shim-http-server.ts` + `deno/import_map.json` — redirects the
  real source's own `std/http/server.ts` import to bind a
  harness-chosen port instead of hardcoded 8000.
- `deno/bootstrap-text.ts` — the one-line loader that applies the
  patch then `import()`s the real, unmodified `index.ts` directly from
  the Intelligence authority repository (read-only).
