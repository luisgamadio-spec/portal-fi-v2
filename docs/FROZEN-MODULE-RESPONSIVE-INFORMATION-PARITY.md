# Frozen Module Responsive Information Parity (PORTAL-NEXT-07.6, Gate 41)

For every surface touched this Wave: pre-Wave material information, its
post-Wave location, and whether the underlying value is identical.
Business values were re-verified via the full regression suite (Score
12/12, Coparticipado 22/22, Gestão 30/30 — all still passing after the
CSS/markup changes below), not merely assumed unchanged.

## Landing

| PRE-WAVE INFO | POST-WAVE LOCATION | VALUE PARITY | INTERACTION PARITY | STATUS |
|---|---|---|---|---|
| 5 category labels (Gestão, Novos & Seminovos, Score & Salários, Brabus Intelligence, Auditoria) | Same `.fNavItem` buttons, now wrapping onto multiple lines at ≤768px instead of scrolling sideways | IDENTICAL | IDENTICAL (same click handlers, same active-state logic) | VISIBLE / ACCESSIBLE |
| Module title + description per category | Unchanged (`#landingModuleDetail`) | IDENTICAL | IDENTICAL | VISIBLE / ACCESSIBLE |

## Score

| PRE-WAVE INFO | POST-WAVE LOCATION | VALUE PARITY | INTERACTION PARITY | STATUS |
|---|---|---|---|---|
| #, Vendedor, Loja, Depto, Score (+ meter), Financ. | Same table >480px; vertical label/value stack ≤480px (`data-th`-driven) | IDENTICAL (12/12 fixtures, incl. `long_name`) | Row click → detail panel unchanged (no JS logic touched, only CSS/markup attributes) | VISIBLE / ACCESSIBLE |
| Full vendedor name (previously ellipsis-truncated at narrow widths) | Wraps instead of truncating, at every width | IDENTICAL text, now fully visible instead of "…" | n/a | VISIBLE (improved — was previously ACCESSIBLE-only via title tooltip, now directly VISIBLE) |

## Coparticipado

| PRE-WAVE INFO | POST-WAVE LOCATION | VALUE PARITY | INTERACTION PARITY | STATUS |
|---|---|---|---|---|
| 13 Coparticipados columns (Cliente…Chassi) | Same table >900px (now wrapped/fixed-layout instead of nowrap); full vertical record card ≤900px, every field still shown | IDENTICAL (22/22 fixtures, incl. `nome_longo`, `modelo_sem_taxa`'s "Não encontrado"/"—" warning states) | View-switch tabs (Coparticipados/Subsidiados) and filters untouched | VISIBLE / ACCESSIBLE |
| 11 Subsidiados columns (Cliente…Chassi) | Same | IDENTICAL | Same | VISIBLE / ACCESSIBLE |
| `cpWarn` states ("Não encontrado", "—", "Modelo não encontrado") | Same spans, now able to wrap instead of forcing overflow | IDENTICAL | n/a | VISIBLE |

## Gestão (Análise F&I do Grupo)

| PRE-WAVE INFO | POST-WAVE LOCATION | VALUE PARITY | INTERACTION PARITY | STATUS |
|---|---|---|---|---|
| Financiamentos por Loja (up to 10 cols depending on veículo filter) | Same table >768px; vertical stack ≤768px | IDENTICAL (30/30 fixtures, incl. `store_filter_scope`/`vehicle_filter_scope`) | Filters (Loja/Tipo de veículo/Período) untouched | VISIBLE / ACCESSIBLE |
| Pagos/Faturados/AG.Fat. por Unidade + por Banco | Same | IDENTICAL | n/a | VISIBLE / ACCESSIBLE |
| Planos por Loja/Departamento (Novos 5-type, Seminovos 3-type) | Same | IDENTICAL | n/a | VISIBLE / ACCESSIBLE |
| SPF EXTRA detail (Loja/Departamento/SPF Total/**Comissão Líquida 70%**) | Same | IDENTICAL — 70% formula untouched, `spf_zero`/`spf_100`/`spf_1000`/`spf_12345_67` fixtures all still pass | n/a | VISIBLE / ACCESSIBLE |
| Propostas Recusadas/Aprovadas Válidas por Loja | Same | IDENTICAL | n/a | VISIBLE / ACCESSIBLE |

**Critical expectation met**: material information loss = 0 across all 4
modules. No column was hidden, renamed, or moved behind an unauthorized
new "+ Detalhes" split — every previously-visible field remains directly
visible (wrapped/stacked, never truncated or dropped) at every required
viewport.
