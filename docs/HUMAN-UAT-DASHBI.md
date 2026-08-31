# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.2)

**Technical status: TECHNICALLY GREEN** (25/25 golden-fixture parity — 0 change from PORTAL-NEXT-07.1 — 0 console/page errors, 0 backend network calls, 0 page-level horizontal overflow at 6 breakpoints, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). Not the same thing as approval. PORTAL-NEXT-07.1 confirmed the restored content itself (Análise por Modelos/Ranking/Novos por Loja/vehicle imagery) was correct — this round only changes **how and when** those 3 surfaces appear.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## O que mudou desde a rodada anterior

Você pediu que as análises complementares (Análise por Modelos, Ranking, Novos por Loja) não fiquem todas expandidas ao mesmo tempo — como no Portal anterior, onde só uma aparece por vez. Agora existe um controle compacto logo abaixo das tabelas de Loja/Vendedor, com 4 opções: **Visão Geral · Análise por Modelos · Ranking · Novos por Loja**. Apenas uma fica ativa por vez; as outras não ocupam espaço nenhum na página.

## 7 passos

1. Com **Grupo** selecionado (padrão): confirme que o controle mostra só **Visão Geral** e **Ranking** — Análise por Modelos e Novos por Loja nem aparecem como opção (não é um botão desabilitado, ele simplesmente não existe nessa visão).
2. Clique em **Ranking**: confirme que só o Ranking aparece, nada mais.
3. Alterne para **Novos**: confirme que agora aparecem as 4 opções, e que o Ranking continua selecionado/visível (ele existe nas 3 visões).
4. Clique em **Análise por Modelos**: confirme que Classificação dos Planos + o seletor de veículos + os indicadores por modelo aparecem juntos, e que Ranking desaparece.
5. Clique em **Novos por Loja**: confirme que só essa tabela aparece.
6. Com Novos por Loja ainda selecionado, alterne para **Seminovos**: confirme que a página não fica em branco — ela volta automaticamente para **Visão Geral** (Novos por Loja e Análise por Modelos não existem em Seminovos).
7. Teste a fixture "priority_collision" (seletor "DADOS DE TESTE") para ver os 3 blocos com dado real, e teste o teclado: dê Tab até um dos botões de análise e ative com Enter ou barra de espaço.

Não é necessário revisar código.

## A pergunta principal

**"Agora Ranking, Análise por Modelos e Novos por Loja aparecem apenas quando você os seleciona, como no Portal anterior?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais — sinalizado na própria tela ("DADOS DE TESTE").
- **Nenhum número já homologado mudou** — Vendas/Financiamentos/Produção/Receita/Entrada/Entrada Média/Entrada %, o Ranking (Top 10, ordenação, desempate) e Novos por Loja continuam calculando exatamente igual à rodada anterior. Só a navegação mudou.
- O **Ranking** continua disponível nas 3 visões (Grupo/Novos/Seminovos) — é assim que a produção real se comporta, não uma exclusividade de Novos.
- **Análise por Modelos** e **Novos por Loja** continuam exclusivas de Novos.
- **Classificação dos Planos** agora aparece só dentro de **Análise por Modelos** (não mais como um bloco separado) — é assim que a produção real organiza essa informação (confirmado por leitura direta do código de produção: o bloco de classificação vive dentro da mesma seção de Análise por Modelos).
- Ao trocar de Grupo/Novos/Seminovos, se a análise que você tinha aberto deixar de existir naquela visão, o sistema volta sozinho para Visão Geral — nunca fica com a tela em branco ou travada numa aba que sumiu.
- A fixture "vendedor_nao_localizado_bloqueia" mostra um comportamento real: se um vendedor não está cadastrado, a produção real **interrompe** o processamento inteiro em vez de mostrar um resultado parcial — reproduzido de propósito, não é um erro do V2.
- O selo "FECHAMENTO" continua ao lado dos KPIs principais, visível nas 3 visões.
- A seção "Diagnóstico (dev only)" no rodapé é apenas para verificação técnica.
- A tabela **não é** clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
