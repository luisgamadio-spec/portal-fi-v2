# Development (Gate 38)

## Run it locally

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open `http://localhost:8700/portal-next-v2/index.html`.

Port **8700** was chosen deliberately to avoid colliding with this
project's other established local-dev ports: **8080** (real Portal /
IA UAT, `portal-financiamento-brabus-secure`) and **8600** (Design
Lab — `design-system-2/`, `facelift-prototype-01/`). Do not open
`index.html` directly via `file://` — `fetch('config/module-
registry.json')` will fail under `file://`'s CORS restrictions; a
static server is required.

## Before starting a Wave

```
python config/pre-wave-check.py
```

## Static test suite

```
python tests/foundation-regression.py
```
Runs: token authority sync, module registry structure, Landing
reference resolution, business-logic scanner, prototype/V1
contamination scanners. Individual scripts can also be run directly
(see their own `--help`-equivalent docstrings).

## Real-browser checks (not part of the static suite)

Run these manually (Playwright, or any WebDriver-capable tool) after
any change to the shell:
- **Console/page errors**: load `index.html`, confirm zero.
- **Routing**: click a nav item, confirm the hash and content update;
  reload, confirm the route survives; open a URL with `#/<id>` cold,
  confirm it resolves.
- **Network**: confirm `window.NX_NETWORK_GUARD.flaggedRequests` stays
  `[]` throughout normal use.
- **Responsive**: 360×800, 390×844, 430×932, 768×1024, 1366×768,
  1920×1080 — confirm zero horizontal overflow at each.
- **Keyboard**: first `Tab` must land on the skip link (not the dev
  badge or any other element) — this was a real bug found and fixed
  during this phase (see `REPORT.md`).

## Local commits

This repo has its own history (`git log` inside `portal-next-v2/`),
separate from `portal-financiamento-brabus-secure`. It has **zero**
remotes — do not add one without an explicit human decision.
