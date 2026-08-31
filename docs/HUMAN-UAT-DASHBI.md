# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.5)

**Technical status: TECHNICALLY GREEN** (26/26 golden-fixture parity, 0
console/page errors, 0 backend network calls, 0 horizontal scrollbar
anywhere in Dashbi at all 6 required viewports with detail panels open,
Landing/Score/Coparticipado/Gestão freeze untouched). Esta rodada NÃO
mexe na Análise por Modelos (já finalizada na rodada 07.4.1) — o foco é
Visão Geral, Ranking, Lojas, Vendedores e Novos por Loja.

## O que mudou desde a rodada anterior

Você apontou que, embora a experiência de linha principal + "+
Detalhes" da rodada 07.4 tenha sido bem aprovada, ela escondia
informação importante demais: em "Vendas e Financiamentos por Loja", por
exemplo, Produção e Receita Total só apareciam dentro de "+ Detalhes".
Esta rodada resolve isso em toda a tela:

1. **5 métricas principais agora ficam sempre visíveis, sem clicar em
   nada**: Vendas, Financiamentos, Share, Produção Total e Receita
   Total — em todo lugar onde essa informação existe de verdade
   (Visão Geral, Lojas, Vendedores, Ranking). Métricas de apoio (Receita
   sem SPF, Receita SPF, Retorno Médio) continuam em "+ Detalhes".
2. **Share e Receita Total agora têm destaque visual** nos cartões da
   Visão Geral — Share fica verde/laranja conforme a meta de 40%
   (mesma regra já usada na Análise por Modelos), Receita Total fica
   destacado em azul, em negrito.
3. **Novos por Loja ganhou a coluna Share** (Financiados/Vendidos) —
   Produção/Receita Total não existem para essa leitura específica
   (é uma leitura de mix de planos, não financeira) e por isso não
   foram adicionados ali.
4. **Nas telas pequenas (celular)**, as tabelas que ganharam essas
   colunas extras não viram uma tabela apertada — cada linha se
   reorganiza em um bloco vertical (rótulo em cima, valor embaixo),
   sem nenhuma métrica principal escondida e sem rolagem lateral.

## Se um controle parecer não estar funcionando

Antes de reportar como bug: dê um **hard refresh** (Ctrl+Shift+R). Um
arquivo antigo em cache já causou esse tipo de falso alarme antes — não
significa que bugs reais devam ser ignorados, só elimina cache local
como primeira suspeita.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open (hard refresh recommended after any update): **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## Passos

1. Na **Visão Geral** (view "Grupo"), confirme que os 5 cartões
   principais aparecem lado a lado: Vendas, Financiamentos, Share
   (com destaque verde/laranja), Produção Total, Receita Total (com
   destaque azul em negrito) — sem precisar clicar em nada.
2. Clique em **"+ Detalhes"** abaixo dos cartões e confirme que Receita
   (sem SPF), Receita SPF e Retorno Médio aparecem ali.
3. Em **"Vendas e Financiamentos por Loja"** e **"...por Vendedor"**,
   confirme que Share, Produção Total e Receita Total agora aparecem
   direto na linha principal (não mais escondidos em "+ Detalhes").
4. Troque para **Novos** e abra **Ranking** — confirme que Vendedores,
   Lojas e Departamentos mostram Share e Produção Total na linha
   principal, além de Vendas/Financiamentos/Receita Total que já
   apareciam antes.
5. Abra **Novos por Loja** — confirme que agora existe uma coluna
   Share.
6. Volte para **Análise por Modelos** e confirme que continua
   exatamente como na rodada 07.4.1 (nada deveria ter mudado ali).
7. Reduza a janela do navegador (ou abra no celular) e confirme que
   nenhuma tabela fica com rolagem lateral, e que as 5 métricas
   principais continuam visíveis mesmo na tela pequena (agora em
   blocos verticais, não mais em colunas apertadas).

Não é necessário revisar código.

## As perguntas principais

1. **"Agora as tabelas principais deixam claro de imediato o que
   realmente importa — Vendas, Financiamentos, Share, Produção Total e
   Receita Total — deixando as informações secundárias no + Detalhes?"**
2. **"O destaque visual de Share e Receita Total ajuda a leitura sem
   deixar a tabela colorida ou carregada demais?"**
3. **"Ranking, Lojas, Vendedores e Novos por Loja seguem uma lógica de
   leitura consistente entre si?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais.
- Nenhum número já homologado mudou — Vendas/Financiamentos/Produção/
  Receita/Entrada/Ranking/Novos por Loja calculam exatamente igual à
  rodada anterior (26/26 fixtures, 0 diferença). Só a apresentação
  mudou: quais campos ficam visíveis de imediato vs. atrás de
  "+ Detalhes", e o destaque visual de Share/Receita Total.
- Não existe uma tela separada de "Análise por Departamento" — o
  Ranking já cobre a leitura por Departamento (uma das 3 abas dentro
  dele); nenhuma tela nova foi inventada para isso.
- Produção Total e Receita Total não aparecem em Novos por Loja de
  propósito — essa tabela é sobre mix de planos, não tem essa
  informação na origem, e nada foi inventado para preencher esse
  espaço.
- O destaque azul de Receita Total usa um token de cor (`--color-info`)
  que ainda não tinha esse uso formalizado no Design System — está
  documentado como proposta pendente em
  `docs/DS-CHANGE-PROPOSAL-RECEITA-TOTAL-EMPHASIS-01.md`, não foi
  decidido silenciosamente.
- Essa mesma regra de "sem rolagem lateral" **ainda não foi aplicada**
  aos módulos já aprovados (Landing, Score, Coparticipado, Análise
  F&I) — continuam como estavam, sem nenhuma mudança nesta rodada.
- A tabela não é clicável por coluna para reordenar (mesma limitação já
  registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via
`config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu
automaticamente, mesmo com tudo tecnicamente verde.
