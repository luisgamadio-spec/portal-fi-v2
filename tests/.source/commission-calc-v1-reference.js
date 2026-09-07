/* PM-5I — byte-identical extraction of the REAL V1 (Authority) commission
   formula, portal-financiamento-brabus-secure/assets/js/portal-app.js.
   Every function body below is copied VERBATIM (character-for-character,
   only re-indented) from that file -- no logic added, removed, or
   "improved". Line numbers cited are from the Authority repo at HEAD
   4d8ce1d (== ia-reconciliation-v2-local@908d028 for this specific file,
   confirmed byte-identical via `git diff 4d8ce1d 908d028 -- assets/js/
   portal-app.js` returning empty).

   The only change from the original file is a loading shim: the real
   file reads `PORTAL_CONFIG` as a module-level global via `cfgNum()`;
   here that same function is preserved verbatim and callers pass the
   config explicitly via `window.PORTAL_CONFIG` before invoking, so this
   file can be loaded standalone in a blank page (same technique already
   used by this repo's own cash-conversion-parity-test.py for its
   reference/adapter pair). */

// portal-app.js:64-78, verbatim.
const DEFAULT_PORTAL_CONFIG = {
  share_minimo: 40,
  spf_liquido_percentual: 70,
  bonus_spf_analista: 150,
  limite_retorno_novos: 12000,
  limite_retorno_seminovos: 8000,
  vendedor_faixa_baixo_share_baixo: 10,
  vendedor_faixa_baixo_share_alto: 15,
  vendedor_faixa_alto_share_baixo: 15,
  vendedor_faixa_alto_share_alto: 20,
  gerente_faixa_share_baixo: 3,
  gerente_faixa_share_alto: 4,
  analista_faixa_share_baixo: 3.5,
  analista_faixa_share_alto: 4.5
};
window.PORTAL_CONFIG = { ...DEFAULT_PORTAL_CONFIG };

// portal-app.js:80-84, verbatim.
function cfgNum(chave) {
  const v = window.PORTAL_CONFIG[chave];
  const n = Number(String(v).replace(',', '.'));
  return Number.isFinite(n) ? n : DEFAULT_PORTAL_CONFIG[chave];
}

// portal-app.js:60, verbatim.
const shareNum = (a, b) => b ? ((a / b) * 100) : 0;

// portal-app.js:111-131, verbatim.
function commissionCalc(status, m, cls = '') {
  const share = shareNum(m.financiadas, m.vendidas);
  const shareMin = cfgNum('share_minimo');
  const spfLiquido = (+m.spf || 0) * (cfgNum('spf_liquido_percentual') / 100);
  const rentTotal = (+m.retorno || 0) + spfLiquido;
  let faixa = 0, comissaoPrincipal = 0, comissaoSpf = 0, comissaoTotal = 0;
  if (cls === 'manager') {
    faixa = share >= shareMin ? (cfgNum('gerente_faixa_share_alto') / 100) : (cfgNum('gerente_faixa_share_baixo') / 100);
  } else if (cls === 'analyst') {
    faixa = share >= shareMin ? (cfgNum('analista_faixa_share_alto') / 100) : (cfgNum('analista_faixa_share_baixo') / 100);
    comissaoSpf = (+m.spfQty || 0) * cfgNum('bonus_spf_analista');
  } else {
    const isSemi = (status || '').toString().toUpperCase().includes('SEMINOVOS') && !(status || '').toString().toUpperCase().includes('NOVOS/SEMINOVOS');
    const limite = isSemi ? cfgNum('limite_retorno_seminovos') : cfgNum('limite_retorno_novos');
    if ((+rentTotal || 0) < limite) { faixa = share >= shareMin ? (cfgNum('vendedor_faixa_baixo_share_alto') / 100) : (cfgNum('vendedor_faixa_baixo_share_baixo') / 100); }
    else { faixa = share >= shareMin ? (cfgNum('vendedor_faixa_alto_share_alto') / 100) : (cfgNum('vendedor_faixa_alto_share_baixo') / 100); }
  }
  comissaoPrincipal = rentTotal * faixa;
  comissaoTotal = comissaoPrincipal + comissaoSpf;
  return { share, spfLiquido, rentTotal, faixa, comissaoPrincipal, comissaoSpf, comissaoTotal };
}

// portal-app.js:6252-6284, verbatim (secure-mode branch only -- the
// legacy/XLSX branch, gated on `PORTAL_RUNTIME_CONFIG.authMode`, is
// classified STALE_V1_REFERENCE this wave, never the live production
// path; `t` is passed in directly here instead of being computed from
// DATA.auth, since that population step belongs to the caller/RPC layer,
// not to this pure-formula extraction).
function calcGestorFIGrupo(t) {
  const share = t.vendidas ? ((t.financiadas / t.vendidas) * 100) : 0;
  const faixa = share < 40 ? 0.0016 : 0.0030; // 0,16% ou 0,30% -- literal, never cfgNum('share_minimo')
  const spfLiquido = (+t.spf || 0) * (cfgNum('spf_liquido_percentual') / 100);
  const base = (+t.retorno || 0) + spfLiquido;
  const comissaoPrincipal = base * faixa;
  const bonusSpf = (+t.spfQty || 0) * 30; // literal, never cfgNum('bonus_spf_analista')
  const comissaoFinal = comissaoPrincipal + bonusSpf;
  return { ...t, share, faixa, spfLiquido, base, comissaoPrincipal, bonusSpf, comissaoFinal };
}

window.V1_REFERENCE = { DEFAULT_PORTAL_CONFIG, cfgNum, shareNum, commissionCalc, calcGestorFIGrupo };
