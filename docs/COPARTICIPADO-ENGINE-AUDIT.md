# Coparticipado Engine Audit (Gates 5-11)

## Gate 3-4 — Where the experience really lives, and the correct source

```
ENTRY:              modules/coparticipado.html — a full standalone page
                    (same architecture as Score), NOT a tab inside
                    another module.
FILES:                 modules/coparticipado.html (730 lines, origin/main)
                     + assets/js/score-coparticipated-secure-adapter.js
                       (43 lines, shared with Score — RPC-only, not
                       needed this Wave since 0 backend)
ROUTE (V1):              opened via IFRAME_MODULES.coparticipadoPortal
                       from the shell (see PORTAL-NEXT-01/
                       ARCHITECTURE-AUDIT.md Gate 4)
PARENT MODULE:              none — standalone, embedded via iframe like
                          Score
DATA SOURCE:                  3 uploaded Excel bases (Base 01 = vendas,
                          Base 02 = financiamentos/serviços, Base 03 =
                          contratos FANDI) + a vendor registry + a
                          "taxa coparticipado" rate table, all normally
                          parsed client-side from admin-uploaded files
                          (master-gestao-bases.js / master-gestao-
                          simuladores.js) — NOT queried from Supabase
                          directly by this page.
AUTH REQUIREMENT:              session + role scope (same as Score,
                          unchanged this Wave — 0 backend, 0 auth
                          implemented)
```

