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
    d: { label: 'D — Hybrid Luxury Navigation', desc: 'Três instrumentos contínuos (um por categoria) com linhas internas, não dez botões soltos.', badge: 'Direção selecionada' },
    e: { label: 'E — Hybrid Luxury Final', desc: 'Refinamento de D: hierarquia de material mais precisa, cabeçalho de categoria integrado, marcador vermelho inset com brilho localizado e restrito.', badge: 'Refinamento do Conceito D' },
    f: { label: 'F — Hybrid Luxury Collapsible', desc: 'Ideia do Human: categorias sempre visíveis, opções ocultas até a categoria ser aberta -- uma categoria aberta por vez, mesma linguagem visual de E.', badge: 'Ideia do Human — em avaliação' }
  };

  // ---------- state ----------
  var state = {
    inventory: 'novos',
    concept: 'a',
    active: {
      novos: { a: 'tradicional', b: 'tradicional', c: 'tradicional', d: 'tradicional', e: 'tradicional', f: 'tradicional' },
      seminovos: { a: 'tradicional', b: 'tradicional', c: 'tradicional', d: 'tradicional', e: 'tradicional', f: 'tradicional' }
    },
    // SIM-NAV-LAB-3 / Concept F only -- which category is currently
    // expanded, per inventory. null = all collapsed (the LAB's
    // intentional initial state, brief §10). Separate from `active`
    // above (the SELECTED simulator mode) -- browsing a category must
    // never change the selected mode (brief §19).
    openCategory: { novos: null, seminovos: null }
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
    var frameClass = conceptKey === 'e' ? 'labFrame labFrameE' : (conceptKey === 'f' ? 'labFrame labFrameF' : 'labFrame');
    var badgeHtml = meta.badge ? '<span class="labConceptBadge">' + esc(meta.badge) + '</span>' : '';
    return (
      '<div class="' + frameClass + '">' +
        '<div class="labConceptLabel"><span class="labConceptLabelName">' + esc(meta.label) + '</span>' + badgeHtml + '<span class="labConceptLabelDesc">' + esc(meta.desc) + '</span></div>' +
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

  // ---------- Concept E: Hybrid Luxury Final (refinement of D) ----------
  // SIM-NAV-LAB-2 -- same three-instrument architecture as D, refined:
  // category header integrated into the panel (index + title, per
  // §10), inset red marker with a restrained localized glow instead
  // of D's full-height border, auto-fit column grid so Seminovos's
  // 2 categories (vs Novos's 3) and each category's differing row
  // count never leave a forced empty column or a stretched group.
  function conceptE(inv, activeMap) {
    return '<nav class="labNavE" aria-label="Modalidade de financiamento">' +
      inv.map(function (g, gi) {
        var idx = String(gi + 1).padStart(2, '0');
        return '<div class="labEGroup"><div class="labEPanel">' +
          '<div class="labEHeader"><span class="labEIndex">' + idx + '</span><span class="labETitle">' + esc(g.group) + '</span></div>' +
          '<div class="labERows" role="group" aria-label="' + esc(g.group) + '">' +
          g.items.map(function (m) {
            var active = m.id === activeMap.e;
            return '<button type="button" class="labERow' + (active ? ' active' : '') + '" data-concept="e" data-mode="' + m.id + '" aria-pressed="' + active + '">' +
              '<span class="labELabel">' + esc(m.label) + '</span>' + chevron() +
              '</button>';
          }).join('') +
          '</div></div></div>';
      }).join('') +
      '</nav>';
  }

  // ---------- Concept F: Hybrid Luxury Collapsible (Human idea) ----------
  // SIM-NAV-LAB-3 -- same three-instrument architecture and material
  // language as E (panel/header/row geometry, tokens, red-marker
  // language all reused, not reinvented), but individual options stay
  // hidden until their category header is opened, and only one
  // category may be open at a time (brief §9/§13). The category
  // header is a real <button> with aria-expanded/aria-controls; its
  // options live in a grid-template-rows-animated wrapper so the
  // expand/collapse is a real CSS transition, not a display toggle --
  // and the options container gets `inert` (+ tabindex=-1 as a
  // belt-and-suspenders) while collapsed so they are never keyboard-
  // reachable (brief §26). A collapsed category whose options contain
  // the CURRENTLY SELECTED mode shows a small secondary hint line
  // (brief §17/§18) -- computed fresh per render, never stale, since
  // it is derived from state.active[inv].f on every call, never cached.
  function conceptF(inv, activeMap) {
    var openCat = state.openCategory[state.inventory];
    return '<nav class="labNavF" aria-label="Modalidade de financiamento">' +
      inv.map(function (g, gi) {
        var idx = String(gi + 1).padStart(2, '0');
        var isOpen = g.group === openCat;
        var slug = g.group.toLowerCase().replace(/[^a-z0-9]+/g, '');
        var panelId = 'labFPanel-' + state.inventory + '-' + slug;
        var current = null;
        g.items.forEach(function (m) { if (m.id === activeMap.f) current = m; });
        var hintHtml = (!isOpen && current) ? '<span class="labFHint">' + esc(current.label) + '</span>' : '';
        return '<div class="labFGroup' + (isOpen ? ' open' : '') + '">' +
          '<div class="labFPanel">' +
            '<button type="button" class="labFHeader" data-group="' + esc(g.group) + '" aria-expanded="' + isOpen + '" aria-controls="' + panelId + '">' +
              '<span class="labFHeaderMain">' +
                '<span class="labFHeaderTop"><span class="labFIndex">' + idx + '</span><span class="labFTitle">' + esc(g.group) + '</span></span>' +
                hintHtml +
              '</span>' +
              '<svg class="labChevron labFDisclosure" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M6 3.5L10.5 8L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
            '</button>' +
            '<div class="labFRowsWrap"><div class="labFRowsInner">' +
              '<div class="labFRows" id="' + panelId + '" role="group" aria-label="' + esc(g.group) + '"' + (isOpen ? '' : ' inert') + '>' +
              g.items.map(function (m) {
                var active = m.id === activeMap.f;
                return '<button type="button" class="labFRow' + (active ? ' active' : '') + '" data-concept="f" data-mode="' + m.id + '" tabindex="' + (isOpen ? '0' : '-1') + '" aria-pressed="' + active + '">' +
                  '<span class="labFLabel">' + esc(m.label) + '</span>' + chevron() +
                  '</button>';
              }).join('') +
              '</div>' +
            '</div></div>' +
          '</div>' +
        '</div>';
      }).join('') +
      '</nav>';
  }

  var RENDERERS = { a: conceptA, b: conceptB, c: conceptC, d: conceptD, e: conceptE, f: conceptF };

  function renderConcept(key) {
    var inv = INVENTORIES[state.inventory];
    var activeMap = state.active[state.inventory];
    return frameHtml(key, RENDERERS[key](inv, activeMap));
  }

  function render() {
    var stage = document.getElementById('labStage');
    if (state.concept === 'compare') {
      stage.innerHTML = '<div class="labCompareGrid">' +
        ['a', 'b', 'c', 'd', 'e', 'f'].map(function (k) { return '<div class="labCompareCell">' + renderConcept(k) + '</div>'; }).join('') +
        '</div>';
    } else if (state.concept === 'compare-de') {
      stage.innerHTML = '<div class="labCompareGrid">' +
        ['d', 'e'].map(function (k) { return '<div class="labCompareCell">' + renderConcept(k) + '</div>'; }).join('') +
        '</div>';
    } else if (state.concept === 'compare-ef') {
      stage.innerHTML = '<div class="labCompareGrid">' +
        ['e', 'f'].map(function (k) { return '<div class="labCompareCell">' + renderConcept(k) + '</div>'; }).join('') +
        '</div>';
    } else {
      stage.innerHTML = renderConcept(state.concept);
    }
    wireStage();
  }

  // SIM-NAV-LAB-3 / Concept F only -- toggles the open category for
  // the current inventory. Clicking the already-open category
  // collapses back to all-collapsed (brief §20); clicking a different
  // one closes the previous and opens the new one (single-open,
  // brief §9). Never touches state.active (selected mode) -- opening/
  // closing a category is browsing, not selecting (brief §19).
  function toggleCategory(groupName) {
    var inv = state.inventory;
    state.openCategory[inv] = (state.openCategory[inv] === groupName) ? null : groupName;
    render();
    var stage = document.getElementById('labStage');
    var again = stage.querySelector('.labFHeader[data-group="' + groupName + '"]');
    if (again) again.focus();
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
    stage.querySelectorAll('.labFHeader').forEach(function (btn) {
      btn.addEventListener('click', function () { toggleCategory(btn.getAttribute('data-group')); });
    });
    // roving keyboard navigation within each group (arrow keys), one
    // group at a time -- Home/End jump to first/last item in the group.
    // A collapsed Concept F options group is `inert`, so its items are
    // simply unreachable here -- no special-casing needed.
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
    // SIM-NAV-LAB-3 / Concept F optional enhancement (brief §27):
    // Left/Right (or Up/Down) roving nav between the 3 category
    // headers. Separate, simple mechanism -- headers carry no
    // data-mode, so the generic loop above never touches them, and
    // this loop never touches rows. No conflicting keyboard model.
    var headers = Array.prototype.slice.call(stage.querySelectorAll('.labFHeader'));
    headers.forEach(function (h, idx) {
      h.addEventListener('keydown', function (e) {
        var next = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = headers[(idx + 1) % headers.length];
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = headers[(idx - 1 + headers.length) % headers.length];
        if (next) { e.preventDefault(); next.focus(); }
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
