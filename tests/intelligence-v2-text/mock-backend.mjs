// IA-V2-2 — local mock Supabase Auth/REST/RPC backend. Stands in for
// the ONE external boundary this phase's local harness needs a
// stand-in for: there is no real Supabase project available for local
// homologation. It serves two callers:
//
//   1. Portal V2's browser frontend (served separately, on
//      http://localhost:8080 -- see ../../README section of this
//      directory) -- for signIn/getSession/resolveAuthorizedProfile
//      (assets/js/auth-boundary.js).
//   2. The REAL, unmodified portal-ai-homolog Deno process (see
//      deno/bootstrap-text.ts) -- for its OWN internal
//      auth.getUser()/usuarios lookup (its MASTER gate) and its
//      financial-tool RPC calls (rate tables, operational_metrics).
//      This is a server-to-server call, not subject to CORS.
//
// Unlike IA-UAT-02's mock-backend.mjs, this one does NOT serve static
// files and does NOT reverse-proxy /functions/v1/* -- Portal V2 is
// its own separate static server (already-approved IA-V2-1 UI,
// unrelated to this mock), and the browser calls the real
// portal-ai-homolog DIRECTLY, cross-origin, at its own port (8801 by
// default) -- so its REAL, unmodified CORS check
// (ALLOWED_ORIGINS.has(origin)) is exercised for real, not bypassed by
// a same-origin proxy trick. That's why Portal V2 must be served from
// http://localhost:8080 specifically (already in the real function's
// CORS allowlist) rather than this repo's usual 8700 test port -- see
// docs/IA-V2-2-TEXT-INTEGRATION.md.
//
// Run: node tests/intelligence-v2-text/mock-backend.mjs [port]
// Default port: 8790

import { createServer } from "node:http";

const PORT = Number(process.argv[2] || 8790);

const FIXED_USER = {
  id: "00000000-0000-4000-8000-000000000001",
  auth_user_id: "00000000-0000-4000-8000-000000000001",
  email: "v2-master@local.test",
  perfil: "MASTER",
  ativo: true,
  primeiro_acesso: false,
  nome: "V2 Master",
  cpf_normalizado: "00000000000",
  loja: "MATRIZ",
  status: "ATIVO"
};
const NON_MASTER_USER = {
  id: "00000000-0000-4000-8000-000000000002",
  auth_user_id: "00000000-0000-4000-8000-000000000002",
  email: "v2-vendedor@local.test",
  perfil: "VENDEDOR",
  ativo: true,
  primeiro_acesso: false,
  nome: "V2 Vendedor",
  cpf_normalizado: "00000000002",
  loja: "MATRIZ",
  status: "ATIVO"
};

const MASTER_ACCESS_TOKEN = "v2-mock-master-access-token";
const NON_MASTER_ACCESS_TOKEN = "v2-mock-non-master-access-token";

const log = [];
function record(kind, detail) {
  log.push({ t: Date.now(), kind, detail });
  if (process.env.V2_MOCK_VERBOSE) console.log(`[mock] ${kind}`, detail);
}

function json(res, status, body) {
  const buf = Buffer.from(JSON.stringify(body));
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, accept-profile, content-profile, prefer, x-supabase-api-version, range, x-client-timezone",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Length": buf.length
  });
  res.end(buf);
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks);
}

// ---------- Synthetic fixture data (never real customer/rate data) ----------
// Same shapes IA-UAT-02 already proved correct against the real
// engine's own RPC row-mapping code -- reused verbatim, not
// re-derived, so this mock stays evidence-consistent across phases.

