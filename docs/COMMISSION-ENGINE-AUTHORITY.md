# Commission Engine Authority Reconciliation (PM-5I)

Audit-only wave. No UI was built. No real write was executed. This
document is the technical record backing the PM-5I final report;
executable proof lives in `tests/commission-engine-parity-test.py`
(33/33 PASS) against `tests/.source/commission-calc-*.js`.

## 1. Implementation inventory

Exhaustive grep across the entire Authority repo (`portal-financiamento-
brabus-secure`) for `commissionCalc`, `calcularPreviewFechamentoCompetencia`,
`managerCommissionSummary`, `calcGestorFIGrupo`, `FAIXAS_COMISSAO`, and
every other commission-adjacent term listed in the PM-5I brief found
**exactly 2 files**, no third copy anywhere:

| # | File | Role | Runtime | Status |
|---|---|---|---|---|
| 1 | `assets/js/portal-app.js` | V1 production frontend (the real Portal) | Browser | **AUTHORITATIVE** (secure-mode branch only) |
| 2 | `supabase/functions/portal-ai/index.ts` | IA-2C.5/2C.5.1 port, used only to answer chat questions | Deno Edge Function | **DERIVED** (parity-proven) |

`portal-app.js` itself contains **two parallel implementations** gated
by `PORTAL_RUNTIME_CONFIG.authMode`:

- **legacy/XLSX branch** (`calcularPreviewFechamentoCompetencia()`,
  non-secure): reads `DATA.auth`/GitHub-hosted spreadsheets, resolves
  absences via client-side `ausenciaAtivaParaLoja()`/`getAnalystRowsForStore()`,
  reads period dates via `document.getElementById('dtIni').value`
  (real DOM coupling). **Classified STALE_V1_REFERENCE** — not the
  live production path (production runs `authMode==='secure'`,
  confirmed by this same branch check inside `fecharCompetencia()`
  and `calcGestorFIGrupo()` themselves).
- **secure branch** (`calcularPreviewFechamentoCompetenciaSegura()`):
  reads exclusively from 3 real RPCs (`operational_commission_metrics`,
  `operational_analyst_commission_metrics_v2`,
  `operational_salary_manager_directory`), returns `null` (never a
  fabricated zero) if any of the three isn't ready. **This is the
  AUTHORITATIVE implementation** — it is what real production runs.

Both branches call the exact same `commissionCalc(status, m, cls)` —
the pure formula itself is not duplicated, only the population/
aggregation layer differs between legacy and secure.

## 2. V1 closing call graph (secure mode, the live path)

```
Human clicks "Fechar Competência"
  -> fecharCompetencia()                         [portal-app.js:4522]
       -> carregarFechamentosComissao()          [duplicate-close guard]
       -> calcularPreviewFechamentoCompetencia()  [portal-app.js:4849]
            -> (secureMode===true) calcularPreviewFechamentoCompetenciaSegura() [portal-app.js:4890]
                 -> operational_commission_metrics(p_start,p_end)        [RPC, sellers]
                 -> operational_analyst_commission_metrics_v2(p_start,p_end) [RPC, analysts, absence-redistributed server-side]
                 -> operational_salary_manager_directory(p_start,p_end)  [RPC, manager identity/store/department directory]
                 -> gestorFIIdentidadeSegura()    [hardcoded single real user_id lookup, no fallback]
                 -> per VENDEDOR row: commissionCalc(department, m, 'seller')
                 -> per GERENTE bucket (store+department, summed sellers): commissionCalc(status, m, 'manager')
                 -> per ANALISTA row (already redistributed): commissionCalc('ANALISTA', m, 'analyst')
                 -> calcGestorFIGrupo()           [SEPARATE hardcoded formula, portal-app.js:6252]
       -> calcularResumoExecutivoFechamento()     [executive summary cards, independent RPC read]
       -> snapshotRowsPayload(preview, fechamentoId=null)  [portal-app.js:4496 -- builds p_rows]
       -> supabaseClient.rpc('master_close_commission_period', { p_period_id, p_summary, p_rows })
```

## 3. `p_rows` exact schema (from `snapshotRowsPayload`, portal-app.js:4496-4520)

