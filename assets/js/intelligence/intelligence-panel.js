/* PORTAL-NEXT V2 — Brabus Intelligence PERSISTENT PANEL (IA-3E).

   The "operating intelligence layer" experience (IA-3E Section 12/62):
   a shell-level launcher + drawer, mounted ONCE into #nxOverlayRoot by
   shell.js's boot() — NOT into #nxContentOutlet, which
   dispatchModule() rewrites on every route change. Because this
   module's own DOM is never touched by route dispatch, and its
   conversation lives in intelligence-state.js's own module-level
   store (not this file's render() closure), the conversation survives
   navigating between modules — the routed full page
   (assets/js/brabus-intelligence.js, #/brabus-intelligence) still
   exists unchanged alongside this, as a separate, already Human-
   approved experience; this file does not replace it, per Section 10
   "do not create duplicate Intelligence UI" this reuses its adapter
   and its two exported pure renderers (renderAssistantProse,
   renderStructuredBlock) instead of reimplementing Markdown/block
   rendering a second time.

   Transport is UNCHANGED: window.NX_BRABUS_INTELLIGENCE_ADAPTER (the
   same contract-tested adapter the routed page uses) is the only
   thing that ever calls fetch — this file never calls fetch/XHR
   itself, matching the existing module's own zero-business-logic
   discipline. */
