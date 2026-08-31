# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.4)

**Technical status: TECHNICALLY GREEN** (26/26 golden-fixture parity — unchanged from 07.3 — 0 console/page errors, 0 backend network calls, 0 horizontal scrollbar anywhere in Dashbi at all 6 required viewports, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). 07.3's business content (all restored metrics) is unchanged — only *how* wide tables present changed.

## Se um controle parecer não estar funcionando

Antes de reportar como bug: dê um **hard refresh** (Ctrl+Shift+R). Na rodada
anterior, o botão "Análise por Modelos" pareceu não abrir — depois de um hard
refresh funcionou normalmente. A causa foi um arquivo antigo (`dashbi.js`/
`dashbi.css`) ainda em cache no navegador, não um problema de código. Isso não
significa que bugs reais devam ser ignorados — só elimina cache local como
primeira suspeita antes de investigar mais a fundo.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open (hard refresh recommended after any update): **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## O que mudou desde a rodada anterior

Você rejeitou a tabela larga da Análise por Modelos da rodada 07.3 — ela precisava
de rolagem lateral em qualquer tamanho de tela, até em telas grandes. Você definiu
uma regra nova para todo o Portal V2: **nenhuma informação relevante pode exigir
rolagem lateral**. Refizemos a Análise por Modelos (e toda tabela do Dashbi que
também tinha esse problema) usando um padrão novo: **uma linha principal compacta
por modelo, comparável lado a lado, mais um botão "+ Detalhes" que abre um painel
vertical logo abaixo daquele modelo** com todas as métricas avançadas. Nenhuma
métrica foi removida — tudo que estava na tabela larga continua acessível, a um
clique de distância.

## 8 passos

1. Abra **Novos → Análise por Modelos**. Confirme que **não há barra de rolagem lateral** em nenhum lugar da tela.
2. Compare os modelos pela linha principal (Volume, Financiamentos, Penetração — e, em telas largas, também Produção/Receita Total/Ticket Médio/Retorno Médio).
3. Clique em **"+ Detalhes"** de um modelo — confirme que um painel abre logo abaixo daquele modelo, com Financeiro, Retorno, **Parcelamento (Prazo Médio, Parcela Média)**, **Entrada** e **Planos (Qtd Linear/Balão/Reversão, Balão Médio)**.
4. Sem fechar o primeiro, clique em **"+ Detalhes"** de um SEGUNDO modelo. Confirme que os dois ficam abertos ao mesmo tempo e dá para comparar os dois lado a lado.
5. Clique em **"− Detalhes"** de um dos dois — confirme que só aquele fecha, o outro continua aberto.
6. Troque de família de veículo (Outlander/Triton/Eclipse Cross) — confirme que os detalhes fecham e a tela volta ao estado compacto.
7. Role até as tabelas de plano (Resumo/Modelo/Loja) — confirme que também usam "+ Detalhes" e não têm rolagem lateral.
8. Volte para **Ranking** e **Novos por Loja** — confirme que também não têm rolagem lateral e que os números continuam os mesmos de antes.

Teste a fixture "model_analysis_parcelamento_completo" (seletor "DADOS DE TESTE") para ver Prazo Médio/Parcela Média/Balão Médio com valores reais.

Não é necessário revisar código.

## As três perguntas principais

**"Agora a Análise por Modelos ficou fácil de comparar sem nenhuma barra de rolagem lateral, mantendo todas as informações através do + Detalhes?"**

**"O + Detalhes permite encontrar rapidamente Prazo Médio, Parcela Média, Balão Médio, Entrada e as demais métricas sem deixar a tabela principal carregada demais?"**

**"Deixar dois ou mais modelos com os detalhes abertos ao mesmo tempo ajuda na comparação ou torna a tela visualmente pesada?"** (esta é especificamente uma pergunta de preferência — se a resposta for "pesada", podemos limitar a um modelo aberto por vez numa próxima rodada)

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais.
- Nenhum número já homologado mudou — Vendas/Financiamentos/Produção/Receita/Entrada/Ranking/Novos por Loja calculam exatamente igual à rodada anterior. Só a apresentação das tabelas largas mudou.
- Essa mesma regra de "sem rolagem lateral" **ainda não foi aplicada** aos módulos já aprovados (Landing, Score, Coparticipado, Análise F&I) — eles continuam como estavam, sem nenhuma mudança nesta rodada. Encontramos rolagem lateral em pelo menos uma tela de cada um deles e documentamos isso, mas não mexemos neles — são módulos já aprovados e travados, e só devem ser ajustados numa fase futura, com sua autorização explícita.
- A tabela não é clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
