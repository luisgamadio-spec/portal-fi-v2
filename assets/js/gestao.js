/* PORTAL-NEXT V2 -- Gestão (Análise F&I do Grupo) module UI.
   Wave 2: RPC-shaped local contract reconciliation.

   Business logic: NONE in this file (render only). Data source:
   assets/js/adapters/gestao-fixture-provider.js (local-only, RPC-
   shaped simulation -- see that file's header). Response shaping:
   assets/js/adapters/gestao.adapter.js (thin: formatting + safe
   defaulting only). Store display names: assets/js/lookups/
   store-display.js (presentation only -- store IDENTITY everywhere in
   this file is the backend's canonical short code).

   This Wave intentionally does NOT connect to Supabase (Decision in
   the Wave 2 brief) -- when real backend integration happens, only
   gestao-fixture-provider.js's loadGestaoFixture() gets replaced with
   a real `operational_fandi_dashboard` RPC call; this file and the
   adapter do not need to change, because both already consume the
   RPC's own response shape.

   No ANALISTA/GERENTE/VENDEDOR/MASTER/DIRETOR concept exists anywhere
   in this file -- store and department are plain filter parameters,
   exactly like the real RPC treats them for a caller whose scope
   already permits the request. Authorization remains 100%
   backend-owned. */
(function () {
  'use strict';

  var currentStore = 'ALL';
  var currentDepartment = 'ALL';
  var currentPreset = 'CUSTOM';
  var currentDateStart = '2026-01-01';
  var currentDateEnd = '2026-06-30';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  function kpiPrimary(label, value, splitHtml) {
    return '<div class="modKpiCard"><div class="modKpiLabel">' + esc(label) + '</div><div class="modKpiValue">' + value + '</div>' +
      (splitHtml ? '<div class="geSplit">' + splitHtml + '</div>' : '') + '</div>';
  }
  function kpiExec(label, value, hint, accentCls) {
    return '<div class="modKpiCard modKpiCardExec' + (accentCls ? ' ' + accentCls : '') + '"><div class="modKpiLabel">' + esc(label) + '</div><div class="modKpiValue">' + value + '</div><div class="modKpiHint">' + esc(hint) + '</div></div>';
  }
  function kpiSecondary(label, value, hint) {
    return '<div class="modKpiCard modKpiCardSecondary"><div class="modKpiLabel">' + esc(label) + '</div><div class="modKpiValue">' + esc(String(value)) + '</div><div class="modKpiHint">' + esc(hint) + '</div></div>';
  }

  // Classificação dos Planos (Gate 9/10, CRITICAL): left untouched --
  // own gePlanCard/planXxx visual language already carries the correct
  // 5-way business-semantic distinction (border-left color + label),
  // which the shared system's 4 generic modifiers (success/warning/
  // critical/info) do not map onto 1:1. Not migrated, not risked.
  function planCardHtml(A, tipo, data) {
    var cls = { 'LINEAR': 'planLinear', 'BALÃO': 'planBalao', 'SUBSIDIADO': 'planSubsidiado', 'REVERSÃO': 'planReversao', 'COPARTICIPADO': 'planCoparticipado' }[tipo] || '';
    return '<div class="gePlanCard ' + cls + '"><div class="geK">' + esc(tipo) + '</div><div class="geV">' + data.quantity + '</div><div class="geHint">' + A.money(data.financed_value) + '</div></div>';
  }

  function headerRow(headers, numericFrom) {
    numericFrom = numericFrom == null ? 1 : numericFrom;
    return headers.map(function (h, i) {
      return '<th' + (i >= numericFrom ? ' class="modNumCol"' : '') + '>' + esc(h) + '</th>';
    }).join('');
  }
  function row(cells, headers) {
    function th(i) { return headers ? ' data-th="' + esc(headers[i]) + '"' : ''; }
    return '<tr><td' + th(0) + '>' + esc(cells[0]) + '</td>' + cells.slice(1).map(function (c, i) { return '<td class="modNumCol"' + th(i + 1) + '>' + esc(String(c)) + '</td>'; }).join('') + '</tr>';
  }
  function tableHtml(headers, bodyRows) {
    return '<div class="modTableWrap"><table class="modTable"><thead><tr>' + headerRow(headers) + '</tr></thead>' +
      '<tbody>' + (bodyRows.length ? bodyRows.join('') : '<tr><td colspan="' + headers.length + '" class="modMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  function displayStore(code) { return window.NX_STORE_DISPLAY.storeDisplayName(code); }

  // ---- presentation projections (Gate 11/12): the canonical model
  // stays long-format (RPC shape); these only reshape it for a
  // specific table's columns, at render time, never as stored state.

  function dynamicStoreTableHtml(A, stores, department) {
    var headers, body;
    if (department === 'NOVOS') {
      headers = ['Loja', 'Qtd Novos', 'Fin. médio Novos', 'Parcela média Novos', 'Qtd Balão', 'Parcela média Balão'];
      body = stores.map(function (r) { return row([displayStore(r.store), r.quantity, A.money(r.new_average_financed), A.money(r.new_average_installment), r.balloon_quantity, A.money(r.average_balloon)], headers); });
    } else if (department === 'SEMINOVOS') {
      headers = ['Loja', 'Qtd Seminovos', 'Fin. médio Seminovos', 'Parcela média Seminovos', 'Qtd Balão', 'Parcela média Balão'];
      body = stores.map(function (r) { return row([displayStore(r.store), r.quantity, A.money(r.used_average_financed), A.money(r.used_average_installment), r.balloon_quantity, A.money(r.average_balloon)], headers); });
    } else {
      headers = ['Loja', 'Qtd Total', 'Novos', 'Seminovos', 'Fin. médio Novos', 'Fin. médio Seminovos', 'Parcela média Novos', 'Parcela média Seminovos', 'Qtd Balão', 'Parcela média Balão'];
      body = stores.map(function (r) { return row([displayStore(r.store), r.quantity, r.new_quantity, r.used_quantity, A.money(r.new_average_financed), A.money(r.used_average_financed), A.money(r.new_average_installment), A.money(r.used_average_installment), r.balloon_quantity, A.money(r.average_balloon)], headers); });
    }
    return tableHtml(headers, body);
  }

  // Pivots the canonical long-format status_by_store/status_by_bank
  // array into the wide table this section has always shown -- a pure
  // render-time projection (Gate 11), the array itself stays long.
  function pivotStatusLong(rows, keyField) {
    var byKey = {};
    var order = [];
    rows.forEach(function (r) {
      var k = r[keyField];
      if (!byKey[k]) { byKey[k] = { key: k, pagaQtd: 0, pagaValor: 0, fatQtd: 0, fatValor: 0, agQtd: 0, agValor: 0, totalQtd: 0, totalValor: 0 }; order.push(k); }
      var b = byKey[k];
      if (r.status === 'PAGA') { b.pagaQtd += r.quantity; b.pagaValor += r.financed_value; }
      else if (r.status === 'FATURADA') { b.fatQtd += r.quantity; b.fatValor += r.financed_value; }
      else if (r.status === 'AG. FATURAMENTO') { b.agQtd += r.quantity; b.agValor += r.financed_value; }
      b.totalQtd += r.quantity; b.totalValor += r.financed_value;
    });
    return order.map(function (k) { return byKey[k]; }).sort(function (a, b) { return b.totalValor - a.totalValor; });
  }

  function statusTableHtml(A, rows, keyField, isStore) {
    var headers = [isStore ? 'Unidade' : 'Banco', 'Pago Qtd', 'Pago Valor', 'Faturado Qtd', 'Faturado Valor', 'AG. Fat. Qtd', 'AG. Fat. Valor', 'Total Qtd', 'Total Valor'];
    var pivoted = pivotStatusLong(rows, keyField);
    var body = pivoted.map(function (r) {
      return row([isStore ? displayStore(r.key) : r.key, r.pagaQtd, A.money(r.pagaValor), r.fatQtd, A.money(r.fatValor), r.agQtd, A.money(r.agValor), r.totalQtd, A.money(r.totalValor)], headers);
    });
    return tableHtml(headers, body);
  }

  // Pivots plans_by_store_department (long: store/department/plan_type/
  // quantity) into the per-department matrix table -- canonical array
  // stays long, only this render helper projects it (Gate 12).
  function planStoreDeptTableHtml(rows, dept) {
    var isNovos = dept === 'NOVOS';
    var types = isNovos ? ['LINEAR', 'BALÃO', 'SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO'] : ['LINEAR', 'BALÃO', 'REVERSÃO'];
    var headers = isNovos
      ? ['Loja', 'Linear', 'Balão', 'Subsidiado', 'Reversão', 'Coparticipado', 'Total']
      : ['Loja', 'Linear', 'Balão', 'Reversão', 'Total'];
    var byStore = {};
    var order = [];
    rows.filter(function (r) { return r.department === dept; }).forEach(function (r) {
      if (!byStore[r.store]) { byStore[r.store] = { store: r.store, total: 0 }; order.push(r.store); }
      byStore[r.store][r.plan_type] = (byStore[r.store][r.plan_type] || 0) + r.quantity;
      byStore[r.store].total += r.quantity;
    });
    var body = order.map(function (s) {
      var b = byStore[s];
      var cells = types.map(function (t) { return b[t] || 0; }).concat([b.total]);
      return '<tr><td data-th="' + esc(headers[0]) + '">' + esc(displayStore(s)) + '</td>' + cells.map(function (c, i) { return '<td class="modNumCol" data-th="' + esc(headers[i + 1]) + '">' + c + '</td>'; }).join('') + '</tr>';
    });
    return '<div class="modTableWrap"><table class="modTable"><thead><tr>' + headerRow(headers) + '</tr></thead>' +
      '<tbody>' + (body.length ? body.join('') : '<tr><td colspan="' + headers.length + '" class="modMuted">Nenhuma loja encontrada.</td></tr>') + '</tbody></table></div>';
  }

  // proposal_outcomes (long: store/department/outcome/quantity/
  // financed_value) grouped per store for one outcome (Gate 13:
  // production contract is the source of truth, no CPF-dedup
  // algorithm involved at all).
  function outcomeTableHtml(A, rows, outcome, department) {
    var filtered = rows.filter(function (r) { return r.outcome === outcome; });
    var byStore = {};
    var order = [];
    filtered.forEach(function (r) {
      if (!byStore[r.store]) { byStore[r.store] = { store: r.store, novosQtd: 0, novosValor: 0, seminovosQtd: 0, seminovosValor: 0, qtd: 0, valor: 0 }; order.push(r.store); }
      var b = byStore[r.store];
      if (r.department === 'SEMINOVOS') { b.seminovosQtd += r.quantity; b.seminovosValor += r.financed_value; }
      else { b.novosQtd += r.quantity; b.novosValor += r.financed_value; }
      b.qtd += r.quantity; b.valor += r.financed_value;
    });
    var items = order.map(function (s) { return byStore[s]; }).sort(function (a, b) { return b.qtd - a.qtd || b.valor - a.valor; });

    var headers, body;
    if (department === 'NOVOS') {
      headers = ['Loja', 'Qtd CPFs Novos', 'Valor Novos', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([displayStore(r.store), r.novosQtd, A.money(r.novosValor), A.money(r.novosQtd ? r.novosValor / r.novosQtd : 0)], headers); });
    } else if (department === 'SEMINOVOS') {
      headers = ['Loja', 'Qtd CPFs Seminovos', 'Valor Seminovos', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([displayStore(r.store), r.seminovosQtd, A.money(r.seminovosValor), A.money(r.seminovosQtd ? r.seminovosValor / r.seminovosQtd : 0)], headers); });
    } else {
      headers = ['Loja', 'Novos Qtd', 'Novos Valor', 'Seminovos Qtd', 'Seminovos Valor', 'Total CPFs', 'Valor Total', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([displayStore(r.store), r.novosQtd, A.money(r.novosValor), r.seminovosQtd, A.money(r.seminovosValor), r.qtd, A.money(r.valor), A.money(r.qtd ? r.valor / r.qtd : 0)], headers); });
    }
    return { items: items, html: tableHtml(headers, body) };
  }

  function render() {
    var A = window.NX_GESTAO_ADAPTER;
    var department = currentDepartment === 'ALL' ? null : currentDepartment;
    var store = currentStore === 'ALL' ? null : currentStore;

    return window.NX_GESTAO_FIXTURE_PROVIDER.loadGestaoFixture({
      start: currentDateStart, end: currentDateEnd, store: store, department: department
    }).then(function (raw) {
      var out = A.normalizeResponse(raw);
      var periodo = (currentDateStart || 'Início') + ' a ' + (currentDateEnd || 'Fim');
      var visaoLoja = displayStore(currentStore === 'ALL' ? null : currentStore);
      var visaoTipo = currentDepartment === 'ALL' ? 'Todos os veículos' : (currentDepartment === 'NOVOS' ? 'Novos' : 'Seminovos');
      var filtered = currentDepartment !== 'ALL';

      // Per-status totals: the RPC's status_by_store carries no
      // department dimension, so (unlike "Produção Total" below) these
      // 3 cards show qtd+valor only -- the Novos/Seminovos split isn't
      // part of this contract field, so it isn't fabricated here.
      function statusTotal(status) {
        return out.status_by_store.filter(function (r) { return r.status === status; })
          .reduce(function (acc, r) { acc.qtd += r.quantity; acc.valor += r.financed_value; return acc; }, { qtd: 0, valor: 0 });
      }
      var pagaTotal = statusTotal('PAGA');
      var fatTotal = statusTotal('FATURADA');
      var agTotal = statusTotal('AG. FATURAMENTO');
      var novosTotal = out.stores.reduce(function (s, r) { return s + r.new_quantity; }, 0);
      var semisTotal = out.stores.reduce(function (s, r) { return s + r.used_quantity; }, 0);
      var novosValorTotal = out.stores.reduce(function (s, r) { return s + r.new_quantity * r.new_average_financed; }, 0);
      var semisValorTotal = out.stores.reduce(function (s, r) { return s + r.used_quantity * r.used_average_financed; }, 0);

      function productionCardHtml(title, qtd, valor, novos, seminovos, valorNovos, valorSeminovos) {
        if (filtered || novos == null) {
          return '<div class="modKpiCard"><div class="modKpiLabel">' + esc(title) + '</div><div class="modKpiValue">' + qtd + '</div>' +
            '<div class="geSplit">' + A.money(valor) + '</div></div>';
        }
        return kpiPrimary(title, qtd,
          '<span>Novos <b>' + novos + '</b> · ' + A.money(valorNovos) + '</span>' +
          '<span>Seminovos <b>' + seminovos + '</b> · ' + A.money(valorSeminovos) + '</span>');
      }

      var planoMap = {};
      out.plans.forEach(function (p) { planoMap[p.plan_type] = p; });
      var planCards = ['SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO', 'BALÃO', 'LINEAR'].map(function (t) {
        return planCardHtml(A, t, planoMap[t] || { quantity: 0, financed_value: 0 });
      }).join('');

      var spfTotal = out.spf_extra.reduce(function (s, r) { return s + r.spf_value; }, 0);
      var spfComissao = out.spf_extra.reduce(function (s, r) { return s + r.spf_70_value; }, 0);
      var spfDetailRows = out.spf_extra.map(function (r) {
        return '<tr><td data-th="Loja">' + esc(displayStore(r.store)) + '</td><td data-th="Departamento">' + esc(r.department) + '</td><td class="modNumCol" data-th="SPF Total">' + A.money(r.spf_value) + '</td><td class="modNumCol" data-th="Comissão Líquida 70%">' + A.money(r.spf_70_value) + '</td></tr>';
      });

      var perdidas = out.proposal_outcomes.filter(function (r) { return r.outcome === 'RECUSADA'; }).reduce(function (s, r) { return s + r.financed_value; }, 0);
      var abertas = out.proposal_outcomes.filter(function (r) { return r.outcome === 'APROVADA'; }).reduce(function (s, r) { return s + r.financed_value; }, 0);

      var totalGeralQtd = out.summary.operational_quantity;
      var pmtWeightedSum = out.stores.reduce(function (s, r) { return s + r.new_average_installment * r.new_quantity + r.used_average_installment * r.used_quantity; }, 0);
      var pmtMedio = totalGeralQtd ? pmtWeightedSum / totalGeralQtd : 0;
      var balaoQtdTotal = out.stores.reduce(function (s, r) { return s + r.balloon_quantity; }, 0);
      var balaoValorSum = out.stores.reduce(function (s, r) { return s + r.average_balloon * r.balloon_quantity; }, 0);
      var balaoMedio = balaoQtdTotal ? balaoValorSum / balaoQtdTotal : 0;

      var recusadas = outcomeTableHtml(A, out.proposal_outcomes, 'RECUSADA', department);
      var aprovadas = outcomeTableHtml(A, out.proposal_outcomes, 'APROVADA', department);

      var html =
        '<div class="modKpiGrid">' +
        productionCardHtml('Produção Paga', pagaTotal.qtd, pagaTotal.valor) +
        productionCardHtml('Produção Faturada', fatTotal.qtd, fatTotal.valor) +
        productionCardHtml('Produção Ag. Faturamento', agTotal.qtd, agTotal.valor) +
        productionCardHtml('Produção Total', totalGeralQtd, out.summary.total_financed, novosTotal, semisTotal, novosValorTotal, semisValorTotal) +
        '</div>' +

        '<div class="modKpiGrid">' +
        kpiExec('Valor de Produção Total', A.money(out.summary.total_financed), 'Paga + Faturada + Ag. Faturamento • ' + visaoTipo) +
        kpiExec('Valor Total de Propostas Perdidas', A.money(perdidas), 'Recusadas • ' + visaoTipo, 'modKpiCardWarning') +
        kpiExec('Valor de Propostas em Aberto', A.money(abertas), 'Aprovadas • ' + visaoTipo, 'modKpiCardInfo') +
        '</div>' +

        '<h2>Classificação dos Planos</h2>' +
        '<div class="gePlanGrid">' + planCards + '</div>' +
        '<p class="modMuted">Classificação e escopo de elegibilidade definidos pela RPC operational_fandi_dashboard (produção): SUBSIDIADO &gt; REVERSÃO &gt; COPARTICIPADO &gt; BALÃO &gt; LINEAR.</p>' +

        '<h2>Planos por Loja e Departamento</h2>' +
        '<p class="modMuted">Novos (5 tipos) e Seminovos (3 tipos), mesmo escopo do contrato de produção.</p>' +
        planStoreDeptTableHtml(out.plans_by_store_department, 'NOVOS') +
        planStoreDeptTableHtml(out.plans_by_store_department, 'SEMINOVOS') +

        '<h2>SPF EXTRA</h2>' +
        '<div class="modKpiGrid">' +
        kpiExec('Total SPF EXTRA', A.money(spfTotal), 'Valor total de opcionais SPF EXTRA') +
        kpiExec('Comissão Líquida SPF EXTRA', A.money(spfComissao), 'Soma de spf_70_value (contrato do backend, regra 70% não recalculada em V2)') +
        '</div>' +
        '<div class="modTableWrap"><table class="modTable"><thead><tr>' + headerRow(['Loja', 'Departamento', 'SPF Total', 'Comissão Líquida 70%'], 2) + '</tr></thead>' +
        '<tbody>' + (spfDetailRows.length ? spfDetailRows.join('') : '<tr><td colspan="4" class="modMuted">Nenhum SPF Extra encontrado.</td></tr>') + '</tbody></table></div>' +

        '<h2>Indicadores de Apoio</h2>' +
        '<div class="modKpiGrid">' +
        kpiSecondary('Visão', visaoLoja, currentStore !== 'ALL' ? 'unidade filtrada' : 'consolidado geral') +
        kpiSecondary('Tipo de veículo', visaoTipo, filtered ? 'filtro aplicado' : 'novos + seminovos') +
        kpiSecondary('Período analisado', periodo, 'faturamento ou pagamento no período') +
        kpiSecondary('Total geral (3 status)', totalGeralQtd, 'Paga + Faturada + Ag. Faturamento') +
        kpiSecondary('Parcela média (PMT)', A.money(pmtMedio), 'média geral ponderada') +
        kpiSecondary('Operações com balão', balaoQtdTotal, 'parcela média ' + A.money(balaoMedio)) +
        '</div>' +

        '<h2>Financiamentos por Loja</h2>' + dynamicStoreTableHtml(A, out.stores, currentDepartment === 'ALL' ? null : currentDepartment) +

        '<h2>Pagos, Faturados e AG. Faturamento por Unidade</h2>' + statusTableHtml(A, out.status_by_store, 'store', true) +

        '<h2>Pagos, Faturados e AG. Faturamento por Banco</h2>' + statusTableHtml(A, out.status_by_bank, 'bank', false) +

        '<h2>Propostas Recusadas Válidas por Loja</h2>' +
        '<div class="modKpiGrid">' +
        kpiSecondary('Lojas com recusadas', recusadas.items.length, 'agregado por loja') +
        kpiSecondary('CPFs com recusa líquida', recusadas.items.reduce(function (s, r) { return s + r.qtd; }, 0), 'contrato proposal_outcomes') +
        kpiSecondary('Valor recusado', A.money(recusadas.items.reduce(function (s, r) { return s + r.valor; }, 0)), 'soma financed_value') +
        kpiSecondary('Maior loja', recusadas.items[0] ? displayStore(recusadas.items[0].store) : '-', (recusadas.items[0] ? recusadas.items[0].qtd : 0) + ' CPFs') +
        '</div>' + recusadas.html +

        '<h2>Propostas Aprovadas Válidas por Loja</h2>' +
        '<div class="modKpiGrid">' +
        kpiSecondary('Lojas com aprovadas', aprovadas.items.length, 'agregado por loja') +
        kpiSecondary('CPFs aprovados válidos', aprovadas.items.reduce(function (s, r) { return s + r.qtd; }, 0), 'contrato proposal_outcomes') +
        kpiSecondary('Valor aprovado', A.money(aprovadas.items.reduce(function (s, r) { return s + r.valor; }, 0)), 'soma financed_value') +
        kpiSecondary('Maior loja', aprovadas.items[0] ? displayStore(aprovadas.items[0].store) : '-', (aprovadas.items[0] ? aprovadas.items[0].qtd : 0) + ' CPFs') +
        '</div>' + aprovadas.html;

      document.getElementById('gePanel').innerHTML = html;
    });
  }

  function applyPresetAndRender(preset) {
    currentPreset = preset;
    if (preset !== 'CUSTOM') {
      var today = new Date(2026, 7, 30); // fixed reference date (NEXT_LOCAL fixture mode -- deterministic, not wall-clock, so UAT is reproducible)
      var r = window.NX_GESTAO_ADAPTER.computePeriodPreset(preset, today);
      if (r) {
        currentDateStart = r.start.toISOString().slice(0, 10);
        currentDateEnd = r.end.toISOString().slice(0, 10);
        document.getElementById('geDateStart').value = currentDateStart;
        document.getElementById('geDateEnd').value = currentDateEnd;
      }
    }
    document.querySelectorAll('.gePresetBtn').forEach(function (b) { b.classList.toggle('gePresetActive', b.dataset.preset === preset); });
    render();
  }

  function wireEvents() {
    document.getElementById('geStoreFilter').addEventListener('change', function (e) { currentStore = e.target.value; render(); });
    document.getElementById('geDateStart').addEventListener('change', function (e) { currentDateStart = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.gePresetBtn').forEach(function (b) { b.classList.remove('gePresetActive'); }); render(); });
    document.getElementById('geDateEnd').addEventListener('change', function (e) { currentDateEnd = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.gePresetBtn').forEach(function (b) { b.classList.remove('gePresetActive'); }); render(); });
    document.querySelectorAll('.gePresetBtn').forEach(function (btn) {
      btn.addEventListener('click', function () { applyPresetAndRender(btn.dataset.preset); });
    });
    document.querySelectorAll('.geVehicleBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        currentDepartment = btn.dataset.department;
        document.querySelectorAll('.geVehicleBtn').forEach(function (b) { b.classList.toggle('geVehicleActive', b === btn); });
        render();
      });
    });
  }

  window.NX_GESTAO_PAGE = {
    render: function (outlet) {
      var D = window.NX_STORE_DISPLAY;
      // value = canonical code (Wave 2 Gate 6): selector value, RPC
      // request param, and RPC response `store` field are always the
      // same string -- 0 translation anywhere in identity/comparison
      // logic. Display label comes only from storeDisplayName().
      var storeOptions = ['<option value="ALL">' + esc(D.storeDisplayName('ALL')) + '</option>'].concat(
        D.CANONICAL_STORES.map(function (code) { return '<option value="' + esc(code) + '">' + esc(D.storeDisplayName(code)) + '</option>'; })
      ).join('');
      outlet.innerHTML =
        '<div class="gePage">' +
        '<div class="modPageHeader"><div class="modHeaderMain"><h1 class="modTitle">Análise F&amp;I do Grupo</h1><p class="modSubtitle">Análise operacional F&amp;I/FANDI consolidada do Grupo.</p></div></div>' +
        '<div class="modFixtureBanner"><span class="modFixtureLabel">DADOS LOCAIS (FIXTURE RPC-SHAPED, NEXT_LOCAL)</span></div>' +
        '<div class="modFilters">' +
        '<div class="modField"><label for="geStoreFilter">Loja / Unidade</label><select id="geStoreFilter">' + storeOptions + '</select></div>' +
        '<div class="modField"><label>Período rápido</label><div class="gePresetGroup">' +
        '<button type="button" class="gePresetBtn" data-preset="CURRENT_MONTH">Mês atual</button>' +
        '<button type="button" class="gePresetBtn" data-preset="PREVIOUS_MONTH">Mês anterior</button>' +
        '<button type="button" class="gePresetBtn" data-preset="LAST_6_MONTHS">Últimos 6 meses</button>' +
        '</div></div>' +
        '<div class="modField"><label for="geDateStart">Data inicial</label><input id="geDateStart" type="date" value="' + currentDateStart + '"></div>' +
        '<div class="modField"><label for="geDateEnd">Data final</label><input id="geDateEnd" type="date" value="' + currentDateEnd + '"></div>' +
        '</div>' +
        '<div class="modField" style="margin-bottom:var(--space-4)"><label>Tipo de veículo</label><div class="geVehicleGroup">' +
        '<button type="button" class="geVehicleBtn geVehicleActive" data-department="ALL">Todos</button>' +
        '<button type="button" class="geVehicleBtn" data-department="NOVOS">Novos</button>' +
        '<button type="button" class="geVehicleBtn" data-department="SEMINOVOS">Seminovos</button>' +
        '</div></div>' +
        '<div id="gePanel"></div>' +
        '</div>';
      wireEvents();
      return render();
    }
  };
})();
