# Template: `agent-docs/domains/<name>.md`

Each domain doc has the same shape. Target length: **80–200 lines**. If yours exceeds 200, the domain is probably two domains. If under 30, it's probably part of another.

Use this exact structure:

```markdown
# Domain: <name>

**Last verified**: YYYY-MM-DD @ <commit SHA>
**Root**: `<path/to/domain/>` (and others if multi-path)

## When to read me
Read this when you're working in `<root path>`, touching `<related-concern>`, or implementing anything related to <one-line capability>.

Skip this if you're only working in <other-domain>. If you're not sure which domain you're in — go back to [MAP.md](../MAP.md).

## Responsibility
<2–4 sentences. What this domain owns. Be specific about what it does NOT own — the boundary is more useful than the inclusion.>

## Entry points
| File | Symbol | What it does |
|------|--------|--------------|
| `path/to/file.py` | `main()` | <one line> |
| `path/to/router.ts` | `Router` | <one line> |

## Architecture (3–7 bullets)
- <one bullet per major moving part. Avoid prose. e.g., "Requests hit `router.py`, get validated by `schemas.py`, dispatched to `services/`, which write via `repository.py`.">
- ...

## Files of interest
Only list files the agent will likely need to read. Aim for 5–20.

| Path | What it does |
|------|--------------|
| `path/to/file.py` | <one line> |
| ... | ... |

## Conventions
Domain-local rules an agent must follow when editing here. 3–8 bullets.
- <e.g., "All handlers return `Result[T, ApiError]`, never raise.">
- <e.g., "Migrations go in `migrations/`, named `NNNN_description.sql`.">

## Gotchas
Non-obvious things. Past bugs. Counter-intuitive constraints. Things that look wrong but aren't.
- <e.g., "`session_id` in the cookie is **not** the DB primary key — it's the Redis key. PK is `user_id`.">
- <e.g., "Don't call `verify_token()` inside the middleware — it's already validated by the gateway.">

## How to extend
Common changes and where to make them.
- **Adding a new endpoint**: <where, what files to touch>
- **Adding a new <thing>**: <where>
- **Changing <X>**: <where>

## Neighbors
- **Depends on**: [<domain>.md](<domain>.md) (for <reason>), [<other>.md](<other>.md) (for <reason>)
- **Depended on by**: [<domain>.md](<domain>.md), ...

## External integrations
<Only if any. List third-party services this domain talks to. Include the auth boundary (where credentials are loaded from).>
- <Service>: <what it's used for>, config at `<path>`.

## Tests
- Where the tests live: `<path>`
- How to run them: `<command>`
- <Any special setup, e.g., requires a running Postgres>

## Notes
<Free-form section for things that don't fit elsewhere. Hand-written notes go here and the `update` mode preserves them.>
```

## Writing rules (agent-friendly, not human-friendly)

1. **Tables > prose** for file lists, entry points, neighbors. An agent parses tables predictably.
2. **No paragraph longer than 5 lines.** Split with subheadings.
3. **No marketing words**: drop "robust", "scalable", "elegant", "beautifully", "production-grade".
4. **Concrete file paths and symbol names**, not abstract descriptions. `auth/middleware.py:verify_token()` beats "the auth middleware".
5. **Last-verified date is mandatory**. Without it, `audit` can't function.
6. **Neighbors section is mandatory**. Skipping it forces the agent back to MAP.md, which defeats the layered design.

## When to split a domain

A domain doc that hits any of these is too big:
- More than 200 lines.
- More than 20 files in "Files of interest".
- "Responsibility" needs an "and" connecting two different things.
- "How to extend" has more than 8 entries.

Split along the natural seam in the code. Update MAP.md when you do.
