/* PORTAL-NEXT V2 — Module Registry loader (Gate 13).
   Loads config/module-registry.json (metadata only, no business logic
   — see tests/business-logic-scanner.py) and exposes lookup helpers. */
(function () {
  'use strict';

  window.NX_REGISTRY = {
    modules: [],
    loaded: false,
    error: null,

    load: function () {
      var self = this;
      return fetch('config/module-registry.json')
        .then(function (r) {
          if (!r.ok) throw new Error('module-registry.json HTTP ' + r.status);
          return r.json();
        })
        .then(function (data) {
          self.modules = data.modules || [];
          self.migrationStatusEnum = data.migrationStatusEnum || [];
          self.loaded = true;
          return self.modules;
        })
        .catch(function (err) {
          self.error = String(err && err.message || err);
          console.error('[module-registry] failed to load', err);
          throw err;
        });
    },

    byId: function (id) {
      return this.modules.find(function (m) { return m.id === id; }) || null;
    }
  };
})();
