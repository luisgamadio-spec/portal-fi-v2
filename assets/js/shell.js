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
    'simulador-seminovos': 'NX_SIMULADOR_SEMINOVOS_PAGE',
    'brabus-intelligence': 'NX_BRABUS_INTELLIGENCE_PAGE'
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

  /* ---------- AUTH FOUNDATION Phase 2B, Gate 10: centralized route
     guard. Runs BEFORE landing/module dispatch -- a direct hash
     navigation can never reach a module's mount code without passing
     this check first, matching the target flow HASH CHANGE -> ROUTER
     -> AUTH STATE CHECK -> REGISTRY RESOLUTION -> AUTHORIZATION CHECK
     -> SHELL DISPATCH -> MODULE MOUNT. Fail-closed throughout (Gate
     26): an unknown authMode, a PERMISSION_MATRIX module with no
     permissionId, or any unrecognized combination denies rather than
     defaulting to allow. */
  function isRouteAuthorized(entry) {
    if (!entry) return true; // unknown-route 404 is handled by renderPlaceholder itself, not a permission concern
    return window.NX_AUTH_CORE.isModuleAuthorized(entry);
  }

  // Defense in depth alongside landing.js's own currentRouteId() guard:
  // if a newer route dispatch has started before this one's async chain
  // finishes, skip its remaining side effects (module dispatch, design
  // trace) rather than letting a stale navigation act after the fact.
  var routeToken = 0;
  function onRouteChange(routeId) {
    var myToken = ++routeToken;
    var entry = window.NX_REGISTRY.byId(routeId);

    if (window.NX_AUTH_CORE.getState() !== window.NX_AUTH_CORE.STATES.AUTH_NOT_CONFIGURED &&
        window.NX_AUTH_CORE.getState() !== window.NX_AUTH_CORE.STATES.AUTHORIZED) {
      // AUTH FOUNDATION Phase 2B, Gate 11: any authenticated-app route
      // requested while not AUTHORIZED renders Login, never the
      // requested module -- a direct hash/URL cannot bypass this.
      window.NX_LOGIN.render();
      return;
    }
    if (entry && entry.authMode && !isRouteAuthorized(entry)) {
      // Not a dedicated error page (Gate 24's failure-matrix
      // discipline, matching V1: an unauthorized module simply isn't
      // navigable) -- return to the authenticated Landing.
      window.NX_ROUTER.navigate('landing');
      return;
    }

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

  /* ---------- Shell Wave 2B: tablet/mobile navigation drawer.
     Same #pGlobalNav DOM/data (renderGlobalNav in landing.js) as
     desktop -- this only toggles a body-level state class that CSS
     uses to slide the SAME sidebar in as an overlay. No second nav
     list, no duplicated module/group data. Listeners are attached once
     at boot to the stable #pGlobalNav/#pNavTrigger/#pNavBackdrop
     elements (event delegation for nav-item clicks), so they keep
     working across renderGlobalNav's per-route innerHTML rebuilds. */
  function setupNavDrawer() {
    var trigger = document.getElementById('pNavTrigger');
    var nav = document.getElementById('pGlobalNav');
    var backdrop = document.getElementById('pNavBackdrop');
    if (!trigger || !nav || !backdrop) return;

    function isOpen() { return document.body.classList.contains('nav-drawer-open'); }

    function openDrawer() {
      document.body.classList.add('nav-drawer-open');
      trigger.setAttribute('aria-expanded', 'true');
      backdrop.hidden = false;
      document.body.style.overflow = 'hidden';
    }
    function closeDrawer(returnFocus) {
      document.body.classList.remove('nav-drawer-open');
      trigger.setAttribute('aria-expanded', 'false');
      backdrop.hidden = true;
      document.body.style.overflow = '';
      if (returnFocus) trigger.focus();
    }

    trigger.addEventListener('click', function () {
      if (isOpen()) closeDrawer(true);
      else openDrawer();
    });
    backdrop.addEventListener('click', function () { closeDrawer(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen()) closeDrawer(true);
    });
    // A nav-item selection already navigates via its href/hashchange —
    // just close the drawer so the destination is visible underneath.
    nav.addEventListener('click', function (e) {
      var link = e.target.closest('.pNavItem, .pBrand');
      if (link && isOpen()) closeDrawer(false);
    });
    // Growing back to desktop width with the drawer open would leave a
    // stale open state (and the scroll lock) behind otherwise.
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1279 && isOpen()) closeDrawer(false);
    });
  }

  /* ---------- AUTH FOUNDATION Phase 2B, Gate 17: boot sequence.
     SESSION RESOLUTION -> PROFILE RESOLUTION -> AUTHORIZATION CONTEXT
     completes (auth-core.js's boot()) BEFORE the registry/router are
     wired at all -- no shell/module content can flash before
     authorization is known, per Gate 17's explicit requirement. The
     outlet's static "Carregando…" placeholder (index.html) covers
     this whole window; nxRoot itself stays hidden until AUTHORIZED
     (or AUTH_NOT_CONFIGURED, which behaves as pre-Auth-Foundation). */
  function boot() {
    setupDevBadge();
    setupNavDrawer();
    window.NX_AUTH_CORE.onStateChange(function (state) {
      var STATES = window.NX_AUTH_CORE.STATES;
      var bootLoading = document.getElementById('nxBootLoading');
      if (bootLoading && state !== STATES.INITIALIZING_SESSION) bootLoading.hidden = true;
      if (state === STATES.AUTHORIZED || state === STATES.AUTH_NOT_CONFIGURED) {
        document.getElementById('nxRoot').hidden = false;
        window.NX_LOGIN.hide();
        // Re-evaluate the current route under the now-current auth
        // state (covers: fresh login -> land on the route that was
        // originally requested if still valid, or Landing by default;
        // logout elsewhere reverting AUTHORIZED -> SIGNED_OUT re-shows
        // Login via the same listener's else branch below).
        if (!window.NX_ROUTER.currentRouteId()) {
          window.NX_ROUTER.navigate(DEFAULT_ROUTE);
        } else {
          onRouteChange(window.NX_ROUTER.currentRouteId());
        }
      } else if (state !== STATES.INITIALIZING_SESSION && state !== STATES.AUTHENTICATING && state !== STATES.AUTHENTICATED_RESOLVING_PROFILE) {
        document.getElementById('nxRoot').hidden = true;
        window.NX_LOGIN.render();
      }
    });

    window.NX_REGISTRY.load().then(function () {
      window.NX_ROUTER.onChange(onRouteChange);
      return window.NX_AUTH_CORE.boot();
    }).catch(function () {
      document.getElementById('nxContentOutlet').innerHTML =
        '<div class="nxPlaceholder"><h1>Registry failed to load</h1>' +
        '<p>config/module-registry.json could not be fetched. If you ' +
        'opened this file directly (file://), start a local server ' +
        'instead — see docs/DEVELOPMENT.md.</p></div>';
    });
  }
  document.addEventListener('DOMContentLoaded', boot);
})();
