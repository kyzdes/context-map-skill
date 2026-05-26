# Template: `agent-docs/MAP.md`

This is the **single entry point** for any agent working in this repo. Keep it under 120 lines. If it grows past that, you're putting domain content here instead of in the domain docs.

Use this exact structure (preserve order, headers, and table shape):

```markdown
# Project Map: <Project Name>

**Last verified**: YYYY-MM-DD @ <commit SHA>

## What this project is
<One paragraph, 3–5 sentences. What it does, who uses it, what shape it has (monorepo / single service / library / app). No marketing language.>

## Tech stack
- Language(s): <python 3.12 / typescript 5.x / ...>
- Backend: <fastapi / express / ...>
- Frontend: <next.js 15 / vite + react / ...>
- Storage: <postgres / supabase / redis / s3>
- Deploy: <fly.io / vercel / docker compose / k8s>
- Tests: <pytest / vitest / playwright>

## How agents should navigate this repo
1. Find the domain you're working in from the table below.
2. Open the corresponding domain doc.
3. Read its "When to read me" line. If it doesn't match, you're in the wrong place — return here.
4. Use the domain doc's Neighbors section to navigate further. Don't come back to MAP.md unless lost.

## Domains
| Domain | Root path | Responsibility | Deep doc |
|--------|-----------|----------------|----------|
| <name> | `<path>`  | <one line>     | [<name>.md](domains/<name>.md) |
| ...    | ...       | ...            | ... |

## Cross-cutting concerns
Things that span multiple domains. Read these when the task isn't local to one domain.
- Auth & permissions → [cross-cutting.md#auth](cross-cutting.md#auth)
- Request lifecycle → [cross-cutting.md#request-flow](cross-cutting.md#request-flow)
- Deploy & infrastructure → [cross-cutting.md#deploy](cross-cutting.md#deploy)
- Project-wide conventions → [_meta/conventions.md](_meta/conventions.md)

## Project memory (decisions, known issues, gotchas)
The **memory layer** is the gitignored sibling of this navigation layer. Read it before planning a change.

- `../context-map-<slug>/context-map.md` — router into project memory.
- `decisions.md` (D-###), `known-issues.md` (KI-###), `gotchas.md` (G-###), `tasks.md` (T-###). Domain docs cite these IDs; they never restate them.
- The machine-readable pairing lives in `_meta/links.json`.

<If no `context-map-*/` exists yet, this section says: "Not maintained yet — invoke the `context-map` skill (`generate --layer memory`) to set up.">

## Maintenance
Docs in `agent-docs/` are the source of truth for **agent navigation**. They go stale fast if not maintained.

- After changing entry points, public API, architecture, or domain boundaries — update the affected `agent-docs/domains/<name>.md` in the same PR.
- To regenerate a doc: invoke the `context-map` skill with `update <domain>`.
- To check staleness: invoke `context-map` with `audit`.

<If hook-based policy was chosen, mention that the Stop hook surfaces a reminder when touched domains are detected.>
```

## What goes here vs. in domain docs

**MAP.md is for routing**, not content. If you're tempted to write "the auth domain uses JWTs stored in cookies" → that's a domain-doc fact, not a MAP fact. Keep the MAP to a directory of pointers.

**Bad MAP.md content** (don't include):
- Implementation details of any single domain.
- Code snippets.
- Architecture diagrams (those belong in `cross-cutting.md` or a separate human doc).
- Long prose explanations of how things work.

**Good MAP.md content**:
- The domain table.
- The cross-cutting links.
- The navigation rule (1-2-3 above).
- The maintenance rule.
