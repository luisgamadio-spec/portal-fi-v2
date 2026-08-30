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

  /* ---------- Gate 23: Context Beam event hook, not fired indiscriminately ---------- */
  window.NX_CONTEXT_BEAM = {
    fire: function (reason) {
      // Intentionally a no-op in Foundation. Real firing is reserved
      // for genuine group/module context changes once real modules
      // exist — placeholders must not trigger it just to "look alive".
      console.debug('[context-beam] fire() called with no-op Foundation stub. reason=', reason);
    }
  };

  function renderNav(modules, activeId) {
    var list = document.getElementById('nxNavList');
    list.innerHTML = '';
    modules.forEach(function (m) {
      var li = document.createElement('li');
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'nxNavItem';
      btn.textContent = m.name.split(' ')[0];
      btn.title = m.name;
      btn.setAttribute('data-route', m.id);
      if (m.id === activeId) btn.setAttribute('aria-current', 'page');
      btn.addEventListener('click', function () { window.NX_ROUTER.navigate(m.id); });
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

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
    renderNav(window.NX_REGISTRY.modules, routeId);
    renderPlaceholder(entry, routeId, hasRenderedOnce);
    window.NX_DESIGN_TRACE.render(entry, routeId);
    hasRenderedOnce = true;
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
