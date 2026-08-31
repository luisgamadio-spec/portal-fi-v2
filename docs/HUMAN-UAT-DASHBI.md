# Human UAT — Análise Geral do Grupo (Dashbi) V2 (Gates 149-150, 159-161)

**Technical status: TECHNICALLY GREEN** (24/24 golden-fixture parity, 0 console/page errors across all fixtures and 6 breakpoints, 0 backend network calls, Landing/Score/Coparticipado/Análise F&I freeze re-verified byte-identical). Not the same thing as approval.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/dashbi**

## 7 steps

1. Abra Análise Geral do Grupo / Dashbi (link acima) e revise os KPIs primários da Grupo (Vendas, Financiamentos, Produção, Receita, Retorno).
2. Alterne para Novos e depois Seminovos (botões "Visão").
3. Teste período (Mês atual/Mês anterior/Últimos 6 meses/Último ano ou datas manuais).
4. Revise "Vendas e Financiamentos por Loja" e "por Vendedor".
5. Abra a fixture "priority_collision" (seletor "DADOS DE TESTE") para conferir a Classificação dos Planos.
6. Revise cuidadosamente a **Análise por Modelos** (alterne entre OUTLANDER/TRITON/ECLIPSE CROSS) — especialmente **Entrada, Entrada Média e Entrada %**. Experimente as fixtures "entrada_elegivel" e "nova_entrada_sem_match" para ver o diagnóstico de correspondência de chassi.
7. Volte para Análise F&I e Landing.

Não é necessário revisar código.

## A pergunta principal

**"Esta Análise Geral do Grupo V2 preserva as informações e o comportamento que você utiliza hoje, mas apresenta tudo com a experiência Red Precision que homologamos?"**

## A pergunta sobre Análise por Modelos

**"Na Análise por Modelos, os indicadores e a leitura de Entrada estão organizados e apresentados da forma que você espera?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais — sinalizado na própria tela ("DADOS DE TESTE").
- **Dashbi** ("Análise Geral do Grupo") e **Análise F&I do Grupo** (já aprovada) são duas telas irmãs dentro da mesma categoria de menu real ("📊 Gestão") — arquivos, dados e lógicas de negócio completamente diferentes e independentes.
- Análise por Modelos é **exclusiva de Novos** — nenhum registro Seminovos entra nessa análise, mesmo comportamento real de produção.
- A fixture "vendedor_nao_localizado_bloqueia" mostra um comportamento real: se um vendedor não está cadastrado, a produção real **interrompe** o processamento inteiro em vez de mostrar um resultado parcial — reproduzido de propósito, não é um erro do V2.
- O selo "FECHAMENTO" só aparece quando o período filtrado é exatamente um mês fechado (do dia 1 ao último dia) — teste com a fixture "fechamento_mes_fechado" e as datas 01/03/2026 a 31/03/2026.
- A seção "Diagnóstico (dev only)" no rodapé é apenas para verificação técnica — não faz parte da experiência final e não deve ser confundida com um indicador de negócio.
- A tabela **não é** clicável por coluna para reordenar (mesma limitação já registrada para todos os módulos anteriores).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `dashbi` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
