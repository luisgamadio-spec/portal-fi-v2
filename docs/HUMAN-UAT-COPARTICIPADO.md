# Human UAT — Coparticipado V2 (Gates 79-80)

**Technical status: PASS** (22/22 golden-fixture parity, 0 console/page
errors across every fixture and breakpoint, 0 backend network calls,
Landing/Score freeze re-verified byte-identical). Not the same thing as
approval.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/coparticipado**

## 5 steps

1. Abrir o Coparticipado normal (link acima).
2. Testar a fixture "normal" (deixe o seletor em "combinado (todos os
   cenários)" — rotulado "DADOS DE TESTE (NEXT_LOCAL)") e observar a
   tabela de Planos Coparticipados.
3. Trocar filtros/ordenação — use os filtros de Loja e Departamento no
   topo e confira que a tabela atualiza corretamente; alterne entre
   "Visão Coparticipados" e "Visão Subsidiados".
4. Abrir detalh[e] — não há um segundo nível de detalhe por linha nesta
   tela (a própria linha já é a operação de financiamento individual,
   igual à produção real — ver "O que você deve saber" abaixo).
5. Voltar para a Landing (link "PF" ou clique no rail à esquerda) e
   confirmar que o Score e a Landing continuam intactos.

Não é necessário revisar código.

## A pergunta principal

**"Este módulo Coparticipado V2 preserva as informações e regras que
você utiliza hoje, mas com a experiência Red Precision que
homologamos?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados
  reais — isso está sinalizado na própria tela ("DADOS DE TESTE").
  Use o seletor de fixture para inspecionar cenários isolados
  (`priority_collision`, `duplicate_b3`, `modelo_sem_taxa`,
  `nome_longo`, `valores_grandes`, `missing_base02` etc.) além da
  visão combinada padrão.
- As duas visões ("Visão Coparticipados" / "Visão Subsidiados") e as
  colunas de cada tabela são as mesmas da produção real — nada foi
  adicionado ou removido (ver `docs/COPARTICIPADO-EXTRACTION-TRACE.md`).
- **Não existe drill-down por linha** — a própria produção não tem um
  modal de detalhe para essas duas tabelas; a linha já é a unidade
  mais fina real (uma operação de financiamento).
- A aba "Diagnóstico" (alerta de vendedores não cadastrados) **não foi
  migrada** — depende do cadastro real de vendedores (backend), fora
  do escopo desta Wave (0 backend). A exportação para Excel também não
  foi migrada, pelo mesmo motivo (0 I/O de arquivo).
- A tabela **não é** clicável por coluna para reordenar — mesma
  limitação já registrada para o Score (indicador visual de coluna
  ordenável nunca foi definido no Design System, UNRESOLVED), e a
  própria produção também não permite isso nestas duas tabelas.

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via
`config/module-registry.json`'s `coparticipado` entry. Esta fase não
promoveu automaticamente, mesmo com tudo tecnicamente verde.
