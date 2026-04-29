---
name: context-map
description: Generate, update, audit, and conflict-check project context maps for AI coding agents. Use when the user asks for a project context map, agent memory document, onboarding map, known issues/decisions log, or wants to preserve project decisions and gotchas for future AI development work.
metadata:
  short-description: Create AI-agent project context maps
  version: "0.2"
---

# Context Map

Create or maintain a `context-map-<slug>/` folder at the project root: a compact operational map split across domain files that helps AI coding agents reorient after a context reset, find the right files, avoid repeated mistakes, and respect project history.

A context map is not a README, PRD, or full architecture spec. It is project memory for future agents.

## Output Language

All context-map files are generated in **English** regardless of session language. Conversation with the user stays in the session language. Preserve established non-English project names or domain terms only when translating would reduce precision; note that choice in `Confidence Notes`.

The full schema (layout, frontmatter, table columns, enums, required sections) lives in `references/schema.md`. Treat it as authoritative; if any other file disagrees, follow `schema.md` and fix the other file.

## Modes

- **generate**: create a new `context-map-<slug>/` folder.
- **update**: refresh an existing map while preserving hand-written notes.
- **audit**: review an existing map and report missing/stale sections, schema violations, and drift from code.
- **conflict-check**: compare a requested change against `known-issues.md` and `decisions.md`, stop before editing code, and ask the user before violating project history.
- **migrate-legacy**: convert an older single-file `context-map.md` / `docs/context-map.md` into the new folder layout via `scripts/migrate_legacy.py`.
- **batch-discover**: find project candidates across one or more project roots.
- **batch-plan**: show discovered projects and ask the user to select numbers/ranges before writing maps.
- **batch-generate**: create or update context maps for selected projects, one project at a time.
- **batch-index**: collect existing context maps into a dashboard-ready JSON index.
- **dashboard-data**: prepare or refresh `~/.context-map/index.json` for a future local web UI.

Infer the mode from the request. Default to `generate` when no map exists and `update` when one exists. If a legacy single-file map is detected, default to `migrate-legacy` and stop before touching code.

## First Run

If no `context-map-*/` folder exists in the project, treat this as a first run and read `references/first-run.md` before making edits.

On first run the skill:

1. Briefly explains, in the session language, that it will create a project memory folder for future agents.
2. Scans for existing agent-config files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md`) and proposes adding a "Project Context Map" stanza to the most appropriate one, always waiting for user approval (details in `references/first-run.md`).
3. Optionally offers to add a generic rule to `~/.claude/CLAUDE.md` so every future project with a `context-map-*/` folder is read automatically. Only on explicit approval.
4. Optionally offers `.gitignore` updates when the repo is public or visibility is unclear.

Do not modify `CLAUDE.md`, `AGENTS.md`, `.gitignore`, or `~/.claude/CLAUDE.md` silently. Everything goes through a visible diff and explicit approval.

## Batch And Dashboard

For batch requests, read `references/batch-workflow.md` and `references/dashboard-data.md`.

Default config path:

```text
~/.context-map/config.json
```

Default dashboard index path:

```text
~/.context-map/index.json
```

Batch generation must show discovered project candidates and ask the user to choose projects before writing files. Do not deeply analyze many codebases in one context. Process selected projects as a queue and write durable progress after each project.

## Required Workflow

1. Find the project root. Prefer the current working directory unless the user names a path.
2. Read existing agent/project guidance first: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md`, README, architecture docs, PRD, `decisions.md`, `known-issues.md`, ADRs, troubleshooting notes.
3. If this is first run, follow `references/first-run.md`.
4. Run the bundled inspector:

```bash
python3 scripts/inspect_project.py /path/to/project --format json
```

JSON output includes git signals (recent commits, churn per directory) and doc-drift candidates, in addition to file/stack/scale data.

5. Determine project scale using `references/heuristics.md`.
6. Cross-check code against existing docs to build a confidence ledger (see `references/first-run.md` → `Context Collection Flow`):
   - `verified`: present in code and mentioned in docs, consistent.
   - `inferred`: present in code, not documented.
   - `stale`: mentioned in docs, absent or changed in code.
   - `conflicting`: docs disagree with each other.
   - `duplicate`: same topic repeated in multiple docs with different detail.
