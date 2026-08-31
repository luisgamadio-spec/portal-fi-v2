# Dashbi Data Contract (Gates 7-12, 43-44)

## Real architecture (Gate 3-4, proved not presumed)

Unlike Gestão (one single worksheet with row inheritance), Dashbi crosses **three real bases** (Base01 sales, Base02 financing, Base03 FANDI contracts) — closer to Coparticipado's architecture but with its own independent crossing logic, its own independent scoring function, and (unique to this module) a **hard date-cutoff split** between "historical" and "Nova" (new) input formats.

```
Production source:     modules/analise-geral-grupo-secure-original-
                       layout.html (origin/main, blob
                       f29546bc3718e6573ac069b66c8bcc02f227d600 —
                       confirmed local clone DIVERGENT (like Score/
                       Coparticipado), origin/main == live production)
Live boot path:            production's own external adapter (assets/
                          js/analise-geral-grupo-secure-adapter.js)
                          unconditionally overrides window.processar
                          with a Supabase RPC loader
                          (operational_metrics) and calls it on
                          DOMContentLoaded — the functions below are
                          NOT what a live user's browser runs by
                          default. They ARE the real, full business-
                          logic engine reachable via the page's own
                          "MODO TESTE" manual-file path
                          (processarDashboardTesteManualLocal, origin/
                          main lines 5897-5986) — the only path
                          testable with 0 backend calls, and the one
                          that actually contains the classification/
                          crossing/Entrada logic (the secure adapter's
                          metricsToLegacy() only reshapes an already-
                          aggregated, already-classified payload).
```

## The historical/Nova date-cutoff split (Gate 23, confirmed present)

```
CUTOFF DATE:    2026-06-01 (exact, found in 4 independent places:
               adaptarBase01NovaParaFormatoAntigo/adaptarBase02NovaPara
               FormatoAntigo's own d>=2026-06-01 filter, and
               filtrarNovoManualLocalBase01Adaptada/Base02Adaptada's
               own identical filter for the "Local"/test path)
HISTORICAL:        rows with date <= 2026-05-31 (filtrarHistoricoManual
                 Local) — original Base01/Base02 column shapes
NOVA (NEW):           rows with date >= 2026-06-01 — a DIFFERENT column
                    shape, requiring adaptarBase01NovaLocal/
                    adaptarBase02NovaLocal to reshape into the
                    historical shape before entering the SAME
                    processBase01/processBase02 pipeline
BOTH STREAMS ARE CONCATENATED, not chosen exclusively:
                       b1raw = [...b1Hist, ...b1Nova]; b2raw =
                       [...b2Hist, ...b2Nova] (production's own code,
                       byte-identical in the adapter's compute()).
```
This is real, current, must-preserve business logic — not a legacy artifact to clean up. Golden fixture: `date_cutoff_misto` (one historical row at 2026-05-31, one Nova row at exactly 2026-06-01, both included via their respective pipelines).

## Base01 (sales) — historical format

```
KEY COLUMNS:    Transação/Transacao (must be in ALLOWED_SALES=
               {V21,VD,U21} for the row to be VALID; EXCLUDE_TX=
               {V18,V06,U08,U03} and DEV_TX={V07,U07} are tracked but
               do not themselves validate a row), Chassi/CHASSI, Data
               Venda/DATA_VENDA, Nome Vendedor/Vendedor, Modelo/
               DES_MODELO, Valor Venda/VALOR_VENDA
GROUPING:              by chassi; only the CHRONOLOGICALLY LAST
                     relevant row per chassi determines valid/excluded
DEPARTMENT (deptFromBase01):  U21 -> Seminovos; V21/VD -> Novos;
                            fallback via N/U or COD_TIPO_VENDA prefix
```

## Base01 (sales) — Nova format, before adaptarBase01NovaLocal

