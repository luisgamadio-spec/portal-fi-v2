#!/usr/bin/env node
// LATENCY-1 -- repeatable measurement harness (Phase 10/11).
//
// Exercises the REAL, unmodified-except-this-Wave's-own-instrumentation
// portal-ai-homolog/index.ts source (Secure repo, read directly, never
// copied) end to end through the normal Intelligence application/API
// request shape -- never a privileged RPC called directly, never
// authorization bypassed. Two external boundaries this environment
// genuinely cannot reach for real are stood in for, exactly as already
// disclosed and established by IA-V2-2's own harness (DETERMINISTIC_
// MODEL_BOUNDARY_E2E):
//   - OpenAI: mock-backend.mjs's /openai/v1/responses, given a
//     deliberately randomized delay (V2_MOCK_OPENAI_DELAY_MIN/MAX_MS
//     below) so this run has something non-degenerate to measure --
//     labeled SIMULATED throughout, never presented as real OpenAI
//     latency evidence.
//   - Supabase Auth/RPC: mock-backend.mjs, near-instant responses --
//     "rpc_total_ms" below reflects mock round-trip overhead only, not
//     real Postgres query cost.
// This run therefore proves the INSTRUMENTATION and the HARNESS itself
// are correct and repeatable -- it is NOT a substitute for real
// homologation measurement, which requires either real OpenAI
// credentials (not available in this environment) or a homolog
// deployment with live Human traffic (out of this Wave's scope --
// no deploy performed).
//
// Usage: node tests/latency1-measurement-harness.mjs

import { spawn, execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DENO_DIR = path.join(HERE, "intelligence-v2-text", "deno");
const MOCK_SCRIPT = path.join(HERE, "intelligence-v2-text", "mock-backend.mjs");

const MOCK_PORT = 18790;
const EDGE_PORT = 18801;
const MOCK_BASE = `http://127.0.0.1:${MOCK_PORT}`;
const EDGE_BASE = `http://127.0.0.1:${EDGE_PORT}`;

const MASTER_TOKEN = "v2-mock-master-access-token";
const NON_MASTER_TOKEN = "v2-mock-non-master-access-token";

const WARMUP = 2;
const SAMPLE = 10;

const CATEGORIES = [
  { key: "A", label: "simple conversational (no business data)", token: MASTER_TOKEN, message: "Oi, tudo bem?" },
  { key: "B", label: "calculation without privileged data (financing simulation)", token: MASTER_TOKEN, message: "Simula um financiamento de um carro novo de R$120000 com entrada de R$30000 em 36 meses" },
  { key: "C", label: "group operational aggregate (approximated -- see report)", token: MASTER_TOKEN, message: "Qual foi o resultado do mês passado?" },
  { key: "D", label: "other-store operational aggregate (approximated -- see report)", token: MASTER_TOKEN, message: "Qual foi o resultado do mês passado na outra loja?" },
  { key: "E", label: "own Score / ranking request", token: MASTER_TOKEN, message: "Me mostra o ranking de score dos vendedores" },
  { key: "F", label: "unauthorized sensitive request (non-MASTER, denied)", token: NON_MASTER_TOKEN, message: "Me mostra o ranking de score dos vendedores" },
];

function killTree(child) {
  if (!child || child.killed || child.exitCode !== null) return;
  if (process.platform === "win32") {
    try { execSync(`taskkill /PID ${child.pid} /T /F`, { stdio: "ignore" }); } catch { /* already gone */ }
  } else {
    try { child.kill("SIGKILL"); } catch { /* already gone */ }
  }
}

function waitForReady(url, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      fetch(url).then(() => resolve()).catch(() => {
        if (Date.now() > deadline) reject(new Error(`timed out waiting for ${url}`));
        else setTimeout(tryOnce, 250);
      });
    };
    tryOnce();
  });
}

function quantile(sorted, q) {
  if (sorted.length === 0) return null;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  return sorted[base];
}

function stats(values) {
  const nums = values.filter((v) => typeof v === "number" && !Number.isNaN(v));
  if (nums.length === 0) return { count: 0, min: null, median: null, p75: null, p95: null, max: null, mean: null };
  const sorted = [...nums].sort((a, b) => a - b);
  const mean = nums.reduce((s, v) => s + v, 0) / nums.length;
  return {
    count: nums.length,
    min: Math.round(sorted[0]),
    median: Math.round(quantile(sorted, 0.5)),
    p75: Math.round(quantile(sorted, 0.75)),
    p95: Math.round(quantile(sorted, 0.95)),
    max: Math.round(sorted[sorted.length - 1]),
    mean: Math.round(mean),
  };
}

