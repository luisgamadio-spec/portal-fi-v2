# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.4.1)

**Technical status: TECHNICALLY GREEN** (26/26 golden-fixture parity, 0 console/page errors, 0 backend network calls, 0 horizontal scrollbar anywhere in Dashbi at all 6 required viewports, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). Você aprovou fortemente a experiência de linha principal + "+ Detalhes" da rodada 07.4 — esta rodada só ajusta 2 pontos dentro do painel de detalhes do modelo, sem mudar mais nada da experiência.

## O que mudou desde a rodada anterior

1. **"Entrada Qtd" foi removida** do painel de detalhes — era só um número interno de apoio ao cálculo, nunca uma métrica real da produção. Entrada Média e Entrada % continuam lá, com os mesmos valores de sempre.
2. **Qtd Subsidiado e Qtd Coparticipado foram adicionadas** ao grupo Planos, junto com Qtd Linear/Qtd Balão/Qtd Reversão que já existiam. Agora as 5 categorias de plano aparecem juntas, na ordem oficial de classificação (Subsidiado, Reversão, Coparticipado, Balão, Linear).

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

## 5 passos

1. Abra **Novos → Análise por Modelos** e clique em **"+ Detalhes"** de um modelo com dados (teste a fixture "model_analysis_parcelamento_completo" no seletor "DADOS DE TESTE" — ela tem Subsidiado e Coparticipado reais, além de Linear e Balão).
2. Confirme que **"Entrada Qtd" não aparece mais** — só Entrada Média e Entrada % (ambas com o mesmo valor de sempre).
3. No grupo **Planos**, confirme que agora aparecem as 5 categorias: Qtd Subsidiado, Qtd Reversão, Qtd Coparticipado, Qtd Balão, Qtd Linear — mais Balão Médio.
4. Confirme que **não há barra de rolagem lateral** em nenhum lugar da tela (a mesma verificação da rodada anterior).
5. Volte para **Ranking** e **Novos por Loja** — confirme que continuam exatamente como antes.

Não é necessário revisar código.

## A pergunta principal

**"Agora a Análise por Modelos apresenta as métricas de plano corretamente — Entrada Qtd removida e as 5 categorias de plano completas no grupo Planos?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais.
- Nenhum número já homologado mudou — Vendas/Financiamentos/Produção/Receita/Entrada/Ranking/Novos por Loja calculam exatamente igual à rodada anterior. Só a apresentação das tabelas largas mudou.
- Essa mesma regra de "sem rolagem lateral" **ainda não foi aplicada** aos módulos já aprovados (Landing, Score, Coparticipado, Análise F&I) — eles continuam como estavam, sem nenhuma mudança nesta rodada. Encontramos rolagem lateral em pelo menos uma tela de cada um deles e documentamos isso, mas não mexemos neles — são módulos já aprovados e travados, e só devem ser ajustados numa fase futura, com sua autorização explícita.
- A tabela não é clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
