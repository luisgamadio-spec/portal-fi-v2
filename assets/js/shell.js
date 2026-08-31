/* PORTAL-NEXT V2 — Shell boot (Gates 10, 11, 13, 22, 23, 32).
   Wires router + module registry + nav + content outlet + Design
   Trace dev panel. No module's real UI is implemented here — every
   route renders a minimal structural placeholder proving routing
   works, per Gate 10's explicit "no full visual mockup" instruction. */
(function () {
  'use strict';

  var DEFAULT_ROUTE = 'landing';

  /* ---------- Gate 22: Parametric Reactive motion runtime, loadable but OFF ---------- */
  window.NX_MOTION = {
    parametricReactive: {
      available: true,
      enabled: false, // default OFF — modules not yet classified/migrated
      configSource: 'design-system-2/tokens.css --signature-motion-*',
      reason: 'Foundation phase — density has not been classified per-module yet (Gate 11 in the Skill requires classifying density BEFORE motion).'
    }
  };

  /* ---------- Gate 23/12: Context Beam event hook — REAL as of this
     Wave (Landing exists now), fires only on an actual route/context
     change, never on every hover/click. See assets/css/landing.css
     .ctxBeam and assets/js/landing.js, which is the actual caller. */
  window.NX_CONTEXT_BEAM = {
    fire: function () {
      if (window.MotionEngine && window.MotionEngine.reduce) return;
      var beam = document.getElementById('ctxBeam');
      if (!beam) return;
      beam.classList.add('active');
      setTimeout(function () { beam.classList.remove('active'); }, 420);
    }
  };

  function renderPlaceholder(entry, routeId, moveFocus) {
    var outlet = document.getElementById('nxContentOutlet');
    if (!entry) {
      outlet.innerHTML =
        '<div class="nxPlaceholder"><h1>Route not found</h1>' +
        '<p><span class="nxStatusTag">#/' + routeId + '</span> is not in the module registry.</p></div>';
      return;
    }
    outlet.innerHTML =
      '<div class="nxPlaceholder">' +
      '<h1>' + entry.name + '</h1>' +
      '<p>' + entry.title + '</p>' +
      '<span class="nxStatusTag">' + entry.migrationStatus + '</span>' +
      '<dl class="nxMeta">' +
      '<dt>route</dt><dd>#/' + entry.id + '</dd>' +
      '<dt>density</dt><dd>' + entry.density + '</dd>' +
      '<dt>auth</dt><dd>' + entry.authRequirement + '</dd>' +
      '<dt>design pattern</dt><dd>' + entry.designPattern + '</dd>' +
      '<dt>migration wave</dt><dd>' + entry.migrationWave + '</dd>' +
      '</dl>' +
      '</div>';
    // Move focus to the outlet only on a REAL navigation (user clicked
    // a nav item / changed the hash) — never on the very first render
    // during boot, which would steal focus away from the page's
    // natural top-of-DOM tab order (the skip link must be tab stop 1
    // on cold load, per Gate 24).
    if (moveFocus) outlet.focus();
  }

  var hasRenderedOnce = false;
  function onRouteChange(routeId) {
    var entry = window.NX_REGISTRY.byId(routeId);
    window.NX_LANDING.renderRoute(routeId, entry).then(function () {
      if (!window.NX_LANDING.isLandingRoute(routeId)) {
        if (routeId === 'score' && window.NX_SCORE_PAGE) {
          // Gate 26/27: real Score route, shell/outlet unchanged —
          // NX_SCORE_PAGE only renders INTO the same #nxContentOutlet
          // every other route already uses.
          var outlet = document.getElementById('nxContentOutlet');
          window.NX_SCORE_PAGE.render(outlet).then(function () {
            if (hasRenderedOnce) outlet.focus();
          });
        } else if (routeId === 'coparticipado' && window.NX_COPARTICIPADO_PAGE) {
          // PORTAL-NEXT-05 Gate 28: real Coparticipado route, same
          // outlet-only rendering contract as Score.
          var cpOutlet = document.getElementById('nxContentOutlet');
          window.NX_COPARTICIPADO_PAGE.render(cpOutlet).then(function () {
            if (hasRenderedOnce) cpOutlet.focus();
          });
        } else if (routeId === 'gestao' && window.NX_GESTAO_PAGE) {
          // PORTAL-NEXT-06 Gate 40: real Gestão route, same outlet-only
          // rendering contract as Score/Coparticipado.
          var geOutlet = document.getElementById('nxContentOutlet');
          window.NX_GESTAO_PAGE.render(geOutlet).then(function () {
            if (hasRenderedOnce) geOutlet.focus();
          });
        } else if (routeId === 'dashbi' && window.NX_DASHBI_PAGE) {
          // PORTAL-NEXT-07 Gate 99: real Dashbi route, same outlet-only
          // rendering contract as every prior module.
          var dbOutlet = document.getElementById('nxContentOutlet');
          window.NX_DASHBI_PAGE.render(dbOutlet).then(function () {
            if (hasRenderedOnce) dbOutlet.focus();
          });
        } else {
          renderPlaceholder(entry, routeId, hasRenderedOnce);
        }
      }
      window.NX_DESIGN_TRACE.render(entry, routeId);
      hasRenderedOnce = true;
    });
  }

  function setupDevBadge() {
    var toggleBtn = document.getElementById('nxDesignTraceToggle');
    var panel = document.getElementById('nxDesignTrace');
    toggleBtn.addEventListener('click', function () {
      var isHidden = panel.hasAttribute('hidden');
      if (isHidden) panel.removeAttribute('hidden');
      else panel.setAttribute('hidden', '');
      toggleBtn.setAttribute('aria-expanded', String(isHidden));
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupDevBadge();
    window.NX_REGISTRY.load().then(function () {
      window.NX_ROUTER.onChange(onRouteChange);
      if (!window.NX_ROUTER.currentRouteId()) {
        window.NX_ROUTER.navigate(DEFAULT_ROUTE);
      } else {
        window.NX_ROUTER.resolveInitial();
      }
    }).catch(function () {
      document.getElementById('nxContentOutlet').innerHTML =
        '<div class="nxPlaceholder"><h1>Registry failed to load</h1>' +
        '<p>config/module-registry.json could not be fetched. If you ' +
        'opened this file directly (file://), start a local server ' +
        'instead — see docs/DEVELOPMENT.md.</p></div>';
    });
  });
})();
