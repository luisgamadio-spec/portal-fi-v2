/* PORTAL-NEXT V2 — Simulador Seminovos page (PORTAL-NEXT-08.1, aligned
   PORTAL-NEXT-08.4). Consumes the frozen PORTAL-NEXT-08 engines
   exclusively (window.NX_SIMULADOR_SEMINOVOS_ADAPTER /
   NX_SIMULADOR_SHARED / NX_CASH_CONVERSION_ADAPTER). Zero business
   math is duplicated here.

   PORTAL-NEXT-08.4 Gate 5-8/21/22/34 — navigation scope, re-audited
   against real production (git show origin/main:modules/
   simulador-seminovos.html): the top-level menu
   (.premium-menu-grid-v2) contains exactly 5 reachable buttons —
   openLinear, openBalaoSafra, openDescobridorTaxa, openAntecipacao,
   openCashConversion. Three features this page previously exposed are
   NOT reachable in production, confirmed by the same standard already
   used for the pre-existing dead top-level Linear tab/Taxas
   Subsidiadas (Gate 33 of docs/SIMULATOR-ENGINE-DISCOVERY-08.md):
     - Semestral/Anual (#periodico): full real markup exists inside
       the reachable simulatorScreen, but its only <div class="tabs">
       contains ONE button (data-tab="tradicional") -- no tab ever
       activates #periodico.
     - Financiamento Campanha/Coparticipado (#campaignScreen): the
       screen exists, but its entry button id="openFinanciamentoCampanha"
       does not exist anywhere in the HTML (same silent-no-op guard
       pattern, `if(openCampaign) openCampaign.addEventListener(...)`).
     - Semestral Triton (#semestralCopartScreen): same -- entry button
       id="openSemestralCopart" does not exist.
   Human decision (this Wave): match production exactly. All three
   removed from this page. calcularPeriodico/calcularSemestralTriton
   remain in the adapter (Gate 3 completeness, correct formulas) but
   are deliberately not called by this page -- same treatment already
   established for calcularLinear/calcularSubsidiadas.
   The reachable "Linear" experience is exclusively the nested
   RATE_TABLE engine (calcularLinearRateTable), labeled "Linear" here
   to match production's own "FINANCIAMENTO LINEAR" menu card. */
