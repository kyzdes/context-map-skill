# Dashboard Data Contract

Use this when preparing context maps and indexes for the future local web dashboard. The authoritative schema is `references/schema.md`; this file describes the dashboard-facing surface.

## Frontmatter

Every `context-map.md` starts with the YAML frontmatter defined in `references/schema.md` → `Frontmatter Schema`. Split files (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`, `architecture.md`, `domains/*.md`) have no frontmatter — they are parsed only via the main file's index.

Example:

```yaml
---
context_map_version: 2
project_id: multi-resume
project_slug: multi-resume
name: "Super Resume"
repo_path: /Users/example/Desktop/Projects/multi-resume
repo_url: github.com/example/multi-resume
visibility: private
status: active
scale: M
primary_stack: [Python, FastAPI, Docker]
last_updated: 2026-04-22
last_verified_vs_code: 2026-04-22
generator: context-map-skill/0.2
---
```

See `references/schema.md` for field-level rules, enums, and types. Do not add custom fields; the dashboard ignores them.

## Parseable Sections

The collector parses these canonical sections. Headers and table columns must match `references/schema.md` exactly.

### From `known-issues.md`

```md
## Known Issues

| ID | Area | Priority | Symptom | Cause | Status | Agent-Ready | Rule |
|----|------|----------|---------|-------|--------|-------------|------|
```

### From `decisions.md`

```md
## Decisions

| ID | Date | Decision | Rationale | Consequence | Do Not Repeat |
|----|------|----------|-----------|-------------|---------------|
```

### From `tasks.md`

```md
## Tasks / Next Work

| ID | Area | Type | Task | Status | Agent-Ready | Validation |
|----|------|------|------|--------|-------------|------------|
```

### From `gotchas.md`

```md
## Gotchas

| ID | Category | Description | Trigger | Guardrail |
|----|----------|-------------|---------|-----------|
```

### From `context-map.md`

- `## Tech Stack` table
- `## Confidence Notes` table
- `## Current Phase` bullet block
- `## Linked Files` list

Allowed enum values are enumerated in `references/schema.md`. The collector rejects rows with unknown enum values and records them in `parse_warnings`.

## Dashboard Index

Default path:

```text
~/.context-map/index.json
```

Shape:

```json
{
  "version": 2,
  "generated_at": "2026-04-22T00:00:00+03:00",
  "projects": [
    {
      "project_id": "multi-resume",
      "project_slug": "multi-resume",
      "name": "Super Resume",
      "path": "/Users/example/Desktop/Projects/multi-resume",
      "context_map_folder": "/Users/example/Desktop/Projects/multi-resume/context-map-multi-resume",
      "context_map_main": "/Users/example/Desktop/Projects/multi-resume/context-map-multi-resume/context-map.md",
      "repo_url": "github.com/example/multi-resume",
      "visibility": "private",
      "status": "active",
      "scale": "M",
      "stack": ["Python", "FastAPI", "Docker"],
      "last_updated": "2026-04-22",
      "last_verified_vs_code": "2026-04-22",
      "parse_status": "ok",
      "parse_warnings": [],
      "known_issues": [],
      "decisions": [],
      "tasks": [],
      "gotchas": [],
      "confidence_notes": [],
      "current_phase": {
        "active_focus": "auth refactor",
        "recently_changed": ["src/auth/", "migrations/"],
        "unstable_areas": ["payment webhook (KI-003)"],
        "signals": "42 commits last 30d, last commit 2026-04-21"
      }
    }
  ]
}
```

`parse_status` values:

- `ok`: frontmatter and every declared split file parse without errors.
- `partial`: main file parses but one or more expected split files are missing or malformed.
- `legacy`: only a v1 single-file map exists; the project should run `migrate-legacy`.
- `missing`: no context map found.
- `error`: parsing failed (record the exception in `parse_warnings`).

## Prompt Composer Input

The dashboard composes an agent prompt from selected tasks:

```md
You are working on selected tasks across N projects.

Global rules:
- For each project, read `context-map-<slug>/context-map.md` and the split files listed in its `## Linked Files` section.
- Respect Known Issues, Decisions, and the Agent Conflict Protocol.
- If a requested change conflicts with Decisions, ask before proceeding.
- Do not expose secrets.

## Project: <name>
Path: <repo_path>
Folder: context-map-<slug>/
Task: <task row>
Relevant context:
- Known issues: ...
- Decisions: ...
- Validation: ...
- Expected output: ...
```
