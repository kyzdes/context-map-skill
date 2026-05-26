# Context Map Heuristics

Rules to classify project scale, decide template size, and collect research signals. Scale drives file presence (see `references/schema.md` → `File Presence By Scale`) and template choice (see `references/templates.md`).

## Exclude From Scans

Ignore generated, vendored, cache, and build directories:

```text
.git
node_modules
.next
dist
build
.build
DerivedData
venv
.venv
__pycache__
.pytest_cache
.mypy_cache
coverage
.turbo
.cache
Pods
vendor
```

## Scale Detection

Classify using source files after exclusions.

| Scale | Typical Shape | Target Size of `context-map.md` |
|-------|---------------|---------------------------------|
| XS | 1–5 source files, one language, no DB/deploy | 30–80 lines |
| S | 6–25 source files, one app/service | 80–160 lines |
| M | 26–150 source files, API/DB/deploy or 1–2 apps | 160–320 lines |
| L | 151–1000 source files, multiple apps, CI/CD, integrations | 300–600 lines, plus split files |
| XL | Multiple repos, platform, SDKs, or environments | root index + `architecture.md`; domain docs live in the **navigation layer** (`agent-docs/domains/*.md`), not in the memory tree |

Escalate at least to M if any of these exist:

- production deploy or CI/CD workflow;
- database migrations or schema;
- auth, payments, billing, or external AI APIs;
- mobile app plus backend/web;
- public API / SDK;
- critical operational scripts.

Escalate to L if the project has two or more major surfaces:

- frontend + backend + mobile;
- app + worker + API;
- monorepo packages / apps;
- production infrastructure plus observability.

Use XL when one context map would become a platform encyclopedia. The root memory map routes to the navigation layer's domain docs (`agent-docs/domains/*.md`) instead of carrying its own copies.

## Domain Decomposition (navigation layer)

The navigation layer splits a codebase into **domains** — units an agent reads as a whole when working there. Scale gates whether the navigation layer is generated at all, and how many domains to expect:

| Scale | Memory layer | Navigation layer (`agent-docs/`) | Domains | Parallel subagents? |
|-------|--------------|----------------------------------|---------|---------------------|
| XS | single `context-map.md` | none (offer `MAP.md` only if asked) | 0 | no |
| S | full split files | optional; `MAP.md` + a few domains if wanted | 3–5 | no |
| M | full split + `architecture.md` | recommended; `MAP.md` + domains | 6–12 | only if ≥ 5 |
| L | split + `architecture.md` | yes | 10–25 | yes |
| XL | split + `architecture.md`, **no** memory `domains/` | yes — owns all domain docs | 10–25 | yes |

The navigation layer is **opt-in below M, default at M+**. The memory layer is always offered (it is the foundation).

A directory is a good **domain** when:

- it has a clear root path (or a small set);
- you can state its responsibility in one line without "and";
- a change to it usually doesn't require simultaneous changes elsewhere;
- one domain doc is enough for an agent to work in it.

Split or merge when:

- the name is "utilities" / "helpers" / "misc" — too vague; split by what they help with;
- it spans 5+ unrelated subfolders — likely 2+ domains hiding;
- you can't describe it without "all" / "various" / "stuff";
- its doc would exceed 200 lines (split) or fall under 30 lines (merge).

Cross-cutting concerns (auth, deploy, logging, request flow, conventions) go in `cross-cutting.md`, not forced into a domain.

`scripts/inspect_project.py` emits a `domain_candidates` block (directory clusters ranked by source count + churn) as a **seed** for this decomposition — the Decompose phase edits/confirms it with the user.

## Git Churn As A Scale Confidence Signal

Scale classification is primarily file-count based. Git churn is used as a secondary signal recorded in `Current Phase` and `Confidence Notes`:

- If `git log -n 200 --name-only` touches files across 5+ top-level directories, bias toward L.
- If the repo has > 6 months of commits but one top-level directory gets > 70% of churn, flag it as the `Active focus` and keep root-level sections concise.
- If git is absent (no `.git`), mark `repo_url: null` and `Confidence Notes` row: "no git history available, scale inferred from file layout only".

## Stack Signals

| Signal | Stack |
|--------|-------|
| `package.json` | Node / React / Next / Vite |
| `next.config.*` | Next.js |
| `vite.config.*` | Vite |
| `pyproject.toml`, `requirements.txt` | Python |
| `manage.py` | Django |
| `app/main.py`, `uvicorn` | FastAPI |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `project.yml`, `*.xcodeproj`, `*.xcworkspace` | iOS / macOS |
| `Dockerfile`, `docker-compose.yml` | Container deploy |
| `.github/workflows/*.yml` | GitHub Actions |
| `wrangler.toml`, `wrangler.jsonc` | Cloudflare Workers |
| `prisma/schema.prisma` | Prisma |
| `migrations/`, `alembic/` | DB migrations |

## Read Priority

When generating or updating a map, read in this order:

1. Agent instructions: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md`.
2. Project docs: README, PRD, architecture, docs index.
3. Project memory: `decisions.md`, ADRs, `known-issues.md`, fixed-errors, troubleshooting.
4. Config and manifests: package scripts, `pyproject.toml`, Docker, CI.
5. Entry points and major modules.
6. Tests and validation scripts.
7. Git signals: recent commits, churn per directory, last-touched dates of docs.

Cross-check every claim that survives into the map against the code. Flag inconsistencies in `Confidence Notes` using the classifier from `references/first-run.md` → `Context Collection Flow`.

## Batch Discovery

When scanning many projects, a directory is a project candidate when it contains one of:

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

Show discovered candidates before writing files. The user chooses by number or range.