const RPC_FIXTURES = {
  simulador_get_linear_zerokm: {
    ok: true,
    linhas: [
      { prazo: 36, entrada_pct: 0.2, taxa: 0.021 },
      { prazo: 48, entrada_pct: 0.2, taxa: 0.023 },
      { prazo: 60, entrada_pct: 0.2, taxa: 0.025 }
    ]
  },
  simulador_get_taxas_subsidiadas: {
    ok: true,
    linhas: [
      { prazo: 24, taxa: 0.0049, coeficiente: 0.048, rebate: 0.02 },
      { prazo: 36, taxa: 0.0099, coeficiente: 0.036, rebate: 0.03 }
    ]
  },
  simulador_get_coparticipado: {
    ok: true,
    linhas: {
      matriz_modelos: [
        { modelo: "L200 TRITON", entrada_minima: 0.6, rebate_total: 0.05, rebate_hpe: 0.5, rebate_brabus: 0.5, prazo: 24, taxa: 1.99 },
        { modelo: "L200 TRITON", entrada_minima: 0.6, rebate_total: 0.05, rebate_hpe: 0.5, rebate_brabus: 0.5, prazo: 36, taxa: 2.1 }
      ],
      tx_coef: [
        { prazo: 24, taxa: 1.99, coeficiente: 0.045 },
        { prazo: 36, taxa: 2.1, coeficiente: 0.036 }
      ]
    }
  },
  simulador_get_balao_zerokm: {
    ok: true,
    linhas: [
      { bloco: "TRADICIONAL", entrada_minima: 0.2, prazo: 36, max_balao: 4, taxa: 0.019 },
      { bloco: "TRADICIONAL", entrada_minima: 0.2, prazo: 48, max_balao: 4, taxa: 0.021 }
    ]
  },
  simulador_get_antecipacao: {
    ok: true,
    linhas: Array.from({ length: 60 }, (_, i) => ({ meses_antecipacao: i + 1, desconto: Math.min(0.35, (i + 1) * 0.006) }))
  },
  // Shared by consultar_score_vendedores AND analisar_historico_financiamento
  // (both real tools call fetchScoreCoparticipatedData -> this same RPC).
  // Field-for-field match of the real CoparticipatedFinanceRow/
  // CoparticipatedSaleRow interfaces -- synthetic, never real Brabus data.
  operational_score_coparticipated_data: {
    sales: [
      { date: "2026-08-05", seller: "V2 Vendedor Um", store: "MATRIZ", department: "NOVOS", model: "L200 TRITON", sale_value: 210000 },
      { date: "2026-08-12", seller: "V2 Vendedor Dois", store: "MATRIZ", department: "SEMINOVOS", model: "PAJERO SPORT", sale_value: 175000 }
    ],
    finance: [
      { date: "2026-08-05", seller: "V2 Vendedor Um", store: "MATRIZ", department: "NOVOS", model: "L200 TRITON", sale_value: 210000, financed_value: 168000, return_value: 12500, spf_value: 3200, spf_count: 1, installments: 36, installment_value: 5480.5, balloon_value: 0, plan: "LINEAR", status: "ATIVO", operation_reference: "***V2MOCK1" },
      { date: "2026-08-12", seller: "V2 Vendedor Dois", store: "MATRIZ", department: "SEMINOVOS", model: "PAJERO SPORT", sale_value: 175000, financed_value: 140000, return_value: 9800, spf_value: 2100, spf_count: 1, installments: 48, installment_value: 3720.1, balloon_value: 0, plan: "LINEAR", status: "ATIVO", operation_reference: "***V2MOCK2" }
    ]
  }
};

function operationalMetricsFixture() {
  return {
    rows: [
      {
        seller_id: "v2-seller-1", seller_name: "Vendedor V2 1", store: "MATRIZ", department: "NOVOS",
        sold_count: 8, sales_value: 1040000, financed_count: 6, share_percent: 75,
        production_value: 62000, return_value: 41000, spf_count: 3, spf_value: 9000,
        spf_net_value: 8200, profitability_value: 51000, plan_breakdown: []
      },
      {
        seller_id: "v2-seller-2", seller_name: "Vendedor V2 2", store: "FILIAL SUL", department: "SEMINOVOS",
        sold_count: 5, sales_value: 585000, financed_count: 4, share_percent: 80,
        production_value: 38500, return_value: 27600, spf_count: 2, spf_value: 5400,
        spf_net_value: 4950, profitability_value: 33200, plan_breakdown: []
      }
    ]
  };
}

// ---------- Supabase Auth ----------