7. Load templates from `references/templates.md` and the schema from `references/schema.md`. Populate split files per scale.
8. Always include `Known Issues`, `Decisions`, `Tasks / Next Work`, `Gotchas`, `Agent Conflict Protocol`, and `Confidence Notes` unless the user explicitly asks for a minimal XS scratch note.
9. Validate the generated folder:

```bash
python3 scripts/validate_context_map.py /path/to/project/context-map-<slug>
```

10. If validation fails, fix the output before reporting success. Never claim completion with failing validation.
11. Ensure the generated folder is gitignored. The skill never lets context-map content leak into a repo's history — it is project memory, not source code, and may carry private operational notes:

```bash
# always: project-level rule (idempotent; touches only the project's .gitignore)
python3 scripts/ensure_gitignore.py --scope project --project /path/to/project

# once per machine (skill offers this on first ever run, then skips):
python3 scripts/ensure_gitignore.py --scope global
```

The global rule writes to the user's git excludes file (resolved via `core.excludesfile` → `$XDG_CONFIG_HOME/git/ignore` → `~/.config/git/ignore`) so every repo on the machine ignores `context-map-*/` even if its local `.gitignore` is missing the rule.

12. If the requested work conflicts with a known issue or decision, stop before editing code and ask the user to confirm the change of direction. See `references/decision-format.md` → `Agent Conflict Protocol`.

## Batch Workflow

For `batch-*` modes:

1. Load `~/.context-map/config.json` if it exists.
2. Merge roots from config and the user's request.
3. Run discovery:

```bash
python3 scripts/discover_projects.py --config ~/.context-map/config.json --format markdown
```

4. Show project candidates with numbers, path, scale, stack, context-map status (`none`, `v2`, `legacy`, `invalid`), and git status.
5. Ask the user to choose numbers/ranges unless they explicitly requested all.
6. For each selected project, run the single-project workflow and update/write its context map.
7. Refresh the dashboard index:

```bash
python3 scripts/collect_context_maps.py --config ~/.context-map/config.json --output ~/.context-map/index.json
```

If a batch is large, split it into chunks of 3–5 projects and report progress after each chunk.

## Where To Write

- Existing `context-map-<slug>/` folder: update files in place.
- No map yet: create `context-map-<slug>/` at project root, with the split files required by the project's scale.
- Legacy `context-map.md` or `docs/context-map.md` detected: run `migrate-legacy` (do not silently overwrite).

Do not include secrets, private tokens, passwords, API keys, or live credentials. Reference secret-holding file paths only if useful and safe.

## Required Sections

See `references/schema.md` → `Required Sections By File` for the authoritative matrix. In short, every project above XS needs: identity, current phase, tech stack, read-first routing, architecture overview, known issues, decisions, tasks, gotchas, agent conflict protocol, confidence notes, validation checklist, update protocol.

See also:

- `references/schema.md` for every canonical table and field.
- `references/templates.md` for per-file templates keyed to scale.
- `references/heuristics.md` for scale detection.
- `references/decision-format.md` for `Known Issues`, `Decisions`, and conflict protocol details.
- `references/first-run.md` for onboarding, `.gitignore`, agent-file integration.
- `references/batch-workflow.md` for multi-project discovery and queueing.
- `references/dashboard-data.md` for frontmatter and index JSON shape.
- `references/quality-check.md` for final validation.

## Update Rules

When updating an existing map:

- Preserve accurate manual notes. The stanzas and tables touched by the skill are idempotent where possible; hand-written commentary between sections must survive.
- Remove or mark stale claims when code/docs contradict them; add a row to `Confidence Notes` for each contradiction.
- Prefer adding a new decision over silently rewriting project history.
- If a known issue was fixed, keep it when future agents might repeat the mistake; mark status `fixed` and add the regression rule.
- Keep `context-map.md` concise. Move deep details into `architecture.md` or `domains/*.md`.
- Bump `last_updated` and `last_verified_vs_code` on every run.
