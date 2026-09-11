/* SIM-NAV-LAB-1 -- Premium Simulator Navigation LAB.
   Standalone LAB script. Never imported by any production module.
   Content below is copied read-only from the REAL, approved MODES
   arrays (assets/js/simulador-novos.js / simulador-seminovos.js) --
   labels and grouping are never invented here, per the brief's own
   "same content across concepts" / "do not invent Seminovos options"
   requirement. Nothing here computes a financial value; this is
   navigation-presentation only. */
(function () {
  'use strict';

  // ---------- content (read-only copy of the real MODES arrays) ----------
  var INVENTORIES = {
    novos: [
      { group: 'Financiamento', items: [
        { id: 'tradicional', label: 'Tradicional (Balão)' },
        { id: 'periodico', label: 'Semestral / Anual' },
        { id: 'parcelaunica', label: 'Parcela Única' },
        { id: 'linear', label: 'Financiamento Linear' }
      ]},
      { group: 'Campanhas', items: [
        { id: 'campanha', label: 'Plano Coparticipado' },
        { id: 'subsidiadas', label: 'Taxas Subsidiadas' },
        { id: 'triton', label: 'Semestral Triton / Outlander' }
      ]},
      { group: 'Ferramentas', items: [
        { id: 'descobridor', label: 'Descobridor de Taxa' },
        { id: 'antecipacao', label: 'Antecipação de Parcelas' },
        { id: 'cashconversion', label: 'Cash Conversion' }
      ]}
    ],
    seminovos: [
      { group: 'Financiamento', items: [
        { id: 'tradicional', label: 'Tradicional (Balão)' },
        { id: 'ratetable', label: 'Linear' }
      ]},
      { group: 'Ferramentas', items: [
        { id: 'descobridor', label: 'Descobridor de Taxa' },
        { id: 'antecipacao', label: 'Antecipação de Parcelas' },
        { id: 'cashconversion', label: 'Cash Conversion' }
      ]}
    ]
  };

  var HEADER_BY_INVENTORY = {
    novos: {
      eyebrow: 'SIMULADOR · NOVOS',
      title: 'Simulador de Financiamento — Novos',
      subtitle: 'Motores extraídos e verificados (PORTAL-NEXT-08) — 0 recálculo de fórmula nesta interface.'
    },
    seminovos: {
      eyebrow: 'SIMULADOR · SEMINOVOS',
      title: 'Simulador de Financiamento — Seminovos',
      subtitle: 'Motores extraídos e verificados — 0 recálculo de fórmula nesta interface.'
    }
  };

  var CONCEPT_META = {
    a: { label: 'A — Premium Segmented', desc: 'Uma superfície segmentada por categoria, sem botões flutuantes -- o vermelho marca a seleção, não preenche.' },
    b: { label: 'B — Minimal Navigation Tiles', desc: 'Blocos baixos e uniformes em grade -- geometria consistente, nunca definida pelo tamanho do texto.' },
    c: { label: 'C — Cockpit Command List', desc: 'Lista técnica, quase sem caixas -- índice numérico, separadores finos, leitura de instrumento.' },
    d: { label: 'D — Hybrid Luxury Navigation', desc: 'Três instrumentos contínuos (um por categoria) com linhas internas, não dez botões soltos.' }
  };

  // ---------- state ----------
  var state = {
    inventory: 'novos',
    concept: 'a',
    active: {
      novos: { a: 'tradicional', b: 'tradicional', c: 'tradicional', d: 'tradicional' },
      seminovos: { a: 'tradicional', b: 'tradicional', c: 'tradicional', d: 'tradicional' }
    }
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function chevron() {
    return '<svg class="labChevron" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M6 3.5L10.5 8L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  // ---------- frame (shared header context, per concept §8) ----------
  function frameHtml(conceptKey, navHtml) {
    var h = HEADER_BY_INVENTORY[state.inventory];
    var meta = CONCEPT_META[conceptKey];
    return (
      '<div class="labFrame">' +
        '<div class="labConceptLabel"><span class="labConceptLabelName">' + esc(meta.label) + '</span><span class="labConceptLabelDesc">' + esc(meta.desc) + '</span></div>' +
        '<div class="labSimHeader">' +
          '<span class="modEyebrow">' + esc(h.eyebrow) + '</span>' +
          '<h1 class="modTitle labSimTitle">' + esc(h.title) + '</h1>' +
          '<p class="modSubtitle">' + esc(h.subtitle) + '</p>' +
        '</div>' +
        navHtml +
        '<div class="labPlaceholder">Área do simulador</div>' +
      '</div>'
    );
  }

  // ---------- Concept A: Premium Segmented ----------
  function conceptA(inv, activeMap) {
    return '<nav class="labNavA" aria-label="Modalidade de financiamento">' +
      inv.map(function (g) {
        return '<div class="labAGroup">' +
          '<span class="labGroupLabel">' + esc(g.group) + '</span>' +
          '<div class="labASeg" role="radiogroup" aria-label="' + esc(g.group) + '">' +
          g.items.map(function (m) {
            var active = m.id === activeMap.a;
            return '<button type="button" class="labASegItem' + (active ? ' active' : '') + '" data-concept="a" data-mode="' + m.id + '" role="radio" aria-checked="' + active + '">' + esc(m.label) + '</button>';
          }).join('') +
          '</div></div>';
      }).join('') +
      '</nav>';
  }

  // ---------- Concept B: Minimal Navigation Tiles ----------
  function conceptB(inv, activeMap) {
    return '<nav class="labNavB" aria-label="Modalidade de financiamento">' +
      inv.map(function (g) {
        return '<div class="labBGroup">' +
          '<span class="labGroupLabel">' + esc(g.group) + '</span>' +
          '<div class="labBGrid" role="group" aria-label="' + esc(g.group) + '">' +
          g.items.map(function (m) {
            var active = m.id === activeMap.b;
            return '<button type="button" class="labBTile' + (active ? ' active' : '') + '" data-concept="b" data-mode="' + m.id + '" aria-pressed="' + active + '">' +
              '<span class="labBTileLabel">' + esc(m.label) + '</span>' + chevron() +
              '</button>';
          }).join('') +
          '</div></div>';
      }).join('') +
      '</nav>';
  }

  // ---------- Concept C: Cockpit Command List ----------
  function conceptC(inv, activeMap) {
    return '<nav class="labNavC" aria-label="Modalidade de financiamento">' +
      inv.map(function (g) {
        return '<div class="labCGroup">' +
          '<span class="labGroupLabel">' + esc(g.group) + '</span>' +
          '<div class="labCList" role="group" aria-label="' + esc(g.group) + '">' +
          g.items.map(function (m, i) {
            var active = m.id === activeMap.c;
            var idx = String(i + 1).padStart(2, '0');
            return '<button type="button" class="labCRow' + (active ? ' active' : '') + '" data-concept="c" data-mode="' + m.id + '" aria-pressed="' + active + '">' +
              '<span class="labCIndex">' + idx + '</span>' +
              '<span class="labCLabel">' + esc(m.label) + '</span>' +
              chevron() +
              '</button>';
          }).join('') +
          '</div></div>';
      }).join('') +
      '</nav>';
  }

  // ---------- Concept D: Hybrid Luxury Navigation ----------
  function conceptD(inv, activeMap) {
    return '<nav class="labNavD" aria-label="Modalidade de financiamento">' +
      inv.map(function (g) {
        return '<div class="labDGroup">' +
          '<span class="labGroupLabel">' + esc(g.group) + '</span>' +
          '<div class="labDPanel" role="group" aria-label="' + esc(g.group) + '">' +
          g.items.map(function (m) {
            var active = m.id === activeMap.d;
            return '<button type="button" class="labDRow' + (active ? ' active' : '') + '" data-concept="d" data-mode="' + m.id + '" aria-pressed="' + active + '">' +
              '<span class="labDLabel">' + esc(m.label) + '</span>' + chevron() +
              '</button>';
          }).join('') +
          '</div></div>';
      }).join('') +
      '</nav>';
  }

  var RENDERERS = { a: conceptA, b: conceptB, c: conceptC, d: conceptD };

  function renderConcept(key) {
    var inv = INVENTORIES[state.inventory];
    var activeMap = state.active[state.inventory];
    return frameHtml(key, RENDERERS[key](inv, activeMap));
  }

  function render() {
    var stage = document.getElementById('labStage');
    if (state.concept === 'compare') {
      stage.innerHTML = '<div class="labCompareGrid">' +
        ['a', 'b', 'c', 'd'].map(function (k) { return '<div class="labCompareCell">' + renderConcept(k) + '</div>'; }).join('') +
        '</div>';
    } else {
      stage.innerHTML = renderConcept(state.concept);
    }
    wireStage();
  }

  // ---------- interaction ----------
  function wireStage() {
    var stage = document.getElementById('labStage');
    stage.querySelectorAll('[data-mode]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var c = btn.getAttribute('data-concept');
        var m = btn.getAttribute('data-mode');
        state.active[state.inventory][c] = m;
        render();
        // restore focus to the just-selected control after re-render
        var again = stage.querySelector('[data-concept="' + c + '"][data-mode="' + m + '"]');
        if (again) again.focus();
      });
    });
    // roving keyboard navigation within each group (arrow keys), one
    // group at a time -- Home/End jump to first/last item in the group.
    stage.querySelectorAll('[role="group"], [role="radiogroup"]').forEach(function (group) {
      var items = Array.prototype.slice.call(group.querySelectorAll('[data-mode]'));
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
  }

  function wireChrome() {
    document.querySelectorAll('.labConceptBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.labConceptBtn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        state.concept = btn.getAttribute('data-concept');
        render();
      });
    });
    document.querySelectorAll('#labInventorySeg .labSegBtn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('#labInventorySeg .labSegBtn').forEach(function (b) {
          b.classList.remove('active'); b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-checked', 'true');
        state.inventory = btn.getAttribute('data-inventory');
        render();
      });
    });
  }

  wireChrome();
  render();
})();
