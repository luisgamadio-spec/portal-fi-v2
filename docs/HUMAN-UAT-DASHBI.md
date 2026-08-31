# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.3)

**Technical status: TECHNICALLY GREEN** (26/26 golden-fixture parity — 25 unchanged + 1 new — 0 console/page errors, 0 backend network calls, 0 page-level horizontal overflow at 6 breakpoints, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). PORTAL-NEXT-07.2's selective navigation is unchanged — this round only restores columns/metrics inside the Análise por Modelos panel.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## O que mudou desde a rodada anterior

Você identificou que a Análise por Modelos estava sem colunas/métricas que existem no Portal atual — citou Balão Médio e Parcela Média como exemplos, mas avisou que não era a lista completa. Fizemos um levantamento completo (produção × V2, coluna por coluna) antes de mudar qualquer código, e restauramos tudo que estava faltando: um bloco de indicadores por família (13 métricas, novo), 8 colunas por modelo que não apareciam (Receita, Receita SPF, Prazo Médio, Parcela Média, Qtd Linear, Qtd Balão, Qtd Reversão, Balão Médio), e 4 tabelas de plano que não existiam (resumo da família, por loja, detalhe Coparticipado/Subsidiado/Reversão, e Inconsistências TRITON quando aplicável).

**Uma decisão de apresentação que pedimos para você revisar especificamente**: o Portal atual mostra só 3 indicadores por modelo por padrão (Volume/Financiada/Penetração), com os outros 15 escondidos atrás de um botão "Ver Detalhes" que abre um modal — isso porque 18 colunas não cabem em nenhuma tela sem rolagem. A V2 **não replicou esse modal** — em vez disso, todas as 18 colunas ficam numa única tabela larga, com a coluna Modelo fixa e rolagem horizontal, agrupada por Volume/Financeiro/Retorno/Parcelamento/Entrada/Planos. Nenhuma métrica foi escondida atrás de cliques extras, mas a experiência de navegação é diferente da atual.

## 6 passos

1. Abra **Novos → Análise por Modelos**. Confirme o novo bloco de indicadores da família (Volume vendido, Financiamentos, Penetração, Produção, Receita, Receita SPF, Receita Total, Ticket médio, Média de retorno, Prazo médio, Média de parcela, Entrada média, % Entrada médio) logo abaixo do seletor de veículos.
2. Role a tabela "Indicadores por modelo" na horizontal. Confirme que agora aparecem TODAS as colunas: Volume, Financiamentos, Penetração, Produção, Receita, Receita SPF, Receita Total, Ticket Médio, Retorno Médio, **Prazo Médio**, **Parcela Média**, Entrada Qtd, Entrada Média, Entrada %, **Qtd Linear**, **Qtd Balão**, **Qtd Reversão**, **Balão Médio**.
3. Teste a fixture "model_analysis_parcelamento_completo" (seletor "DADOS DE TESTE") — ela tem dados reais de PMT, Quantidade de Parcelas e Balão PMT espalhados em 2 modelos (OUTLANDER HPE-S e OUTLANDER SIGNATURE), então Prazo Médio/Parcela Média/Balão Médio aparecem com valores diferentes de zero.
4. Confirme as 4 tabelas de plano abaixo: "Resumo tipos de plano" (1 linha, total da família, com percentuais), "Quantidade por tipo de plano / Modelo" (com percentuais, não só contagem), "Quantidade por tipo de plano / Loja" (nova), "Detalhe Coparticipado / Subsidiado / Reversão" (nova).
5. Teste a fixture "modelo_inconsistencia_triton" para ver a tabela condicional "Inconsistências TRITON" aparecer (ela só existe quando há dado real).
6. Confirme que Ranking e Novos por Loja continuam exatamente como na rodada anterior — nenhuma mudança nesses dois.

Não é necessário revisar código.

## As duas perguntas principais

**"Agora a Análise por Modelos da V2 possui todas as colunas e métricas que existem no Portal atual, sem perder a organização Red Precision?"**

**"As métricas como Parcela Média, Média de Parcelas e Balão Médio estão apresentadas com o significado e a leitura que você esperava?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais.
- **Parcela Média** = valor médio da parcela em R$ (não a quantidade de parcelas).
- **Prazo Médio** já é a "quantidade média de parcelas" — conferimos e a produção real não tem uma métrica separada com esse nome; são a mesma coisa, só que o rótulo em produção é "Prazo Médio" (formatado como "24,0x", por exemplo).
- **Balão Médio** = valor médio do balão, calculado só entre os contratos que realmente têm balão (não dividido pelo total de financiamentos).
- Nenhum número já homologado (Vendas/Financiamentos/Produção/Receita Total/Entrada/Entrada Média/Entrada %, Ranking, Novos por Loja) mudou nesta rodada — só a Análise por Modelos ganhou colunas novas.
- A tabela larga de indicadores por modelo não é clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