function handleAuth(req, res, url) {
  if (url.pathname === "/auth/v1/token" && req.method === "POST") {
    record("auth.token", { grant_type: url.searchParams.get("grant_type") });
    return json(res, 200, {
      access_token: MASTER_ACCESS_TOKEN,
      token_type: "bearer",
      expires_in: 3600,
      refresh_token: "v2-mock-refresh-token",
      user: { id: FIXED_USER.id, email: FIXED_USER.email, aud: "authenticated", role: "authenticated" }
    });
  }
  if (url.pathname === "/auth/v1/user") {
    const authHeader = req.headers["authorization"] || "";
    const token = authHeader.replace(/^Bearer\s+/i, "").trim();
    // Allowlist, not a blocklist -- real GoTrue rejects anything that
    // isn't a valid signed user JWT (see IA-UAT-02 for the full
    // rationale re: the anon-key-as-bearer fallback quirk).
    if (token === MASTER_ACCESS_TOKEN) {
      record("auth.user", {});
      return json(res, 200, { id: FIXED_USER.id, email: FIXED_USER.email, aud: "authenticated", role: "authenticated" });
    }
    if (token === NON_MASTER_ACCESS_TOKEN) {
      record("auth.user.non_master", {});
      return json(res, 200, { id: NON_MASTER_USER.id, email: NON_MASTER_USER.email, aud: "authenticated", role: "authenticated" });
    }
    record("auth.user.rejected", { token });
    return json(res, 401, { error: "invalid_token", error_description: "JWT expired or invalid" });
  }
  if (url.pathname === "/auth/v1/logout") return json(res, 204, {});
  return null;
}

// ---------- Supabase REST / RPC ----------

async function handleRest(req, res, url) {
  if (url.pathname === "/rest/v1/usuarios") {
    record("rest.usuarios", { query: url.search });
    const isSingle = (req.headers["accept"] || "").includes("vnd.pgrst.object");
    const wantsNonMaster = url.search.includes(NON_MASTER_USER.auth_user_id);
    const row = wantsNonMaster ? NON_MASTER_USER : FIXED_USER;
    return json(res, 200, isSingle ? row : [row]);
  }

  const rpcMatch = url.pathname.match(/^\/rest\/v1\/rpc\/([a-z_]+)$/);
  if (rpcMatch && req.method === "POST") {
    const name = rpcMatch[1];
    const bodyRaw = await readBody(req);
    let params = {};
    try { params = bodyRaw.length ? JSON.parse(bodyRaw.toString("utf8")) : {}; } catch { /* ignore */ }
    record("rpc", { name, params });

    if (name === "usuario_logado_fi" || name === "registrar_meu_login") return json(res, 200, [FIXED_USER]);
    if (name === "operational_record_access_event") return json(res, 200, { ok: true });
    if (name in RPC_FIXTURES) return json(res, 200, RPC_FIXTURES[name]);
    if (name === "operational_metrics") return json(res, 200, operationalMetricsFixture());

    // Generic, disclosed fallback for every RPC not explicitly
    // fixtured this phase -- shaped to avoid crashing defensive
    // frontend/tool code, never a fabricated specific business claim.
    record("rpc.generic_fallback", { name });
    return json(res, 200, { ok: true, linhas: [] });
  }

  return null;
}

// ---------- OpenAI mock (Gate 31/32: DETERMINISTIC_MODEL_BOUNDARY_E2E,
// NOT real OpenAI orchestration -- no safe local homolog OpenAI
// credentials are available this phase, so this is disclosed and used
// instead. Redirected here from the real portal-ai-homolog process by
// deno/fetch-patch.ts, which rewrites https://api.openai.com/* to
// this mock's /openai/* -- the real source code itself is unmodified
// and has no idea it's talking to a mock.
//
// The mock "model" only ever DECIDES which tool to call for a known
// scripted prompt and narrates the tool's own real result back in
// text -- it never invents or computes a financial number itself.
// ---------- */

function lastUserMessage(input) {
  for (let i = input.length - 1; i >= 0; i--) {
    if (input[i]?.role === "user") return String(input[i].content || "");
  }
  return "";
}
function lastFunctionCallOutput(input) {
  for (let i = input.length - 1; i >= 0; i--) {
    if (input[i]?.type === "function_call_output") return input[i];
  }
  return null;
}

