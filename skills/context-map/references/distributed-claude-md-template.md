# Template: distributed `CLAUDE.md` files

When the user opts into distributed CLAUDE.md generation, drop one of these inside each domain root (e.g., `backend/app/auth/CLAUDE.md`). Claude Code auto-loads it when an agent works in that folder, which means the agent gets the right pointer and the right local rules without having to read MAP.md first.

Keep each file **under 40 lines**. They're loaded on every tool call in that folder — bloat costs tokens forever.

## Template

```markdown
# Local rules: <domain name>

You're in the **<domain>** domain of <project>.

**Before editing anything here**, read [agent-docs/domains/<name>.md](<relative path to the doc>). It has the entry points, file list, neighbors, and gotchas you need.

## Local conventions
- <bullet — 3 to 7 max>
- ...

## Local foot-guns
- <bullet — non-obvious things that bite people in this folder, 2 to 5 max>
- ...

## After editing
If you change entry points, public API, or architecture inside this domain, update [agent-docs/domains/<name>.md](<relative path>) in the same PR.

To regenerate: invoke the `context-map` skill with `update <name>`.
```

## What to put in "Local conventions"

Things that apply *only here*, not project-wide. Project-wide conventions belong in `agent-docs/_meta/conventions.md` and are referenced from there.

Examples of good local conventions:
- "Handlers in this folder return `Result[T, ApiError]`; raising is forbidden because the middleware doesn't catch."
- "All migrations land in `./migrations/`. Schema for a migration: `NNNN_short_description.sql`."
- "Components in this folder must be pure server components (no `"use client"`)."

Examples of bad local conventions (these belong elsewhere):
- "Use 2 spaces for indentation." → project-wide, belongs in `.editorconfig` and `_meta/conventions.md`.
- "All variables in camelCase." → project-wide.
- "Always run tests before commit." → project-wide, belongs in root CLAUDE.md.

## What to put in "Local foot-guns"

Past bugs, surprising behavior, things that look right but aren't. These are the single highest-value content in a distributed CLAUDE.md because they prevent recurrence.

Examples:
- "`session_id` in the cookie is **not** the DB primary key — it's the Redis key. PK is `user_id`. Confused this in #234."
- "Don't import from `./internal/`. It's only re-exported via `index.ts` for a reason."
- "Polymorphic SQLAlchemy relations don't work with our connection pooler. Use explicit FK fields."

## When to skip distributed CLAUDE.md

- Project has < 6 domains: probably not worth the cost.
- Domains share so much that a CLAUDE.md per domain would be 80% duplicate: keep root-only.
- User explicitly says no.

When in doubt, ask the user once during Phase 3.
