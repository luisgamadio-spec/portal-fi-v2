/* PORTAL-NEXT V2 — Brabus Intelligence CONTRACT adapter (IA-V2-1).

   THIS FILE IS A CONTRACT MODEL, NOT A BUSINESS ENGINE. It has three
   jobs, and only three: (1) shape a request the way the real
   Intelligence backend expects it, (2) normalize/validate a response
   the way the real backend actually returns it, (3) serve synthetic,
   clearly-labeled FIXTURE responses standing in for that backend this
   Wave (0 network calls -- see docs/IA-V2-1-CONTRACT.md). It contains
   ZERO financial calculation, ZERO tool-selection logic, ZERO copy of
   the Intelligence system prompt or tool registry -- every fixture
   response below is a plain data literal, not a computed one. When
   IA-V2-2 wires the real backend, `resolveFixtureScenario` is the
   ONLY function that gets replaced with a real `fetch()` call; nothing
   downstream (the page controller, the renderer) needs to change,
   because both already speak this same shape.

   Contract source: the real, reconciled `portal-ai-homolog` Edge
   Function (portal-financiamento-brabus-secure /
   ia-reconciliation-v2-local worktree) and its frontend caller
   (assets/js/portal-ai-ui.js's baiSend/baiFormatValue) — recovered
   behaviorally for IA-V2-PLAN-01/IA-V2-1, never transplanted. */