| Field | Type | Origin | Notes |
|---|---|---|---|
| `fechamento_id` | null at call time | literal | server assigns the real id inside the RPC |
| `periodo_id` | uuid/null | `PERIODO_SELECIONADO.id` | |
| `nome_periodo` | text | `PERIODO_SELECIONADO.nome_periodo` or `'Datas manuais'` | |
| `data_inicio`/`data_fim` | date | `PERIODO_SELECIONADO` or raw `#dtIni`/`#dtFim` DOM values | legacy-branch-only DOM read; secure preview always has a real `PERIODO_SELECIONADO` |
| `loja` | text | `l.loja` (row) | |
| `perfil` | text | `l.perfil` (row) | `VENDEDOR`/`GERENTE`/`ANALISTA`/`GESTOR F&I` |
| `nome` | text | `l.nome` (row) | |
| `status` | text | `l.status` (row) | **this field is the row's own department/status label, e.g. "NOVOS"/"GERENTE NOVOS" — it is NEVER the competência's own status; that lives only in `periodos_comissao.status`/`fechamentos_comissao.status`, confirmed by the RPC's own migration comment (PM-5G)** |
| `vendidas`/`financiadas`/`producao`/`retorno` | numeric | `l.m.*` | raw RPC metrics, unrounded |
| `share` | numeric | `l.c.share` or `shareNum(...)` fallback | percentage points (e.g. `50`, not `0.5`) |
| `spf_extra` | numeric | `l.m.spf` | |
| `spf_liquido` | numeric | `l.c.spfLiquido` | `spf_extra * spf_liquido_percentual/100` |
| `rentabilidade_total` | numeric | `l.c.rentTotal` | `retorno + spf_liquido` |
| `faixa` | numeric | `l.c.faixa` | fraction (e.g. `0.15`, not `15`) |
| `comissao_principal` | numeric | `l.c.comissaoPrincipal` | `rentTotal * faixa` |
| `comissao_spf` | numeric | `l.c.comissaoSpf` | analyst bonus only (`spfQty * bonus_spf_analista`); 0 for VENDEDOR/GERENTE |
| `comissao_total` | numeric | `l.comissao` | **VENDEDOR/ANALISTA/GESTOR F&I**: `comissaoPrincipal + comissaoSpf`. **GERENTE**: `comissaoPrincipal` ONLY (deliberate, portal-app.js:4859/4944 — GERENTE never carries an SPF bonus, "comissao" reuses only the principal figure) |

Server-side (`master_close_commission_period`, real SQL read in PM-5G):
`status`(payload) → `snapshot_comissoes.departamento`; `comissao_principal`/
`comissao_spf`/`comissao_total` collapse into `snapshot_comissoes.comissao`
(= `comissao_total`) + `detalhes` jsonb preserving the 3-way split.

## 4. `detalhes` schema (snapshot_comissoes.detalhes, jsonb)

```json
{ "comissao_principal": <numeric>, "comissao_spf": <numeric>, "comissao_total": <numeric> }
```
Confirmed identical shape independently from 3 sources: the real INSERT
statement in `master_close_commission_period` (PM-5G), the real
`SnapshotCommissionRow`/`commissionTotals()` consumer in `portal-ai/
index.ts` (PM-5H), and this wave's own reading of `snapshotRowsPayload`.
Consumed by Histórico's `commissionTotals()`/`checkSnapshotIntegrity()`
(PM-5H, ported verbatim) and by `master_commission_snapshot_export`'s
own fail-closed check (`detalhes IS NULL`).

## 5. Field-by-field algorithm (VENDEDOR / GERENTE / ANALISTA), verbatim from `commissionCalc`

```
share       = vendidas ? (financiadas/vendidas)*100 : 0        // percentage points, zero-denominator guarded
shareMin    = cfg.share_minimo                                  // default 40
spfLiquido  = (spf||0) * (cfg.spf_liquido_percentual/100)        // default 70%
rentTotal   = (retorno||0) + spfLiquido

MANAGER:  faixa = share>=shareMin ? cfg.gerente_faixa_share_alto/100 : cfg.gerente_faixa_share_baixo/100   // 4%/3%
ANALYST:  faixa = share>=shareMin ? cfg.analista_faixa_share_alto/100 : cfg.analista_faixa_share_baixo/100 // 4.5%/3.5%
          comissaoSpf = (spfQty||0) * cfg.bonus_spf_analista                                                // default 150/unidade
SELLER:   isSemi = status.includes('SEMINOVOS') && !status.includes('NOVOS/SEMINOVOS')
          limite = isSemi ? cfg.limite_retorno_seminovos : cfg.limite_retorno_novos                         // 8000/12000
          faixa  = rentTotal < limite
                     ? (share>=shareMin ? cfg.vendedor_faixa_baixo_share_alto/100 : cfg.vendedor_faixa_baixo_share_baixo/100)   // 15%/10%
                     : (share>=shareMin ? cfg.vendedor_faixa_alto_share_alto/100  : cfg.vendedor_faixa_alto_share_baixo/100)    // 20%/15%

comissaoPrincipal = rentTotal * faixa
comissaoTotal     = comissaoPrincipal + comissaoSpf   // comissaoSpf is 0 for seller/manager
```

