/* PORTAL-NEXT V2 — Brabus Intelligence LATENCY DIAGNOSTIC COLLECTOR
   (LATENCY-2C).

   LATENCY-2B's own finding: LATENCY-1 timing metadata exists and is
   live, but a real Human sample could not be recovered after the
   browser session closed, because it only ever reached console.log
   (`[bai-timing]`) -- never a retrievable artifact, and there is no
   server-side log-retrieval path in this environment either (confirmed
   that Wave). Human does not want a recurring "open DevTools, copy
   console" workflow.

   This file does NOT create a second timing architecture. It is the
   ONE place intelligence-panel.js's own logDevTiming() (Text) and
   intelligence-voice.js's own bridgeToPortalIntelligence() (Voice)
   hand their ALREADY-built, ALREADY-safe [bai-timing] object, so it
   can additionally be kept in a small in-memory ring buffer and
   exported as one JSON file on a Human's explicit action. Same
   "single timing truth" discipline as IA-3G.4/LATENCY-1: this module
   never reads payload/reply/conversation content, ever.

   SAFETY:
   - memory only -- no localStorage/sessionStorage/IndexedDB, no
     network call, no server upload, no external analytics.
   - homologation/dev only (window.NX_ENVIRONMENT, already the
     existing, established classification -- AUTHORIZED_PRODUCTION is
     this repo's own real, deployed GitHub Pages homologation
     hostname, confirmed structurally elsewhere to be the only
     non-local hostname this repo's own script tags ever serve;
     UNKNOWN_HOST -- including the real, separate production domain,
     which this repo never serves at all -- fails closed).
   - explicit, named allowlist serializer (buildSafeEntry below) --
     never a generic spread of the caller's object, even though that
     object is already safe by construction (buildDevTiming()'s own
     "hand-copied, never spread" discipline) -- defense in depth at
     this hand-off point too, matching this codebase's existing
     layering style.
   - cleared automatically on every identity transition (logout or a
     different authenticated user) via NX_INTELLIGENCE_STATE's own
     existing onOwnerChange event (SESSIONSEC1) -- never a new/parallel
     identity read, never preserved across identities. */
