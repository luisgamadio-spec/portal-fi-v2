/* PORTAL-NEXT V2 — Simulador Novos page (PORTAL-NEXT-08.1).
   Consumes the frozen PORTAL-NEXT-08 engines exclusively
   (window.NX_SIMULADOR_NOVOS_ADAPTER / NX_SIMULADOR_SHARED /
   NX_CAMPANHA_ADAPTER / NX_CASH_CONVERSION_ADAPTER). Zero business
   math is duplicated here — every number shown comes directly from an
   adapter return value. See docs/SIMULATOR-UI-MIGRATION-08-1.md. */
(function () {
  'use strict';

  var UI = window.NX_SIM_UI;
  var S = window.NX_SIMULADOR_SHARED;
  var N = window.NX_SIMULADOR_NOVOS_ADAPTER;
  var CAMP = window.NX_CAMPANHA_ADAPTER;
  var CC = window.NX_CASH_CONVERSION_ADAPTER;

  var MODES = [
    { id: 'tradicional', group: 'Financiamento', label: 'Tradicional (Balão)' },
    { id: 'periodico', group: 'Financiamento', label: 'Semestral / Anual' },
    { id: 'parcelaunica', group: 'Financiamento', label: 'Parcela Única' },
    { id: 'linear', group: 'Financiamento', label: 'Financiamento Linear' },
    { id: 'campanha', group: 'Campanhas', label: 'Financiamento Campanha' },
    { id: 'subsidiadas', group: 'Campanhas', label: 'Taxas Subsidiadas' },
    { id: 'triton', group: 'Campanhas', label: 'Semestral Triton / Outlander' },
    { id: 'descobridor', group: 'Ferramentas', label: 'Descobridor de Taxa' },
    { id: 'antecipacao', group: 'Ferramentas', label: 'Antecipação de Parcelas' },
    { id: 'cashconversion', group: 'Ferramentas', label: 'Cash Conversion' }
  ];
  var MODE_DESC = {
    tradicional: 'Financiamento tradicional com balão opcional — entrada mínima de 10%.',
    periodico: 'Parcelas semestrais ou anuais — entrada mínima varia por prazo.',
    parcelaunica: 'Uma única parcela no mês 25, após 24 meses de carência — entrada mínima de 50%.',
    linear: 'Parcela mensal fixa, todos os prazos calculados automaticamente.',
    campanha: 'Condições especiais por modelo — entrada mínima de 60% do valor de venda.',
    subsidiadas: 'Comparação de taxas subsidiadas por prazo — entrada mínima de 50%.',
    triton: 'Campanha Taxa 0% — entrada fixa por modelo, sem alteração manual.',
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
    SEM_REGRA_CADASTRADA: 'Prazo sem regra cadastrada na tabela para a faixa de entrada informada.',
    BALAO_FORA_DO_PRAZO: 'Existe balão fora do prazo. Use parcelas entre 1 e o prazo escolhido.',
    BALAO_DUPLICADO: 'Não é permitido inserir dois balões na mesma parcela.',
    BALAO_VALOR_INVALIDO: 'Informe valor válido para todos os balões.',
    BALOES_ACIMA_DO_LIMITE: 'A soma dos balões ultrapassa o valor máximo permitido, calculado sobre o valor financiado.',
    BALOES_ALTOS_DEMAIS: 'Os balões escolhidos são altos demais para gerar uma parcela mensal válida.',
    ENTRADA_ABAIXO_DO_MINIMO: 'A entrada mínima permitida para este plano não foi atingida.',
    BEM_INVALIDO: 'Informe um Valor do Bem válido.',
    ENTRADA_MINIMA_50PCT: 'A entrada mínima permitida para esta modalidade é de 50%.',
    INFORME_BEM: 'Informe o Valor do Bem.',
    INFORME_ENTRADA: 'Informe o Valor da Entrada.',
    FINANCIADO_INVALIDO: 'O valor financiado precisa ser maior que zero.',
    MIN_VENDA_MAIOR_QUE_BEM: 'O valor mínimo de venda deve ser menor que o valor do bem.',
    PRAZO_INVALIDO: 'Informe um prazo válido entre 1 e 60 meses.',
    PARCELA_INVALIDA: 'Informe uma parcela maior que zero.',
    PARCELA_INCOMPATIVEL: 'Parcela incompatível com os dados informados. Revise os valores.',
    PRIMEIRA_PARCELA_AUSENTE: 'Informe a data da primeira parcela.',
    DATA_AUSENTE: 'Informe a data desejada para antecipação.',
    INTERVALO_INVALIDO: 'Informe um intervalo válido de parcelas.',
    PARCELA_INVALIDA_INTERVALO: 'Informe uma parcela válida dentro do prazo.',
    NENHUMA_PARCELA_FUTURA: 'Nenhuma parcela futura encontrada. Revise a data de antecipação.'
  };
  function errMsg(code) { return ERROR_MSG[code] || 'Dados inválidos para este cálculo.'; }

  var currentMode = MODES[0].id;
  var balloons = []; // {mes, valor} for Tradicional

  function switchMode(id) {
    currentMode = id;
    balloons = [];
    renderModeArea();
  }

  function renderModeArea() {
    document.getElementById('smModeDesc').textContent = MODE_DESC[currentMode] || '';
    var formRegion = document.getElementById('smFormRegion');
    var resultRegion = document.getElementById('smResultRegion');
    formRegion.innerHTML = formHtml(currentMode);
    resultRegion.innerHTML = UI.emptyBlock('Preencha os campos e clique em Calcular.');
    wireForm(currentMode);
  }

  /* ---------- forms ---------- */
  function formHtml(mode) {
    switch (mode) {
      case 'tradicional':
        return UI.moneyField('nBem', 'Valor do bem', 'R$ 100.000,00') +
          UI.moneyField('nEntrada', 'Entrada', 'R$ 20.000,00') +
          UI.segmentedField('nPrazo', 'Prazo', TRAD_TERMS.map(function (t) { return { value: t, label: t + 'x' }; }), 48) +
          '<div class="field"><label>Balões</label>' +
          '<div class="smBalloonList" id="nBaloesList"></div>' +
          '<button type="button" class="btn btn-secondary btn-sm" id="nAddBalao">+ Adicionar balão</button></div>' +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'periodico':
        return UI.moneyField('nBem', 'Valor do bem', 'R$ 100.000,00') +
          UI.moneyField('nEntrada', 'Entrada', 'R$ 20.000,00') +
          UI.segmentedField('nPrazo', 'Prazo', PERIOD_TERMS.map(function (t) { return { value: t, label: t + 'x' }; }), 48) +
          UI.segmentedField('nTipo', 'Periodicidade', [{ value: 'semestral', label: 'Semestral' }, { value: 'anual', label: 'Anual' }], 'semestral') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'parcelaunica':
        return UI.moneyField('nBem', 'Valor do bem', 'R$ 100.000,00') +
          UI.moneyField('nEntrada', 'Entrada', 'R$ 50.000,00') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'linear':
        return UI.moneyField('nBem', 'Valor do bem', 'R$ 100.000,00') +
          UI.moneyField('nEntrada', 'Entrada', 'R$ 20.000,00', 'Recalcula automaticamente, sem botão Calcular (comportamento original).');
      case 'campanha':
        return UI.selectField('nModelo', 'Modelo', CAMP._internal.MODELS.map(function (m) { return { value: m.name, label: m.name }; }), 'ECLIPSE CROSS HPE-S S-AWC') +
          UI.moneyField('nSale', 'Valor de venda', 'R$ 200.000,00') +
          UI.moneyField('nEntry', 'Entrada', 'R$ 120.000,00') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'subsidiadas':
        return UI.moneyField('nBem', 'Valor do bem', 'R$ 100.000,00') +
          UI.moneyField('nEntrada', 'Entrada', 'R$ 50.000,00') +
          UI.moneyField('nMinVenda', 'Valor mínimo de venda (opcional)', '') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'triton':
        return UI.selectField('nModelo', 'Modelo', TRITON_MODELS.map(function (m) { return { value: m, label: m }; }), 'TRITON HPE') +
          UI.moneyField('nBem', 'Valor de venda', 'R$ 200.000,00', 'Entrada fixa de 60% — não editável.') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'descobridor':
        return UI.moneyField('nFinanciado', 'Valor financiado', 'R$ 80.000,00') +
          UI.numberField('nPrazoNum', 'Prazo (meses)', 48, { min: 1, max: 60 }) +
          UI.moneyField('nParcela', 'Parcela', 'R$ 2.200,00') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'antecipacao':
        return UI.numberField('nPrazoNum', 'Prazo (meses)', 48, { min: 1, max: 60 }) +
          UI.moneyField('nParcela', 'Valor da parcela mensal', 'R$ 2.000,00') +
          UI.dateField('nPrimeira', 'Data da primeira parcela', '') +
          UI.dateField('nData', 'Data desejada para antecipação', '') +
          UI.segmentedField('nTipoAnt', 'O que antecipar', [{ value: 'todo', label: 'Contrato todo' }, { value: 'algumas', label: 'Algumas parcelas' }, { value: 'uma', label: 'Uma parcela' }], 'todo') +
          '<div id="nAntExtra"></div>' +
          '<span class="hint">Balões não são suportados nesta versão da interface (o motor extraído suporta; ver limitações conhecidas).</span>' +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      case 'cashconversion':
        return UI.moneyField('nCapital', 'Capital', 'R$ 100.000,00') +
          UI.moneyField('nParcelaCC', 'Parcela ofertada', 'R$ 2.500,00') +
          UI.numberField('nPrazoCC', 'Prazo (meses)', 36, { min: 1, max: 60 }) +
          UI.percentField('nTaxaCC', 'Taxa de aplicação mensal (%)', '0,80') +
          '<button type="button" class="btn btn-primary" id="nCalc" style="width:100%;margin-top:6px">Calcular</button>';
      default:
        return '';
    }
  }

  function antExtraHtml(tipo) {
    if (tipo === 'algumas') return UI.numberField('nDe', 'De (parcela nº)', 1, { min: 1 }) + UI.numberField('nAte', 'Até (parcela nº)', 12, { min: 1 });
    if (tipo === 'uma') return UI.numberField('nParcelaUnicaNum', 'Parcela nº', 1, { min: 1 });
    return '';
  }

  function renderBaloesList() {
    var list = document.getElementById('nBaloesList');
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
      el.addEventListener('blur', function () {
        if (el.getAttribute('data-bfield') === 'valor') el.value = UI.brl(S.parseBRL(el.value));
      });
    });
    list.querySelectorAll('[data-bremove]').forEach(function (el) {
      el.addEventListener('click', function () { balloons.splice(Number(el.getAttribute('data-bremove')), 1); renderBaloesList(); });
    });
  }

  function wireForm(mode) {
    if (mode === 'tradicional') {
      renderBaloesList();
      document.getElementById('nAddBalao').addEventListener('click', function () { balloons.push({ mes: null, valor: 0, valorText: '' }); renderBaloesList(); });
      UI.wireSegmented('nPrazo', function () {});
      document.getElementById('nCalc').addEventListener('click', function () { calcTradicional(); });
    } else if (mode === 'periodico') {
      UI.wireSegmented('nPrazo', function () {});
      UI.wireSegmented('nTipo', function () {});
      document.getElementById('nCalc').addEventListener('click', calcPeriodico);
    } else if (mode === 'parcelaunica') {
      document.getElementById('nCalc').addEventListener('click', runParcelaUnica);
    } else if (mode === 'linear') {
      UI.wireMoneyMask('nBem', calcLinear);
      UI.wireMoneyMask('nEntrada', calcLinear);
      calcLinear();
    } else if (mode === 'campanha') {
      document.getElementById('nCalc').addEventListener('click', calcCampanha);
    } else if (mode === 'subsidiadas') {
      document.getElementById('nCalc').addEventListener('click', calcSubsidiadas);
    } else if (mode === 'triton') {
      document.getElementById('nCalc').addEventListener('click', calcTriton);
    } else if (mode === 'descobridor') {
      document.getElementById('nCalc').addEventListener('click', calcDescobridor);
    } else if (mode === 'antecipacao') {
      document.getElementById('nAntExtra').innerHTML = antExtraHtml('todo');
      UI.wireSegmented('nTipoAnt', function (v) { document.getElementById('nAntExtra').innerHTML = antExtraHtml(v); });
      document.getElementById('nCalc').addEventListener('click', calcAntecipacao);
    } else if (mode === 'cashconversion') {
      document.getElementById('nCalc').addEventListener('click', calcCashConversion);
    }
  }

  function setResult(html) { document.getElementById('smResultRegion').innerHTML = html; }

  /* ---------- calculations (adapter calls only) ---------- */
  function calcTradicional() {
    var r = N.calcularTradicional({
      bem: UI.moneyVal('nBem'), entrada: UI.moneyVal('nEntrada'),
      prazo: Number(UI.getSegmentedValue('nPrazo')),
      baloes: balloons.filter(function (b) { return b.mes || b.valor; }).map(function (b) { return { mes: b.mes, valor: b.valor }; })
    });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var html = UI.resultHero('Parcela mensal', r.parcela);
    var secondary = [{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Taxa aplicada', value: UI.pct2(r.taxa) }, { label: 'Limite de balão', value: UI.brl(r.limite) }];
    html += UI.secondaryGrid(secondary);
    if (r.totalBaloes) {
      var rows = balloons.filter(function (b) { return b.mes && b.valor; }).sort(function (a, b) { return a.mes - b.mes; })
        .map(function (b) { return '<tr><td>Parcela ' + b.mes + '</td><td class="num">' + UI.brl(b.valor) + '</td><td class="num">' + UI.brl(r.parcela + b.valor) + '</td></tr>'; }).join('');
      html += '<div class="smTableWrap"><table class="smTable"><thead><tr><th>Mês do balão</th><th>Valor do balão</th><th>Total devido no mês</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    }
    setResult(html);
  }
  function calcPeriodico() {
    var r = N.calcularPeriodico({ bem: UI.moneyVal('nBem'), entrada: UI.moneyVal('nEntrada'), prazo: Number(UI.getSegmentedValue('nPrazo')), tipo: UI.getSegmentedValue('nTipo') });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error) + (r.minEntrada != null ? ' Mínimo: ' + UI.pct1(r.minEntrada) + '.' : ''))); return; }
    var html = UI.resultHero('Parcela ' + (UI.getSegmentedValue('nTipo') === 'semestral' ? 'semestral' : 'anual'), r.parcela);
    html += UI.secondaryGrid([{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Taxa aplicada', value: UI.pct2(r.taxa) }, { label: 'Nº de parcelas', value: String(r.meses.length) }]);
    setResult(html);
  }
  function runParcelaUnica() {
    var r = N.calcularParcelaUnica({ bem: UI.moneyVal('nBem'), entrada: UI.moneyVal('nEntrada') });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error) + (r.minEntrada != null ? ' Mínimo: ' + UI.pct1(r.minEntrada) + '.' : ''))); return; }
    var html = UI.resultHero('Parcela única (mês 25)', r.parcela);
    html += UI.secondaryGrid([{ label: 'Entrada', value: UI.pct1(r.pe) }, { label: 'Financiado', value: UI.brl(r.fin) }, { label: 'Coeficiente', value: r.coef.toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) }]);
    setResult(html);
  }
  function calcLinear() {
    var r = N.calcularLinear({ bem: UI.moneyVal('nBem'), entrada: UI.moneyVal('nEntrada') });
    if (r.empty) { setResult(UI.emptyBlock('Preencha o valor do bem e a entrada para visualizar todos os prazos.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var valid = r.itens.filter(function (x) { return x.parcela > 0; });
    var menor = valid.length ? Math.min.apply(null, valid.map(function (x) { return x.parcela; })) : null;
    var html = UI.termGrid(r.itens.map(function (x) { return { prazo: x.prazo, payment: x.parcela, rate: null, best: menor != null && x.parcela != null && Math.abs(x.parcela - menor) < 0.01 }; }));
    setResult('<p class="kpiLabel" style="margin-bottom:12px">Parcela por prazo — faixa de entrada ' + UI.pct1(r.faixa) + '</p>' + html);
  }
  function calcCampanha() {
    var r = CAMP.compute({ model: UI.textVal('nModelo'), saleValue: UI.moneyVal('nSale'), entryValue: UI.moneyVal('nEntry') });
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
  function calcSubsidiadas() {
    var r = N.calcularSubsidiadas({ bem: UI.moneyVal('nBem'), entrada: UI.moneyVal('nEntrada'), minVenda: UI.moneyVal('nMinVenda') });
    if (r.empty) { setResult(UI.emptyBlock('Preencha os campos e clique em Calcular.')); return; }
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var byTaxa = {};
    r.rows.forEach(function (row) { (byTaxa[row.taxa] = byTaxa[row.taxa] || []).push(row); });
    var groupsHtml = Object.keys(byTaxa).sort(function (a, b) { return Number(a) - Number(b); }).map(function (taxa) {
      var rows = byTaxa[taxa].sort(function (a, b) { return a.prazo - b.prazo; }).map(function (row) {
        var pillCls = row.melhor ? 'excellent' : (r.minVenda > 0 ? (row.viavel ? 'good' : 'bad') : 'neutral');
        var status = row.melhor ? 'Melhor opção' : (r.minVenda > 0 ? (row.viavel ? 'Dentro do mínimo' : 'Abaixo do mínimo') : 'Simulado');
        return '<div class="smCompareRow' + (row.melhor ? ' best' : '') + '">' +
          '<div><span class="lbl">Prazo</span><span class="v">' + row.prazo + 'x</span></div>' +
          '<div><span class="lbl">Parcela</span><span class="v">' + UI.brl(row.parcela) + '</span></div>' +
          '<div><span class="lbl">Rebate — custo comercial</span><span class="v">' + UI.brl(row.rebateValor) + '</span></div>' +
          '<div><span class="lbl">Valor final de venda</span><span class="v">' + UI.brl(row.valorFinalVenda) + '</span></div>' +
          '<span class="smPill ' + pillCls + '">' + status + '</span></div>';
      }).join('');
      return '<div class="smCompareGroup"><div class="smCompareGroupHead"><strong>Taxa ' + UI.pct2(Number(taxa)) + '</strong></div>' + rows + '</div>';
    }).join('');
    setResult('<div class="smCompareGroups">' + groupsHtml + '</div>' +
      '<p class="smFootnote">Rebate é o custo comercial da taxa subsidiada — nunca um desconto concedido ao cliente. Valor final de venda já considera o valor líquido para a loja.</p>');
  }
  function calcTriton() {
    var r = N.calcularSemestralTriton({ bem: UI.moneyVal('nBem'), modelo: UI.textVal('nModelo') });
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error) || 'Informe o valor de venda para calcular a campanha.')); return; }
    var html = UI.resultHero('Parcela (4x semestrais)', r.parcela);
    html += UI.secondaryGrid([
      { label: 'Entrada fixa (' + UI.pct1(r.entradaPct != null ? r.entradaPct : 0.6) + ')', value: UI.brl(r.entrada) },
      { label: 'Financiado', value: UI.brl(r.financiado) },
      { label: 'Rebate total — custo comercial', value: UI.brl(r.rebateTotal) },
      { label: 'Rebate Brabus', value: UI.brl(r.rebateBrabus) },
      { label: 'Rebate HPE', value: UI.brl(r.rebateHpe) },
      { label: 'Valor final de venda', value: UI.brl(r.valorFinalVenda) }
    ]);
    setResult(html + '<p class="smFootnote">Entrada fixa por modelo — não permite alteração manual.</p>');
  }
  function calcDescobridor() {
    var r = N.calcularDescobridor({ financiado: UI.moneyVal('nFinanciado'), prazo: UI.numVal('nPrazoNum'), parcela: UI.moneyVal('nParcela') });
    if (r.error) { setResult(UI.errorBlock(errMsg(r.error))); return; }
    var html = '<div class="resultHero"><p class="kpiLabel">Taxa efetiva mensal (CET)</p><p class="resultValue">' + UI.pct2(r.taxaCetMes) + '</p></div>';
    html += UI.secondaryGrid([{ label: 'Taxa nominal estimada', value: UI.pct2(r.taxaNet) }, { label: 'Total pago', value: UI.brl(r.total) }, { label: 'Juros totais', value: UI.brl(r.juros) }]);
    setResult(html);
  }
  function calcAntecipacao() {
    var tipo = UI.getSegmentedValue('nTipoAnt');
    var r = N.calcularAntecipacao({
      prazo: UI.numVal('nPrazoNum'), parcela: UI.moneyVal('nParcela'),
      primeiraParcela: UI.textVal('nPrimeira') ? new Date(UI.textVal('nPrimeira') + 'T00:00:00') : null,
      dataAntecipacao: UI.textVal('nData') ? new Date(UI.textVal('nData') + 'T00:00:00') : null,
      tipo: tipo, de: UI.numVal('nDe'), ate: UI.numVal('nAte'), parcelaUnica: UI.numVal('nParcelaUnicaNum'), baloes: []
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
    var taxaPct = Number(String(UI.textVal('nTaxaCC')).replace(',', '.')) || 0;
    var r = CC.compute({ capital: UI.moneyVal('nCapital'), parcela: UI.moneyVal('nParcelaCC'), prazoMeses: UI.numVal('nPrazoCC'), taxaAplicacao: taxaPct / 100 });
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

  window.NX_SIMULADOR_NOVOS_PAGE = {
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
        '<span class="smProductBadge">Simulador · Novos</span>' +
        '<div class="smHeader"><div><h1>Simulador de Financiamento — Novos</h1><p>Motores extraídos e verificados (PORTAL-NEXT-08) — 0 recálculo de fórmula nesta interface.</p></div></div>' +
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
