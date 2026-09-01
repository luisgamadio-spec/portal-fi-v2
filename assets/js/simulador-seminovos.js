/* PORTAL-NEXT V2 — Simulador Seminovos page (PORTAL-NEXT-08.1).
   Consumes the frozen PORTAL-NEXT-08 engines exclusively
   (window.NX_SIMULADOR_SEMINOVOS_ADAPTER / NX_SIMULADOR_SHARED /
   NX_CAMPANHA_ADAPTER / NX_CASH_CONVERSION_ADAPTER). Zero business
   math is duplicated here. Dead-code Gate 47: the top-level
   "Financiamento Linear" (calcularLinear) and "Taxas Subsidiadas"
   (calcularSubsidiadas) engines exist in the adapter for Gate 3
   completeness but are DELIBERATELY NOT exposed as modes below —
   confirmed dead/unreachable in real production (0 matching DOM
   markup), see docs/SIMULATOR-ENGINE-DISCOVERY-08.md Gate 33. */
(function () {
  'use strict';

  var UI = window.NX_SIM_UI;
  var S = window.NX_SIMULADOR_SHARED;
  var SN = window.NX_SIMULADOR_SEMINOVOS_ADAPTER;
  var CAMP = window.NX_CAMPANHA_ADAPTER;
  var CC = window.NX_CASH_CONVERSION_ADAPTER;

  var MODES = [
    { id: 'tradicional', group: 'Financiamento', label: 'Tradicional (Balão)' },
    { id: 'periodico', group: 'Financiamento', label: 'Semestral / Anual' },
    { id: 'ratetable', group: 'Financiamento', label: 'Financiamento Seminovos' },
    { id: 'campanha', group: 'Campanhas', label: 'Financiamento Campanha' },
    { id: 'triton', group: 'Campanhas', label: 'Semestral Triton' },
    { id: 'descobridor', group: 'Ferramentas', label: 'Descobridor de Taxa' },
    { id: 'antecipacao', group: 'Ferramentas', label: 'Antecipação de Parcelas' },
    { id: 'cashconversion', group: 'Ferramentas', label: 'Cash Conversion' }
  ];
  var MODE_DESC = {
    tradicional: 'Financiamento tradicional com balão opcional — a taxa depende do ano do veículo e da entrada.',
    periodico: 'Parcelas semestrais ou anuais — entrada mínima varia por prazo.',
    ratetable: 'Condições próprias por ano do veículo e faixa de entrada — inclui prazo de 50x.',
    campanha: 'Condições especiais por modelo — entrada mínima de 60% do valor de venda.',
    triton: 'Campanha Taxa 0% — entrada fixa de 60% para todos os modelos, sem alteração manual.',
    descobridor: 'Estima a taxa efetiva a partir do valor financiado, prazo e parcela.',
    antecipacao: 'Calcula o valor com desconto para antecipação de parcelas.',
    cashconversion: 'Compara o custo do financiamento com o rendimento de manter o capital aplicado.'
  };
  var TRAD_TERMS = [12, 24, 30, 36, 40, 42, 48];
  var PERIOD_TERMS = [24, 36, 48];
  var TRITON_MODELS = ['TRITON HPE', 'TRITON HPE-S', 'TRITON KATANA', 'TRITON SAVANA', 'TRITON TERRA'];

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
    ENTRADA_ABAIXO_DO_MINIMO: 'A entrada mínima permitida para este plano não foi atingida.',
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

  function switchMode(id) { currentMode = id; balloons = []; renderModeArea(); }

  function renderModeArea() {
    document.getElementById('smModeDesc').textContent = MODE_DESC[currentMode] || '';
    document.getElementById('smFormRegion').innerHTML = formHtml(currentMode);
    document.getElementById('smResultRegion').innerHTML = UI.emptyBlock('Preencha os campos e clique em Calcular.');
    wireForm(currentMode);
  }

  function formHtml(mode) {
    switch (mode) {
      case 'tradicional':
        return UI.moneyField('sBem', 'Valor do bem', 'R$ 80.000,00') +
          UI.moneyField('sEntrada', 'Entrada', 'R$ 16.000,00') +
          UI.numberField('sAno', 'Ano do veículo', 2022, { min: 1900, max: 2099, hint: 'Tabelas cadastradas para 2017–2024 e 2025–2099.' }) +
          UI.segmentedField('sPrazo', 'Prazo', TRAD_TERMS.map(function (t) { return { value: t, label: t + 'x' }; }), 24) +
          '<div class="field"><label>Balões</label><div class="smBalloonList" id="sBaloesList"></div>' +
          '<button type="button" class="btn btn-secondary btn-sm" id="sAddBalao">+ Adicionar balão</button></div>' +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'periodico':
        return UI.moneyField('sBem', 'Valor do bem', 'R$ 80.000,00') +
          UI.moneyField('sEntrada', 'Entrada', 'R$ 20.000,00') +
          UI.segmentedField('sPrazo', 'Prazo', PERIOD_TERMS.map(function (t) { return { value: t, label: t + 'x' }; }), 48) +
          UI.segmentedField('sTipo', 'Periodicidade', [{ value: 'semestral', label: 'Semestral' }, { value: 'anual', label: 'Anual' }], 'semestral') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'ratetable':
        return UI.numberField('sAnoRT', 'Ano do veículo', 2020, { min: 2007, max: 2099, hint: 'Tabela cadastrada para 2007–2099.' }) +
          UI.moneyField('sValorRT', 'Valor do veículo', 'R$ 80.000,00') +
          UI.moneyField('sEntradaRT', 'Entrada', 'R$ 0,00', 'Entrada permitida a partir de 0%.') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'campanha':
        return UI.selectField('sModelo', 'Modelo', CAMP._internal.MODELS.map(function (m) { return { value: m.name, label: m.name }; }), 'ECLIPSE CROSS HPE-S S-AWC') +
          UI.moneyField('sSale', 'Valor de venda', 'R$ 180.000,00') +
          UI.moneyField('sEntry', 'Entrada', 'R$ 108.000,00') +
          '<button type="button" class="btn btn-primary" id="sCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'triton':
        return UI.selectField('sModelo', 'Modelo', TRITON_MODELS.map(function (m) { return { value: m, label: m }; }), 'TRITON HPE') +
          UI.moneyField('sBem', 'Valor de venda', 'R$ 180.000,00', 'Entrada fixa de 60% — não editável.') +
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
      UI.wireSegmented('sPrazo', function () {});
      document.getElementById('sCalc').addEventListener('click', calcTradicional);
    } else if (mode === 'periodico') {
      UI.wireSegmented('sPrazo', function () {});
      UI.wireSegmented('sTipo', function () {});
      document.getElementById('sCalc').addEventListener('click', calcPeriodico);
    } else if (mode === 'ratetable') {
      document.getElementById('sCalc').addEventListener('click', calcRateTable);
    } else if (mode === 'campanha') {
      document.getElementById('sCalc').addEventListener('click', calcCampanha);
    } else if (mode === 'triton') {
      document.getElementById('sCalc').addEventListener('click', calcTriton);
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

  function calcTradicional() {
    var r = SN.calcularTradicional({
      bem: UI.moneyVal('sBem'), entrada: UI.moneyVal('sEntrada'), prazo: Number(UI.getSegmentedValue('sPrazo')),
      ano: UI.numVal('sAno'),
      baloes: balloons.filter(function (b) { return b.mes || b.valor; }).map(function (b) { return { mes: b.mes, valor: b.valor }; })
    });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var html = UI.resultHero('Parcela mensal', r.parcela);
    html += UI.secondaryGrid([{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Taxa aplicada', value: UI.pct2(r.taxa) }, { label: 'Limite de balão', value: UI.brl(r.limite) }]);
    if (r.totalBaloes) {
      var rows = balloons.filter(function (b) { return b.mes && b.valor; }).sort(function (a, b) { return a.mes - b.mes; })
        .map(function (b) { return '<tr><td>Parcela ' + b.mes + '</td><td class="num">' + UI.brl(b.valor) + '</td><td class="num">' + UI.brl(r.parcela + b.valor) + '</td></tr>'; }).join('');
      html += '<div class="smTableWrap"><table class="smTable"><thead><tr><th>Mês do balão</th><th>Valor do balão</th><th>Total devido no mês</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    }
    setResult(html);
  }
  function calcPeriodico() {
    var r = SN.calcularPeriodico({ bem: UI.moneyVal('sBem'), entrada: UI.moneyVal('sEntrada'), prazo: Number(UI.getSegmentedValue('sPrazo')), tipo: UI.getSegmentedValue('sTipo') });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error) + (r.minEntrada != null ? ' Mínimo: ' + UI.pct1(r.minEntrada) + '.' : ''))); return; }
    var html = UI.resultHero('Parcela ' + (UI.getSegmentedValue('sTipo') === 'semestral' ? 'semestral' : 'anual'), r.parcela);
    html += UI.secondaryGrid([{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Taxa aplicada', value: UI.pct2(r.taxa) }, { label: 'Nº de parcelas', value: String(r.meses.length) }]);
    setResult(html);
  }
  function calcRateTable() {
    var r = SN.calcularLinearRateTable({ ano: UI.numVal('sAnoRT'), valor: UI.moneyVal('sValorRT'), entrada: UI.moneyVal('sEntradaRT') });
    if (r.invalid) { setResult(UI.errorBlock('Verifique o ano do veículo e a entrada informada (entrada não pode ser maior que o valor do veículo, nem o percentual maior que 100%).')); return; }
    var html = UI.termGrid(r.terms.map(function (t) { return { prazo: t.prazo, payment: t.payment, rate: t.rate, best: false }; }));
    setResult('<p class="kpiLabel" style="margin-bottom:12px">Parcela por prazo — faixa ' + (r.band || '—') + ' · entrada ' + r.eBand + '%</p>' + html +
      '<p class="smFootnote">Financiado: ' + UI.brl(r.financiado) + '</p>');
  }
  function calcCampanha() {
    var r = CAMP.compute({ model: UI.textVal('sModelo'), saleValue: UI.moneyVal('sSale'), entryValue: UI.moneyVal('sEntry') });
    if (!r.valid) { setResult(UI.errorBlock('A entrada informada é menor que o mínimo exigido para este modelo (' + UI.pct1(r.minValue / (r.sale || 1)) + ' do valor de venda).')); return; }
    var html = UI.termGrid(r.terms.map(function (t) { return { prazo: t.prazo, payment: t.payment, rate: t.rate, best: false }; }));
    html += UI.secondaryGrid([
      { label: 'Financiado', value: UI.brl(r.financed) },
      { label: 'Rebate total — custo comercial da taxa', value: UI.brl(r.rebateTotal) },
      { label: 'Rebate Brabus', value: UI.brl(r.rebateBrabus) },
      { label: 'Rebate HPE', value: UI.brl(r.rebateHpe) },
      { label: 'Valor final de venda', value: UI.brl(r.finalSale) }
    ]);
    setResult('<p class="kpiLabel" style="margin-bottom:12px">Parcela por prazo</p>' + html);
  }
  function calcTriton() {
    var r = SN.calcularSemestralTriton({ bem: UI.moneyVal('sBem'), modelo: UI.textVal('sModelo') });
    if (r.error) { setResult(UI.errorBlock('Informe o valor de venda para calcular a campanha.')); return; }
    var html = UI.resultHero('Parcela (4x semestrais)', r.parcela);
    html += UI.secondaryGrid([
      { label: 'Entrada fixa (60%)', value: UI.brl(r.entrada) },
      { label: 'Financiado', value: UI.brl(r.financiado) },
      { label: 'Rebate total — custo comercial', value: UI.brl(r.rebateTotal) },
      { label: 'Rebate Brabus', value: UI.brl(r.rebateBrabus) },
      { label: 'Rebate HPE', value: UI.brl(r.rebateHpe) },
      { label: 'Valor final de venda', value: UI.brl(r.valorFinalVenda) }
    ]);
    setResult(html + '<p class="smFootnote">Entrada fixa de 60% para todos os modelos — não permite alteração manual.</p>');
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
      var groups = {};
      MODES.forEach(function (m) { (groups[m.group] = groups[m.group] || []).push(m); });
      var optgroups = Object.keys(groups).map(function (g) {
        return '<optgroup label="' + UI.esc(g) + '">' + groups[g].map(function (m) { return '<option value="' + m.id + '">' + UI.esc(m.label) + '</option>'; }).join('') + '</optgroup>';
      }).join('');
      outlet.innerHTML =
        '<div class="smPage">' +
        '<span class="smProductBadge">Simulador · Seminovos</span>' +
        '<div class="smHeader"><div><h1>Simulador de Financiamento — Seminovos</h1><p>Motores extraídos e verificados (PORTAL-NEXT-08) — 0 recálculo de fórmula nesta interface.</p></div></div>' +
        '<div class="smModeBar"><label for="smModeSelect">Modalidade</label><select class="select" id="smModeSelect">' + optgroups + '</select>' +
        '<p class="smModeDesc" id="smModeDesc"></p></div>' +
        '<div class="smGrid"><div class="smFormCard" id="smFormRegion"></div><div class="smResultCard" id="smResultRegion" aria-live="polite" aria-atomic="true"></div></div>' +
        '</div>';
      document.getElementById('smModeSelect').addEventListener('change', function (e) { switchMode(e.target.value); });
      renderModeArea();
      return Promise.resolve();
    }
  };
})();
