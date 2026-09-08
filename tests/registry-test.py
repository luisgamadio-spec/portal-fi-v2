#!/usr/bin/env python3
"""Gate 13/39 — Module Registry structural test."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.dirname(HERE)
REGISTRY_PATH = os.path.join(V2_ROOT, "config", "module-registry.json")

REQUIRED_FIELDS = [
    "id", "name", "route", "title", "density", "authRequirement",
    "designPattern", "entryPoint", "businessSource", "functionalSource",
    "approvedReference", "migrationWave", "risk", "migrationStatus", "notes"
]

def main():
    data = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    modules = data.get("modules", [])
    enum = data.get("migrationStatusEnum", [])
    errors = []

    print(f"[PASS] {len(modules)} modules found in registry" if modules else "[FAIL] 0 modules found")
    if not modules:
        errors.append("registry has 0 modules")
    # Expected status per module (Gate 139: no module may self-promote to
    # HUMAN_APPROVED without an explicit human decision on record — see
    # each module's own "humanApprovalNote" in module-registry.json for
    # that record. Dashbi allowed HUMAN_APPROVED as of PORTAL-NEXT-07.6.1,
    # which reconciled a human approval ("Aprovado.") given after
    # PORTAL-NEXT-07.5.2's report that this test's own history had not
    # yet captured — not an auto-promotion, the record it guards against).
    EXPECTED_STATUS = {
        "landing": {"HUMAN_APPROVED"},
        "score": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "HUMAN_APPROVED"},
        "coparticipado": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "gestao": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        "dashbi": {"UAT_PENDING", "VISUAL_PARITY_PENDING", "PARITY_PENDING", "IN_PROGRESS", "HUMAN_APPROVED"},
        # PM-6A.2 (2026-09-07): both simulators were already HUMAN_APPROVED
        # in the registry and in docs/MIGRATION-STATUS.md (PORTAL-NEXT-08.5,
        # Gate 1/2 — human approval "Fechamos os simuladores.", see
        # docs/SIMULATOR-HUMAN-UAT-CLOSURE-08-5.md) before this fix; this
        # allowlist had simply never been updated to accept that status.
        # No new human decision is recorded by this change.
        "simulador-novos": {"NOT_MIGRATED", "IN_PROGRESS", "VISUAL_PARITY_PENDING", "UAT_PENDING", "HUMAN_APPROVED"},
        "simulador-seminovos": {"NOT_MIGRATED", "IN_PROGRESS", "VISUAL_PARITY_PENDING", "UAT_PENDING", "HUMAN_APPROVED"},
        # IA-V2-1: fixture-driven module shell + adapter landed, 0 real
        # backend/auth yet — IN_PROGRESS, not UAT_PENDING (that status is
        # reserved for a module whose real functional behavior is ready
        # for human review, which fixture-only Intelligence is not).
        "brabus-intelligence": {"NOT_MIGRATED", "IN_PROGRESS"},
        # STALE THROUGH PHASE PM-6A.1 (2026-09-07), corrected: this
        # comment previously said "The 16 other admin tabs remain
        # entirely unbuilt" — no longer true. Phase PM-6A (audit) found
        # all 13 required top-level Painel Master capabilities (17 real
        # V1 tabs minus 4 excluded by product decision — Revisões
        # Cadastrais/superseded, Relatórios RH/DP/absorbed into
        # Histórico, Métrica Analista/no product utility, Futuras
        # Funcionalidades/obsolete placeholder) implemented and
        # TECH_READY. Phase PM-6A.1 reconciled the Human UAT ledger:
        # 11/13 HUMAN_APPROVED_LOCAL, 2/13 MIXED (a real-production-event
        # dimension still pending for Fechamento de Competência and
        # Histórico de Competências — see docs/HUMAN-UAT-PAINEL-MASTER.md
        # for the full matrix). migrationStatus promoted IN_PROGRESS ->
        # UAT_PENDING on that basis — NOT HUMAN_APPROVED for the module
        # as a whole, which still requires one explicit human decision
        # covering all of Painel Master, not on record. UAT_PENDING kept
        # in this allowlist alongside IN_PROGRESS (not narrowed to just
        # the new value) so this guard continues to reject any future
        # silent self-promotion straight to HUMAN_APPROVED (Gate 139).
        "shell-admin": {"IN_PROGRESS", "UAT_PENDING"},
        # PA-1 (2026-09-07): real V1 authority proven (analistas_fi table
        # + 2 live RPCs confirmed against the real project), auth reused
        # as-is (ANALISTA_OR_MASTER already existed in auth-core.js), V2
        # implementation landed technically complete. PA-1C (2026-09-07):
        # Human explicit approval on record, verbatim "validado" — see
        # this module's own humanApprovalNote in module-registry.json —
        # HUMAN_APPROVED added on that basis, not an auto-promotion.
        "painel-analista-fi": {"NOT_MIGRATED", "UAT_PENDING", "HUMAN_APPROVED"},
        # CA-1 (2026-09-07): real V1 authority proven by direct source read
        # PLUS live, read-only database introspection (table DDL, RLS,
        # GRANTs, all 9 RPC bodies via pg_get_functiondef) — see this
        # module's own migrationCA1Note in module-registry.json and
        # docs/CHANGE-PROPOSAL-CENTRAL-ATENDIMENTO-FI.md. V2 implementation
        # landed technically complete (roster CRUD, forced status changes,
        # bulk end-of-shift, filterable/exportable history), reusing the
        # existing MASTER_ONLY authMode as-is. CA-1A (2026-09-08): committed
        # (a0e7b9b), NO_SAFE_MUTATION_TARGET_PROVEN against the real
        # database, Human UAT scoped READ-ONLY + EXPORT accordingly. CA-1B
        # (2026-09-08): Human explicit approval on record, verbatim
        # "validado" — see this module's own humanApprovalNote in
        # module-registry.json — HUMAN_APPROVED added on that basis, not an
        # auto-promotion. FROZEN as of this status.
        "central-atendimento-fi": {"NOT_MIGRATED", "UAT_PENDING", "HUMAN_APPROVED"},
    }

    for m in modules:
        for field in REQUIRED_FIELDS:
            if field not in m:
                errors.append(f"module '{m.get('id','?')}' missing field '{field}'")
        mid = m.get("id")
        status = m.get("migrationStatus")
        if mid in EXPECTED_STATUS:
            if status not in EXPECTED_STATUS[mid]:
                errors.append(f"module '{mid}' has migrationStatus={status!r}, expected one of {EXPECTED_STATUS[mid]}")
        elif status != "NOT_MIGRATED":
            errors.append(f"module '{mid}' has migrationStatus={status!r}, expected NOT_MIGRATED — only Landing/Score/Coparticipado/Gestão/Dashbi may have changed status so far (Gate 29/65)")
        if status not in enum:
            errors.append(f"module '{mid}' migrationStatus not in enum")

    ids = [m.get("id") for m in modules]
    dupes = set(i for i in ids if ids.count(i) > 1)
    if dupes:
        errors.append(f"duplicate module ids: {dupes}")

    print(f"[{'PASS' if not errors else 'FAIL'}] all modules have required contract fields and correct status discipline (landing=HUMAN_APPROVED, score/coparticipado/simulador-novos/simulador-seminovos=UAT_PENDING/VISUAL_PARITY_PENDING, brabus-intelligence=NOT_MIGRATED/IN_PROGRESS, all others=NOT_MIGRATED)")
    if errors:
        for e in errors:
            print("  -", e)
        print("\nRESULT: FAIL")
        sys.exit(1)
    print("\nRESULT: PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
