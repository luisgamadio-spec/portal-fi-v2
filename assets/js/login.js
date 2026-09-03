/* PORTAL-NEXT V2 — Login (AUTH FOUNDATION Phase 2B).

   LOGIN owns authentication UX only (AUTH FOUNDATION Phase 1 Gate 20)
   -- it renders the form and reacts to assets/js/auth-core.js's state,
   never calls Supabase directly, never duplicates a Supabase client.

   AUTH FOUNDATION Phase 2A Gate 16 (corrected from Phase 1): Landing
   is LOGIN_REQUIRED, not anonymous -- this file is V2's one genuinely
   anonymous surface. */
(function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
    });
  }

  // AUTH FOUNDATION Phase 1 Gate 24: generic, non-disclosing messages
  // matching V1's own security posture exactly -- never reveal which
  // specific check failed.
  var STATE_MESSAGES = {};
  function messagesFor(STATES) {
    var m = {};
    m[STATES.INVALID_CREDENTIALS] = 'E-mail ou senha inválidos.';
    m[STATES.NO_PORTAL_PROFILE] = 'Usuário não provisionado ou inativo.';
    m[STATES.INACTIVE_USER] = 'Usuário não provisionado ou inativo.';
    m[STATES.SESSION_EXPIRED] = 'Sua sessão expirou. Entre novamente.';
    m[STATES.NETWORK_ERROR] = 'Não foi possível conectar. Verifique sua conexão e tente novamente.';
    m[STATES.RPC_ERROR] = 'Não foi possível concluir o login agora. Tente novamente.';
    return m;
  }

  // AUTH FOUNDATION Phase 2B, Gate 16: TURNSTILE_PRODUCTION_WIRING_PENDING.
  // V1 gates real login behind Cloudflare Turnstile (production site
  // key, cannot run meaningfully against a local/homolog host without
  // production configuration coupling this Wave was told not to
  // introduce). This is the explicit extension point: a future gate
  // replaces getCaptchaToken() with a real widget render + token
  // read, without touching auth-core.js's login() signature (it
  // already accepts a captchaToken as an optional 3rd argument the
  // backend RPC contract can start requiring later -- see
  // AUTH-V1-FIRST-ACCESS-DEFECT's sibling tracking note for the
  // equivalent V1-parity gap this leaves open). No secret, no
  // production key, no global disable of anti-abuse anywhere.
  function getCaptchaToken() {
    return Promise.resolve(null);
  }

  var mounted = false;
  var submitting = false;

  function ensureMounted() {
    var root = document.getElementById('nxLoginRoot');
    if (mounted || !root) return root;
    root.innerHTML =
      '<div class="loginShell">' +
        '<div class="loginCard">' +
          '<img class="loginLogo" src="assets/images/brabus-logo.png" alt="Grupo Brabus Mitsubishi">' +
          '<h1 class="loginTitle">Portal F&amp;I</h1>' +
          '<p class="loginSubtitle">Entre com sua conta para continuar.</p>' +
          '<form id="loginForm" novalidate>' +
            '<div class="loginField">' +
              '<label for="loginEmail">E-mail</label>' +
              '<input id="loginEmail" name="email" type="email" autocomplete="username" required>' +
            '</div>' +
            '<div class="loginField">' +
              '<label for="loginPassword">Senha</label>' +
              '<input id="loginPassword" name="password" type="password" autocomplete="current-password" required>' +
            '</div>' +
            '<div id="loginStatus" class="loginStatus" role="status" aria-live="polite" hidden></div>' +
            '<button type="submit" id="loginSubmit" class="loginSubmit">Entrar</button>' +
          '</form>' +
        '</div>' +
      '</div>';

    var form = document.getElementById('loginForm');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (submitting) return;
      var email = document.getElementById('loginEmail').value.trim();
      var password = document.getElementById('loginPassword').value;
      if (!email || !password) return;
      submitting = true;
      setSubmitting(true);
      getCaptchaToken().then(function (captchaToken) {
        window.NX_AUTH_CORE.login(email, password, captchaToken);
      });
    });
    mounted = true;
    return root;
  }

  function setSubmitting(isSubmitting) {
    var btn = document.getElementById('loginSubmit');
    var email = document.getElementById('loginEmail');
    var password = document.getElementById('loginPassword');
    if (btn) { btn.disabled = isSubmitting; btn.textContent = isSubmitting ? 'Entrando…' : 'Entrar'; }
    if (email) email.disabled = isSubmitting;
    if (password) password.disabled = isSubmitting;
  }

  function renderStatus(text, kind) {
    var el = document.getElementById('loginStatus');
    if (!el) return;
    if (!text) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.className = 'loginStatus loginStatus' + (kind === 'error' ? 'Error' : 'Info');
    el.textContent = text;
  }

  window.NX_LOGIN = {
    render: function () {
      var root = ensureMounted();
      if (!root) return;
      root.hidden = false;

      var STATES = window.NX_AUTH_CORE.STATES;
      STATE_MESSAGES = messagesFor(STATES);
      var state = window.NX_AUTH_CORE.getState();

      if (state === STATES.AUTHENTICATING || state === STATES.AUTHENTICATED_RESOLVING_PROFILE) {
        submitting = true;
        setSubmitting(true);
        renderStatus(null);
        return;
      }

      submitting = false;
      setSubmitting(false);
      var message = STATE_MESSAGES[state];
      if (message) renderStatus(message, 'error');
      else renderStatus(null);
    },

    hide: function () {
      var root = document.getElementById('nxLoginRoot');
      if (root) root.hidden = true;
    }
  };

  // Re-render on every relevant auth-core transition so the login
  // screen reflects INVALID_CREDENTIALS/NETWORK_ERROR/etc. without
  // shell.js having to know Login's own internal states.
  document.addEventListener('DOMContentLoaded', function () {
    window.NX_AUTH_CORE.onStateChange(function (state) {
      var STATES = window.NX_AUTH_CORE.STATES;
      if (state === STATES.AUTHORIZED || state === STATES.AUTH_NOT_CONFIGURED) return; // shell.js hides Login itself
      var root = document.getElementById('nxLoginRoot');
      if (root && !root.hidden) window.NX_LOGIN.render();
    });
  });
})();