```
KEY COLUMNS:    Vendedor/VENDEDOR (an NBS code, resolved via
               lookupNbsLocal -> montarMapaVendedoresLocal's own
               NBS_VENDOR_LOOKUP_LOCAL, populated from the "Base de
               Vendedores" upload), Novo/Novo-Usado/NOVO/N-U, Chassi/
               Chassi Completo/Chassi Resumido, Modelo/Desc. Modelo/...,
               Valor Venda/Valor NF/..., Nome Cliente/Cliente/...,
               Data venda/Data Venda/...
ADAPTED SHAPE:          adaptarBase01NovaLocal() reshapes these into the
                      historical column names (Transação, Chassi,
                      Nome Vendedor, etc.) so the SAME processBase01
                      can consume both streams unmodified.
```

## Base02 (financing) — historical format

```
ELIGIBILITY (isFin):    financiado===1 OR desc contains "FINANCIAMENTO"
                       OR valorFin>0 OR receita>0 — AND valorFin>0 is
                       required for the row to actually enter `valid`.
KEY COLUMNS:                FINANCIADO/Financiado, DESCRICAO/Descrição/
                          Tipo, VALOR_FINANCIADO/Valor Financiado/
                          PRODUCAO/Produção, RECEITA/Retorno/
                          VALOR_LIQUIDO, RECEITA_SPF/Receita SPF,
                          NOME_VENDEDOR/Nome Vendedor/Vendedor,
                          DES_MODELO/Modelo/VEICULO, CLIENTE/Cliente,
                          CPF, COD_TIPO_VENDA/N-U/Tipo
DEPARTMENT (deptFromBase02):    U/USADO/SEMI -> Seminovos; N/NOVO ->
                              Novos; fallback via COD_DEPARTAMENTO
                              prefix "2"
```

## Base02 (financing) — Nova format, before adaptarBase02NovaLocal

```
FILTER FIRST:    filtrarDescricaoFinanciamentoBase02Nova — only rows
                whose Descrição Serviço contains "POR PLANO-
                FINANCIAMENTO" or "POR PLANO FINANCIAMENTO" survive.
KEY COLUMNS:         Nome/Vendedor/VENDEDOR (NBS), Novo/Usado/NOVO/N-U,
                   Valor Serviço/..., Retorno Bruto/..., Cliente/Nome
                   Cliente, Desc. Modelo/Modelo, Chassi Resumido/
                   Chassi Completo/Chassi, Data Venda/...
ENTRADA ENRICHMENT:        NOT computed inside adaptarBase02NovaLocal
                        itself — a SEPARATE step, enriquecerEntrada
                        Base02Adaptada(rows, indiceVendasNovas), run
                        AFTER the Base01-Nova chassi index is built.
                        See docs/DASHBI-MODEL-ANALYSIS-CONTRACT.md.
```

## Base03 (FANDI contracts) — no Modalidade filter (real difference from Coparticipado)

```
buildB03Index(rows) indexes EVERY row by client keys — unlike
Coparticipado's buildB3Index, there is NO "Op - Modalidade === FANDI"
filter here. Confirmed by direct source read, not presumed identical
to the sibling module.

KEY COLUMNS:    Cli - Nome/Cliente/..., Cli - CPF/CNPJ/CPF/...,
               Tabela - TC Devolvida (R$)/..., Tabela - Código IF/...,
               Op Fin - Balão PMT (R$)/..., Op Fin - PMT (R$)/...,
               Op Fin - Quantidade Parcelas/..., Op Fin - Financiado
               (R$)/...
```

## Base03 column resolution — positional alias fallback (Gate 43-44, historical risk confirmed real)

```
getTCDevolvidaValue(row):    tries named columns first (Tabela - TC
                            Devolvida (R$) and aliases); if ALL are
                            empty, falls back to row.__COL_E IF
                            row.__HEADER_E looks like a TC-Devolvida
                            header OR row.__COL_E's own value already
                            reads as COPARTICIPADO — i.e. an
                            "anonymized" Base03 export where the real
                            column landed at position E (5th column)
                            without a recognizable header.
getCodigoIFValue(row):           same pattern, position F (6th column),
                                testing for SUBSIDIADO/REVERSAO text or
                                a matching header.
__COL_E/__COL_F/__HEADER_E/__HEADER_F:  populated by production's own
                                       readWorkbookSmart() Excel
                                       reader — since file parsing is
                                       deferred this Wave, fixtures
                                       that want to exercise this path
                                       set these properties directly
                                       on the raw Base03 row object
                                       (see the base03_alias_posicional
                                       fixture).
```
Golden fixture `base03_alias_posicional`: a Base03 row with NO named TC/IF columns, only `__COL_F: "SUBSIDIADO"` — proves the classifier still resolves SUBSIDIADO correctly via the positional fallback. This directly answers Gate 43/44 ("missing required Base03 fields must not silently remap to the wrong column, but must use the SAME resolution production itself defines") — the fallback is production's own, not invented here.