const MODEL_SCRIPT = [
  { match: /resultado do mês passado/i, call: { name: "consultar_resultado", arguments: { period: "previous_month", start_date: null, end_date: null, store: null, department: null } } },
  {
    match: /financiamento linear.*R\$\s*120\.000|linear.*36 meses/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: null, department: "NOVOS", vehicle_value: 120000, down_payment: 30000, down_payment_percent: null, target_payment: null, term_months: 36, vehicle_year: null, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /financiamento linear.*seminovo|linear seminovo/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: null, department: "SEMINOVOS", vehicle_value: 80000, down_payment: 16000, down_payment_percent: null, target_payment: null, term_months: 36, vehicle_year: 2022, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /balão de R\$\s*40\.000/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: "BALAO", department: "NOVOS", vehicle_value: 150000, down_payment: 30000, down_payment_percent: null, target_payment: null, term_months: 36, vehicle_year: null, down_payment_percents: null, balloon_value: 40000, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /Coparticipado.*L200 Triton|L200 Triton.*Coparticipado/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: "COPARTICIPADO", department: "NOVOS", vehicle_value: 200000, down_payment: 120000, down_payment_percent: null, target_payment: null, term_months: 24, vehicle_year: null, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: "L200 TRITON", rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /Taxas Subsidiadas.*R\$\s*90\.000|R\$\s*90\.000.*Taxas Subsidiadas/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: "TAXAS_SUBSIDIADAS", department: "NOVOS", vehicle_value: 90000, down_payment: 50000, down_payment_percent: null, target_payment: null, term_months: null, vehicle_year: null, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /entrada de R\$\s*10\.000/i, // negative/ineligible -- below the 50% floor
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: "TAXAS_SUBSIDIADAS", department: "NOVOS", vehicle_value: 50000, down_payment: 10000, down_payment_percent: null, target_payment: null, term_months: null, vehicle_year: null, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: null } }
  },
  {
    match: /taxa implícita.*R\$\s*100\.000|R\$\s*100\.000.*36x/i,
    call: { name: "calcular_taxa_financiamento", arguments: { financed_amount: 100000, term_months: 36, payment: 4485.75 } }
  },
  {
    match: /antecipação.*explícita|antecipação.*data de.*2027/i,
    call: { name: "simular_antecipacao", arguments: { term_months: 36, monthly_payment: 1800, first_due_date: "2027-01-05", settlement_date: "2027-03-01", scope: "all", range_from: null, range_to: null, single_installment: null, balloons: null } }
  },
  {
    match: /antecipação.*R\$\s*50\.000.*sem informar/i,
    call: { name: "simular_antecipacao", arguments: { term_months: 36, monthly_payment: 1800, first_due_date: null, settlement_date: "2027-03-01", scope: "all", range_from: null, range_to: null, single_installment: null, balloons: null } }
  },
  { match: /pagar à vista R\$\s*50\.000 ou financiar/i, call: { name: "simular_cash_conversion", arguments: { capital: 50000, monthly_payment: 1500, term_months: 12, application_rate: null } } },
  { match: /0,90%|2% ao mês em vez da taxa oficial/i, call: { name: "simular_cash_conversion", arguments: { capital: 50000, monthly_payment: 1500, term_months: 12, application_rate: 0.02 } } },
  {
    match: /semestral|anual/i,
    call: { name: "simular_financiamento", arguments: { mode: "payment", financing_type: "SEMESTRAL_ANUAL", department: "NOVOS", vehicle_value: 100000, down_payment: 30000, down_payment_percent: null, target_payment: null, term_months: 36, vehicle_year: null, down_payment_percents: null, balloon_value: null, balloon_month: null, balloon_cap: null, term_months_list: null, balloons: null, balloon_count_max: null, priority: null, model: null, rate: null, min_sale_value: null, periodicity: "semestral" } }
  },
  {
    match: /ranking de score/i,
    call: { name: "consultar_score_vendedores", arguments: { mode: "ranking", period: "previous_month", start_date: null, end_date: null, store: null, department: null, seller: null, top_n: null, order: null } }
  },
  {
    match: /hist[óo]rico de financiamentos/i,
    call: { name: "analisar_historico_financiamento", arguments: { period: "previous_month", start_date: null, end_date: null, department: null, store: null, model: null, plan_filter: null, mode: "summary", down_payment_min_percent: null, down_payment_max_percent: null, limit: null } }
  },
  { match: /outro cliente, esquece esse/i, call: { name: "iniciar_novo_cliente", arguments: {} } }
];

