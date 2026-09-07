/* PM-5I — mechanical JS extraction of the IA-2C.5.1 port,
   portal-financiamento-brabus-secure/supabase/functions/portal-ai/
   index.ts (Deno/TypeScript), lines 1830-1843 (COMMISSION_CONFIG_
   DEFAULTS) and 1870-1894 (liveCommissionCalc) and 2016-2033 (the
   inline GESTOR F&I block, wrapped here into a function for testing).
   The ONLY change from the .ts source is removing TypeScript-only
   syntax (`: type` parameter/return annotations, `Record<string,
   number>`) so this runs as plain JS in a browser page -- every
   expression, operator, branch and literal constant is otherwise
   character-for-character identical to the real file. Confirmed this
   file's own commit (d0996b6) is an ancestor of both the current
   Authority HEAD (4d8ce1d) and ia-reconciliation-v2-local (908d028),
   and portal-ai/index.ts itself is byte-identical between those two. */

// portal-ai/index.ts:1830-1843, verbatim (values only -- identical to
// the V1 reference's DEFAULT_PORTAL_CONFIG by inspection, cross-checked
// field-by-field in the PM-5I report).
const COMMISSION_CONFIG_DEFAULTS = {
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

// portal-ai/index.ts:1870-1894 ("commissionCalc() -- portal-app.js:111-131,
// verbatim." per the file's own comment), TS type annotations stripped only.
function liveCommissionCalc(status, m, cls, cfg) {
  const share = m.vendidas ? (m.financiadas / m.vendidas) * 100 : 0;
  const shareMin = cfg.share_minimo;
  const spfLiquido = (m.spf || 0) * (cfg.spf_liquido_percentual / 100);
  const rentTotal = (m.retorno || 0) + spfLiquido;
  let faixa = 0, comissaoSpf = 0;
  if (cls === "manager") {
    faixa = share >= shareMin ? cfg.gerente_faixa_share_alto / 100 : cfg.gerente_faixa_share_baixo / 100;
  } else if (cls === "analyst") {
    faixa = share >= shareMin ? cfg.analista_faixa_share_alto / 100 : cfg.analista_faixa_share_baixo / 100;
    comissaoSpf = (m.spfQty || 0) * cfg.bonus_spf_analista;
  } else {
    const statusUpper = String(status || "").toUpperCase();
    const isSemi = statusUpper.includes("SEMINOVOS") && !statusUpper.includes("NOVOS/SEMINOVOS");
    const limite = isSemi ? cfg.limite_retorno_seminovos : cfg.limite_retorno_novos;
    if (rentTotal < limite) {
      faixa = share >= shareMin ? cfg.vendedor_faixa_baixo_share_alto / 100 : cfg.vendedor_faixa_baixo_share_baixo / 100;
    } else {
      faixa = share >= shareMin ? cfg.vendedor_faixa_alto_share_alto / 100 : cfg.vendedor_faixa_alto_share_baixo / 100;
    }
  }
  const comissaoPrincipal = rentTotal * faixa;
  const comissaoTotal = comissaoPrincipal + comissaoSpf;
  return { share, spfLiquido, rentTotal, faixa, comissaoPrincipal, comissaoSpf, comissaoTotal };
}

// portal-ai/index.ts:2021-2028 (the GESTOR F&I block inside
// fetchLivePreviewLines), wrapped in a function taking `gm`/`cfg`
// directly (the surrounding aggregation-from-`totals` step belongs to
// the RPC-calling caller, not this pure-formula extraction) -- every
// expression otherwise verbatim, including both comments citing the
// literal (non-cfg) constants.
function liveGestorFIGrupo(gm, cfg) {
  const gShare = gm.vendidas ? (gm.financiadas / gm.vendidas) * 100 : 0;
  const gFaixa = gShare < 40 ? 0.0016 : 0.0030; // portal-app.js:6246, literal -- nunca cfg.share_minimo
  const gSpfLiquido = (gm.spf || 0) * (cfg.spf_liquido_percentual / 100);
  const gBase = (gm.retorno || 0) + gSpfLiquido;
  const gPrincipal = gBase * gFaixa;
  const gBonusSpf = (gm.spfQty || 0) * 30; // portal-app.js:6250, literal -- nunca cfg.bonus_spf_analista
  const gTotal = gPrincipal + gBonusSpf;
  return { share: gShare, faixa: gFaixa, spfLiquido: gSpfLiquido, rentTotal: gBase, comissaoPrincipal: gPrincipal, bonusSpf: gBonusSpf, comissaoFinal: gTotal };
}

window.IA_CANDIDATE = { COMMISSION_CONFIG_DEFAULTS, liveCommissionCalc, liveGestorFIGrupo };
