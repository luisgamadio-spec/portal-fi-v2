# Human UAT — Gestão (Análise F&I do Grupo) V2 (Gates 147-148)

**Technical status: TECHNICALLY GREEN FOR IMPLEMENTED SCOPE**, with one surface explicitly BLOCKED pending a separate business decision (26/26 golden-fixture parity for everything else, 0 console/page errors across all fixtures and breakpoints, 0 backend network calls, Landing/Score/Coparticipado freeze re-verified byte-identical). Not the same thing as approval.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/gestao**

## 6 steps

1. Abra Gestão / Grupo (link acima) e confira os indicadores principais (Produção Paga/Faturada/Ag. Faturamento/Total).
2. Alterne entre Todos / Novos / Seminovos (botões "Tipo de veículo").
3. Teste período (botões "Mês atual"/"Mês anterior"/"Últimos 6 meses" ou datas manuais) e loja ("Loja / Unidade").
4. Confira "Planos por Loja e Departamento" e "Financiamentos por Loja".
5. Abra a fixture "priority_collision" ou "valores_grandes" (seletor "DADOS DE TESTE") para ver um cenário de stress.
6. Volte à Landing e confira rapidamente Score/Coparticipado.

Não é necessário revisar código.

## A pergunta principal

**"Esta Gestão V2 preserva a informação e o comportamento que você usa hoje, mas apresenta isso com a experiência Red Precision que homologamos?"**

## Uma pergunta separada, sobre uma decisão de negócio (não misturar com a pergunta acima)

O card **"Comissão Líquida SPF EXTRA"** (seção SPF EXTRA) está marcado **BLOQUEADO — DECISÃO HUMANA PENDENTE**. Existem hoje dois mecanismos reais e diferentes para esse percentual: um valor fixo de 70% escrito nesta própria tela (o que você vê no V1 hoje), e um parâmetro configurável (`spf_liquido_percentual`) usado pelo motor de comissão real do Portal, que um MASTER pode alterar no painel de configuração sem precisar de um novo deploy. Os dois coincidem em 70% hoje, mas podem divergir silenciosamente no futuro. Ver `docs/GESTAO-COMMISSION-DECISION.md` para o detalhe completo.

**"A regra de comissão usada nesta superfície deve seguir qual autoridade de negócio — o valor fixo desta tela, ou o parâmetro configurável do motor de comissão real?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais — sinalizado na própria tela ("DADOS DE TESTE").
- **Gestão, nesta produção real, é uma CATEGORIA de menu** ("📊 Gestão") que contém duas telas irmãs: "Análise F&I do Grupo" (esta, migrada nesta Wave) e "Análise Geral do Grupo" (um arquivo bem maior e diferente, ainda NOT_MIGRATED, Wave 5 — não confundir as duas).
- **Não existem** nesta tela real: Vendas/Financiamentos como métricas separadas de Produção, Share/Penetração, Receita, Ticket Médio, Retorno Médio, Análise por Modelo, Análise por Vendedor, FECHAMENTO, gráficos, ou exportação — confirmado por leitura direta do código-fonte real, não é uma lacuna de migração.
- A tabela **não é** clicável por coluna para reordenar (mesma limitação já registrada para Score/Coparticipado — a própria produção também não permite isso aqui).
- Upload de planilha e a API segura ao vivo não foram migrados (0 backend nesta Wave) — a tela V2 usa apenas fixtures locais selecionáveis.

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `gestao` entry. Esta fase não promoveu automaticamente, mesmo com a maior parte tecnicamente verde. A decisão sobre a Comissão Líquida SPF EXTRA é independente da aprovação visual/funcional — pode aprovar a tela e ainda deixar a decisão de comissão pendente, ou vice-versa.
