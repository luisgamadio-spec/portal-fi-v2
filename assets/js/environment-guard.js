/* PORTAL-NEXT V2 -- Environment Guard (Gate 18, redesigned GL-1C).

   REDESIGNED (Go-Live deployment reconciliation, GL-1C): the original
   contract was "block every hostname that merely LOOKS like a
   production host" (a hardcoded *.github.io / brabus.blistiq.com.br
   pattern list), which had no path to ever legitimately authorize a
   real V2 deployment -- it could only ever say STOP. That made sense
   before any real deployment was planned; it does not once Strategy B
   (V2's own standalone GitHub Pages deployment) is the intended target.

   NEW CONTRACT -- exactly three states, always exactly one applies:

     LOCAL_DEV            -- hostname is localhost/127.0.0.1. Always
                             allowed, unconditionally.
     AUTHORIZED_PRODUCTION -- hostname is NOT local dev, AND the
                             hostname appears in the production runtime
                             config's own `authorizedHostnames` array
                             (assets/js/intelligence-runtime-config.js,
                             overridden by .production.js on a real
                             host). This authorization can ONLY come
                             from that server-shipped, hand-maintained
                             config file -- never from a client-editable
                             query parameter, localStorage value, or any
                             other client-controlled signal, since the
                             whole point of this guard is that a client
                             cannot self-authorize its own host.
     UNKNOWN_HOST          -- neither of the above. FAIL CLOSED --
                             refuses to render, exactly like the
                             original guard's behavior, just reached via
                             an explicit allowlist miss rather than a
                             blocklist hit. This is deliberately the
                             DEFAULT today: intelligence-runtime-
                             config.js's own committed authorizedHostnames
                             is an empty array, and no production file is
                             loaded by index.html yet -- so every real
                             host, including a future real V2 GitHub
                             Pages hostname, remains UNKNOWN_HOST (and
                             therefore blocked) until a Human explicitly
                             records that hostname in a real production
                             config file. This is intentional, not a
                             bug: GL-1C's own brief is explicit that
                             "the final hostname has not yet been chosen"
                             and must never be invented here.

   TIMING NOTE: the actual authorization decision is deliberately made
   inside the DOMContentLoaded handler below, not at top-level script
   execution. This file may load before intelligence-runtime-
   config(.production).js in index.html's current script order; by the
   time DOMContentLoaded fires, every earlier synchronous <script> tag
   (including the config file, wherever it sits in the document) has
   already executed, so window.NX_INTELLIGENCE_CONFIG is guaranteed to
   be populated by then. This avoids requiring a script-order change in
   index.html as part of this guard redesign. */
(function () {
  'use strict';

  var LOCAL_DEV_HOSTNAMES = ['localhost', '127.0.0.1'];

  function classifyEnvironment() {
    var host = (typeof location !== 'undefined' && location.hostname) || '';
    var isLocalDev = LOCAL_DEV_HOSTNAMES.indexOf(host) !== -1;

    var cfg = window.NX_INTELLIGENCE_CONFIG || {};
    var authorizedHostnames = Array.isArray(cfg.authorizedHostnames) ? cfg.authorizedHostnames : [];
    var isAuthorizedProduction = !isLocalDev && authorizedHostnames.indexOf(host) !== -1;

    var name = isLocalDev ? 'LOCAL_DEV' : (isAuthorizedProduction ? 'AUTHORIZED_PRODUCTION' : 'UNKNOWN_HOST');
    return { name: name, hostname: host, allowed: name !== 'UNKNOWN_HOST' };
  }

  // A preliminary classification is published immediately (before
  // DOMContentLoaded) so any code that merely wants to READ the
  // environment name early (e.g. for a log line) can do so -- but this
  // preliminary read may be based on an authorizedHostnames list that
  // hasn't loaded yet, so `allowed` here is advisory only. The
  // authoritative, enforced decision is the one computed again inside
  // DOMContentLoaded below, after every earlier script has executed.
  window.NX_ENVIRONMENT = classifyEnvironment();
  window.NX_ENVIRONMENT.checkedAt = new Date().toISOString();
  window.NX_ENVIRONMENT.production = false; // legacy field, preserved for any existing consumer; superseded by .name

  document.addEventListener('DOMContentLoaded', function () {
    var result = classifyEnvironment();
    result.checkedAt = new Date().toISOString();
    result.production = result.name === 'AUTHORIZED_PRODUCTION';
    window.NX_ENVIRONMENT = result;

    if (!result.allowed) {
      document.body.innerHTML =
        '<pre style="padding:24px;font-family:monospace;white-space:pre-wrap">' +
        'ENVIRONMENT GUARD STOP\n\n' +
        'This is PORTAL-NEXT V2 and it is running on a hostname (' + result.hostname + ') ' +
        'that is not recognized as LOCAL_DEV and does not appear in this build\'s ' +
        'authorizedHostnames allowlist. Refusing to render.\n\n' +
        'If this IS the intended production host, a Human must record it in ' +
        'assets/js/intelligence-runtime-config.production.js\'s authorizedHostnames ' +
        'array -- this cannot be self-authorized from the browser.' +
        '</pre>';
      console.error('[environment-guard] STOP: unauthorized/unknown host:', result.hostname);
    }
  });
})();
