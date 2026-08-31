# Human UAT — Gestão (Análise F&I do Grupo) V2 (PORTAL-NEXT-06.1)

**Technical status: TECHNICALLY GREEN.** A superfície "Comissão Líquida SPF EXTRA", antes bloqueada aguardando decisão humana, foi resolvida (ver `docs/GESTAO-COMMISSION-DECISION.md` — 70% fixo, não configurável, decisão registrada). O alinhamento das tabelas também foi corrigido nesta fase (30/30 golden-fixture parity, 0 console/page errors, 0 chamadas de backend, Landing/Score/Coparticipado reverificados byte-idênticos). Não é o mesmo que aprovação.

## How to open it

```
cd C:\Projetos\PORTAL-FI-DESIGN-LAB
python -m http.server 8700
```
Then open: **http://localhost:8700/portal-next-v2/index.html#/gestao**

## O que verificar

1. Alinhamento dos cabeçalhos e valores nas tabelas (compare visualmente a coluna de cada número com o cabeçalho acima dela, em qualquer tabela — "Planos por Loja e Departamento", "Financiamentos por Loja", etc.).
2. Leitura vertical das colunas (os números devem formar uma coluna reta, terminando no mesmo eixo que o cabeçalho).
3. Seção "SPF EXTRA": confira o card "Total SPF EXTRA".
4. Confira que "Comissão Líquida SPF EXTRA" = 70% do total SPF EXTRA (ex.: R$ 10.000,00 → R$ 7.000,00), sem o rótulo de bloqueio que existia antes.

Não é necessário revisar código.

## A pergunta

**"Agora a Gestão está visualmente alinhada e a regra de SPF EXTRA está representada corretamente?"**

## O que você deve saber antes de avaliar

- Os dados exibidos são **fixtures locais sintéticas**, não dados reais — sinalizado na própria tela ("DADOS DE TESTE").
- A regra "Comissão Líquida SPF EXTRA = Total × 70%" já foi decidida por você (ver `docs/GESTAO-COMMISSION-DECISION.md`) e vale **somente** para esta métrica específica — não foi generalizada para outras comissões, nem alterou o módulo Salários/Comissões.
- **Gestão, nesta produção real, é uma CATEGORIA de menu** ("📊 Gestão") que contém duas telas irmãs: "Análise F&I do Grupo" (esta) e "Análise Geral do Grupo" (um arquivo bem maior e diferente, ainda NOT_MIGRATED, Wave 5 — não confundir as duas).
- A tabela **não é** clicável por coluna para reordenar (mesma limitação já registrada para Score/Coparticipado — a própria produção também não permite isso aqui).

## O que acontece depois

Quem decide se isso vira `HUMAN_APPROVED` é você — via `config/module-registry.json`'s `gestao` entry. Esta fase não promoveu automaticamente, mesmo com tudo tecnicamente verde.