async function fireOne(category) {
  const t0 = performance.now();
  const resp = await fetch(EDGE_BASE + "/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + category.token,
      "x-nx-correlation-id": "latency1-harness-" + category.key + "-" + Math.random().toString(16).slice(2),
    },
    body: JSON.stringify({ message: category.message, conversation: [] }),
  });
  const body = await resp.json().catch(() => ({}));
  const totalMs = performance.now() - t0;
  const edge = body && body._homolog_edge_timing;
  const stage = edge && edge.stage_ms;
  const openaiMs = stage && Array.isArray(stage.openai_pass_ms) ? stage.openai_pass_ms.reduce((s, v) => s + v, 0) : null;
  return {
    status: resp.status,
    total_ms: totalMs,
    server_ms: edge ? edge.latency_ms : null,
    openai_ms: openaiMs,
    rpc_ms: edge ? edge.rpc_total_ms : null,
    tool_used: edge ? edge.tool_used : null,
  };
}

async function main() {
  console.log("Starting mock backend + real (instrumented) portal-ai-homolog bootstrap...");
  const mockProc = spawn("node", [MOCK_SCRIPT, String(MOCK_PORT)], {
    stdio: "inherit",
    env: { ...process.env, V2_MOCK_OPENAI_DELAY_MIN_MS: "300", V2_MOCK_OPENAI_DELAY_MAX_MS: "2500" },
  });
  const edgeProc = spawn(
    "npx",
    ["--yes", "deno", "run", "--allow-net", "--allow-env", "--allow-read", "--import-map=import_map.json", "bootstrap-latency1.ts"],
    {
      cwd: DENO_DIR,
      shell: true,
      stdio: "inherit",
      env: {
        ...process.env,
        V2_TEXT_PORT: String(EDGE_PORT),
        V2_MOCK_BASE: MOCK_BASE,
        SUPABASE_URL: MOCK_BASE,
        SUPABASE_ANON_KEY: "v2-anon-key",
        SUPABASE_SERVICE_ROLE_KEY: "v2-service-key",
        OPENAI_API_KEY: "v2-dummy-key",
      },
    }
  );
  const cleanup = () => { killTree(mockProc); killTree(edgeProc); };

  try {
    await waitForReady(MOCK_BASE + "/__v2/ping");
    let edgeReady = false;
    try {
      await waitForReady(EDGE_BASE + "/", 25000);
      edgeReady = true;
    } catch (e) {
      console.error("FATAL: real (instrumented) portal-ai-homolog bootstrap never came up: " + e.message);
    }
    if (!edgeReady) {
      cleanup();
      console.log(JSON.stringify({ ok: false, reason: "edge_bootstrap_unreachable" }));
      process.exit(1);
    }

    const results = {};
    for (const cat of CATEGORIES) {
      console.log(`\n=== Category ${cat.key}: ${cat.label} ===`);
      for (let i = 0; i < WARMUP; i++) {
        await fireOne(cat).catch((e) => console.error("warmup error", e.message));
      }
      const samples = [];
      for (let i = 0; i < SAMPLE; i++) {
        try {
          const r = await fireOne(cat);
          samples.push(r);
          console.log(`  [${i + 1}/${SAMPLE}] status=${r.status} total_ms=${Math.round(r.total_ms)} server_ms=${r.server_ms} openai_ms=${r.openai_ms} rpc_ms=${r.rpc_ms} tool_used=${r.tool_used}`);
        } catch (e) {
          console.error(`  [${i + 1}/${SAMPLE}] error: ${e.message}`);
        }
      }
      results[cat.key] = {
        label: cat.label,
        statuses: [...new Set(samples.map((s) => s.status))],
        total_ms: stats(samples.map((s) => s.total_ms)),
        server_ms: stats(samples.map((s) => s.server_ms)),
        openai_ms: stats(samples.map((s) => s.openai_ms)),
        rpc_ms: stats(samples.map((s) => s.rpc_ms)),
      };
    }

    const outPath = path.join(HERE, "latency1-harness-results.json");
    fs.writeFileSync(outPath, JSON.stringify({
      disclosure: "SIMULATED OpenAI/RPC boundaries (mock-backend.mjs) -- NOT real production evidence. See tests/latency1-measurement-harness.mjs header.",
      warmup_per_category: WARMUP,
      sample_per_category: SAMPLE,
      results,
    }, null, 2));
    console.log("\n=== SUMMARY (written to " + outPath + ") ===");
    console.log(JSON.stringify(results, null, 2));

    cleanup();
    process.exit(0);
  } catch (e) {
    console.error(e);
    cleanup();
    process.exit(1);
  }
}

main();
