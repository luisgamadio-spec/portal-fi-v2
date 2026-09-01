/* PORTAL-NEXT V2 — Simuladores shared UI helpers (PORTAL-NEXT-08.1).
   Presentation-only: formatting, generic field builders, generic
   result-block builders. Contains ZERO business logic — every
   calculation call goes through the PORTAL-NEXT-08 frozen adapters
   (window.NX_SIMULADOR_SHARED/_NOVOS_ADAPTER/_SEMINOVOS_ADAPTER/
   _CAMPANHA_ADAPTER/_CASH_CONVERSION_ADAPTER). Money parsing reuses
   NX_SIMULADOR_SHARED.parseBRL (Gate 18: do not alter parseBRL
   semantics invisibly). */
(function () {
  'use strict';

  var S = window.NX_SIMULADOR_SHARED;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function brl(n) {
    if (n == null || !isFinite(n)) return '—';
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }
  // Digits-only currency formatting (no "R$"), for re-formatting the
  // RAW VALUE of an .inputAffix input on blur -- the .prefix span
  // already renders "R$" separately; writing brl()'s own "R$ ..." into
  // the input's value produced a real, human-caught "R$ R$ ..." bug
  // (PORTAL-NEXT-08.2 Change 3). Presentation only -- parseBRL's own
  // parsing semantics are untouched.
  function brlDigits(n) {
    if (n == null || !isFinite(n)) return '';
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function pct1(n) {
    if (n == null || !isFinite(n)) return '—';
    return (n * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
  }
  function pct2(n) {
    if (n == null || !isFinite(n)) return '—';
    return (n * 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
  }

  /* ---------- generic field markup builders ---------- */
  function moneyField(id, label, value, hint) {
    // .inputAffix .prefix already renders the "R$" glyph -- the raw
    // input value must be digits-only (matching the approved
    // reference's own convention, value="219990,00") to avoid a
    // doubled "R$ R$" display.
    var cleanValue = String(value || '').replace(/^R\$\s*/, '');
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label>' +
      '<div class="inputAffix"><span class="prefix">R$</span>' +
      '<input class="input mono" id="' + id + '" inputmode="decimal" value="' + esc(cleanValue) + '"></div>' +
      (hint ? '<span class="hint">' + esc(hint) + '</span>' : '') + '</div>';
  }
  function numberField(id, label, value, opts) {
    opts = opts || {};
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label>' +
      '<input class="input mono" id="' + id + '" type="number" inputmode="numeric"' +
      (opts.min != null ? ' min="' + opts.min + '"' : '') +
      (opts.max != null ? ' max="' + opts.max + '"' : '') +
      ' value="' + esc(value != null ? value : '') + '" placeholder="' + esc(opts.placeholder || '') + '">' +
      (opts.hint ? '<span class="hint">' + esc(opts.hint) + '</span>' : '') + '</div>';
  }
  function percentField(id, label, value, hint) {
    // Brazilian decimal-comma input (e.g. "0,80") -- deliberately NOT
    // type="number", which silently rejects comma decimals (requires a
    // dot regardless of locale) and would blank the field on render.
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label>' +
      '<input class="input mono" id="' + id + '" type="text" inputmode="decimal" value="' + esc(value || '') + '">' +
      (hint ? '<span class="hint">' + esc(hint) + '</span>' : '') + '</div>';
  }
  function dateField(id, label, value) {
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label>' +
      '<input class="input" id="' + id + '" type="date" value="' + esc(value || '') + '"></div>';
  }
  function segmentedField(id, label, options, activeValue, hint) {
    var buttons = options.map(function (o) {
      return '<button type="button" data-v="' + esc(o.value) + '" class="' + (String(o.value) === String(activeValue) ? 'active' : '') + '">' + esc(o.label) + '</button>';
    }).join('');
    return '<div class="field"><label>' + esc(label) + '</label><div class="segmented" id="' + id + '" role="group" aria-label="' + esc(label) + '">' + buttons + '</div>' +
      (hint ? '<span class="hint">' + esc(hint) + '</span>' : '') + '</div>';
  }
  function selectField(id, label, options, activeValue) {
    var opts = options.map(function (o) {
      return '<option value="' + esc(o.value) + '"' + (String(o.value) === String(activeValue) ? ' selected' : '') + '>' + esc(o.label) + '</option>';
    }).join('');
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label><select class="select" id="' + id + '">' + opts + '</select></div>';
  }

  function getSegmentedValue(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var active = el.querySelector('button.active');
    return active ? active.getAttribute('data-v') : null;
  }
  function wireSegmented(id, onChange) {
    var el = document.getElementById(id);
    if (!el) return;
    el.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        el.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        onChange(btn.getAttribute('data-v'));
      });
    });
  }
  function wireMoneyMask(id, onInput) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('blur', function () { el.value = brlDigits(S.parseBRL(el.value)); if (onInput) onInput(); });
    el.addEventListener('input', function () { if (onInput) onInput(); });
  }

  function moneyVal(id) { var el = document.getElementById(id); return el ? S.parseBRL(el.value) : 0; }
  function numVal(id) { var el = document.getElementById(id); return el ? Number(el.value) : NaN; }
  function textVal(id) { var el = document.getElementById(id); return el ? el.value : ''; }

  /* ---------- generic result blocks ---------- */
  function resultHero(label, value) {
    return '<div class="resultHero"><p class="kpiLabel">' + esc(label) + '</p><p class="resultValue">' + esc(brl(value)) + '</p></div>';
  }
  function secondaryGrid(items) {
    // items: [{label, value (already-formatted string)}]
    return '<div class="resultSecondaryGrid">' + items.map(function (it) {
      return '<div><p class="kpiLabel">' + esc(it.label) + '</p><p class="val">' + esc(it.value) + '</p></div>';
    }).join('') + '</div>';
  }
  function termGrid(items) {
    // items: [{prazo, payment (number|null), rate (number|null), best (bool)}]
    return '<div class="smTermGrid">' + items.map(function (it) {
      return '<div class="smTermCard' + (it.best ? ' best' : '') + '"><div class="term">' + it.prazo + 'x</div>' +
        (it.payment != null ? '<div class="payment">' + esc(brl(it.payment)) + '</div>' + (it.rate != null ? '<div class="rate">' + esc(pct2(it.rate)) + ' a.m.</div>' : '') : '<div class="unavailable">—</div>') +
        '</div>';
    }).join('') + '</div>';
  }
  function errorBlock(text) {
    return '<div class="errorState"><div class="t">Não foi possível calcular</div>' + esc(text) + '</div>';
  }
  function emptyBlock(text) {
    return '<div class="emptyState"><div class="t">Nenhum cálculo ainda</div>' + esc(text) + '</div>';
  }
  function warningBlock(text) {
    return '<div class="smWarning">' + esc(text) + '</div>';
  }

  window.NX_SIM_UI = {
    esc: esc, brl: brl, brlDigits: brlDigits, pct1: pct1, pct2: pct2,
    moneyField: moneyField, numberField: numberField, percentField: percentField, dateField: dateField,
    segmentedField: segmentedField, selectField: selectField,
    getSegmentedValue: getSegmentedValue, wireSegmented: wireSegmented, wireMoneyMask: wireMoneyMask,
    moneyVal: moneyVal, numVal: numVal, textVal: textVal,
    resultHero: resultHero, secondaryGrid: secondaryGrid, termGrid: termGrid,
    errorBlock: errorBlock, emptyBlock: emptyBlock, warningBlock: warningBlock
  };
})();
