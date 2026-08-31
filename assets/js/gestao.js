/* PORTAL-NEXT V2 -- Gestão (Análise F&I do Grupo) module UI.
   Business logic: assets/js/adapters/gestao.adapter.js (byte-identical
   extraction -- see docs/GESTAO-ENGINE-AUDIT.md and docs/GESTAO-
   FUNCTION-MAP.md). This file only renders.

   Real production surface migrated (verified by direct source read of
   origin/main:modules/analise-fi-grupo.html render(), lines 2310-2455):
     - Produção Paga/Faturada/Ag.Faturamento/Total (4 KPI cards)
     - Executive KPIs: Valor de Produção Total / Propostas Perdidas /
       Propostas em Aberto
     - Classificação dos Planos (5 cards)
     - Planos por Loja e Departamento (2 tables, Novos 5-type / Seminovos
       3-type -- exact real column scope, see GESTAO-KPI-CONTRACT.md)
     - SPF EXTRA (Total + Comissão Líquida = Total x 70%, fixed/non-
       configurable per the human's PORTAL-NEXT-06.1 decision -- see
       docs/GESTAO-COMMISSION-DECISION.md; same byte-identical 0.70
       computation extracted since PORTAL-NEXT-06, no new formula)
     - Support KPIs (Visão/Tipo/Período/Total geral/PMT médio/Balão)
     - Financiamentos por Loja, Status por Unidade, Status por Banco
     - Propostas Recusadas Válidas / Aprovadas Válidas por Loja
     - Filters: Loja, Tipo de veículo (Todos/Novos/Seminovos), período
       (3 presets + manual dates)

   NOT migrated (Gate 137 deferred, real reasons -- see
   docs/GESTAO-FUNCTION-MAP.md):
     - Excel/CSV upload + the live secure-API path (0 backend/0 file
       I/O this Wave)
     - Model Analysis, Seller Analysis, FECHAMENTO, charts, export --
       CONFIRMED ABSENT from this specific production module (not a
       migration gap -- see docs/GESTAO-KPI-CONTRACT.md's N/A section) */
