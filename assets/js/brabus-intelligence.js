/* PORTAL-NEXT V2 — Brabus Intelligence page (IA-V2-1, real transport
   added IA-V2-2).

   Two transport modes, selected by window.NX_INTELLIGENCE_CONFIG.mode
   (default 'fixture', safe everywhere -- Gate 8 containment):
   'fixture' behaves exactly as IA-V2-1 shipped it (0 network calls,
   synthetic contract data, fixture banner visible). 'real_text' calls
   the real, unmodified portal-ai-homolog contract via
   NX_AUTH.getAccessToken() + A.sendRealText() -- this file still never
   calls fetch/XHR itself, that lives entirely in the adapter, and both
   modes converge on the exact same applyResult()/renderConversation()
   path below, so nothing about rendering forks between them. ZERO
   business logic either way: this file only builds/reads DOM and
   calls the adapter's pure formatting functions — every number/date/
   percent shown comes verbatim from a response object neither mode
   computes.

   Conversation state lives in this module's own closure, reset on
   every render() call — matching every other V2 module's lifecycle
   (no module in this repo preserves state across a route re-entry;
   inventing that here would be a new, unasked-for product decision,
   see IA-V2-PLAN-01 §STATE). */
(function () {
  'use strict';

  var A = window.NX_BRABUS_INTELLIGENCE_ADAPTER;

  var conversation = []; // [{role, content, blocks}]
  var sending = false;

  function isRealTextMode() {
    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    return cfg.mode === 'real_text';
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ============================================================
     ASSISTANT PROSE RENDERER (HOTFIX-03) — a narrow, safe Markdown
     subset for the model's own conversational reply text ONLY (never
     structured blocks, never user messages, never conversation state
     sent back to the backend -- see applyResult/createRequest, which
     both still read/send msg.content verbatim, untouched by this).

     Security: esc() runs FIRST, over the ENTIRE raw string, before any
     Markdown-to-HTML transform. Every tag this renderer ever emits is
     a fixed, hardcoded literal (<p>, <strong>, <em>, <code>, <ul>,
     <ol>, <li>, <br>) -- never text derived from unescaped input, so
     no raw HTML/script/event-handler/javascript: URL from the model
     can ever reach the DOM: with < and > already turned into entities
     before this function's own regexes ever run, there is no "<" left
     in the string for any of them to match or reintroduce as a tag. */

  function mdInline(escapedText) {
    // Placeholder uses a Private-Use-Area character (U+E000) as a
    // delimiter, never a raw control byte -- practically impossible
    // to collide with real conversational text, and keeps this file
    // as ordinary UTF-8 text (a literal NUL byte here previously made
    // the file misdetect as binary to some tools -- HOTFIX-04 cleanup).
    var codeStore = [];
    var out = escapedText.replace(/`([^`\n]+?)`/g, function (_, code) {
      codeStore.push(code);
      return '\uE000CODE' + (codeStore.length - 1) + '\uE000';
    });
    out = out
      .replace(/\*\*([^\n]+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, '$1<em>$2</em>');
    out = out.replace(/\uE000CODE(\d+)\uE000/g, function (_, idx) {
      return '<code>' + codeStore[Number(idx)] + '</code>';
    });
    return out;
  }

  /* HOTFIX-04 -- ordered-list continuity. A model reply routinely
     interleaves each numbered item with its own subordinate "- "
     detail bullets (and a blank line between items), e.g.:

       1. Forma de pagamento
          - Linear: ...
          - Balão: ...

       2. Valor das parcelas mensais
          - Linear: ...

     Blank lines and "- " lines belong to the SAME ordered list unless
     what follows is genuinely something else (a paragraph, a heading,
     or end of input) -- otherwise every interruption started a brand
     new <ol>, and a native <ol> always restarts its own numbering at
     1, which is exactly the "1. / 1. / 1." defect this fixes. This
     stays narrow and specific to the one nesting shape actually
     observed (ordered item + flat "- " detail bullets), not a
     general-purpose Markdown parser. */
  function peekNextNonBlank(lines, i) {
    var j = i;
    while (j < lines.length && lines[j].trim() === '') j++;
    return j;
  }

  function renderAssistantProse(raw) {
    var escaped = esc(raw).replace(/\r\n/g, '\n');
    var lines = escaped.split('\n');
    var htmlParts = [];
    var paragraphBuf = [];

    function flushParagraph() {
      if (paragraphBuf.length) {
        htmlParts.push('<p>' + mdInline(paragraphBuf.join('<br>')) + '</p>');
        paragraphBuf = [];
      }
    }

    var i = 0;
    while (i < lines.length) {
      var trimmed = lines[i].trim();

      if (trimmed === '') { flushParagraph(); i++; continue; }

      var heading = /^(#{2,3})\s+(.*)$/.exec(trimmed);
      if (heading) {
        flushParagraph();
        htmlParts.push('<p class="baiMdHeading">' + mdInline(heading[2]) + '</p>');
        i++; continue;
      }

      var ulItem = /^-\s+(.*)$/.exec(trimmed);
      if (ulItem) {
        flushParagraph();
        var liItems = [];
        while (i < lines.length) {
          var here = lines[i].trim();
          if (here === '') {
            var nxt = peekNextNonBlank(lines, i);
            if (nxt < lines.length && /^-\s+/.test(lines[nxt].trim())) { i = nxt; continue; }
            break;
          }
          var m = /^-\s+(.*)$/.exec(here);
          if (!m) break;
          liItems.push('<li>' + mdInline(m[1]) + '</li>');
          i++;
        }
        htmlParts.push('<ul>' + liItems.join('') + '</ul>');
        continue;
      }

      var olItem = /^\d+\.\s+(.*)$/.exec(trimmed);
      if (olItem) {
        flushParagraph();
        var oItems = [];
        while (i < lines.length) {
          var here2 = lines[i].trim();
          if (here2 === '') {
            var nxt2 = peekNextNonBlank(lines, i);
            var lookahead = nxt2 < lines.length ? lines[nxt2].trim() : '';
            if (/^\d+\.\s+/.test(lookahead) || /^-\s+/.test(lookahead)) { i = nxt2; continue; }
            break;
          }
          var om = /^\d+\.\s+(.*)$/.exec(here2);
          if (om) {
            oItems.push({ text: om[1], subs: [] });
            i++;
            continue;
          }
          var subm = /^-\s+(.*)$/.exec(here2);
          if (subm && oItems.length) {
            oItems[oItems.length - 1].subs.push(subm[1]);
            i++;
            continue;
          }
          break;
        }
        var oHtml = oItems.map(function (it) {
          var subHtml = it.subs.length
            ? '<ul>' + it.subs.map(function (s) { return '<li>' + mdInline(s) + '</li>'; }).join('') + '</ul>'
            : '';
          return '<li>' + mdInline(it.text) + subHtml + '</li>';
        }).join('');
        htmlParts.push('<ol>' + oHtml + '</ol>');
        continue;
      }

      paragraphBuf.push(trimmed);
      i++;
    }
    flushParagraph();
    return htmlParts.join('');
  }

  /* ============================================================
     STRUCTURED BLOCK RENDERER — renderStructuredBlock(block)
     dispatches by block.type into 6 presentation-only functions.
     Every value shown is read from block.items[].value via
     A.formatValue -- NONE of these functions performs arithmetic,
     derives a delta, or computes anything not already in the payload.
     ============================================================ */

  function metricItemHtml(item) {
    var f = A.formatValue(item.value, item.format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiMetricItem"><p class="modKpiLabel">' + esc(item.label) + '</p>' +
      '<p class="modKpiValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function renderMetrics(block) {
    var items = (block.items || []).map(metricItemHtml).join('');
    return blockPanelHtml(block, '<div class="baiMetricsGrid">' + items + '</div>');
  }

  function renderComparison(block) {
    function side(s) {
      if (!s) return '';
      var items = (s.items || []).map(metricItemHtml).join('');
      return '<div class="baiComparisonSide"><p class="baiComparisonSideLabel">' + esc(s.label) +
        (s.period_label ? ' <span class="modMuted" style="display:inline;margin:0">· ' + esc(s.period_label) + '</span>' : '') + '</p>' +
        '<div class="baiMetricsGrid">' + items + '</div></div>';
    }
    return blockPanelHtml(block, '<div class="baiComparisonGrid">' + side(block.a) + side(block.b) + '</div>', true);
  }

  /* ============================================================
     STRUCTURED BLOCK FIELD CONTRACT (HOTFIX-05 --
     IA-V2-2-STRUCTURED-BLOCK-FIX-01). ranking/score_ranking/
     score_breakdown/operations do NOT use the {label,value,format}
     shape metrics/comparison use -- rediscovered field-by-field from
     the real, authoritative source
     (supabase/functions/portal-ai-homolog/index.ts, every
     `buildXBlock` function that returns one of these 4 types, ~8 call
     sites). RANKING_FIELD_META/RANKING_DIMENSION_LABELS below mirror
     the backend's OWN METRIC_LABELS/DIMENSION_LABELS constants (same
     Portuguese labels, same keys) plus the additional field/dimension
     identifiers this module's own real UAT observed -- every key here
     traces to a real field the backend actually emits, none invented.
     No financial formula lives here: this is presentation-label
     lookup only, never a calculation. */
  var RANKING_FIELD_META = {
    sales: { label: 'Vendas', format: 'int' },
    financed: { label: 'Financiamentos', format: 'int' },
    share_percent: { label: 'Share', format: 'percent' },
    production: { label: 'Produção', format: 'currency' },
    return: { label: 'Retorno', format: 'currency' },
    return_avg_percent: { label: 'Retorno Médio', format: 'percent' },
    spf: { label: 'SPF', format: 'currency' },
    profitability: { label: 'Rentabilidade', format: 'currency' },
    sim_payment: { label: 'Parcela', format: 'currency' },
    sim_financed: { label: 'Financiado', format: 'currency' },
    sim_down_payment: { label: 'Entrada', format: 'currency' },
    hist_count: { label: 'Operações', format: 'int' },
    hist_avg_down_payment_percent: { label: 'Entrada Média', format: 'percent' },
    hist_avg_installment_value: { label: 'Parcela Média', format: 'currency' },
    hist_avg_term_months: { label: 'Prazo Médio (meses)', format: 'int' },
    seller: { label: 'Vendedor', format: 'text' },
    store: { label: 'Loja', format: 'text' },
    department: { label: 'Departamento', format: 'text' },
    classification: { label: 'Classificação', format: 'text' },
    score: { label: 'Score', format: null },
    penetration_percent: { label: 'Penetração', format: 'percent' },
    average_return_percent: { label: 'Retorno Médio', format: 'percent' },
    main_plan: { label: 'Plano Principal', format: 'text' },
    family_count: { label: 'Famílias', format: 'int' },
    reference: { label: 'Referência', format: 'text' },
    date: { label: 'Data', format: 'date' },
    model: { label: 'Modelo', format: 'text' },
    financed_value: { label: 'Financiado', format: 'currency' },
    return_value: { label: 'Retorno', format: 'currency' },
    down_payment_value: { label: 'Entrada', format: 'currency' },
    down_payment_percent: { label: 'Entrada (%)', format: 'percent' },
    installment_value: { label: 'Parcela', format: 'currency' },
    installments: { label: 'Parcelas', format: 'int' }
  };
  // Mirrors the backend's own DIMENSION_LABELS (store/seller/model/plan)
  // plus the simulation/histórico dimension identifiers this module's
  // real UAT observed on block.dimension (down_payment/term_months/
  // rate_term/down_payment_bucket) -- same source, never invented.
  var RANKING_DIMENSION_LABELS = {
    store: 'Loja', seller: 'Vendedor', model: 'Modelo', plan: 'Plano',
    down_payment: 'Entrada', term_months: 'Prazo', term: 'Prazo',
    rate_term: 'Condição', down_payment_bucket: 'Faixa de Entrada'
  };

  function fieldMeta(key) {
    return RANKING_FIELD_META[key] || { label: key, format: null };
  }

  function rankingValueCell(it, key) {
    var meta = fieldMeta(key);
    var f = A.formatValue(it[key], meta.format);
    var colClass = meta.format === 'currency' ? 'modCurrencyCol' : (meta.format === 'percent' ? 'modPercentCol' : 'modNumCol');
    return '<td class="' + colClass + '">' + esc(f.text) + '</td>';
  }

  // Real shape: {dimension, metric, items:[{position, name, ...one or
  // more metric-named fields}]} -- NOT {label,value,format} per item.
  // `name` is the row label and `metric` names which item field is the
  // primary value in every producer this was checked against (Resultado
  // ranking, Linear/Balão/Coparticipado/Subsidiado compare_down_payments,
  // Histórico distributions). Any OTHER fields present on the item
  // (e.g. Coparticipado's compare also carries sim_down_payment/
  // sim_financed alongside sim_payment) render as their own columns
  // too, so no real backend data is dropped -- gate: "Responsive
  // transformation may change layout, never information."
  function renderRanking(block) {
    var items = block.items || [];
    if (!items.length) return blockPanelHtml(block, '<p class="modMuted">Sem itens para exibir.</p>', true);
    var keys = Object.keys(items[0]).filter(function (k) { return k !== 'position' && k !== 'name'; });
    if (block.metric && keys.indexOf(block.metric) > 0) {
      keys.splice(keys.indexOf(block.metric), 1);
      keys.unshift(block.metric);
    }
    var nameHeader = RANKING_DIMENSION_LABELS[block.dimension] || 'Item';
    var headerCells = '<th>#</th><th>' + esc(nameHeader) + '</th>' +
      keys.map(function (k) { return '<th>' + esc(fieldMeta(k).label) + '</th>'; }).join('');
    var rows = items.map(function (it, idx) {
      var pos = (it.position !== undefined && it.position !== null) ? it.position : idx + 1;
      return '<tr><td class="modNumCol">' + esc(String(pos)) + '</td><td>' + esc(it.name != null ? it.name : '') + '</td>' +
        keys.map(function (k) { return rankingValueCell(it, k); }).join('') + '</tr>';
    }).join('');
    var table = '<div class="modTableWrap"><table class="modTable"><thead><tr>' + headerCells + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
    return blockPanelHtml(block, table, true);
  }

  // Real shape: top-level {..., total_count, total_financed_value,
  // truncated, shown_count, items:[{reference, date, store, department,
  // seller?, model, financed_value, return_value?, down_payment_value?,
  // down_payment_percent?, installment_value?, installments?}]} -- two
  // real variants exist (Coparticipado/Subsidiado operations vs.
  // Histórico similar_operations), differing only in which optional
  // fields are present; both handled by iterating whatever the item
  // actually has. Rendered as CARDS, never a table -- the backend's own
  // source comment is explicit: "cards com referência mascarada, nunca
  // uma tabela (mobile-first)".
  var OPERATIONS_CARD_TOP_FIELDS = ['reference', 'date', 'store', 'department', 'seller', 'model'];

  function operationsCardHtml(it) {
    var headerParts = [];
    if (it.reference) headerParts.push('<span class="baiOpRef">' + esc(it.reference) + '</span>');
    if (it.date) headerParts.push('<span class="modMuted">' + esc(A.formatValue(it.date, 'date').text) + '</span>');
    var subtitleParts = [it.store, it.department, it.model, it.seller].filter(function (v) { return v; }).map(esc);
    var dataKeys = Object.keys(it).filter(function (k) { return OPERATIONS_CARD_TOP_FIELDS.indexOf(k) === -1; });
    var dataHtml = dataKeys.map(function (k) {
      var meta = fieldMeta(k);
      var f = A.formatValue(it[k], meta.format);
      return '<div class="baiOperationRow"><span class="modMuted" style="margin:0">' + esc(meta.label) + '</span><span>' + esc(f.text) + '</span></div>';
    }).join('');
    return '<div class="baiOperationCard">' +
      '<div class="baiOpCardHeader">' + headerParts.join(' · ') + '</div>' +
      (subtitleParts.length ? '<p class="modMuted" style="margin:2px 0 6px">' + subtitleParts.join(' · ') + '</p>' : '') +
      dataHtml + '</div>';
  }

  function renderOperations(block) {
    var items = block.items || [];
    var cards = items.length ? items.map(operationsCardHtml).join('') : '<p class="modMuted">Sem operações no período.</p>';
    var summaryBits = [];
    if (block.total_count !== undefined && block.total_count !== null) summaryBits.push(block.total_count + ' operação(ões)');
    if (block.total_financed_value !== undefined && block.total_financed_value !== null) summaryBits.push('financiado total ' + A.formatValue(block.total_financed_value, 'currency').text);
    if (block.truncated) summaryBits.push('lista truncada — mostrando ' + (block.shown_count || items.length));
    var summaryHtml = summaryBits.length ? '<p class="baiBlockPeriod">' + esc(summaryBits.join(' · ')) + '</p>' : '';
    return blockPanelHtml(block, summaryHtml + '<div class="baiOperationsList">' + cards + '</div>', true);
  }

  // Real shape: NO block.items at all -- identity/summary fields sit
  // flat on the block itself (seller, store, department, score,
  // classification, rank, sales, financed, penetration_percent,
  // average_return_percent, plan_mix, main_plan, family_count), plus
  // `components:[{label,value,max}]` for the score's own point
  // breakdown (Volume/Penetração/Mix/SPF Extra/Retorno médio per the
  // source's own comment) -- 100% backend-computed, never
  // reconstructed or recalculated here.
  function renderScoreBreakdown(block) {
    var summaryItems = [];
    function pushIfPresent(label, value, format) {
      if (value === undefined || value === null) return;
      summaryItems.push({ label: label, value: value, format: format });
    }
    pushIfPresent('Score', block.score, null);
    pushIfPresent('Classificação', block.classification, 'text');
    pushIfPresent('Posição', block.rank, 'int');
    pushIfPresent('Vendas', block.sales, 'int');
    pushIfPresent('Financiamentos', block.financed, 'int');
    pushIfPresent('Penetração', block.penetration_percent, 'percent');
    pushIfPresent('Retorno Médio', block.average_return_percent, 'percent');
    var summaryHtml = '<div class="baiMetricsGrid">' + summaryItems.map(metricItemHtml).join('') + '</div>';

    var components = Array.isArray(block.components) ? block.components : [];
    var componentsHtml = components.length ? '<div class="baiOperationsList">' + components.map(function (c) {
      var maxText = (c.max !== undefined && c.max !== null) ? ' / ' + esc(String(c.max)) : '';
      return '<div class="baiOperationRow"><span class="modMuted" style="margin:0">' + esc(c.label) + '</span><span>' + esc(String(c.value)) + maxText + '</span></div>';
    }).join('') + '</div>' : '';

    var planMixHtml = '';
    if (block.plan_mix && typeof block.plan_mix === 'object') {
      var planEntries = Object.keys(block.plan_mix).map(function (k) { return esc(k) + ': ' + esc(String(block.plan_mix[k])); });
      if (planEntries.length) planMixHtml = '<p class="baiBlockPeriod">Mix de planos — ' + planEntries.join(' · ') + '</p>';
    }

    return blockPanelHtml(block, summaryHtml + componentsHtml + planMixHtml);
  }

  // Real shape: items:[{rank, seller, store, department, score,
  // classification, sales, financed}] -- NOT {label,value,format}.
  function renderScoreRanking(block) {
    var items = block.items || [];
    if (!items.length) return blockPanelHtml(block, '<p class="modMuted">Sem itens para exibir.</p>', true);
    var rows = items.map(function (it) {
      var scoreF = A.formatValue(it.score, null);
      var salesF = A.formatValue(it.sales, 'int');
      var financedF = A.formatValue(it.financed, 'int');
      return '<tr><td class="modNumCol">' + esc(it.rank != null ? String(it.rank) : '') + '</td>' +
        '<td>' + esc(it.seller || '') + '</td>' +
        '<td>' + esc(it.store || '') + '</td>' +
        '<td>' + esc(it.department || '') + '</td>' +
        '<td class="modNumCol">' + esc(scoreF.text) + '</td>' +
        '<td>' + esc(it.classification || '') + '</td>' +
        '<td class="modNumCol">' + esc(salesF.text) + '</td>' +
        '<td class="modNumCol">' + esc(financedF.text) + '</td></tr>';
    }).join('');
    var table = '<div class="modTableWrap"><table class="modTable"><thead><tr><th>#</th><th>Vendedor</th><th>Loja</th><th>Depto</th><th>Score</th><th>Classificação</th><th>Vendas</th><th>Financ.</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    return blockPanelHtml(block, table, true);
  }

  var RENDERERS = {
    metrics: renderMetrics,
    comparison: renderComparison,
    ranking: renderRanking,
    operations: renderOperations,
    score_breakdown: renderScoreBreakdown,
    score_ranking: renderScoreRanking
  };

  function blockPanelHtml(block, bodyHtml, skipModPanelResult) {
    return '<div class="' + (skipModPanelResult ? '' : 'modPanelResult ') + 'baiBlockPanel">' +
      '<h2 class="baiBlockTitle">' + esc(block.title || 'Resultado') + '</h2>' +
      (block.period_label ? '<p class="baiBlockPeriod">' + esc(block.period_label) + '</p>' : '') +
      bodyHtml + '</div>';
  }

  function renderStructuredBlock(block) {
    var fn = RENDERERS[block.type];
    return fn ? fn(block) : '';
  }

  /* ============================================================
     CONVERSATION RENDERING
     ============================================================ */

  function messageHtml(msg) {
    var roleClass = msg.role === 'user' ? 'baiMessageUser' : 'baiMessageAssistant';
    var roleLabel = msg.role === 'user' ? 'Você' : 'Brabus Intelligence';
    // Markdown rendering applies ONLY to real assistant replies -- user
    // input stays plain text (Gate: never render user-authored
    // Markdown), and error bubbles are our own fixed strings, not
    // model output, so they stay plain too.
    var isAssistantProse = msg.role !== 'user' && !msg.isError;
    var bubbleContent = isAssistantProse ? renderAssistantProse(msg.content) : esc(msg.content);
    var bubbleClass = 'baiBubble' + (msg.isError ? ' baiBubbleError' : '') + (isAssistantProse ? ' baiBubbleMd' : '');
    var bubble = '<div class="' + bubbleClass + '">' + bubbleContent + '</div>';
    var blocksHtml = '';
    if (Array.isArray(msg.blocks) && msg.blocks.length) {
      blocksHtml = '<div class="baiStructuredRegion">' + msg.blocks.map(renderStructuredBlock).join('') + '</div>';
    }
    return '<div class="baiMessage ' + roleClass + '"><span class="baiRoleLabel">' + esc(roleLabel) + '</span>' + bubble + blocksHtml + '</div>';
  }

  function loadingHtml() {
    return '<div class="baiMessage baiMessageAssistant"><div class="baiBubble baiBubbleLoading modLoadingState">' +
      '<span class="modLoadingDot" aria-hidden="true"></span>Analisando os dados do Portal…</div></div>';
  }

  function renderConversation() {
    var el = document.getElementById('baiConversation');
    if (!el) return;
    if (conversation.length === 0) {
      // IA-V2-1-VISUAL-FIX-01 -- no empty-state panel, by explicit
      // human visual UAT request ("like opening ChatGPT": empty means
      // visually empty, not a bordered card announcing there's nothing
      // yet). .baiConversation's own min-height keeps the composer from
      // jumping up flush under the fixture banner; no other placeholder.
      el.innerHTML = '';
      // Returning to the empty state (Nova conversa) should return the
      // page to the top too -- otherwise the window can be left scrolled
      // to wherever the prior, now-cleared conversation had grown to.
      window.scrollTo(0, 0);
      return;
    }
    el.innerHTML = conversation.map(messageHtml).join('') + (sending ? loadingHtml() : '');
    // #baiConversation has no `overflow` of its own -- the whole page
    // grows and the WINDOW scrolls, not this element, so `el.scrollTop`
    // was a no-op (found live during IA-V2-1-VISUAL-QA-01's screenshot
    // pass: several captures came back showing an empty viewport
    // because the window hadn't followed new content into view).
    window.scrollTo(0, document.documentElement.scrollHeight);
  }

  /* ============================================================
     SEND FLOW — simulates the real request/response round trip
     against fixture data ONLY. A short, fixed, deterministic delay
     (150ms) stands in for real network latency, purely so the
     loading state is genuinely reachable/demonstrable and testable
     — never a multi-second wait, never randomized (Gate 37).
     ============================================================ */

  var FIXTURE_LATENCY_MS = 150;

  function setSending(state) {
    sending = state;
    var btn = document.getElementById('baiSendBtn');
    var input = document.getElementById('baiInput');
    if (btn) btn.disabled = state;
    if (input) input.disabled = state;
  }

  // Shared by BOTH transports -- the one place that turns a
  // {response}/{error} result into conversation state, so fixture and
  // real_text can never silently diverge in how they apply a result
  // (scenario_reset pruning, error-bubble styling, etc. all live here
  // exactly once).
  function applyResult(result) {
    setSending(false);
    if (result.error) {
      conversation.push({ role: 'assistant', content: result.error.message, blocks: null, isError: true });
      renderConversation();
      return;
    }
    var normalized = result.response;
    if (normalized.scenario_reset) {
      // Mirrors the real frontend's own scenario_reset handling:
      // prune back to just the triggering user turn, then append the
      // reply -- never invent new reset semantics (Gate 34).
      var lastUserIdx = -1;
      for (var i = conversation.length - 1; i >= 0; i--) {
        if (conversation[i].role === 'user') { lastUserIdx = i; break; }
      }
      if (lastUserIdx > 0) conversation = conversation.slice(lastUserIdx);
    }
    conversation.push({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
    renderConversation();
  }

  function handleSendFixture(text, priorTurns) {
    // Model the real request contract even though nothing is sent over
    // the network -- proves the shape is correct without needing a
    // live backend (Gate 15/32 of IA-V2-1).
    A.createRequest(text, priorTurns);

    setTimeout(function () {
      var scenario = A.resolveFixtureScenario(text);
      if (!scenario) {
        setSending(false);
        conversation.push({ role: 'assistant', content: 'Não tenho um cenário de teste para essa pergunta neste protótipo local — isso não indica uma falha do contrato, apenas que este fixture não cobre esta frase. Veja o seletor de cenários acima para os exemplos disponíveis.', blocks: null, isError: false });
        renderConversation();
        return;
      }
      if (scenario.error) {
        applyResult({ error: scenario.error });
        return;
      }
      applyResult({ response: A.normalizeResponse(scenario.response) });
    }, FIXTURE_LATENCY_MS);
  }

  function handleSendRealText(text, priorTurns) {
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      return;
    }
    window.NX_AUTH.getAccessToken().then(function (token) {
      if (!token) {
        applyResult({ error: { status: 401, message: 'Sessão expirada — entre novamente.' } });
        return;
      }
      return A.sendRealText(text, priorTurns, token).then(applyResult);
    }).catch(function () {
      applyResult({ error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
    });
  }

  function handleSend(text) {
    if (sending || !text) return;
    conversation.push({ role: 'user', content: text });
    // setSending BEFORE renderConversation -- renderConversation's own
    // loading-bubble condition reads `sending`, so calling it first
    // would render with sending still false and the bubble would never
    // appear (found live during IA-V2-1-VISUAL-QA-01's loading-state
    // pass).
    setSending(true);
    renderConversation();

    var priorTurns = conversation.slice(0, -1);
    if (isRealTextMode()) handleSendRealText(text, priorTurns);
    else handleSendFixture(text, priorTurns);
  }

  function onNovaConversa() {
    if (sending) return;
    conversation = [];
    renderConversation();
    var input = document.getElementById('baiInput');
    if (input) { input.value = ''; input.focus(); }
  }

  /* ============================================================
     COMPOSER
     ============================================================ */

  function wireComposer() {
    var input = document.getElementById('baiInput');
    var btn = document.getElementById('baiSendBtn');
    function submit() {
      var text = (input.value || '').trim();
      if (!text) return;
      input.value = '';
      handleSend(text);
    }
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', function (e) {
      // Enter submits; Shift+Enter inserts a newline (Gate 12).
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });
  }

  function wireFixtureBanner() {
    var select = document.getElementById('baiFixtureSelect');
    var input = document.getElementById('baiInput');
    if (!select || !input) return;
    select.addEventListener('change', function () {
      var scenario = A.loadFixtureScenario(select.value);
      if (scenario) {
        input.value = scenario.prompt;
        input.focus();
      }
      select.value = '';
    });
  }

  /* ============================================================
     PAGE SHELL
     ============================================================ */

  function fixtureBannerHtml() {
    var options = A.SCENARIOS.map(function (s) {
      return '<option value="' + esc(s.id) + '">' + esc(s.description) + '</option>';
    }).join('');
    return '<div class="modFixtureBanner"><span class="modFixtureLabel">DADOS DE TESTE / CONTRATO LOCAL</span>' +
      '<span>Nenhum backend real conectado — respostas vêm de um contrato de fixture local.</span>' +
      '<label for="baiFixtureSelect">preencher com um cenário de exemplo:</label>' +
      '<select id="baiFixtureSelect"><option value="">— escolher —</option>' + options + '</select></div>';
  }

  function pageHtml() {
    // Gate 34/35 of IA-V2-2 -- the fixture banner/selector are dev/
    // test tooling that must never appear once REAL_TEXT is active;
    // the approved IA-V2-1 clean initial state is otherwise identical
    // either way (Gate 46 visual freeze).
    return '<div class="baiPage">' +
      '<div class="modPageHeader"><div class="modHeaderMain">' +
      '<span class="modEyebrow">INTELLIGENCE</span>' +
      '<h1 class="modTitle">Brabus Intelligence</h1>' +
      '<p class="modSubtitle">Assistente F&amp;I para análise, simulação e apoio comercial.</p>' +
      '</div><div class="modHeaderActions baiHeaderActions">' +
      '<button type="button" class="modBtn modBtnGhost" id="baiNewChatBtn">Nova conversa</button>' +
      '</div></div>' +
      (isRealTextMode() ? '' : fixtureBannerHtml()) +
      '<div class="baiWorkspace">' +
      '<div class="baiConversation" id="baiConversation" aria-live="polite" aria-atomic="false"></div>' +
      '<div class="baiComposer">' +
      '<textarea id="baiInput" class="baiComposerInput" aria-label="Pergunta para a Brabus Intelligence" placeholder="Pergunte sobre financiamento, resultado, score ou condição financeira..." rows="1"></textarea>' +
      '<div class="baiComposerActions"><button type="button" class="modBtn modBtnPrimary" id="baiSendBtn">Enviar</button></div>' +
      '</div></div></div>';
  }

  window.NX_BRABUS_INTELLIGENCE_PAGE = {
    render: function (outlet) {
      conversation = [];
      sending = false;
      outlet.innerHTML = pageHtml();
      wireComposer();
      wireFixtureBanner();
      document.getElementById('baiNewChatBtn').addEventListener('click', onNovaConversa);
      renderConversation();
      return Promise.resolve();
    },
    // exposed for tests, DOM-independent
    renderStructuredBlock: renderStructuredBlock,
    isRealTextMode: isRealTextMode,
    renderAssistantProse: renderAssistantProse
  };
})();
