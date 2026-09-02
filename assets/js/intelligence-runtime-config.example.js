// Copie para intelligence-runtime-config.local.js somente no computador
// de teste (esse arquivo é ignorado pelo git). Nunca aponte para um
// projeto Supabase real ou produção a partir daqui.
window.NX_INTELLIGENCE_CONFIG = {
  mode: 'real_text',
  supabaseUrl: 'http://127.0.0.1:8790',
  supabasePublishableKey: 'local-mock-anon-key',
  textEndpoint: 'http://127.0.0.1:8801/'
};