## Crossings

```
Base01 x Base02:    KEY = chassi (Base01's own de-duplication is by
                   chassi with last-by-date wins; Base02 does not
                   itself cross against Base01 in processBase02 --
                   that crossing only happens for Entrada purposes,
                   via buildSalesByChassiForEntry/criarIndiceVendasNovas
                   PorChassi, see MODEL-ANALYSIS-CONTRACT.md).
Base02 x Base03:    KEY = pooled candidates from CPF/CNPJ (exact),
                   full client name, AND up to 3 name "variants"
                   (clientNameVariants: raw normalized, cleaned of
                   LTDA/EIRELI/ME/EPP/SA suffixes, and a 28-char
                   truncation of the cleaned name if >18 chars long --
                   a real, specific truncation-matching heuristic).
                   All candidates are pooled then scored
                   (scoreB03PlanRow) and the highest-scoring one wins
                   (chooseBestB03Row) -- ties broken by ARRAY ORDER
                   (JS Array.sort is stable), NOT by contract date --
                   a genuine, documented difference from Coparticipado's
                   B3 matching, which DOES tiebreak by most-recent
                   date. Not "fixed" to match Coparticipado -- see
                   docs/DASHBI-CROSS-MODULE-CONSISTENCY.md.
NO MATCH:              matchB3-equivalent (matchB3 doesn't exist here;
                     it's inlined in processBase02) returns null/
                     undefined -> planoClassificado defaults to
                     LINEAR, matched:false.
```

## Exclusions (Gate 24, extracted not retyped)

```
EXCLUDED_SELLERS:    the SAME 9-name Set already confirmed shared
                    across Score/Coparticipado/Gestão (LUIS FERNANDO
                    BUENO DE SOUZA, RICARDO SILVA COSTA, SANDRO SEVERO
                    LEROIS, JOAO FONTOLAN, FELIPE ALEXANDRE VITORINO,
                    JEFFERSON CLEMENTE, MARIO ALBERTO DE SOUZA VAZ,
                    FABIANO OKUBO, SERGIO AUGUSTO SEGURA) -- real,
                    cross-module-consistent evidence, confirmed again.
isRevendaRecord:       TWO distinct mechanisms: (1) a hardcoded single-
                     name check (seller === "JAIR BARBOSA" -> true),
                     (2) loja (direct OR resolved via resolveLoja)
                     containing "REVENDA". Both extracted byte-
                     identical.
VENDOR_MAP:                production ships a ~100-entry hardcoded map
                        of real employee names -> real store names.
                        NOT reproduced verbatim in V2 (real PII, and
                        genuinely irrelevant to fixture-based parity --
                        every fixture supplies its own synthetic
                        vendorRows via setVendors(), which populates
                        VENDOR_MAP/NBS_VENDOR_LOOKUP_LOCAL exactly the
                        way montarMapaVendedoresLocal does in
                        production). See docs/DASHBI-FUNCTION-MAP.md.
MISSING SELLER HARD-STOP (Gate 9, real finding):    if ANY non-excluded
                        seller resolves to loja==="NÃO LOCALIZADO" in
                        either Base01 or Base02, production's own
                        processarDashboardTesteManualLocal ABORTS
                        rendering entirely (showSellerValidationError)
                        rather than showing a partial/wrong result.
                        V2's compute() reproduces this exactly:
                        {blocked:true, missingSellers:[...]}.
```
