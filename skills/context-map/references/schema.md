# Context Map Schema

Single source of truth for frontmatter, table columns, enums, ID formats, required sections, **and the navigation-layer layout**. `SKILL.md`, `references/templates.md`, `references/quality-check.md`, `references/dashboard-data.md`, `scripts/validate_context_map.py`, and `scripts/lint_docs.py` all reference this file.

If anything in another file conflicts with this schema, this file wins. Fix the other file.

## Two Layers

The skill maintains two cross-linked trees at the project root:

- **Memory layer — `context-map-<slug>/` (gitignored).** Project memory: decisions, known issues, gotchas, tasks. The bulk of this schema below.
- **Navigation layer — `agent-docs/` (committed).** Architectural navigation: a `MAP.md` router, per-domain deep docs, cross-cutting concerns, and `_meta/`. Schema in [Navigation Layer](#navigation-layer) below.

Domain docs belong to the **navigation layer only**. The memory tree no longer carries its own `domains/` (removed in version 3); for L/XL projects the memory `context-map.md` routes domain navigation to `../agent-docs/domains/`.

## Output Layout (memory layer)

All generated memory files live in a folder at the project root:

```
context-map-<slug>/
  context-map.md            # main router, always present
  known-issues.md           # S/M/L/XL
  decisions.md              # S/M/L/XL
  tasks.md                  # S/M/L/XL
  gotchas.md                # S/M/L/XL
  architecture.md           # M/L/XL  (flows, data model, API surface)
```

### Slug Rules

- `<slug>` is derived from the project directory basename.
- Lowercase; normalize via NFKD; drop non-ASCII; map any non-`[a-z0-9]` run to `-`; collapse multiple `-`; strip leading/trailing `-`.
- If a git remote exists and its repo name differs, prefer the remote repo name when the directory name is ambiguous (e.g. `Projects/app/`).
- If `context-map-<slug>/` already exists and is not our folder (no `context_map_version` frontmatter in `context-map.md`), ask before overwriting. On collision with another of our folders, append `-2`, `-3`.

### File Presence By Scale

| File | XS | S | M | L | XL |
|------|----|----|---|---|----|
| `context-map.md` | required | required | required | required | required |
| `known-issues.md` | optional | required | required | required | required |
| `decisions.md` | optional | required | required | required | required |
| `tasks.md` | optional | required | required | required | required |
| `gotchas.md` | optional | required | required | required | required |
| `architecture.md` | — | optional | required | required | required |

For XS, a single `context-map.md` with inline mini-tables is acceptable.

Per-domain deep docs are **not** in this table: they live in the navigation layer (`agent-docs/domains/*.md`). See [Navigation Layer](#navigation-layer).

## Language

All generated context-map files are in **English** regardless of session language. Conversation with the user remains in the session language. Preserve non-English proper nouns (product names, domain terms) when translating would reduce precision; note the choice in `Confidence Notes`.

## Frontmatter Schema

Every `context-map.md` begins with YAML frontmatter. Split files (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`, `architecture.md`) do **not** carry frontmatter; they are parsed only after the main file's frontmatter routes the index to them.

```yaml
---
context_map_version: 3
project_id: <slug>
project_slug: <slug>
name: "Human-readable name"
repo_path: /absolute/path/to/project
repo_url: null
visibility: private
status: active
scale: M
primary_stack: [Python, FastAPI, Docker]
nav_layer: agent-docs
last_updated: 2026-04-22
last_verified_vs_code: 2026-04-22
generator: context-map-skill/0.3
---
```

### Fields

| Field | Type | Required | Allowed / Format |
|-------|------|----------|------------------|
| `context_map_version` | int | yes | `3` for this schema |
| `project_id` | string | yes | same as `project_slug` |
| `project_slug` | string | yes | slug per rules above; matches folder suffix |
| `name` | string | yes | human-readable; quote if contains spaces |
| `repo_path` | string | yes | absolute path |
| `repo_url` | string \| null | yes | omit value or set `null` if unknown |
| `visibility` | enum | yes | `private` \| `public` \| `unknown` |
| `status` | enum | yes | `active` \| `paused` \| `archived` \| `unknown` |
| `scale` | enum | yes | `XS` \| `S` \| `M` \| `L` \| `XL` |
| `primary_stack` | array<string> | yes | 1–8 items; short tech names, not full deps |
| `nav_layer` | string \| null | yes | `agent-docs` if a paired navigation layer exists, else `null` |
| `last_updated` | date | yes | ISO `YYYY-MM-DD` |
| `last_verified_vs_code` | date | yes | ISO `YYYY-MM-DD` of the most recent research pass |
| `generator` | string | yes | `context-map-skill/<semver>` |

When `nav_layer: agent-docs`, the `## Linked Files` section MUST include a row pointing to `../agent-docs/MAP.md` (the navigation index), and the navigation layer's `_meta/links.json` MUST point back to this folder. See [Navigation Layer](#navigation-layer).

## Table Schemas

All tables below are canonical. Column names, order, and separator are fixed. Validators reject deviation.

### Known Issues (`known-issues.md`)

```md
## Known Issues

| ID | Area | Priority | Symptom | Cause | Status | Agent-Ready | Rule |
|----|------|----------|---------|-------|--------|-------------|------|
```

- `ID`: `KI-###` (zero-padded, 3 digits minimum, grow as needed).
- `Priority`: `critical` \| `high` \| `medium` \| `low`.
- `Status`: `open` \| `partial` \| `fixed` \| `wontfix` \| `watch`.
- `Agent-Ready`: `yes` \| `no` \| `needs-human`.
- Each row must be understandable without chat history.

### Decisions (`decisions.md`)

```md
## Decisions

| ID | Date | Decision | Rationale | Consequence | Do Not Repeat |
|----|------|----------|-----------|-------------|---------------|
```

- `ID`: `D-###`.
- `Date`: `YYYY-MM-DD`.
- Every decision must include rationale and explicit "do not repeat" guidance.

### Tasks / Next Work (`tasks.md`)

```md
## Tasks / Next Work

| ID | Area | Type | Task | Status | Agent-Ready | Validation |
|----|------|------|------|--------|-------------|------------|
```

- `ID`: `T-###`.
- `Type`: `feature` \| `fix` \| `refactor` \| `docs` \| `ops` \| `research`.
- `Status`: `planned` \| `ready` \| `blocked` \| `in_progress` \| `done` \| `wontfix`.
- `Agent-Ready`: `yes` \| `no` \| `needs-human`.

### Gotchas (`gotchas.md`)

```md
## Gotchas

| ID | Category | Description | Trigger | Guardrail |
|----|----------|-------------|---------|-----------|
```

- `ID`: `G-###`.
- `Category`: `runtime` \| `api` \| `deploy` \| `ui` \| `data` \| `agent` \| `other`.
- Short, actionable. Bullet form allowed for XS.

### Tech Stack (inside `context-map.md`)

```md
## Tech Stack

| Layer | Tech | Version | Notes |
|-------|------|---------|-------|
```

- `Layer` column is canonical (previous `Area` naming is removed).
- `Version` may be `-` if unpinned.

### Read First By Task Type (inside `context-map.md`)

```md
## Read First By Task Type

| Task Type | Start Here | Then Check | Validate With |
|-----------|------------|------------|---------------|
```

### Confidence Notes (inside `context-map.md`)

```md
## Confidence Notes

| Claim | Source | Confidence | Evidence | Needs Human? |
|-------|--------|------------|----------|--------------|
```

- `Confidence`: `verified` \| `inferred` \| `stale` \| `conflicting` \| `duplicate`.
- `Source`: file path (with `:line` when useful) or `inferred`.
- `Needs Human?`: `yes` \| `no`.

### Current Phase (inside `context-map.md`)

Free-form bullet block; produced by the git-signal extractor. No table.

```md
## Current Phase

- Active focus: <area>
- Recently changed: <dirs, last 14d>
- Unstable areas: <files or subsystems>
- Last verified vs code: YYYY-MM-DD
- Signals: N commits last 30d, last commit YYYY-MM-DD
```

### Validation Checklist (inside `context-map.md`, M+)

```md
## Validation Checklist

| Change Type | Required Check |
|-------------|----------------|
```

## Required Sections By File

### `context-map.md` (main)

| Section | XS | S | M | L | XL |
|---------|----|----|---|---|----|
| frontmatter | yes | yes | yes | yes | yes |
| `## Project Identity` | yes | yes | yes | yes | yes |
| `## Current Phase` | yes | yes | yes | yes | yes |
| `## Tech Stack` | yes | yes | yes | yes | yes |
| `## Directory Structure` | yes | yes | yes | yes | yes |
| `## Read First By Task Type` | no | yes | yes | yes | yes |
| `## Architecture Overview` | no | no | yes | yes | yes |
| `## Linked Files` | no | yes | yes | yes | yes |
| `## Confidence Notes` | yes | yes | yes | yes | yes |
| `## Agent Conflict Protocol` | no | yes | yes | yes | yes |
| `## Validation Checklist` | no | no | yes | yes | yes |
| `## Update Protocol` | yes | yes | yes | yes | yes |

`## Linked Files` is a compact list of relative paths to the split files:

```md
## Linked Files

- `known-issues.md` — open bugs, regressions to avoid.
- `decisions.md` — active product/architecture decisions.
- `tasks.md` — ready and planned work.
- `gotchas.md` — traps, unusual configurations.
- `architecture.md` — flows, data model, API surface.
- `../agent-docs/MAP.md` — navigation index; read first to find which domain owns the code. (only when `nav_layer: agent-docs`)
```

### Split files

Each split file starts with a single `##` header matching the table section above, optional paragraph-level intro, the canonical table, and nothing else. Validators check exactly one table of the expected shape.

## ID Uniqueness

`KI-###`, `D-###`, `T-###`, `G-###` IDs must be unique within their file. IDs are never reused after a row is deleted — pick the next unused number.

## Parser Contract

Downstream tooling (`collect_context_maps.py`, `validate_context_map.py`, future dashboard) relies on:

1. Frontmatter is the first non-whitespace content in `context-map.md`, delimited by `---`.
2. Canonical section headers are exact: `## Known Issues`, `## Decisions`, `## Tasks / Next Work`, `## Gotchas`, `## Tech Stack`, `## Read First By Task Type`, `## Confidence Notes`, `## Current Phase`, `## Agent Conflict Protocol`, `## Validation Checklist`, `## Linked Files`, `## Update Protocol`, `## Project Identity`, `## Directory Structure`, `## Architecture Overview`.
3. Tables use standard GitHub Markdown: pipe-separated, header row, divider row (`|---|`), body rows. No extra alignment markers.
4. Split files hold exactly one canonical table under a top-level `##` header.

## Navigation Layer

The committed navigation layer is produced and maintained by the same skill. Its layout:

```
agent-docs/
  MAP.md                 # router; read first. <= 120 lines.
  cross-cutting.md       # concerns spanning domains (auth, deploy, request flow, conventions)
  domains/
    <domain>.md          # per-domain deep doc; 30–200 lines
  _meta/
    conventions.md       # project-wide conventions, referenced by every domain doc
    domain-paths.json     # {domain: [roots]} — roots are repo-relative; directory roots SHOULD end with "/"
    last-verified.json    # {generated_at, commit, docs: {<doc>: {last_verified, commit}}} — drives audit
    links.json            # pairing to the memory layer (machine-readable cross-link)
```

### Canonical domain-doc headers (in order)

Enforced by `scripts/lint_docs.py`. A domain doc MUST contain, in this order:

`# Domain:` · `## When to read me` · `## Responsibility` · `## Entry points` · `## Architecture` · `## Files of interest` · `## Conventions` · `## Gotchas` · `## How to extend` · `## Neighbors` · `## Tests` · `## Notes`

Plus a `**Last verified**: YYYY-MM-DD @ <commit SHA>` line near the top. Canonical table headers: Entry points → `| File | Symbol | What it does |`; Files of interest → `| Path | What it does |`. The `## Notes` section holds hand-written content and is preserved across `update`.

### MAP.md required sections

`# Project Map: <name>`, `**Last verified**`, `## What this project is`, `## Tech stack`, `## How agents should navigate this repo`, `## Domains` (table linking to `domains/<name>.md`), `## Cross-cutting concerns`, `## Project memory` (links to `../context-map-<slug>/`), `## Maintenance`.

### `_meta/links.json` shape

```json
{
  "links_version": 1,
  "memory_folder": "context-map-<slug>",
  "memory_main": "../context-map-<slug>/context-map.md",
  "verified": "YYYY-MM-DD"
}
```

The navigation layer stays **committed** (the freshness gate needs it in the repo). The memory layer stays **gitignored**. `scripts/ensure_gitignore.py` enforces this asymmetry.

## Version History

- `3` — adds the committed navigation layer (`agent-docs/`); removes the memory tree's `domains/` (domain docs now live in the navigation layer); adds `nav_layer` frontmatter and the `../agent-docs/MAP.md` cross-link row. Migration from `2` is additive (frontmatter only). Bumps generator to `0.3`.
- `2` — split-folder layout, English-only, strict schema, `Confidence Notes` required, `Current Phase` standardised, new `generator` and `last_verified_vs_code` fields.
- `1` — single-file layout, session-language output. Detected by parsers; marked `legacy, needs migration`.
