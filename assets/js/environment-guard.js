/* PORTAL-NEXT V2 — Environment Guard (Gate 18).
   Declares this build as NEXT_LOCAL and asserts, at runtime, that we
   are not accidentally being served from anything resembling a
   production host. This file contains no deploy target, no
   GitHub Pages config, no hostname to publish to — it only checks. */
(function () {
  'use strict';

  var PRODUCTION_HOSTNAME_PATTERNS = [
    /brabus\.blistiq\.com\.br$/i,
    /\.github\.io$/i
  ];

  var host = (typeof location !== 'undefined' && location.hostname) || '';
  var looksLikeProduction = PRODUCTION_HOSTNAME_PATTERNS.some(function (re) {
    return re.test(host);
  });

  window.NX_ENVIRONMENT = {
    name: 'NEXT_LOCAL',
    production: false,
    hostname: host,
    checkedAt: new Date().toISOString(),
    productionHostnameDetected: looksLikeProduction
  };

  if (looksLikeProduction) {
    // This build must never run on a production-looking host. Fail
    // loudly rather than silently rendering as if nothing were wrong.
    document.addEventListener('DOMContentLoaded', function () {
      document.body.innerHTML =
        '<pre style="padding:24px;font-family:monospace;white-space:pre-wrap">' +
        'ENVIRONMENT GUARD STOP\n\n' +
        'This is PORTAL-NEXT V2 Foundation (NEXT_LOCAL build) and it is ' +
        'running on a hostname (' + host + ') that matches a known ' +
        'production pattern. This build has no deploy target and should ' +
        'never be reachable from a production host. Refusing to render.' +
        '</pre>';
    });
    console.error('[environment-guard] STOP: production-looking hostname detected:', host);
  }
})();
