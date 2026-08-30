/* PORTAL-NEXT V2 — Landing (Gate 8: TRANSPLANT + CONTROLLED ADAPTATION).
   STRUCTURE: transplanted verbatim from design-system-2.1/references/
   baselines/module-landing-approved/{pages.js,app.js} — same class
   names, same DOM nesting, same interaction model (hover/focus/click
   selects a category, module block click navigates, Context Beam
   fires only on an actual category/route change, respects
   prefers-reduced-motion throughout).
   TOKENS: design-system-2/tokens.css (linked, not copied).
   CONTENT: config/module-registry.json + config/landing-groups.json
   (V2's real modules — see docs/LANDING-CONTENT-MAP.md for the
   mapping decision).
   ROUTING: V2's own router.js (NX_ROUTER), not the reference's hash
   resolver.
   MOTION: design-motion-lab-03/engine.js (window.MotionEngine, linked
   directly — not reimplemented, per Gate 9/11). */
(function () {
  'use strict';

  var NAV_ICONS = {
    landing: 'PF', dashbi: 'AG', gestao: 'FI', coparticipado: 'CO',
    score: 'SC', 'salarios-comissoes': 'SL', 'simulador-novos': 'NV',
    'simulador-seminovos': 'SM', 'brabus-intelligence': 'AI', 'shell-admin': 'AU'
  };

  var landingGroups = null;
  var landingAmbientMount = null;
  var lastRoute = null;

  function loadGroups() {
    if (landingGroups) return Promise.resolve(landingGroups);
    return fetch('config/landing-groups.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { landingGroups = data.groups; return landingGroups; });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  /* ---------- persistent chrome (Gate 7: only what Landing needs) ---------- */
  function renderGlobalNav(activeRouteId) {
    var modules = window.NX_REGISTRY.modules;
    var html = '<div class="brandMark" title="Brabus F&amp;I">B</div>' +
      '<a href="#/landing" class="gNavBtn' + (activeRouteId === 'landing' ? ' active' : '') + '" aria-label="Landing">' + NAV_ICONS.landing + '</a>';
    modules.forEach(function (m) {
      if (m.id === 'landing') return;
      var code = NAV_ICONS[m.id] || m.id.slice(0, 2).toUpperCase();
      html += '<a href="#/' + m.id + '" class="gNavBtn' + (activeRouteId === m.id ? ' active' : '') + '" aria-label="' + esc(m.name) + '" title="' + esc(m.name) + '">' + code + '</a>';
    });
    document.getElementById('pGlobalNav').innerHTML = html;
  }

  function renderTopBar(entry) {
    var bc = document.getElementById('pBreadcrumb');
    if (bc) bc.innerHTML = 'Portal F&amp;I <span style="margin:0 6px">/</span> <b>' + esc(entry ? entry.name : 'Landing') + '</b>';
  }

  /* ---------- Landing HTML (transplanted from pages.js pageLanding/landingModuleBlockHtml) ---------- */
  function landingHtml(groups) {
    var navItems = groups.map(function (g, i) {
      return '<button type="button" class="fNavItem' + (i === 0 ? ' active' : '') + '" data-idx="' + i + '">' +
        '<span class="idx">' + String(i + 1).padStart(2, '0') + '</span><span class="label">' + esc(g.label) + '</span></button>';
    }).join('');
    return '<div class="fShell" id="landingShell">' +
      '<div class="contextBeam" id="landingBeam"></div>' +
      '<nav class="fNav" id="landingNav">' + navItems + '</nav>' +
      '<section class="fCanvas"><div class="ambientLayer" id="landingAmbientLayer" aria-hidden="true"></div><div class="motionProtectFull"></div><div class="fCanvasInner">' +
      '<div id="landingModuleDetail"></div>' +
      '</div></section>' +
      '</div>';
  }

  function moduleBlockHtml(m) {
    /* No eyebrow ("N módulos nesta categoria"), no status/code footer —
       matches the reference exactly; that metadata was explicitly
       rejected by human UAT in FACELIFT-PROTOTYPE-01.2 (see
       docs/LANDING-CONTENT-MAP.md "MUST NOT show" list). */
    return '<div class="fModuleBlock" data-route="' + m.id + '" tabindex="0" role="button" aria-label="Abrir ' + esc(m.landingTitle || m.name) + '">' +
      '<div class="fModuleTop"><h3 class="fModuleTitle">' + esc(m.landingTitle || m.name) + '</h3><span class="fModuleArrow">→</span></div>' +
      '<p class="fModuleDesc">' + esc(m.landingDesc || m.title) + '</p>' +
      '</div>';
  }

  /* ---------- ambient motion (Gate 11: exact normative Parametric Reactive config) ---------- */
  function mountLandingAmbient() {
    var layer = document.getElementById('landingAmbientLayer');
    if (landingAmbientMount) { landingAmbientMount.destroy(); landingAmbientMount = null; }
    if (!layer) return;
    if (window.MotionEngine && window.MotionEngine.reduce) { layer.style.opacity = '0'; return; }
    if (!window.MotionEngine) { console.warn('[landing] MotionEngine not loaded — ambient motion skipped.'); return; }
    var canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    layer.innerHTML = '';
    layer.appendChild(canvas);
    layer.style.opacity = '0.25'; /* LOW density = full presence, normative Parametric Reactive config */
    landingAmbientMount = window.MotionEngine.mount(canvas, 'parametric_reactive', { speed: 0.75, colorMode: 'brand_red', customColor: '#c1121f' });
    window.NX_MOTION.parametricReactive.enabled = true;
  }
  function unmountLandingAmbient() {
    if (landingAmbientMount) { landingAmbientMount.destroy(); landingAmbientMount = null; }
    window.NX_MOTION.parametricReactive.enabled = false;
  }

  /* ---------- wiring (transplanted from app.js wireLanding) ---------- */
  function wireLanding(groups) {
    var navEl = document.getElementById('landingNav');
    var beamEl = document.getElementById('landingBeam');
    var shellEl = document.getElementById('landingShell');
    var detailEl = document.getElementById('landingModuleDetail');
    var activeIdx = 0;

    function moduleByIdGlobal(id) { return window.NX_REGISTRY.byId(id); }

    function selectGroup(idx, fireBeam) {
      var g = groups[idx];
      detailEl.innerHTML = g.moduleIds.map(function (mid) {
        var m = moduleByIdGlobal(mid);
        return m ? moduleBlockHtml(m) : '';
      }).join('');
      navEl.querySelectorAll('.fNavItem').forEach(function (b, i) { b.classList.toggle('active', i === idx); });
      if (fireBeam && !(window.MotionEngine && window.MotionEngine.reduce)) {
        var btn = navEl.querySelector('.fNavItem[data-idx="' + idx + '"]');
        var shellRect = shellEl.getBoundingClientRect();
        var btnRect = btn.getBoundingClientRect();
        var navRect = navEl.getBoundingClientRect();
        beamEl.style.left = (navRect.right - shellRect.left) + 'px';
        beamEl.style.top = (btnRect.top - shellRect.top + btnRect.height / 2) + 'px';
        beamEl.classList.add('active');
        setTimeout(function () { beamEl.classList.remove('active'); }, 420);
      }
    }
    selectGroup(0, false);

    navEl.querySelectorAll('.fNavItem').forEach(function (btn, idx) {
      btn.addEventListener('click', function () { if (idx !== activeIdx) { activeIdx = idx; selectGroup(idx, true); } });
      btn.addEventListener('mouseenter', function () { if (idx !== activeIdx) { activeIdx = idx; selectGroup(idx, true); } });
      btn.addEventListener('focus', function () { if (idx !== activeIdx) { activeIdx = idx; selectGroup(idx, true); } });
      btn.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (idx !== activeIdx) { activeIdx = idx; selectGroup(idx, true); } } });
    });
    detailEl.addEventListener('click', function (e) {
      var block = e.target.closest('.fModuleBlock'); if (!block) return;
      window.NX_ROUTER.navigate(block.getAttribute('data-route'));
    });
    detailEl.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var block = e.target.closest('.fModuleBlock'); if (!block) return;
      e.preventDefault();
      window.NX_ROUTER.navigate(block.getAttribute('data-route'));
    });
  }

  /* ---------- public entry, called by shell.js on every route change ---------- */
  window.NX_LANDING = {
    isLandingRoute: function (routeId) { return routeId === 'landing'; },

    renderRoute: function (routeId, entry) {
      var moduleChanged = lastRoute !== null && lastRoute !== routeId;
      lastRoute = routeId;

      document.body.classList.toggle('landing-active', routeId === 'landing');
      renderGlobalNav(routeId);
      renderTopBar(entry);
      if (moduleChanged) window.NX_CONTEXT_BEAM.fire();

      if (routeId === 'landing') {
        return loadGroups().then(function (groups) {
          document.getElementById('nxContentOutlet').innerHTML = landingHtml(groups);
          mountLandingAmbient();
          wireLanding(groups);
        });
      }
      unmountLandingAmbient();
      return Promise.resolve(null);
    }
  };
})();
