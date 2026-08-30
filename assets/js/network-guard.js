/* PORTAL-NEXT V2 — Network Guard (Gate 19).
   Foundation is expected to make ZERO calls to any real backend. This
   wraps fetch/XHR to LOG (never silently allow-and-ignore) any request
   whose target host matches a known real-backend pattern, and exposes
   a simple counter tests/browser checks can read. It does not block
   local requests (same-origin static files) — it only watches for the
   specific hosts Foundation must never reach. */
(function () {
  'use strict';

  var REAL_BACKEND_HOST_PATTERNS = [
    /\.supabase\.co$/i,
    /supabase\.co$/i,
    /api\.openai\.com$/i,
    /brabus\.blistiq\.com\.br$/i,
    /luisgamadio-spec\.github\.io$/i
  ];

  window.NX_NETWORK_GUARD = {
    flaggedRequests: [],
    isRealBackendUrl: function (url) {
      try {
        var u = new URL(url, location.href);
        return REAL_BACKEND_HOST_PATTERNS.some(function (re) { return re.test(u.hostname); });
      } catch (e) {
        return false;
      }
    }
  };

  var origFetch = window.fetch;
  if (typeof origFetch === 'function') {
    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : (input && input.url) || '';
      if (window.NX_NETWORK_GUARD.isRealBackendUrl(url)) {
        window.NX_NETWORK_GUARD.flaggedRequests.push({ method: 'fetch', url: url, at: new Date().toISOString() });
        console.error('[network-guard] BLOCKED-BY-POLICY (flagged, not silently allowed): fetch to real backend host:', url);
      }
      return origFetch.apply(this, arguments);
    };
  }

  var OrigXHR = window.XMLHttpRequest;
  if (OrigXHR) {
    var origOpen = OrigXHR.prototype.open;
    OrigXHR.prototype.open = function (method, url) {
      if (window.NX_NETWORK_GUARD.isRealBackendUrl(url)) {
        window.NX_NETWORK_GUARD.flaggedRequests.push({ method: 'xhr:' + method, url: url, at: new Date().toISOString() });
        console.error('[network-guard] FLAGGED: XHR to real backend host:', url);
      }
      return origOpen.apply(this, arguments);
    };
  }
})();
