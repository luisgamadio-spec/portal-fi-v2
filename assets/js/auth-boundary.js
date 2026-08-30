/* PORTAL-NEXT V2 — Auth Boundary (Gate 17).
   Interface/contract ONLY. No login implementation, no Supabase call,
   no secret, no credential of any kind. This exists so a future Wave
   knows the SHAPE it must implement when it actually wires real
   Supabase Auth (reused exactly as V1 implements it — see
   PORTAL-NEXT-01/SHADOW-UAT-PLAN.md Gate 21: "no parallel auth is
   created"). Every method below throws NOT_IMPLEMENTED. */
(function () {
  'use strict';

  function notImplemented(name) {
    return function () {
      throw new Error(
        '[auth-boundary] ' + name + '() is a Foundation-phase contract ' +
        'stub, not a real implementation. It must be wired to reuse ' +
        'V1\'s exact Supabase Auth flow (signInWithPassword + RPC-based ' +
        'role resolution via usuario_logado_fi) in a future Wave — see ' +
        'PORTAL-NEXT-01/ARCHITECTURE-AUDIT.md Gate 6. No new auth ' +
        'mechanism should ever be invented here.'
      );
    };
  }

  window.NX_AUTH = {
    // Resolves to { session, user: { tipo, ... } } on success. V1's
    // equivalent: supabaseClient.auth.signInWithPassword(...) then RPC
    // usuario_logado_fi() to resolve the authorized profile — never
    // trust a client-side role claim (see ARCHITECTURE-AUDIT.md Gate 6).
    signIn: notImplemented('signIn'),

    // Resolves to the current session or null. V1's equivalent:
    // supabaseClient.auth.getSession().
    getSession: notImplemented('getSession'),

    // Subscribes to auth state changes. V1's equivalent:
    // supabaseClient.auth.onAuthStateChange(...).
    onAuthStateChange: notImplemented('onAuthStateChange'),

    // Resolves the authorized role/profile for the current session via
    // a SERVER-SIDE RPC call — never a client-side claim. V1's
    // equivalent: RPC usuario_logado_fi().
    resolveAuthorizedProfile: notImplemented('resolveAuthorizedProfile'),

    signOut: notImplemented('signOut')
  };
})();