**Gate 4 — local vs. remote, proved not presumed:**
```
modules/coparticipado.html:                    local 2cdb3e3... != origin/main f729c40...
assets/js/score-coparticipated-secure-adapter.js: local 279a10a... != origin/main 6f2c79b...
```
Both files ARE divergent (unlike some Score files that weren't). Live
production fetch confirms `origin/main == production` for both,
byte-exact. **Everything below is read from `git show origin/main:...`,
not the local clone.**

## Gate 6 — Classification function, exact priority (PROVED, not presumed)

```js
function classifyPlan(b3row){
  if(!b3row) return 'LINEAR';
  const cod=getIF(b3row), ifN=asNumber(cod), ifT=planText(cod),
        balao=asNumber(getCol(b3row,['Op Fin - Balão PMT (R$)','Balão PMT','Balao PMT']));
  if(ifT.includes('SUBSIDIADO')||ifN===999) return 'SUBSIDIADO';
  if(ifT.includes('REVERSAO')||ifN===777) return 'REVERSÃO';
  if(isCoparticipadoValido(b3row)) return 'COPARTICIPADO';
  if(balao>0) return 'BALÃO';
  return 'LINEAR';
}
```
**Priority, confirmed exactly as historically documented — SUBSIDIADO
> REVERSÃO > COPARTICIPADO > BALÃO > LINEAR** (Gate 10 explicitly
warned not to presume this without proof; proved via direct source
read, not memory).

`isCoparticipadoValido(row) = isTCcoparticipado(row) && isSituacaoCoparticipadoValida(row)`
— BOTH conditions required:
```js
function isTCcoparticipado(row){ const tc=getTC(row),tcN=asNumber(tc); return planText(tc).includes('COPARTICIPADO')||tcN===1 }
function isSituacaoCoparticipadoValida(row){ const s=getSituacaoB3(row); return s==='PAGA'||s==='FATURADA' }
```

## Gate 7 — Base 03 fields, audited exactly

```
Op - Modalidade:      filters WHICH Base 03 rows are even eligible —
                     buildB3Index() keeps ONLY rows where
                     normalizeText(getCol(r,['Op - Modalidade','Modalidade']))==='FANDI'.
                     Non-FANDI rows are invisible to matching entirely.
Tabela - Código IF:     999 (or text containing "SUBSIDIADO") -> SUBSIDIADO;
                     777 (or text containing "REVERSAO") -> REVERSÃO.
TC Devolvida:             (Tabela - TC Devolvida (R$)) — text containing
                     "COPARTICIPADO" or numeric value 1 -> the TC-side
                     half of the COPARTICIPADO test.
Op - Situação (PAGA/       PAGA or FATURADA -> the situation-side half of
FATURADA):                the COPARTICIPADO test. Also used for B3
                         candidate scoring (situacaoScoreB3): PAGA/
                         FATURADA=100, ASSINADO=70, ENCERRADA=20,
                         contains "CANCEL"=-40, contains "RECUS"=-60,
                         else 0.
```

## Gate 8 — Crossings, exact keys and fallback behavior

```
Base 01 x Base 02 (processFins matching sales):
  KEY:           chassi (normalized). Tries chassiFull (Chassi
                Completo) first, falls back to chassiResumido
                (Chassi Resumido) if no full match.
  FALLBACK:        if no sale matches by either chassi key, dept/modelo
                are derived independently from the Base 02 row itself
                (deptFin/modeloPadrao) rather than left blank.
  NO SALE MATCH:      valorVenda defaults to 0, dept/modelo derived as above.

Base 02 x Base 03 (matchB3, the fuzzy-match/scoring engine):
  CANDIDATE KEYS (in this order, ALL collected then scored together,
  not first-match-wins): CPF/CNPJ (exact digits), full client name
  (normalized), "clean" name (normalized + LTDA/EIRELI/ME/EPP/S A/SA
  suffixes stripped). Every candidate from every key is pooled, then
  ranked by:
    scoreB3(row) -- SUBSIDIADO/999=100, REVERSAO/777=95,
                    isCoparticipadoValido=90, balao>0=80,
                    isTCcoparticipado=5, else PMT-presence(20)+
                    parcelas-presence(10)
  + situacaoScoreB3(row) -- PAGA/FATURADA=100, ASSINADO=70,
                    ENCERRADA=20, CANCEL*=-40, RECUS*=-60, else 0
  + closenessScoreB3(row,targetValor) -- financed-value proximity:
                    diff<1=80, relDiff<=0.5%=60, <=2%=35, <=5%=15,
                    else -25
  TIEBREAK:          if total scores tie exactly, most recent
                    "Op - Data Contrato"/"Op - Data Inclusão" wins.
  NO MATCH:            matchB3 returns null -> classifyPlan(null) =
                    'LINEAR' (the fallback default).
  DUPLICATE B3 rows:      all candidates are pooled and SCORED, not
                        deduplicated by a rule — the highest-scoring
                        one wins per the formula above, exactly once
                        per fin record (chooseB3 returns a single row).
```

## Gate 9 — Exclusions, extracted exactly (not retyped from memory)

```js
const EXCLUDED_SELLERS = new Set(['LUIS FERNANDO BUENO DE SOUZA','RICARDO SILVA COSTA',
  'SANDRO SEVERO LEROIS','JOAO FONTOLAN','FELIPE ALEXANDRE VITORINO','JEFFERSON CLEMENTE',
  'MARIO ALBERTO DE SOUZA VAZ','FABIANO OKUBO','SERGIO AUGUSTO SEGURA']);
function rowHasExcluded(row){ const joined=Object.values(row||{}).map(normalizeText).join(' | ');
  return [...EXCLUDED_SELLERS].some(n=>joined.includes(n)) }
```
Applied to BOTH `processSales` and `processFins` (any row whose
serialized values contain an excluded seller's name anywhere is
dropped entirely). `processSales` ALSO drops any row where
`Veic. Tipo` contains "REVENDA" — a second, distinct exclusion rule.
**Same list found in `portal-app.js` for Score (PORTAL-NEXT-01's
audit)** — one shared constant reused across modules, confirmed
identical here.

## Gate 11 — Real bug history (not corrected, not reopened)

There is Lab-known history of a Coparticipado operation being
undercounted at some point in the past. **This audit did not look for
or attempt to reproduce that history** — the only question this phase
answers is "what does `origin/main` compute right now," and that
current behavior (traced above, byte-verified) is what gets migrated.
If today's production logic already contains a fix, that fix is what's
inherited automatically by reading the current source; if it doesn't,
this Wave does not add one either (Gate 11's own instruction).

## Full pipeline map (Gate 58 preview — full trace in EXTRACTION-TRACE)

```
Base 01 (raw rows) --processSales()--> DATA.sales[]
Base 02 (raw rows) --+
Base 03 (raw rows) --buildB3Index()--> b3idx {byCpf,byName,byClean}
DATA.sales[] + Base02 rows + b3idx --processFins()--> DATA.fins[]
  (each fin record already carries its final `plano` classification)
DATA.fins[] filtered by plano==='COPARTICIPADO' --calcCoparticipacaoDetalhe()-->
  {ok, rebateTotal, parteBrabus, valorRebateTotal, coparticipacao}
  (needs findTaxaCopart(modelo) against DATA.taxasCopart, a rate table)
```

## Deferred (Gate 57) — not extracted this Wave, and why

```
DEFERRED DEPENDENCY:    raw Base01/02/03 Excel-file PARSING itself
                       (how the uploaded .xlsx rows become the plain
                       JS row objects processSales/processFins/
                       buildB3Index consume)
SOURCE:                    master-gestao-bases.js (admin upload tooling)
REASON:                       Excel parsing is I/O + admin-workflow
                            concerned, not Coparticipado's own
                            classification logic; this Wave's fixtures
                            provide already-parsed plain row objects
                            directly (same shape the real parser would
                            produce), consistent with 0 backend/0 file
                            I/O this Wave.
FUTURE WAVE:                    whichever Wave migrates the MASTER
                              admin upload tooling, not a Coparticipado
                              concern specifically.

DEFERRED DEPENDENCY:    the "taxa coparticipado" rate table's own Excel
                       parsing (rebateTotal/parteBrabus per model)
SOURCE:                    master-gestao-simuladores.js
REASON:                       same as above — this Wave's fixtures
                            provide a pre-built rate table object
                            directly.
FUTURE WAVE:                    same admin-tooling Wave as above.
```
Everything else in the real pipeline — `processSales`, `buildB3Index`,
`processFins`, `matchB3`/`chooseB3`/`scoreB3`/`situacaoScoreB3`/
`closenessScoreB3`, `classifyPlan` and its dependencies, `find
TaxaCopart`, `calcCoparticipacaoDetalhe` — **is extracted byte-
identical**. See `docs/COPARTICIPADO-EXTRACTION-TRACE.md`.
