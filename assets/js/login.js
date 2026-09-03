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
    m[STATES.CAPTCHA_FAILED] = 'Não foi possível validar a verificação de segurança. Tente novamente.';
    return m;
  }

  // AUTH FOUNDATION Phase 3B: Cloudflare Turnstile wiring. LOGIN owns
  // the entire widget lifecycle (Gate 8) -- Auth Core only ever
  // receives an opaque captchaToken string, never touches Cloudflare
  // DOM/script. turnstileSiteKey absent/empty (every mock/fixture
  // host, the committed default) means real mode is not in use here
  // at all: getCaptchaToken() resolves null immediately, zero
  // Cloudflare network dependency (Gate 14/20). Pattern verified
  // against V1's own already-working implementation (Authority repo,
  // portal-app.js loadTurnstileScript()/obtainTurnstileToken()) rather
  // than invented from memory (Gate 7).
  var turnstileSiteKey = String((window.NX_INTELLIGENCE_CONFIG || {}).turnstileSiteKey || '').trim();
  var turnstileScriptPromise = null;
  var turnstileTokenPromise = null; // in-flight guard: prevents duplicate concurrent widgets

  function loadTurnstileScript() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (turnstileScriptPromise) return turnstileScriptPromise;
    turnstileScriptPromise = new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[data-nx-turnstile]');
      var script = existing || document.createElement('script');
      var timeout = setTimeout(function () {
        reject(new Error('Tempo esgotado ao carregar a verificação de segurança.'));
      }, 20000);
      script.onload = function () {
        clearTimeout(timeout);
        if (window.turnstile) resolve(window.turnstile);
        else reject(new Error('A verificação de segurança não foi inicializada.'));
      };
      script.onerror = function () {
        clearTimeout(timeout);
        turnstileScriptPromise = null;
        reject(new Error('Não foi possível carregar a verificação de segurança.'));
      };
      if (!existing) {
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
        script.async = true;
        script.defer = true;
        script.dataset.nxTurnstile = 'true';
        document.head.appendChild(script);
      }
    });
    return turnstileScriptPromise;
  }

  // Renders a fresh widget into #loginTurnstile and executes it
  // (execution:'execute' + appearance:'interaction-only' -- invisible
  // unless Cloudflare decides an interactive check is required,
  // matching Gate 12's "no redesign"). A new widget per call, mirrors
  // V1's own proven pattern exactly -- this also IS the token reset
  // Gate 17 asks for: a stale/used token is never reused, the next
  // submit attempt always requests a fresh one.
  function renderAndExecuteTurnstile(api) {
    return new Promise(function (resolve, reject) {
      var host = document.getElementById('loginTurnstile');
      if (!host) { reject(new Error('Verificação de segurança indisponível nesta tela.')); return; }
      host.innerHTML = '';
      var finished = false;
      var timer = setTimeout(function () {
        finish(new Error('A verificação de segurança expirou. Tente novamente.'));
      }, 60000);
      function finish(error, token) {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        if (error) reject(error); else resolve(token);
      }
      try {
        var widgetId = api.render(host, {
          sitekey: turnstileSiteKey,
          theme: 'dark',
          appearance: 'interaction-only',
          execution: 'execute',
          callback: function (token) { finish(null, token); },
          'error-callback': function () { finish(new Error('CAPTCHA_FAILED')); },
          'expired-callback': function () { finish(new Error('A verificação de segurança expirou. Tente novamente.')); }
        });
        api.execute(widgetId);
      } catch (err) { finish(err); }
    });
  }

  function getCaptchaToken() {
    if (!turnstileSiteKey) return Promise.resolve(null);
    if (turnstileTokenPromise) return turnstileTokenPromise;
    turnstileTokenPromise = loadTurnstileScript()
      .then(renderAndExecuteTurnstile)
      .then(function (token) {
        turnstileTokenPromise = null;
        return token;
      }, function (err) {
        turnstileTokenPromise = null;
        throw err;
      });
    return turnstileTokenPromise;
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
            (turnstileSiteKey ? '<div id="loginTurnstile" class="loginTurnstile" aria-label="Verificação de segurança"></div>' : '') +
            '<div id="loginStatus" class="loginStatus" role="status" aria-live="polite" hidden></div>' +
            '<button type="submit" id="loginSubmit" class="loginSubmit">Entrar</button>' +
          '</form>' +
        '</div>' +
      '</div>';

    // Warm up the Turnstile script early (Gate 10) so the first
    // submit doesn't pay the full script-load latency -- purely a
    // prefetch, no widget is rendered/executed until an actual submit.
    if (turnstileSiteKey) loadTurnstileScript().catch(function () {});

    var form = document.getElementById('loginForm');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (submitting) return;
      var email = document.getElementById('loginEmail').value.trim();
      var password = document.getElementById('loginPassword').value;
      if (!email || !password) return;
      submitting = true;
      setSubmitting(true);
      renderStatus(null);
      // Gate 14: in real mode, never call signInWithPassword without
      // a captchaToken -- a rejected getCaptchaToken() falls straight
      // to the .catch below and auth-core.login() is never reached.
      getCaptchaToken().then(function (captchaToken) {
        return window.NX_AUTH_CORE.login(email, password, captchaToken);
      }).catch(function () {
        submitting = false;
        setSubmitting(false);
        renderStatus('Não foi possível validar a verificação de segurança. Tente novamente.', 'error');
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