(function () {
  'use strict';

  /* ============================================================
     REQUEST CONTRACT
     ============================================================ */

  // The real backend only ever sees the last 8 prior turns, and only
  // {role, content} -- structured blocks are deliberately never resent
  // (they don't help the model and just inflate the payload).
  var MAX_HISTORY = 8;

  function createRequest(message, conversation) {
    var prior = (conversation || []).slice(-MAX_HISTORY).map(function (m) {
      return { role: m.role, content: m.content };
    });
    return { message: String(message || ''), conversation: prior };
  }

  /* ============================================================
     RESPONSE CONTRACT
     ============================================================ */

  // Exactly the 6 block "type" discriminators proven to exist across
  // all 12 real Intelligence tools (IA-V2-PLAN-01 §Structured Results)
  // -- no per-tool renderer, the tool's own semantics already live
  // inside the block's fields.
  var BLOCK_TYPES = ['metrics', 'comparison', 'ranking', 'operations', 'score_breakdown', 'score_ranking'];

  function validateBlock(block) {
    return !!block && typeof block === 'object' && BLOCK_TYPES.indexOf(block.type) !== -1;
  }

  // Strips internal/debug metadata (the real backend's homolog-only
  // `_homolog_debug` field) and keeps only what a presentation layer
  // may use. `blocks` may legitimately contain entries this Wave's
  // renderer doesn't recognize (defense in depth, matching the real
  // backend's own "malformed block -> silently omitted" discipline) --
  // those are filtered out here, never thrown.
  function normalizeResponse(payload) {
    payload = payload || {};
    var blocks = Array.isArray(payload.blocks) ? payload.blocks.filter(validateBlock) : null;
    return {
      reply: typeof payload.reply === 'string' ? payload.reply : '',
      blocks: blocks && blocks.length ? blocks : null,
      request_id: typeof payload.request_id === 'string' ? payload.request_id : null,
      scenario_reset: payload.scenario_reset === true
    };
  }

  /* ============================================================
     FORMAT CONTRACT — ported BEHAVIORALLY from the real frontend's
     baiFormatValue (assets/js/portal-ai-ui.js in the Intelligence
     repo), not copied verbatim (different DOM API). Same 3 semantic
     rules, most important one first:

     PERCENT VALUES ARE ALREADY PERCENTAGE POINTS. The real backend's
     block builders do the x100 conversion server-side BEFORE the
     value ever reaches a block (e.g. Cash Conversion's 0.0112 fraction
     becomes 1.12 inside the block) -- this formatter must never
     multiply/divide again. This is the exact opposite convention from
     this repo's OWN Simuladores helpers (NX_SIM_UI.pct1/pct2), which
     format a raw fraction from V2's local calculators and DO multiply
     by 100 -- those two helpers must never be used interchangeably;
     mixing them up here would double- or never-convert the value and
     silently reintroduce the exact class of percentage-scale bug this
     contract is written to avoid.
     ============================================================ */

  function formatValue(value, format) {
    if (format === 'date') {
      if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return { text: '—', title: null };
      var p = value.split('-');
      return { text: p[2] + '/' + p[1] + '/' + p[0], title: null };
    }
    // 'text' -- a free-text value (e.g. a masked operation description),
    // rendered verbatim, never formatted as a number. Not present in the
    // ported baiFormatValue (whose caller never had a text-format item);
    // added here for the Operations block's own item shape, which does
    // carry free-text values -- disclosed in docs/IA-V2-1-CONTRACT.md as
    // this Wave's own addition, not independently re-verified against
    // the real backend's exact field-by-field operations shape.
    if (format === 'text') {
      return { text: (value === null || value === undefined) ? '—' : String(value), title: null };
    }
    if (value === null || value === undefined || typeof value !== 'number' || !isFinite(value)) {
      return { text: '—', title: null };
    }
    if (format === 'currency') {
      var full = value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 });
      if (Math.abs(value) >= 1000000) {
        var compact = 'R$ ' + (value / 1000000).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' mi';
        return { text: compact, title: full };
      }
      return { text: full, title: null };
    }
    if (format === 'percent') {
      // NO x100 here -- see the contract note above.
      return { text: value.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%', title: null };
    }
    if (format === 'int') {
      return { text: value.toLocaleString('pt-BR', { maximumFractionDigits: 0 }), title: null };
    }
    return { text: value.toLocaleString('pt-BR'), title: null };
  }

  /* ============================================================
     FIXTURE SCENARIOS (IA-V2-1 ONLY — see docs/IA-V2-1-CONTRACT.md).

     Every value below is a plain synthetic literal, never derived from
     a formula. Field names/shapes mirror the real contract exactly
     (recovered by reading the real source, not guessed) so the
     adapter/renderer built against these fixtures needs ZERO change
     when IA-V2-2 swaps this function for a real backend call.
     ============================================================ */

  var SCENARIOS = [
    {
      id: 'plain-text',
      description: 'Basic TEXT question (consultar_resultado)',
      prompt: 'Qual foi o resultado do mês passado?',
      match: /resultado do m[eê]s passado/i,
      response: {
        reply: 'No mês anterior o grupo fechou 13 vendas, 10 financiamentos (share de 76,9%), com produção de R$ 100.500,00 e retorno de R$ 68.600,00.',
        blocks: [{
          type: 'metrics', title: 'Grupo — mês anterior', period_label: 'mês anterior',
          items: [
            { key: 'sales', label: 'Vendas', value: 13, format: 'int' },
            { key: 'financed', label: 'Financiamentos', value: 10, format: 'int' },
            { key: 'share_percent', label: 'Share', value: 76.9, format: 'percent' },
            { key: 'production', label: 'Produção', value: 100500, format: 'currency' },
            { key: 'return', label: 'Retorno', value: 68600, format: 'currency' }
          ]
        }],
        request_id: 'fixture-plain-text', scenario_reset: false
      }
    },
    {
      id: 'linear',
      description: 'Financiamento Linear',
      prompt: 'Simula um financiamento linear de um veículo novo de R$ 120.000, com R$ 30.000 de entrada, em 36 meses.',
      match: /financiamento linear/i,
      response: {
        reply: 'A parcela do financiamento Linear em 36x fica R$ 4.010,97, com R$ 90.000,00 financiado.',
        blocks: [{
          type: 'metrics', title: 'Simulação — Financiamento Linear Novos', period_label: 'Simulação — não é proposta nem aprovação de crédito',
          items: [
            { key: 'vehicle_value', label: 'Valor do veículo', value: 120000, format: 'currency' },
            { key: 'down_payment', label: 'Entrada', value: 30000, format: 'currency' },
            { key: 'down_payment_percent', label: 'Entrada (%)', value: 25, format: 'percent' },
            { key: 'financed_amount', label: 'Financiado', value: 90000, format: 'currency' },
            { key: 'payment_36', label: 'Parcela 36x', value: 4010.97, format: 'currency' }
          ]
        }],
        request_id: 'fixture-linear', scenario_reset: false
      }
    },
    {
      id: 'balao',
      // Also the combined-blocks fixture (Gate 14) -- the real backend
      // can return more than one block per reply; a Balão
      // optimize-comparison reply is the clearest real example. Kept
      // short here since this string is also used as a dropdown
      // <option> label (a long sentence would overflow the select).
      description: 'Financiamento Balão',
      prompt: 'Simula um financiamento com balão de R$ 40.000 num veículo de R$ 150.000, entrada de R$ 30.000, em 36 meses.',
      match: /bal[ãa]o de R\$\s*40\.000/i,
      response: {
        reply: 'A parcela do Balão em 36x fica R$ 3.180,45, com balão de R$ 40.000,00 no último mês. Veja também como essa condição se compara a outros prazos.',
        blocks: [
          {
            // Real ranking contract (IA-V2-2-STRUCTURED-BLOCK-FIX-01):
            // items carry {position, name, <metric-named field>}, never
            // {label,value,format} -- see buildBalaoOptimizeComparisonBlock
            // in the authoritative source.
            type: 'ranking', title: 'Balão — comparação por prazo', period_label: 'Simulação — não é proposta nem aprovação de crédito',
            dimension: 'term_months', metric: 'sim_payment',
            items: [
              { position: 1, name: '30x', sim_payment: 3620.1 },
              { position: 2, name: '36x', sim_payment: 3180.45 },
              { position: 3, name: '42x', sim_payment: 2890.75 }
            ]
          },
          {
            type: 'metrics', title: 'Simulação — Financiamento Balão Novos (36x)', period_label: 'Simulação — não é proposta nem aprovação de crédito',
            items: [
              { key: 'vehicle_value', label: 'Valor do veículo', value: 150000, format: 'currency' },
              { key: 'down_payment', label: 'Entrada', value: 30000, format: 'currency' },
              { key: 'balloon_value', label: 'Valor do balão', value: 40000, format: 'currency' },
              { key: 'balloon_month', label: 'Mês do balão', value: 36, format: 'int' },
              { key: 'payment', label: 'Parcela mensal', value: 3180.45, format: 'currency' }
            ]
          }
        ],
        request_id: 'fixture-balao', scenario_reset: false
      }
    },
    {
      id: 'coparticipado',
      description: 'Plano Coparticipado',
      prompt: 'Quero simular Coparticipado para a L200 Triton, R$ 200.000, entrada R$ 120.000, 24 meses.',
      match: /coparticipado/i,
      response: {
        reply: 'No Plano Coparticipado, a L200 Triton em 24x fica com parcela de R$ 3.600,00 e rebate total de R$ 4.000,00.',
        blocks: [{
          type: 'metrics', title: 'Simulação — Plano Coparticipado (L200 TRITON, 24x)', period_label: 'Simulação — não é proposta nem aprovação de crédito',
          items: [
            { key: 'financed', label: 'Valor financiado', value: 80000, format: 'currency' },
            { key: 'payment', label: 'Parcela 24x', value: 3600, format: 'currency' },
            { key: 'rebate_total', label: 'Rebate total', value: 4000, format: 'currency' },
            { key: 'final_sale_value', label: 'Valor final de venda', value: 198000, format: 'currency' }
          ]
        }],
        request_id: 'fixture-coparticipado', scenario_reset: false
      }
    },
    {
      id: 'subsidiado',
      description: 'Taxas Subsidiadas',
      prompt: 'Quais as condições de Taxas Subsidiadas para um bem de R$ 90.000 com entrada de R$ 50.000?',
      match: /taxas subsidiadas/i,
      response: {
        reply: 'Para R$ 90.000,00 com entrada de R$ 50.000,00, há 2 opções de prazo disponíveis nas Taxas Subsidiadas.',
        blocks: [{
          // Real shape -- see buildSubsidiadasRankingBlock in the
          // authoritative source (dimension: "rate_term").
          type: 'ranking', title: 'Taxas Subsidiadas — todas as opções', period_label: 'Simulação — não é proposta nem aprovação de crédito',
          dimension: 'rate_term', metric: 'sim_payment',
          items: [
            { position: 1, name: '24x', sim_payment: 1920 },
            { position: 2, name: '36x', sim_payment: 1440 }
          ]
        }],
        request_id: 'fixture-subsidiado', scenario_reset: false
      }
    },
    {
      id: 'taxa-implicita',
      description: 'Taxa Implícita (Descobridor de Taxa)',
      prompt: 'Um cliente financiou R$ 100.000 em 36x de R$ 4.485,75. Qual a taxa implícita desse contrato?',
      match: /taxa impl[ií]cita/i,
      response: {
        reply: 'Para R$ 100.000,00 em 36x de R$ 4.485,75, a Taxa NET fica em 2,58% a.m. e a Taxa CET em 2,86% a.m. — são cálculos independentes, nunca compare um pelo outro sem indicar qual é qual.',
        blocks: [{
          type: 'metrics', title: 'Cálculo — Taxa Implícita (Descobridor de Taxa)', period_label: 'Aproximação matemática pela Tabela PRICE — não comprova disponibilidade comercial nem histórica',
          items: [
            { key: 'financed_amount', label: 'Valor financiado informado', value: 100000, format: 'currency' },
            { key: 'payment', label: 'Parcela (36x)', value: 4485.75, format: 'currency' },
            { key: 'taxa_net', label: 'Taxa NET ao mês (resultado principal)', value: 2.58, format: 'percent' },
            { key: 'taxa_cet', label: 'Taxa CET ao mês (sobre o valor informado, sem ajuste)', value: 2.86, format: 'percent' },
            { key: 'total_pago', label: 'Total pago (nominal)', value: 161487, format: 'currency' },
            { key: 'juros_totais', label: 'Juros totais aproximados', value: 61487, format: 'currency' },
            { key: 'taxa_anual', label: 'Taxa NET efetiva anual (derivada, cálculo adicional)', value: 35.73, format: 'percent' }
          ]
        }],
        request_id: 'fixture-taxa-implicita', scenario_reset: false
      }
    },
    {
      id: 'antecipacao',
      description: 'Antecipação sem first_due_date',
      prompt: 'Quero simular a antecipação de um contrato com saldo de R$ 50.000, sem informar a data da próxima parcela.',
      match: /antecipa[çc][ãa]o de um contrato/i,
      response: {
        reply: 'Como você não informou a data da próxima parcela, usei hoje + 30 dias corridos como referência. O valor final com desconto fica R$ 48.654,00.',
        blocks: [{
          type: 'metrics', title: 'Antecipação — Contrato todo', period_label: 'Estimativa comercial para conferência',
          items: [
            { key: 'first_due_date', label: 'Primeira parcela considerada (assumida)', value: '2026-10-01', format: 'date' },
            { key: 'gross_total', label: 'Valor bruto', value: 54000, format: 'currency' },
            { key: 'discount_total', label: 'Desconto total', value: 5346, format: 'currency' },
            { key: 'settlement_amount', label: 'Valor final com desconto', value: 48654, format: 'currency' },
            { key: 'discount_percent', label: 'Desconto (% do bruto)', value: 9.9, format: 'percent' }
          ]
        }],
        request_id: 'fixture-antecipacao', scenario_reset: false
      }
    },
    {
      id: 'cash-conversion',
      description: 'Cash Conversion',
      prompt: 'Vale mais a pena o cliente pagar à vista R$ 50.000 ou financiar e deixar o dinheiro aplicado por 12 meses?',
      match: /pagar [àa] vista R\$\s*50\.000 ou financiar/i,
      response: {
        reply: 'Financiando e mantendo os R$ 50.000,00 aplicados à taxa oficial de 1,12% a.m., o capital projetado ao final do prazo supera o custo do financiamento.',
        blocks: [{
          type: 'metrics', title: 'Simulação — Cash Conversion', period_label: null,
          items: [
            { key: 'capital', label: 'Capital inicial', value: 50000, format: 'currency' },
            { key: 'payment', label: 'Parcela ofertada (12x)', value: 1500, format: 'currency' },
            { key: 'application_rate', label: 'Taxa de aplicação (a.m.) — premissa padrão fixa', value: 1.1, format: 'percent' },
            { key: 'future_value', label: 'Capital final projetado', value: 57149.8, format: 'currency' },
            { key: 'projected_difference', label: 'Diferença projetada', value: 39149.8, format: 'currency' }
          ]
        }],
        request_id: 'fixture-cash-conversion', scenario_reset: false
      }
    },
    {
      id: 'score',
      description: 'Score Vendedores (breakdown)',
      prompt: 'Qual o score do vendedor Ana Paula Ribeiro neste período?',
      match: /score (do|da) vendedor/i,
      response: {
        reply: 'O Score de Ana Paula Ribeiro no período fica em 87,4 pontos, banda "Alto Desempenho".',
        blocks: [{
          // Real shape -- see buildScoreBreakdownBlock in the
          // authoritative source: NO items array at all, flat identity/
          // summary fields on the block itself + components[].
          type: 'score_breakdown', title: 'Score F&I — Ana Paula Ribeiro', period_label: 'competência atual',
          seller: 'Ana Paula Ribeiro', store: 'Barra Funda', department: 'NOVOS',
          score: 87.4, classification: 'Alto Desempenho', rank: 1,
          sales: 12, financed: 10,
          penetration_percent: 68.5, average_return_percent: 3.2,
          components: [
            { label: 'Volume', value: 20, max: 25 },
            { label: 'Penetração', value: 16, max: 20 },
            { label: 'Mix de planos', value: 14, max: 20 }
          ],
          plan_mix: { LINEAR: 8, BALAO: 4 }, main_plan: 'LINEAR', family_count: 3
        }],
        request_id: 'fixture-score', scenario_reset: false
      }
    },
    {
      id: 'historico',
      description: 'Histórico de Financiamentos',
      prompt: 'Me mostra o histórico de financiamentos dos últimos 90 dias.',
      match: /hist[óo]rico de financiamentos/i,
      response: {
        reply: 'No período, o histórico registra 42 operações, entrada média de 22,4% e prazo médio de 38 meses.',
        blocks: [{
          type: 'metrics', title: 'Histórico — resumo do período', period_label: 'últimos 90 dias',
          items: [
            { key: 'operations_count', label: 'Operações', value: 42, format: 'int' },
            { key: 'avg_down_payment_percent', label: 'Entrada média', value: 22.4, format: 'percent' },
            { key: 'avg_term', label: 'Prazo médio (meses)', value: 38, format: 'int' }
          ]
        }],
        request_id: 'fixture-historico', scenario_reset: false
      }
    },
    {
      id: 'comparison',
      description: 'Comparação entre lojas (comparar_resultado)',
      prompt: 'Compara o resultado de Barra Funda com Santo Amaro neste mês.',
      match: /compara(r)? (o resultado de|a loja)/i,
      response: {
        reply: 'Comparando as duas lojas no período: a Barra Funda teve share maior, a Santo Amaro teve produção maior.',
        blocks: [{
          type: 'comparison', title: 'Comparação',
          a: { label: 'Barra Funda', period_label: 'mês atual', items: [
            { key: 'sales', label: 'Vendas', value: 9, format: 'int' },
            { key: 'share_percent', label: 'Share', value: 81.2, format: 'percent' },
            { key: 'production', label: 'Produção', value: 62000, format: 'currency' }
          ] },
          b: { label: 'Santo Amaro', period_label: 'mês atual', items: [
            { key: 'sales', label: 'Vendas', value: 11, format: 'int' },
            { key: 'share_percent', label: 'Share', value: 74.6, format: 'percent' },
            { key: 'production', label: 'Produção', value: 79500, format: 'currency' }
          ] },
          deltas: { sales: 2, share_percent: -6.6, production: 17500 }
        }],
        request_id: 'fixture-comparison', scenario_reset: false
      }
    },
    {
      id: 'operations',
      description: 'Operações especiais (consultar_operacoes_especiais)',
      prompt: 'Tem operações especiais registradas neste período?',
      match: /opera[çc][õo]es especiais/i,
      response: {
        reply: 'Encontrei 2 operações especiais no período, todas com dado de cliente mascarado por política de segurança.',
        blocks: [{
          // Real shape -- see buildOperationsBlock in the authoritative
          // source: top-level totals + items:[{reference (masked),
          // date, store, department, seller, model, financed_value,
          // return_value}], never {label,value,format}. Rendered as
          // cards, never a table (source's own explicit intent).
          type: 'operations', title: 'Operações especiais — período atual',
          total_count: 2, total_financed_value: 404400, total_return_value: 20200, truncated: false, shown_count: 2,
          items: [
            { reference: '***4471', date: '2026-08-12', store: 'Barra Funda', department: 'NOVOS', seller: 'Ana Paula Ribeiro', model: 'PAJERO SPORT', financed_value: 189900, return_value: 9500 },
            { reference: '***9903', date: '2026-08-20', store: 'Santo Amaro', department: 'NOVOS', seller: 'Bruno Alves', model: 'L200 TRITON', financed_value: 214500, return_value: 10700 }
          ]
        }],
        request_id: 'fixture-operations', scenario_reset: false
      }
    },
    {
      id: 'score-ranking',
      description: 'Ranking de Score (score_ranking)',
      prompt: 'Mostra o ranking de score do período.',
      match: /ranking de score/i,
      response: {
        reply: 'O ranking de Score do período tem Ana Paula Ribeiro em primeiro lugar, com 87,4 pontos.',
        blocks: [{
          // Real shape -- see buildScoreRankingBlock in the
          // authoritative source: items:[{rank,seller,store,department,
          // score,classification,sales,financed}], never
          // {label,value,format}.
          type: 'score_ranking', title: 'Ranking Score F&I — período atual',
          items: [
            { rank: 1, seller: 'Ana Paula Ribeiro', store: 'Barra Funda', department: 'NOVOS', score: 87.4, classification: 'Alto Desempenho', sales: 12, financed: 10 },
            { rank: 2, seller: 'Carlos Eduardo Souza', store: 'Santo Amaro', department: 'NOVOS', score: 81.9, classification: 'Alto Desempenho', sales: 10, financed: 9 },
            { rank: 3, seller: 'Bruno Kaminski', store: 'Barra Funda', department: 'SEMINOVOS', score: 76.2, classification: 'Médio Desempenho', sales: 8, financed: 6 }
          ]
        }],
        request_id: 'fixture-score-ranking', scenario_reset: false
      }
    },
    {
      id: 'unauthenticated',
      description: '401 — no/expired session',
      prompt: '__fixture_401__',
      match: /__fixture_401__/,
      error: { status: 401, message: 'Sessão expirada — entre novamente.' }
    },
    {
      id: 'forbidden',
      description: '403 — authenticated, non-MASTER',
      prompt: '__fixture_403__',
      match: /__fixture_403__/,
      error: { status: 403, message: 'Este recurso não está disponível para o seu perfil.' }
    },
    {
      id: 'upstream-error',
      description: 'Upstream/model error',
      prompt: '__fixture_upstream_error__',
      match: /__fixture_upstream_error__/,
      error: { status: 502, message: 'Não foi possível concluir a análise agora. Tente novamente.' }
    },
    {
      id: 'scenario-reset',
      description: 'iniciar_novo_cliente — scenario_reset:true',
      prompt: 'Beleza, agora é outro cliente, esquece esse.',
      match: /outro cliente, esquece esse/i,
      response: {
        reply: 'Prontinho, começamos do zero — pode me contar sobre o novo cliente.',
        blocks: null,
        request_id: 'fixture-scenario-reset', scenario_reset: true
      }
    }
  ];

  function resolveFixtureScenario(message) {
    var text = String(message || '');
    for (var i = 0; i < SCENARIOS.length; i++) {
      if (SCENARIOS[i].match.test(text)) return SCENARIOS[i];
    }
    return null;
  }

  function loadFixtureScenario(id) {
    for (var i = 0; i < SCENARIOS.length; i++) {
      if (SCENARIOS[i].id === id) return SCENARIOS[i];
    }
    return null;
  }

  /* ============================================================
     REAL TEXT TRANSPORT (IA-V2-2) -- the ONLY function that changes
     when swapping fixture for a real backend, exactly as planned in
     IA-V2-1-CONTRACT.md. Sends the SAME request shape createRequest()
     already produces, to the real portal-ai-homolog contract
     (POST, Content-Type/apikey/Authorization headers, {message,
     conversation} body), and returns the SAME {response}/{error}
     shape resolveFixtureScenario()'s callers already handle -- no
     fork in the page controller's own send flow. Zero financial
     logic: this function only moves bytes and maps an HTTP status to
     the already-established Portuguese error copy (Gate 26), it never
     inspects or computes a financial value. */
  var ERROR_MESSAGE_BY_STATUS = {
    401: 'Sessão expirada — entre novamente.',
    403: 'Este recurso não está disponível para o seu perfil.',
    // IA-V2-3B -- the backend's own server-authoritative kill switch
    // (never a frontend toggle) returns 503 when Intelligence is
    // disabled. Same tone as 401/403: plain, non-technical, no retry
    // loop, no fixture fallback -- applyResult() already renders every
    // error identically as a normal conversation bubble.
    503: 'Brabus Intelligence está temporariamente indisponível.'
  };
  function errorMessageForStatus(status) {
    return ERROR_MESSAGE_BY_STATUS[status] || 'Não foi possível concluir a análise agora. Tente novamente.';
  }

  function sendRealText(message, conversation, accessToken) {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    if (!cfg.textEndpoint || !cfg.supabasePublishableKey) {
      return Promise.resolve({ error: { status: 0, message: 'Configuração de Intelligence ausente — modo real_text não está configurado neste ambiente.' } });
    }
    if (!accessToken) {
      return Promise.resolve({ error: { status: 401, message: errorMessageForStatus(401) } });
    }
    var body = createRequest(message, conversation);
    return fetch(cfg.textEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': cfg.supabasePublishableKey,
        'Authorization': 'Bearer ' + accessToken
      },
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().catch(function () { return {}; }).then(function (payload) {
        if (!resp.ok) {
          return { error: { status: resp.status, message: errorMessageForStatus(resp.status) } };
        }
        return { response: normalizeResponse(payload) };
      });
    }).catch(function () {
      return { error: { status: 0, message: errorMessageForStatus(0) } };
    });
  }

  window.NX_BRABUS_INTELLIGENCE_ADAPTER = {
    MAX_HISTORY: MAX_HISTORY,
    BLOCK_TYPES: BLOCK_TYPES,
    createRequest: createRequest,
    normalizeResponse: normalizeResponse,
    validateBlock: validateBlock,
    formatValue: formatValue,
    SCENARIOS: SCENARIOS,
    resolveFixtureScenario: resolveFixtureScenario,
    loadFixtureScenario: loadFixtureScenario,
    sendRealText: sendRealText
  };
})();