No internal rounding anywhere in this function — raw IEEE-754 doubles
returned; rounding only ever happens at display time (`fmtMoney`/
`fmtPct2`, both `toLocaleString`/`toFixed`-based) or, in the IA port,
at response-serialization time (`round2`, 2 decimal places) — never
inside the formula itself, and never before persistence (the real
INSERT statement stores the raw computed values unrounded).

## 6. GESTOR F&I — a SEPARATE, non-configurable formula (`calcGestorFIGrupo`, portal-app.js:6252-6284)

**Does not call `commissionCalc` at all.** Two constants are hard-coded
literals, never read from `PORTAL_CONFIG`:

```
share = vendidas ? (financiadas/vendidas)*100 : 0
faixa = share < 40 ? 0.0016 : 0.0030            // 0.16%/0.30%, LITERAL — never cfg.share_minimo
spfLiquido = (spf||0) * (cfg.spf_liquido_percentual/100)   // this one DOES read config
base = (retorno||0) + spfLiquido
comissaoPrincipal = base * faixa
bonusSpf = (spfQty||0) * 30                      // LITERAL R$30/unidade — never cfg.bonus_spf_analista
comissaoFinal = comissaoPrincipal + bonusSpf
```

Population source (secure mode): the *group-level* `totals` object from
`operational_commission_metrics` (the same official, non-duplicated
total the real V1 comment explicitly warns must never be re-derived by
summing individual rows — summing rows across profiles was measured to
overestimate a real competência's total by 4x).

**Identity gate**: `gestorFIIdentidadeSegura()` resolves the Gestor F&I
person via a single **hardcoded real `usuario_id` UUID constant**
(named in a source-code comment together with the real person's full
name — redacted here per this wave's own Gate 42 privacy discipline;
not reproduced in this document or in any test/fixture). No fallback:
if that specific user is ever deactivated or the id no longer resolves,
`calcularPreviewFechamentoCompetenciaSegura()` returns `null` and the
close preview is structurally blocked. This is a real, narrow fragility
inherited by any future V2 port — flagged explicitly, not fixed (out of
scope: this wave changes no formula, no identity resolution).

## 7. Configuration inventory (`operational_portal_config` / `DEFAULT_PORTAL_CONFIG`, all 13 keys are genuinely financial)

| Key | Default | Used by | Effect |
|---|---|---|---|
| `share_minimo` | 40 | seller/manager/analyst faixa branch | threshold, percentage points |
| `spf_liquido_percentual` | 70 | spfLiquido (all profiles incl. Gestor F&I) | percentage |
| `bonus_spf_analista` | 150 | analyst comissaoSpf | R$ per SPF unit |
| `limite_retorno_novos` | 12000 | seller (NOVOS) faixa branch | R$ threshold |
| `limite_retorno_seminovos` | 8000 | seller (SEMINOVOS) faixa branch | R$ threshold |
| `vendedor_faixa_baixo_share_baixo` | 10 | seller faixa | % |
| `vendedor_faixa_baixo_share_alto` | 15 | seller faixa | % |
| `vendedor_faixa_alto_share_baixo` | 15 | seller faixa | % |
| `vendedor_faixa_alto_share_alto` | 20 | seller faixa | % |
| `gerente_faixa_share_baixo` | 3 | manager faixa | % |
| `gerente_faixa_share_alto` | 4 | manager faixa | % |
| `analista_faixa_share_baixo` | 3.5 | analyst faixa | % |
| `analista_faixa_share_alto` | 4.5 | analyst faixa | % |

Confirmed (PM-5G/PM-5H): none of these 13 keys currently has a stored
override row in `configuracoes` — production runs 100% on these
defaults today. Live overrides are still fetched on every calculation
(never cached indefinitely), consistent with `portal-ai`'s own comment:
"nunca assume que os defaults valem para sempre."

## 8. Temporal / absence / store-change semantics

In **secure mode** (the authoritative, live path), none of this
resolution happens client-side anymore — it has moved server-side:

- `operational_analyst_commission_metrics_v2` already returns
  analyst rows **pre-redistributed** for férias/ausências (confirmed
  by the client comment: "já vem redistribuído... não recalcular
  aqui"). The client/port never touches `ausencias_analistas` directly
  in secure mode.
- Store/department historical attribution is resolved server-side via
  `resolve_store_temporal(usuario_id, data, fallback)` /
  `resolve_department_temporal(usuario_id, data, fallback)` (real SQL
  functions, INVOKER, read in PM-5G) — these are what make
  `mudancas_loja_vendedores` affect historical commission attribution;
  again, no client-side logic reimplements this.
- The **legacy** (STALE) branch DID do this client-side
  (`ausenciaAtivaParaLoja`/`getAnalystRowsForStore`/`overlapRange`), but
  since that branch is not the live path, its exact rules are recorded
  here for completeness only, not as something to port: absences
  overlapping the period cause metric REDISTRIBUTION (subtracted from
  the original analyst's residual, attributed to the substitute for the
  overlapping sub-range) — the same real-world rule, just executed
  server-side today instead of client-side.

**Practical consequence for a future V2 engine**: a V2 port does **not**
need to reimplement absence/store-change temporal logic at all — it
only needs to call the 3 real RPCs and trust their already-resolved
output, exactly like both `portal-app.js` (secure branch) and the IA
port already do.

## 9. V1 × IA-2C.5.1 parity matrix (executable, `tests/commission-engine-parity-test.py`)

33/33 PASS, **exact floating-point equality** (not epsilon-tolerant) on
every field, across:

- All 4 seller faixa quadrants (share × retorno), NOVOS and SEMINOVOS
- The `"NOVOS/SEMINOVOS"` combined-status exclusion (must NOT be treated as SEMINOVOS)
- `share` boundary exactly at 40 and just below it
- `retorno` boundary exactly at the limite and just below it
- Zero vendidas / zero financiadas / zero produção / zero retorno with positive SPF
- Positive SPF, negative retorno, a `spfQty` key entirely absent from the input
- GERENTE at both share tiers and the boundary
- ANALISTA at both share tiers, with and without SPF bonus quantity
- GESTOR F&I (separate formula) at share below/at/above 40, zero, and negative retorno
- Determinism (each case evaluated twice, byte-identical JSON both times)
- Order-independence (evaluation order reversed, no per-row result changes — expected, since the formula is a pure per-row function with no cross-row state)

**Difference found and classified** (Gate 30):
`INTENTIONAL_SCOPE_REDUCTION` — the IA port's `fetchLivePreviewLines`
never calls (or ports) `gestorFIIdentidadeSegura()`; it labels the
Gestor F&I row with the generic string `"Gestor F&I do Grupo"` instead
of the real person's name/CPF, and never blocks its own preview if that
identity can't resolve. This is a deliberate, reasonable choice for a
chat-answering tool (it doesn't need to write an immutable, personally-
attributed financial record) but is **not** acceptable for an actual
official closing snapshot, which must record the same real identity V1
does. Any future V2 port of the *write* path must reinstate the real
identity gate (including its fail-closed `null` behavior) — the IA
port's own version alone is not sufficient authority for that specific
field. No other drift of any kind was found across all 33 cases.

## 10. Portability assessment

`commissionCalc`/`calcGestorFIGrupo` are already pure functions of
`(status, m, cls, config)` (or `(m, config)`) with zero DOM, zero
`window`, zero Supabase, zero side effects — proven by this wave's own
extraction running unmodified in a blank browser page. They can be
extracted into a shared pure module with no behavior change. The
*aggregation* layer (`calcularPreviewFechamentoCompetenciaSegura`) is
also portable in secure mode (3 RPC calls + pure in-memory grouping) —
its only non-trivial dependency is the hardcoded Gestor F&I identity
constant (§6), which is a data dependency, not a technical portability
blocker.

## 11. Authority classification

| Implementation | Classification |
|---|---|
| `portal-app.js`, secure branch (`calcularPreviewFechamentoCompetenciaSegura` + `commissionCalc` + `calcGestorFIGrupo`) | **AUTHORITATIVE** |
| `portal-app.js`, legacy/XLSX branch | STALE (documented, not live) |
| `portal-ai/index.ts` (`liveCommissionCalc` + the Gestor F&I block) | **DERIVED**, parity-proven (33/33), one documented INTENTIONAL_SCOPE_REDUCTION (§9) |

## 12. Decision

**COMMISSION_ENGINE_AUTHORITY_AND_PARITY_RECONCILED.**
**CLOSING_ENGINE_READY_FOR_PM5J** — with two explicit, narrow carry-
overs a future PM-5J must honor, not re-litigate: (a) the Gestor F&I
real-identity gate (§6/§9) must be present and fail-closed in any
write-path implementation; (b) the GERENTE `comissao_total =
comissaoPrincipal` quirk (§3) must be preserved exactly, not "fixed"
into `comissaoPrincipal + comissaoSpf` (which happens to be
mathematically identical only because GERENTE's `comissaoSpf` is
always 0, but the distinction is deliberate in both real sources and
should stay explicit in any port for clarity/auditability).
