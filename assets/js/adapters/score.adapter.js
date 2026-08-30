/* PORTAL-NEXT V2 — Score Adapter (Gate 5: PURE EXTRACTION).
   SOURCE: git show origin/main:modules/score.html
   (portal-financiamento-brabus-secure) — NOT the local clone, which is
   PROVED divergent for this file (see docs/SCORE-ENGINE-AUDIT.md Gate
   3). Confirmed origin/main == live production (PORTAL-NEXT-03.1).

   calcScores() and its direct dependencies (SCORE_WEIGHTS,
   MIX_PLANOS_UNIVERSO, num, pct) below are copied BYTE-IDENTICAL from
   that source. Do not "clean up," rename, reformat, or otherwise
   touch the extracted lines — see Gate 47 (No "cleanup" drift). Any
   future change to calcScores must come from a NEW extraction off a
   NEW production source, never a local edit "for readability".

   The ONE deliberate substitution: isScoreSellerEligible below is a
   local stub (accept-all), NOT extracted from production. Real
   eligibility filtering requires DATA.vendors (a backend-loaded
   registry) — out of scope for this zero-backend Wave (Gate 25).
   Fixtures fed to this adapter must already represent eligible
   sellers only. This substitution touches NOTHING inside calcScores()
   itself — it only changes what the pre-existing filter call resolves
   to. */
(function () {
  'use strict';

  // NOT extracted from production — see comment above. Every fixture
  // record is assumed pre-filtered/eligible.
  function isScoreSellerEligible(r) { return true; }

  // ==== BEGIN byte-identical extraction from origin/main:modules/score.html ====
  const SCORE_WEIGHTS={Novos:{volume:250,share:230,familias:130,planos:130,spf:100,retorno:160},Seminovos:{volume:300,share:270,spf:150,retorno:280}};
  const MIX_PLANOS_UNIVERSO=new Set(['LINEAR','BALÃO','COPARTICIPADO','SUBSIDIADO']);
  function num(v,d=0){return (v||0).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d})}
  function pct(v){return isFinite(v)?(v*100).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+'%':'0,0%'}
  function calcScores(sales,fins){sales=(sales||[]).filter(isScoreSellerEligible);fins=(fins||[]).filter(isScoreSellerEligible);const by={};function get(v){const k=`${v.vendedor}|${v.loja}|${v.dept}`;return by[k]||(by[k]={vendedor:v.vendedor,loja:v.loja,dept:v.dept,vendas:0,fin:0,producao:0,retorno:0,spf:0,spfQtd:0,familias:new Set(),plans:new Set(),planCounts:{}})}sales.forEach(s=>{const o=get(s);o.vendas++;if(s.dept==='Novos')o.familias.add(s.familia)});fins.forEach(f=>{const o=get(f);o.fin++;o.producao+=f.valorFinanciado;o.retorno+=f.retorno+f.receitaSPF;o.spf+=f.receitaSPF;o.spfQtd+=f.spfQtd||0;o.plans.add(f.plano);o.planCounts[f.plano]=(o.planCounts[f.plano]||0)+1});const maxVenda={Novos:Math.max(1,...Object.values(by).filter(x=>x.dept==='Novos').map(x=>x.vendas)),Seminovos:Math.max(1,...Object.values(by).filter(x=>x.dept==='Seminovos').map(x=>x.vendas))};return Object.values(by).map(o=>{const w=SCORE_WEIGHTS[o.dept]||SCORE_WEIGHTS.Seminovos;const share=o.vendas?o.fin/o.vendas:0;const ret=o.producao?o.retorno/o.producao:0;const volume=Math.min(1,o.vendas/(maxVenda[o.dept]||1));const spfRate=o.fin?o.spfQtd/o.fin:0;const confVendas=Math.min(1,o.vendas/4);const confFin=Math.min(1,o.fin/2);const breakdown=[];let score=0;function addBreak(label,points,max,detail,amostra){breakdown.push({label,points,max,pct:max?points/max:0,detail,amostra});score+=points}addBreak('Volume de vendas',w.volume*volume,w.volume,`${num(o.vendas)} venda(s) · referência ${num(maxVenda[o.dept]||1)}`);addBreak('Penetração de financiamento',w.share*Math.min(1,share/0.6)*confVendas,w.share,`${num(o.fin)} financiado(s) / ${num(o.vendas)} venda(s) (${pct(share)})`,`${num(o.vendas)}/4 vendas`);if(o.dept==='Novos'){addBreak('Mix de famílias vendidas',w.familias*Math.min(1,o.familias.size/3),w.familias,`${num(o.familias.size)} de 3 famílias`);const planosValidos=new Set([...o.plans].filter(p=>MIX_PLANOS_UNIVERSO.has(p)));addBreak('Mix de planos (diversidade)',w.planos*Math.min(1,planosValidos.size/MIX_PLANOS_UNIVERSO.size),w.planos,`${num(planosValidos.size)} de ${MIX_PLANOS_UNIVERSO.size} planos comerciais`)}addBreak('SPF EXTRA',w.spf*Math.min(1,spfRate)*confFin,w.spf,`${num(o.spfQtd)} SPF / ${num(o.fin)} financiamento(s)`,`${num(o.fin)}/2 financiamentos`);addBreak('Retorno médio',w.retorno*Math.min(1,ret/0.08)*confFin,w.retorno,pct(ret),`${num(o.fin)}/2 financiamentos`);o.score=Math.round(Math.max(0,Math.min(1000,score)));o.scoreBreakdown=breakdown.map(x=>({...x,points:Math.round(x.points)}));o.share=share;o.retornoMed=ret;o.planoMais=Object.entries(o.planCounts).sort((a,b)=>b[1]-a[1])[0]?.[0]||'—';return o}).sort((a,b)=>b.score-a.score||b.fin-a.fin)}
  // ==== END byte-identical extraction ====

  window.NX_SCORE_ADAPTER = {
    id: 'score',
    compute: calcScores,
    groundTruthRef: 'origin/main:modules/score.html (portal-financiamento-brabus-secure) == live production (PORTAL-NEXT-03.1 PROVED); see docs/SCORE-ENGINE-AUDIT.md',
    // exposed for the parity harness and dev tooling only — not part
    // of the product surface
    _internal: { SCORE_WEIGHTS, MIX_PLANOS_UNIVERSO, num, pct }
  };

  // Register with the Foundation's business-adapter boundary contract.
  if (window.NX_BUSINESS_ADAPTERS) {
    window.NX_BUSINESS_ADAPTERS.registry.score = window.NX_SCORE_ADAPTER;
  }
})();
