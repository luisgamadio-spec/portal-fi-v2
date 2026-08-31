# PORTAL-NEXT-07.6.3 — Stale-Serve Investigation (Score + Dashbi UAT Rejection #2)

Human visual UAT rejected PORTAL-NEXT-07.6.2 a second time, reporting the
exact same compressed-desktop-table symptoms the 07.6.2 fix was meant to
resolve, via screenshots taken after commit `b4fe4f6`. This document is
the Gate 0/1/29/30 investigation into whether the served application
actually corresponded to that commit — before touching any code again.

## Finding — 7 zombie `http.server` processes on port 8700

```
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object CommandLine -like '*http.server 8700*'
```
returned **14 processes** (7 pairs — each pair a WindowsApps launcher
shim + the real `pythoncore-3.14-64` interpreter it re-exec'd into),
started at 7 distinct timestamps spanning 2026-08-30 14:49 through
2026-08-31 13:47 — one for every time this session started
`python -m http.server 8700` across the whole multi-day engagement,
none of which had ever been stopped. `netstat -ano` confirmed **7 of
them simultaneously in LISTENING state on the same port** — possible on
Windows because Python's `http.server` (via `socketserver.TCPServer`)
sets `allow_reuse_address = True`, which Windows honors for concurrent
binds unlike stricter POSIX `SO_REUSEPORT` semantics elsewhere. Every
new connection could be routed to any one of the 7 by the OS,
nondeterministically, on every reload.

**Why this likely isn't a content-staleness vector by itself**:
`http.server` reads each file fresh from disk on every request — it has
no in-process cache — so even a zombie started days ago would still
serve the CURRENT file content, *provided it was started from the same
correct directory*. The real risk was never confirmed to be "wrong
content served," but the zombie accumulation itself is a genuine
environmental defect (unbounded process/handle growth, unpredictable
which process actually answers) and was corrected regardless, since it
directly blocks the kind of confident "prove what's being served"
verification Gate 0 demands.

**More likely explanation, also addressed**: no response from this
server sends a `Cache-Control` header (confirmed via `curl -I` on
`dashbi.css`) — only `Last-Modified`. Browsers commonly apply
heuristic freshness caching to such responses on a normal reload (not
a hard refresh), which is the exact, previously-confirmed root cause of
an earlier false-alarm bug report in this same engagement
(PORTAL-NEXT-07.3.1 — resolved by a hard refresh, no code change). This
is the leading candidate for what the human's screenshots actually
show: browser-cached CSS from before the 07.6.2 fix landed, not a
defect in the fix itself.

## Remediation applied this Wave

1. All 14 zombie processes killed (`Stop-Process -Force`), confirmed
   via a fresh `netstat -ano` that port 8700 was completely free.
2. Exactly one clean `python -m http.server 8700` restarted from the
   verified-correct directory (`C:\Projetos\PORTAL-FI-DESIGN-LAB`).
   `netstat -ano` re-confirmed a single LISTENING owner.
3. Served-file hash verified byte-identical to the working tree for
   both `dashbi.css` and `score.css` (`curl | sha1sum` vs. `sha1sum` on
   disk) — proves the server is not the source of any discrepancy now.

## Proof the current build (still commit `b4fe4f6`, unchanged) is correct

Re-tested via the real routes (`http://localhost:8700/portal-next-v2/
index.html#/score` and `#/dashbi`), not just fixture HTML or unit
assertions:

- **Computed-style proof** (Gate 11), not just visual: at 390px with a
  Dashbi `+ Detalhes` row open (the exact interaction that caused the
  07.6.2-era bug), `table-layout: auto` (not `fixed`), identity/Receita
  Total cells render at the full available width (332px, `flexBasis:
  100%`, no `min-width`/`max-width` constraint), Vendas/Financiamentos
  render paired (`flexBasis: calc(50% - 8px)`, 158px each). For Score,
  the table's own `display` computes to `block` (not `table`) at this
  breakpoint — it structurally stops being a table at all, the
  strongest possible proof it isn't constrained by desktop column
  geometry.
- **Exhaustive real-route sweep**: all 12 Score fixtures × 5 viewports
  (320/360/390/430/768) — 0 overflow, 0 suspiciously-narrow (<20px)
  cells. All 3 Dashbi views (Grupo/Novos/Seminovos) × 5 viewports ×
  closed/multi-detail-open states — 0 problems. Ranking and Novos por
  Loja at narrow width with detail open — 0 problems. Every one of
  these combinations passed cleanly against the code already committed
  at `b4fe4f6` — no code change was made or needed this Wave.
- **Screenshots** via the real served route (fresh browser context,
  default caching behavior, `networkidle` wait) confirm the visual
  result: full-width labeled records, `+ Detalhes` opening cleanly,
  currency values intact, long names wrapping by word.
- **Regression**: Score 12/12, Dashbi 26/26 (Ranking = Vendedores +
  Lojas, Model Analysis's 4 removed sections still absent), Coparticipado
  22/22, Gestão 30/30, Landing 20/20, foundation 10/10, registry PASS —
  all unchanged, confirming 0 business-logic drift.
- **Keyboard/focus** re-verified on the real route: `+ Detalhes`
  reachable and activatable via keyboard with a visible computed
  outline; Score row same.

## Disposition

**0 code change this Wave** — `git status` shows a clean working tree
(only the pre-existing, unrelated `tests/screenshots/dashbi-wave-0731/`
untracked directory). The committed PORTAL-NEXT-07.6.2 implementation
already satisfies every "true record mode" requirement in this Wave's
own brief, proven by computed style and exhaustive real-route testing,
not assumed. This document itself is the only new file this Wave.

**What's being asked of the human before re-evaluating**: reload with
the browser cache actually cleared (hard refresh / disabled cache, not
a normal reload) against the now-single, clean server — the same advice
already given once before in this engagement for an equivalent false
alarm (PORTAL-NEXT-07.3.1). If the compressed-table appearance
persists after a genuine hard refresh against this cleaned
environment, that would be new, real evidence of an actual remaining
defect — reported here as the honest next step, not silently assumed
resolved.
