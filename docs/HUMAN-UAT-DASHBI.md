# Human UAT — Análise Geral do Grupo (Dashbi) V2 (PORTAL-NEXT-07.1)

**Technical status: TECHNICALLY GREEN** (25/25 golden-fixture parity incl. the new Ranking tie-break fixture, 0 console/page errors, 0 backend network calls, 0 page-level horizontal overflow at 360/390/430, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). Not the same thing as approval — this round specifically targets the 4 issues you raised on the previous round.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## 6 steps (targeting your 4 issues directly)

1. Com **Grupo** selecionado (padrão): confirme que **Classificação dos Planos** e **Análise por Modelos** (com o seletor de família/imagens) **não aparecem** — devem existir somente em Novos.
2. Alterne para **Novos**: confirme que Classificação dos Planos e Análise por Modelos **voltam a aparecer**, com o seletor de veículos mostrando as imagens reais (Outlander/Eclipse Cross/Triton) — clique em cada card para trocar de família.
3. Alterne para **Seminovos**: confirme que os dois blocos acima continuam ocultos (mesma regra de Novos).
4. Em qualquer visão (Grupo/Novos/Seminovos), role até **Ranking** — confirme que os TOP 10 Vendedores/Lojas/Departamentos aparecem, ordenados por maior Receita Total. Troque de visão e confirme que o Ranking se atualiza e permanece visível nas 3.
5. Volte para **Novos** e role até **Novos por Loja** — confirme que a leitura por loja/unidade (Vendidos/Financiados/Balão/Subsidiada/Coparticipada/Reversão/Linear/Plano Destaque) aparece, e que ela **desaparece** ao trocar para Grupo ou Seminovos.
6. Teste a fixture "priority_collision" e a "multi_loja_vendedor" (seletor "DADOS DE TESTE") para ver os 3 blocos acima com mais de uma linha de dado.

Não é necessário revisar código.

## A pergunta principal

**"Agora a Análise Geral do Grupo mantém Ranking e Novos por Loja, mostra a Análise por Modelos somente em Novos e recupera as imagens dos veículos da forma que você esperava?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais — sinalizado na própria tela ("DADOS DE TESTE").
- As imagens dos veículos são as **mesmas fotos reais que a produção usa hoje** (extraídas diretamente do arquivo de produção, não geradas nem baixadas da internet), só redimensionadas para o seletor compacto.
- O **Ranking** aparece nas 3 visões (Grupo/Novos/Seminovos) porque é assim que a produção real se comporta — não é um bloco exclusivo de Novos como Análise por Modelos.
- **Novos por Loja** é exclusivo de Novos porque a própria produção assim define (mesma aba/visibilidade da Análise por Modelos).
- Nenhum número de Vendas/Financiamentos/Produção/Receita/Entrada já homologado nesta tela mudou nesta rodada — só a visibilidade de Classificação dos Planos/Análise por Modelos, a presença de Ranking/Novos por Loja, e a apresentação dos veículos.
- A fixture "vendedor_nao_localizado_bloqueia" mostra um comportamento real: se um vendedor não está cadastrado, a produção real **interrompe** o processamento inteiro em vez de mostrar um resultado parcial — reproduzido de propósito, não é um erro do V2.
- O selo "FECHAMENTO" só aparece quando o período filtrado é exatamente um mês fechado (do dia 1 ao último dia) — teste com a fixture "fechamento_mes_fechado" e as datas 01/03/2026 a 31/03/2026. Ele agora fica ao lado dos KPIs principais (visível nas 3 visões), não mais grudado no título de Classificação dos Planos, já que este último só aparece em Novos.
- A seção "Diagnóstico (dev only)" no rodapé é apenas para verificação técnica — não faz parte da experiência final e não deve ser confundida com um indicador de negócio.
- A tabela **não é** clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
