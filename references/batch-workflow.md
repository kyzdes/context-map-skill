# Batch Workflow

Use this when the user wants to create, update, audit, or index context maps across many projects.

## User Experience

Batch mode must not require opening each project manually.

Default flow:

1. Discover project candidates from configured and requested roots.
2. Show a numbered list with context-map status (`none`, `v2`, `legacy`, `invalid`).
3. Ask the user to choose project numbers/ranges.
4. Process selected projects one at a time.
5. After each project, write/update its `context-map-<slug>/` folder, validate it, and refresh durable progress.
6. Refresh the dashboard index.

Do not automatically write context maps for every discovered directory unless the user explicitly says "all".

## Config

Default path:

```text
~/.context-map/config.json
```

Recommended shape:

```json
{
  "version": 2,
  "project_roots": [
    "/Users/example/Desktop/Projects"
  ],
  "exclude_dirs": [
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    ".build",
    "DerivedData",
    "venv",
    ".venv"
  ],
  "context_map_folder_pattern": "context-map-*",
  "legacy_context_map_names": [
    "context-map.md",
    "docs/context-map.md",
    "CONTEXT-MAP.md",
    "docs/CONTEXT-MAP.md"
  ],
  "dashboard_index_path": "~/.context-map/index.json"
}
```

`context_map_folder_pattern` locates new-layout maps. `legacy_context_map_names` is kept for discovery only — finding one flags the project for `migrate-legacy`, it does not count as a valid map.

If the config is missing, use roots from the user request or current working directory. Offer to create the config only with user approval.

## Discovery Rules

A directory is a project candidate when it contains one of:

- `.git`
- `package.json`
- `pyproject.toml`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `compose.yml`
- `go.mod`
- `Cargo.toml`
- `project.yml`
- `Package.swift`
- `wrangler.toml`
- `wrangler.jsonc`
- `*.xcodeproj`
- `*.xcworkspace`

Avoid nested duplicates:

- If a directory has `.git`, treat it as a project root; do not scan deeper into that root for more candidates unless the nested project is also a `.git` repo.
- If both a parent and a child are candidates without `.git`, prefer the child when it has stronger app markers (`package.json`, `pyproject.toml`, `project.yml`).

### Context-Map Status Classification

| Status | Meaning |
|--------|---------|
| `none` | no folder matching `context-map-*/` and no legacy file |
| `v2` | folder exists, `context-map.md` has `context_map_version: 2` frontmatter |
| `legacy` | only a legacy single-file `context-map.md` / `docs/context-map.md` exists |
| `invalid` | folder exists but `validate_context_map.py` reports errors |

## Candidate List Format

```text
[1] multi-resume
    path: /Users/.../multi-resume
    scale: M
    stack: Python, FastAPI, Docker
    context map: v2, last_verified 2026-04-22
    git: dirty=false, branch=main

[2] MDredactor
    path: /Users/.../MD-editor/MDredactor
    scale: L
    stack: Swift/iOS/macOS
    context map: legacy (migrate recommended)
    git: no repo at root
```

Selection syntax:

```text
1,3,5-8
all
none
```

## Queueing To Protect Context

Never deeply analyze many codebases in one context.

For selected projects:

1. Start with `inspect_project.py --format json` for the project.
2. Read only that project's docs and relevant files.
3. Generate / update the `context-map-<slug>/` folder.
4. Run `validate_context_map.py` on it.
5. Write durable progress before moving to the next project.
6. If more than five projects are selected, process in chunks of 3–5 and summarize progress after each chunk.

Manual compact is not part of the workflow. Durable files are the recovery surface:

- each project's `context-map-<slug>/` folder;
- `~/.context-map/index.json`;
- optional batch plan output from discovery.

## Batch Completion

Final response should include:

- processed projects (with `v2` / refreshed);
- projects marked `legacy` that still need `migrate-legacy`;
- skipped projects and reason;
- created / updated folders;
- validator summary (pass / fail counts);
- index path;
- any projects that need manual review.