(function () {
  'use strict';

  var STORES = ['ABC', 'ALPHAVILLE', 'ANÁLIA FRANCO', 'BARRA FUNDA', 'BANDEIRANTES', 'EUROPA', 'GASTÃO VIDIGAL', 'NAÇÕES UNIDAS'];

  var fixturesData = null;
  var currentFixtureId = 'ALL';
  var currentStore = 'ALL';
  var currentVehicle = 'TODOS';
  var currentPreset = 'CUSTOM';
  var currentDateStart = '2026-01-01';
  var currentDateEnd = '2026-12-31';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  function loadFixtures() {
    if (fixturesData) return Promise.resolve(fixturesData);
    return fetch('tests/fixtures/gestao-fixtures.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { fixturesData = data.cases; return fixturesData; });
  }

  function buildFixtureInput(id) {
    var rows;
    if (id !== 'ALL') {
      rows = fixturesData.filter(function (c) { return c.id === id; })[0].rows;
    } else {
      rows = [];
      fixturesData.forEach(function (c) { rows = rows.concat(c.rows); });
    }
    return { rows: rows, start: currentDateStart, end: currentDateEnd, store: currentStore, vehicle: currentVehicle };
  }

  function kpiPrimary(label, value, splitHtml) {
    return '<div class="geKpiCardPrimary"><div class="geK">' + esc(label) + '</div><div class="geV">' + value + '</div>' +
      (splitHtml ? '<div class="geSplit">' + splitHtml + '</div>' : '') + '</div>';
  }
  function kpiExec(label, value, hint) {
    return '<div class="geKpiCardExec"><div class="geK">' + esc(label) + '</div><div class="geV">' + value + '</div><div class="geHint">' + esc(hint) + '</div></div>';
  }
  function kpiSecondary(label, value, hint) {
    return '<div class="geKpiCardSecondary"><div class="geK">' + esc(label) + '</div><div class="geV">' + esc(String(value)) + '</div><div class="geHint">' + esc(hint) + '</div></div>';
  }

  function productionCardHtml(A, title, data, filtered) {
    if (filtered) {
      return '<div class="geKpiCardPrimary"><div class="geK">' + esc(title) + '</div><div class="geV">' + data.qtd + '</div>' +
        '<div class="geSplit">' + A.money(data.valor) + '</div></div>';
    }
    return kpiPrimary(title, data.qtd,
      '<span>Novos <b>' + data.novos + '</b> · ' + A.money(data.valorNovos) + '</span>' +
      '<span>Seminovos <b>' + data.seminovos + '</b> · ' + A.money(data.valorSeminovos) + '</span>');
  }

  function planCardHtml(A, tipo, data) {
    var cls = { 'LINEAR': 'planLinear', 'BALÃO': 'planBalao', 'SUBSIDIADO': 'planSubsidiado', 'REVERSÃO': 'planReversao', 'COPARTICIPADO': 'planCoparticipado' }[tipo] || '';
    return '<div class="gePlanCard ' + cls + '"><div class="geK">' + esc(tipo) + '</div><div class="geV">' + data.qtd + '</div><div class="geHint">' + A.money(data.valor) + '</div></div>';
  }

  function planStoreDeptTableHtml(rows, dept) {
    var isNovos = dept === 'Novos';
    var headers = isNovos
      ? ['Loja', 'Linear', 'Balão', 'Subsidiado', 'Reversão', 'Coparticipado', 'Total']
      : ['Loja', 'Linear', 'Balão', 'Reversão', 'Total'];
    var body = rows.filter(function (r) { return isNovos ? r.novos.total > 0 : r.seminovos.total > 0; }).map(function (r) {
      var b = isNovos ? r.novos : r.seminovos;
      var cells = isNovos
        ? [b.LINEAR, b['BALÃO'], b.SUBSIDIADO, b['REVERSÃO'], b.COPARTICIPADO, b.total]
        : [b.LINEAR, b['BALÃO'], b['REVERSÃO'], b.total];
      return '<tr><td>' + esc(r.loja) + '</td>' + cells.map(function (c) { return '<td class="geNumCol">' + c + '</td>'; }).join('') + '</tr>';
    }).join('');
    return '<div class="geTableWrap"><table class="geTable"><thead><tr>' + headerRow(headers) + '</tr></thead>' +
      '<tbody>' + (body || '<tr><td colspan="' + headers.length + '" class="geMuted">Nenhuma loja encontrada.</td></tr>') + '</tbody></table></div>';
  }

  function dynamicStoreTableHtml(A, store, vehicle) {
    var headers, body;
    if (vehicle === 'Novos') {
      headers = ['Loja', 'Qtd Novos', 'Fin. médio Novos', 'Parcela média Novos', 'Qtd Balão', 'Parcela média Balão'];
      body = store.map(function (r) { return row([r.loja, r.qtd, A.money(r.finNovos), A.money(r.pmtNovos), r.qtdBalao, A.money(r.balaoMedio)]); });
    } else if (vehicle === 'Seminovos') {
      headers = ['Loja', 'Qtd Seminovos', 'Fin. médio Seminovos', 'Parcela média Seminovos', 'Qtd Balão', 'Parcela média Balão'];
      body = store.map(function (r) { return row([r.loja, r.qtd, A.money(r.finSemis), A.money(r.pmtSemis), r.qtdBalao, A.money(r.balaoMedio)]); });
    } else {
      headers = ['Loja', 'Qtd Total', 'Novos', 'Seminovos', 'Fin. médio Novos', 'Fin. médio Seminovos', 'Parcela média Novos', 'Parcela média Seminovos', 'Qtd Balão', 'Parcela média Balão'];
      body = store.map(function (r) { return row([r.loja, r.qtd, r.novos, r.seminovos, A.money(r.finNovos), A.money(r.finSemis), A.money(r.pmtNovos), A.money(r.pmtSemis), r.qtdBalao, A.money(r.balaoMedio)]); });
    }
    return tableHtml(headers, body);
  }

  // Shared column-alignment contract (Gate 8-10): a numeric column's
  // header and its values share ONE axis -- both get .geNumCol
  // (text-align:right + tabular-nums, assets/css/gestao.css), never a
  // per-cell offset. `numericFrom` is the index where numeric columns
  // begin (every Gestão table is "N leading text columns, then numeric
  // to the end" -- default 1, since every table here has exactly one
  // leading text column (Loja/Unidade/Banco), except the SPF Extra
  // detail table, which has two (Loja, Departamento)).
  function headerRow(headers, numericFrom) {
    numericFrom = numericFrom == null ? 1 : numericFrom;
    return headers.map(function (h, i) {
      return '<th' + (i >= numericFrom ? ' class="geNumCol"' : '') + '>' + esc(h) + '</th>';
    }).join('');
  }
  function row(cells) {
    return '<tr><td>' + esc(cells[0]) + '</td>' + cells.slice(1).map(function (c) { return '<td class="geNumCol">' + esc(String(c)) + '</td>'; }).join('') + '</tr>';
  }
  function tableHtml(headers, bodyRows) {
    return '<div class="geTableWrap"><table class="geTable"><thead><tr>' + headerRow(headers) + '</tr></thead>' +
      '<tbody>' + (bodyRows.length ? bodyRows.join('') : '<tr><td colspan="' + headers.length + '" class="geMuted">Nenhum dado encontrado.</td></tr>') + '</tbody></table></div>';
  }

  function statusTableHtml(A, rows, keyField) {
    var headers = [keyField === 'loja' ? 'Unidade' : 'Banco', 'Pago Qtd', 'Pago Valor', 'Faturado Qtd', 'Faturado Valor', 'AG. Fat. Qtd', 'AG. Fat. Valor', 'Total Qtd', 'Total Valor'];
    var body = rows.map(function (r) {
      return row([r[keyField], r.pagaQtd, A.money(r.pagaValor), r.fatQtd, A.money(r.fatValor), r.agQtd, A.money(r.agValor), r.totalQtd, A.money(r.totalValor)]);
    });
    return tableHtml(headers, body);
  }

  function cpfTableHtml(A, items, vehicle) {
    var headers, body;
    if (vehicle === 'Novos') {
      headers = ['Loja', 'Qtd CPFs Novos', 'Valor Novos', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([r.loja, r.novosQtd, A.money(r.novosValor), A.money(r.novosQtd ? r.novosValor / r.novosQtd : 0)]); });
    } else if (vehicle === 'Seminovos') {
      headers = ['Loja', 'Qtd CPFs Seminovos', 'Valor Seminovos', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([r.loja, r.seminovosQtd, A.money(r.seminovosValor), A.money(r.seminovosQtd ? r.seminovosValor / r.seminovosQtd : 0)]); });
    } else {
      headers = ['Loja', 'Novos Qtd', 'Novos Valor', 'Seminovos Qtd', 'Seminovos Valor', 'Total CPFs', 'Valor Total', 'Valor Médio por CPF'];
      body = items.map(function (r) { return row([r.loja, r.novosQtd, A.money(r.novosValor), r.seminovosQtd, A.money(r.seminovosValor), r.qtd, A.money(r.valor), A.money(r.qtd ? r.valor / r.qtd : 0)]); });
    }
    return tableHtml(headers, body);
  }

  function render() {
    var A = window.NX_GESTAO_ADAPTER;
    var input = buildFixtureInput(currentFixtureId);
    var out = A.compute(input);
    var periodo = (currentDateStart || 'Início') + ' a ' + (currentDateEnd || 'Fim');
    var visaoLoja = currentStore !== 'ALL' ? currentStore : 'Todas as lojas';
    var visaoTipo = currentVehicle !== 'TODOS' ? currentVehicle : 'Todos os veículos';
    var filtered = currentVehicle !== 'TODOS';

    var pmtMedio = out.operacional.length ? (function () {
      var vals = out.operacional.map(function (r) { return r.pmt; }).filter(function (v) { return v > 0; });
      return vals.length ? vals.reduce(function (s, v) { return s + v; }, 0) / vals.length : 0;
    })() : 0;
    var comBalao = out.operacional.filter(function (r) { return r.balao > 0; });
    var balaoMedio = comBalao.length ? comBalao.reduce(function (s, r) { return s + r.balao; }, 0) / comBalao.length : 0;

    var planoMap = {};
    out.planos.forEach(function (p) { planoMap[p.tipo] = p; });
    var planCards = ['SUBSIDIADO', 'REVERSÃO', 'COPARTICIPADO', 'BALÃO', 'LINEAR'].map(function (t) {
      return planCardHtml(A, t, planoMap[t] || { qtd: 0, valor: 0 });
    }).join('');

    var spfExtra = out.spfExtra || { detalhes: [], total: 0, comissao: 0 };
    var spfDetailRows = spfExtra.detalhes.map(function (r) {
      return '<tr><td>' + esc(r.loja) + '</td><td>' + esc(r.departamento) + '</td><td class="geNumCol">' + A.money(r.valor) + '</td><td class="geNumCol">' + A.money(r.comissao) + '</td></tr>';
    });

    var html =
      '<div class="geKpiGridPrimary">' +
      productionCardHtml(A, 'Produção Paga', out.pagaResumo, filtered) +
      productionCardHtml(A, 'Produção Faturada', out.fatResumo, filtered) +
      productionCardHtml(A, 'Produção Ag. Faturamento', out.agResumo, filtered) +
      productionCardHtml(A, 'Produção Total', out.totalPagoFatResumo, filtered) +
      '</div>' +

      '<div class="geKpiGridExec">' +
      kpiExec('Valor de Produção Total', A.money(out.totalPagoFatResumo.valor), 'Paga + Faturada • ' + visaoTipo) +
      kpiExec('Valor Total de Propostas Perdidas', A.money((out.cpf.recusadas || []).reduce(function (s, r) { return s + r.valor; }, 0)), 'Recusadas • ' + visaoTipo) +
      kpiExec('Valor de Propostas em Aberto', A.money((out.cpf.aprovadas || []).reduce(function (s, r) { return s + r.valor; }, 0)), 'Aprovadas • ' + visaoTipo) +
      '</div>' +

      '<h2>Classificação dos Planos</h2>' +
      '<div class="gePlanGrid">' + planCards + '</div>' +
      '<p class="geMuted">Classificação oficial por proposta, após o filtro obrigatório Op - Modalidade = FANDI: Código IF 999 ou SUBSIDIADO; Código IF 777 ou REVERSÃO; TC Devolvida 1 ou COPARTICIPADO; PMT Balão ou Valor Balão maior que zero; demais propostas = LINEAR.</p>' +

      '<h2>Planos por Loja e Departamento</h2>' +
      '<p class="geMuted">Novos (5 tipos) e Seminovos (3 tipos — Subsidiado/Coparticipado não são apurados para Seminovos nesta análise, mesmo escopo real de produção).</p>' +
      planStoreDeptTableHtml(out.planosLojaDept, 'Novos') +
      planStoreDeptTableHtml(out.planosLojaDept, 'Seminovos') +

      '<h2>SPF EXTRA</h2>' +
      '<div class="geKpiGridExec">' +
      kpiExec('Total SPF EXTRA', A.money(spfExtra.total), 'Valor total de opcionais SPF EXTRA') +
      kpiExec('Comissão Líquida SPF EXTRA', A.money(spfExtra.comissao), '70% sobre o total SPF EXTRA (regra fixa, não configurável — docs/GESTAO-COMMISSION-DECISION.md)') +
      '</div>' +
      '<div class="geTableWrap"><table class="geTable"><thead><tr>' + headerRow(['Loja', 'Departamento', 'SPF Total', 'Comissão Líquida 70%'], 2) + '</tr></thead>' +
      '<tbody>' + (spfDetailRows.length ? spfDetailRows.join('') : '<tr><td colspan="4" class="geMuted">Nenhum SPF Extra encontrado.</td></tr>') + '</tbody></table></div>' +

      '<h2>Indicadores de Apoio</h2>' +
      '<div class="geKpiGridSecondary">' +
      kpiSecondary('Visão', visaoLoja, currentStore !== 'ALL' ? 'unidade filtrada' : 'consolidado geral') +
      kpiSecondary('Tipo de veículo', visaoTipo, filtered ? 'filtro aplicado' : 'novos + seminovos') +
      kpiSecondary('Período analisado', periodo, 'faturamento ou pagamento no período') +
      kpiSecondary('Total geral (3 status)', out.operacional.length, 'Paga + Faturada + Ag. Faturamento') +
      kpiSecondary('Parcela média (PMT)', A.money(pmtMedio), 'média geral ponderada') +
      kpiSecondary('Operações com balão', comBalao.length, 'parcela média ' + A.money(balaoMedio)) +
      '</div>' +

      '<h2>Financiamentos por Loja</h2>' + dynamicStoreTableHtml(A, out.store, currentVehicle) +

      '<h2>Pagos, Faturados e AG. Faturamento por Unidade</h2>' + statusTableHtml(A, out.statusStore, 'loja') +

      '<h2>Pagos, Faturados e AG. Faturamento por Banco</h2>' + statusTableHtml(A, out.statusBank, 'banco') +

      '<h2>Propostas Recusadas Válidas por Loja</h2>' +
      '<div class="geKpiGridSecondary">' +
      kpiSecondary('Lojas com recusadas', out.cpf.recusadas.length, 'CPF único por loja') +
      kpiSecondary('CPFs com recusa líquida', out.cpf.recusadas.reduce(function (s, r) { return s + r.qtd; }, 0), 'cada CPF conta 1 vez') +
      kpiSecondary('Valor recusado', A.money(out.cpf.recusadas.reduce(function (s, r) { return s + r.valor; }, 0)), 'maior valor único por CPF válido') +
      kpiSecondary('Maior loja', out.cpf.recusadas[0] ? out.cpf.recusadas[0].loja : '-', (out.cpf.recusadas[0] ? out.cpf.recusadas[0].qtd : 0) + ' CPFs') +
      '</div>' + cpfTableHtml(A, out.cpf.recusadas, currentVehicle) +

      '<h2>Propostas Aprovadas Válidas por Loja</h2>' +
      '<div class="geKpiGridSecondary">' +
      kpiSecondary('Lojas com aprovadas', out.cpf.aprovadas.length, 'CPF único por loja') +
      kpiSecondary('CPFs aprovados válidos', out.cpf.aprovadas.reduce(function (s, r) { return s + r.qtd; }, 0), 'cada CPF conta 1 vez') +
      kpiSecondary('Valor aprovado', A.money(out.cpf.aprovadas.reduce(function (s, r) { return s + r.valor; }, 0)), 'maior valor único por CPF válido') +
      kpiSecondary('Maior loja', out.cpf.aprovadas[0] ? out.cpf.aprovadas[0].loja : '-', (out.cpf.aprovadas[0] ? out.cpf.aprovadas[0].qtd : 0) + ' CPFs') +
      '</div>' + cpfTableHtml(A, out.cpf.aprovadas, currentVehicle);

    document.getElementById('gePanel').innerHTML = html;
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
    document.getElementById('geFixtureSelect').addEventListener('change', function (e) { currentFixtureId = e.target.value; render(); });
    document.getElementById('geStoreFilter').addEventListener('change', function (e) { currentStore = e.target.value; render(); });
    document.getElementById('geDateStart').addEventListener('change', function (e) { currentDateStart = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.gePresetBtn').forEach(function (b) { b.classList.remove('gePresetActive'); }); render(); });
    document.getElementById('geDateEnd').addEventListener('change', function (e) { currentDateEnd = e.target.value; currentPreset = 'CUSTOM'; document.querySelectorAll('.gePresetBtn').forEach(function (b) { b.classList.remove('gePresetActive'); }); render(); });
    document.querySelectorAll('.gePresetBtn').forEach(function (btn) {
      btn.addEventListener('click', function () { applyPresetAndRender(btn.dataset.preset); });
    });
    document.querySelectorAll('.geVehicleBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        currentVehicle = btn.dataset.vehicle;
        document.querySelectorAll('.geVehicleBtn').forEach(function (b) { b.classList.toggle('geVehicleActive', b === btn); });
        render();
      });
    });
  }

  window.NX_GESTAO_PAGE = {
    render: function (outlet) {
      return loadFixtures().then(function () {
        var fixtureOptions = ['<option value="ALL">combinado (todos os cenários)</option>'].concat(
          fixturesData.map(function (c) { return '<option value="' + esc(c.id) + '">' + esc(c.id) + '</option>'; })
        ).join('');
        var storeOptions = ['<option value="ALL">Todas as lojas</option>'].concat(
          STORES.map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + '</option>'; })
        ).join('');
        outlet.innerHTML =
          '<div class="gePage">' +
          '<div class="geHeader"><div><h1>Análise F&amp;I do Grupo</h1><p>Análise operacional F&amp;I/FANDI consolidada do Grupo.</p></div></div>' +
          '<div class="geFixtureBar"><span class="geFixtureLabel">DADOS DE TESTE (NEXT_LOCAL)</span>' +
          '<label for="geFixtureSelect">fixture:</label><select id="geFixtureSelect">' + fixtureOptions + '</select></div>' +
          '<div class="geFilters">' +
          '<div class="geField"><label for="geStoreFilter">Loja / Unidade</label><select id="geStoreFilter">' + storeOptions + '</select></div>' +
          '<div class="geField"><label>Período rápido</label><div class="gePresetGroup">' +
          '<button type="button" class="gePresetBtn" data-preset="CURRENT_MONTH">Mês atual</button>' +
          '<button type="button" class="gePresetBtn" data-preset="PREVIOUS_MONTH">Mês anterior</button>' +
          '<button type="button" class="gePresetBtn" data-preset="LAST_6_MONTHS">Últimos 6 meses</button>' +
          '</div></div>' +
          '<div class="geField"><label for="geDateStart">Data inicial</label><input id="geDateStart" type="date" value="' + currentDateStart + '"></div>' +
          '<div class="geField"><label for="geDateEnd">Data final</label><input id="geDateEnd" type="date" value="' + currentDateEnd + '"></div>' +
          '</div>' +
          '<div class="geField" style="margin-bottom:var(--space-4)"><label>Tipo de veículo</label><div class="geVehicleGroup">' +
          '<button type="button" class="geVehicleBtn geVehicleActive" data-vehicle="TODOS">Todos</button>' +
          '<button type="button" class="geVehicleBtn" data-vehicle="Novos">Novos</button>' +
          '<button type="button" class="geVehicleBtn" data-vehicle="Seminovos">Seminovos</button>' +
          '</div></div>' +
          '<div id="gePanel"></div>' +
          '</div>';
        wireEvents();
        render();
      });
    }
  };
})();
