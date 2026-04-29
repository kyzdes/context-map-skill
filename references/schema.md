# Context Map Schema

Single source of truth for frontmatter, table columns, enums, ID formats, and required sections. `SKILL.md`, `references/templates.md`, `references/quality-check.md`, `references/dashboard-data.md`, and the `scripts/` validators all reference this file.

If anything in another file conflicts with this schema, this file wins. Fix the other file.

## Output Layout

All generated files live in a folder at the project root:

```
context-map-<slug>/
  context-map.md            # main router, always present
  known-issues.md           # S/M/L/XL
  decisions.md              # S/M/L/XL
  tasks.md                  # S/M/L/XL
  gotchas.md                # S/M/L/XL
  architecture.md           # M/L/XL
  domains/                  # XL only
    frontend.md
    backend.md
    mobile.md
    deploy.md
    integrations.md
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
| `domains/*.md` | — | — | — | optional | required |

For XS, a single `context-map.md` with inline mini-tables is acceptable.

## Language

All generated context-map files are in **English** regardless of session language. Conversation with the user remains in the session language. Preserve non-English proper nouns (product names, domain terms) when translating would reduce precision; note the choice in `Confidence Notes`.

## Frontmatter Schema

Every `context-map.md` begins with YAML frontmatter. Split files (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`, `architecture.md`, `domains/*.md`) do **not** carry frontmatter; they are parsed only after the main file's frontmatter routes the index to them.

```yaml
---
context_map_version: 2
project_id: <slug>
project_slug: <slug>
name: "Human-readable name"
repo_path: /absolute/path/to/project
repo_url: null
visibility: private
status: active
scale: M
primary_stack: [Python, FastAPI, Docker]
last_updated: 2026-04-22
last_verified_vs_code: 2026-04-22
generator: context-map-skill/0.2
---
```

### Fields

| Field | Type | Required | Allowed / Format |
|-------|------|----------|------------------|
| `context_map_version` | int | yes | `2` for this schema |
| `project_id` | string | yes | same as `project_slug` |
| `project_slug` | string | yes | slug per rules above; matches folder suffix |
| `name` | string | yes | human-readable; quote if contains spaces |
| `repo_path` | string | yes | absolute path |
| `repo_url` | string \| null | yes | omit value or set `null` if unknown |
| `visibility` | enum | yes | `private` \| `public` \| `unknown` |
| `status` | enum | yes | `active` \| `paused` \| `archived` \| `unknown` |
| `scale` | enum | yes | `XS` \| `S` \| `M` \| `L` \| `XL` |
| `primary_stack` | array<string> | yes | 1–8 items; short tech names, not full deps |
| `last_updated` | date | yes | ISO `YYYY-MM-DD` |
| `last_verified_vs_code` | date | yes | ISO `YYYY-MM-DD` of the most recent research pass |
| `generator` | string | yes | `context-map-skill/<semver>` |

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

## Version History

- `2` — split-folder layout, English-only, strict schema, `Confidence Notes` required, `Current Phase` standardised, new `generator` and `last_verified_vs_code` fields.
- `1` — single-file layout, session-language output. Detected by parsers; marked `legacy, needs migration`.
