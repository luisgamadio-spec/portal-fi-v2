// IA-V2-2 harness shim -- redirects portal-ai-homolog/index.ts's own
// `import { serve } from "https://deno.land/std@0.168.0/http/server.ts"`
// (via --import-map) to this file, so the real, UNMODIFIED source can
// bind to a harness-controlled local port instead of std's hardcoded
// default (port 8000). Behavior is otherwise identical to the real
// std serve(): same handler signature, same semantics -- only the
// bind port/hostname is sourced from an env var instead of omitted.
// (Identical in purpose to ia-reconciliation-v2-local's own
// tests/ai-uat-e2e/deno/shim-http-server.ts from IA-UAT-02 -- kept as
// its own copy here rather than imported across repos, since the
// Intelligence repository stays read-only this phase.)
export async function serve(
  handler: (req: Request) => Response | Promise<Response>,
  _options?: { port?: number; hostname?: string }
): Promise<void> {
  const port = Number(Deno.env.get("V2_TEXT_PORT") || 8000);
  const server = Deno.serve({ port, hostname: "127.0.0.1", onListen: () => {
    console.log(`[v2-shim] listening on http://127.0.0.1:${port}`);
  } }, handler);
  await server.finished;
}
