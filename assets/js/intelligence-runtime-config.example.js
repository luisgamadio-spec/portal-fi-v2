// Copie para intelligence-runtime-config.local.js somente no computador
// de teste (esse arquivo é ignorado pelo git). Nunca aponte para um
// projeto Supabase real ou produção a partir daqui.
//
// AUTH FOUNDATION Phase 2C: supabaseUrl/supabasePublishableKey aqui
// ativam o login/guard de autorização geral do Portal V2 (não só a
// Intelligence) -- ver assets/js/intelligence-runtime-config.js.
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'real_text',
  supabaseUrl: 'http://127.0.0.1:8790',
  supabasePublishableKey: 'local-mock-anon-key',
  textEndpoint: 'http://127.0.0.1:8801/'
};