(function () {
  'use strict';

  var A, P, S, C; // assigned in mount(): adapter, page (render helpers), state store, context provider

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var FIXTURE_LATENCY_MS = 150;

  /* ============================================================
     VISIBILITY — MASTER-only presentation (Section 15/18/19/49).
     Reads ONLY window.NX_AUTH_CORE's own existing, server-derived
     Auth Context (Object.freeze'd there, see auth-core.js) — never
     localStorage, DOM, a URL param, or anything this file invents.
     Non-visible means the launcher/drawer DOM does not exist at all
     (removed from the tree, not CSS-hidden) — a test can assert
     document.getElementById('baiLauncherRoot') === null. ============ */

  function isVisibleNow() {
    var AC = window.NX_AUTH_CORE;
    if (!AC) return false;
    var state = AC.getState();
    var STATES = AC.STATES;
    var authorized;
    // AUTH_NOT_CONFIGURED mirrors every other module's own convention
    // (auth-core.js's isModuleAuthorized) — no real Supabase Auth
    // wired on this host, so the pre-Auth-Foundation behavior applies.
    if (state === STATES.AUTH_NOT_CONFIGURED) authorized = true;
    else if (state === STATES.AUTHORIZED) {
      // IA-ENTRY-02: Human decision -- the Living Core is no longer
      // MASTER-exclusive. It now consumes the EXACT SAME canonical
      // authority the routed brabus-intelligence module/Landing card
      // already use (auth-core.js's own isModuleAuthorized(), never a
      // second, duplicated permission matrix, never a hardcoded
      // per-profile list) -- any profile authorized for the
      // brabus-intelligence module gets the launcher; anyone not
      // authorized gets it completely absent, matching this module's
      // real authMode (SEPARATE_AUTHORITY today: real enforcement
      // lives server-side, in the Edge Function itself, unchanged by
      // this Wave -- see this Wave's own report for the read-only
      // audit of that boundary).
      var entry = window.NX_REGISTRY && window.NX_REGISTRY.byId('brabus-intelligence');
      authorized = !!(entry && AC.isModuleAuthorized(entry));
    } else authorized = false;
    if (!authorized) return false;
    // Never stack the persistent launcher on top of the routed,
    // dedicated Intelligence page itself (#/brabus-intelligence) — a
    // second, redundant Intelligence surface on its own page would be
    // confusing UX, not a feature. UXCHAT1 (Human decision: ONE
    // Intelligence experience) made shell.js's own onRouteChange()
    // redirect away from this route before NX_INTELLIGENCE_CONTEXT's
    // route ever becomes 'brabus-intelligence' at all, so this specific
    // check is no longer reachable in normal navigation — kept anyway
    // as defense in depth (covers any future/direct call that still
    // sets this exact route value) rather than deleted, since removing
    // it would buy nothing and the legacy page itself was deliberately
    // left on disk, not deleted, this same Wave.
    if (C) {
      var ctxSnap = C.getSnapshot();
      if (ctxSnap && ctxSnap.route === 'brabus-intelligence') return false;
    }
    return true;
  }

  /* ============================================================
     RENDERING — reuses NX_BRABUS_INTELLIGENCE_PAGE's own exported
     renderAssistantProse/renderStructuredBlock (the exact same
     Markdown-safety and structured-block logic the routed, Human-
     approved page uses — never duplicated/reimplemented here) for
     every block type EXCEPT the compact `metrics` type, which gets
     its own presentation-only "evidence" treatment below (IA-3E.4).
     Every other type (comparison/ranking/operations/score_*) still
     goes through P.renderStructuredBlock completely unchanged.
     ============================================================ */

  /* ---------- Compact metrics evidence (IA-3E.4) ----------
     Human found the generic 2-column KPI grid still read as a "mini
     dashboard" even after IA-3E.3's alignment fix, with a redundant
     block heading ("GRUPO — MÊS ANTERIOR · mês anterior") repeating
     what the prose above it already said. This groups a metrics
     block's own items into two presentation lanes using metadata the
     block ALREADY carries on every item — item.format — never an
     invented business rule:
       - format === 'currency'  -> a "financial fact" (label above
         value, 2 per row) — the only values a Human actually reads
         as money and wants aligned/scannable;
       - anything else (int/percent/text/date/null) -> a compact,
         wrapping inline "strip" chip ("13 Vendas") — volume/share/
         count-shaped facts that read naturally as a phrase.
     This is why it generalizes to 2-6+ metrics of any real block
     without hardcoding this fixture's 5 specific keys: the grouping
     rule is the same regardless of which/how-many items a block has.
     No value is ever dropped — every item in block.items renders
     somewhere, either as a chip or as a fact. Only the `metrics` type
     is handled here (Section 15/35) — comparison/ranking/operations/
     score_* keep using the shared renderer's own presentation. */

  function isFinancialItem(item) {
    return !!item && item.format === 'currency';
  }

  function metricChipHtml(item) {
    var f = A.formatValue(item.value, item.format);
    return '<span class="baiMetricChip"><strong>' + esc(f.text) + '</strong> ' + esc(item.label) + '</span>';
  }

  function metricFactHtml(item) {
    var f = A.formatValue(item.value, item.format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiMetricFact"><p class="baiMetricFactLabel">' + esc(item.label) + '</p>' +
      '<p class="baiMetricFactValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function compactMetricsHtml(block) {
    var items = Array.isArray(block.items) ? block.items : [];
    var strip = items.filter(function (it) { return !isFinancialItem(it); });
    var facts = items.filter(isFinancialItem);
    // The block's own title/period is NOT dropped -- it is real
    // semantic context (e.g. which group/period this answer covers)
    // -- just not visually repeated when the prose already says it.
    // Screen-reader-only, same clip-rect technique as the role labels
    // (Section 5/19/13: "preserve semantic information for
    // accessibility... do not display redundant title/subtitle").
    var headingParts = [block.title, block.period_label].filter(function (v) { return !!v; });
    var headingSr = headingParts.length ? '<span class="baiSrOnly">' + esc(headingParts.join(' — ')) + '</span>' : '';
    var stripHtml = strip.length ? '<div class="baiMetricStrip">' + strip.map(metricChipHtml).join('') + '</div>' : '';
    var factsHtml = facts.length ? '<div class="baiMetricFacts">' + facts.map(metricFactHtml).join('') + '</div>' : '';
    if (!strip.length && !facts.length) {
      return '<div class="baiCompactMetrics">' + headingSr + '<p class="modMuted">Sem itens para exibir.</p></div>';
    }
    return '<div class="baiCompactMetrics">' + headingSr + stripHtml + factsHtml + '</div>';
  }

  /* ---------- Compact ranking cards (IA-3H.1C.3) ----------
     Human evidence ("Qual loja teve o melhor resultado?" -> "RANKING DE
     LOJAS POR RETORNO") found the shared `ranking` renderer's wide,
     multi-column <table> (brabus-intelligence.js's renderRanking, still
     used unmodified by the routed full-page module and by every OTHER
     structured-block type here) unreadable once compressed into this
     420px drawer -- numeric values sat under raw/near-raw column
     headers with no per-value label, exactly the "compressed desktop
     table" the brief calls out. This mirrors compactMetricsHtml's own
     precedent (a drawer-only presentation, built from the SAME shared,
     authoritative field metadata -- P.rankingFieldMeta -- never a
     second guessed label table) instead of reformatting the table:
     one labeled fact per value, so a single card is understandable on
     its own (Section 15's own bar: "screenshot one card and still
     understand what each number means"). Generic by construction --
     covers every real `ranking` payload (Resultado/Balão/Subsidiado/
     Coparticipado/Histórico all share this exact {dimension, metric,
     items:[{position,name,...}]} shape, already proven in intelligence-
     structured-block-test.py), not special-cased to stores or to this
     one screenshot's "retorno" metric. Only the `ranking` type is
     handled here -- score_ranking (a fixed, different item shape, not
     implicated by the Human's evidence) keeps using the shared
     renderer's own table, unchanged, per the same narrow-scope
     discipline IA-3E.4 already established for `metrics`. */

  function rankingItemKeys(item, primaryMetric) {
    var keys = Object.keys(item).filter(function (k) { return k !== 'position' && k !== 'name'; });
    // The block's own declared primary metric (e.g. "return" for a
    // retorno ranking) leads -- same ordering rule as the shared
    // table renderer, so which value is "the point" of this ranking
    // never disagrees between the two presentations.
    if (primaryMetric && keys.indexOf(primaryMetric) > 0) {
      keys.splice(keys.indexOf(primaryMetric), 1);
      keys.unshift(primaryMetric);
    }
    return keys;
  }

  function rankingMetricHtml(key, value, isPrimary) {
    var meta = P.rankingFieldMeta(key);
    var f = A.formatValue(value, meta.format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiRankMetric' + (isPrimary ? ' baiRankMetricPrimary' : '') + '">' +
      '<p class="baiRankMetricLabel">' + esc(meta.label) + '</p>' +
      '<p class="baiRankMetricValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function rankingCardHtml(item, idx, keys) {
    var pos = (item.position !== undefined && item.position !== null) ? item.position : idx + 1;
    var name = (item.name !== undefined && item.name !== null) ? String(item.name) : '';
    var metricsHtml = keys.map(function (k, ki) { return rankingMetricHtml(k, item[k], ki === 0); }).join('');
    return '<div class="baiRankCard">' +
      '<div class="baiRankCardHeader"><span class="baiRankPos">#' + esc(String(pos)) + '</span>' +
      '<span class="baiRankName">' + esc(name) + '</span></div>' +
      '<div class="baiRankMetrics">' + metricsHtml + '</div></div>';
  }

  function rankingCardsHtml(block) {
    var items = Array.isArray(block.items) ? block.items : [];
    var headingParts = [block.title, block.period_label].filter(function (v) { return !!v; });
    var headingHtml = headingParts.length
      ? '<h2 class="baiBlockTitle">' + esc(block.title || '') + '</h2>' + (block.period_label ? '<p class="baiBlockPeriod">' + esc(block.period_label) + '</p>' : '')
      : '';
    if (!items.length) {
      return '<div class="baiBlockPanel">' + headingHtml + '<p class="modMuted">Sem itens para exibir.</p></div>';
    }
    var keys = rankingItemKeys(items[0], block.metric);
    var listHtml = items.map(function (it, idx) { return rankingCardHtml(it, idx, keys); }).join('');
    return '<div class="baiBlockPanel">' + headingHtml + '<div class="baiRankList">' + listHtml + '</div></div>';
  }

  /* ---------- Financing plan cards (IA-3J.4C) ----------
     Real Human UAT ("continua confuso... precisamos separar em cards
     para entender do que se trata cada plano") traced to
     compactMetricsHtml above: it renders a metrics block's own
     title/period as screen-reader-ONLY (baiSrOnly), which is exactly
     right for a block whose title just repeats what the prose already
     said (e.g. "Resultado do Grupo — Mês Anterior") -- but wrong for a
     financing recommendation, where the title is the ONLY thing
     distinguishing "this is Balão" from "this is Linear". Human was
     left reading an anonymous metric grid and inferring the plan from
     field names alone.

     buildBalaoMetricsBlock/buildSimulationMetricsBlock (portal-ai-
     homolog, IA-3J.4C) now attach an explicit `financing_card`
     object to exactly these two block shapes (payment mode only) --
     {kind:"BALAO"|"LINEAR", term_months, monthly_payment, down_payment,
     financed_amount, balloons?, target_payment, target_distance} --
     presentation metadata only, never consumed by any calculation.
     This is a robust, non-title-parsing signal; every OTHER metrics
     block (Score, Comissões, Resultado, Coparticipado, etc.) has no
     financing_card and keeps using compactMetricsHtml completely
     unchanged below. */

  function hasFinancingCard(block) {
    return !!(block && block.type === 'metrics' && block.financing_card);
  }

  /* ---------- Required-down-payment "loose grid" -> proper cards (IA-UAT-05) ----------
     portal-ai-homolog's own buildSimulationMetricsBlock NEVER attaches
     a financing_card for mode="required_down_payment" (confirmed by
     direct reading, Secure repo, READ-ONLY this Wave) -- only
     "payment" mode does. IA-UAT-04's deterministic commercial selector
     dispatches every selected LINEAR proposal through exactly this
     required_down_payment shape, so each one arrived here as a flat
     metrics grid (Valor do Veículo + one Entrada/Parcela pair PER
     term), never a card -- the real cause of the Human's "alternativas
     Linear como campos soltos / repetição de Valor do Veículo" UAT
     finding. Backend is READ-ONLY this Wave (presentation only), so
     this is synthesized HERE from the exact, stable label template
     that backend function has used unchanged across every prior Wave
     (confirmed unique to this one code path) -- never a guess, and no
     financial NUMBER is recomputed, only regrouped + the one display-
     only subtraction (financed = veículo - entrada) done with numbers
     the backend already validated, the SAME arithmetic the backend's
     own "payment"-mode cards already do server-side. */
  var REQUIRED_DOWN_PAYMENT_ENTRADA_RE = /^Entrada necessária \((\d+)x\)$/;
  var REQUIRED_DOWN_PAYMENT_PARCELA_RE = /^Parcela obtida \((\d+)x\)$/;

  function isRequiredDownPaymentGridBlock(block) {
    return !!(block && block.type === 'metrics' && !block.financing_card && Array.isArray(block.items) &&
      block.items.some(function (i) { return REQUIRED_DOWN_PAYMENT_ENTRADA_RE.test(i.label); }));
  }

  function round2Display(n) {
    return Math.round(n * 100) / 100;
  }

  // One synthetic {type:'metrics', financing_card:{...}} per term found
  // in the grid -- a single required_down_payment block carries more
  // than one term only via the explicit "todas as opções" bypass
  // (Section 10 never dispatches more than one term per block through
  // the normal <=3-proposal selection) -- still renders each as its
  // own proper card instead of one shared grid either way.
  function syntheticFinancingCardsFromGrid(block) {
    var vehicleItem = block.items.filter(function (i) { return i.label === 'Valor do Veículo'; })[0];
    var targetItem = block.items.filter(function (i) { return i.label === 'Parcela Desejada'; })[0];
    var targetPayment = targetItem ? targetItem.value : null;
    var vehicleValue = vehicleItem ? vehicleItem.value : null;
    var cards = [];
    block.items.forEach(function (item, idx) {
      var m = REQUIRED_DOWN_PAYMENT_ENTRADA_RE.exec(item.label);
      if (!m) return;
      var term = Number(m[1]);
      var next = block.items[idx + 1];
      var pm = next && REQUIRED_DOWN_PAYMENT_PARCELA_RE.exec(next.label);
      var monthlyPayment = (pm && Number(pm[1]) === term) ? next.value : null;
      var downPayment = item.value;
      var financedAmount = (vehicleValue != null && downPayment != null) ? round2Display(vehicleValue - downPayment) : null;
      var distance = (targetPayment != null && monthlyPayment != null) ? round2Display(Math.abs(monthlyPayment - targetPayment)) : null;
      cards.push({
        type: 'metrics',
        financing_card: {
          kind: 'LINEAR', term_months: term, monthly_payment: monthlyPayment, down_payment: downPayment,
          financed_amount: financedAmount, target_payment: targetPayment, target_distance: distance
        }
      });
    });
    return cards;
  }

  function financingPlanFactHtml(label, value, format) {
    var f = A.formatValue(value, format);
    var titleAttr = f.title ? ' title="' + esc(f.title) + '"' : '';
    return '<div class="baiPlanFact"><p class="baiPlanFactLabel">' + esc(label) + '</p>' +
      '<p class="baiPlanFactValue"' + titleAttr + '>' + esc(f.text) + '</p></div>';
  }

  function financingPlanCardHtml(block, isPrimary) {
    var fc = block.financing_card;
    var kindLabel = fc.kind === 'BALAO' ? 'Balão' : 'Linear';
    var cardClass = 'baiPlanCard' + (isPrimary ? ' baiPlanCardPrimary' : ' baiPlanCardSecondary');
    var badgeHtml = isPrimary ? '<p class="baiPlanCardBadge">Recomendado</p>' : '';
    var heroValue = A.formatValue(fc.monthly_payment, 'currency');
    var headerHtml =
      '<div class="baiPlanCardHeader">' + badgeHtml +
      '<p class="baiPlanCardKind">' + esc(kindLabel) + ' · ' + esc(String(fc.term_months)) + ' meses</p>' +
      '<p class="baiPlanCardHero">' + esc(heroValue.text) + '<span class="baiPlanCardHeroUnit"> /mês</span></p>' +
      '</div>';

    var facts = [];
    if (fc.down_payment != null) facts.push(financingPlanFactHtml('Entrada', fc.down_payment, 'currency'));
    if (fc.financed_amount != null) facts.push(financingPlanFactHtml('Financiado', fc.financed_amount, 'currency'));
    var factsHtml = facts.length ? '<div class="baiPlanCardFacts">' + facts.join('') + '</div>' : '';

    var balloonsHtml = '';
    if (Array.isArray(fc.balloons) && fc.balloons.length) {
      var balloonItems = fc.balloons.map(function (b, i) {
        return financingPlanFactHtml('Balão ' + (i + 1) + ' · mês ' + b.month, b.value, 'currency');
      }).join('');
      balloonsHtml = '<div class="baiPlanCardFacts baiPlanCardBalloons">' + balloonItems + '</div>';
    }

    // IA-UAT-05, Section 6 -- PARCELA DESEJADA and PARCELA OBTIDA are
    // never shown as two separate facts (the hero above already IS the
    // obtained payment); when they are exactly equal (distance rounds
    // to R$0,00) no comparison line is shown at all -- only a genuine,
    // material difference earns one, and even then only the short
    // "R$X acima/abaixo da meta" form, never a redundant restatement of
    // the target value the hero already conveys.
    var targetHtml = '';
    if (fc.target_payment != null && fc.target_distance != null) {
      var roundedDistance = round2Display(fc.target_distance);
      if (roundedDistance > 0) {
        var distFmt = A.formatValue(roundedDistance, 'currency');
        var direction = fc.monthly_payment <= fc.target_payment ? 'abaixo da meta' : 'acima da meta';
        targetHtml = '<p class="baiPlanCardTarget">' + esc(distFmt.text) + ' ' + esc(direction) + '</p>';
      }
    }

    return '<div class="' + cardClass + '">' + headerHtml + factsHtml + balloonsHtml + targetHtml + '</div>';
  }

  /* ---------- Settlement (Antecipação) and Cash Conversion cards (IA-3K.1) ----------
     Real conversational UAT (UAT-VOICE-01A/01B) found both domains'
     calculation/speed approved but their presentation "visualmente
     cru e repetitivo" -- the shared compactMetricsHtml grid above,
     same complaint the financing-plan cards (IA-3J.4C) already fixed
     for Balão/Linear. `settlement_card`/`cash_conversion_card`
     (portal-ai-homolog, IA-3K.1) are the SAME contract class as
     `financing_card` -- presentation-only metadata, never consumed by
     any calculation -- so these reuse the EXACT same .baiPlanCard*
     classes already defined for the financing cards (zero new CSS,
     per this Wave's own explicit "não criar uma nova linguagem
     visual" instruction) rather than inventing a second visual
     language. Every OTHER metrics block (Score, Comissões, Resultado,
     Taxa Implícita, etc.) has neither field and keeps using
     compactMetricsHtml completely unchanged. */

  function hasSettlementCard(block) {
    return !!(block && block.type === 'metrics' && block.settlement_card);
  }

  function hasCashConversionCard(block) {
    return !!(block && block.type === 'metrics' && block.cash_conversion_card);
  }

  // Converts a decimal fraction (e.g. 0.0112) to a rounded percentage
  // number (1.12) for A.formatValue(..., 'percent'), which -- same
  // convention as every other percent field this file already reads
  // from portal-ai-homolog (down_payment_percent, break_even_rate in
  // the existing metrics item builder) -- expects percentage points,
  // never a raw fraction, and a plain `*100` alone reintroduces
  // binary floating-point noise (0.0112*100 === 1.1199999999999999).
  function fracToPercent(frac) {
    return Math.round(frac * 100 * 100) / 100;
  }

  function settlementCardHtml(block) {
    var sc = block.settlement_card;
    var heroValue = A.formatValue(sc.settlement_amount, 'currency');
    var dateValue = A.formatValue(sc.settlement_date, 'date');
    var headerHtml =
      '<div class="baiPlanCardHeader">' +
      '<p class="baiPlanCardKind">Quitação Antecipada</p>' +
      '<p class="baiPlanCardHero">' + esc(heroValue.text) + '</p>' +
      '<p class="baiPlanCardHeroUnit">Valor estimado para quitação em ' + esc(dateValue.text) + '</p>' +
      '</div>';

    var facts = [
      financingPlanFactHtml('Valor nominal restante', sc.gross_total, 'currency'),
      financingPlanFactHtml('Desconto estimado', sc.discount_total, 'currency'),
      financingPlanFactHtml('Economia', sc.discount_percent_of_gross, 'percent')
    ].join('');
    var factsHtml = '<div class="baiPlanCardFacts">' + facts + '</div>';

    var secondaryParts = [esc(String(sc.installments_considered)) + ' pagamentos restantes'];
    if (Array.isArray(sc.balloons)) {
      sc.balloons.forEach(function (b) {
        secondaryParts.push('Balão de ' + esc(A.formatValue(b.value, 'currency').text) + ' na parcela ' + esc(String(b.installment_number)));
      });
    }
    var secondaryHtml = '<div class="baiPlanCardBalloons"><p class="baiPlanFactValue">' + secondaryParts.join(' · ') + '</p></div>';

    var noteParts = [];
    if (sc.first_due_date_assumed) {
      noteParts.push('Primeira parcela assumida em ' + esc(A.formatValue(sc.first_due_date, 'date').text) + ' (premissa: hoje + 30 dias).');
    }
    noteParts.push('Estimativa comercial. O valor oficial para quitação é definido pela instituição financeira.');
    var noteHtml = '<p class="baiPlanCardTarget">' + noteParts.join(' ') + '</p>';

    return '<div class="baiPlanCardGroup"><div class="baiPlanCard">' + headerHtml + factsHtml + secondaryHtml + noteHtml + '</div></div>';
  }

  function cashConversionCardHtml(block) {
    var cc = block.cash_conversion_card;
    var headerHtml = '<div class="baiPlanCardHeader"><p class="baiPlanCardKind">Cash Conversion</p></div>';

    var scenarioFacts = [
      financingPlanFactHtml('Capital preservado', cc.capital, 'currency'),
      financingPlanFactHtml('Financiamento (' + cc.term_months + 'x)', cc.monthly_payment, 'currency'),
      financingPlanFactHtml('Taxa considerada (a.m.)', fracToPercent(cc.application_rate), 'percent')
    ];
    if (cc.break_even_rate != null) {
      scenarioFacts.push(financingPlanFactHtml('Taxa de equilíbrio (a.m.)', fracToPercent(cc.break_even_rate), 'percent'));
    }
    var scenarioHtml = '<div class="baiPlanCardFacts">' + scenarioFacts.join('') + '</div>';

    var resultLabel = cc.classification === 'FINANCIAR' ? 'Vantagem matemática: Financiar'
      : cc.classification === 'UTILIZAR' ? 'Vantagem matemática: À Vista'
      : 'Resultado matemático: Equivalente';
    var diffFmt = A.formatValue(Math.abs(cc.projected_difference), 'currency');
    var resultHtml = '<div class="baiPlanCardBalloons">' +
      '<p class="baiPlanCardKind">' + esc(resultLabel) + '</p>' +
      (cc.classification !== 'EQUIVALENTE' ? '<p class="baiPlanCardHero">' + esc(diffFmt.text) + '</p>' : '') +
      '</div>';

    var capitalFmt = A.formatValue(cc.capital, 'currency');
    var strategyHtml = '<p class="baiPlanCardTarget">Financiar mantém ' + esc(capitalFmt.text) + ' disponíveis para liquidez/investimento.</p>';

    return '<div class="baiPlanCardGroup"><div class="baiPlanCard">' + headerHtml + scenarioHtml + resultHtml + strategyHtml + '</div></div>';
  }

  /* Groups ALL financing-plan blocks in one message's blocks[] and
     decides which is visually primary -- purely by comparing
     target_distance (the exact "closest to the target the Human
     stated" semantic IA-3J.4A already made authoritative backend-side,
     applied here across independent tool calls/blocks). Falls back to
     "first one in the array" only when no block carries a usable
     distance (e.g. no target_payment was ever given) -- reading order,
     never an invented ranking. Every non-financing block in the same
     message renders through the existing, unmodified renderOneBlock. */
  function renderBlocksHtml(blocks) {
    // IA-UAT-05 -- expand any required-down-payment "loose grid" block
    // into its own real financing card(s) BEFORE grouping, so Text and
    // Voice render the exact SAME cards regardless of which backend
    // shape (payment vs required_down_payment) produced the proposal.
    // This never mutates the canonical message/blocks array
    // (S.getConversation()'s own state) -- `expanded` is a fresh,
    // render-local array built fresh on every call.
    var expanded = [];
    blocks.forEach(function (b) {
      if (isRequiredDownPaymentGridBlock(b)) expanded.push.apply(expanded, syntheticFinancingCardsFromGrid(b));
      else expanded.push(b);
    });

    var financing = expanded.filter(hasFinancingCard);
    if (!financing.length) return expanded.map(renderOneBlock).join('');

    // IA-UAT-05 -- array order already encodes the backend's own
    // RECOMENDADO-first selection (IA-UAT-04's selectCommercialProposals
    // pushes proposals in exactly that order, and portal-ai-homolog's
    // own dispatch loop pushes their blocks in that same order) --
    // target_distance now only overrides it when a LATER candidate is
    // MEANINGFULLY closer (>R$1,00 margin). The new <=3-proposal flow
    // computes every proposal's own entrada independently via a R$0,01-
    // tolerance bisection search, so all of them sit within a few cents
    // of the target and array order correctly wins; a real, material
    // gap (e.g. the pre-existing financing-plan-cards fixture's own
    // R$33,06 vs R$1.184,38) still overrides it exactly as before --
    // the OLDER engine-first flow's already-approved behavior is
    // unchanged.
    var primary = financing[0];
    var haveDistances = financing.every(function (b) { return b.financing_card.target_distance != null; });
    if (haveDistances) {
      primary = financing.reduce(function (best, b) {
        return (b.financing_card.target_distance < best.financing_card.target_distance - 1) ? b : best;
      });
    }

    var groupHtml = '<div class="baiPlanCardGroup">' +
      financing.map(function (b) { return financingPlanCardHtml(b, b === primary); }).join('') +
      '</div>';
    var otherHtml = expanded.filter(function (b) { return !hasFinancingCard(b); }).map(renderOneBlock).join('');
    return groupHtml + otherHtml;
  }

  function renderOneBlock(block) {
    if (!block) return '';
    if (hasSettlementCard(block)) return settlementCardHtml(block);
    if (hasCashConversionCard(block)) return cashConversionCardHtml(block);
    if (block.type === 'metrics') return compactMetricsHtml(block);
    if (block.type === 'ranking') return rankingCardsHtml(block);
    return P.renderStructuredBlock(block);
  }

  function messageHtml(msg) {
    var isUser = msg.role === 'user';
    var roleClass = isUser ? 'baiMessageUser' : 'baiMessageAssistant';
    var roleLabel = isUser ? 'Você' : 'Brabus Intelligence';
    var labelHtml = '<span class="baiRoleLabel">' + esc(roleLabel) + '</span>';

    if (isUser || msg.isError) {
      // User turns and error turns keep the plain bubble treatment --
      // there is no metrics/evidence to cohere them with.
      var plainClass = 'baiBubble' + (msg.isError ? ' baiBubbleError' : '');
      return '<div class="baiMessage ' + roleClass + '">' + labelHtml +
        '<div class="' + plainClass + '">' + esc(msg.content) + '</div></div>';
    }

    // A real assistant answer (IA-3E.3 Section 11 -- conversation
    // first, data second): prose renders DIRECTLY on the conversation
    // surface, no card. Optional structured facts follow as a subtly
    // divided secondary section (intelligence.css's .baiAnswerMetrics),
    // never a second competing bordered box. The structured-block
    // markup itself (P.renderStructuredBlock) is 100% the shared,
    // unmodified renderer -- only the wrapper it sits in here differs.
    var proseHtml = '<div class="baiAnswerProse baiBubbleMd">' + P.renderAssistantProse(msg.content) + '</div>';
    var metricsHtml = '';
    if (Array.isArray(msg.blocks) && msg.blocks.length) {
      metricsHtml = '<div class="baiAnswerMetrics">' + renderBlocksHtml(msg.blocks) + '</div>';
    }
    return '<div class="baiMessage ' + roleClass + '">' + labelHtml + proseHtml + metricsHtml + '</div>';
  }

  function loadingHtml() {
    return '<div class="baiMessage baiMessageAssistant"><div class="baiBubble baiBubbleLoading modLoadingState">' +
      '<span class="modLoadingDot" aria-hidden="true"></span>Analisando os dados do Portal…</div></div>';
  }

  /* ============================================================
     EMPTY STATE (IA-3I, Section 11/12) -- intentional composition
     replacing the old blank drawer. Suggestions are truthful, real
     fixture-scenario matches (brabus-intelligence.adapter.js's own
     SCENARIOS regexes) -- clicking one only fills+focuses the input
     (never auto-sends), so the Human always keeps the final "send"
     decision, and a real backend answer is never implied for a
     question this build cannot actually resolve. ============ */
  // V2-UAT-02 (Section A): the old, permanent 3-item list was 100%
  // managerial/gestão -- it never communicated the Intelligence's own
  // commercial/financing/antecipação/Cash Conversion capability. Kept
  // as a POOL grouped by real use case (never inventing a new
  // question the adapter can't actually answer -- same fixture-
  // scenario-truthful principle as before), 3 chips visible at a time,
  // rotating which category is temporarily omitted so gestão never
  // disappears from the pool, it's just not in every single set.
  var SUGGESTION_CATEGORIES = [
    { key: 'financiamento', items: [
      'Simule uma parcela para este cliente',
      'Quanto preciso de entrada para chegar nesta parcela?',
      'Encontre uma opção Linear e Balão'
    ] },
    { key: 'antecipacao', items: [
      'Calcule a antecipação deste contrato'
    ] },
    { key: 'cash_conversion', items: [
      'Vale preservar o capital e financiar?',
      'Faça um Cash Conversion deste cenário'
    ] },
    { key: 'gestao', items: [
      'Qual foi o resultado do mês passado?',
      'Como está o score do vendedor?',
      'Compare o resultado entre as lojas'
    ] }
  ];

  // Deterministic (never Math.random -- reproducible in tests, no
  // continuous timer/auto-play): each "Nova conversa" advances this by
  // one, rotating which 3-of-4 categories show and which item inside
  // each shows. suggestionRotation=0 (every fresh page load) always
  // yields the brief's own reference set (financiamento/antecipação/
  // cash), so the very first thing a Human sees already demonstrates
  // the commercial capability, not just gestão.
  var suggestionRotation = 0;

  function pickSuggestions() {
    var n = SUGGESTION_CATEGORIES.length;
    var order = [];
    for (var i = 0; i < n; i++) order.push((suggestionRotation + i) % n);
    return order.slice(0, 3).map(function (ci) {
      var cat = SUGGESTION_CATEGORIES[ci];
      return cat.items[suggestionRotation % cat.items.length];
    });
  }

  function suggestionChipsHtml(list) {
    return list.map(function (s) {
      return '<button type="button" class="baiSuggestionChip">' + esc(s) + '</button>';
    }).join('');
  }

  // Re-renders just the suggestion chips (not the whole empty state) --
  // #baiPanelSuggestions keeps its one delegated click listener
  // (wireSuggestions(), untouched below), so regenerating its children
  // needs no re-wiring.
  function renderSuggestions() {
    var box = document.getElementById('baiPanelSuggestions');
    if (!box) return;
    box.innerHTML = suggestionChipsHtml(pickSuggestions());
  }

  function emptyStateHtml() {
    var suggestionsHtml = suggestionChipsHtml(pickSuggestions());
    return '<div class="baiPanelEmptyState" id="baiPanelEmptyState">' +
      '<div class="baiEmptyMark" aria-hidden="true">' +
      '<svg viewBox="0 0 48 48" width="40" height="40" fill="none">' +
      '<path d="M24 6.8c3.8.4 7.8 2 10.6 5.2 3.2 3.6 4.6 8.8 3.4 13.8-1.2 5-5.2 9.4-10.2 11-5 1.6-11 .4-14.8-3.4-3.8-3.8-5.4-9.8-3.8-15 1.6-5.2 6-9.4 11.2-11 1.2-.4 2.4-.6 3.6-.6z" stroke="currentColor" stroke-width="1.4"/>' +
      '<path d="M18.6 30c1.8 1.6 4.6 1.8 6.8.8" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>' +
      '</svg></div>' +
      '<h3 class="baiEmptyTitle">Como posso ajudar?</h3>' +
      '<p class="baiEmptySubtitle">Pergunte sobre financiamento, resultado ou score do Portal F&amp;I.</p>' +
      '<div class="baiSuggestions" id="baiPanelSuggestions">' + suggestionsHtml + '</div>' +
      '</div>';
  }

  // IA-3I.1-001 (Section 12/13): root cause of "suggestions don't do
  // anything" -- wireSuggestions() was written but never CALLED from
  // buildPanelDom() (see the fix at that call site below), so the real
  // DOM buttons existed with zero listener attached. Fixed AND
  // upgraded per the Human's explicit product decision: one click now
  // submits immediately through submitText() -- the SAME function
  // wireComposer()'s Send/Enter path uses -- never a second request
  // implementation. A real <button> already gives Enter/Space
  // activation for free (both fire a native `click` the delegated
  // listener below catches identically to a mouse click).
  function wireSuggestions() {
    var box = document.getElementById('baiPanelSuggestions');
    if (!box) return;
    box.addEventListener('click', function (e) {
      var btn = e.target.closest('.baiSuggestionChip');
      if (!btn) return;
      submitText(btn.textContent);
    });
  }

  var NEAR_BOTTOM_THRESHOLD_PX = 80;

  function renderConversation() {
    var el = document.getElementById('baiPanelConversation');
    if (!el) return;
    // .baiPanelBody is the real `overflow-y:auto` container (see the
    // scroll-target bugfix below) -- read its scroll position BEFORE
    // re-rendering, so a Human who deliberately scrolled up to reread
    // an earlier turn isn't yanked back down by a new message arriving
    // (IA-3E.3 Section 26, a soft, deterministic improvement over the
    // IA-3E.2-disclosed D1 limitation): only auto-scroll if they were
    // already near the bottom.
    var scrollHost = el.closest('.baiPanelBody') || el;
    var wasNearBottom = (scrollHost.scrollHeight - scrollHost.scrollTop - scrollHost.clientHeight) <= NEAR_BOTTOM_THRESHOLD_PX;

    var snap = S.getSnapshot();
    var busy = snap.textState === S.TEXT_STATES.SENDING || snap.textState === S.TEXT_STATES.THINKING;
    var isEmpty = snap.conversation.length === 0 && !busy;
    // IA-3I: the intentional empty-state composition (Section 11) --
    // toggled here, alongside the conversation render, so it always
    // matches the SAME real conversation-emptiness signal the
    // conversation view itself already uses (never a second guess).
    var emptyStateEl = document.getElementById('baiPanelEmptyState');
    if (emptyStateEl) emptyStateEl.hidden = !isEmpty;
    if (isEmpty) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = snap.conversation.map(messageHtml).join('') + (busy ? loadingHtml() : '');
    // BUGFIX (found live during IA-3E.2's own long-conversation check):
    // #baiPanelConversation itself never overflows -- it grows freely
    // inside .baiPanelBody. Setting scrollTop on the wrong (non-
    // scrolling) element silently did nothing -- the newest message
    // was reachable only by a human manually scrolling. Scroll the
    // real container instead, and only when appropriate (above).
    if (wasNearBottom) scrollHost.scrollTop = scrollHost.scrollHeight;
  }

  function updateContextChip() {
    var chip = document.getElementById('baiPanelContextChip');
    if (!chip) return;
    var desc = C.describe();
    if (desc) {
      chip.hidden = false;
      // IA-3I: "Contexto · X" replaces the more technical-reading
      // "Analisando: X" (Section 10) -- same underlying, real, module-
      // published context string (esc()'d, never sent anywhere), only
      // the wording changed.
      chip.innerHTML = '<span class="baiPanelContextDot" aria-hidden="true"></span>' +
        '<span class="baiPanelContextText">Contexto · ' + esc(desc) + '</span>';
    } else {
      chip.hidden = true;
      chip.innerHTML = '';
    }
  }

  /* ============================================================
     STICKY STATUS (DISABLED/SESSION_EXPIRED/FORBIDDEN) — Section 16/
     40/41/50/51/52: a clean, non-technical status line, composer
     disabled while stuck, NEVER an automatic retry/timer — the only
     way out is a deliberate human action ("Nova conversa" or a fresh
     send once the underlying condition has genuinely changed).
     ============================================================ */

  function statusLineFor(state) {
    if (state === S.TEXT_STATES.DISABLED) return 'Brabus Intelligence está temporariamente indisponível.';
    if (state === S.TEXT_STATES.SESSION_EXPIRED) return 'Sessão expirada — entre novamente para continuar.';
    if (state === S.TEXT_STATES.FORBIDDEN) return 'Este recurso não está disponível para o seu perfil.';
    return '';
  }

  function setComposerEnabled(enabled) {
    var input = document.getElementById('baiPanelInput');
    if (input) input.disabled = !enabled;
    // IA-3I: Send's own disabled state is now computed by
    // updateSendButtonState() (locked-state OR empty-text, Section 17)
    // -- a single authoritative place, never two writers disagreeing.
    updateSendButtonState();
  }

  function applyPersistentState(state) {
    var line = document.getElementById('baiPanelStatusLine');
    var msg = statusLineFor(state);
    if (line) {
      if (msg) { line.hidden = false; line.textContent = msg; }
      else { line.hidden = true; line.textContent = ''; }
    }
    var locked = state === S.TEXT_STATES.DISABLED || state === S.TEXT_STATES.SESSION_EXPIRED ||
      state === S.TEXT_STATES.FORBIDDEN || state === S.TEXT_STATES.SENDING || state === S.TEXT_STATES.THINKING;
    setComposerEnabled(!locked);
  }

  /* ============================================================
     SEND FLOW — mirrors brabus-intelligence.js's own applyResult/
     handleSendFixture/handleSendRealText contract-for-contract (same
     adapter calls, same error-status mapping), rewritten to drive the
     explicit TEXT_STATES machine instead of two closure booleans.
     ============================================================ */

  // IA-3G.5A -- dev-only console diagnostic (never rendered, never
  // part of the approved drawer UI -- Section 23's own "console;
  // dedicated dev object" allowance). Only fires when `result._devTiming`
  // is present, which only ever happens for a real_text response that
  // carried the homolog-only `_homolog_edge_timing` field -- absent for
  // fixture mode, absent for any error short-circuited before fetch,
  // and (by construction, since this repo never modified the real
  // production Edge Function) absent for production. Logs numbers,
  // a random correlation id, and an opaque instance id only -- no
  // prompt, no reply text, no business data.
  function logDevTiming(devTiming, renderCompleteAt) {
    if (!devTiming) return;
    var out = {};
    for (var k in devTiming) out[k] = devTiming[k];
    if (devTiming.client_receive_at) out.render_ms = renderCompleteAt - devTiming.client_receive_at;
    if (devTiming.ui_submit_at) out.total_ui_ms = renderCompleteAt - devTiming.ui_submit_at;
    // eslint-disable-next-line no-console
    console.log('[bai-timing]', out);
    // LATENCY-2C -- the SAME already-safe object handed to the
    // homolog/dev-only in-memory diagnostic collector, so a Human
    // sample survives this console line without needing DevTools.
    if (window.NX_INTELLIGENCE_LATENCY_DIAG) window.NX_INTELLIGENCE_LATENCY_DIAG.capture(out, 'text');
  }

  function applyResult(result) {
    if (result.error) {
      var status = result.error.status;
      S.pushMessage({ role: 'assistant', content: result.error.message, blocks: null, isError: true });
      if (status === 503) S.setTextState(S.TEXT_STATES.DISABLED);
      else if (status === 401) S.setTextState(S.TEXT_STATES.SESSION_EXPIRED);
      else if (status === 403) S.setTextState(S.TEXT_STATES.FORBIDDEN);
      else S.setTextState(S.TEXT_STATES.ERROR);
      applyPersistentState(S.getTextState());
      renderConversation();
      logDevTiming(result._devTiming, Date.now());
      return;
    }
    var normalized = result.response;
    if (normalized.scenario_reset) S.spliceFromLastUser();
    S.pushMessage({ role: 'assistant', content: normalized.reply, blocks: normalized.blocks, isError: false });
    // COMPLETE is a momentary signal (Section 13), not a resting
    // composer-disabled state -- settle to OPEN_IDLE right after.
    S.setTextState(S.TEXT_STATES.COMPLETE);
    renderConversation();
    logDevTiming(result._devTiming, Date.now());
    S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
  }

  // SESSIONSEC1 -- Section 14 race protection. `gen` is the identity
  // generation (NX_INTELLIGENCE_STATE.getGeneration()) captured at the
  // moment a send began; if it no longer matches by the time a result
  // comes back, the authenticated identity changed while this request
  // was in flight (e.g. USER A sent, then logged out, then USER B
  // logged in, all before USER A's response arrived) -- the result is
  // silently dropped, never rendered and never allowed to influence
  // this (now different-owner) conversation. Every async path that can
  // outlive an identity change must go through this, not call
  // applyResult directly.
  function applyResultIfCurrent(gen, result) {
    if (S.getGeneration() !== gen) return;
    applyResult(result);
  }

  function handleSendFixture(text, priorTurns, gen) {
    A.createRequest(text, priorTurns); // models the contract shape even though nothing is sent (Gate 15/32, matching the routed page)
    setTimeout(function () {
      if (S.getGeneration() !== gen) return;
      var scenario = A.resolveFixtureScenario(text);
      if (!scenario) {
        S.pushMessage({ role: 'assistant', isError: false, blocks: null, content: 'Não tenho um cenário de teste para essa pergunta neste protótipo local — isso não indica uma falha do contrato, apenas que este fixture não cobre esta frase.' });
        S.setTextState(S.TEXT_STATES.OPEN_IDLE);
        applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
        renderConversation();
        return;
      }
      if (scenario.error) { applyResultIfCurrent(gen, { error: scenario.error }); return; }
      applyResultIfCurrent(gen, { response: A.normalizeResponse(scenario.response) });
    }, FIXTURE_LATENCY_MS);
  }

  // IA-3H.1C.4 (D14) -- proactive Text surface gate, checked fresh
  // before every real send, never cached across sends (an admin could
  // toggle the flag mid-session; this endpoint is already read fresh on
  // every request server-side too -- operational_current_scope() has
  // the same "no caching" discipline). Reuses the EXISTING, already-
  // governed, already-authenticated-general-user RPC
  // (operational_portal_config(), via window.NX_MASTER_CONFIG_PROVIDER
  // -- the same provider Painel Master's own Configurações page already
  // calls) -- no new RPC, no new endpoint, no new authorization
  // subsystem. Resolves `false` (fail-closed) on any error/malformed
  // response/missing row, the identical rule the server's own
  // findFlag() uses. This is the Text UI's OWN decision about whether
  // to even attempt a send -- it does not touch, weaken, or duplicate
  // the server's own independent enforcement of the same flag (see
  // portal-ai-homolog's surface-aware intelligenceEnabled derivation),
  // and it has zero effect on intelligence-voice.js's bridge, which
  // never calls this function.
  function isTextSurfaceEnabled() {
    if (!window.NX_MASTER_CONFIG_PROVIDER || typeof window.NX_MASTER_CONFIG_PROVIDER.readConfig !== 'function') {
      return Promise.resolve(false);
    }
    return window.NX_MASTER_CONFIG_PROVIDER.readConfig().then(function (rows) {
      var row = Array.isArray(rows) ? rows.filter(function (r) { return r && r.chave === 'ia_texto_habilitada'; })[0] : null;
      return !!row && String(row.valor || '').trim().toLowerCase() === 'true';
    }, function () {
      return false;
    });
  }

  function handleSendRealText(text, priorTurns, uiSubmitAt, gen) {
    if (!window.NX_AUTH || typeof window.NX_AUTH.getAccessToken !== 'function') {
      applyResultIfCurrent(gen, { error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      return;
    }
    // IA-3H.1C.3 -- sanitized turn sequence number (a plain count of the
    // Human's own prior questions in this conversation, never content),
    // carried through to _devTiming so a multi-turn latency pattern is
    // readable directly off the existing [bai-timing] log line.
    var turnIndex = priorTurns.filter(function (m) { return m.role === 'user'; }).length + 1;
    isTextSurfaceEnabled().then(function (enabled) {
      if (S.getGeneration() !== gen) return;
      if (!enabled) {
        // Same error shape/status the server itself would return for
        // this exact condition (errorMessageForStatus(503) in the
        // adapter) -- applyResult()'s own existing 503 handling
        // (TEXT_STATES.DISABLED, composer disabled, no retry loop)
        // applies unchanged. No network request was made: sendRealText
        // is never called on this path.
        applyResultIfCurrent(gen, { error: { status: 503, message: 'Brabus Intelligence está temporariamente indisponível.' } });
        return;
      }
      // IA-3G.5A -- getAccessToken() calls the real Supabase SDK's own
      // auth.getSession(), which can silently perform a real network
      // token-refresh call before resolving (supabase-js's own documented
      // behavior when the current access token is expired/near-expiry) --
      // a plausible pre-fetch delay entirely invisible to Edge-side
      // instrumentation. Measured here, separately from the fetch() that
      // follows, specifically to test that hypothesis with real numbers.
      var t_getToken = Date.now();
      window.NX_AUTH.getAccessToken().then(function (token) {
        var getTokenMs = Date.now() - t_getToken;
        if (S.getGeneration() !== gen) return;
        if (!token) { applyResultIfCurrent(gen, { error: { status: 401, message: 'Sessão expirada — entre novamente.' } }); return; }
        return A.sendRealText(text, priorTurns, token, { uiSubmitAt: uiSubmitAt, getTokenMs: getTokenMs, turnIndex: turnIndex }).then(function (result) {
          applyResultIfCurrent(gen, result);
        });
      }).catch(function () {
        applyResultIfCurrent(gen, { error: { status: 0, message: 'Não foi possível concluir a análise agora. Tente novamente.' } });
      });
    });
  }

  function handleSend(text) {
    if (!text) return;
    // IA-3G.5A -- captured as the very first line, before any state
    // change or DOM work, so it marks the true moment the Human's
    // action was received by this code.
    var uiSubmitAt = Date.now();
    var st = S.getTextState();
    if (st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING) return;
    // SESSIONSEC1 -- captured BEFORE any async work starts, per this
    // send's own identity. Threaded through to every deferred callback
    // below (handleSendRealText/handleSendFixture and everything they
    // call) so a result that comes back after the authenticated
    // identity has since changed is recognized and dropped.
    var gen = S.getGeneration();
    S.pushMessage({ role: 'user', content: text, blocks: null, isError: false });
    S.setTextState(S.TEXT_STATES.SENDING);
    applyPersistentState(S.TEXT_STATES.SENDING);
    renderConversation();
    var priorTurns = S.getConversation().slice(0, -1);
    S.setTextState(S.TEXT_STATES.THINKING);
    applyPersistentState(S.TEXT_STATES.THINKING);
    // SEC-1C.3 -- checked first, before either real path: see
    // isHomologMisconfigured()'s own comment (brabus-intelligence.js).
    // applyResult() already renders every error as a normal
    // conversation bubble (adapter's own established contract) -- no
    // new rendering path introduced here.
    if (P.isHomologMisconfigured && P.isHomologMisconfigured()) {
      applyResult({ error: { status: 0, message: 'Brabus Intelligence indisponível — configuração de homologação ausente.' } });
    } else if (P.isRealTextMode()) handleSendRealText(text, priorTurns, uiSubmitAt, gen);
    else handleSendFixture(text, priorTurns, gen);
  }

  function onNovaConversa() {
    var st = S.getTextState();
    if (st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING) return;
    S.resetConversation();
    S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.TEXT_STATES.OPEN_IDLE);
    // V2-UAT-02 (Section A): the one discreet moment the suggestion set
    // is allowed to change -- a deliberate Human action, never a
    // continuous auto-rotating carousel.
    suggestionRotation++;
    renderSuggestions();
    renderConversation();
    var input = document.getElementById('baiPanelInput');
    if (input) { input.value = ''; autoGrowComposer(input); input.focus(); }
  }

  /* ============================================================
     COMPOSER — auto-grow (IA-3E.2 Section 14, high priority). A
     static `rows="1"` + fixed CSS height was the exact cause of the
     Human-reported white native scrollbar: any wrapped second line
     immediately overflowed a textarea whose height never changed,
     forcing the browser's own default scrollbar UI to appear. This
     resizes the element itself (bounded [MIN,MAX]) so the browser's
     internal scrollbar only ever appears once content genuinely
     exceeds MAX_COMPOSER_HEIGHT — and even then it is CSS-styled
     (intelligence.css's scrollbar-width/::-webkit-scrollbar rules),
     never the stark default.
     ============================================================ */

  var MIN_COMPOSER_HEIGHT = 40;
  var MAX_COMPOSER_HEIGHT = 132; // must match intelligence.css's .baiComposerInput max-height

  function autoGrowComposer(el) {
    el.style.height = 'auto';
    var next = Math.min(Math.max(el.scrollHeight, MIN_COMPOSER_HEIGHT), MAX_COMPOSER_HEIGHT);
    el.style.height = next + 'px';
  }

  // IA-3I (Section 17) -- Send's own visual authority now tracks
  // whether there is real text to send, layered on TOP of the
  // existing locked/busy disabling (applyPersistentState's own
  // setComposerEnabled) -- this only ADDS an emptiness condition, it
  // never re-enables a genuinely locked composer. A dedicated CSS
  // class (.baiSendBtnActive) drives the red/authoritative look;
  // `disabled` itself remains the real, authoritative, assistive-
  // tech-visible state (Section 18).
  function updateSendButtonState() {
    var input = document.getElementById('baiPanelInput');
    var btn = document.getElementById('baiPanelSendBtn');
    if (!input || !btn) return;
    var hasText = !!(input.value || '').trim();
    var st = S ? S.getTextState() : null;
    var isLocked = st === S.TEXT_STATES.DISABLED || st === S.TEXT_STATES.SESSION_EXPIRED ||
      st === S.TEXT_STATES.FORBIDDEN || st === S.TEXT_STATES.SENDING || st === S.TEXT_STATES.THINKING;
    btn.disabled = isLocked || !hasText;
    btn.classList.toggle('baiSendBtnActive', hasText && !isLocked);
  }

  // IA-3I.1 (Section 13): the ONE submit pipeline -- both the Send
  // button/Enter key AND a suggestion click funnel through this same
  // function, which itself does nothing but clear/resize the real
  // composer and call the existing, unmodified handleSend(). Double-
  // submit protection is inherited for free from handleSend()'s own
  // pre-existing SENDING/THINKING guard -- no new guard invented here.
  function submitText(text) {
    text = (text || '').trim();
    if (!text) return;
    var input = document.getElementById('baiPanelInput');
    if (input) { input.value = ''; autoGrowComposer(input); updateSendButtonState(); }
    handleSend(text);
  }

  function wireComposer() {
    var input = document.getElementById('baiPanelInput');
    var btn = document.getElementById('baiPanelSendBtn');
    function submit() { submitText(input.value); }
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', function (e) {
      // Enter submits; Shift+Enter inserts a newline (Section 36),
      // matching the routed page's own composer exactly.
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    input.addEventListener('input', function () {
      autoGrowComposer(input);
      updateSendButtonState();
      var st = S.getTextState();
      if (st === S.TEXT_STATES.OPEN_IDLE || st === S.TEXT_STATES.COMPLETE || st === S.TEXT_STATES.ERROR) {
        S.setTextState(S.TEXT_STATES.COMPOSING);
      }
    });
    autoGrowComposer(input);
    updateSendButtonState();
  }

  /* ============================================================
     VOICE ENTRY CONTROL (IA-3H.1, Section 9/10/11/43/44) -- a single
     microphone affordance inside the existing composer actions, never
     a second drawer/dashboard. This file owns ONLY the button's own
     markup/label/aria state; every real session mechanic (WebRTC,
     auth, ephemeral credential, tool bridge, cleanup) lives in
     assets/js/intelligence/intelligence-voice.js, which this button
     merely calls into -- matching the existing adapter/state/panel
     separation (transport vs. store vs. UI) this drawer already uses
     for Text. ============================================================ */

  // V2-UAT-02 (Section B3): idle/disconnected now reads "Conversar por
  // voz" (the brief's own literal hover-reveal example) instead of the
  // terse "Voz" -- a clearer call-to-action when the Orb isn't active
  // yet. States already IN a session keep their short, informative
  // labels unchanged.
  var VOICE_LABEL_BY_STATE = {
    VOICE_IDLE: 'Conversar por voz', VOICE_DISCONNECTED: 'Conversar por voz',
    VOICE_CONNECTING: 'Conectando…', VOICE_LISTENING: 'Ouvindo',
    VOICE_THINKING: 'Pensando…', VOICE_SPEAKING: 'Falando',
    VOICE_INTERRUPTED: 'Ouvindo', VOICE_ERROR: 'Erro — tentar de novo'
  };

  // Subtle, non-decorative state signal: a plain CSS class per state
  // drives the Voice Orb's color/motion treatment in intelligence.css;
  // color is never the only signal, the button's own text label always
  // changes too. V2-UAT-02 (Section B4) fix: this used to strip the
  // 'VOICE_' prefix (producing e.g. 'baiVoiceStateLISTENING'), but
  // every CSS selector for it was written keeping the full state name
  // (e.g. '.baiVoiceStateVOICE_LISTENING') -- the two never matched, so
  // every per-state rule below was dead code and all 5 states rendered
  // visually identical. No new states invented, no lifecycle touched --
  // this only fixes the class the SAME existing VOICE_STATES values
  // already produce, so B4's "reuse the real states, don't fork a new
  // tree" requirement actually reaches the DOM.
  function voiceStateClass(state) {
    return state ? 'baiVoiceState' + state : '';
  }

  // IA-3H.2.1C: the icon is a small, static Fluid-Aperture-family mark
  // (NOT the real dynamic orb algorithm -- decorative UI only, no
  // analyser/microphone/second Voice runtime, Section 9). A slightly
  // irregular circular contour + a small inner seam arc, the same
  // visual language as the real Focus Mode presence, drawn once as a
  // hand-authored static path (no JS deformation math needed for an
  // 18x18 icon). aria-hidden -- the button's own aria-label already
  // carries the accessible name; this never duplicates it for AT.
  // IA-3I (Section 15): the persistent rectangular "Voz" button is
  // retired -- the Fluid Aperture mark alone is now the trigger, a
  // compact circular control. Markup is otherwise UNCHANGED (same
  // #baiPanelVoiceBtn id, same mark/seam paths, same #baiPanelVoiceBtnLabel
  // span) so every existing runtime/test contract keeps working; the
  // label becomes screen-reader-only via CSS (never removed -- it
  // still announces state changes to assistive tech) and its text is
  // ALSO mirrored onto a native `title` attribute for an optional
  // mouse-hover tooltip (Section 15's own "may reveal on hover").
  // V2-UAT-02 (Section B) -- "Voice Orb": same Living Core FAMILY as
  // the floating launcher (dark core + thin red ring + orbiting arc,
  // Object.freeze'd token reuse, no new colors) but with a genuinely
  // unambiguous microphone glyph at its center -- the brief's own
  // explicit complaint was that the old abstract Fluid-Aperture-style
  // mark "parece um controle técnico," not obviously "click here to
  // talk." No emoji, no generic Unicode glyph: a real minimalist mic
  // (capsule + stand + base), stroke-only to match the existing icon
  // language. Same #baiPanelVoiceBtn id/click listener/aria contract --
  // only the inner markup and the label's visibility (now hover/focus-
  // revealed instead of permanently sr-only, still real DOM text for
  // assistive tech either way) changed.
  function voiceButtonHtml() {
    return '<button type="button" class="modBtn baiVoiceBtn" id="baiPanelVoiceBtn" aria-pressed="false" title="Voz" aria-label="Iniciar conversa por voz com a Brabus Intelligence">' +
      '<span class="baiVoiceOrbCore" aria-hidden="true">' +
        '<span class="baiVoiceOrbArc"></span>' +
        '<span class="baiVoiceOrbRing"></span>' +
      '</span>' +
      '<svg class="baiVoiceBtnMark" viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true" focusable="false">' +
      '<rect class="baiVoiceBtnMarkCapsule" x="9.4" y="2.6" width="5.2" height="10" rx="2.6" stroke="currentColor" stroke-width="1.6"/>' +
      '<path class="baiVoiceBtnMarkStand" d="M5.6 11v.9a6.4 6.4 0 0 0 12.8 0V11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
      '<line class="baiVoiceBtnMarkPost" x1="12" y1="18.3" x2="12" y2="21" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
      '<line class="baiVoiceBtnMarkBase" x1="8.8" y1="21" x2="15.2" y2="21" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
      '</svg>' +
      '<span class="baiVoiceBtnLabel" id="baiPanelVoiceBtnLabel">Conversar por voz</span>' +
      '</button>';
  }

  function updateVoiceButton() {
    var btn = document.getElementById('baiPanelVoiceBtn');
    var label = document.getElementById('baiPanelVoiceBtnLabel');
    if (!btn || !label || !S) return;
    var state = S.getVoiceState();
    var VS = S.VOICE_STATES;
    var isActive = state !== VS.VOICE_DISCONNECTED && state !== VS.VOICE_IDLE && state !== VS.VOICE_ERROR;
    var stateText = VOICE_LABEL_BY_STATE[state] || 'Voz';
    label.textContent = stateText;
    btn.setAttribute('title', stateText);
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    btn.setAttribute('aria-label', isActive
      ? 'Encerrar conversa por voz com a Brabus Intelligence'
      : 'Iniciar conversa por voz com a Brabus Intelligence');
    btn.className = 'modBtn baiVoiceBtn ' + voiceStateClass(state);
  }

  /* ============================================================
     OPEN / CLOSE
     ============================================================ */

  function openPanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    var backdrop = document.getElementById('baiPanelBackdrop');
    var launcherBtn = document.getElementById('baiLauncherBtn');
    if (drawer) drawer.hidden = false;
    if (backdrop) backdrop.hidden = false;
    if (launcherBtn) launcherBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('bai-panel-open');
    if (S.getTextState() === S.TEXT_STATES.CLOSED) S.setTextState(S.TEXT_STATES.OPEN_IDLE);
    applyPersistentState(S.getTextState());
    renderConversation();
    updateContextChip();
    updateVoiceButton();
    var input = document.getElementById('baiPanelInput');
    if (input) input.focus();
  }

  function closePanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    var backdrop = document.getElementById('baiPanelBackdrop');
    var launcherBtn = document.getElementById('baiLauncherBtn');
    // IA-3I (Section 26): Voice Focus is now a STATE of this same
    // Workspace, not a separate modal the Human closes independently
    // -- closing the Workspace while Voice is active must cleanly end
    // that session too (Voice's own existing end()/cleanup path,
    // never a second/duplicate teardown), so nothing is left running
    // in the background behind a closed Workspace.
    if (window.NX_INTELLIGENCE_VOICE && window.NX_INTELLIGENCE_VOICE.isActive()) {
      window.NX_INTELLIGENCE_VOICE.end();
    }
    if (drawer) drawer.hidden = true;
    if (backdrop) backdrop.hidden = true;
    if (launcherBtn) { launcherBtn.setAttribute('aria-expanded', 'false'); launcherBtn.focus(); }
    document.body.classList.remove('bai-panel-open');
    // Closing never discards the conversation (intelligence-state.js's
    // own store is untouched) — only the panel's own visibility state
    // resets, matching a real "minimize", not a reset (Section 12).
    S.setTextState(S.TEXT_STATES.CLOSED);
  }

  function togglePanel() {
    var drawer = document.getElementById('baiPanelDrawer');
    if (drawer && !drawer.hidden) closePanel();
    else openPanel();
  }

  /* ============================================================
     DOM BUILD / VISIBILITY LIFECYCLE
     ============================================================ */

  // IA-ENTRY-01: "Living Core" re-skin of the launcher -- purely a
  // visual swap of what's INSIDE the button. Same #baiLauncherBtn id,
  // same aria-expanded/aria-controls/aria-label contract, same single
  // click listener wired once in buildPanelDom() (togglePanel) -- no
  // new listener, no change to open/close authority. The decorative
  // core/ring/orbit nodes are aria-hidden; the expanding label is a
  // second aria-hidden text node (the button's own aria-label already
  // announces "Abrir Brabus Intelligence" to assistive tech, so the
  // visible hover label must not be announced a second time).
  function launcherHtml() {
    return '<button type="button" class="baiLauncherBtn" id="baiLauncherBtn" aria-expanded="false" aria-controls="baiPanelDrawer" aria-label="Abrir Brabus Intelligence">' +
      '<span class="baiLauncherCore" aria-hidden="true">' +
        '<span class="baiLauncherOrbit"></span>' +
        '<span class="baiLauncherRing"></span>' +
        '<span class="baiLauncherNucleus"></span>' +
      '</span>' +
      '<span class="baiLauncherLabel" aria-hidden="true">Brabus Intelligence</span>' +
      '</button>' +
      '<div class="baiPanelBackdrop" id="baiPanelBackdrop" hidden></div>';
  }

  function panelHtml() {
    // No "INTELLIGENCE" eyebrow badge -- the title directly below it
    // already said the same thing (IA-3E.2 Section 8's own finding E);
    // removed from markup entirely, not just visually hidden.
    //
    // IA-3G.3 -- transport provenance (Section 22). The drawer had NO
    // way to tell a fixture-mode session apart from a real_text one --
    // the routed page has its own fixtureBannerHtml(), but this panel
    // never did. Found live: a local UAT scratchpad file
    // (intelligence-runtime-config.local.js, gitignored) went missing
    // between Waves, silently reverting the whole page to the
    // committed 'fixture' default, and the Human's screenshot -- a
    // perfectly plausible-looking synthetic answer -- gave no visible
    // signal that had happened. Two layers, both inert on any
    // non-real_text-configured host in production (mode there is
    // always the committed 'fixture' default, so this never renders
    // there either -- it's not a localhost-only check, it's a
    // mode-only one, exactly like the routed page's own banner):
    //   1. a data-nx-transport attribute (fixture|real_text) on the
    //      drawer root -- zero visual footprint, lets a test or a
    //      developer's own console check prove the mode directly;
    //   2. a small text line, visible ONLY in fixture mode (mirrors
    //      the routed page's fixtureBannerHtml() convention exactly),
    //      so a Human doing local UAT sees it, not just an automated
    //      test -- completely absent from the DOM in real_text mode,
    //      so the Human-approved real-mode drawer is untouched.
    // SEC-1C.3 -- a third mode, checked first: P.isHomologMisconfigured()
    // (brabus-intelligence.js, reusing environment-guard.js's own
    // AUTHORIZED_PRODUCTION classification, never a duplicated
    // hostname check) is true only on a recognized, non-local host
    // that isn't wired to real_text -- a genuine misconfiguration, not
    // a legitimate local-fixture-dev state. Exactly the class of gap a
    // real Human UAT hit: this drawer opened, looked fully functional,
    // and answered every question -- including the adversarial ones --
    // from local fixture data on a real published homolog host.
    var transportMode = (P && P.isHomologMisconfigured && P.isHomologMisconfigured()) ? 'misconfigured'
      : (P && P.isRealTextMode()) ? 'real_text' : 'fixture';
    // Reuses .modFixtureBanner as-is (module-system.css) -- the SAME
    // shared "dev tooling, not production UI" visual language every
    // other module's own fixture banner already uses, rather than
    // inventing a second, competing visual treatment for the same
    // concept.
    var provenanceBannerHtml = transportMode === 'fixture'
      ? '<p class="modFixtureBanner baiPanelProvenanceBanner" id="baiPanelProvenanceBanner" style="margin:0 var(--bai-rail);border-radius:var(--radius-sm)">Modo de teste local — respostas não vêm do servidor real.</p>'
      : transportMode === 'misconfigured'
      ? '<p class="modFixtureBanner baiPanelProvenanceBanner" id="baiPanelProvenanceBanner" style="margin:0 var(--bai-rail);border-radius:var(--radius-sm)">Brabus Intelligence indisponível — configuração de homologação ausente.</p>'
      : '';
    // IA-3I (Section 10): "Nova conversa" becomes a compact icon
    // action (a real accessible button, native `title` tooltip,
    // never underlined-link styling) -- same #baiPanelNewChatBtn id,
    // same click handler, only the visible content changed.
    var newChatIconHtml = '<button type="button" class="baiIconBtn" id="baiPanelNewChatBtn" title="Nova conversa" aria-label="Nova conversa">' +
      '<svg viewBox="0 0 20 20" width="16" height="16" fill="none" aria-hidden="true" focusable="false">' +
      '<path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>' +
      '</svg></button>';
    // IA-3I (Section 17): the generic "Enviar" text is retired -- a
    // compact directional glyph inside the same #baiPanelSendBtn
    // element (id/aria-label/click contract unchanged). Enter/Shift+
    // Enter submission semantics (wireComposer) are untouched.
    var sendIconHtml = '<svg viewBox="0 0 20 20" width="16" height="16" fill="none" aria-hidden="true" focusable="false">' +
      '<path d="M10 15.5V5M10 5l-4.5 4.5M10 5l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' +
      '</svg>';
    return '<aside class="baiPanelDrawer baiWorkspaceShell" id="baiPanelDrawer" role="dialog" aria-modal="true" aria-label="Brabus Intelligence" data-nx-transport="' + transportMode + '" hidden>' +
      '<div class="baiPanelAmbient" aria-hidden="true"></div>' +
      '<div class="baiPanelHeader">' +
      '<div><h2 class="baiPanelTitle">Brabus Intelligence</h2>' +
      '<p class="baiPanelContextChip" id="baiPanelContextChip" hidden></p></div>' +
      '<div class="baiPanelHeaderActions">' +
      newChatIconHtml +
      '<button type="button" class="baiPanelCloseBtn" id="baiPanelCloseBtn" aria-label="Fechar Brabus Intelligence">&times;</button>' +
      '</div></div>' +
      provenanceBannerHtml +
      '<div class="baiPanelBody">' +
      emptyStateHtml() +
      '<div class="baiConversation" id="baiPanelConversation" aria-live="polite" aria-atomic="false"></div></div>' +
      '<div class="baiComposer baiPanelComposer">' +
      voiceButtonHtml() +
      '<textarea id="baiPanelInput" class="baiComposerInput" aria-label="Pergunta para a Brabus Intelligence" placeholder="Pergunte sobre financiamento, resultado ou score..." rows="1"></textarea>' +
      '<div class="baiComposerActions">' +
      '<button type="button" class="baiSendBtn" id="baiPanelSendBtn" aria-label="Enviar mensagem" disabled>' + sendIconHtml + '</button>' +
      '</div></div>' +
      '<p class="baiPanelStatusLine" id="baiPanelStatusLine" hidden></p>' +
      '</aside>';
  }

  var panelBuilt = false;

  function buildPanelDom() {
    if (panelBuilt) return;
    var root = document.getElementById('nxOverlayRoot');
    if (!root) return;
    var wrap = document.createElement('div');
    wrap.className = 'baiLauncherRoot';
    wrap.id = 'baiLauncherRoot';
    wrap.innerHTML = launcherHtml() + panelHtml();
    root.appendChild(wrap);

    wireComposer();
    wireSuggestions(); // IA-3I.1-001: was defined but never called -- see its own doc comment
    document.getElementById('baiPanelNewChatBtn').addEventListener('click', onNovaConversa);
    document.getElementById('baiPanelCloseBtn').addEventListener('click', closePanel);
    document.getElementById('baiPanelBackdrop').addEventListener('click', closePanel);
    document.getElementById('baiLauncherBtn').addEventListener('click', togglePanel);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var drawer = document.getElementById('baiPanelDrawer');
        if (drawer && !drawer.hidden) closePanel();
      }
    });

    var voiceBtn = document.getElementById('baiPanelVoiceBtn');
    if (voiceBtn) voiceBtn.addEventListener('click', function () {
      if (window.NX_INTELLIGENCE_VOICE) window.NX_INTELLIGENCE_VOICE.toggle();
    });

    S.onChange(function () { renderConversation(); updateVoiceButton(); });
    C.onChange(function () { updateContextChip(); });

    panelBuilt = true;
    renderConversation();
    applyPersistentState(S.getTextState());
    updateContextChip();
    updateVoiceButton();
  }

  function refreshVisibility() {
    var visible = isVisibleNow();
    var existing = document.getElementById('baiLauncherRoot');
    if (visible) {
      if (!existing) buildPanelDom();
    } else if (existing) {
      // Real removal (Section 49: "do not rely only on CSS hiding"),
      // not display:none — a non-MASTER/unauthenticated viewer has no
      // Intelligence DOM node anywhere in the document at all.
      existing.parentNode.removeChild(existing);
      panelBuilt = false;
      document.body.classList.remove('bai-panel-open');
      S.setTextState(S.TEXT_STATES.CLOSED);
    }
  }

  window.NX_INTELLIGENCE_PANEL = {
    mount: function () {
      if (!window.NX_BRABUS_INTELLIGENCE_ADAPTER || !window.NX_BRABUS_INTELLIGENCE_PAGE ||
        !window.NX_INTELLIGENCE_STATE || !window.NX_INTELLIGENCE_CONTEXT) {
        console.error('[intelligence-panel] a required dependency is missing — not mounting');
        return;
      }
      A = window.NX_BRABUS_INTELLIGENCE_ADAPTER;
      P = window.NX_BRABUS_INTELLIGENCE_PAGE;
      S = window.NX_INTELLIGENCE_STATE;
      C = window.NX_INTELLIGENCE_CONTEXT;
      if (window.NX_AUTH_CORE) window.NX_AUTH_CORE.onStateChange(function () { refreshVisibility(); });
      // Route changes can also flip visibility (entering/leaving
      // #/brabus-intelligence, see isVisibleNow's route suppression
      // above) — always active, independent of whether the panel DOM
      // has been built yet (buildPanelDom's own C.onChange only wires
      // the context CHIP, once the panel exists).
      C.onChange(function () { refreshVisibility(); });
      refreshVisibility();
    },
    // exposed for tests
    isVisibleNow: isVisibleNow,
    openPanel: function () { openPanel(); },
    closePanel: function () { closePanel(); },
    // Test-only hook: re-runs the same visibility decision mount()'s
    // own onStateChange listener runs on a real auth transition. Real
    // callers never need this — production visibility changes are
    // driven exclusively by genuine NX_AUTH_CORE state transitions.
    refresh: function () { refreshVisibility(); }
  };
})();