(function () {
  'use strict';

  var UI = window.NX_SIM_UI;
  var S = window.NX_SIMULADOR_SHARED;
  var SN = window.NX_SIMULADOR_SEMINOVOS_ADAPTER;
  var CC = window.NX_CASH_CONVERSION_ADAPTER;

  var MODES = [
    { id: 'tradicional', group: 'Financiamento', label: 'Tradicional (Balão)' },
    { id: 'ratetable', group: 'Financiamento', label: 'Linear' },
    { id: 'descobridor', group: 'Ferramentas', label: 'Descobridor de Taxa' },
    { id: 'antecipacao', group: 'Ferramentas', label: 'Antecipação de Parcelas' },
    { id: 'cashconversion', group: 'Ferramentas', label: 'Cash Conversion' }
  ];
  var MODE_DESC = {
    tradicional: 'Financiamento tradicional com balão opcional — a taxa depende do ano do veículo e da entrada.',
    ratetable: 'Condições próprias por ano do veículo e faixa de entrada — inclui prazo de 50x.',
    descobridor: 'Estima a taxa efetiva a partir do valor financiado, prazo e parcela.',
    antecipacao: 'Calcula o valor com desconto para antecipação de parcelas.',
    cashconversion: 'Compara o custo do financiamento com o rendimento de manter o capital aplicado.'
  };
  var TRAD_TERMS = [12, 24, 30, 36, 40, 42, 48];

  var ERROR_MSG = {
    ENTRADA_MINIMA_10PCT: 'A entrada mínima permitida para este plano é de 10%.',
    ENTRADA_MAIOR_QUE_BEM: 'A entrada deve ser menor que o valor do bem.',
    SEM_REGRA_CADASTRADA: 'Prazo sem regra cadastrada na tabela para a faixa de ano e entrada informada.',
    ANO_AUSENTE: 'Digite o ano do veículo para identificar a tabela correta.',
    BALAO_FORA_DO_PRAZO: 'Existe balão fora do prazo. Use parcelas entre 1 e o prazo escolhido.',
    BALAO_DUPLICADO: 'Não é permitido inserir dois balões na mesma parcela.',
    BALAO_VALOR_INVALIDO: 'Informe valor válido para todos os balões.',
    BALOES_ACIMA_DO_LIMITE: 'A soma dos balões ultrapassa o valor máximo permitido, calculado sobre o valor financiado.',
    BALOES_ALTOS_DEMAIS: 'Os balões escolhidos são altos demais para gerar uma parcela mensal válida.',
    BEM_INVALIDO: 'Informe um Valor do Bem válido.',
    PRAZO_INVALIDO: 'Informe um prazo válido entre 1 e 60 meses.',
    PARCELA_INVALIDA: 'Informe uma parcela maior que zero.',
    FINANCIADO_INVALIDO: 'O valor financiado precisa ser maior que zero.',
    PARCELA_INCOMPATIVEL: 'Parcela incompatível com os dados informados. Revise os valores.',
    PRIMEIRA_PARCELA_AUSENTE: 'Informe a data da primeira parcela.',
    DATA_AUSENTE: 'Informe a data desejada para antecipação.',
    INTERVALO_INVALIDO: 'Informe um intervalo válido de parcelas.',
    PARCELA_INVALIDA_INTERVALO: 'Informe uma parcela válida dentro do prazo.',
    NENHUMA_PARCELA_FUTURA: 'Nenhuma parcela futura encontrada. Revise a data de antecipação.'
  };
  function errMsg(code) { return ERROR_MSG[code] || 'Dados inválidos para este cálculo.'; }

  var currentMode = MODES[0].id;
  var balloons = [];
  // SIM-NAV-4 / Concept F.2 (Human-approved final authority,
  // SIM_NAV_F2_HUMAN_APPROVED) -- which category group is currently
  // expanded; null = all collapsed (the default on every page load).
  // Deliberately separate from currentMode: browsing/opening a
  // category must NEVER change the selected simulator mode -- only an
  // actual option click/Enter does (see the .smModeBtn click handler
  // in wireModeNav() below). Independent copy, mirroring
  // simulador-novos.js's own identical change.
  var openCategory = null;

  /* ---------- Grouped-button mode nav, mirroring Novos' 08.2 pattern
     (approved by human UAT) -- independent copy, Seminovos' own
     smaller MODES list, no Novos file touched.
     SIM-NAV-4: markup refined again to the Human-approved Concept F.2
     look (labs/simuladores-navigation-lab.css, commits 1909bd1/
     8ded4b0/5158925), replacing SIM-NAV-3's Concept E -- mirroring the
     identical change just made in simulador-novos.js. Categories
     collapsed by default; only one open at a time; selecting an
     option auto-collapses it and shows a red+bold current-mode hint
     on its (now collapsed) header. .smModeBtn/.smModeBtnLabel/
     .smModeGroupLabel/data-mode are UNCHANGED from E -- pre-existing
     tests that click '.smModeBtn[data-mode="..."]' or read
     .smModeGroupLabel/.smModeBtn.textContent keep working unmodified;
     only a new clickable .smModeGroupHeader and a .smModeRowsWrap
     animation wrapper were added around the same existing
     elements. ---------- */
  function modeGroups() {
    var groups = {}, order = [];
    MODES.forEach(function (m) {
      if (!groups[m.group]) { groups[m.group] = []; order.push(m.group); }
      groups[m.group].push(m);
    });
    return order.map(function (g) { return { name: g, items: groups[g] }; });
  }
  function modeChevron() {
    return '<svg class="smChevron" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M6 3.5L10.5 8L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }
  // SIM-REG-01: "Falar com um Analista" CTA -- mirrors simulador-
  // novos.js's own identical addition (independent copy, same as
  // every prior change to this file). Lives in .modPageHeader (shared
  // flex/space-between header row, 0 shared CSS change), static
  // markup rendered once by render(), never touched by switchMode()/
  // toggleCategory()'s nav-only re-renders. Action/destination
  // authority lives entirely in window.NX_FI_ATENDIMENTO
  // (fi-atendimento.js).
  function analystCtaHtml(origin) {
    return '<button type="button" class="smAnalystCta" id="smAnalystCtaBtn" data-analyst-origin="' + origin + '">' +
      '<svg class="smAnalystCtaIcon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2 3.5h12v7H6.5L3 13.5V10.5H2z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      'Falar com um Analista' +
      '</button>';
  }
  function wireAnalystCta() {
    var btn = document.getElementById('smAnalystCtaBtn');
    if (btn) {
      btn.addEventListener('click', function () {
        if (window.NX_FI_ATENDIMENTO) window.NX_FI_ATENDIMENTO.falarComAnalista(btn.getAttribute('data-analyst-origin'));
      });
    }
  }
  // SIM-NAV-4 / F.2 -- which category (group name) owns a given mode
  // id. Used to restore focus to the correct (now-collapsed) header
  // after a selection auto-collapses its panel.
  function groupForMode(mode) {
    var owner = null;
    MODES.forEach(function (m) { if (m.id === mode) owner = m.group; });
    return owner;
  }
  function modeNavHtml() {
    return '<nav class="smModeNav" aria-label="Modalidade de financiamento">' +
      modeGroups().map(function (g) {
        var isOpen = g.name === openCategory;
        var slug = g.name.toLowerCase().replace(/[^a-z0-9]+/g, '');
        var panelId = 'smModePanel-' + slug;
        var current = null;
        g.items.forEach(function (m) { if (m.id === currentMode) current = m; });
        // SIM-NAV-4 / F.2: collapsed current-mode hint -- only for the
        // category that actually owns the current mode, never while
        // that same category is open (the expanded row's own active
        // treatment already shows it there; no duplication).
        var hintHtml = (!isOpen && current) ? '<span class="smModeHint">' + UI.esc(current.label) + '</span>' : '';
        return '<div class="smModeGroup' + (isOpen ? ' open' : '') + '">' +
          '<button type="button" class="smModeGroupHeader" data-group="' + UI.esc(g.name) + '" aria-expanded="' + isOpen + '" aria-controls="' + panelId + '">' +
            '<span class="smModeGroupHeaderMain">' +
              '<span class="smModeGroupLabel">' + UI.esc(g.name) + '</span>' +
              hintHtml +
            '</span>' +
            '<svg class="smChevron smModeDisclosure" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M6 3.5L10.5 8L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</button>' +
          '<div class="smModeRowsWrap"><div class="smModeRowsInner">' +
          '<div class="smModeButtons" id="' + panelId + '" role="group" aria-label="' + UI.esc(g.name) + '"' + (isOpen ? '' : ' inert') + '>' +
          g.items.map(function (m) {
            var active = m.id === currentMode;
            return '<button type="button" class="smModeBtn' + (active ? ' active' : '') + '" data-mode="' + m.id + '" tabindex="' + (isOpen ? '0' : '-1') + '"' + (active ? ' aria-current="true"' : '') + '>' +
              '<span class="smModeBtnLabel">' + UI.esc(m.label) + '</span>' + modeChevron() +
              '</button>';
          }).join('') +
          '</div></div></div>' +
        '</div>';
      }).join('') +
      '</nav>';
  }
  // SIM-NAV-4 / F.2 -- toggles the open category. Clicking the
  // already-open category collapses back to all-collapsed; clicking a
  // different one closes the previous and opens the new one
  // (single-open). Re-renders ONLY the nav region -- never touches
  // currentMode/balloons/renderModeArea(), so browsing a category
  // never disturbs the in-progress form in the currently selected mode.
  function toggleCategory(groupName) {
    openCategory = (openCategory === groupName) ? null : groupName;
    document.getElementById('smModeNavRegion').innerHTML = modeNavHtml();
    wireModeNav();
    var header = document.querySelector('.smModeGroupHeader[data-group="' + groupName + '"]');
    if (header) header.focus();
  }
  function wireModeNav() {
    document.querySelectorAll('.smModeBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var m = btn.getAttribute('data-mode');
        var owner = groupForMode(m);
        // SIM-NAV-4 / F.2: an ACTUAL option selection (this handler
        // only -- never the category-header toggle, hover, or roving
        // keyboard focus below) auto-collapses its panel. switchMode()
        // is the existing, unmodified mode-switch business authority;
        // it already re-renders/rewires the nav region itself, so
        // openCategory is simply reset before calling it -- no
        // duplicate render, no duplicate dispatch.
        openCategory = null;
        switchMode(m);
        // The just-selected row is now inert (its panel collapsed) --
        // focusing it would silently fail and strand keyboard focus.
        // Return focus to the header that now shows this selection's
        // hint instead.
        var header = owner ? document.querySelector('.smModeGroupHeader[data-group="' + owner + '"]') : null;
        if (header) header.focus();
      });
    });
    document.querySelectorAll('.smModeGroupHeader').forEach(function (btn) {
      btn.addEventListener('click', function () { toggleCategory(btn.getAttribute('data-group')); });
    });
    // SIM-NAV-3 / Concept E: roving keyboard nav within each category
    // group, additive to (not replacing) native Tab access and native
    // Enter/Space button activation -- no conflicting keyboard model.
    // A collapsed group is `inert`, so its items are simply
    // unreachable here -- no special-casing needed.
    document.querySelectorAll('.smModeButtons').forEach(function (group) {
      var items = Array.prototype.slice.call(group.querySelectorAll('.smModeBtn'));
      items.forEach(function (item, idx) {
        item.addEventListener('keydown', function (e) {
          var next = null;
          if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = items[(idx + 1) % items.length];
          else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') next = items[(idx - 1 + items.length) % items.length];
          else if (e.key === 'Home') next = items[0];
          else if (e.key === 'End') next = items[items.length - 1];
          if (next) { e.preventDefault(); next.focus(); }
        });
      });
    });
    // SIM-NAV-4 / F.2: Left/Right (or Up/Down) roving nav between the
    // category headers themselves. Separate, simple mechanism --
    // headers carry no data-mode, so the generic loop above never
    // touches them, and this loop never touches rows. No conflicting
    // keyboard model.
    var headers = Array.prototype.slice.call(document.querySelectorAll('.smModeGroupHeader'));
    headers.forEach(function (h, idx) {
      h.addEventListener('keydown', function (e) {
        var next = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = headers[(idx + 1) % headers.length];
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = headers[(idx - 1 + headers.length) % headers.length];
        if (next) { e.preventDefault(); next.focus(); }
      });
    });
  }

  function switchMode(id) {
    currentMode = id;
    balloons = [];
    document.getElementById('smModeNavRegion').innerHTML = modeNavHtml();
    wireModeNav();
    renderModeArea();
  }

  function renderModeArea() {
    disconnectTermGridObservers();
    document.getElementById('smModeDesc').textContent = MODE_DESC[currentMode] || '';
    document.getElementById('smFormRegion').innerHTML = formHtml(currentMode);
    document.getElementById('smResultRegion').innerHTML = UI.emptyBlock('Preencha os campos e clique em Calcular.');
    wireForm(currentMode);
  }

  /* ---------- Balanced term grid, mirroring Novos' 08.2 pattern
     (approved by human UAT) -- independent copy, pure presentation,
     0 dependency on Novos' file. Only Tradicional (Balão) has a term
     SELECTOR here; Linear/RATE_TABLE shows every term as a RESULT row
     (Gate 9/10), no selector needed. ---------- */
  function balancedColumns(containerWidth, itemMinWidth, n) {
    if (n <= 1) return 1;
    var maxFit = Math.max(1, Math.floor(containerWidth / itemMinWidth));
    var cap = Math.min(maxFit, n);
    if (cap >= n) return n;
    var c;
    for (c = cap; c >= 2; c--) { var rem = n % c; if (rem === 0 || rem >= 2) return c; }
    for (c = cap + 1; c <= n; c++) { var rem2 = n % c; if (rem2 === 0 || rem2 >= 2) return c; }
    return cap;
  }
  function termGridFieldHtml(id, label, terms, activeValue) {
    var buttons = terms.map(function (t) {
      return '<button type="button" data-v="' + t + '" class="' + (String(t) === String(activeValue) ? 'active' : '') + '">' + t + 'x</button>';
    }).join('');
    return '<div class="field"><label id="' + id + 'Label">' + UI.esc(label) + '</label>' +
      '<div class="smTermSelectGrid" id="' + id + '" role="group" aria-labelledby="' + id + 'Label">' + buttons + '</div></div>';
  }
  var termGridObservers = [];
  function wireTermGrid(id, termCount) {
    var container = document.getElementById(id);
    if (!container) return;
    function recompute() {
      var w = container.clientWidth || container.parentElement.clientWidth;
      container.style.setProperty('--term-cols', String(balancedColumns(w, 60, termCount)));
    }
    recompute();
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(recompute);
      ro.observe(container);
      termGridObservers.push(ro);
    } else {
      window.addEventListener('resize', recompute);
    }
    container.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        container.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
      });
    });
  }
  function disconnectTermGridObservers() {
    termGridObservers.forEach(function (ro) { ro.disconnect(); });
    termGridObservers = [];
  }

  // V2_SIMULATOR_INSTALLMENT_GRID_VISUAL_FIX: same shared mechanism as
  // simulador-novos.js's own wireResultTermGrid -- see simuladores-
  // shared.js's UI.wireTermResultGrid for the root-cause explanation.
  function wireResultTermGrid(itemCount) {
    var grid = document.querySelector('#smResultRegion .smTermGrid');
    if (!grid) return;
    var ro = UI.wireTermResultGrid(grid, 110, itemCount);
    if (ro) termGridObservers.push(ro);
  }

  function formHtml(mode) {
    switch (mode) {
      case 'tradicional':
        return UI.moneyField('sBem', 'Valor do bem', 'R$ 80.000,00') +
          UI.moneyField('sEntrada', 'Entrada', 'R$ 16.000,00') +
          UI.numberField('sAno', 'Ano do veículo', 2022, { min: 1900, max: 2099, hint: 'Tabelas cadastradas para 2017–2024 e 2025–2099.' }) +
          termGridFieldHtml('sPrazo', 'Prazo', TRAD_TERMS, 24) +
          '<div class="field"><label>Balões</label><div class="smBalloonList" id="sBaloesList"></div>' +
          '<button type="button" class="btn btn-secondary btn-sm" id="sAddBalao">+ Adicionar balão</button></div>' +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'ratetable':
        return UI.numberField('sAnoRT', 'Ano do veículo', 2020, { min: 2007, max: 2099, hint: 'Tabela cadastrada para 2007–2099.' }) +
          UI.moneyField('sValorRT', 'Valor do veículo', 'R$ 80.000,00') +
          UI.moneyField('sEntradaRT', 'Entrada', 'R$ 0,00', 'Entrada permitida a partir de 0%.') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'descobridor':
        return UI.moneyField('sFinanciado', 'Valor financiado', 'R$ 70.000,00') +
          UI.numberField('sPrazoNum', 'Prazo (meses)', 36, { min: 1, max: 60 }) +
          UI.moneyField('sParcela', 'Parcela', 'R$ 2.400,00') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'antecipacao':
        return UI.numberField('sPrazoNum', 'Prazo (meses)', 36, { min: 1, max: 60 }) +
          UI.moneyField('sParcela', 'Valor da parcela mensal', 'R$ 1.800,00') +
          UI.dateField('sPrimeira', 'Data da primeira parcela', '') +
          UI.dateField('sData', 'Data desejada para antecipação', '') +
          UI.segmentedField('sTipoAnt', 'O que antecipar', [{ value: 'todo', label: 'Contrato todo' }, { value: 'algumas', label: 'Algumas parcelas' }, { value: 'uma', label: 'Uma parcela' }], 'todo') +
          '<div id="sAntExtra"></div>' +
          '<span class="hint">Balões não são suportados nesta versão da interface (o motor extraído suporta; ver limitações conhecidas).</span>' +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'cashconversion':
        return UI.moneyField('sCapital', 'Capital', 'R$ 100.000,00') +
          UI.moneyField('sParcelaCC', 'Parcela ofertada', 'R$ 2.500,00') +
          UI.numberField('sPrazoCC', 'Prazo (meses)', 36, { min: 1, max: 60 }) +
          UI.percentField('sTaxaCC', 'Taxa de aplicação mensal (%)', '0,80') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      default:
        return '';
    }
  }

  function antExtraHtml(tipo) {
    if (tipo === 'algumas') return UI.numberField('sDe', 'De (parcela nº)', 1, { min: 1 }) + UI.numberField('sAte', 'Até (parcela nº)', 12, { min: 1 });
    if (tipo === 'uma') return UI.numberField('sParcelaUnicaNum', 'Parcela nº', 1, { min: 1 });
    return '';
  }

  function renderBaloesList() {
    var list = document.getElementById('sBaloesList');
    if (!list) return;
    list.innerHTML = balloons.map(function (b, i) {
      return '<div class="smBalloonRow">' +
        '<div class="field"><label>Mês do balão ' + (i + 1) + '</label><input class="input mono" type="number" min="1" data-bidx="' + i + '" data-bfield="mes" value="' + (b.mes || '') + '"></div>' +
        '<div class="field"><label>Valor do balão ' + (i + 1) + '</label><div class="inputAffix"><span class="prefix">R$</span><input class="input mono" data-bidx="' + i + '" data-bfield="valor" value="' + (b.valorText || '') + '"></div></div>' +
        '<button type="button" class="btn btn-tertiary btn-sm" data-bremove="' + i + '" aria-label="Remover balão ' + (i + 1) + '">Remover</button>' +
        '</div>';
    }).join('');
    list.querySelectorAll('[data-bidx]').forEach(function (el) {
      el.addEventListener('input', function () {
        var idx = Number(el.getAttribute('data-bidx')), field = el.getAttribute('data-bfield');
        if (field === 'mes') balloons[idx].mes = Number(el.value) || 0;
        else { balloons[idx].valorText = el.value; balloons[idx].valor = S.parseBRL(el.value); }
      });
      el.addEventListener('blur', function () { if (el.getAttribute('data-bfield') === 'valor') el.value = UI.brlDigits(S.parseBRL(el.value)); });
    });
    list.querySelectorAll('[data-bremove]').forEach(function (el) {
      el.addEventListener('click', function () { balloons.splice(Number(el.getAttribute('data-bremove')), 1); renderBaloesList(); });
    });
  }

  function wireForm(mode) {
    if (mode === 'tradicional') {
      renderBaloesList();
      document.getElementById('sAddBalao').addEventListener('click', function () { balloons.push({ mes: null, valor: 0, valorText: '' }); renderBaloesList(); });
      wireTermGrid('sPrazo', TRAD_TERMS.length);
      document.getElementById('sCalc').addEventListener('click', calcTradicional);
    } else if (mode === 'ratetable') {
      document.getElementById('sCalc').addEventListener('click', calcRateTable);
    } else if (mode === 'descobridor') {
      document.getElementById('sCalc').addEventListener('click', calcDescobridor);
    } else if (mode === 'antecipacao') {
      document.getElementById('sAntExtra').innerHTML = antExtraHtml('todo');
      UI.wireSegmented('sTipoAnt', function (v) { document.getElementById('sAntExtra').innerHTML = antExtraHtml(v); });
      document.getElementById('sCalc').addEventListener('click', calcAntecipacao);
    } else if (mode === 'cashconversion') {
      document.getElementById('sCalc').addEventListener('click', calcCashConversion);
    }
  }

  function setResult(html) { document.getElementById('smResultRegion').innerHTML = html; }

  /* ---------- Balloon payment-structure story, mirroring Novos' 08.2
     pattern (approved by human UAT) -- PRESENTATION ONLY, derives
     entirely from Seminovos' OWN calcularTradicional() r.parcela and
     the already-validated balloon list. 0 math duplicated: Seminovos'
     engine genuinely differs from Novos' (vehicle-year table, 1.0 vs
     0.7 balloon-cap ratio -- see docs/SIMULATOR-ENGINE-DISCOVERY-08.md
     Gate 49), but this summary function is generic pure presentation
     over (prazo, parcela, baloes), identical shape in both. ---------- */
  function balloonScheduleSummary(prazo, parcela, validBaloes) {
    var specials = validBaloes.slice().sort(function (a, b) { return a.mes - b.mes; })
      .map(function (b) { return { mes: b.mes, balao: b.valor, total: parcela + b.valor }; });
    return { regularCount: prazo - specials.length, regularValue: parcela, specials: specials };
  }
  function renderBalloonStory(prazo, parcela, validBaloes) {
    var s = balloonScheduleSummary(prazo, parcela, validBaloes);
    var html = '<div class="resultHero"><p class="kpiLabel">Plano simulado</p>';
    if (s.regularCount > 0) {
      html += '<p class="smPlanRegular"><span class="smPlanRegularCount">' + s.regularCount + 'x</span> de <span class="resultValue smPlanRegularValue">' + UI.brl(s.regularValue) + '</span></p>';
    }
    html += '</div>';
    html += '<div class="smPlanSpecials">' + s.specials.map(function (sp) {
      return '<div class="smPlanSpecialRow"><span class="kpiLabel">Parcela ' + sp.mes + '</span><span class="smPlanSpecialValue">' + UI.brl(sp.total) + '</span>' +
        '<span class="smPlanSpecialBreakdown">' + UI.brl(parcela) + ' (parcela) + ' + UI.brl(sp.balao) + ' (balão)</span></div>';
    }).join('') + '</div>';
    html += '<p class="smFootnote">Total de parcelas do plano: ' + prazo + '. Os meses com balão substituem o valor da parcela regular naquele mês por um valor especial (parcela + balão) — não são parcelas adicionais.</p>';
    return html;
  }

  function calcTradicional() {
    var prazo = Number(UI.getSegmentedValue('sPrazo'));
    var validBaloes = balloons.filter(function (b) { return b.mes && b.valor; }).map(function (b) { return { mes: b.mes, valor: b.valor }; });
    var r = SN.calcularTradicional({
      bem: UI.moneyVal('sBem'), entrada: UI.moneyVal('sEntrada'), prazo: prazo,
      ano: UI.numVal('sAno'),
      baloes: validBaloes
    });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var secondary = [{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Taxa aplicada', value: UI.pct2(r.taxa) }, { label: 'Limite de balão', value: UI.brl(r.limite) }];
    var html;
    if (validBaloes.length > 0) {
      html = renderBalloonStory(prazo, r.parcela, validBaloes) + UI.secondaryGrid(secondary);
    } else {
      html = UI.resultHero('Parcela mensal', r.parcela) + UI.secondaryGrid(secondary);
    }
    setResult(html);
  }
  function calcRateTable() {
    var r = SN.calcularLinearRateTable({ ano: UI.numVal('sAnoRT'), valor: UI.moneyVal('sValorRT'), entrada: UI.moneyVal('sEntradaRT') });
    if (r.invalid) { setResult(UI.errorBlock('Verifique o ano do veículo e a entrada informada (entrada não pode ser maior que o valor do veículo, nem o percentual maior que 100%).')); return; }
    var html = UI.termGrid(r.terms.map(function (t) { return { prazo: t.prazo, payment: t.payment, rate: t.rate, best: false }; }));
    setResult('<p class="kpiLabel" style="margin-bottom:12px">Parcela por prazo — faixa ' + (r.band || '—') + ' · entrada ' + r.eBand + '%</p>' + html +
      '<p class="smFootnote">Financiado: ' + UI.brl(r.financiado) + '</p>');
    wireResultTermGrid(r.terms.length);
  }
  function calcDescobridor() {
    var r = SN.calcularDescobridor({ financiado: UI.moneyVal('sFinanciado'), prazo: UI.numVal('sPrazoNum'), parcela: UI.moneyVal('sParcela') });
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var html = '<div class="resultHero"><p class="kpiLabel">Taxa efetiva mensal (CET)</p><p class="resultValue">' + UI.pct2(r.taxaCetMes) + '</p></div>';
    html += UI.secondaryGrid([{ label: 'Taxa nominal estimada', value: UI.pct2(r.taxaNet) }, { label: 'Total pago', value: UI.brl(r.total) }, { label: 'Juros totais', value: UI.brl(r.juros) }]);
    setResult(html);
  }
  function calcAntecipacao() {
    var tipo = UI.getSegmentedValue('sTipoAnt');
    var r = SN.calcularAntecipacao({
      prazo: UI.numVal('sPrazoNum'), parcela: UI.moneyVal('sParcela'),
      primeiraParcela: UI.textVal('sPrimeira') ? new Date(UI.textVal('sPrimeira') + 'T00:00:00') : null,
      dataAntecipacao: UI.textVal('sData') ? new Date(UI.textVal('sData') + 'T00:00:00') : null,
      tipo: tipo, de: UI.numVal('sDe'), ate: UI.numVal('sAte'), parcelaUnica: UI.numVal('sParcelaUnicaNum'), baloes: []
    });
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var rows = r.rows.map(function (row) {
      return '<tr><td>Parcela ' + row.num + '</td><td>' + row.venc.toLocaleDateString('pt-BR') + '</td><td class="num">' + UI.brl(row.bruto) + '</td><td class="num">' + UI.pct2(row.desconto) + '</td><td class="num">' + UI.brl(row.final) + '</td></tr>';
    }).join('');
    var html = UI.resultHero('Valor final com desconto', r.finalTotal);
    html += UI.secondaryGrid([{ label: 'Valor bruto', value: UI.brl(r.brutoTotal) }, { label: 'Desconto total', value: UI.brl(r.descTotal) }, { label: 'Parcelas antecipadas', value: String(r.rows.length) }]);
    if (r.missing) html = UI.warningBlock('Algumas parcelas não tinham percentual cadastrado na tabela e foram calculadas sem desconto.') + html;
    html += '<div class="smTableWrap"><table class="smTable"><thead><tr><th>Parcela</th><th>Vencimento</th><th>Valor bruto</th><th>Desconto</th><th>Valor final</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    setResult(html);
  }
  function calcCashConversion() {
    var taxaPct = Number(String(UI.textVal('sTaxaCC')).replace(',', '.')) || 0;
    var r = CC.compute({ capital: UI.moneyVal('sCapital'), parcela: UI.moneyVal('sParcelaCC'), prazoMeses: UI.numVal('sPrazoCC'), taxaAplicacao: taxaPct / 100 });
    if (!r) { setResult(UI.errorBlock('Não foi possível calcular com os dados informados.')); return; }
    var html = '<div class="resultHero"><p class="kpiLabel">Classificação</p><p><span class="smClassBadge ' + r.classificacao + '">' + r.classificacao + '</span></p></div>';
    html += UI.secondaryGrid([
      { label: 'Valor final do financiamento', value: UI.brl(r.valorFinalFinanciamento) },
      { label: 'Capital final projetado', value: UI.brl(r.valorFuturoAplicacao) },
      { label: 'Rendimento projetado', value: UI.brl(r.rendimentoAplicacao) },
      { label: 'Diferença projetada', value: UI.brl(r.diferencaProjetada) }
    ]);
    setResult(html);
  }

  window.NX_SIMULADOR_SEMINOVOS_PAGE = {
    render: function (outlet) {
      currentMode = MODES[0].id;
      balloons = [];
      openCategory = null; // SIM-NAV-4 / F.2: all categories collapsed on entry
      outlet.innerHTML =
        '<div class="smPage">' +
        '<span class="smProductBadge">Simulador · Seminovos</span>' +
        '<div class="modPageHeader"><div class="modHeaderMain"><h1 class="modTitle">Simulador de Financiamento — Seminovos</h1><p class="modSubtitle">Motores extraídos e verificados (PORTAL-NEXT-08) — 0 recálculo de fórmula nesta interface.</p></div>' + analystCtaHtml('simulador_seminovos') + '</div>' +
        '<div id="smModeNavRegion">' + modeNavHtml() + '</div>' +
        '<p class="smModeDesc" id="smModeDesc"></p>' +
        '<div class="smGrid" id="smMainGrid"><div class="modPanelForm" id="smFormRegion"></div><div class="modPanelResult" id="smResultRegion" aria-live="polite" aria-atomic="true"></div></div>' +
        '</div>';
      wireModeNav();
      wireAnalystCta();
      renderModeArea();
      return Promise.resolve();
    },
    balloonScheduleSummary: balloonScheduleSummary,
    balancedColumns: balancedColumns
  };
})();
