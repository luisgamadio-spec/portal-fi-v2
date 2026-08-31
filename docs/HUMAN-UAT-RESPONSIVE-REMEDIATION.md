# Human UAT — Responsive Remediation (PORTAL-NEXT-07.6.2)

**Escopo desta rodada: SOMENTE apresentação responsiva.** Landing, Score,
Coparticipado, Análise F&I do Grupo (Gestão) e Dashbi já estão
`HUMAN_APPROVED` / `FROZEN` no negócio — nenhuma regra de cálculo,
classificação, filtro ou comissão foi tocada. Você não precisa revalidar
nada disso.

## O que mudou nesta rodada (07.6.2) — correção de Score e Dashbi

Sua avaliação visual anterior apontou um problema real: não era mais
rolagem lateral, mas as tabelas de Score e Dashbi ficavam esmagadas em
telas estreitas — cabeçalhos e valores quebrando verticalmente,
"FINANCIAMENTOS" quebrando quase letra por letra, valores em R$
partidos em várias linhas. Investigamos e encontramos a causa raiz real
(não só um ajuste superficial): quando um "+ Detalhes" estava aberto em
tela estreita, uma regra de CSS antiga (`table-layout:fixed`) ainda
forçava a tabela a um layout de colunas fixas por trás da nova
apresentação em blocos — reproduzimos o problema exatamente e
corrigimos.

Além disso, redesenhamos a apresentação em blocos: antes cada campo
disputava espaço com os vizinhos de forma imprevisível; agora cada
campo ocupa a linha inteira (Vendedor/Loja com destaque, Score em
bloco próprio com a barra aprovada, valores em R$ sempre em uma linha
só) — só Vendas e Financiamentos (Dashbi) dividem uma linha, por serem
sempre números curtos.

**Technical status: TECHNICALLY GREEN** — ver
`docs/FROZEN-MODULE-NO-SCROLL-REMEDIATION.md` e
`docs/RESPONSIVE-TEST-EVIDENCE-07-6-1.md` para o relatório técnico
completo.

## O que mudou na rodada anterior (07.6, para referência)

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
- Dashbi: **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## Passos — foco desta rodada: Score e Dashbi

1. Abra **Score** e **Dashbi** na mesma largura estreita de navegador que
   mostrou o problema antes (recomendado: ~390px, ou reduza a janela até
   ficar parecido com um celular).
2. Em **Score**, confirme: nome do vendedor com destaque e legível
   (mesmo nomes longos), Loja/Depto/Financ. cada um em sua própria
   linha, Score em um bloco separado com a barra intacta — nada
   quebrando letra por letra.
3. Em **Dashbi**, abra "Vendas e Financiamentos por Loja" e "...por
   Vendedor", e clique em "+ Detalhes" em pelo menos uma linha (esse
   era exatamente o estado que quebrava antes). Confirme: Vendas e
   Financiamentos lado a lado (únicos dois campos assim), Share em
   destaque, Produção Total e Receita Total cada um em sua própria
   linha com o valor completo, "+ Detalhes" continua fácil de tocar.
4. Teste a fixture de nome longo em ambas as telas (seletor "DADOS DE
   TESTE") — nomes devem quebrar por palavra normalmente, nunca letra
   por letra.
5. Confirme que Landing, Coparticipado e Análise F&I continuam como na
   rodada anterior (não foram tocados desta vez).

Não é necessário revisar código nem revalidar cálculos.

## A pergunta principal desta rodada

**"Score e Dashbi agora reorganizam as informações em blocos legíveis,
sem esmagar a tabela, sem quebrar cabeçalhos/valores verticalmente e
sem introduzir rolagem horizontal?"**

## Perguntas da rodada anterior (07.6, ainda válidas para Landing/Coparticipado/Gestão)

1. Em desktop, Landing, Coparticipado e Análise F&I continuam
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

- Nenhum cálculo de negócio mudou: Score (12/12), Coparticipado (22/22),
  Análise F&I (30/30, incluindo os 4 casos de arredondamento da
  Comissão Líquida SPF EXTRA = 70%) e Dashbi (26/26) passam exatamente
  igual a antes. `dashbi.js`/`dashbi.adapter.js`/`score.adapter.js`
  ficaram byte-idênticos — só o CSS de apresentação mudou.
- Um ponto pequeno e conhecido, não corrigido de propósito: no Landing,
  há um "sangramento" de 18px do retângulo de destaque ao passar o mouse
  sobre um módulo — ele já é contido pelo próprio layout (nunca vira uma
  barra de rolagem visível ou funcional em nenhum tamanho de tela) e é
  parte do design original, não uma correção pendente.
- Em Coparticipado, no celular a tabela vira um cartão com todos os
  campos empilhados (não existe uma versão "resumida" com campos
  escondidos atrás de + Detalhes) — nenhuma informação foi omitida.
- Em Score, a coluna "#" (posição no ranking) aparece como rótulo "#"
  acima do número, na mesma lógica de rótulo/valor usada em todos os
  outros campos.

## Depois da sua avaliação

Cada módulo tem dois status separados:

```
Landing:            NEGÓCIO HUMAN_APPROVED/FROZEN · RESPONSIVO UAT_PENDING
Score:                   NEGÓCIO UAT_PENDING (conflito de banda do Design
                        System não resolvido) · RESPONSIVO UAT_PENDING
Coparticipado:               NEGÓCIO HUMAN_APPROVED/FROZEN · RESPONSIVO
                             UAT_PENDING
Análise F&I / Gestão:             NEGÓCIO HUMAN_APPROVED/FROZEN ·
                                  RESPONSIVO UAT_PENDING
Dashbi:                               NEGÓCIO HUMAN_APPROVED/FROZEN
                                     (aprovado após a rodada 07.5.2) ·
                                    RESPONSIVO UAT_PENDING (um defeito
                                   real foi encontrado e corrigido nesta
                                  rodada — aguardando nova avaliação
                                 visual antes de fechar novamente)
```

Só a sua aprovação explícita muda RESPONSIVO para HUMAN_APPROVED/FROZEN.
Aprovar o responsivo não muda nem reabre o negócio (Score continua
precisando de uma decisão separada sobre o conflito de banda) — e não
autoriza nenhuma nova Wave (PORTAL-NEXT-08) automaticamente.
