/* PORTAL-NEXT V2 — Brabus Intelligence CONTEXT PROVIDER (IA-3E).

   Builds the CLIENT_CONTEXT_HINTS envelope (IA-3E Section 23/30-32):
   route/moduleId/moduleTitle plus optional activeSection/period/
   store/department/seller/model. This is PRESENTATION ONLY — a
   human-visible convenience (the panel's own context chip) that helps
   a human phrase their question, never a value sent to or trusted by
   the backend, and never a grant of any kind:

     - the real portal-ai-homolog contract reads ONLY {message,
       conversation} from the request body (confirmed by direct source
       read this Wave, supabase/functions/portal-ai-homolog/index.ts,
       "só lê message/conversation, nunca user_id/perfil/loja/
       departamento vindos do cliente") — any extra field this module
       produced would be silently ignored, never enforced;
     - this module itself never calls fetch/XHR and is never given the
       adapter's sendRealText/createRequest to call automatically —
       see docs/IA-3E-V2-INTELLIGENCE-PANEL.md for why sending it over
       the wire was deliberately deferred, not implemented as a
       silent no-op;
     - authority (module access, store/department scope, MASTER) is
       decided exclusively by the server on every real request,
       exactly as it already is today — this module cannot widen that
       even if it wanted to, since nothing it produces reaches the
       authorization boundary.

   Automatic wiring is ROUTE-LEVEL ONLY this Wave (Section 33): shell.js
   calls setRoute() on every navigation, for every module, without
   touching any individual module's own (frozen) source. publish() is
   a voluntary, allow-listed API a module MAY call in a future wave to
   contribute deeper hints — nothing in this codebase calls it yet. */
(function () {
  'use strict';

  var ALLOWED_HINT_KEYS = ['activeSection', 'periodStart', 'periodEnd', 'store', 'department', 'seller', 'model'];

  var current = {
    route: null,
    moduleId: null,
    moduleTitle: null,
    activeSection: null,
    periodStart: null,
    periodEnd: null,
    store: null,
    department: null,
    seller: null,
    model: null
  };
  var listeners = [];

  function getSnapshot() {
    return Object.freeze({
      route: current.route,
      moduleId: current.moduleId,
      moduleTitle: current.moduleTitle,
      activeSection: current.activeSection,
      periodStart: current.periodStart,
      periodEnd: current.periodEnd,
      store: current.store,
      department: current.department,
      seller: current.seller,
      model: current.model
    });
  }

  function notify() {
    var snap = getSnapshot();
    listeners.forEach(function (fn) {
      try { fn(snap); } catch (e) { console.error('[intelligence-context] listener error', e); }
    });
  }

  window.NX_INTELLIGENCE_CONTEXT = {
    // Called by shell.js's onRouteChange, once per navigation, for
    // EVERY route (not just brabus-intelligence's own) — the shell
    // already knows routeId/entry at that point, so this needs no
    // extra lookup of its own. A route change always clears any
    // deeper hint a previous module may have published: a stale
    // store/department/period must never leak into a different
    // module's conversation context.
    setRoute: function (routeId, entry) {
      current.route = routeId || null;
      current.moduleId = entry ? entry.id : null;
      current.moduleTitle = entry ? (entry.landingTitle || entry.title || entry.name || null) : null;
      current.activeSection = null;
      current.periodStart = null;
      current.periodEnd = null;
      current.store = null;
      current.department = null;
      current.seller = null;
      current.model = null;
      notify();
    },

    // Voluntary, allow-listed hint publisher. Silently drops any key
    // not on ALLOWED_HINT_KEYS (defense in depth — a module can never
    // inject an authority-shaped field like "perfil" or "isMaster"
    // through this API even by accident) and coerces every accepted
    // value to a plain string (never an object a caller could later
    // mutate through a held reference).
    publish: function (partial) {
      if (!partial || typeof partial !== 'object') return;
      ALLOWED_HINT_KEYS.forEach(function (k) {
        if (Object.prototype.hasOwnProperty.call(partial, k)) {
          var v = partial[k];
          current[k] = (v === null || v === undefined) ? null : String(v);
        }
      });
      notify();
    },

    getSnapshot: getSnapshot,
    onChange: function (fn) { listeners.push(fn); },

    // Human-readable label for the panel's own context chip. Never
    // sent anywhere — a display convenience only.
    describe: function () {
      var parts = [];
      if (current.moduleTitle) parts.push(current.moduleTitle);
      if (current.store) parts.push(current.store);
      if (current.department) parts.push(current.department);
      var period = [current.periodStart, current.periodEnd].filter(Boolean).join(' – ');
      if (period) parts.push(period);
      return parts.join(' · ');
    }
  };
})();
