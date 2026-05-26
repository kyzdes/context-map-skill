# Context Map Templates (memory layer)

All templates below define the content of individual files inside the **memory layer** `context-map-<slug>/`. Column names, enums, and section headers are fixed by `references/schema.md` — do not deviate. Generated content is always English.

> **Navigation-layer templates live in separate files**: `map-template.md`, `domain-doc-template.md`, `cross-cutting-template.md`, `distributed-claude-md-template.md`. Domain docs belong to the navigation layer (`agent-docs/domains/*.md`); the memory tree no longer carries its own `domains/`.

Pick the variant per file by project scale (see `references/schema.md` → `File Presence By Scale`). When a section is marked optional, include it only when the project has signal worth recording.

## Shared Rules

- Every `context-map.md` starts with the YAML frontmatter from `references/schema.md`.
- Split files (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`, `architecture.md`) do **not** carry frontmatter.
- One canonical top-level heading per split file; exactly one canonical table per split file (except `architecture.md`).
- Relative links between files use the filename only, since they live in the same folder: `` [`known-issues.md`](known-issues.md) ``.

---

## `context-map.md`

### XS

```md
---
context_map_version: 3
project_id: PROJECT-SLUG
project_slug: PROJECT-SLUG
name: "PROJECT"
repo_path: /absolute/path/to/project
repo_url: null
visibility: unknown
status: active
scale: XS
primary_stack: []
last_updated: YYYY-MM-DD
last_verified_vs_code: YYYY-MM-DD
generator: context-map-skill/0.3
---

# Context Map: PROJECT

> Project memory for AI agents after context reset.
> Scope: tiny project or single script.

## Project Identity

One paragraph: what it is, inputs, outputs.

## Current Phase

- Active focus: ...
- Recently changed: ...
- Last verified vs code: YYYY-MM-DD

## Tech Stack

| Layer | Tech | Version | Notes |
|-------|------|---------|-------|

## Directory Structure

```text
path/to/file  — purpose
```

## Run / Test

```bash
...
```

## Known Issues

- None known.

## Decisions

- None recorded.

## Gotchas

- None known.

## Confidence Notes

| Claim | Source | Confidence | Evidence | Needs Human? |
|-------|--------|------------|----------|--------------|

## Update Protocol

- Update when CLI/API/commands change or a fix prevents a future regression.
```

### S / M

```md
---
context_map_version: 3
project_id: PROJECT-SLUG
project_slug: PROJECT-SLUG
name: "PROJECT"
repo_path: /absolute/path/to/project
repo_url: null
visibility: unknown
status: active
scale: S            # or M
primary_stack: []
last_updated: YYYY-MM-DD
last_verified_vs_code: YYYY-MM-DD
generator: context-map-skill/0.3
---

# Context Map: PROJECT

> Router map for AI agents. Split files hold structured memory.

## Project Identity

Short, concrete: what it is in engineering terms (stack, primary entry points, main surfaces).

## Current Phase

- Active focus: <area>
- Recently changed: <dirs, last 14 days>
- Unstable areas: <files or subsystems>
- Last verified vs code: YYYY-MM-DD
- Signals: N commits last 30d, last commit YYYY-MM-DD

## Tech Stack

| Layer | Tech | Version | Notes |
|-------|------|---------|-------|

## Directory Structure

```text
...
```

## Read First By Task Type

| Task Type | Start Here | Then Check | Validate With |
|-----------|------------|------------|---------------|

## Architecture Overview                  <!-- M only; omit for S -->

```text
flow or ascii diagram
```

## Linked Files

- [`known-issues.md`](known-issues.md) — open bugs and regressions to avoid.
- [`decisions.md`](decisions.md) — active product/architecture decisions.
- [`tasks.md`](tasks.md) — ready and planned work.
- [`gotchas.md`](gotchas.md) — traps, unusual configurations.
- [`architecture.md`](architecture.md) — flows, data model, API surface.  <!-- M only -->

## Agent Conflict Protocol

Before editing code, read `known-issues.md` and `decisions.md`. If the requested change conflicts with a recorded decision or known issue:

1. Do not silently override it.
2. Explain the conflict in one short paragraph.
3. Ask the user whether to intentionally change course.
4. If confirmed, update `decisions.md` (and `known-issues.md` if relevant) with the new entry and rationale.

## Validation Checklist                   <!-- M only; omit for S -->

| Change Type | Required Check |
|-------------|----------------|

## Confidence Notes

| Claim | Source | Confidence | Evidence | Needs Human? |
|-------|--------|------------|----------|--------------|

## Update Protocol

Update this folder when:

- entry points, architecture, deploy flow, run/test commands change;
- DB schema, API contracts, auth, payments, or external integrations change;
- a significant decision is made or reversed;
- a known issue is discovered, fixed, accepted, or gets a workaround;
- a fix prevents a future regression.
```

### L

Same frontmatter (with `scale: L`) and same sections as M. Additionally include:

```md
## Apps / Packages

| Name | Path | Purpose | Owner |
|------|------|---------|-------|

## Critical Invariants

- ...
```

`architecture.md` is required. Large operational content (flows, data model, API surface) moves into `architecture.md` so the root map stays a router. Per-domain navigation docs live in the **navigation layer** (`agent-docs/domains/*.md`), not here.

### XL

```md
---
context_map_version: 3
project_id: PLATFORM-SLUG
project_slug: PLATFORM-SLUG
name: "PLATFORM"
repo_path: /absolute/path/to/platform-or-root
repo_url: null
visibility: unknown
status: active
scale: XL
primary_stack: []
last_updated: YYYY-MM-DD
last_verified_vs_code: YYYY-MM-DD
generator: context-map-skill/0.3
---

# Context Map: PLATFORM

> Root index for an AI assistant across a multi-repo / multi-surface platform.

## Project Identity

## Current Phase

(as in M/L)

## Repositories

| Name | Path | Role | Status |
|------|------|------|--------|

## Environments

| Env | URL | Purpose |
|-----|-----|---------|

## System Boundaries

```text
ascii map of surfaces and integrations
```

## Read First By Task Type

| Task Type | Start Here | Then Check | Validate With |
|-----------|------------|------------|---------------|

## Cross-Cutting Invariants

- ...

## Linked Files

- [`known-issues.md`](known-issues.md)
- [`decisions.md`](decisions.md)
- [`tasks.md`](tasks.md)
- [`gotchas.md`](gotchas.md)
- [`architecture.md`](architecture.md)
- [`../agent-docs/MAP.md`](../agent-docs/MAP.md) — navigation index; per-domain docs live there (only when `nav_layer: agent-docs`)

## Agent Conflict Protocol

(as in M/L)

## Validation Checklist

| Change Type | Required Check |
|-------------|----------------|

## Confidence Notes

| Claim | Source | Confidence | Evidence | Needs Human? |
|-------|--------|------------|----------|--------------|

## Update Protocol

(as in M/L)
```

---

## `known-issues.md`

```md
# Known Issues

> Project memory for active bugs, regressions to avoid, and watched areas. IDs are never reused.

## Known Issues

| ID | Area | Priority | Symptom | Cause | Status | Agent-Ready | Rule |
|----|------|----------|---------|-------|--------|-------------|------|
```

XS may inline this section inside `context-map.md` instead of a split file. S/M/L/XL must use the split file with the canonical table above.

---

## `decisions.md`

```md
# Decisions

> Active decisions that affect day-to-day agent work. Link to long-form ADRs in `docs/` when applicable.

## Decisions

| ID | Date | Decision | Rationale | Consequence | Do Not Repeat |
|----|------|----------|-----------|-------------|---------------|
```

---

## `tasks.md`

```md
# Tasks / Next Work

> Planned, ready, and in-progress work. Dashboards compose agent prompts from this table.

## Tasks / Next Work

| ID | Area | Type | Task | Status | Agent-Ready | Validation |
|----|------|------|------|--------|-------------|------------|
```

---

## `gotchas.md`

```md
# Gotchas

> Traps, surprising configurations, or risks that repeated themselves. Fixed issues with regression potential live in `known-issues.md` with status `fixed`.

## Gotchas

| ID | Category | Description | Trigger | Guardrail |
|----|----------|-------------|---------|-----------|
```

---

## `architecture.md`

```md
# Architecture

> Flows, data model, API surface, deployment shape. Keep diagrams ASCII and tables concrete.

## Key Flows

### Flow 1 — <name>

```text
Client -> API -> Service -> DB
```

## Data Model / Schema

| Entity | Storage | Key Fields | Notes |
|--------|---------|------------|-------|

## API Surface

| Method | Path | Purpose | Auth | Validates With |
|--------|------|---------|------|----------------|

## Configuration

| Key / File | Purpose | Default |
|------------|---------|---------|

## Local Development

```bash
...
```

## Deployment

```text
pipeline or target description
```

## Observability

| Signal | Where |
|--------|-------|
```

Omit subsections that don't apply; don't fabricate them.

---

## Per-domain docs → navigation layer

The memory tree no longer carries `domains/*.md` (removed in schema v3). Per-domain deep docs live in the **navigation layer** at `agent-docs/domains/*.md`, generated from `references/domain-doc-template.md`. For L/XL projects the memory `context-map.md` routes domain navigation to `../agent-docs/MAP.md` via the `## Linked Files` cross-link; it does not duplicate domain content.