(function () {
  'use strict';

  var MAX_ENTRIES = 100;
  var entries = [];

  // Enabled on the real deployed homologation hostname
  // (AUTHORIZED_PRODUCTION, environment-guard.js's own name for it --
  // NOT the separate brabus.blistiq.com.br production domain this repo
  // never serves) and on local dev, for this Wave's own testing.
  // Fails closed (disabled) on any UNKNOWN_HOST or if NX_ENVIRONMENT
  // itself is somehow absent.
  function isHomologOrDevEnabled() {
    var env = window.NX_ENVIRONMENT;
    return !!env && (env.name === 'AUTHORIZED_PRODUCTION' || env.name === 'LOCAL_DEV');
  }

  function num(v) { return (typeof v === 'number' && !isNaN(v)) ? v : null; }
  function bool(v) { return (typeof v === 'boolean') ? v : null; }
  function str(v, maxLen) { return (typeof v === 'string') ? v.slice(0, maxLen || 64) : null; }
  function numArray(v, maxLen) {
    if (!Array.isArray(v)) return null;
    var out = [];
    for (var i = 0; i < v.length && i < (maxLen || 20); i++) {
      if (typeof v[i] === 'number') out.push(v[i]);
    }
    return out;
  }

  // The ONE explicit allowlist -- every field this function does not
  // name is dropped, unconditionally, regardless of what the caller's
  // object also happens to carry. Adding a future safe field means
  // adding one more named line here, never widening this into a spread.
  function buildSafeEntry(raw, surface) {
    if (!raw || typeof raw !== 'object') return null;
    var stage = (raw.stage_ms && typeof raw.stage_ms === 'object') ? raw.stage_ms : {};
    var openaiPassMs = numArray(stage.openai_pass_ms, 10);
    var openaiPassCount = num(stage.openai_pass_count);
    var retryCount = num(raw.openai_retry_count);
    var entry = {
      captured_at: Date.now(),
      surface: (surface === 'voice') ? 'voice' : 'text',
      correlation_id: str(raw.correlation_id, 100),
      // LATENCY-1's own mapping: execution_path is already the safe
      // categorical "which path" identifier (its own report's "tool
      // category" equivalent) -- not renamed here, same vocabulary.
      execution_path: str(stage.execution_path, 40),

      client_total_ms: num(raw.total_ui_ms),
      network_plus_server_ms: num(raw.network_plus_server_ms),
      client_parse_adapter_ms: num(raw.client_parse_adapter_ms),
      render_ms: num(raw.render_ms),

      edge_total_ms: num(raw.edge_latency_ms),
      request_validation_ms: num(stage.request_validation_ms),
      kill_switch_config_ms: num(stage.kill_switch_config_ms),
      authority_resolution_ms: num(stage.authority_resolution_ms),
      tool_policy_ms: num(stage.tool_policy_ms),
      response_assembly_ms: num(stage.response_assembly_ms),

      rpc_total_ms: num(raw.rpc_total_ms),
      rpc_count: num(raw.rpc_count),

      openai_pass_ms: openaiPassMs,
      openai_pass_count: openaiPassCount,
      openai_total_ms: openaiPassMs ? openaiPassMs.reduce(function (s, n) { return s + n; }, 0) : null,
      openai_retry_count: retryCount,
      openai_retry_occurred: bool(raw.openai_retry_occurred),
      // LATENCY-2C Section 5 -- "if useful and safe": pure arithmetic
      // on two fields already on this same entry, never a new capture.
      openai_attempt_count: (openaiPassCount !== null && retryCount !== null) ? (openaiPassCount + retryCount) : null,
      openai_model: str(raw.openai_model, 40),
      first_token_observable: bool(raw.first_token_observable),

      tool_used: bool(raw.tool_used),
      instance_age_ms: num(raw.edge_instance_age_ms),

      // Voice-only -- Section 10: included only because it is already
      // reliably measured (intelligence-voice.js's own t0 -> Date.now()
      // span around the shared-adapter call, the same number diagPush
      // already records separately). null for Text, never fabricated.
      voice_tool_bridge_ms: (surface === 'voice') ? num(raw.voice_tool_bridge_ms) : null
    };
    // Section 11 -- external_unaccounted_ms, ONLY when honestly
    // derivable from fields this same entry already carries (never
    // invented when either side is missing). network_plus_server_ms is
    // the client-measured "fetch resolved" span (network + Edge total,
    // client clock); edge_total_ms is the Edge's own self-reported
    // total (Edge clock). Their difference approximates whatever time
    // is not accounted for by either side's own measured work -- only
    // as trustworthy as clock sync between the two machines, the exact
    // same caveat buildDevTiming's own *_approx fields already carry.
    entry.external_unaccounted_ms = (entry.network_plus_server_ms !== null && entry.edge_total_ms !== null)
      ? (entry.network_plus_server_ms - entry.edge_total_ms)
      : null;
    return entry;
  }

  function capture(raw, surface) {
    if (!isHomologOrDevEnabled()) return;
    var entry = buildSafeEntry(raw, surface);
    if (!entry) return;
    entries.push(entry);
    if (entries.length > MAX_ENTRIES) entries.shift(); // FIFO
  }

  function getEntries() { return entries.slice(); }

  function clear() { entries = []; }

  function exportJson() {
    var env = window.NX_ENVIRONMENT;
    return JSON.stringify({
      schema_version: 1,
      exported_at: new Date().toISOString(),
      environment: 'HOMOLOGATION',
      environment_hostname: (env && env.hostname) || null,
      entry_count: entries.length,
      entries: entries
    }, null, 2);
  }

  function pad2(n) { return String(n).padStart(2, '0'); }

  function downloadExport() {
    var json = exportJson();
    var blob = new Blob([json], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var d = new Date();
    var filename = 'brabus-intelligence-latency-' +
      d.getFullYear() + pad2(d.getMonth() + 1) + pad2(d.getDate()) + '-' +
      pad2(d.getHours()) + pad2(d.getMinutes()) + pad2(d.getSeconds()) + '.json';
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  window.NX_INTELLIGENCE_LATENCY_DIAG = {
    isEnabled: isHomologOrDevEnabled,
    capture: capture,
    getEntries: getEntries,
    clear: clear,
    exportJson: exportJson,
    downloadExport: downloadExport
  };

  // SESSIONSEC1 -- diagnostics never outlive the identity that produced
  // them. Reuses NX_INTELLIGENCE_STATE's own existing owner-change
  // event (the exact mechanism the conversation store itself already
  // resets on) rather than a second, parallel auth listener.
  if (window.NX_INTELLIGENCE_STATE && typeof window.NX_INTELLIGENCE_STATE.onOwnerChange === 'function') {
    window.NX_INTELLIGENCE_STATE.onOwnerChange(function () { clear(); });
  }
})();
