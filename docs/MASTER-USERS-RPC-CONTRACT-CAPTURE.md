# MASTER_USERS_REAL_CONTRACT_V1

Painel Master Phase 2A, Gate 4/39 — pg_get_functiondef capture of every
RPC the Usuários surface depends on, taken directly from the real
Supabase project (`yacqlelpzchcotgngwbh`, read-only inspection only,
2026-09-04). Governance note (Phase 0/1 Gate 5): 74/135 admin functions
exist only in production, never committed to any migration file. Of the
6 functions below, only `master_convidar_usuario` and
`master_gerar_continuacao_primeiro_acesso` have a Git-tracked definition
(via `ia-reconciliation-v2-local/supabase/migrations/`); the other 4 are
captured here specifically so V2's frontend is never built against an
invisible contract (Phase 0/1 Gate 39's own instruction).

Do not hand-edit this file to "fix" a signature — it is a byte capture
of the live definition at read time. If the real function ever changes,
re-run the capture and update this file in the same commit that adapts
the frontend to the new shape.

## master_admin_security_data()

**In Git**: NO (production-only). Returns bundled `{users, configurations, audit}`.
`SECURITY DEFINER`, `VOLATILE`, gated by `is_master()`.

```sql
CREATE OR REPLACE FUNCTION public.master_admin_security_data()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
begin
  if not public.is_master() then
    raise exception 'Acesso exclusivo do perfil Master.'
      using errcode = '42501';
  end if;

  return jsonb_build_object(
    'users', coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', u.id,
          'cpf', u.cpf,
          'cpf_normalizado', u.cpf_normalizado,
          'nome', u.nome,
          'perfil', u.perfil,
          'loja', u.loja,
          'status', u.status,
          'ativo', u.ativo,
          'primeiro_acesso', u.primeiro_acesso,
          'ultimo_login', u.ultimo_login,
          'email_auth', u.email_auth,
          'tem_auth', (u.auth_user_id is not null),
          'email_divergente', (
            u.auth_user_id is not null
            and exists (
              select 1 from auth.users au
              where au.id = u.auth_user_id
                and lower(au.email) is distinct from lower(u.email_auth)
            )
          ),
          'auth_confirmado', (
            u.auth_user_id is not null
            and exists (
              select 1 from auth.users au
              where au.id = u.auth_user_id
                and au.email_confirmed_at is not null
            )
          ),
          'ativacao_legado', (
            select jsonb_build_object(
              'status', a.status,
              'email_novo', a.email_novo,
              'criado_em', a.criado_em,
              'ultimo_envio_em', a.ultimo_envio_em,
              'expira_em', a.expira_em,
              'verificado_em', a.verificado_em,
              'concluido_em', a.concluido_em
            )
            from public.ativacoes_acesso_usuario a
            where a.usuario_id = u.id
            order by a.criado_em desc
            limit 1
          )
        )
        order by u.nome
      )
      from public.usuarios u
    ), '[]'::jsonb),
    'configurations', coalesce((...13 commission keys, unrelated to Usuários...), '[]'::jsonb),
    'audit', coalesce((
      select jsonb_agg(to_jsonb(a) order by a.criado_em desc)
      from (
        select id, tipo, descricao, base_origem, loja, vendedor, cpf,
               resolvido, resolvido_por, resolvido_em, criado_em
        from public.auditoria
        order by criado_em desc
        limit 100
      ) a
    ), '[]'::jsonb)
  );
end;
$function$
```

**Fields V2's Usuários view-model must consume**: `id, cpf (mask), cpf_normalizado (mask), nome, perfil, loja, status, ativo, primeiro_acesso, ultimo_login, email_auth, tem_auth, email_divergente, auth_confirmado, ativacao_legado{...}`.
**Fields NEVER to render**: raw `cpf`/`cpf_normalizado` unmasked, `auth_user_id` (not even returned here — only the boolean `tem_auth`), any invite token.
**Login NBS is NOT in this payload** — confirmed absent (Phase 0/1 finding); do not fabricate it.

## master_convidar_usuario(p_cpf, p_nome, p_perfil, p_loja, p_email, p_nbs default null, p_status default null)

**In Git**: YES — `ia-reconciliation-v2-local/supabase/migrations/20260819180000_fase216b_reconciliacao_pos_cadastro.sql:712-829`.
`SECURITY DEFINER`, `VOLATILE`.

Full validation performed server-side (authoritative — frontend validation is UX-only echo of this):
- CPF: digits only, length ≤ 11, required.
- Nome: required, non-blank.
- Perfil: must be one of `MASTER, DIRETOR NOVOS, DIRETOR SEMINOVOS, ANALISTA, GERENTE, VENDEDOR, RECURSOS HUMANOS, RH`.
- Loja: if provided, must be one of `ABC, ALPHAVILLE, ANALIA FRANCO, BANDEIRANTES, BARRA FUNDA, EUROPA, GASTAO, NACOES`.
- Email: RFC-shaped, required; rejects `@portalfi.brabus`/`@brabus-fi.local` (internal/fake domains).
- Status (department): required for `VENDEDOR/GERENTE/ANALISTA` (one of `NOVOS, SEMINOVOS, NOVOS/SEMINOVOS`); auto-set for `DIRETOR NOVOS→NOVOS`, `DIRETOR SEMINOVOS→SEMINOVOS`, `MASTER→MASTER`; left `null` for `RH`.
- Uniqueness: CPF and email both rejected if already in use (`23505`).
- NBS (optional): if provided, rejected if already bound to another active user or a seller record with a conflicting CPF.
- On success: inserts `usuarios` (inactive, `primeiro_acesso=true`), links `portal_sellers` if NBS matched, calls `portal_reconcile_user_facts`, inserts `convites_usuario` (`status='PENDENTE'`), inserts `auditoria` (`tipo='CONVITE_USUARIO'`).
- Returns `{convite_id, usuario_id, email, status:'PENDENTE', departamento}`.

**Frontend form fields must be EXACTLY**: CPF, Nome, Perfil, Loja (optional), Email, NBS (optional), Status/Departamento (conditionally required). No other field exists on this RPC.

## master_atualizar_autorizacao_usuario(p_usuario_id, p_perfil, p_loja, p_status, p_ativo)

**In Git**: NO (production-only, captured live). `SECURITY DEFINER`, `VOLATILE`.

```sql
CREATE OR REPLACE FUNCTION public.master_atualizar_autorizacao_usuario(p_usuario_id uuid, p_perfil text, p_loja text, p_status text, p_ativo boolean)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
declare
  v_perfil text := upper(trim(coalesce(p_perfil, '')));
  v_actor_nome text;
  v_alvo public.usuarios%rowtype;
begin
  if not public.is_master() then
    raise exception 'Acesso negado.' using errcode = '42501';
  end if;

  if v_perfil not in (
    'MASTER', 'DIRETOR NOVOS', 'DIRETOR SEMINOVOS',
    'ANALISTA', 'GERENTE', 'VENDEDOR', 'RECURSOS HUMANOS', 'RH'
  ) then
    raise exception 'Perfil inválido.' using errcode = '22023';
  end if;

  update public.usuarios
  set perfil = v_perfil,
      loja = nullif(trim(coalesce(p_loja, '')), ''),
      status = nullif(trim(coalesce(p_status, '')), ''),
      ativo = coalesce(p_ativo, false)
  where id = p_usuario_id
  returning * into v_alvo;

  if v_alvo.id is null then
    raise exception 'Usuário não encontrado.' using errcode = 'P0002';
  end if;

  select nome into v_actor_nome from public.usuarios where auth_user_id = auth.uid();

  insert into public.auditoria (
    tipo, descricao, base_origem, vendedor, cpf, loja, resolvido
  ) values (
    'ADMIN_USUARIO',
    format('Autorização de usuário atualizada por %s (perfil=%s, ativo=%s)',
      coalesce(v_actor_nome, '—'), v_alvo.perfil, v_alvo.ativo),
    'RPC master_atualizar_autorizacao_usuario',
    v_alvo.nome, v_alvo.cpf, v_alvo.loja, false
  );

  return true;
end;
$function$
```

**Note**: this is a full-row overwrite (perfil/loja/status/ativo all set unconditionally), not a partial patch — the frontend must always send all 4 fields, pre-filled with the current values for any field the operator didn't intend to change. Block/Unblock reuses this same RPC with only `p_ativo` toggled and the other 3 fields echoed back unchanged.

## master_reenviar_convite(p_convite_id)

**In Git**: NO (production-only, captured live). `SECURITY DEFINER`, `VOLATILE`.

Rejects with a real, user-facing error (`55000`) if the target already has an `auth_user_id` (Auth account exists) — resend-by-RPC only applies to the "no Auth yet" case; the "Auth exists but unconfirmed" case must use the separate `admin-resend-user-invite` Edge Function instead (Phase 0/1 finding, confirmed here structurally: this RPC explicitly refuses that case rather than silently doing the wrong thing). Rejects `ACEITO` invites. On success: resets `convites_usuario.status='PENDENTE'`, inserts audit.

## master_listar_convites()

**In Git**: NO (production-only, captured live). `SECURITY DEFINER`, table-returning, gated by `public.is_master()` inline (`where public.is_master()` in the query itself — a different, terser gating idiom than the other RPCs' explicit `if not is_master() then raise`, but equivalent in effect: a non-MASTER caller gets zero rows, not an exception).

Returns one row per invite: `id, usuario_id, cpf, nome, perfil, loja, email, nbs, status, convidado_por, convidado_em, atualizado_em, tentativas_envio, aceito_em, erro_mensagem, usuario_auth_user_id, usuario_ativo, usuario_primeiro_acesso`.

## master_gerar_continuacao_primeiro_acesso(p_usuario_id, p_token_hash, p_expira_em)

**In Git**: YES — `ia-reconciliation-v2-local/supabase/migrations/20260819150000_incidente221_continuacao_primeiro_acesso.sql:72`. `SECURITY DEFINER`, `VOLATILE`.

Deliberately out of Phase 2A's UI scope (not a common daily action — a rare recovery-path tool for "Auth confirmed but Portal activation never finished"), but captured here since it's part of the full Users backend contract inventory. Full validation chain: re-reads target fresh (never trusts the caller's view), rejects if already active, rejects if `primeiro_acesso` not pending, rejects if no Auth account, rejects legacy (`@portalfi.brabus`/`@brabus-fi.local`) accounts (use migration flow instead), rejects unconfirmed Auth email, requires a `PENDENTE`/`ENVIADO` invite, server-side 5-minute rate limit. Deferred to a later Phase.

## is_master()

```sql
CREATE OR REPLACE FUNCTION public.is_master()
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
  select coalesce(public.current_portal_profile() = 'MASTER', false)
$function$
```

The shared helper several of the above RPCs use instead of re-deriving MASTER status inline.

## Edge Functions (Phase 0/1 inventory, reconfirmed unchanged)

`admin-invite-user`, `admin-resend-user-invite`, `admin-generate-user-access-link`, `admin-generate-legacy-migration-link` — all four: JWT-authenticated caller + server-side `service_role`-escalated MASTER re-check, zero `console.log` of tokens/links, all side effects audited. Full detail in the Phase 0/1 report (this document does not repeat it — no new capture needed, source unchanged).

## Profile / Store / Status enums (Gate 18-20, extracted from the above bodies, not invented)

- **Perfil** (8 values, from `master_convidar_usuario`'s `v_perfis_validos` and `usuarios_perfil_check`): `MASTER, DIRETOR NOVOS, DIRETOR SEMINOVOS, ANALISTA, GERENTE, VENDEDOR, RECURSOS HUMANOS, RH`.
- **Loja** (8 values, `BRABUS_SPECIFIC_STORE_CATALOG_DEBT` — hardcoded inside the RPC, not from a catalog table): `ABC, ALPHAVILLE, ANALIA FRANCO, BANDEIRANTES, BARRA FUNDA, EUROPA, GASTAO, NACOES`.
- **Status/Departamento** (3 values, required only for VENDEDOR/GERENTE/ANALISTA): `NOVOS, SEMINOVOS, NOVOS/SEMINOVOS`.

## User lifecycle (MASTER_USER_LIFECYCLE_V1, derived from real fields only)

| State | Derived from | Label (pt-BR) |
|---|---|---|
| `INVITED` | `tem_auth=false` (no Auth account yet) | "Convidado — aguardando aceite" |
| `AUTH_CREATED_UNCONFIRMED` | `tem_auth=true`, `auth_confirmado=false` | "Conta criada — e-mail não confirmado" |
| `FIRST_ACCESS_PENDING` | `tem_auth=true`, `auth_confirmado=true`, `primeiro_acesso=true` | "Confirmado — primeiro acesso pendente" |
| `ACTIVE` | `ativo=true`, `primeiro_acesso=false` | "Ativo" |
| `INACTIVE` | `ativo=false` (and not the invite-pending case above) | "Inativo/Bloqueado" |

No state beyond what these 4 real fields (`tem_auth`, `auth_confirmado`, `primeiro_acesso`, `ativo`) can derive — no invented "PENDING_REVIEW" or similar.