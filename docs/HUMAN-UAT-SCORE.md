# Human UAT — Score V2 (Gates 71-72)

**Technical status: PASS** (12/12 golden-fixture parity, normative
compliance PASS except the disclosed band conflict). Not the same
thing as approval.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/score**

## 5 steps

1. Abrir o Score normal (link acima).
2. Observar score / breakdown / explicação de cada critério (clique
   numa linha da tabela).
3. Testar o ranking/tabela — a ordem já vem de `calcScores()`, não é
   reordenável por coluna nesta Wave (ver nota abaixo).
4. Trocar a fixture dev para `long_name` e `large_values` (seletor no
   topo, rotulado "DADOS DE TESTE") e conferir que nada quebra.
5. Voltar para a Landing (link "PF" ou clique no rail à esquerda).

Não é necessário revisar código.

## A pergunta principal

**"Este Score V2 preserva a informação que você usa hoje, mas com a
experiência Red Precision que homologamos?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados
  reais — isso está sinalizado na própria tela ("DADOS DE TESTE").
- A tabela **não é** clicável por coluna para reordenar — a ordem
  mostrada é sempre a mesma que `calcScores()` já produz (score desc,
  desempate por financiamentos). O indicador visual de coluna
  ordenável nunca foi definido no Design System (UNRESOLVED) — não foi
  inventado aqui.
- **Não existe "faixa" (ALTO/BOM/BAIXO)** — o Design System pede uma,
  mas a produção real não tem esse conceito. Isso é um conflito real,
  não uma omissão — ver `docs/SCORE-ENGINE-AUDIT.md`.
- O drill-down de "ver vendas individuais" (modal com cada
  financiamento) **não foi migrado** — só o detalhamento por critério
  (a mesma lógica de pontuação). Ver `docs/SCORE-EXTRACTION-TRACE.md`.

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via
`config/module-registry.json`'s `score` entry. Esta fase não promoveu
automaticamente, mesmo com tudo tecnicamente verde.
