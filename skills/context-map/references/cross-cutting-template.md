# Template: `agent-docs/cross-cutting.md`

Cross-cutting concerns are things that span multiple domains: auth, request flow, deploy, observability, conventions. They live here so domain docs don't repeat them.

Keep this doc focused. Target: 100–250 lines. If it grows past that, split into named files (e.g., `cross-cutting/auth.md`, `cross-cutting/deploy.md`).

```markdown
# Cross-cutting concerns

**Last verified**: YYYY-MM-DD @ <commit SHA>

## Auth
<How auth works end-to-end. Where credentials are stored. Where they're validated. Which domains touch auth and how.>

- **Identity store**: <e.g., Supabase `auth.users` table>
- **Session mechanism**: <e.g., JWT in HTTP-only cookie>
- **Validation point**: <e.g., `backend/app/middleware/auth.py`>
- **Authorization model**: <e.g., RLS policies in `db/policies.sql`>
- **Domains that touch auth**: [auth.md](domains/auth.md), [api.md](domains/api.md)

## Request flow
<Trace one canonical request through the system. Concrete example beats abstract diagram.>

Example: a `POST /api/apps/install` request:
1. Hits `<entry>` → routed by `<router>`.
2. Validated against `<schema>` in `<file>`.
3. Auth checked by `<middleware>`.
4. Handler `<file>:<function>` invoked.
5. Service layer calls `<service>` which writes via `<repo>`.
6. Response shape: `<schema>` defined in `<file>`.

## Deploy
<What runs where. How a change gets to production.>

- **Build**: <command, where>
- **Where it runs**: <fly.io / vercel / self-hosted>
- **Config / secrets**: <where they live, how they're loaded>
- **Migrations**: <how they're applied, who runs them>
- **Rollback**: <procedure>

## Observability
- **Logs**: <where they go, what format, retention>
- **Metrics**: <if any, dashboard link or path>
- **Errors**: <Sentry / similar, project name>
- **Tracing**: <if any>

## Project-wide conventions
Refer to [_meta/conventions.md](_meta/conventions.md) — same place every domain doc points to.
```

## What does NOT belong here

- Domain-internal details (those go in the domain doc).
- Historical decisions / rejected approaches (those go in `context-map-*/decisions.md`).
- Architecture diagrams aimed at humans (those go in a `docs/` folder separate from `agent-docs/`).
- API reference documentation (use OpenAPI / generated docs).
