# Human UAT — Responsive Remediation (PORTAL-NEXT-07.6)

**Escopo desta rodada: SOMENTE apresentação responsiva.** Landing, Score,
Coparticipado e Análise F&I do Grupo (Gestão) já estão `HUMAN_APPROVED` /
`FROZEN` no negócio — nenhuma regra de cálculo, classificação, filtro ou
comissão foi tocada. Você não precisa revalidar nada disso. O que está em
avaliação agora é só: a versão responsiva (sem rolagem lateral) desses 4
módulos já aprovados.

**Technical status: TECHNICALLY GREEN** — ver
`docs/FROZEN-MODULE-NO-SCROLL-REMEDIATION.md` para o relatório técnico
completo (causa raiz, correção e prova de paridade por módulo).

## O que mudou

Auditorias anteriores (07.4) já tinham identificado que Landing, Score,
Coparticipado e Análise F&I tinham dependência de rolagem lateral em pelo
menos uma tela — mas esses módulos já estavam aprovados, então nada foi
mexido até agora. Esta rodada corrigiu isso, mantendo intactos: a
identidade visual, a hierarquia de informação aprovada em desktop, e
todos os valores/cálculos.

- **Landing**: o menu de categorias no celular não exige mais arrastar
  para o lado — as 5 categorias se reorganizam em várias linhas.
- **Score**: a tabela de ranking de vendedores se reorganiza em blocos
  verticais no celular; nomes longos agora aparecem por completo (antes
  eram cortados com "...").
- **Coparticipado**: as tabelas de Coparticipados e Subsidiados (as mais
  largas do Portal) continuam como tabela normal em telas maiores, e
  viram um cartão vertical com todos os campos no celular — nenhum campo
  foi escondido.
- **Análise F&I do Grupo**: as 8 tabelas do módulo (Financiamentos por
  Loja, Pagos/Faturados por Unidade/Banco, Planos por Loja/Departamento,
  SPF Extra, Propostas Recusadas/Aprovadas) se reorganizam em blocos
  verticais em telas menores.

## Como abrir

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```

- Landing: **http://localhost:8700/portal-next-v2/index.html#/landing**
- Score: **http://localhost:8700/portal-next-v2/index.html#/score**
- Coparticipado: **http://localhost:8700/portal-next-v2/index.html#/coparticipado**
- Análise F&I: **http://localhost:8700/portal-next-v2/index.html#/gestao**

## Passos

1. Abra cada uma das 4 telas acima em uma janela larga (desktop) e
   confirme que continuam visualmente iguais ao que você já aprovou.
2. Reduza a largura da janela do navegador aos poucos (ou abra pelo
   celular) em cada uma das 4 telas e confirme que a informação se
   reorganiza naturalmente, sem nenhuma rolagem lateral.
3. Em Score e Coparticipado, teste a fixture com nome longo (seletor
   "DADOS DE TESTE") e confirme que valores financeiros, percentuais e
   nomes continuam legíveis, sem cortar e sem quebrar letra por letra.
4. Confirme que filtros, botões, abas e navegação continuam fáceis de
   usar em qualquer tamanho de tela.

Não é necessário revisar código nem revalidar cálculos.

## Perguntas de validação

1. Em desktop, Landing, Score, Coparticipado e Análise F&I continuam
   visualmente como as versões que já foram aprovadas?
2. Reduzindo a largura da janela, as informações agora se reorganizam
   naturalmente sem exigir nenhuma rolagem horizontal?
3. Alguma informação importante desapareceu ou ficou escondida?
4. Valores financeiros, percentuais, nomes e textos longos continuam
   fáceis de ler?
5. Filtros, botões, navegação e demais ações continuam confortáveis de
   usar?
6. A versão responsiva continua parecendo o mesmo Portal aprovado, em
   vez de um novo redesign?

## O que você deve saber antes de avaliar

- Nenhum cálculo de negócio mudou: Score (12/12), Coparticipado (22/22)
  e Análise F&I (30/30, incluindo os 4 casos de arredondamento da
  Comissão Líquida SPF EXTRA = 70%) passam exatamente igual a antes.
- O Dashbi (Análise Geral do Grupo) não foi tocado nesta rodada — seus
  arquivos ficaram byte-idênticos, confirmado por hash.
- Um ponto pequeno e conhecido, não corrigido de propósito: no Landing,
  há um "sangramento" de 18px do retângulo de destaque ao passar o mouse
  sobre um módulo — ele já é contido pelo próprio layout (nunca vira uma
  barra de rolagem visível ou funcional em nenhum tamanho de tela) e é
  parte do design original, não uma correção pendente.
- Em Coparticipado, no celular a tabela vira um cartão com todos os
  campos empilhados (não existe uma versão "resumida" com campos
  escondidos atrás de + Detalhes) — nenhuma informação foi omitida.

## Depois da sua avaliação

Cada módulo passa a ter dois status separados:

```
NEGÓCIO/FUNCIONAL:  HUMAN_APPROVED / FROZEN   (já era, continua sendo)
RESPONSIVO:              UAT_PENDING          (aguardando sua avaliação)
```

Só a sua aprovação explícita muda RESPONSIVO para HUMAN_APPROVED/FROZEN.
Aprovar o responsivo não muda nem reabre o negócio — e não autoriza
nenhuma nova Wave (PORTAL-NEXT-08) automaticamente.
