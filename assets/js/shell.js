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

  /* ---------- Shell Wave 2A Gate 9/22 fix: move focus to the outlet on
     a real navigation (Gate 24 accessibility requirement, pre-existing)
     WITHOUT the browser's default scroll-into-view, which does not
     account for the sticky top bar and was scrolling exactly the top
     bar's height, tucking the new module's first paint under it. Scroll
     to the top explicitly instead — the correct behavior for a fresh
     route render regardless of where the previous module had scrolled to. */
  function focusOutletForNavigation(outlet) {
    outlet.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  /* ---------- Shell Wave 2A Gate 14: not-migrated / deferred state.
     Leads with a calm, human-readable message; keeps the diagnostic
     metadata (useful for development) but demoted into a <details> so
     it doesn't read as a developer-only dump. */
  function renderPlaceholder(entry, routeId, moveFocus) {
    var outlet = document.getElementById('nxContentOutlet');
    if (!entry) {
      outlet.innerHTML =
        '<div class="nxPlaceholder"><h1>Página não encontrada</h1>' +
        '<p><span class="nxStatusTag">#/' + routeId + '</span> não existe no registro de módulos.</p></div>';
      if (moveFocus) focusOutletForNavigation(outlet);
      return;
    }
    outlet.innerHTML =
      '<div class="nxPlaceholder nxDeferredState">' +
      '<span class="nxStatusTag">Em breve</span>' +
      '<h1>' + (entry.landingTitle || entry.name) + '</h1>' +
      '<p>Em preparação para o Portal V2. Esta área ainda não está disponível — volte em breve.</p>' +
      '<a class="nxDeferredHome" href="#/landing">Voltar para o início</a>' +
      '<details class="nxMetaDetails"><summary>Detalhes técnicos</summary>' +
      '<dl class="nxMeta">' +
      '<dt>rota</dt><dd>#/' + entry.id + '</dd>' +
      '<dt>status</dt><dd>' + entry.migrationStatus + '</dd>' +
      '<dt>densidade</dt><dd>' + entry.density + '</dd>' +
      '<dt>autenticação</dt><dd>' + entry.authRequirement + '</dd>' +
      '<dt>padrão de design</dt><dd>' + entry.designPattern + '</dd>' +
      '<dt>wave</dt><dd>' + entry.migrationWave + '</dd>' +
      '</dl></details>' +
      '</div>';
    if (moveFocus) outlet.focus();
  }

  /* ---------- Shell Wave 2A Gate 12: subtle, static loading state.
     No animation (Gate 17 — no motion/polish this Wave); reuses the
     same "Carregando…" language already established by index.html's
     own cold-load placeholder (Gate 15 — no new pattern invented). */
  function showModuleLoading(outlet) {
    outlet.innerHTML = '<div class="nxModuleLoading"><span class="nxModuleLoadingDot" aria-hidden="true"></span>Carregando módulo…</div>';
  }

  /* ---------- Shell Wave 2A Gate 13: structural module-load failure
     state. NOT backend/RPC error handling — this only covers the
     module's own render() promise rejecting. */
  function renderModuleError(outlet, entry, err) {
    var name = entry ? entry.name : 'este módulo';
    outlet.innerHTML =
      '<div class="nxPlaceholder nxModuleError">' +
      '<span class="nxStatusTag nxStatusTagError">Falha ao carregar</span>' +
      '<h1>Não foi possível abrir ' + name + '</h1>' +
      '<p>Ocorreu um erro ao carregar este módulo. Você pode tentar novamente ou voltar para o início.</p>' +
      '<a class="nxDeferredHome" href="#/landing">Voltar para o início</a>' +
      '</div>';
    console.error('[shell] module render failed for route', entry && entry.id, err);
  }

  /* ---------- Shell Wave 2A Gate 7: data-driven module dispatch.
     Replaces the prior hand-written if/else-if chain (one clause per
     migrated module) with a small declarative map from route id to the
     page global it registers — still explicit (module globals don't
     follow one predictable naming rule), but adding a module is now a
     one-line registration instead of a new branch, and every module
     gets the same loading/error handling for free. */
  var MODULE_PAGES = {
    score: 'NX_SCORE_PAGE',
    coparticipado: 'NX_COPARTICIPADO_PAGE',
    gestao: 'NX_GESTAO_PAGE',
    dashbi: 'NX_DASHBI_PAGE',
    'simulador-novos': 'NX_SIMULADOR_NOVOS_PAGE',
    'simulador-seminovos': 'NX_SIMULADOR_SEMINOVOS_PAGE'
  };

  var hasRenderedOnce = false;
  function dispatchModule(routeId, entry) {
    var pageGlobalName = MODULE_PAGES[routeId];
    var page = pageGlobalName && window[pageGlobalName];
    var outlet = document.getElementById('nxContentOutlet');
    if (!page) {
      renderPlaceholder(entry, routeId, hasRenderedOnce);
      return Promise.resolve();
    }
    showModuleLoading(outlet);
    return page.render(outlet).then(function () {
      if (hasRenderedOnce) focusOutletForNavigation(outlet);
    }).catch(function (err) {
      renderModuleError(outlet, entry, err);
    });
  }

  // Defense in depth alongside landing.js's own currentRouteId() guard:
  // if a newer route dispatch has started before this one's async chain
  // finishes, skip its remaining side effects (module dispatch, design
  // trace) rather than letting a stale navigation act after the fact.
  var routeToken = 0;
  function onRouteChange(routeId) {
    var myToken = ++routeToken;
    var entry = window.NX_REGISTRY.byId(routeId);
    window.NX_LANDING.renderRoute(routeId, entry).then(function () {
      if (myToken !== routeToken) return;
      if (!window.NX_LANDING.isLandingRoute(routeId)) {
        return dispatchModule(routeId, entry);
      }
    }).then(function () {
      if (myToken !== routeToken) return;
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