function textResponse(text) {
  return { output: [{ type: "message", content: [{ type: "output_text", text }] }], usage: { input_tokens: 10, output_tokens: 10 }, model: "v2-mock-model" };
}
function toolCallResponse(name, args, callId) {
  return { output: [{ type: "function_call", call_id: callId, name, arguments: JSON.stringify(args) }], usage: { input_tokens: 10, output_tokens: 10 }, model: "v2-mock-model" };
}
function narrateToolResult(name, outputJson) {
  let parsed;
  try { parsed = JSON.parse(outputJson); } catch { parsed = null; }
  if (!parsed) return "Não consegui interpretar o resultado da consulta.";
  if (parsed.error) return `Não consegui concluir: ${parsed.error}`;
  if (name === "iniciar_novo_cliente") return "Prontinho, começamos do zero — pode me contar sobre o novo cliente.";
  return `[V2 mock narration for ${name}] ${JSON.stringify(parsed)}`;
}

async function handleOpenAI(req, res, url) {
  if (url.pathname === "/openai/v1/responses" && req.method === "POST") {
    const bodyRaw = await readBody(req);
    const body = JSON.parse(bodyRaw.toString("utf8"));
    const input = body.input || [];
    record("openai.responses", { lastUser: lastUserMessage(input).slice(0, 120), inputLen: input.length });

    const pendingOutput = lastFunctionCallOutput(input);
    if (pendingOutput) {
      const toolName = pendingOutput.call_id.startsWith("mock-") ? pendingOutput.call_id.slice("mock-".length) : "tool";
      return json(res, 200, textResponse(narrateToolResult(toolName, pendingOutput.output)));
    }

    const userMsg = lastUserMessage(input);
    if (userMsg === "__V2_TRIGGER_UPSTREAM_ERROR__") {
      record("openai.responses.simulated_failure", {});
      return json(res, 500, { error: { message: "simulated upstream failure (IA-V2-2 test harness)" } });
    }
    const scripted = MODEL_SCRIPT.find((s) => s.match.test(userMsg));
    if (scripted) return json(res, 200, toolCallResponse(scripted.call.name, scripted.call.arguments, `mock-${scripted.call.name}`));

    record("openai.responses.unscripted", { userMsg: userMsg.slice(0, 200) });
    return json(res, 200, textResponse("Não tenho um cenário de teste roteirizado para essa pergunta neste mock local."));
  }
  return null;
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, accept-profile, content-profile, prefer, x-supabase-api-version, range, x-client-timezone",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    });
    return res.end();
  }
  if (url.pathname === "/__v2/log") return json(res, 200, log);
  if (url.pathname === "/__v2/ping") return json(res, 200, { ok: true });

  try {
    if (url.pathname.startsWith("/auth/v1/")) {
      const handled = handleAuth(req, res, url);
      if (handled !== null) return;
    }
    if (url.pathname.startsWith("/rest/v1/")) {
      const handled = await handleRest(req, res, url);
      if (handled !== null) return;
    }
    if (url.pathname.startsWith("/openai/")) {
      const handled = await handleOpenAI(req, res, url);
      if (handled !== null) return;
    }
  } catch (e) {
    record("error", { message: String(e) });
    return json(res, 500, { error: "mock_backend_error", detail: String(e) });
  }

  record("unhandled", { method: req.method, path: url.pathname });
  json(res, 404, { error: "not_found_in_mock", path: url.pathname });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[mock-backend] listening on http://127.0.0.1:${PORT}`);
});
