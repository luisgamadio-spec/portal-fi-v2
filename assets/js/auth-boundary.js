/* PORTAL-NEXT V2 — Auth Boundary (IA-V2-2).

   Real implementation of the same contract the Foundation-phase stub
   declared (Gate 17 of that Wave) — same shape, same method names,
   NOT a new auth mechanism. Reuses V1's exact real flow:
   supabaseClient.auth.signInWithPassword({email, password}) for
   login, supabaseClient.auth.getSession() for the current session,
   and RPC usuario_logado_fi() for role resolution — a SERVER-SIDE
   lookup, never a client-side claim (see
   PORTAL-NEXT-01/ARCHITECTURE-AUDIT.md Gate 6, carried forward here).

   Only active when window.NX_INTELLIGENCE_CONFIG.mode === 'real_text'
   AND both supabaseUrl/supabasePublishableKey are configured (Gate 8
   feature containment — the default committed config has mode:
   'fixture' and both fields null, so this module does nothing on any
   host where no local override file exists, production included).
   When inactive, every method still throws with the same
   NOT_IMPLEMENTED-shaped message the Foundation stub used, so any
   other caller that isn't Intelligence's own real-mode path continues
   to fail loudly instead of silently no-op'ing. */
(function () {
  'use strict';

  function notImplemented(name) {
    return function () {
      throw new Error(
        '[auth-boundary] ' + name + '() has no active Supabase client this ' +
        'session -- either NX_INTELLIGENCE_CONFIG.mode is not "real_text", ' +
        'or supabaseUrl/supabasePublishableKey are not configured. See ' +
        'assets/js/intelligence-runtime-config.example.js.'
      );
    };
  }

  var cfg = window.NX_INTELLIGENCE_CONFIG || {};
  var active = cfg.mode === 'real_text' && !!cfg.supabaseUrl && !!cfg.supabasePublishableKey;

  if (!active || typeof window.supabase === 'undefined') {
    window.NX_AUTH = {
      signIn: notImplemented('signIn'),
      getSession: notImplemented('getSession'),
      onAuthStateChange: notImplemented('onAuthStateChange'),
      resolveAuthorizedProfile: notImplemented('resolveAuthorizedProfile'),
      signOut: notImplemented('signOut')
    };
    return;
  }

  var client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabasePublishableKey);

  // Mirrors V1's portalUserFromDatabase() field mapping exactly (same
  // row shape from usuario_logado_fi()) -- not reinvented, not
  // simplified, so a real backend's real row shape is handled
  // identically to how the production frontend already handles it.
  function userFromRow(row) {
    if (!row) return null;
    return {
      id: row.id,
      authUserId: row.auth_user_id,
      nome: row.nome || '',
      tipo: String(row.perfil || '').toUpperCase(),
      loja: row.loja || '',
      ativo: row.ativo !== false,
      primeiroAcesso: row.primeiro_acesso === true
    };
  }

  window.NX_AUTH = {
    signIn: function (email, password) {
      return client.auth.signInWithPassword({ email: email, password: password }).then(function (result) {
        if (result.error) throw result.error;
        return { session: result.data.session };
      });
    },

    getSession: function () {
      return client.auth.getSession().then(function (result) {
        return result.data ? result.data.session : null;
      });
    },

    onAuthStateChange: function (callback) {
      return client.auth.onAuthStateChange(function (event, session) {
        callback(event, session);
      });
    },

    // SERVER-SIDE role resolution only -- never trusts a client-held
    // claim. A caller that skips this and reads e.g. a JWT's own
    // unverified claims for authorization would be reintroducing
    // exactly what Gate 6 forbids.
    resolveAuthorizedProfile: function () {
      return client.rpc('usuario_logado_fi').then(function (result) {
        if (result.error) throw result.error;
        var row = Array.isArray(result.data) ? result.data[0] : result.data;
        var user = userFromRow(row);
        if (!user || !user.ativo) throw new Error('Usuário não provisionado ou inativo.');
        return user;
      });
    },

    signOut: function () {
      return client.auth.signOut();
    },

    // Not part of the original Foundation-stub contract -- added here
    // because the TEXT transport adapter needs the raw bearer token,
    // not just the session object, and re-deriving it from getSession()
    // at every call site would duplicate this same one-liner everywhere.
    getAccessToken: function () {
      return client.auth.getSession().then(function (result) {
        var session = result.data ? result.data.session : null;
        return session ? session.access_token : null;
      });
    }
  };
})();
