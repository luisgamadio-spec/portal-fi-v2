# Human UAT — Responsive Remediation (PORTAL-NEXT-07.6.4)

**Escopo desta rodada: SOMENTE apresentação responsiva.** Landing, Score,
Coparticipado, Análise F&I do Grupo (Gestão) e Dashbi já estão
`HUMAN_APPROVED` / `FROZEN` no negócio (exceto Score, veja abaixo) —
nenhuma regra de cálculo, classificação, filtro ou comissão foi tocada.
Você não precisa revalidar nada disso.

## IMPORTANTE — o que mudou nesta rodada (07.6.4)

Sua rejeição visual se repetiu mesmo depois do hard refresh solicitado
na rodada 07.6.3 — então paramos de tentar consertar a mesma abordagem
(transformar a tabela de desktop via CSS) pela terceira vez e trocamos
de estratégia:

**Score e Dashbi agora têm duas apresentações completamente separadas**,
alimentadas pelos mesmos dados já calculados — nenhum cálculo duplicado:

- **Desktop** (1366px+): a mesma tabela de sempre, sem nenhuma mudança.
- **Celular/tela estreita** (até 767px): **cartões individuais**, sem
  nenhuma estrutura de tabela por trás — não é mais a tabela "disfarçada"
  de blocos, é um componente novo e diferente. Em cada largura, só uma
  das duas versões existe visualmente (a outra fica completamente
  oculta) — comprovado por inspeção direta do navegador, não só visual.

Aplicamos isso em Score e em todas as tabelas do Dashbi que
compartilhavam o mesmo problema: Lojas, Vendedores, Ranking e Novos por
Loja.

**Technical status: TECHNICALLY GREEN** — ver
`docs/FROZEN-MODULE-NO-SCROLL-REMEDIATION.md` para o relatório técnico
completo, incluindo a prova de que a tabela de desktop deixa de existir
visualmente na tela estreita (não é só CSS escondendo, é uma
apresentação estruturalmente diferente).

## Como abrir

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Se o servidor já estiver rodando, não inicie um segundo.

- Score: **http://localhost:8700/portal-next-v2/index.html#/score**
- Dashbi: **http://localhost:8700/portal-next-v2/index.html#/dashbi**
- Landing: **http://localhost:8700/portal-next-v2/index.html#/landing**
- Coparticipado: **http://localhost:8700/portal-next-v2/index.html#/coparticipado**
- Análise F&I: **http://localhost:8700/portal-next-v2/index.html#/gestao**

## Passos — foco desta rodada: Score e Dashbi

1. Abra **Score** e **Dashbi** na mesma largura estreita que mostrou o
   problema antes (~390px, ou reduza a janela do navegador até ficar
   parecido com um celular).
2. Confirme que **não aparece mais nenhum cabeçalho de tabela** ("#​ |
   VENDEDOR | LOJA | DEPTO | SCORE | FINANC." em Score, "LOJA | VENDAS |
   FINANCIAMENTOS | SHARE | PRODUÇÃO TOTAL | RECEITA TOTAL" em Dashbi) —
   em vez disso, cada vendedor/loja aparece como um cartão individual
   com rótulo e valor.
3. Em **Score**: nome do vendedor em destaque, Loja/Depto/Financ. cada
   um legível, Score em bloco próprio com a barra aprovada em largura
   total.
4. Em **Dashbi**, abra "Vendas e Financiamentos por Loja" e "...por
   Vendedor", clique em "+ Detalhes" em pelo menos um cartão. Confirme:
   Vendas e Financiamentos lado a lado, Share em destaque, Produção
   Total e Receita Total cada um com o valor completo em uma linha.
5. Teste a fixture de nome longo (seletor "DADOS DE TESTE") em ambas as
   telas.
6. Confirme que Landing, Coparticipado e Análise F&I continuam como nas
   rodadas anteriores (não foram tocados nesta rodada).

Não é necessário revisar código nem revalidar cálculos.

## A pergunta principal desta rodada

**"Score e Dashbi agora aparecem como cartões individuais em tela
estreita — sem nenhum vestígio da tabela de desktop, sem cabeçalhos
comprimidos, sem quebra de texto letra por letra?"**

## O que você deve saber antes de avaliar

- Nenhum cálculo de negócio mudou: Score (12/12), Dashbi (26/26),
  Coparticipado (22/22) e Análise F&I (30/30) passam exatamente igual a
  antes. `dashbi.adapter.js`/`score.adapter.js` ficaram byte-idênticos —
  só a apresentação em tela estreita foi reconstruída do zero.
- Os cartões mostram exatamente os mesmos campos que a tabela de
  desktop, na mesma ordem de prioridade — nada foi escondido atrás de
  "+ Detalhes" que não estivesse lá antes.
- Um ponto pequeno e conhecido do Landing (sangramento de 18px do
  destaque de hover, contido, nunca vira rolagem) segue documentado, não
  corrigido, sem impacto visual real.

## Histórico desta investigação (rodadas anteriores)

```
07.6:    Primeira correção de rolagem lateral (Landing/Score/
         Coparticipado/Gestão) — TECHNICALLY GREEN, aprovação humana
         pendente.
07.6.1:  Status do Dashbi reconciliado (aprovação humana já dada após
         07.5.2); testes responsivos literais (zoom/orientação/resize/
         teclado) executados — 0 mudança de código.
07.6.2:  Primeira tentativa de corrigir legibilidade de Score/Dashbi
         (registro determinístico dentro da mesma tabela) —
         TECHNICALLY GREEN — REJEITADO PELO HUMANO.
07.6.3:  Investigação de ambiente: 14 processos de servidor duplicados
         encontrados e corrigidos; código da 07.6.2 reverificado
         exaustivamente e considerado correto — TECHNICALLY GREEN —
         REJEITADO PELO HUMANO NOVAMENTE, mesmo após hard refresh real.
07.6.4:  Mudança de estratégia (esta rodada) — dois renderizadores
         independentes (tabela de desktop + cartões de celular, sem
         nenhuma estrutura de tabela), não mais uma transformação CSS
         da mesma tabela.
```

Nenhuma dessas rodadas foi reescrita como aprovada — cada rejeição
humana está registrada como tal em `docs/MIGRATION-STATUS.md`.

## Depois da sua avaliação

```
Landing:              NEGÓCIO HUMAN_APPROVED/FROZEN · RESPONSIVO UAT_PENDING
Score:                     NEGÓCIO UAT_PENDING (conflito de banda do
                          Design System não resolvido) · RESPONSIVO
                         UAT_PENDING
Coparticipado:                 NEGÓCIO HUMAN_APPROVED/FROZEN ·
                               RESPONSIVO UAT_PENDING
Análise F&I / Gestão:               NEGÓCIO HUMAN_APPROVED/FROZEN ·
                                    RESPONSIVO UAT_PENDING
Dashbi:                                 NEGÓCIO HUMAN_APPROVED/FROZEN
                                       (aprovado após 07.5.2) ·
                                      RESPONSIVO UAT_PENDING (nova
                                     apresentação em cartões, aguardando
                                    sua avaliação)
```

Só a sua aprovação explícita muda RESPONSIVO para HUMAN_APPROVED/FROZEN.
Aprovar o responsivo não muda nem reabre o negócio (Score continua
precisando de uma decisão separada sobre o conflito de banda) — e não
autoriza nenhuma nova Wave (PORTAL-NEXT-08) automaticamente.
